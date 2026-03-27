#!/usr/bin/env python3
"""
MQTT OTA updater with extended metrics.

- Downloads firmware announced over MQTT
- Verifies file hash and a binary-hash-tree root hash
- Moves verified firmware to sketch dir and compiles/uploads via arduino-cli
- Records detailed metrics to ota_metrics.json (events/counters/security/system/resources/timing)
"""

import os
import re
import json
import time
import shutil
import hashlib
import subprocess
import requests
import threading
from pathlib import Path

import psutil  # <-- New import for resource snapshots
import paho.mqtt.client as mqtt

# -----------------------
# Configuration (edit)
# -----------------------
METRICS_FILE = "ota_metrics.json"
FIRMWARE_DIR = "./1.SecureOTA"
SKETCH_DIR = "./1.SecureOTA"
MQTT_BROKER_IP = "127.0.0.1"
MQTT_BROKER_PORT = 1883
MQTT_SUB_TOPIC = "test/topic"

# MQTT credentials (set before running, or leave as None for no auth)
MQTT_USER = "testuser"
MQTT_PASS = "testpass"

# Arduino cli defaults
ARDUINO_CLI_BIN = "arduino-cli"  # ensure in PATH
# -----------------------

# --- SimpleMetrics ---------------------------------------------------------
class SimpleMetrics:
    """Minimal robust metrics collector with atomic save."""

    def __init__(self, filename=METRICS_FILE):
        self.filename = filename
        self.counters = {}
        self.events = []      # generic events (name/status/details/time)
        self.security = []    # verification checks
        self.system = {}      # static metadata
        self.resources = []   # new: resource snapshots
        # add thread lock for safety if MQTT uses threads
        try:
            import threading as _th
            self._lock = _th.Lock()
        except Exception:
            self._lock = None

    def _with_lock(fn):
        def wrapper(self, *a, **k):
            if self._lock:
                with self._lock:
                    return fn(self, *a, **k)
            else:
                return fn(self, *a, **k)
        return wrapper

    @_with_lock
    def increment(self, key, amount=1):
        self.counters[key] = self.counters.get(key, 0) + amount

    @_with_lock
    def add_event(self, name, status="ok", details=None):
        ev = {
            "name": name,
            "status": status,
            "details": details,
            "time": time.time()
        }
        self.events.append(ev)

    @_with_lock
    def add_security_check(self, check, result, extra=None):
        sc = {
            "check": check,
            "result": result,
            "extra": extra,
            "time": time.time()
        }
        self.security.append(sc)

    @_with_lock
    def set_system(self, key, value):
        self.system.setdefault(key, value)

    @_with_lock
    def record_resource_snapshot(self, note=None):
        vm = psutil.virtual_memory()
        self.resources.append({
            "timestamp": time.time(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "mem_mb": vm.used / 1e6,
            "note": note
        })

    @_with_lock
    def save(self):
        """Merge session metrics into on-disk JSON file atomically."""
        data = {}
        try:
            if os.path.exists(self.filename):
                with open(self.filename, "r") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
        except Exception:
            data = {}

        # Ensure schema
        if not isinstance(data.get("counters"), dict):
            data["counters"] = {}
        if not isinstance(data.get("events"), list):
            data["events"] = []
        if not isinstance(data.get("security"), list):
            data["security"] = []
        if not isinstance(data.get("system"), dict):
            data["system"] = {}
        if not isinstance(data.get("resources"), list):
            data["resources"] = []

        # Merge counters
        for k, v in self.counters.items():
            data["counters"][k] = data["counters"].get(k, 0) + v

        # Append events, security, resources
        data["events"].extend(self.events)
        data["security"].extend(self.security)
        data["resources"].extend(self.resources)
        data["system"].update(self.system)

        # Atomic write
        tmp = self.filename + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.filename)
        except Exception as e:
            print(f"[metrics] Failed to save metrics: {e}")

        # reset in-memory buffers
        self.counters.clear()
        self.events.clear()
        self.security.clear()
        self.resources.clear()


# global metrics instance
metrics = SimpleMetrics()

# -----------------------
# BinaryHashTree
# -----------------------
class BinaryHashTree:
    def __init__(self):
        self.root_hash = None

    def compute_file_hash(self, file_path):
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.digest()

    def build_tree(self, directory_path):
        ino_files = self.get_ino_files(directory_path)
        if len(ino_files) == 0:
            self.root_hash = None
            return
        data = [self.compute_file_hash(file) for file in sorted(ino_files)]
        self.root_hash = self.build_binary_hash_tree(data)

    def get_ino_files(self, directory_path):
        ino_files = []
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                if file.lower().endswith(".ino"):
                    ino_files.append(os.path.join(root, file))
        return ino_files

    def build_binary_hash_tree(self, data):
        if len(data) == 0:
            return None
        if len(data) == 1:
            return data[0]
        if len(data) % 2 == 1:
            data = data + [data[-1]]
        mid = len(data) // 2
        left_hash = self.build_binary_hash_tree(data[:mid])
        right_hash = self.build_binary_hash_tree(data[mid:])
        return hashlib.sha256(left_hash + right_hash).digest()

    def get_root_hash(self):
        return self.root_hash

# -----------------------
# Helper utils
# -----------------------
def compute_file_hash_hex(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(4096), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def get_next_firmware_filename(directory):
    os.makedirs(directory, exist_ok=True)
    files = os.listdir(directory)
    pattern = re.compile(r'^(\d+)\.SecureOTA\.ino$')
    max_number = 0
    for filename in files:
        match = pattern.match(filename)
        if match:
            number = int(match.group(1))
            if number > max_number:
                max_number = number
    return f"{max_number + 1}.SecureOTA.ino"

# -----------------------
# Arduino helpers
# -----------------------
def find_first_arduino_board(fqbn_hint=None):
    try:
        result = subprocess.run([ARDUINO_CLI_BIN, "board", "list"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
        out = result.stdout + "\n" + result.stderr
    except Exception as e:
        metrics.add_event("arduino_cli_list", "fail", {"error": str(e)})
        metrics.save()
        return None, None

    m = re.search(r"(/dev/tty\w+).*?(arduino:[\w:-]+)", out)
    if m:
        return m.group(1), m.group(2)
    return None, None

def arduino_compile_and_upload(sketch_path, port, fqbn, timeout=120):
    result = {"compile": None, "upload": None}
    try:
        ino_files = [f for f in os.listdir(sketch_path) if f.endswith(".ino")]
        if not ino_files:
            metrics.add_event("arduino_compile", "fail", {"error": "No .ino file found in sketch path"})
            metrics.save()
            result["compile"] = {"rc": 1, "stdout": "", "stderr": "No .ino file found"}
            return result
        ino_file = ino_files[0]
        ino_path = os.path.join(sketch_path, ino_file)

        compile_cmd = [ARDUINO_CLI_BIN, "compile", "--fqbn", "arduino:avr:uno", ino_path]
        cproc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        result["compile"] = {"rc": cproc.returncode, "stdout": cproc.stdout, "stderr": cproc.stderr}
        metrics.add_event("arduino_compile", "ok" if cproc.returncode == 0 else "fail", {"rc": cproc.returncode})
        metrics.save()
        if cproc.returncode != 0:
            return result

        upload_cmd = [ARDUINO_CLI_BIN, "upload", "-p", port, "--fqbn", fqbn, ino_path]
        uproc = subprocess.run(upload_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        result["upload"] = {"rc": uproc.returncode, "stdout": uproc.stdout, "stderr": uproc.stderr}
        metrics.add_event("arduino_upload", "ok" if uproc.returncode == 0 else "fail", {"rc": uproc.returncode})
        metrics.save()
    except subprocess.TimeoutExpired as e:
        metrics.add_event("arduino_cli_timeout", "fail", {"error": str(e)})
        metrics.save()
    except Exception as e:
        metrics.add_event("arduino_cli_exception", "fail", {"error": str(e)})
        metrics.save()
    return result

# -----------------------
# MQTT callbacks
# -----------------------
message_count = 0
root_hash = None
moterVersion = 0
lightVersion = 0

def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    metrics.add_event("mqtt_connect", "ok", {"rc": rc})
    metrics.increment("mqtt_connects")
    metrics.save()
    client.subscribe(MQTT_SUB_TOPIC)

def on_message(client, userdata, msg):
    import os  # Ensure access
    global message_count, root_hash, moterVersion
    message_count += 1
    metrics.increment("mqtt_messages")
    metrics.record_resource_snapshot("before_update_start")
    t0 = time.time()

    try:
        payload = json.loads(msg.payload.decode("utf-8"))
    except Exception as e:
        metrics.add_event("mqtt_message_parse", "fail", {"error": str(e)})
        metrics.save()
        print("Received non-JSON or invalid payload:", e)
        return

    print("MQTT payload:", payload)
    metrics.add_event("mqtt_message_received", "ok", {"payload_keys": list(payload.keys())})
    metrics.save()

    firmware_url = payload.get("URL")
    if not firmware_url:
        metrics.add_event("mqtt_message_invalid", "fail", {"reason": "no URL in payload"})
        metrics.save()
        print("No URL in payload; ignoring.")
        return

    if firmware_url.startswith("http://") or firmware_url.startswith("https://"):
        firmware_location = firmware_url
    else:
        firmware_location = f"http://{MQTT_BROKER_IP}{firmware_url}"

    try:
        advertised_version = float(payload.get("Version", 0))
    except Exception:
        advertised_version = 0

    if advertised_version <= moterVersion:
        print("No new firmware update required.")
        metrics.add_event("update_skipped", "ok", {"advertised_version": advertised_version, "current_version": moterVersion})
        metrics.save()
        return

    print("New firmware version available:", advertised_version)
    metrics.add_event("update_available", "ok", {"advertised_version": advertised_version})
    metrics.increment("updates_found")
    metrics.save()

    # --- Download firmware ---
    t0_download = time.time()
    fname = "1.SecureOTA.ino"
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    firmware_path = os.path.join(FIRMWARE_DIR, fname)
    try:
        r = requests.get(firmware_location, timeout=30)
        r.raise_for_status()
        with open(firmware_path, "wb") as f:
            f.write(r.content)
        metrics.add_event("firmware_download", "ok", {"url": firmware_location, "file": firmware_path, "size": len(r.content)})
        metrics.add_event("firmware_size_bytes", "ok", {"bytes": os.path.getsize(firmware_path)})
        metrics.increment("firmware_downloads")
        metrics.add_event("firmware_download_time", "ok", {"duration_sec": time.time()-t0_download})
        metrics.record_resource_snapshot("after_download")
        metrics.save()
        print(f"Firmware downloaded to {firmware_path}")
    except Exception as e:
        metrics.add_event("firmware_download", "fail", {"error": str(e), "url": firmware_location})
        metrics.increment("firmware_download_failures")
        metrics.save()
        print("Error downloading firmware:", e)
        return

    # --- File hash ---
    t0_hash = time.time()
    expected_file_hash = payload.get("FileHash")
    try:
        actual_file_hash = compute_file_hash_hex(firmware_path)
        if expected_file_hash:
            if expected_file_hash == actual_file_hash:
                metrics.add_security_check("file_hash", "ok", {"expected": expected_file_hash, "got": actual_file_hash})
            else:
                metrics.add_security_check("file_hash", "fail", {"expected": expected_file_hash, "got": actual_file_hash})
                metrics.increment("file_hash_mismatch")
                metrics.save()
                print("FileHash mismatch — aborting update.")
                return
        else:
            metrics.add_event("file_hash_missing", "ok", {"computed": actual_file_hash})
        metrics.add_event("file_hash_time", "ok", {"duration_sec": time.time()-t0_hash})
        metrics.record_resource_snapshot("after_file_hash_check")
        metrics.save()
    except Exception as e:
        metrics.add_event("file_hash_error", "fail", {"error": str(e)})
        metrics.save()
        print("Error computing file hash:", e)
        return

    # --- Binary hash tree ---
    t0_bht = time.time()
    expected_root_hash = payload.get("RootHash")
    try:
        bht = BinaryHashTree()
        bht.build_tree(FIRMWARE_DIR)
        new_root_hash = bht.get_root_hash()
        if new_root_hash is None:
            metrics.add_event("bht_empty", "fail", {"dir": FIRMWARE_DIR})
            metrics.save()
            print("No .ino files present for root-hash calculation.")
            return
        new_root_hash_hex = new_root_hash.hex()
        print("New Root Hash:", new_root_hash_hex)
        metrics.add_event("bht_rebuild", "ok", {"root": new_root_hash_hex})
        if expected_root_hash:
            if expected_root_hash == new_root_hash_hex:
                metrics.add_security_check("root_hash", "ok", {"expected": expected_root_hash, "got": new_root_hash_hex})
            else:
                metrics.add_security_check("root_hash", "fail", {"expected": expected_root_hash, "got": new_root_hash_hex})
                metrics.increment("root_hash_mismatch")
                metrics.save()
                print("RootHashes do not match. Firmware might be tampered or updated.")
                return
        else:
            metrics.add_event("root_hash_missing", "ok", {"computed": new_root_hash_hex})
        metrics.add_event("bht_time", "ok", {"duration_sec": time.time()-t0_bht})
        metrics.record_resource_snapshot("after_bht")
        metrics.save()
        print("Root Hash:", new_root_hash_hex)
    except Exception as e:
        metrics.add_event("bht_error", "fail", {"error": str(e)})
        metrics.save()
        print("Error building binary hash tree:", e)
        return

    # --- Move firmware ---
    t0_move = time.time()
    try:
        os.makedirs(SKETCH_DIR, exist_ok=True)
        target_path = os.path.join(SKETCH_DIR, os.path.basename(firmware_path))
        shutil.move(firmware_path, target_path)
        metrics.add_event("firmware_move", "ok", {"from": firmware_path, "to": target_path})
        metrics.increment("firmware_moves")
        metrics.add_event("firmware_move_time", "ok", {"duration_sec": time.time()-t0_move})
        metrics.record_resource_snapshot("after_move")
        metrics.save()
        print(f"Moved firmware to sketch path: {target_path}")
    except Exception as e:
        metrics.add_event("firmware_move", "fail", {"error": str(e)})
        metrics.increment("firmware_move_failures")
        metrics.save()
        print("Failed to move firmware to sketch path:", e)
        return

    # --- Compile & upload ---
    port, fqbn = find_first_arduino_board()
    if not port or not fqbn:
        metrics.add_event("arduino_board_not_found", "fail", {})
        metrics.increment("arduino_board_missing")
        metrics.save()
        print("No Arduino board found; aborting upload.")
        return

    t0_compile = time.time()
    compile_upload_result = arduino_compile_and_upload(SKETCH_DIR, port, fqbn)
    metrics.add_event("compile_upload_time", "ok", {"duration_sec": time.time()-t0_compile})
    metrics.record_resource_snapshot("after_compile_upload")
    metrics.add_event("deploy_result", "ok", {"compile": compile_upload_result.get("compile"), "upload": compile_upload_result.get("upload")})
    metrics.increment("deploy_attempts")
    if (compile_upload_result.get("compile") and compile_upload_result["compile"].get("rc") != 0) or \
       (compile_upload_result.get("upload") and compile_upload_result["upload"].get("rc") != 0):
        metrics.increment("deploy_failures")
        metrics.add_event("deploy_status", "fail", compile_upload_result)
        print("Compile or upload failed; check metrics for details.")
    else:
        metrics.increment("deploy_success")
        metrics.add_event("deploy_status", "ok", compile_upload_result)
        try:
            moterVersion = float(advertised_version)
            metrics.add_event("version_bumped", "ok", {"new_version": moterVersion})
        except Exception:
            pass
    metrics.save()
    elapsed = time.time() - t0
    metrics.add_event("update_total_time", "ok", {"seconds": elapsed})
    metrics.record_resource_snapshot("after_update_complete")
    metrics.save()
    print(f"Update process completed in {elapsed:.1f} seconds.")

# -----------------------
# Main runner
# -----------------------
def run_mqtt_loop():
    client = mqtt.Client()
    if MQTT_USER and MQTT_PASS:
        client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER_IP, MQTT_BROKER_PORT, 60)
    except Exception as e:
        metrics.add_event("mqtt_connect_fail", "fail", {"error": str(e)})
        metrics.save()
        print("Failed to connect to MQTT broker:", e)
        return

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Interrupted by user; shutting down.")
    except Exception as e:
        metrics.add_event("mqtt_loop_exception", "fail", {"error": str(e)})
        metrics.save()
        print("MQTT loop exception:", e)

if __name__ == "__main__":
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    os.makedirs(SKETCH_DIR, exist_ok=True)
    metrics.set_system("host", os.uname().nodename if hasattr(os, "uname") else "unknown")
    metrics.set_system("firmware_dir", os.path.abspath(FIRMWARE_DIR))
    metrics.set_system("sketch_dir", os.path.abspath(SKETCH_DIR))
    metrics.save()
    run_mqtt_loop()
