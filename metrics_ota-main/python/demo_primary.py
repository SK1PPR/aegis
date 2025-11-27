"""
demo_primary.py (instrumented with SimpleMetrics, crypto fix)

Primary client demo for Uptane, extended to collect metrics. Metrics are
appended to `uptane_metrics.json` in the same schema.

Includes fix for crypto backend mismatch by forcing supported crypto
libraries (`pynacl` for ed25519, `pyca-cryptography` for RSA).
"""
from __future__ import print_function, unicode_literals
from io import open

import atexit
import canonicaljson
import json
import os
import shutil
import socket
import threading
import time

import demo
import uptane  # Import before TUF modules; may change tuf.conf values.
import uptane.common
import uptane.clients.primary as primary
import uptane.encoding.asn1_codec as asn1_codec
import tuf.client.updater
import tuf.keys
import tuf.repository_tool as rt
from demo.uptane_banners import *
from uptane import ENDCOLORS, GREEN, RED, YELLOW
import tuf.conf

from six.moves import range, xmlrpc_client, xmlrpc_server

import readline, rlcompleter
readline.parse_and_bind('tab: complete')

# === Crypto backend fix ===
tuf.conf.ED25519_CRYPTO_LIBRARY = 'pynacl'
tuf.conf.RSA_CRYPTO_LIBRARY = 'pyca-cryptography'
tuf.conf.GENERAL_CRYPTO_LIBRARY = 'pyca-cryptography'

# === Metrics ===
from .simple_metrics import metrics

# Initialize metrics categories if missing
for attr in ['network', 'ecu_updates', 'manifests', 'comm']:
    if not hasattr(metrics, attr):
        setattr(metrics, attr, [])

CLIENT_DIRECTORY_PREFIX = 'temp_primary'
CLIENT_DIRECTORY = None
_vin = 'democar'
_ecu_serial = 'INFOdemocar'
METRICS_FILE = os.path.join(uptane.WORKING_DIR, '/home/user/Desktop/shikharvashistha/OTA Metrics/uptane/uptane_metrics.json')

current_firmware_fileinfo = {}
primary_ecu = None
ecu_key = None
director_proxy = None
listener_thread = None
most_recent_signed_vehicle_manifest = None

uptane.DEMO_MODE = True

# ------------------ Utilities ------------------ #
def _metrics_system_bootstrap():
    try:
        metrics.system.setdefault('framework', 'uptane-primary-demo')
        metrics.system.setdefault('vin', _vin)
        metrics.system.setdefault('ecu_serial', _ecu_serial)
        metrics.system.setdefault('working_dir', getattr(uptane, 'WORKING_DIR', 'unknown'))
        metrics.system.setdefault('metadata_format', getattr(tuf.conf, 'METADATA_FORMAT', 'json'))
        metrics.system.setdefault('demo_mode', bool(getattr(uptane, 'DEMO_MODE', False)))
    except Exception:
        pass
    
def _metrics_save():
    try:
        metrics.record_resources()
        metrics.save(METRICS_FILE)
        print(f"Metrics saved to {METRICS_FILE}")
    except Exception as e:
        print("Failed to save metrics:", e)


atexit.register(_metrics_save)

# ------------------ Primary setup ------------------ #
def clean_slate(use_new_keys=False, vin=_vin, ecu_serial=_ecu_serial):
    global primary_ecu, CLIENT_DIRECTORY, _vin, _ecu_serial, listener_thread

    metrics.start('clean_slate')
    _vin = vin
    _ecu_serial = ecu_serial
    _metrics_system_bootstrap()

    CLIENT_DIRECTORY = os.path.join(
        uptane.WORKING_DIR, CLIENT_DIRECTORY_PREFIX + demo.get_random_string(5)
    )

    key_timeserver_pub = demo.import_public_key('timeserver')
    clock = tuf.formats.unix_timestamp_to_datetime(int(time.time())).isoformat() + 'Z'
    tuf.formats.ISO8601_DATETIME_SCHEMA.check_match(clock)

    load_or_generate_key(use_new_keys)
    atexit.register(clean_up_temp_folder)

    try:
        metrics.start('create_client_dirs')
        uptane.common.create_directory_structure_for_client(
            CLIENT_DIRECTORY,
            create_primary_pinning_file(),
            {
                demo.IMAGE_REPO_NAME: demo.IMAGE_REPO_ROOT_FNAME,
                demo.DIRECTOR_REPO_NAME: os.path.join(
                    demo.DIRECTOR_REPO_DIR, vin, 'metadata', 'root' + demo.METADATA_EXTENSION
                ),
            },
        )
        metrics.record_success('create_client_dirs')
    except IOError:
        metrics.record_error('create_client_dirs')
        raise Exception(
            RED + 'Unable to create Primary client directory structure.' + ENDCOLORS
        )
    finally:
        metrics.stop('create_client_dirs')

    tuf.conf.repository_directory = CLIENT_DIRECTORY

    metrics.start('primary_ctor')
    primary_ecu = primary.Primary(
        full_client_dir=os.path.join(uptane.WORKING_DIR, CLIENT_DIRECTORY),
        director_repo_name=demo.DIRECTOR_REPO_NAME,
        vin=_vin,
        ecu_serial=_ecu_serial,
        primary_key=ecu_key,
        time=clock,
        timeserver_public_key=key_timeserver_pub,
    )
    metrics.stop('primary_ctor')
    metrics.record_success('primary_ctor')

    if listener_thread is None:
        listener_thread = threading.Thread(target=listen)
        listener_thread.setDaemon(True)
        listener_thread.start()
    print('\n' + GREEN + 'Primary is now listening for messages from Secondaries.' + ENDCOLORS)

    try:
        register_self_with_director()
    except xmlrpc_client.Fault:
        print('Registration with Director failed. Assuming already registered.')
        metrics.record_error('register_director')

    print(GREEN + 'Generating this Primary\'s first Vehicle Version Manifest.' + ENDCOLORS)
    generate_signed_vehicle_manifest()
    submit_vehicle_manifest_to_director()
    metrics.stop('clean_slate')
    metrics.record_success('clean_slate')
    _metrics_save()

# ------------------ Pinning & Keys ------------------ #
def create_primary_pinning_file():
    with open(demo.DEMO_PRIMARY_PINNING_FNAME, 'r') as fobj:
        pinnings = json.load(fobj)
    fname_to_create = os.path.join(demo.DEMO_DIR, 'pinned.json_primary_' + demo.get_random_string(5))
    atexit.register(clean_up_temp_file, fname_to_create)
    mirror = pinnings['repositories'][demo.DIRECTOR_REPO_NAME]['mirrors'][0].replace('<VIN>', _vin)
    pinnings['repositories'][demo.DIRECTOR_REPO_NAME]['mirrors'][0] = mirror
    with open(fname_to_create, 'wb') as fobj:
        fobj.write(canonicaljson.encode_canonical_json(pinnings))
    return fname_to_create

def load_or_generate_key(use_new_keys=False):
    global ecu_key
    metrics.start('load_or_generate_key')
    if use_new_keys:
        demo.generate_key('primary')
    key_pub = demo.import_public_key('primary')
    key_pri = demo.import_private_key('primary')
    ecu_key = uptane.common.canonical_key_from_pub_and_pri(key_pub, key_pri)
    metrics.stop('load_or_generate_key')
    metrics.record_success('load_or_generate_key')

# ------------------ Update Cycle ------------------ #
def update_cycle():
    metrics.start('update_cycle')

    # Timeserver
    metrics.start('timeserver_request')
    nonces_to_send = primary_ecu.get_nonces_to_send_and_rotate()
    tserver = xmlrpc_client.ServerProxy('http://' + str(demo.TIMESERVER_HOST) + ':' + str(demo.TIMESERVER_PORT))
    t0 = time.time()
    if tuf.conf.METADATA_FORMAT == 'der':
        time_attestation = tserver.get_signed_time_der(nonces_to_send).data
    else:
        time_attestation = tserver.get_signed_time(nonces_to_send)
    verify_start = time.time()
    primary_ecu.update_time(time_attestation)
    metrics.record_verification_latency((time.time()-verify_start)*1000, method='timeserver_attestation')
    metrics.stop('timeserver_request')
    metrics.record_success('timeserver_request')

    # Metadata & Images
    metrics.start('primary_update_cycle')
    try:
        primary_ecu.primary_update_cycle()
        metrics.stop('primary_update_cycle')
        metrics.record_success('primary_update_cycle')
    except Exception:
        metrics.record_error('primary_update_cycle')
        metrics.stop('primary_update_cycle')
        raise

    generate_signed_vehicle_manifest()
    submit_vehicle_manifest_to_director()
    metrics.stop('update_cycle')
    metrics.record_success('update_cycle')
    _metrics_save()

# ------------------ Manifests ------------------ #
def generate_signed_vehicle_manifest():
    global most_recent_signed_vehicle_manifest
    metrics.start('generate_vvm')
    most_recent_signed_vehicle_manifest = primary_ecu.generate_signed_vehicle_manifest()

    # Determine size safely
    if isinstance(most_recent_signed_vehicle_manifest, bytes):
        size_bytes = len(most_recent_signed_vehicle_manifest)
    else:
        size_bytes = len(canonicaljson.encode_canonical_json(most_recent_signed_vehicle_manifest))

    metrics.record_manifest(
        ecu_id=_ecu_serial,
        size_bytes=size_bytes,
        latency_ms=0
    )
    metrics.stop('generate_vvm')
    metrics.record_success('generate_vvm')

def submit_vehicle_manifest_to_director(signed_vehicle_manifest=None):
    global most_recent_signed_vehicle_manifest

    if signed_vehicle_manifest is None:
        signed_vehicle_manifest = most_recent_signed_vehicle_manifest

    # Validate schema based on metadata format
    if tuf.conf.METADATA_FORMAT == 'der':
        uptane.formats.DER_DATA_SCHEMA.check_match(signed_vehicle_manifest)
        payload = xmlrpc_client.Binary(signed_vehicle_manifest)
        size_bytes = len(signed_vehicle_manifest)  # raw bytes
    else:
        uptane.formats.SIGNABLE_VEHICLE_VERSION_MANIFEST_SCHEMA.check_match(signed_vehicle_manifest)
        payload = signed_vehicle_manifest
        size_bytes = len(canonicaljson.encode_canonical_json(signed_vehicle_manifest))

    server = xmlrpc_client.ServerProxy(
        'http://' + str(demo.DIRECTOR_SERVER_HOST) + ':' + str(demo.DIRECTOR_SERVER_PORT)
    )

    print("Submitting the Primary's manifest to the Director.")

    metrics.start('submit_vvm')
    server.submit_vehicle_manifest(primary_ecu.vin, primary_ecu.ecu_serial, payload)
    metrics.record_manifest(
        ecu_id=_ecu_serial,
        size_bytes=size_bytes,
        latency_ms=0
    )
    metrics.stop('submit_vvm')
    metrics.record_success('submit_vvm')

    print(GREEN + 'Submission of Vehicle Manifest complete.' + ENDCOLORS)


# ------------------ Registration ------------------ #
def register_self_with_director():
    server = xmlrpc_client.ServerProxy('http://' + str(demo.DIRECTOR_SERVER_HOST) + ':' + str(demo.DIRECTOR_SERVER_PORT))
    metrics.start('register_director')
    server.register_ecu_serial(
        primary_ecu.ecu_serial,
        uptane.common.public_key_from_canonical(primary_ecu.primary_key),
        _vin,
        True
    )
    metrics.stop('register_director')
    metrics.record_success('register_director')
    _metrics_save()

# ------------------ Distribution APIs ------------------ #
def get_image_for_ecu(ecu_serial):
    metrics.start('get_image_for_ecu')
    primary_ecu._check_ecu_serial(ecu_serial)
    image_fname = primary_ecu.get_image_fname_for_ecu(ecu_serial)
    if image_fname is None:
        metrics.record_error('get_image_for_ecu')
        metrics.stop('get_image_for_ecu')
        return None, None

    data = open(image_fname, 'rb').read()
    binary_data = xmlrpc_client.Binary(data)
    relative_fname = os.path.relpath(image_fname, os.path.join(primary_ecu.full_client_dir, 'targets'))

    metrics.record_bandwidth(bytes_used=len(data))
    metrics.events.append({'event':'image_distributed','ecu_serial':ecu_serial,'filename':relative_fname,'size':len(data),'timestamp':time.time()})
    metrics.record_ecu_update(ecu_id=ecu_serial,image=relative_fname,success=True)
    metrics.record_comm(src='primary', dst=ecu_serial, latency_ms=0, bytes_sent=len(data))
    metrics.record_network(src='primary', dst='ecu_server', latency_ms=0, bytes_sent=len(data))

    metrics.record_success('get_image_for_ecu')
    metrics.stop('get_image_for_ecu')
    _metrics_save()
    return (relative_fname, binary_data)

def get_metadata_for_ecu(ecu_serial, force_partial_verification=False):
    metrics.start('get_metadata_for_ecu')
    primary_ecu._check_ecu_serial(ecu_serial)
    fname = primary_ecu.get_partial_metadata_fname() if force_partial_verification else primary_ecu.get_full_metadata_archive_fname()
    mode = 'partial' if force_partial_verification else 'full'
    data = open(fname, 'rb').read()
    binary_data = xmlrpc_client.Binary(data)
    metrics.record_bandwidth(bytes_used=len(data))
    metrics.events.append({'event':'metadata_distributed','ecu_serial':ecu_serial,'mode':mode,'size':len(data),'timestamp':time.time()})
    metrics.record_comm(src='primary', dst=ecu_serial, latency_ms=0, bytes_sent=len(data))
    metrics.record_network(src='primary', dst='ecu_server', latency_ms=0, bytes_sent=len(data))
    metrics.record_success('get_metadata_for_ecu')
    metrics.stop('get_metadata_for_ecu')
    _metrics_save()
    return binary_data

def get_time_attestation_for_ecu(ecu_serial):
    metrics.start('get_time_attestation_for_ecu')
    primary_ecu._check_ecu_serial(ecu_serial)
    attestation = primary_ecu.get_last_timeserver_attestation()
    if tuf.conf.METADATA_FORMAT == 'der':
        attestation = xmlrpc_client.Binary(attestation)
    metrics.record_success('get_time_attestation_for_ecu')
    metrics.stop('get_time_attestation_for_ecu')
    _metrics_save()
    return attestation

# ------------------ XML-RPC ------------------ #
class RequestHandler(xmlrpc_server.SimpleXMLRPCRequestHandler):
    rpc_paths = ('/RPC2',)

def register_ecu_manifest_wrapper(vin, ecu_serial, nonce, signed_ecu_manifest):
    metrics.start('submit_ecu_manifest_from_secondary')
    try:
        if tuf.conf.METADATA_FORMAT == 'der':
            primary_ecu.register_ecu_manifest(vin, ecu_serial, nonce, signed_ecu_manifest.data)
        else:
            primary_ecu.register_ecu_manifest(vin, ecu_serial, nonce, signed_ecu_manifest)
        metrics.record_success('submit_ecu_manifest_from_secondary')
        metrics.record_ecu_update(ecu_id=ecu_serial,image='unknown',success=True)
    except Exception:
        metrics.record_error('submit_ecu_manifest_from_secondary')
        raise
    finally:
        metrics.stop('submit_ecu_manifest_from_secondary')
        _metrics_save()

def listen():
    server = None
    successful_port = None
    for port in demo.PRIMARY_SERVER_AVAILABLE_PORTS:
        try:
            server = xmlrpc_server.SimpleXMLRPCServer(
                (demo.PRIMARY_SERVER_HOST, port), requestHandler=RequestHandler, allow_none=True
            )
        except socket.error:
            continue
        else:
            successful_port = port
            break
    if server is None:
        raise RuntimeError('No available port to bind Primary XMLRPC Server.')

    server.register_function(register_ecu_manifest_wrapper, 'submit_ecu_manifest')
    server.register_function(primary_ecu.register_new_secondary, 'register_new_secondary')
    server.register_function(get_time_attestation_for_ecu, 'get_time_attestation_for_ecu')
    server.register_function(get_image_for_ecu, 'get_image')
    server.register_function(get_metadata_for_ecu, 'get_metadata')
    server.register_function(primary_ecu.update_exists_for_ecu, 'update_exists_for_ecu')

    print('Primary listening on port ' + str(successful_port))
    server.serve_forever()

# ------------------ Cleanup ------------------ #
def clean_up_temp_file(filename):
    if os.path.isfile(filename):
        os.remove(filename)

def clean_up_temp_folder():
    if os.path.isdir(CLIENT_DIRECTORY):
        shutil.rmtree(CLIENT_DIRECTORY)

def try_banners():
    preview_all_banners()

def looping_update():
    while True:
        try:
            update_cycle()
        except Exception as e:
            print(repr(e))
            metrics.record_error('update_cycle')
        time.sleep(1)
