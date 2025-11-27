#!/usr/bin/env python3
"""TUF Client Example with Extended Metrics"""
# Copyright 2012 - 2017, New York University and the TUF contributors
# SPDX-License-Identifier: MIT OR Apache-2.0

import argparse
import logging
import os
import sys
import traceback
import time
import json
from hashlib import sha256
from pathlib import Path

import urllib3
import psutil   # for resource snapshots

from tuf.api.exceptions import DownloadError, RepositoryError
from tuf.ngclient import Updater

# constants
DOWNLOAD_DIR = "./downloads"
CLIENT_EXAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_FILE = "tuf_metrics.json"

# Extended metrics collector
class SimpleMetrics:
    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []     # system resource snapshots
        self.security = []      # verification/auth checks
        self.ml_metrics = []    # model-related metrics
        self.system = {}        # static metadata

    # ---- basic timing ----
    def start(self, label):
        self.timings[label] = time.time()

    def stop(self, label):
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({"metric": label, "duration_sec": duration, "timestamp": time.time()})
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1

    def record_success(self, label):
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1

    def record_error(self, label):
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1

    # ---- OTA-specific ----
    def record_update_attempt(self, update_id, success, rollback=False):
        self.events.append({
            "event": "update_attempt",
            "update_id": update_id,
            "success": success,
            "rollback": rollback,
            "timestamp": time.time()
        })
        self.counters["updates_attempted"] = self.counters.get("updates_attempted", 0) + 1
        if success:
            self.counters["updates_successful"] = self.counters.get("updates_successful", 0) + 1
        if rollback:
            self.counters["updates_rollback"] = self.counters.get("updates_rollback", 0) + 1

    def record_verification_latency(self, ms, method="rsa2048"):
        self.security.append({
            "verification_method": method,
            "latency_ms": ms,
            "timestamp": time.time()
        })

    def record_bandwidth(self, bytes_used, delta_bytes=None, full_bytes=None):
        event = {"bytes_used": bytes_used, "timestamp": time.time()}
        if delta_bytes and full_bytes:
            event["delta_ratio"] = delta_bytes / full_bytes
        self.events.append({"event": "bandwidth", **event})

    def record_storage_overhead(self, extra_bytes):
        self.events.append({
            "event": "storage_overhead",
            "extra_bytes": extra_bytes,
            "timestamp": time.time()
        })

    def record_resources(self):
        vm = psutil.virtual_memory()
        self.resources.append({
            "timestamp": time.time(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "mem_mb": vm.used / 1e6,
        })

    # ---- ML-specific ----
    def record_model_metrics(self, model_id, deploy_time, inference_latency, accuracy_delta=None, wer=None):
        self.ml_metrics.append({
            "model_id": model_id,
            "deploy_time_sec": deploy_time,
            "inference_latency_ms": inference_latency,
            "accuracy_delta": accuracy_delta,
            "wer": wer,
            "timestamp": time.time()
        })

    # ---- export & persistence ----
    def export(self):
        return {
            "events": self.events,
            "counters": self.counters,
            "resources": self.resources,
            "security": self.security,
            "ml_metrics": self.ml_metrics,
            "system": self.system,
        }

    def save(self, filename=METRICS_FILE):
        data = {}
        if os.path.exists(filename):
            with open(filename, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}

        # merge counters
        for k, v in self.counters.items():
            data.setdefault("counters", {})
            data["counters"][k] = data["counters"].get(k, 0) + v

        # append everything else
        for field in ["events", "resources", "security", "ml_metrics"]:
            data.setdefault(field, [])
            data[field].extend(getattr(self, field))

        data.setdefault("system", {}).update(self.system)

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Metrics appended to {filename}")


metrics = SimpleMetrics()

def build_metadata_dir(base_url: str) -> str:
    name = sha256(base_url.encode()).hexdigest()[:8]
    return f"{Path.home()}/.local/share/tuf-example/{name}"

def init_tofu(base_url: str) -> bool:
    """Initialize local trusted metadata (Trust-On-First-Use) and create a directory for downloads."""
    metrics.start("init_tofu")
    t0 = time.time()
    metadata_dir = build_metadata_dir(base_url)
    response = urllib3.request("GET", f"{base_url}/metadata/1.root.json")
    verify_time_ms = (time.time() - t0) * 1000
    metrics.record_verification_latency(verify_time_ms, method="bootstrap_http")

    if response.status != 200:
        print(f"Failed to download initial root {base_url}/metadata/1.root.json")
        metrics.record_error("init_tofu")
        metrics.stop("init_tofu")
        return False
    Updater(
        metadata_dir=metadata_dir,
        metadata_base_url=f"{base_url}/metadata/",
        target_base_url=f"{base_url}/targets/",
        target_dir=DOWNLOAD_DIR,
        bootstrap=response.data,
    )
    print(f"Trust-on-First-Use: Initialized new root in {metadata_dir}")
    metrics.record_success("init_tofu")
    metrics.stop("init_tofu")
    return True

def download(base_url: str, target: str) -> bool:
    """
    Download the target file using ``ngclient`` Updater.
    Returns: A boolean indicating if process was successful
    """
    metrics.start("download")
    metadata_dir = build_metadata_dir(base_url)
    if not os.path.isfile(f"{metadata_dir}/root.json"):
        print(
            "Trusted local root not found. Use 'tofu' command to Trust-On-First-Use or copy trusted root metadata to "
            f"{metadata_dir}/root.json"
        )
        metrics.record_error("download")
        metrics.stop("download")
        metrics.record_update_attempt(update_id=target, success=False)
        return False
    print(f"Using trusted root in {metadata_dir}")
    try:
        updater = Updater(
            metadata_dir=metadata_dir,
            metadata_base_url=f"{base_url}/metadata/",
            target_base_url=f"{base_url}/targets/",
            target_dir=DOWNLOAD_DIR,
        )
        t_verify = time.time()
        updater.refresh()
        verify_time_ms = (time.time() - t_verify) * 1000
        metrics.record_verification_latency(verify_time_ms, method="tuf_refresh")

        info = updater.get_targetinfo(target)
        if info is None:
            print(f"Target {target} not found")
            metrics.record_error("download")
            metrics.stop("download")
            metrics.record_update_attempt(update_id=target, success=False)
            return True

        path = updater.find_cached_target(info)
        if path:
            print(f"Target is available in {path}")
            metrics.record_success("download")
            metrics.stop("download")
            metrics.record_update_attempt(update_id=target, success=True)
            return True

        download_start = time.time()
        path = updater.download_target(info)
        download_end = time.time()
        print(f"Target downloaded and available in {path}")
        metrics.events.append({
            "metric": "download.target",
            "download_time_sec": download_end - download_start,
            "target": target,
            "size": getattr(info, 'length', 'unknown'),
            "timestamp": time.time(),
        })
        metrics.record_bandwidth(
            bytes_used=getattr(info, 'length', 0),
            delta_bytes=None,
            full_bytes=getattr(info, 'length', 0)
        )
        metrics.record_resources()

    except (OSError, RepositoryError, DownloadError) as e:
        print(f"Failed to download target {target}: {e}")
        metrics.record_error("download")
        if logging.root.level < logging.ERROR:
            traceback.print_exc()
        metrics.stop("download")
        metrics.record_update_attempt(update_id=target, success=False)
        return False

    metrics.record_success("download")
    metrics.stop("download")
    metrics.record_update_attempt(update_id=target, success=True)
    return True

def main() -> str | None:
    """Main TUF Client Example function"""
    client_args = argparse.ArgumentParser(description="TUF Client Example")
    client_args.add_argument(
        "-v",
        "--verbose",
        help="Output verbosity level (-v, -vv, ...)",
        action="count",
        default=0,
    )
    client_args.add_argument(
        "-u",
        "--url",
        help="Base repository URL",
        default="http://127.0.0.1:8001",
    )
    sub_command = client_args.add_subparsers(dest="sub_command")
    sub_command.add_parser(
        "tofu",
        help="Initialize client with Trust-On-First-Use",
    )
    download_parser = sub_command.add_parser(
        "download",
        help="Download a target file",
    )
    download_parser.add_argument(
        "target",
        metavar="TARGET",
        help="Target file",
    )
    command_args = client_args.parse_args()
    if command_args.verbose == 0:
        loglevel = logging.ERROR
    elif command_args.verbose == 1:
        loglevel = logging.WARNING
    elif command_args.verbose == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    result = None
    if command_args.sub_command == "tofu":
        if not init_tofu(command_args.url):
            result = "Failed to initialize local repository"
    elif command_args.sub_command == "download":
        if not download(command_args.url, command_args.target):
            result = f"Failed to download {command_args.target}"
    else:
        client_args.print_help()
    metrics.record_resources()
    metrics.save()  # Save metrics at the end of any run
    return result

if __name__ == "__main__":
    sys.exit(main())
