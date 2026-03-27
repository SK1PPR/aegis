#!/usr/bin/env python3
"""RAUC OTA Update Client with Extended Metrics Collection"""
# SPDX-License-Identifier: MIT OR Apache-2.0

import argparse
import asyncio
import json
import logging
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Dict, Optional, Any, List
import psutil

# D-Bus imports for RAUC integration
try:
    import dbus
    import dbus.mainloop.glib
    from gi.repository import GLib
    DBUS_AVAILABLE = True
except ImportError:
    DBUS_AVAILABLE = False
    print("Warning: D-Bus libraries not available. Install python3-dbus and python3-gi")

# Constants
RAUC_SERVICE_NAME = "de.pengutronix.rauc"
RAUC_OBJECT_PATH = "/"
RAUC_INSTALLER_INTERFACE = "de.pengutronix.rauc.Installer"
METRICS_FILE = "rauc_ota_metrics.json"

class RAUCMetrics:
    """Extended metrics collector for RAUC OTA updates"""

    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []     # system resource snapshots
        self.security = []      # verification/auth checks  
        self.ml_metrics = []    # model-related metrics
        self.system = {}        # static metadata
        self.rauc_events = []   # RAUC-specific events
        self.slots_info = {}    # slot status tracking

    # ---- Basic timing ----
    def start(self, label: str):
        """Start timing for a labeled operation"""
        self.timings[label] = time.time()

    def stop(self, label: str) -> Optional[float]:
        """Stop timing and record duration"""
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({
                "metric": label,
                "duration_sec": duration,
                "timestamp": time.time()
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1
            del self.timings[label]
            return duration
        return None

    def record_success(self, label: str):
        """Record successful operation"""
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1

    def record_error(self, label: str):
        """Record failed operation"""
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1

    # ---- RAUC/OTA-specific metrics ----
    def record_update_attempt(self, bundle_path: str, success: bool, rollback=False):
        """Record an update attempt"""
        self.rauc_events.append({
            "event": "update_attempt", 
            "bundle_path": bundle_path,
            "success": success,
            "rollback": rollback,
            "timestamp": time.time()
        })
        self.counters["updates_attempted"] = self.counters.get("updates_attempted", 0) + 1
        if success:
            self.counters["updates_successful"] = self.counters.get("updates_successful", 0) + 1
        if rollback:
            self.counters["updates_rollback"] = self.counters.get("updates_rollback", 0) + 1

    def record_installation_progress(self, percentage: int, message: str, nesting_depth: int):
        """Record RAUC installation progress updates"""
        self.rauc_events.append({
            "event": "installation_progress",
            "percentage": percentage,
            "message": message,
            "nesting_depth": nesting_depth,
            "timestamp": time.time()
        })

    def record_slot_status(self, slot_info: Dict[str, Any]):
        """Record current slot status information"""
        self.slots_info = {
            "slots": slot_info,
            "timestamp": time.time()
        }

    def record_verification_latency(self, ms: float, method="rauc_signature"):
        """Record bundle verification timing"""
        self.security.append({
            "verification_method": method,
            "latency_ms": ms,
            "timestamp": time.time()
        })

    def record_bundle_info(self, bundle_path: str, bundle_size: int, bundle_info: Dict):
        """Record bundle metadata and size"""
        self.rauc_events.append({
            "event": "bundle_info",
            "bundle_path": bundle_path,
            "bundle_size": bundle_size,
            "bundle_info": bundle_info,
            "timestamp": time.time()
        })

    def record_bandwidth(self, bytes_used: int, duration_sec: float):
        """Record bandwidth usage for bundle transfer"""
        bandwidth_bps = bytes_used / duration_sec if duration_sec > 0 else 0
        self.events.append({
            "event": "bandwidth",
            "bytes_used": bytes_used,
            "duration_sec": duration_sec,
            "bandwidth_bps": bandwidth_bps,
            "timestamp": time.time()
        })

    def record_storage_overhead(self, extra_bytes: int):
        """Record additional storage used during update"""
        self.events.append({
            "event": "storage_overhead",
            "extra_bytes": extra_bytes,
            "timestamp": time.time()
        })

    def record_resources(self):
        """Take a snapshot of system resources"""
        try:
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            self.resources.append({
                "timestamp": time.time(),
                "cpu_pct": psutil.cpu_percent(interval=None),
                "mem_mb": vm.used / 1e6,
                "mem_available_mb": vm.available / 1e6,
                "disk_used_gb": disk.used / 1e9,
                "disk_free_gb": disk.free / 1e9,
                "load_avg": os.getloadavg() if hasattr(os, 'getloadavg') else None
            })
        except Exception as e:
            logging.warning(f"Failed to record system resources: {e}")

    # ---- ML-specific (if using RAUC for AI/ML model updates) ----
    def record_model_metrics(self, model_id: str, deploy_time: float, 
                           inference_latency: Optional[float] = None, 
                           accuracy_delta: Optional[float] = None, 
                           wer: Optional[float] = None):
        """Record ML model deployment metrics"""
        self.ml_metrics.append({
            "model_id": model_id,
            "deploy_time_sec": deploy_time,
            "inference_latency_ms": inference_latency,
            "accuracy_delta": accuracy_delta,
            "wer": wer,
            "timestamp": time.time()
        })

    # ---- Export & persistence ----
    def export(self) -> Dict[str, Any]:
        """Export all metrics to dictionary"""
        return {
            "events": self.events,
            "counters": self.counters,
            "resources": self.resources,
            "security": self.security,
            "ml_metrics": self.ml_metrics,
            "rauc_events": self.rauc_events,
            "slots_info": self.slots_info,
            "system": self.system,
        }

    def save(self, filename: str = METRICS_FILE):
        """Save metrics to JSON file (accumulative)"""
        data = {}
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                data = {}

        # Merge counters
        for k, v in self.counters.items():
            data.setdefault("counters", {})
            data["counters"][k] = data["counters"].get(k, 0) + v

        # Append lists
        for field in ["events", "resources", "security", "ml_metrics", "rauc_events"]:
            data.setdefault(field, [])
            data[field].extend(getattr(self, field))

        # Update latest info
        data.setdefault("system", {}).update(self.system)
        if self.slots_info:
            data["latest_slots_info"] = self.slots_info

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"RAUC metrics saved to {filename}")


class RAUCClient:
    """RAUC D-Bus client with metrics collection"""

    def __init__(self, metrics: RAUCMetrics):
        self.metrics = metrics
        self.bus = None
        self.rauc_proxy = None
        self.loop = None
        self.installation_in_progress = False

    def connect(self) -> bool:
        """Connect to RAUC D-Bus service"""
        if not DBUS_AVAILABLE:
            print("Error: D-Bus libraries not available")
            return False

        try:
            self.metrics.start("rauc_connect")

            # Set up D-Bus main loop
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
            self.loop = GLib.MainLoop()

            # Connect to system bus
            self.bus = dbus.SystemBus()

            # Get RAUC service proxy
            self.rauc_proxy = self.bus.get_object(RAUC_SERVICE_NAME, RAUC_OBJECT_PATH)

            # Test connection by getting slot status
            installer = dbus.Interface(self.rauc_proxy, RAUC_INSTALLER_INTERFACE)
            slot_status = installer.GetSlotStatus()
            self.metrics.record_slot_status(dict(slot_status))

            # Connect to progress signals
            self.bus.add_signal_receiver(
                self._on_properties_changed,
                dbus_interface="org.freedesktop.DBus.Properties",
                signal_name="PropertiesChanged",
                path=RAUC_OBJECT_PATH
            )

            # Connect to completion signal  
            self.bus.add_signal_receiver(
                self._on_installation_completed,
                dbus_interface=RAUC_INSTALLER_INTERFACE,
                signal_name="Completed",
                path=RAUC_OBJECT_PATH
            )

            self.metrics.stop("rauc_connect")
            self.metrics.record_success("rauc_connect")
            print("Connected to RAUC service")
            return True

        except Exception as e:
            self.metrics.stop("rauc_connect")
            self.metrics.record_error("rauc_connect")
            print(f"Failed to connect to RAUC: {e}")
            return False

    def get_system_info(self) -> Dict[str, Any]:
        """Get RAUC system information"""
        try:
            self.metrics.start("get_system_info")

            installer = dbus.Interface(self.rauc_proxy, RAUC_INSTALLER_INTERFACE)

            # Get slot status
            slot_status = dict(installer.GetSlotStatus())

            # Get primary slot
            try:
                primary = installer.GetPrimary()
            except:
                primary = "unknown"

            # Get last error
            try:
                properties = dbus.Interface(self.rauc_proxy, "org.freedesktop.DBus.Properties")
                last_error = properties.Get(RAUC_INSTALLER_INTERFACE, "LastError")
            except:
                last_error = ""

            system_info = {
                "slot_status": slot_status,
                "primary_slot": primary,
                "last_error": str(last_error),
                "timestamp": time.time()
            }

            self.metrics.record_slot_status(slot_status)
            self.metrics.stop("get_system_info")
            self.metrics.record_success("get_system_info")

            return system_info

        except Exception as e:
            self.metrics.stop("get_system_info")
            self.metrics.record_error("get_system_info")
            print(f"Failed to get system info: {e}")
            return {}

    def inspect_bundle(self, bundle_path: str) -> Dict[str, Any]:
        """Inspect a RAUC bundle"""
        try:
            self.metrics.start("inspect_bundle")

            installer = dbus.Interface(self.rauc_proxy, RAUC_INSTALLER_INTERFACE)

            # Inspect bundle (RAUC 1.9+)
            try:
                bundle_info = dict(installer.InspectBundle(bundle_path, {}))
            except:
                # Fallback for older RAUC versions
                bundle_info = {"error": "InspectBundle not available"}

            # Get bundle file size if it's a local file
            bundle_size = 0
            if os.path.isfile(bundle_path):
                bundle_size = os.path.getsize(bundle_path)

            self.metrics.record_bundle_info(bundle_path, bundle_size, bundle_info)
            self.metrics.stop("inspect_bundle")
            self.metrics.record_success("inspect_bundle")

            return bundle_info

        except Exception as e:
            self.metrics.stop("inspect_bundle")
            self.metrics.record_error("inspect_bundle") 
            print(f"Failed to inspect bundle: {e}")
            return {}

    def install_bundle(self, bundle_path: str) -> bool:
        """Install a RAUC bundle with progress monitoring"""
        try:
            self.metrics.start("install_bundle")

            # Record system resources before installation
            self.metrics.record_resources()

            installer = dbus.Interface(self.rauc_proxy, RAUC_INSTALLER_INTERFACE)

            # Start installation
            self.installation_in_progress = True
            installer.InstallBundle(bundle_path, {})

            print(f"Installation of {bundle_path} started...")
            print("Monitoring progress... (Press Ctrl+C to stop monitoring)")

            # Run main loop to receive progress signals
            try:
                self.loop.run()
            except KeyboardInterrupt:
                print("\nMonitoring stopped by user")

            self.metrics.stop("install_bundle")

            # Record final system resources
            self.metrics.record_resources()

            return not self.installation_in_progress  # False if still in progress

        except Exception as e:
            self.metrics.stop("install_bundle")
            self.metrics.record_error("install_bundle")
            self.metrics.record_update_attempt(bundle_path, False)
            print(f"Failed to install bundle: {e}")
            return False

    def _on_properties_changed(self, interface, changed_props, invalidated_props):
        """Handle D-Bus properties changed signal for progress monitoring"""
        if interface == RAUC_INSTALLER_INTERFACE and "Progress" in changed_props:
            progress = changed_props["Progress"]
            if len(progress) >= 3:
                percentage = int(progress[0])
                message = str(progress[1])
                nesting_depth = int(progress[2])

                # Record progress
                self.metrics.record_installation_progress(percentage, message, nesting_depth)

                # Display progress
                indent = "  " * nesting_depth
                print(f"{indent}[{percentage}%] {message}")

                # Record resources periodically
                if percentage % 20 == 0:
                    self.metrics.record_resources()

    def _on_installation_completed(self, result):
        """Handle installation completed signal"""
        success = (result == 0)

        if success:
            print("\n✓ Installation completed successfully!")
            self.metrics.record_success("install_bundle")
        else:
            print(f"\n✗ Installation failed with code: {result}")
            self.metrics.record_error("install_bundle")

        self.installation_in_progress = False
        self.loop.quit()

    def mark_slot(self, state: str, slot_name: str = "booted") -> bool:
        """Mark a slot with given state (good/bad/active)"""
        try:
            self.metrics.start(f"mark_slot_{state}")

            installer = dbus.Interface(self.rauc_proxy, RAUC_INSTALLER_INTERFACE)
            installer.Mark(state, slot_name)

            self.metrics.stop(f"mark_slot_{state}")
            self.metrics.record_success(f"mark_slot_{state}")
            print(f"Marked slot {slot_name} as {state}")
            return True

        except Exception as e:
            self.metrics.stop(f"mark_slot_{state}")
            self.metrics.record_error(f"mark_slot_{state}")
            print(f"Failed to mark slot: {e}")
            return False


def main():
    """Main RAUC OTA client with metrics"""
    parser = argparse.ArgumentParser(description="RAUC OTA Client with Metrics")
    parser.add_argument(
        "-v", "--verbose",
        help="Output verbosity level (-v, -vv, ...)",
        action="count",
        default=0,
    )
    parser.add_argument(
        "--metrics-file",
        help="Metrics output file",
        default=METRICS_FILE,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Status command
    status_parser = subparsers.add_parser("status", help="Get system status")
    status_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Inspect command
    inspect_parser = subparsers.add_parser("inspect", help="Inspect bundle")
    inspect_parser.add_argument("bundle", help="Bundle file path")
    inspect_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # Install command
    install_parser = subparsers.add_parser("install", help="Install bundle")
    install_parser.add_argument("bundle", help="Bundle file path")

    # Mark command
    mark_parser = subparsers.add_parser("mark", help="Mark slot")
    mark_parser.add_argument("state", choices=["good", "bad", "active"], help="Slot state")
    mark_parser.add_argument("slot", nargs="?", default="booted", help="Slot name")

    args = parser.parse_args()

    # Set up logging
    if args.verbose == 0:
        loglevel = logging.ERROR
    elif args.verbose == 1:
        loglevel = logging.WARNING
    elif args.verbose == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)

    # Initialize metrics
    metrics = RAUCMetrics()

    # Record system info
    metrics.system = {
        "platform": sys.platform,
        "python_version": sys.version,
        "pid": os.getpid(),
        "start_time": time.time(),
        "command": " ".join(sys.argv),
    }

    # Initialize RAUC client
    client = RAUCClient(metrics)

    # Connect to RAUC
    if not client.connect():
        metrics.save(args.metrics_file)
        return 1

    try:
        result = 0

        if args.command == "status":
            info = client.get_system_info()
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print("=== RAUC System Status ===")
                print(f"Primary slot: {info.get('primary_slot', 'unknown')}")
                if info.get('last_error'):
                    print(f"Last error: {info['last_error']}")
                print("\nSlot Status:")
                for slot, data in info.get('slot_status', {}).items():
                    print(f"  {slot}: {dict(data)}")

        elif args.command == "inspect":
            info = client.inspect_bundle(args.bundle)
            if args.json:
                print(json.dumps(info, indent=2))
            else:
                print(f"=== Bundle Info: {args.bundle} ===")
                for key, value in info.items():
                    print(f"{key}: {value}")

        elif args.command == "install":
            if not os.path.exists(args.bundle):
                print(f"Error: Bundle file not found: {args.bundle}")
                result = 1
            else:
                success = client.install_bundle(args.bundle)
                metrics.record_update_attempt(args.bundle, success)
                if not success:
                    result = 1

        elif args.command == "mark":
            success = client.mark_slot(args.state, args.slot)
            if not success:
                result = 1

        else:
            parser.print_help()
            result = 1

    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        result = 1
    except Exception as e:
        print(f"Error: {e}")
        if args.verbose > 2:
            traceback.print_exc()
        result = 1
    finally:
        # Always record final resources and save metrics
        metrics.record_resources()
        metrics.save(args.metrics_file)

    return result


if __name__ == "__main__":
    sys.exit(main())
