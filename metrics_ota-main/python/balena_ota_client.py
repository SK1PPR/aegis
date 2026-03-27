#!/usr/bin/env python3
"""Extended TUF Client with Open Balena OTA Metrics"""
# Extends the original TUF client with Balena-specific OTA update metrics

import argparse
import logging
import os
import sys
import traceback
import time
import json
import subprocess
import requests
import docker
from hashlib import sha256
from pathlib import Path
from datetime import datetime, timezone

import urllib3
import psutil   # for resource snapshots

from tuf.api.exceptions import DownloadError, RepositoryError
from tuf.ngclient import Updater

# constants
DOWNLOAD_DIR = "./downloads"
CLIENT_EXAMPLE_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_FILE = "balena_ota_metrics.json"
BALENA_CONFIG_FILE = "balena_config.json"

class BalenaOTAMetrics:
    """Extended metrics collector for Balena OTA updates with TUF integration"""
    
    def __init__(self):
        # Original TUF metrics
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []     # system resource snapshots
        self.security = []      # verification/auth checks
        self.ml_metrics = []    # model-related metrics
        self.system = {}        # static metadata
        
        # Balena-specific metrics
        self.balena_metrics = {
            "container_operations": [],
            "fleet_sync_events": [],
            "supervisor_stats": [],
            "registry_operations": [],
            "device_connectivity": [],
            "service_health": [],
            "deployment_pipeline": []
        }
        
        # Initialize Docker client for container metrics
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"Warning: Docker client not available: {e}")
            self.docker_client = None
    
    # ---- Original TUF metrics methods ----
    def start(self, label):
        self.timings[label] = time.time()

    def stop(self, label):
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({
                "metric": label, 
                "duration_sec": duration, 
                "timestamp": time.time()
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1

    def record_success(self, label):
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1

    def record_error(self, label):
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1

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

    def record_resources(self):
        vm = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=None)
        self.resources.append({
            "timestamp": time.time(),
            "cpu_pct": cpu_percent,
            "mem_mb": vm.used / 1e6,
            "mem_total_mb": vm.total / 1e6,
            "mem_available_mb": vm.available / 1e6
        })

    # ---- Balena-specific metrics methods ----
    def record_balena_push_start(self, fleet_name, source_dir):
        """Record start of balena push operation"""
        self.start("balena_push")
        self.balena_metrics["deployment_pipeline"].append({
            "event": "push_started",
            "fleet": fleet_name,
            "source_dir": source_dir,
            "timestamp": time.time()
        })

    def record_balena_push_complete(self, fleet_name, release_hash, success=True):
        """Record completion of balena push operation"""
        self.stop("balena_push")
        self.balena_metrics["deployment_pipeline"].append({
            "event": "push_completed",
            "fleet": fleet_name,
            "release_hash": release_hash,
            "success": success,
            "timestamp": time.time()
        })
        if success:
            self.record_success("balena_push")
        else:
            self.record_error("balena_push")

    def record_container_pull(self, image_name, pull_time_sec, size_bytes):
        """Record container image pull metrics"""
        self.balena_metrics["container_operations"].append({
            "operation": "pull",
            "image": image_name,
            "pull_time_sec": pull_time_sec,
            "size_bytes": size_bytes,
            "timestamp": time.time()
        })

    def record_container_startup(self, container_name, startup_time_sec, success=True):
        """Record container startup metrics"""
        self.balena_metrics["container_operations"].append({
            "operation": "startup",
            "container": container_name,
            "startup_time_sec": startup_time_sec,
            "success": success,
            "timestamp": time.time()
        })

    def record_fleet_sync_status(self, fleet_name, devices_online, devices_total, sync_status):
        """Record fleet synchronization status"""
        self.balena_metrics["fleet_sync_events"].append({
            "fleet": fleet_name,
            "devices_online": devices_online,
            "devices_total": devices_total,
            "sync_status": sync_status,
            "timestamp": time.time()
        })

    def record_supervisor_metrics(self, device_uuid, cpu_usage, memory_mb, temperature_c=None):
        """Record balena supervisor device metrics"""
        metrics_entry = {
            "device_uuid": device_uuid,
            "cpu_usage_pct": cpu_usage,
            "memory_mb": memory_mb,
            "timestamp": time.time()
        }
        if temperature_c:
            metrics_entry["temperature_c"] = temperature_c
            
        self.balena_metrics["supervisor_stats"].append(metrics_entry)

    def record_registry_push(self, image_tag, push_time_sec, size_bytes):
        """Record container registry push operation"""
        self.balena_metrics["registry_operations"].append({
            "operation": "push",
            "image_tag": image_tag,
            "push_time_sec": push_time_sec,
            "size_bytes": size_bytes,
            "timestamp": time.time()
        })

    def record_device_connectivity(self, device_uuid, connection_status, signal_strength=None):
        """Record device connectivity metrics"""
        entry = {
            "device_uuid": device_uuid,
            "status": connection_status,
            "timestamp": time.time()
        }
        if signal_strength:
            entry["signal_strength"] = signal_strength
            
        self.balena_metrics["device_connectivity"].append(entry)

    def record_service_health_check(self, service_name, status, response_time_ms=None):
        """Record service health check results"""
        health_entry = {
            "service": service_name,
            "status": status,
            "timestamp": time.time()
        }
        if response_time_ms:
            health_entry["response_time_ms"] = response_time_ms
            
        self.balena_metrics["service_health"].append(health_entry)

    def get_docker_container_stats(self, container_name):
        """Collect Docker container statistics"""
        if not self.docker_client:
            return None
            
        try:
            container = self.docker_client.containers.get(container_name)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * len(stats['cpu_stats']['cpu_usage']['percpu_usage']) * 100
            
            # Memory usage
            memory_usage = stats['memory_stats']['usage']
            memory_limit = stats['memory_stats']['limit']
            
            return {
                "cpu_percent": cpu_percent,
                "memory_usage_mb": memory_usage / 1e6,
                "memory_limit_mb": memory_limit / 1e6,
                "memory_percent": (memory_usage / memory_limit) * 100 if memory_limit > 0 else 0
            }
        except Exception as e:
            print(f"Error getting container stats: {e}")
            return None

    # ---- Export and persistence methods ----
    def export(self):
        """Export all metrics including Balena-specific ones"""
        return {
            "tuf_metrics": {
                "events": self.events,
                "counters": self.counters,
                "resources": self.resources,
                "security": self.security,
                "ml_metrics": self.ml_metrics,
                "system": self.system,
            },
            "balena_metrics": self.balena_metrics,
            "export_timestamp": time.time(),
            "export_datetime": datetime.now(timezone.utc).isoformat()
        }

    def save(self, filename=METRICS_FILE):
        """Save metrics to file with merge capability"""
        data = {}
        if os.path.exists(filename):
            with open(filename, "r") as f:
                try:
                    data = json.load(f)
                except json.JSONDecodeError:
                    data = {}

        # Get current export
        current_data = self.export()
        
        # Merge TUF counters
        if "tuf_metrics" not in data:
            data["tuf_metrics"] = {"counters": {}, "events": [], "resources": [], "security": [], "ml_metrics": []}
            
        for k, v in current_data["tuf_metrics"]["counters"].items():
            data["tuf_metrics"]["counters"][k] = data["tuf_metrics"]["counters"].get(k, 0) + v

        # Append TUF events
        for field in ["events", "resources", "security", "ml_metrics"]:
            data["tuf_metrics"][field].extend(current_data["tuf_metrics"][field])

        # Merge Balena metrics
        if "balena_metrics" not in data:
            data["balena_metrics"] = {key: [] for key in self.balena_metrics.keys()}
            
        for key, values in current_data["balena_metrics"].items():
            data["balena_metrics"][key].extend(values)

        # Update system info and timestamps
        data["tuf_metrics"]["system"] = current_data["tuf_metrics"]["system"]
        data["last_update"] = current_data["export_datetime"]

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Metrics saved to {filename}")

    def print_summary(self):
        """Print a summary of collected metrics"""
        print("\n" + "="*50)
        print("BALENA OTA METRICS SUMMARY")
        print("="*50)
        
        print("\nTUF Metrics:")
        print(f"  Total events: {len(self.events)}")
        print(f"  Counters: {len(self.counters)}")
        print(f"  Resource snapshots: {len(self.resources)}")
        print(f"  Security events: {len(self.security)}")
        
        print("\nBalena Metrics:")
        for category, events in self.balena_metrics.items():
            print(f"  {category}: {len(events)} events")
        
        if self.counters:
            print("\nKey Counters:")
            for key, value in self.counters.items():
                print(f"  {key}: {value}")
        
        print("="*50 + "\n")

# Global metrics instance
metrics = BalenaOTAMetrics()

class BalenaOTAManager:
    """Manages Balena OTA update operations with metrics collection"""
    
    def __init__(self, config_file=BALENA_CONFIG_FILE):
        self.config = self.load_config(config_file)
        self.api_url = self.config.get("api_url", "https://api.balena-cloud.com")
        self.auth_token = self.config.get("auth_token", "")
        
    def load_config(self, config_file):
        """Load Balena configuration"""
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                return json.load(f)
        else:
            # Create default config
            default_config = {
                "api_url": "https://api.your-balena-instance.com",
                "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MzYzMTIyLCJleHAiOjE3NTY0OTA5OTIsImp3dF9zZWNyZXQiOiJENk00VUNONEdQSTdJTFNRQlBXNVpQQUNJNlEzSDVMSyIsImF1dGhUaW1lIjoxNzU2MzYxMzkyOTQ0LCJ0d29GYWN0b3JSZXF1aXJlZCI6ZmFsc2UsImlhdCI6MTc1NjM2ODU5NH0.1tokC1gFG0Om1FFxUqmOJxNr7Bm0_4CRjW5nj0iTxYo",
                "fleet_name": "my-ota-test",
                "device_type": "raspberrypi4-64"
            }
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default config at {config_file}. Please update with your settings.")
            return default_config
    
    def balena_push(self, source_dir, fleet_name=None):
        """Execute balena push with metrics collection"""
        fleet_name = fleet_name or self.config.get("fleet_name", "my-fleet")
        
        print(f"Starting balena push to fleet '{fleet_name}'...")
        metrics.record_balena_push_start(fleet_name, source_dir)
        
        try:
            # Execute balena push command
            cmd = ["balena", "push", fleet_name, "--source", source_dir, "--noparent-check", "--debug"]
            print(f"Running: {' '.join(cmd)}")
            
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            push_duration = time.time() - start_time
            
            if result.returncode == 0:
                # Extract release hash from output (simplified)
                release_hash = "unknown"
                for line in result.stdout.split('\n'):
                    if "Release:" in line:
                        release_hash = line.split(":")[-1].strip()
                        break
                
                metrics.record_balena_push_complete(fleet_name, release_hash, success=True)
                print(f"✓ Push completed successfully in {push_duration:.2f}s")
                print(f"Release hash: {release_hash}")
                return True
            else:
                metrics.record_balena_push_complete(fleet_name, "failed", success=False)
                print(f"✗ Push failed after {push_duration:.2f}s")
                print(f"Error: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            metrics.record_balena_push_complete(fleet_name, "timeout", success=False)
            print("✗ Push timed out")
            return False
        except Exception as e:
            metrics.record_balena_push_complete(fleet_name, "error", success=False)
            print(f"✗ Push error: {e}")
            return False
    
    def check_fleet_status(self, fleet_name=None):
        """Check fleet status and record metrics"""
        fleet_name = fleet_name or self.config.get("fleet_name", "my-fleet")
        
        try:
            # This would normally use balena CLI or API
            cmd = ["balena", "devices", "--fleet", fleet_name, "--json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                devices = json.loads(result.stdout)
                online_count = sum(1 for d in devices if d.get("is_online"))
                total_count = len(devices)
                
                sync_status = "healthy" if online_count == total_count else "degraded"
                metrics.record_fleet_sync_status(fleet_name, online_count, total_count, sync_status)
                
                print(f"Fleet '{fleet_name}': {online_count}/{total_count} devices online")
                
                # Record individual device metrics
                for device in devices:
                    if device.get("is_online"):
                        uuid = device.get("uuid", "unknown")
                        cpu = device.get("cpu_usage", 0)
                        memory = device.get("memory_usage", 0)
                        temp = device.get("cpu_temp")
                        
                        metrics.record_supervisor_metrics(uuid, cpu, memory, temp)
                        metrics.record_device_connectivity(uuid, "online")
                
                return True
            else:
                print(f"Failed to get fleet status: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error checking fleet status: {e}")
            return False

# TUF integration functions (simplified versions of original)
def build_metadata_dir(base_url: str) -> str:
    name = sha256(base_url.encode()).hexdigest()[:8]
    return f"{Path.home()}/.local/share/tuf-example/{name}"

def init_tofu(base_url: str) -> bool:
    """Initialize local trusted metadata (Trust-On-First-Use)"""
    metrics.start("init_tofu")
    t0 = time.time()
    
    try:
        metadata_dir = build_metadata_dir(base_url)
        response = urllib3.request("GET", f"{base_url}/metadata/1.root.json")
        
        verify_time_ms = (time.time() - t0) * 1000
        metrics.record_verification_latency(verify_time_ms, method="bootstrap_http")
        
        if response.status != 200:
            print(f"Failed to download initial root {base_url}/metadata/1.root.json")
            metrics.record_error("init_tofu")
            metrics.stop("init_tofu")
            return False
            
        # Initialize TUF updater
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
        
    except Exception as e:
        print(f"TOFU initialization failed: {e}")
        metrics.record_error("init_tofu")
        metrics.stop("init_tofu")
        return False

def main():
    """Main function with integrated Balena OTA and TUF metrics"""
    parser = argparse.ArgumentParser(description="Balena OTA Update Client with Metrics")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                       help="Output verbosity level (-v, -vv, ...)")
    parser.add_argument("--config", default=BALENA_CONFIG_FILE,
                       help="Balena configuration file path")
    
    subparsers = parser.add_subparsers(dest="command")
    
    # TUF commands
    subparsers.add_parser("tofu", help="Initialize TUF Trust-On-First-Use")
    download_parser = subparsers.add_parser("download", help="Download TUF target")
    download_parser.add_argument("target", help="Target file to download")
    
    # Balena commands
    push_parser = subparsers.add_parser("push", help="Push to Balena fleet")
    push_parser.add_argument("source", help="Source directory to push")
    push_parser.add_argument("--fleet", help="Fleet name to push to")

    subparsers.add_parser("status", help="Check fleet status")
    status_parser = subparsers.add_parser("status", help="Check fleet status")
    status_parser.add_argument("--fleet", help="Fleet name to check status for")
    subparsers.add_parser("summary", help="Print metrics summary")
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose == 0:
        loglevel = logging.ERROR
    elif args.verbose == 1:
        loglevel = logging.WARNING
    elif args.verbose == 2:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG
    logging.basicConfig(level=loglevel)
    
    balena_manager = BalenaOTAManager(args.config)
    
    # Record system information
    metrics.system.update({
        "start_time": time.time(),
        "command": args.command,
        "config_file": args.config
    })
    
    try:
        if args.command == "tofu":
            base_url = "http://127.0.0.1:8001"  # Default TUF server
            success = init_tofu(base_url)
            if not success:
                return 1
                
        elif args.command == "download":
            # TUF download implementation would go here
            print(f"Would download TUF target: {args.target}")
            metrics.record_update_attempt(args.target, True)
            
        elif args.command == "push":
            success = balena_manager.balena_push(args.source, args.fleet)
            if not success:
                return 1
                
        elif args.command == "status":
            success = balena_manager.check_fleet_status(args.fleet)
            if not success:
                return 1
                
        elif args.command == "summary":
            metrics.print_summary()
            
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"Command failed: {e}")
        if args.verbose >= 2:
            traceback.print_exc()
        return 1
    finally:
        # Always collect final resource snapshot and save metrics
        metrics.record_resources()
        metrics.save()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
