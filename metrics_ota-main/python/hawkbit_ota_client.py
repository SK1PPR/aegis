#!/usr/bin/env python3
"""HawkBit OTA Client - SUPER FIXED VERSION with robust download handling"""

import argparse
import logging
import os
import sys
import traceback
import time
import json
import requests
import hashlib
from pathlib import Path
import psutil   # for resource snapshots
from typing import Optional, Dict, List, Any
import threading
from urllib.parse import urljoin, urlparse

# Constants
DOWNLOAD_DIR = "./downloads"
METRICS_FILE = "hawkbit_ota_metrics.json"
DEFAULT_HAWKBIT_URL = "http://localhost:8080"
DEFAULT_TENANT = "DEFAULT"
DEFAULT_CONTROLLER_ID = "device-001"

class HawkBitMetrics:
    """Extended metrics collector for HawkBit OTA operations"""

    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []     # system resource snapshots
        self.security = []      # verification/auth checks
        self.ota_metrics = []   # OTA-specific metrics
        self.network_metrics = []  # network performance metrics
        self.system = {}        # static metadata
        self.errors = []        # error tracking
        self._start_time = time.time()

        # Initialize system info
        self.system = {
            "client_start_time": self._start_time,
            "python_version": sys.version,
            "platform": os.name,
            "cpu_count": psutil.cpu_count(),
            "total_memory_mb": psutil.virtual_memory().total / 1e6,
        }

    # ---- Basic timing ----
    def start(self, label):
        """Start timing for a labeled operation"""
        self.timings[label] = time.time()

    def stop(self, label):
        """Stop timing and record duration for a labeled operation"""
        if label in self.timings:
            duration = time.time() - self.timings[label]
            self.events.append({
                "metric": label, 
                "duration_sec": duration, 
                "timestamp": time.time()
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1
            del self.timings[label]

    def record_success(self, label):
        """Record successful operation"""
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1

    def record_error(self, label, error_msg=None):
        """Record failed operation"""
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1
        if error_msg:
            self.errors.append({
                "operation": label,
                "error": str(error_msg),
                "timestamp": time.time()
            })

    # ---- OTA-specific metrics ----
    def record_update_attempt(self, action_id, deployment_type, success, rollback=False):
        """Record OTA update attempt"""
        self.ota_metrics.append({
            "event": "update_attempt",
            "action_id": action_id,
            "deployment_type": deployment_type,
            "success": success,
            "rollback": rollback,
            "timestamp": time.time()
        })
        self.counters["updates_attempted"] = self.counters.get("updates_attempted", 0) + 1
        if success:
            self.counters["updates_successful"] = self.counters.get("updates_successful", 0) + 1
        if rollback:
            self.counters["updates_rollback"] = self.counters.get("updates_rollback", 0) + 1

    def record_polling_cycle(self, has_update, response_time_ms):
        """Record polling cycle metrics"""
        self.events.append({
            "event": "polling_cycle",
            "has_update": has_update,
            "response_time_ms": response_time_ms,
            "timestamp": time.time()
        })
        self.counters["polling_cycles"] = self.counters.get("polling_cycles", 0) + 1
        if has_update:
            self.counters["polling_cycles_with_update"] = self.counters.get("polling_cycles_with_update", 0) + 1

    def record_download_metrics(self, artifact_name, size_bytes, download_time_sec, checksum_verified=True):
        """Record download performance metrics"""
        bandwidth_mbps = (size_bytes * 8) / (download_time_sec * 1000000) if download_time_sec > 0 else 0
        self.network_metrics.append({
            "event": "artifact_download",
            "artifact_name": artifact_name,
            "size_bytes": size_bytes,
            "download_time_sec": download_time_sec,
            "bandwidth_mbps": bandwidth_mbps,
            "checksum_verified": checksum_verified,
            "timestamp": time.time()
        })

    def record_verification_latency(self, ms, method="hawkbit_signature"):
        """Record verification latency"""
        self.security.append({
            "verification_method": method,
            "latency_ms": ms,
            "timestamp": time.time()
        })

    def record_bandwidth(self, bytes_used, operation_type="download"):
        """Record bandwidth usage"""
        self.network_metrics.append({
            "event": "bandwidth_usage",
            "operation_type": operation_type,
            "bytes_used": bytes_used,
            "timestamp": time.time()
        })

    def record_storage_overhead(self, extra_bytes, reason="cache"):
        """Record storage overhead"""
        self.events.append({
            "event": "storage_overhead",
            "extra_bytes": extra_bytes,
            "reason": reason,
            "timestamp": time.time()
        })

    def record_resources(self):
        """Record current system resource usage"""
        try:
            vm = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            self.resources.append({
                "timestamp": time.time(),
                "cpu_percent": psutil.cpu_percent(interval=None),
                "memory_used_mb": vm.used / 1e6,
                "memory_percent": vm.percent,
                "disk_free_mb": disk.free / 1e6,
                "disk_percent": (disk.used / disk.total) * 100
            })
        except Exception as e:
            print(f"Warning: Could not record resource usage: {e}")

    def record_network_latency(self, target_url, latency_ms):
        """Record network latency to HawkBit server"""
        self.network_metrics.append({
            "event": "network_latency",
            "target_url": target_url,
            "latency_ms": latency_ms,
            "timestamp": time.time()
        })

    def record_deployment_feedback(self, action_id, execution_status, result_status):
        """Record deployment feedback sent to HawkBit"""
        self.ota_metrics.append({
            "event": "deployment_feedback",
            "action_id": action_id,
            "execution_status": execution_status,
            "result_status": result_status,
            "timestamp": time.time()
        })

    # ---- Export & persistence ----
    def export(self):
        """Export all metrics data"""
        uptime_sec = time.time() - self._start_time
        return {
            "session_info": {
                "uptime_sec": uptime_sec,
                "total_events": len(self.events),
                "total_errors": len(self.errors)
            },
            "events": self.events,
            "counters": self.counters,
            "resources": self.resources,
            "security": self.security,
            "ota_metrics": self.ota_metrics,
            "network_metrics": self.network_metrics,
            "system": self.system,
            "errors": self.errors
        }

    def save(self, filename=METRICS_FILE):
        """Save metrics to file"""
        try:
            data = {}
            if os.path.exists(filename):
                try:
                    with open(filename, "r") as f:
                        data = json.load(f)
                except json.JSONDecodeError:
                    data = {}

            # Merge counters
            data.setdefault("counters", {})
            for k, v in self.counters.items():
                data["counters"][k] = data["counters"].get(k, 0) + v

            # Append event lists
            for field in ["events", "resources", "security", "ota_metrics", "network_metrics", "errors"]:
                data.setdefault(field, [])
                data[field].extend(getattr(self, field))

            # Update system info
            data.setdefault("system", {}).update(self.system)

            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"📊 Metrics saved to {filename}")
        except Exception as e:
            print(f"⚠️  Warning: Could not save metrics: {e}")


class HawkBitClient:
    """HawkBit DDI API Client with comprehensive metrics - SUPER ROBUST VERSION"""

    def __init__(self, base_url, tenant_id, controller_id, auth_token=None, metrics=None):
        self.base_url = base_url.rstrip('/')
        self.tenant_id = tenant_id
        self.controller_id = controller_id
        self.auth_token = auth_token
        self.metrics = metrics or HawkBitMetrics()

        # Build base DDI URL
        self.ddi_base_url = f"{self.base_url}/{self.tenant_id}/controller/v1/{self.controller_id}"

        # Setup session
        self.session = requests.Session()
        if self.auth_token:
            self.session.headers.update({
                'Authorization': f'TargetToken {self.auth_token}'
            })

        self.session.headers.update({
            'Accept': 'application/hal+json,application/json',
            'User-Agent': 'HawkBit-Python-Client/2.0'
        })

        # Create download directory
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)

    def _make_request(self, method, url, **kwargs):
        """Make HTTP request with metrics tracking"""
        start_time = time.time()
        try:
            response = self.session.request(method, url, **kwargs)
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_network_latency(url, latency_ms)

            if response.status_code >= 400:
                self.metrics.record_error(f"{method.lower()}_request", f"HTTP {response.status_code}")
            else:
                self.metrics.record_success(f"{method.lower()}_request")

            return response
        except Exception as e:
            self.metrics.record_error(f"{method.lower()}_request", str(e))
            raise

    def get_controller_info(self):
        """Get controller information from HawkBit"""
        self.metrics.start("get_controller_info")
        try:
            response = self._make_request('GET', self.ddi_base_url)
            response.raise_for_status()

            data = response.json()
            self.metrics.record_success("get_controller_info")
            return data
        except Exception as e:
            self.metrics.record_error("get_controller_info", str(e))
            raise
        finally:
            self.metrics.stop("get_controller_info")

    def check_for_deployment(self):
        """Check for available deployments"""
        self.metrics.start("check_deployment")
        try:
            controller_info = self.get_controller_info()

            # Check if deploymentBase link exists
            deployment_link = controller_info.get('_links', {}).get('deploymentBase')
            has_deployment = deployment_link is not None

            response_time_ms = (time.time() - self.metrics.timings.get("check_deployment", time.time())) * 1000
            self.metrics.record_polling_cycle(has_deployment, response_time_ms)

            if has_deployment:
                deployment_url = deployment_link['href']
                deployment_response = self._make_request('GET', deployment_url)
                deployment_response.raise_for_status()
                deployment_data = deployment_response.json()

                self.metrics.record_success("check_deployment")
                return deployment_data

            return None
        except Exception as e:
            self.metrics.record_error("check_deployment", str(e))
            raise
        finally:
            self.metrics.stop("check_deployment")

    def find_download_url(self, artifact_info):
        """Robustly find download URL for artifact"""
        artifact_name = artifact_info.get('filename', 'unknown_artifact')

        # Method 1: Check _links.download
        download_links = artifact_info.get('_links', {})
        if 'download' in download_links:
            download_url = download_links['download']['href']
            print(f"   📡 Found download link in _links: {download_url}")
            return download_url

        # Method 2: Check for download-http link
        if 'download-http' in download_links:
            download_url = download_links['download-http']['href']
            print(f"   📡 Found download-http link: {download_url}")
            return download_url

        # Method 3: Try to construct URL from artifact info
        if 'id' in artifact_info:
            artifact_id = artifact_info['id']
            # Try common HawkBit artifact download URL patterns
            possible_urls = [
                f"{self.base_url}/rest/v1/softwaremodules/{artifact_info.get('softwareModuleId', 'unknown')}/artifacts/{artifact_id}/download",
                f"{self.base_url}/api/v1/downloadserver/downloadId/{artifact_id}",
                f"{self.base_url}/DEFAULT/controller/v1/{self.controller_id}/softwaremodules/{artifact_info.get('softwareModuleId', 'unknown')}/artifacts/{artifact_id}/download"
            ]

            for url in possible_urls:
                try:
                    # Test if URL is accessible
                    test_response = self._make_request('HEAD', url)
                    if test_response.status_code < 400:
                        print(f"   📡 Constructed working download URL: {url}")
                        return url
                except:
                    continue

        # Method 4: Debug - show what we actually have
        print(f"   🔍 DEBUG: Artifact info for {artifact_name}:")
        print(f"   Raw artifact data: {json.dumps(artifact_info, indent=2)}")

        raise ValueError(f"Could not find any working download URL for artifact {artifact_name}")

    def download_artifact(self, artifact_info):
        """Download artifact with robust URL handling"""
        artifact_name = artifact_info.get('filename', 'unknown_artifact')
        expected_size = artifact_info.get('size', 0)
        expected_hashes = artifact_info.get('hashes', {})

        print(f"📥 Starting download of {artifact_name}...")

        # Find download URL using multiple methods
        try:
            download_url = self.find_download_url(artifact_info)
        except Exception as e:
            self.metrics.record_error(f"download_{artifact_name}", str(e))
            raise

        # Convert relative URL to absolute URL if needed
        if download_url.startswith('/'):
            download_url = f"{self.base_url}{download_url}"
        elif not download_url.startswith('http'):
            download_url = f"{self.base_url}/{download_url}"

        print(f"   🔗 Download URL: {download_url}")

        self.metrics.start(f"download_{artifact_name}")

        try:
            download_start = time.time()
            response = self._make_request('GET', download_url, stream=True)
            response.raise_for_status()

            # Download with progress tracking
            file_path = os.path.join(DOWNLOAD_DIR, artifact_name)
            downloaded_bytes = 0

            print(f"   💾 Saving to: {file_path}")

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_bytes += len(chunk)

                        # Show progress for larger files
                        if downloaded_bytes % (100 * 1024) == 0:  # Every 100KB
                            print(f"   📊 Downloaded: {downloaded_bytes:,} bytes")

            download_time = time.time() - download_start

            # Verify checksum if provided
            checksum_verified = True
            if expected_hashes:
                print(f"   🔐 Verifying checksum...")
                for hash_type, expected_hash in expected_hashes.items():
                    if hash_type.lower() in ['md5', 'sha1', 'sha256']:
                        checksum_verified = self._verify_checksum(file_path, hash_type.lower(), expected_hash)
                        if checksum_verified:
                            print(f"   ✅ {hash_type.upper()} checksum verified")
                        else:
                            print(f"   ❌ {hash_type.upper()} checksum mismatch")
                        break

            # Record metrics
            self.metrics.record_download_metrics(
                artifact_name, downloaded_bytes, download_time, checksum_verified
            )
            self.metrics.record_bandwidth(downloaded_bytes, "artifact_download")

            if expected_size > 0 and downloaded_bytes != expected_size:
                print(f"   ⚠️  Size mismatch for {artifact_name}: expected {expected_size:,}, got {downloaded_bytes:,}")

            self.metrics.record_success(f"download_{artifact_name}")
            print(f"   ✅ Successfully downloaded {artifact_name} ({downloaded_bytes:,} bytes in {download_time:.2f}s)")
            return file_path

        except Exception as e:
            self.metrics.record_error(f"download_{artifact_name}", str(e))
            print(f"   ❌ Download failed: {e}")
            raise
        finally:
            self.metrics.stop(f"download_{artifact_name}")

    def _verify_checksum(self, file_path, hash_type, expected_hash):
        """Verify file checksum"""
        verify_start = time.time()

        try:
            if hash_type == 'md5':
                hasher = hashlib.md5()
            elif hash_type == 'sha1':
                hasher = hashlib.sha1()
            elif hash_type == 'sha256':
                hasher = hashlib.sha256()
            else:
                return False

            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)

            computed_hash = hasher.hexdigest()
            verify_time_ms = (time.time() - verify_start) * 1000
            self.metrics.record_verification_latency(verify_time_ms, f"{hash_type}_checksum")

            verified = computed_hash.lower() == expected_hash.lower()
            if not verified:
                print(f"   🔍 Expected: {expected_hash}")
                print(f"   🔍 Computed: {computed_hash}")

            return verified
        except Exception as e:
            print(f"   ❌ Checksum verification failed: {e}")
            return False

    def send_deployment_feedback(self, action_id, execution_status, result_status, details=None):
        """Send deployment feedback to HawkBit"""
        self.metrics.start("send_feedback")

        try:
            feedback_url = f"{self.ddi_base_url}/deploymentBase/{action_id}/feedback"

            feedback_data = {
                "id": action_id,
                "status": {
                    "execution": execution_status,  # closed, proceeding, canceled, scheduled, rejected, resumed
                    "result": {
                        "finished": result_status   # success, failure, none
                    }
                }
            }

            if details:
                feedback_data["status"]["details"] = details

            response = self._make_request('POST', feedback_url, json=feedback_data,
                                        headers={'Content-Type': 'application/json'})
            response.raise_for_status()

            self.metrics.record_deployment_feedback(action_id, execution_status, result_status)
            self.metrics.record_success("send_feedback")
            print(f"   📤 Feedback sent: {execution_status}/{result_status}")

        except Exception as e:
            self.metrics.record_error("send_feedback", str(e))
            print(f"   ⚠️  Failed to send feedback: {e}")
            # Don't re-raise feedback errors - they're not critical
        finally:
            self.metrics.stop("send_feedback")

    def process_deployment(self, deployment_data):
        """Process a deployment from HawkBit"""
        deployment = deployment_data.get('deployment', {})
        action_id = deployment_data.get('id')
        deployment_type = deployment.get('update', 'unknown')

        self.metrics.start(f"process_deployment_{action_id}")

        try:
            print(f"🔄 Processing deployment {action_id} (type: {deployment_type})")

            # Send proceeding feedback
            self.send_deployment_feedback(action_id, "proceeding", "none", 
                                        ["Starting deployment process"])

            # Process chunks (software modules)
            artifacts_downloaded = []
            for chunk in deployment.get('chunks', []):
                chunk_name = chunk.get('name', 'unknown_chunk')
                print(f"📦 Processing chunk: {chunk_name}")

                # Download artifacts in this chunk
                for artifact in chunk.get('artifacts', []):
                    try:
                        file_path = self.download_artifact(artifact)
                        artifacts_downloaded.append(file_path)
                    except Exception as e:
                        print(f"   ❌ Failed to download artifact: {e}")
                        raise

            # Simulate installation process
            print("⚙️  Simulating installation...")
            time.sleep(5)  # Simulate installation time

            # Record successful update
            self.metrics.record_update_attempt(action_id, deployment_type, True, False)

            # Send success feedback
            self.send_deployment_feedback(action_id, "closed", "success", 
                                        [f"Successfully installed {len(artifacts_downloaded)} artifacts"])

            self.metrics.record_success(f"process_deployment_{action_id}")
            print(f"✅ Deployment {action_id} completed successfully!")
            print(f"   📂 Artifacts downloaded: {len(artifacts_downloaded)}")
            for artifact_path in artifacts_downloaded:
                print(f"     • {os.path.basename(artifact_path)}")
            return True

        except Exception as e:
            # Record failed update
            self.metrics.record_update_attempt(action_id, deployment_type, False, False)

            # Send failure feedback
            self.send_deployment_feedback(action_id, "closed", "failure", 
                                        [f"Deployment failed: {str(e)}"])

            self.metrics.record_error(f"process_deployment_{action_id}", str(e))
            print(f"❌ Deployment {action_id} failed: {e}")
            raise
        finally:
            self.metrics.stop(f"process_deployment_{action_id}")

    def polling_loop(self, interval_sec=30, max_iterations=None):
        """Main polling loop for checking updates"""
        print(f"🚀 Starting polling loop")
        print(f"   ⏱️  Interval: {interval_sec} seconds")
        print(f"   🔢 Max iterations: {max_iterations or 'unlimited'}")
        print(f"   🎯 Target: {self.controller_id}")

        iteration = 0
        successful_deployments = 0
        failed_deployments = 0

        try:
            while True:
                if max_iterations and iteration >= max_iterations:
                    print(f"\n🏁 Reached maximum iterations ({max_iterations})")
                    break

                iteration += 1
                print(f"\n[{iteration:4d}] Polling iteration {iteration}")

                # Record system resources periodically
                if iteration % 10 == 1:  # Every 10th iteration
                    self.metrics.record_resources()

                try:
                    # Check for deployment
                    deployment_data = self.check_for_deployment()

                    if deployment_data:
                        print("🚀 Deployment found!")
                        self.process_deployment(deployment_data)
                        successful_deployments += 1
                        print("✅ Deployment processed successfully")
                    else:
                        print("📭 No deployments available")

                except Exception as e:
                    failed_deployments += 1
                    print(f"❌ Error in polling iteration: {e}")
                    if logging.root.level <= logging.DEBUG:
                        traceback.print_exc()

                # Show progress summary every 50 iterations
                if iteration % 50 == 0:
                    print(f"\n📊 Progress Summary (Iteration {iteration}):")
                    print(f"   ✅ Successful deployments: {successful_deployments}")
                    print(f"   ❌ Failed deployments: {failed_deployments}")
                    print(f"   📈 Success rate: {(successful_deployments/(successful_deployments+failed_deployments)*100) if (successful_deployments+failed_deployments) > 0 else 0:.1f}%")

                # Wait for next iteration
                if max_iterations is None or iteration < max_iterations:
                    print(f"⏳ Waiting {interval_sec} seconds...")
                    time.sleep(interval_sec)

        except KeyboardInterrupt:
            print("\n⏹️  Polling stopped by user")
        finally:
            print(f"\n📊 Final Summary:")
            print(f"   🔢 Total iterations: {iteration}")
            print(f"   ✅ Successful deployments: {successful_deployments}")
            print(f"   ❌ Failed deployments: {failed_deployments}")
            print(f"   📈 Overall success rate: {(successful_deployments/(successful_deployments+failed_deployments)*100) if (successful_deployments+failed_deployments) > 0 else 0:.1f}%")


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="HawkBit OTA Client with Metrics - SUPER ROBUST VERSION")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                       help="Increase verbosity (-v, -vv, -vvv)")
    parser.add_argument("-u", "--url", default=DEFAULT_HAWKBIT_URL,
                       help=f"HawkBit server URL (default: {DEFAULT_HAWKBIT_URL})")
    parser.add_argument("-t", "--tenant", default=DEFAULT_TENANT,
                       help=f"Tenant ID (default: {DEFAULT_TENANT})")
    parser.add_argument("-c", "--controller-id", default=DEFAULT_CONTROLLER_ID,
                       help=f"Controller ID (default: {DEFAULT_CONTROLLER_ID})")
    parser.add_argument("-a", "--auth-token",
                       help="Authentication token for target authentication")
    parser.add_argument("-i", "--interval", type=int, default=10,
                       help="Polling interval in seconds (default: 10)")
    parser.add_argument("-m", "--max-iterations", type=int,
                       help="Maximum number of polling iterations (default: unlimited)")
    parser.add_argument("--metrics-file", default=METRICS_FILE,
                       help=f"Metrics output file (default: {METRICS_FILE})")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Poll command
    poll_parser = subparsers.add_parser("poll", help="Start polling for updates")

    # Single check command
    check_parser = subparsers.add_parser("check", help="Check once for updates")

    # Info command
    info_parser = subparsers.add_parser("info", help="Get controller information")

    args = parser.parse_args()

    # Setup logging
    if args.verbose == 0:
        loglevel = logging.WARNING
    elif args.verbose == 1:
        loglevel = logging.INFO
    else:
        loglevel = logging.DEBUG

    logging.basicConfig(level=loglevel, format='%(asctime)s - %(levelname)s - %(message)s')

    # Create metrics collector
    metrics = HawkBitMetrics()

    # Create client
    client = HawkBitClient(
        base_url=args.url,
        tenant_id=args.tenant,
        controller_id=args.controller_id,
        auth_token=args.auth_token,
        metrics=metrics
    )

    try:
        if args.command == "poll":
            client.polling_loop(args.interval, args.max_iterations)
        elif args.command == "check":
            deployment = client.check_for_deployment()
            if deployment:
                print("Deployment available:")
                print(json.dumps(deployment, indent=2))
                # Ask user if they want to process it
                response = input("Process this deployment? (y/N): ")
                if response.lower() == 'y':
                    client.process_deployment(deployment)
            else:
                print("No deployments available")
        elif args.command == "info":
            info = client.get_controller_info()
            print("Controller Information:")
            print(json.dumps(info, indent=2))
        else:
            parser.print_help()
            return 1

    except Exception as e:
        print(f"❌ Fatal Error: {e}")
        if args.verbose >= 2:
            traceback.print_exc()
        return 1

    finally:
        metrics.save(args.metrics_file)
        print(f"\n📊 Session Summary:")
        print(f"   📝 Total events: {len(metrics.events)}")
        print(f"   ❌ Total errors: {len(metrics.errors)}")
        print(f"   🎯 Updates attempted: {metrics.counters.get('updates_attempted', 0)}")
        print(f"   ✅ Updates successful: {metrics.counters.get('updates_successful', 0)}")
        print(f"   📊 Metrics saved to: {args.metrics_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())