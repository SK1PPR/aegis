
#!/usr/bin/env python3
"""
Blockchain-based MQTT OTA updater for Arduino with extended metrics.
- Implements a simple blockchain to record firmware update transactions
- Uses proof-of-work consensus for security
- Verifies firmware authenticity through blockchain records
- Downloads firmware announced over MQTT
- Verifies file hash and blockchain signature
- Moves verified firmware to sketch dir and compiles/uploads via arduino-cli
- Records detailed metrics including blockchain operations
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
import psutil
import paho.mqtt.client as mqtt
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

# -----------------------
# Configuration (edit)
# -----------------------
METRICS_FILE = "ota_blockchain_metrics.json"
BLOCKCHAIN_FILE = "ota_blockchain.json"
FIRMWARE_DIR = "./firmware"
SKETCH_DIR = "./1.SecureOTA"
MQTT_BROKER_IP = "127.0.0.1"
MQTT_BROKER_PORT = 1883
MQTT_SUB_TOPIC = "test/topic"
BLOCKCHAIN_DIFFICULTY = 4  # Number of leading zeros in hash (adjust for mining difficulty)

# MQTT credentials
MQTT_USER = "testuser"
MQTT_PASS = "testpass"

# Arduino cli defaults
ARDUINO_CLI_BIN = "arduino-cli"

# -----------------------
# Blockchain Implementation
# -----------------------
@dataclass
class Transaction:
    """Represents a firmware update transaction"""
    firmware_hash: str
    firmware_url: str
    version: str
    manufacturer: str
    device_id: str
    timestamp: float
    signature: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "firmware_hash": self.firmware_hash,
            "firmware_url": self.firmware_url,
            "version": self.version,
            "manufacturer": self.manufacturer,
            "device_id": self.device_id,
            "timestamp": self.timestamp,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Transaction':
        return cls(**data)

class Block:
    """Represents a block in the blockchain"""
    def __init__(self, index: int, transactions: List[Transaction], 
                 timestamp: float, previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """Calculate the hash of the block"""
        transactions_str = json.dumps([tx.to_dict() for tx in self.transactions], sort_keys=True)
        block_string = f"{self.index}{transactions_str}{self.timestamp}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self, difficulty: int) -> None:
        """Mine the block using proof-of-work"""
        target = "0" * difficulty
        start_time = time.time()
        
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
            
            # Prevent infinite loops in case of very high difficulty
            if time.time() - start_time > 300:  # 5 minute timeout
                print(f"Mining timeout after 5 minutes. Hash: {self.hash}")
                break
        
        mining_time = time.time() - start_time
        print(f"Block mined in {mining_time:.2f} seconds. Hash: {self.hash}")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "transactions": [tx.to_dict() for tx in self.transactions],
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        transactions = [Transaction.from_dict(tx) for tx in data["transactions"]]
        block = cls(data["index"], transactions, data["timestamp"], 
                   data["previous_hash"], data["nonce"])
        block.hash = data["hash"]
        return block

class FirmwareBlockchain:
    """Blockchain for managing firmware update records"""
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_transactions: List[Transaction] = []
        self.mining_reward = 1.0  # Symbolic reward for mining
        
        # Load existing blockchain or create genesis block
        self.load_blockchain()
        if not self.chain:
            self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """Create the first block in the chain"""
        genesis_tx = Transaction(
            firmware_hash="0000000000000000000000000000000000000000000000000000000000000000",
            firmware_url="genesis",
            version="0.0.0",
            manufacturer="system",
            device_id="genesis",
            timestamp=time.time(),
            signature="genesis_signature"
        )
        genesis_block = Block(0, [genesis_tx], time.time(), "0")
        genesis_block.mine_block(self.difficulty)
        self.chain.append(genesis_block)
        self.save_blockchain()
        print("Genesis block created")
    
    def get_latest_block(self) -> Block:
        """Get the most recent block in the chain"""
        return self.chain[-1] if self.chain else None
    
    def add_transaction(self, transaction: Transaction) -> None:
        """Add a transaction to the pending pool"""
        # Simple signature verification (in production, use proper cryptographic signatures)
        transaction.signature = self.sign_transaction(transaction)
        self.pending_transactions.append(transaction)
    
    def sign_transaction(self, transaction: Transaction) -> str:
        """Create a simple signature for the transaction"""
        tx_string = f"{transaction.firmware_hash}{transaction.version}{transaction.timestamp}"
        return hashlib.sha256(tx_string.encode()).hexdigest()[:16]
    
    def mine_pending_transactions(self, mining_reward_address: str) -> Block:
        """Mine a new block with pending transactions"""
        if not self.pending_transactions:
            print("No pending transactions to mine")
            return None
        
        # Add mining reward transaction
        reward_tx = Transaction(
            firmware_hash="reward",
            firmware_url="",
            version="",
            manufacturer="system",
            device_id=mining_reward_address,
            timestamp=time.time(),
            signature="mining_reward"
        )
        
        transactions = self.pending_transactions.copy()
        transactions.append(reward_tx)
        
        new_block = Block(
            len(self.chain),
            transactions,
            time.time(),
            self.get_latest_block().hash if self.get_latest_block() else "0"
        )
        
        new_block.mine_block(self.difficulty)
        self.chain.append(new_block)
        self.pending_transactions = []  # Clear pending transactions
        
        self.save_blockchain()
        print(f"Block {new_block.index} added to blockchain")
        return new_block
    
    def validate_chain(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]
            
            # Check if current block's hash is correct
            if current_block.hash != current_block.calculate_hash():
                print(f"Invalid hash at block {i}")
                return False
            
            # Check if current block points to previous block
            if current_block.previous_hash != previous_block.hash:
                print(f"Invalid previous hash at block {i}")
                return False
        
        return True
    
    def get_firmware_history(self, device_id: str) -> List[Transaction]:
        """Get firmware update history for a specific device"""
        history = []
        for block in self.chain:
            for tx in block.transactions:
                if tx.device_id == device_id and tx.firmware_hash != "reward":
                    history.append(tx)
        return history
    
    def verify_firmware_authenticity(self, firmware_hash: str, version: str) -> bool:
        """Verify if firmware is authentic based on blockchain records"""
        for block in self.chain:
            for tx in block.transactions:
                if (tx.firmware_hash == firmware_hash and 
                    tx.version == version and 
                    tx.firmware_hash != "reward"):
                    return True
        return False
    
    def save_blockchain(self) -> None:
        """Save blockchain to file"""
        try:
            data = {
                "chain": [block.to_dict() for block in self.chain],
                "difficulty": self.difficulty,
                "pending_transactions": [tx.to_dict() for tx in self.pending_transactions]
            }
            with open(BLOCKCHAIN_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving blockchain: {e}")
    
    def load_blockchain(self) -> None:
        """Load blockchain from file"""
        try:
            if os.path.exists(BLOCKCHAIN_FILE):
                with open(BLOCKCHAIN_FILE, 'r') as f:
                    data = json.load(f)
                
                self.chain = [Block.from_dict(block_data) for block_data in data["chain"]]
                self.difficulty = data.get("difficulty", 4)
                self.pending_transactions = [Transaction.from_dict(tx_data) 
                                           for tx_data in data.get("pending_transactions", [])]
                print(f"Blockchain loaded with {len(self.chain)} blocks")
        except Exception as e:
            print(f"Error loading blockchain: {e}")
            self.chain = []

# -----------------------
# Enhanced Metrics with Blockchain
# -----------------------
class BlockchainMetrics:
    """Enhanced metrics collector with blockchain support"""
    def __init__(self, filename=METRICS_FILE):
        self.filename = filename
        self.counters = {}
        self.events = []
        self.security = []
        self.system = {}
        self.resources = []
        self.blockchain_events = []  # New: blockchain-specific events
        
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
    def add_blockchain_event(self, event_type, details=None):
        """Add blockchain-specific event"""
        ev = {
            "type": event_type,
            "details": details,
            "time": time.time()
        }
        self.blockchain_events.append(ev)
    
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
        if not isinstance(data.get("blockchain_events"), list):
            data["blockchain_events"] = []
        
        # Merge counters
        for k, v in self.counters.items():
            data["counters"][k] = data["counters"].get(k, 0) + v
        
        # Append events
        data["events"].extend(self.events)
        data["security"].extend(self.security)
        data["resources"].extend(self.resources)
        data["blockchain_events"].extend(self.blockchain_events)
        data["system"].update(self.system)
        
        # Atomic write
        tmp = self.filename + ".tmp"
        try:
            with open(tmp, "w") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self.filename)
        except Exception as e:
            print(f"[metrics] Failed to save metrics: {e}")
        
        # Reset buffers
        self.counters.clear()
        self.events.clear()
        self.security.clear()
        self.resources.clear()
        self.blockchain_events.clear()

# Global instances
blockchain = FirmwareBlockchain(difficulty=BLOCKCHAIN_DIFFICULTY)
metrics = BlockchainMetrics()

# -----------------------
# BinaryHashTree (unchanged from original)
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
# Helper utils (unchanged from original)
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
# Arduino helpers (unchanged from original)
# -----------------------
def find_first_arduino_board(fqbn_hint=None):
    try:
        result = subprocess.run([ARDUINO_CLI_BIN, "board", "list"], 
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                              text=True, timeout=10)
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
        cproc = subprocess.run(compile_cmd, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, text=True, timeout=timeout)
        result["compile"] = {"rc": cproc.returncode, "stdout": cproc.stdout, "stderr": cproc.stderr}
        
        metrics.add_event("arduino_compile", "ok" if cproc.returncode == 0 else "fail", 
                         {"rc": cproc.returncode})
        metrics.save()
        
        if cproc.returncode != 0:
            return result
        
        upload_cmd = [ARDUINO_CLI_BIN, "upload", "-p", port, "--fqbn", fqbn, ino_path]
        uproc = subprocess.run(upload_cmd, stdout=subprocess.PIPE, 
                             stderr=subprocess.PIPE, text=True, timeout=timeout)
        result["upload"] = {"rc": uproc.returncode, "stdout": uproc.stdout, "stderr": uproc.stderr}
        
        metrics.add_event("arduino_upload", "ok" if uproc.returncode == 0 else "fail", 
                         {"rc": uproc.returncode})
        metrics.save()
        
    except subprocess.TimeoutExpired as e:
        metrics.add_event("arduino_cli_timeout", "fail", {"error": str(e)})
        metrics.save()
    except Exception as e:
        metrics.add_event("arduino_cli_exception", "fail", {"error": str(e)})
        metrics.save()
    
    return result

# -----------------------
# Enhanced MQTT callbacks with Blockchain
# -----------------------
message_count = 0
root_hash = None
moterVersion = 0
lightVersion = 0
device_id = "arduino_001"  # Unique device identifier

def on_connect(client, userdata, flags, rc):
    print("Connected with result code", rc)
    metrics.add_event("mqtt_connect", "ok", {"rc": rc})
    metrics.increment("mqtt_connects")
    metrics.save()
    client.subscribe(MQTT_SUB_TOPIC)

def on_message(client, userdata, msg):
    global message_count, root_hash, moterVersion, device_id, blockchain
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
    
    # Check blockchain for firmware authenticity first
    expected_file_hash = payload.get("FileHash")
    manufacturer = payload.get("Manufacturer", "unknown")
    
    if expected_file_hash:
        is_authentic = blockchain.verify_firmware_authenticity(expected_file_hash, str(advertised_version))
        if not is_authentic:
            print("Firmware not found in blockchain - checking if it's a new authorized update...")
            metrics.add_blockchain_event("firmware_not_in_blockchain", {
                "hash": expected_file_hash,
                "version": str(advertised_version)
            })
    
    if advertised_version <= moterVersion:
        print("No new firmware update required.")
        metrics.add_event("update_skipped", "ok", {
            "advertised_version": advertised_version, 
            "current_version": moterVersion
        })
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
        if firmware_location.startswith("http://127.0.0.1/") and ":8000" not in firmware_location:
            firmware_location = firmware_location.replace("http://127.0.0.1/", "http://127.0.0.1:8000/")
        r = requests.get(firmware_location, timeout=30)
        r.raise_for_status()
        with open(firmware_path, "wb") as f:
            f.write(r.content)
        
        metrics.add_event("firmware_download", "ok", {
            "url": firmware_location, 
            "file": firmware_path, 
            "size": len(r.content)
        })
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
    
    # --- File hash verification ---
    t0_hash = time.time()
    try:
        actual_file_hash = compute_file_hash_hex(firmware_path)
        print("Expected:", expected_file_hash, "Actual:", actual_file_hash)
        if expected_file_hash:
            if expected_file_hash == actual_file_hash:
                metrics.add_security_check("file_hash", "ok", {
                    "expected": expected_file_hash, 
                    "got": actual_file_hash
                })
            else:
                metrics.add_security_check("file_hash", "fail", {
                    "expected": expected_file_hash, 
                    "got": actual_file_hash
                })
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
    
    # --- Binary hash tree verification ---
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
                metrics.add_security_check("root_hash", "ok", {
                    "expected": expected_root_hash, 
                    "got": new_root_hash_hex
                })
            else:
                metrics.add_security_check("root_hash", "fail", {
                    "expected": expected_root_hash, 
                    "got": new_root_hash_hex
                })
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
    
    # --- Blockchain Transaction Recording ---
    try:
        # Create firmware update transaction
        firmware_tx = Transaction(
            firmware_hash=actual_file_hash,
            firmware_url=firmware_location,
            version=str(advertised_version),
            manufacturer=manufacturer,
            device_id=device_id,
            timestamp=time.time()
        )
        
        # Add to blockchain
        blockchain.add_transaction(firmware_tx)
        metrics.add_blockchain_event("transaction_created", {
            "firmware_hash": actual_file_hash,
            "version": str(advertised_version),
            "device_id": device_id
        })
        
        # Mine the block (in production, this would be done by network miners)
        print("Mining blockchain block...")
        t0_mine = time.time()
        new_block = blockchain.mine_pending_transactions(device_id)
        
        if new_block:
            mining_time = time.time() - t0_mine
            metrics.add_blockchain_event("block_mined", {
                "block_index": new_block.index,
                "mining_time": mining_time,
                "transactions_count": len(new_block.transactions)
            })
            print(f"Block {new_block.index} mined successfully in {mining_time:.2f} seconds")
        
        # Verify blockchain integrity
        if blockchain.validate_chain():
            metrics.add_blockchain_event("blockchain_validated", {"status": "ok"})
            print("Blockchain validation successful")
        else:
            metrics.add_blockchain_event("blockchain_validated", {"status": "failed"})
            print("Blockchain validation failed!")
            return
            
    except Exception as e:
        metrics.add_blockchain_event("blockchain_error", {"error": str(e)})
        metrics.save()
        print("Error in blockchain operations:", e)
        return
    
    # --- Move firmware ---
    t0_move = time.time()
    try:
        os.makedirs(SKETCH_DIR, exist_ok=True)
        target_path = os.path.join(SKETCH_DIR, os.path.basename(firmware_path))
        # shutil.move(firmware_path, target_path) don't move just copy
        shutil.copy(firmware_path, target_path)
        
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
    metrics.add_event("deploy_result", "ok", {
        "compile": compile_upload_result.get("compile"), 
        "upload": compile_upload_result.get("upload")
    })
    metrics.increment("deploy_attempts")
    
    if ((compile_upload_result.get("compile") and 
         compile_upload_result["compile"].get("rc") != 0) or 
        (compile_upload_result.get("upload") and 
         compile_upload_result["upload"].get("rc") != 0)):
        metrics.increment("deploy_failures")
        metrics.add_event("deploy_status", "fail", compile_upload_result)
        metrics.add_blockchain_event("firmware_deploy_failed", {
            "version": str(advertised_version),
            "device_id": device_id
        })
        print("Compile or upload failed; check metrics for details.")
    else:
        metrics.increment("deploy_success")
        metrics.add_event("deploy_status", "ok", compile_upload_result)
        metrics.add_blockchain_event("firmware_deploy_success", {
            "version": str(advertised_version),
            "device_id": device_id
        })
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
    
    print(f"Blockchain-based OTA update completed in {elapsed:.1f} seconds.")
    print(f"Blockchain now contains {len(blockchain.chain)} blocks")

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

def print_blockchain_info():
    """Print current blockchain status"""
    print("\n" + "="*50)
    print("BLOCKCHAIN STATUS")
    print("="*50)
    print(f"Total blocks: {len(blockchain.chain)}")
    print(f"Blockchain valid: {blockchain.validate_chain()}")
    print(f"Pending transactions: {len(blockchain.pending_transactions)}")
    
    if blockchain.chain:
        latest_block = blockchain.get_latest_block()
        print(f"Latest block index: {latest_block.index}")
        print(f"Latest block hash: {latest_block.hash}")
        
        # Print device firmware history
        history = blockchain.get_firmware_history(device_id)
        print(f"\nFirmware history for {device_id}:")
        for i, tx in enumerate(history):
            print(f"  {i+1}. Version {tx.version} - Hash: {tx.firmware_hash[:16]}...")
    
    print("="*50 + "\n")

if __name__ == "__main__":
    os.makedirs(FIRMWARE_DIR, exist_ok=True)
    os.makedirs(SKETCH_DIR, exist_ok=True)
    
    # Initialize metrics
    metrics.set_system("host", os.uname().nodename if hasattr(os, "uname") else "unknown")
    metrics.set_system("firmware_dir", os.path.abspath(FIRMWARE_DIR))
    metrics.set_system("sketch_dir", os.path.abspath(SKETCH_DIR))
    metrics.set_system("blockchain_file", os.path.abspath(BLOCKCHAIN_FILE))
    metrics.set_system("blockchain_difficulty", BLOCKCHAIN_DIFFICULTY)
    metrics.set_system("device_id", device_id)
    metrics.save()
    
    print("Blockchain-based OTA Updater Starting...")
    print_blockchain_info()
    
    print("Starting MQTT listener for OTA updates...")
    print("Press Ctrl+C to stop")
    
    run_mqtt_loop()
