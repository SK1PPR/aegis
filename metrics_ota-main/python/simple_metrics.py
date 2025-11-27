# simple_metrics.py
import time, json, os, psutil

class SimpleMetrics:
    def __init__(self):
        self.timings = {}
        self.counters = {}
        self.events = []
        self.resources = []
        self.security = []
        self.ecu_updates = []
        self.manifests = []
        self.comm = []
        self.system = {}  # system-wide info
        self.network = []

    # ---- Timing ----
    def start(self, label):
        self.timings[label] = time.time()

    def stop(self, label):
        if label in self.timings:
            d = time.time() - self.timings[label]
            self.events.append({
                "event": "timing",
                "metric": label,
                "duration_sec": d,
                "timestamp": time.time()
            })
            self.counters[f"{label}_count"] = self.counters.get(f"{label}_count", 0) + 1

    # ---- ECU-specific ----
    def record_ecu_update(self, ecu_id, image, success, rollback=False):
        self.ecu_updates.append({
            "ecu_id": ecu_id,
            "image": image,
            "success": success,
            "rollback": rollback,
            "timestamp": time.time()
        })
        self.counters[f"{ecu_id}_attempts"] = self.counters.get(f"{ecu_id}_attempts", 0) + 1
        if success:
            self.counters[f"{ecu_id}_success"] = self.counters.get(f"{ecu_id}_success", 0) + 1
        if rollback:
            self.counters[f"{ecu_id}_rollback"] = self.counters.get(f"{ecu_id}_rollback", 0) + 1

    # ---- Manifest ----
    def record_manifest(self, ecu_id, size_bytes, latency_ms):
        self.manifests.append({
            "ecu_id": ecu_id,
            "size_bytes": size_bytes,
            "latency_ms": latency_ms,
            "timestamp": time.time()
        })

    # ---- Communication ----
    def record_comm(self, src, dst, latency_ms, bytes_sent):
        self.comm.append({
            "src": src,
            "dst": dst,
            "latency_ms": latency_ms,
            "bytes_sent": bytes_sent,
            "timestamp": time.time()
        })

    def record_network(self, src, dst, latency_ms, bytes_sent):
        self.network.append({
            "src": src,
            "dst": dst,
            "latency_ms": latency_ms,
            "bytes_sent": bytes_sent,
            "timestamp": time.time()
        })


    # ---- Security ----
    def record_verification(self, ecu_id, method, latency_ms, success):
        self.security.append({
            "ecu_id": ecu_id,
            "method": method,
            "latency_ms": latency_ms,
            "success": success,
            "timestamp": time.time()
        })

    def record_verification_latency(self, latency_ms, method="unknown"):
        self.security.append({
            "method": method,
            "latency_ms": latency_ms,
            "success": True,
            "timestamp": time.time()
        })

    # ---- Resources ----
    def record_resources(self):
        vm = psutil.virtual_memory()
        self.resources.append({
            "timestamp": time.time(),
            "cpu_pct": psutil.cpu_percent(interval=None),
            "mem_mb": vm.used / 1e6,
        })

    # ---- Bandwidth ----
    def record_bandwidth(self, bytes_used, delta_bytes=None, full_bytes=None):
        self.events.append({
            "event": "bandwidth",
            "bytes_used": bytes_used,
            "delta_bytes": delta_bytes,
            "full_bytes": full_bytes,
            "timestamp": time.time()
        })
        self.counters["bandwidth_bytes"] = self.counters.get("bandwidth_bytes", 0) + bytes_used

    # ---- Generic status ----
    def record_success(self, label):
        self.events.append({
            "event": "success",
            "metric": label,
            "timestamp": time.time()
        })
        self.counters[f"{label}_success"] = self.counters.get(f"{label}_success", 0) + 1

    def record_error(self, label):
        self.events.append({
            "event": "error",
            "metric": label,
            "timestamp": time.time()
        })
        self.counters[f"{label}_error"] = self.counters.get(f"{label}_error", 0) + 1

    # ---- Save ----
    def save(self, filename="/home/user/Desktop/shikharvashistha/OTA Metrics/uptane/uptane_metrics.json"):
        data = {}
        if os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    data = json.load(f)
            except Exception:
                data = {}

        # # --- Counters ---
        # if hasattr(self, "counters") and isinstance(self.counters, dict):
        #     for k, v in self.counters.items():
        #         data.setdefault("counters", {})[k] = data["counters"].get(k, 0) + v
        # else:
        #     data.setdefault("counters", {})

        # --- Other fields ---
        for field in ["events", "resources", "security", "ecu_updates", "manifests", "comm", "system"]:
            if hasattr(self, field):
                val = getattr(self, field)
                if isinstance(val, dict):
                    data.setdefault(field, {}).update(val)
                elif isinstance(val, list):
                    data.setdefault(field, []).extend(val)

        # --- Save ---
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"[+] Metrics appended to {filename}")


metrics = SimpleMetrics()
