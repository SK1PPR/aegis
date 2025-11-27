#!/usr/bin/env python3
"""
SWUpdate OTA Metrics Collection System
Extended from TUF Client Example with SWUpdate-specific metrics
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import threading
from datetime import datetime
from pathlib import Path
import psutil
import socket
import struct
from enum import IntEnum

# SWUpdate IPC constants (from network_ipc.h)
class IPCMessage(IntEnum):
    REQ_INSTALL = 0
    ACK = 1
    NACK = 2
    GET_STATUS = 3
    POST_UPDATE = 4

class RecoveryStatus(IntEnum):
    IDLE = 0
    START = 1
    RUN = 2
    SUCCESS = 3
    FAILURE = 4
    DOWNLOAD = 5
    DONE = 6

class SourceType(IntEnum):
    SOURCE_UNKNOWN = 0
    SOURCE_WEBSERVER = 1
    SOURCE_SURICATTA = 2
    SOURCE_DOWNLOADER = 3
    SOURCE_LOCAL = 4

# Configuration
SWUPDATE_SOCKET = "/tmp/sockinstctrl"
PROGRESS_SOCKET = "/tmp/swupdateprog"
METRICS_FILE = "swupdate_metrics.json"

class SWUpdateMetrics:
    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []
        self.security = []
        self.update_stats = []
        self.handler_metrics = []
        self.progress_data = []
        self.system = {}
        self.session_id = int(time.time())
        
    def start_timer(self, label):
        """Start timing for a specific operation"""
        self.timings[label] = time.time()
        
    def stop_timer(self, label):
        """Stop timing and record duration"""
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({
                "metric": label,
                "duration_sec": duration,
                "timestamp": time.time(),
                "session_id": self.session_id
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1
            
    def record_swupdate_progress(self, step, total_steps, step_name, percentage):
        """Record SWUpdate progress information"""
        self.progress_data.append({
            "step": step,
            "total_steps": total_steps,
            "step_name": step_name,
            "percentage": percentage,
            "timestamp": time.time(),
            "session_id": self.session_id
        })
        
    def record_handler_metrics(self, handler_type, execution_time, bytes_processed, success):
        """Record handler-specific metrics"""
        self.handler_metrics.append({
            "handler_type": handler_type,
            "execution_time_sec": execution_time,
            "bytes_processed": bytes_processed,
            "success": success,
            "timestamp": time.time(),
            "session_id": self.session_id
        })
        
    def record_security_event(self, event_type, status, duration_ms=None, method=None):
        """Record security-related events"""
        event = {
            "event_type": event_type,
            "status": status,
            "timestamp": time.time(),
            "session_id": self.session_id
        }
        if duration_ms:
            event["duration_ms"] = duration_ms
        if method:
            event["method"] = method
        self.security.append(event)
        
    def record_update_attempt(self, update_file, source_type, status, error_code=None):
        """Record update attempt with comprehensive information"""
        self.update_stats.append({
            "update_file": update_file,
            "source_type": source_type,
            "status": status,
            "error_code": error_code,
            "timestamp": time.time(),
            "session_id": self.session_id
        })
        
        # Update counters
        self.counters["updates_attempted"] = self.counters.get("updates_attempted", 0) + 1
        if status == RecoveryStatus.SUCCESS:
            self.counters["updates_successful"] = self.counters.get("updates_successful", 0) + 1
        elif status == RecoveryStatus.FAILURE:
            self.counters["updates_failed"] = self.counters.get("updates_failed", 0) + 1
            
    def record_system_resources(self):
        """Record current system resource usage"""
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        self.resources.append({
            "timestamp": time.time(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "memory_mb": vm.used / 1024 / 1024,
            "memory_percent": vm.percent,
            "disk_used_gb": disk.used / 1024 / 1024 / 1024,
            "disk_percent": (disk.used / disk.total) * 100,
            "session_id": self.session_id
        })
        
    def export_metrics(self):
        """Export all collected metrics"""
        return {
            "session_id": self.session_id,
            "export_timestamp": time.time(),
            "events": self.events,
            "counters": self.counters,
            "resources": self.resources,
            "security": self.security,
            "update_stats": self.update_stats,
            "handler_metrics": self.handler_metrics,
            "progress_data": self.progress_data,
            "system": self.system
        }
        
    def save_metrics(self, filename=METRICS_FILE):
        """Save metrics to file"""
        metrics_data = self.export_metrics()
        
        # Load existing data if file exists
        existing_data = {"sessions": []}
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                existing_data = {"sessions": []}
                
        # Append new session data
        existing_data["sessions"].append(metrics_data)
        
        # # Keep only last 10 sessions to prevent file from growing too large
        # if len(existing_data["sessions"]) > 10:
        #     existing_data["sessions"] = existing_data["sessions"][-10:]
            
        with open(filename, 'w') as f:
            json.dump(existing_data, f, indent=2)
        print(f"Metrics saved to {filename}")

class SWUpdateClient:
    """SWUpdate client with comprehensive metrics collection"""
    
    def __init__(self):
        self.metrics = SWUpdateMetrics()
        
    def update_from_file(self, swu_file, dry_run=False):
        """Perform update from SWU file with metrics collection"""
        if not os.path.exists(swu_file):
            print(f"SWU file not found: {swu_file}")
            return False
            
        print(f"Starting SWUpdate from file: {swu_file}")
        
        # Record system state before update
        self.metrics.record_system_resources()
        self.metrics.start_timer("total_update_time")
        
        try:
            # Build SWUpdate command
            cmd = ["swupdate", "-k", "public.pem"]
            cmd.extend(["-i", swu_file])
            
            if dry_run:
                cmd.append("-n")
                
            # Add verbose logging
            cmd.extend(["-v", "-L"])  # verbose + syslog
            
            # Record update attempt
            self.metrics.record_update_attempt(
                update_file=swu_file,
                source_type=SourceType.SOURCE_LOCAL,
                status=RecoveryStatus.START
            )
            
            # Execute SWUpdate
            self.metrics.start_timer("swupdate_execution")
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            self.metrics.stop_timer("swupdate_execution")
            
            # Analyze results
            success = result.returncode == 0
            
            if success:
                print("SWUpdate completed successfully")
                self.metrics.record_update_attempt(
                    update_file=swu_file,
                    source_type=SourceType.SOURCE_LOCAL,
                    status=RecoveryStatus.SUCCESS
                )
            else:
                print(f"SWUpdate failed with return code {result.returncode}")
                print(f"Error output: {result.stderr}")
                self.metrics.record_update_attempt(
                    update_file=swu_file,
                    source_type=SourceType.SOURCE_LOCAL,
                    status=RecoveryStatus.FAILURE,
                    error_code=result.returncode
                )
                
            return success
            
        except subprocess.TimeoutExpired:
            print("SWUpdate timed out")
            return False
            
        except Exception as e:
            print(f"Error executing SWUpdate: {e}")
            return False
            
        finally:
            self.metrics.stop_timer("total_update_time")
            self.metrics.record_system_resources()
    
    def create_sample_swu(self, output_file="test-update.swu"):
        """Create a sample SWU file for testing"""
        print(f"Creating sample SWU file: {output_file}")
        
        # Create sw-description content
        sw_description_content = """software =
{
    version = "1.0.0";
    description = "Test update for metrics collection";
    
    hardware-compatibility: [ "test-board:1.0" ];
    
    test-board = {
        stable = {
            files: (
                {
                    filename = "test-file.txt";
                    path = "/tmp/test-file.txt";
                    type = "rawfile";
                    sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
                }
            );
        };
    };
}"""
        
        # Create temporary files
        temp_dir = "/tmp/swu_creation"
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            with open(f"{temp_dir}/sw-description", 'w') as f:
                f.write(sw_description_content)
                
            with open(f"{temp_dir}/test-file.txt", 'w') as f:
                f.write("Test file content for SWUpdate metrics")
                
            print(f"Sample SWU components created in {temp_dir}")
            return f"{temp_dir}/sw-description"
            
        except Exception as e:
            print(f"Error creating sample SWU: {e}")
            return None
            
    def run_metrics_test(self):
        """Run a comprehensive metrics test"""
        print("SWUpdate Metrics Test")
        print("=" * 40)
        
        # Simulate update process with metrics
        self.metrics.start_timer("test_simulation")
        
        # Simulate various metrics
        self.metrics.record_security_event("signature_check", "success", 150, "RSA2048")
        self.metrics.record_handler_metrics("raw", 2.5, 1024*1024, True)
        self.metrics.record_swupdate_progress(1, 3, "parsing", 33)
        self.metrics.record_swupdate_progress(2, 3, "installing", 66)
        self.metrics.record_swupdate_progress(3, 3, "finalizing", 100)
        
        time.sleep(1)  # Simulate work
        
        self.metrics.stop_timer("test_simulation")
        self.metrics.record_system_resources()
        
        # Save and display results
        self.metrics.save_metrics()
        self._print_metrics_summary()
        
        return True
        
    def _print_metrics_summary(self):
        """Print metrics summary"""
        print("\nMetrics Summary:")
        print("=" * 30)
        print(f"Session ID: {self.metrics.session_id}")
        print(f"Events: {len(self.metrics.events)}")
        print(f"Progress Updates: {len(self.metrics.progress_data)}")
        print(f"Security Events: {len(self.metrics.security)}")
        print(f"Handler Metrics: {len(self.metrics.handler_metrics)}")
        
        for key, value in self.metrics.counters.items():
            print(f"{key}: {value}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="SWUpdate OTA Metrics")
    parser.add_argument("-i", "--input", help="SWU file to install")
    parser.add_argument("-n", "--dry-run", action="store_true", help="Dry run")
    parser.add_argument("-t", "--test", action="store_true", help="Run test")
    parser.add_argument("-c", "--create", help="Create sample SWU")
    
    args = parser.parse_args()
    
    client = SWUpdateClient()
    
    if args.test:
        return 0 if client.run_metrics_test() else 1
    elif args.create:
        return 0 if client.create_sample_swu(args.create) else 1
    elif args.input:
        success = client.update_from_file(args.input, args.dry_run)
        client.metrics.save_metrics()
        return 0 if success else 1
    else:
        parser.print_help()
        return 1

if __name__ == "__main__":
    sys.exit(main())
