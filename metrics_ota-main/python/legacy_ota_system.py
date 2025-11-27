#!/usr/bin/env python3
"""
Legacy OTA Update System with Comprehensive Metrics Collection
Demonstrates basic legacy OTA update method with detailed performance tracking
"""

import os
import json
import time
import hashlib
import psutil
import urllib.request
import random
import tempfile
import shutil
import socket
import threading
import zipfile
from pathlib import Path
from typing import Dict, List, Optional

# Constants
DOWNLOAD_DIR = "./legacy_downloads"
FIRMWARE_DIR = "./firmware"
BACKUP_DIR = "./backup"
METRICS_FILE = "legacy_ota_metrics.json"
TEMP_DIR = "./temp"

class ComprehensiveMetrics:
    """Enhanced metrics collector for legacy OTA updates"""
    
    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []     # system resource snapshots
        self.security = []      # verification/auth checks
        self.ml_metrics = []    # model-related metrics (if applicable)
        self.system = {}        # static metadata
        self.network_metrics = []
        self.storage_metrics = []
        
        # Initialize system info
        self.system = {
            "os": os.name,
            "cpu_count": psutil.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "platform": "legacy_ota_system",
            "start_time": time.time()
        }
    
    # ---- Basic timing methods ----
    def start_timer(self, label: str):
        """Start timing for a specific operation"""
        self.timings[label] = time.time()
    
    def stop_timer(self, label: str) -> float:
        """Stop timing and record duration"""
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({
                "metric": label,
                "duration_sec": duration,
                "timestamp": time.time(),
                "type": "timing"
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1
            return duration
        return 0.0
    
    def record_success(self, label: str):
        """Record a successful operation"""
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1
    
    def record_error(self, label: str, error_type: str = "unknown"):
        """Record a failed operation with error type"""
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1
        self.events.append({
            "event": "error",
            "operation": label,
            "error_type": error_type,
            "timestamp": time.time()
        })
    
    # ---- OTA-specific metrics ----
    def record_update_attempt(self, update_id: str, success: bool, rollback: bool = False,
                            firmware_size: Optional[int] = None, delta_size: Optional[int] = None):
        """Record OTA update attempt with comprehensive details"""
        self.events.append({
            "event": "update_attempt",
            "update_id": update_id,
            "success": success,
            "rollback": rollback,
            "firmware_size": firmware_size,
            "delta_size": delta_size,
            "timestamp": time.time()
        })
        self.counters["updates_attempted"] = self.counters.get("updates_attempted", 0) + 1
        if success:
            self.counters["updates_successful"] = self.counters.get("updates_successful", 0) + 1
        if rollback:
            self.counters["updates_rollback"] = self.counters.get("updates_rollback", 0) + 1
    
    def record_verification_latency(self, ms: float, method: str = "sha256"):
        """Record security verification timing"""
        self.security.append({
            "verification_method": method,
            "latency_ms": ms,
            "timestamp": time.time()
        })
    
    def record_bandwidth_usage(self, bytes_used: int, operation: str, 
                              delta_bytes: Optional[int] = None, full_bytes: Optional[int] = None):
        """Record bandwidth consumption for different operations"""
        event = {
            "event": "bandwidth",
            "bytes_used": bytes_used,
            "operation": operation,
            "timestamp": time.time()
        }
        if delta_bytes and full_bytes:
            event["delta_ratio"] = delta_bytes / full_bytes
        self.events.append(event)
    
    def record_storage_overhead(self, extra_bytes: int, operation: str):
        """Record storage overhead for operations"""
        self.storage_metrics.append({
            "event": "storage_overhead",
            "extra_bytes": extra_bytes,
            "operation": operation,
            "timestamp": time.time()
        })
    
    def record_resource_snapshot(self, operation: str = "general"):
        """Take a snapshot of current system resources"""
        try:
            vm = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            # Network I/O
            net_io = psutil.net_io_counters()
            
            # Disk I/O
            disk_io = psutil.disk_io_counters()
            
            snapshot = {
                "timestamp": time.time(),
                "operation": operation,
                "cpu_percent": cpu_percent,
                "memory_used_mb": vm.used / 1e6,
                "memory_available_mb": vm.available / 1e6,
                "memory_percent": vm.percent,
                "swap_used_mb": psutil.swap_memory().used / 1e6,
                "network_bytes_sent": net_io.bytes_sent if net_io else 0,
                "network_bytes_recv": net_io.bytes_recv if net_io else 0,
                "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
                "disk_write_bytes": disk_io.write_bytes if disk_io else 0
            }
            
            self.resources.append(snapshot)
            
        except Exception as e:
            self.record_error("resource_snapshot", str(e))
    
    def record_network_performance(self, download_speed_mbps: float, latency_ms: float, 
                                  connection_type: str = "unknown"):
        """Record network performance metrics"""
        self.network_metrics.append({
            "download_speed_mbps": download_speed_mbps,
            "latency_ms": latency_ms,
            "connection_type": connection_type,
            "timestamp": time.time()
        })
    
    # ---- ML-specific metrics (for AI-powered OTA systems) ----
    def record_model_metrics(self, model_id: str, deploy_time: float, 
                           inference_latency: float, accuracy_delta: Optional[float] = None,
                           wer: Optional[float] = None):
        """Record machine learning model deployment metrics"""
        self.ml_metrics.append({
            "model_id": model_id,
            "deploy_time_sec": deploy_time,
            "inference_latency_ms": inference_latency,
            "accuracy_delta": accuracy_delta,
            "wer": wer,
            "timestamp": time.time()
        })
    
    # ---- Export and persistence ----
    def export_metrics(self) -> Dict:
        """Export all collected metrics"""
        return {
            "events": self.events,
            "counters": self.counters,
            "resources": self.resources,
            "security": self.security,
            "ml_metrics": self.ml_metrics,
            "network_metrics": self.network_metrics,
            "storage_metrics": self.storage_metrics,
            "system": self.system,
            "collection_duration": time.time() - self.system.get("start_time", time.time())
        }
    
    def save_metrics(self, filename: str = METRICS_FILE):
        """Save metrics to JSON file with aggregation"""
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
        
        # Append time-series data
        for field in ["events", "resources", "security", "ml_metrics", "network_metrics", "storage_metrics"]:
            data.setdefault(field, [])
            data[field].extend(getattr(self, field))
        
        # Update system info
        data.setdefault("system", {}).update(self.system)
        
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        
        print(f"Metrics saved to {filename}")

class LegacyOTAUpdater:
    """
    Legacy OTA Update System - Simulates traditional update methods
    
    Characteristics of Legacy OTA:
    - Single partition updates (no A/B system)
    - Full firmware download and flash
    - Basic security (simple checksums)
    - Limited rollback capabilities
    - Blocking updates (device unavailable during update)
    """
    
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url
        self.metrics = ComprehensiveMetrics()
        self.current_firmware_version = "1.0.0"
        self.ensure_directories()
    
    def ensure_directories(self):
        """Create necessary directories"""
        for directory in [DOWNLOAD_DIR, FIRMWARE_DIR, BACKUP_DIR, TEMP_DIR]:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def simulate_server_check(self) -> Optional[Dict]:
        """
        Simulate checking update server for available updates
        In real legacy systems, this would be an HTTP/HTTPS request
        """
        self.metrics.start_timer("server_check")
        self.metrics.record_resource_snapshot("server_check")
        
        try:
            # Simulate network latency
            time.sleep(random.uniform(0.5, 2.0))
            
            # Simulate network performance measurement
            latency = random.uniform(50, 200)  # ms
            download_speed = random.uniform(5, 50)  # Mbps
            self.metrics.record_network_performance(download_speed, latency, "wifi")
            
            # Mock update information
            update_info = {
                "version": "1.1.0",
                "size": random.randint(50000, 500000),  # bytes
                "checksum": hashlib.md5(f"firmware_1.1.0_{time.time()}".encode()).hexdigest(),
                "url": f"{self.base_url}/firmware/v1.1.0.bin",
                "changelog": "Bug fixes and security improvements",
                "critical": False,
                "rollback_supported": True
            }
            
            self.metrics.stop_timer("server_check")
            self.metrics.record_success("server_check")
            return update_info
            
        except Exception as e:
            self.metrics.stop_timer("server_check")
            self.metrics.record_error("server_check", str(e))
            return None
    
    def download_firmware(self, update_info: Dict) -> Optional[str]:
        """
        Download firmware update - Legacy method downloads entire firmware
        """
        self.metrics.start_timer("firmware_download")
        
        try:
            firmware_size = update_info["size"]
            firmware_path = os.path.join(DOWNLOAD_DIR, f"firmware_{update_info['version']}.bin")
            
            # Simulate progressive download with bandwidth recording
            downloaded = 0
            chunk_size = 8192
            download_start = time.time()
            
            # Create dummy firmware file
            with open(firmware_path, 'wb') as f:
                while downloaded < firmware_size:
                    chunk_size_actual = min(chunk_size, firmware_size - downloaded)
                    chunk_data = os.urandom(chunk_size_actual)
                    f.write(chunk_data)
                    downloaded += chunk_size_actual
                    
                    # Simulate network delay
                    time.sleep(0.001)  # Small delay to simulate real download
                    
                    # Record resource usage periodically
                    if downloaded % (chunk_size * 10) == 0:
                        self.metrics.record_resource_snapshot("download_progress")
            
            download_time = time.time() - download_start
            download_speed_mbps = (firmware_size * 8) / (download_time * 1e6)  # Convert to Mbps
            
            self.metrics.record_bandwidth_usage(firmware_size, "firmware_download")
            self.metrics.record_network_performance(download_speed_mbps, 0, "download")
            
            self.metrics.stop_timer("firmware_download")
            self.metrics.record_success("firmware_download")
            
            print(f"Downloaded firmware: {firmware_path} ({firmware_size} bytes in {download_time:.2f}s)")
            return firmware_path
            
        except Exception as e:
            self.metrics.stop_timer("firmware_download")
            self.metrics.record_error("firmware_download", str(e))
            return None
    
    def verify_firmware(self, firmware_path: str, expected_checksum: str) -> bool:
        """
        Verify firmware integrity - Legacy method uses simple checksums
        """
        self.metrics.start_timer("firmware_verification")
        verify_start = time.time()
        
        try:
            # Calculate checksum
            hasher = hashlib.md5()
            with open(firmware_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            calculated_checksum = hasher.hexdigest()
            verify_time_ms = (time.time() - verify_start) * 1000
            
            self.metrics.record_verification_latency(verify_time_ms, "md5_checksum")
            
            is_valid = calculated_checksum == expected_checksum
            
            if is_valid:
                self.metrics.record_success("firmware_verification")
            else:
                self.metrics.record_error("firmware_verification", "checksum_mismatch")
            
            self.metrics.stop_timer("firmware_verification")
            return is_valid
            
        except Exception as e:
            self.metrics.stop_timer("firmware_verification")
            self.metrics.record_error("firmware_verification", str(e))
            return False
    
    def backup_current_firmware(self) -> bool:
        """
        Backup current firmware - Legacy systems have limited backup
        """
        self.metrics.start_timer("firmware_backup")
        
        try:
            current_firmware_path = os.path.join(FIRMWARE_DIR, f"current_{self.current_firmware_version}.bin")
            backup_path = os.path.join(BACKUP_DIR, f"backup_{self.current_firmware_version}_{int(time.time())}.bin")
            
            # Create dummy current firmware if not exists
            if not os.path.exists(current_firmware_path):
                with open(current_firmware_path, 'wb') as f:
                    f.write(os.urandom(random.randint(30000, 100000)))
            
            # Copy to backup location
            shutil.copy2(current_firmware_path, backup_path)
            
            backup_size = os.path.getsize(backup_path)
            self.metrics.record_storage_overhead(backup_size, "firmware_backup")
            
            self.metrics.stop_timer("firmware_backup")
            self.metrics.record_success("firmware_backup")
            return True
            
        except Exception as e:
            self.metrics.stop_timer("firmware_backup")
            self.metrics.record_error("firmware_backup", str(e))
            return False
    
    def flash_firmware(self, firmware_path: str, update_info: Dict) -> bool:
        """
        Flash new firmware - Legacy method involves full system replacement
        This is the most critical and risky part of legacy OTA
        """
        self.metrics.start_timer("firmware_flash")
        flash_start = time.time()
        
        try:
            firmware_size = os.path.getsize(firmware_path)
            target_path = os.path.join(FIRMWARE_DIR, f"current_{update_info['version']}.bin")
            
            # Simulate the dangerous flashing process
            print("WARNING: Legacy flashing in progress - device vulnerable to power loss!")
            
            # Record high resource usage during flash
            self.metrics.record_resource_snapshot("flash_start")
            
            # Simulate flash process with multiple steps
            flash_steps = [
                ("erase_flash", 2.0),
                ("write_bootloader", 1.5),
                ("write_firmware", 3.0),
                ("verify_flash", 1.0)
            ]
            
            for step, duration in flash_steps:
                print(f"Executing: {step}")
                time.sleep(duration)  # Simulate time-consuming operation
                self.metrics.record_resource_snapshot(f"flash_{step}")
            
            # Copy firmware to target location
            shutil.copy2(firmware_path, target_path)
            
            # Update version
            self.current_firmware_version = update_info["version"]
            
            flash_time = time.time() - flash_start
            
            # Record flash metrics
            self.metrics.events.append({
                "event": "firmware_flash_complete",
                "flash_time_sec": flash_time,
                "firmware_size": firmware_size,
                "version": update_info["version"],
                "timestamp": time.time()
            })
            
            self.metrics.stop_timer("firmware_flash")
            self.metrics.record_success("firmware_flash")
            return True
            
        except Exception as e:
            self.metrics.stop_timer("firmware_flash")
            self.metrics.record_error("firmware_flash", str(e))
            return False
    
    def post_update_validation(self, update_info: Dict) -> bool:
        """
        Validate system after update - Limited in legacy systems
        """
        self.metrics.start_timer("post_update_validation")
        
        try:
            # Simulate basic system checks
            checks = [
                ("boot_sequence", True),
                ("system_services", True),
                ("hardware_compatibility", True),
                ("network_connectivity", random.choice([True, False]))  # Sometimes fails
            ]
            
            all_passed = True
            for check_name, result in checks:
                if result:
                    self.metrics.record_success(f"validation_{check_name}")
                else:
                    self.metrics.record_error(f"validation_{check_name}", "check_failed")
                    all_passed = False
                
                time.sleep(0.5)  # Simulate check time
            
            self.metrics.stop_timer("post_update_validation")
            
            if all_passed:
                self.metrics.record_success("post_update_validation")
            else:
                self.metrics.record_error("post_update_validation", "validation_failed")
            
            return all_passed
            
        except Exception as e:
            self.metrics.stop_timer("post_update_validation")
            self.metrics.record_error("post_update_validation", str(e))
            return False
    
    def rollback_firmware(self, reason: str = "validation_failed") -> bool:
        """
        Rollback to previous firmware - Limited capability in legacy systems
        """
        self.metrics.start_timer("firmware_rollback")
        
        try:
            # Find most recent backup
            backup_files = list(Path(BACKUP_DIR).glob("backup_*.bin"))
            if not backup_files:
                self.metrics.record_error("firmware_rollback", "no_backup_available")
                self.metrics.stop_timer("firmware_rollback")
                return False
            
            latest_backup = max(backup_files, key=os.path.getctime)
            
            # Extract version from backup filename
            backup_version = latest_backup.stem.split('_')[1]
            
            # Simulate rollback flash process (also risky in legacy systems)
            print(f"Rolling back to version {backup_version}")
            time.sleep(3.0)  # Simulate rollback flash time
            
            # Update current version
            self.current_firmware_version = backup_version
            
            self.metrics.events.append({
                "event": "firmware_rollback_complete",
                "reason": reason,
                "rollback_to_version": backup_version,
                "timestamp": time.time()
            })
            
            self.metrics.stop_timer("firmware_rollback")
            self.metrics.record_success("firmware_rollback")
            return True
            
        except Exception as e:
            self.metrics.stop_timer("firmware_rollback")
            self.metrics.record_error("firmware_rollback", str(e))
            return False
    
    def perform_legacy_ota_update(self) -> bool:
        """
        Execute complete legacy OTA update process
        """
        print("=" * 60)
        print("LEGACY OTA UPDATE PROCESS STARTING")
        print("=" * 60)
        
        update_id = f"legacy_update_{int(time.time())}"
        self.metrics.start_timer("complete_ota_update")
        overall_start = time.time()
        
        try:
            # Step 1: Check for updates
            print("\n1. Checking for updates...")
            update_info = self.simulate_server_check()
            if not update_info:
                print("No updates available or server unreachable")
                self.metrics.record_update_attempt(update_id, False)
                return False
            
            print(f"Update available: {update_info['version']} ({update_info['size']} bytes)")
            
            # Step 2: Download firmware (entire firmware in legacy)
            print("\n2. Downloading firmware...")
            firmware_path = self.download_firmware(update_info)
            if not firmware_path:
                print("Download failed")
                self.metrics.record_update_attempt(update_id, False)
                return False
            
            # Step 3: Verify firmware
            print("\n3. Verifying firmware integrity...")
            if not self.verify_firmware(firmware_path, update_info["checksum"]):
                print("Firmware verification failed")
                self.metrics.record_update_attempt(update_id, False)
                return False
            
            # Step 4: Backup current firmware (limited in legacy)
            print("\n4. Backing up current firmware...")
            if not self.backup_current_firmware():
                print("WARNING: Backup failed - proceeding anyway (risky!)")
            
            # Step 5: Flash new firmware (CRITICAL - device vulnerable)
            print("\n5. Flashing new firmware...")
            if not self.flash_firmware(firmware_path, update_info):
                print("Firmware flashing failed")
                self.metrics.record_update_attempt(update_id, False)
                return False
            
            # Step 6: Post-update validation
            print("\n6. Validating updated system...")
            if not self.post_update_validation(update_info):
                print("Post-update validation failed - initiating rollback...")
                if self.rollback_firmware("validation_failed"):
                    print("Rollback successful")
                    self.metrics.record_update_attempt(update_id, False, rollback=True, 
                                                     firmware_size=update_info["size"])
                else:
                    print("CRITICAL: Rollback also failed - device may be bricked!")
                    self.metrics.record_update_attempt(update_id, False, rollback=False,
                                                     firmware_size=update_info["size"])
                return False
            
            # Success!
            total_time = time.time() - overall_start
            print(f"\n✓ Legacy OTA Update completed successfully in {total_time:.2f} seconds")
            print(f"✓ Updated from {self.current_firmware_version} to {update_info['version']}")
            
            self.metrics.record_update_attempt(update_id, True, rollback=False,
                                             firmware_size=update_info["size"])
            self.metrics.stop_timer("complete_ota_update")
            return True
            
        except Exception as e:
            print(f"\nFATAL ERROR during OTA update: {e}")
            self.metrics.record_error("complete_ota_update", str(e))
            self.metrics.record_update_attempt(update_id, False)
            
            # Attempt emergency rollback
            print("Attempting emergency rollback...")
            self.rollback_firmware("fatal_error")
            
            self.metrics.stop_timer("complete_ota_update")
            return False
        
        finally:
            # Always record final resource state
            self.metrics.record_resource_snapshot("ota_complete")
            self.metrics.save_metrics()

def simulate_multiple_ota_updates(count: int = 1000):
    """
    Simulate multiple OTA updates to collect comprehensive metrics
    """
    print("\n" + "=" * 80)
    print(f"RUNNING {count} LEGACY OTA UPDATE SIMULATIONS")
    print("=" * 80)
    
    updater = LegacyOTAUpdater()
    results = []
    
    for i in range(count):
        print(f"\n{'='*20} UPDATE SIMULATION {i+1}/{count} {'='*20}")
        
        # Record initial state
        updater.metrics.record_resource_snapshot(f"simulation_{i+1}_start")
        
        # Perform update
        success = updater.perform_legacy_ota_update()
        results.append(success)
        
        # Record final state  
        updater.metrics.record_resource_snapshot(f"simulation_{i+1}_end")
        
        # Wait between updates
        if i < count - 1:
            print("\nWaiting before next simulation...")
            time.sleep(2)
    
    # Print summary
    print("\n" + "=" * 80)
    print("SIMULATION SUMMARY")
    print("=" * 80)
    successful = sum(results)
    print(f"Total simulations: {count}")
    print(f"Successful updates: {successful}")
    print(f"Failed updates: {count - successful}")
    print(f"Success rate: {(successful/count)*100:.1f}%")
    
    # Export final metrics
    metrics_data = updater.metrics.export_metrics()
    
    print("\nMETRICS SUMMARY:")
    print(f"- Total events recorded: {len(metrics_data['events'])}")
    print(f"- Resource snapshots: {len(metrics_data['resources'])}")
    print(f"- Security operations: {len(metrics_data['security'])}")
    print(f"- Network measurements: {len(metrics_data['network_metrics'])}")
    print(f"- Storage operations: {len(metrics_data['storage_metrics'])}")
    
    return results, metrics_data

if __name__ == "__main__":
    # Run comprehensive legacy OTA simulation
    results, metrics = simulate_multiple_ota_updates(1000)
    print(f"\nLegacy OTA simulation complete. Metrics saved to {METRICS_FILE}")
