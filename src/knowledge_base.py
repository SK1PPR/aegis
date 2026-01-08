"""
OTA-specific knowledge base with three-stage retrieval pipeline:
1. Metadata Filtering (ECU, region, safety class, version)
2. Vector-Based Semantic Retrieval
3. Schema-Aware and Version-Aware Re-Ranking
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
from sentence_transformers import SentenceTransformer
from datetime import datetime


class SafetyClass(Enum):
    """ASIL safety classification levels"""
    ASIL_A = "ASIL_A"
    ASIL_B = "ASIL_B"
    ASIL_C = "ASIL_C"
    ASIL_D = "ASIL_D"
    QM = "QM"  # Quality Managed (non-safety critical)


class DeploymentMode(Enum):
    """OTA deployment strategies"""
    A_B = "A/B"
    DUAL_BANK = "dual-bank"
    SINGLE_BANK = "single-bank"
    DELTA = "delta"
    FULL = "full"


class ECUType(Enum):
    """Electronic Control Unit types"""
    INFOTAINMENT = "infotainment"
    ADAS = "adas"
    POWERTRAIN = "powertrain"
    BODY_CONTROL = "body_control"
    TELEMATICS = "telematics"
    GATEWAY = "gateway"


@dataclass
class OTAMetadata:
    """Strict metadata for Stage 1 filtering"""
    device_type: ECUType
    sw_version: str  # Semantic version: "1.2.3"
    safety_class: SafetyClass
    region: str  # ISO 3166-1 alpha-2: "US", "EU", "CN"
    hardware_revision: str  # "rev_A", "rev_B"
    deployment_mode: DeploymentMode
    min_sw_version: Optional[str] = None  # Minimum compatible version
    max_sw_version: Optional[str] = None  # Maximum compatible version
    required_capabilities: Set[str] = field(default_factory=set)  # e.g., {"CAN_FD", "Ethernet"}
    

@dataclass
class SchemaField:
    """Schema structure for validation"""
    name: str
    field_type: str  # "string", "integer", "array", "object"
    required: bool
    validation_pattern: Optional[str] = None
    enum_values: Optional[List[str]] = None


@dataclass
class OTADeploymentPattern:
    """OTA deployment pattern with metadata and schema"""
    id: str
    name: str
    description: str
    use_case: str
    
    # Stage 1: Hard metadata
    metadata: OTAMetadata
    
    # Stage 2: Semantic content
    deployment_spec: Dict  # The actual deployment configuration
    best_practices: List[str]
    common_issues: List[str]
    tags: List[str]
    
    # Stage 3: Schema and version info
    schema_fields: List[SchemaField]
    last_updated: str  # ISO 8601 timestamp
    validation_rules: List[str]
    dependencies: List[str]  # Other pattern IDs this depends on
    
    # Additional OTA-specific fields
    rollback_procedure: str
    verification_steps: List[str]
    estimated_duration_seconds: int
    network_requirements: Dict  # bandwidth, timeout, retry


class OTAKnowledgeBase:
    """
    Three-stage retrieval pipeline for OTA deployment patterns.
    
    Stage 1: Metadata Filtering (deterministic)
    Stage 2: Vector Semantic Search (ANN)
    Stage 3: Schema-Aware Re-Ranking (structural + version)
    """
    
    def __init__(self, kb_path: str = None):
        # Default to data directory
        if kb_path is None:
            kb_path = Path(__file__).parent.parent / "data" / "ota_knowledge_base.json"
        self.kb_path = Path(kb_path)
        self.patterns: List[OTADeploymentPattern] = []
        self.embeddings = None
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

        self._load_knowledge_base()
        self._compute_embeddings()
    
    def _load_knowledge_base(self):
        """Load OTA patterns from JSON"""
        if not self.kb_path.exists():
            self._create_default_ota_kb()
        
        with open(self.kb_path, 'r') as f:
            data = json.load(f)
            for item in data['patterns']:
                # Parse metadata
                metadata_dict = item['metadata']
                metadata = OTAMetadata(
                    device_type=ECUType(metadata_dict['device_type']),
                    sw_version=metadata_dict['sw_version'],
                    safety_class=SafetyClass(metadata_dict['safety_class']),
                    region=metadata_dict['region'],
                    hardware_revision=metadata_dict['hardware_revision'],
                    deployment_mode=DeploymentMode(metadata_dict['deployment_mode']),
                    min_sw_version=metadata_dict.get('min_sw_version'),
                    max_sw_version=metadata_dict.get('max_sw_version'),
                    required_capabilities=set(metadata_dict.get('required_capabilities', []))
                )
                
                # Parse schema fields
                schema_fields = [SchemaField(**sf) for sf in item.get('schema_fields', [])]
                
                pattern = OTADeploymentPattern(
                    id=item['id'],
                    name=item['name'],
                    description=item['description'],
                    use_case=item['use_case'],
                    metadata=metadata,
                    deployment_spec=item['deployment_spec'],
                    best_practices=item['best_practices'],
                    common_issues=item['common_issues'],
                    tags=item['tags'],
                    schema_fields=schema_fields,
                    last_updated=item['last_updated'],
                    validation_rules=item['validation_rules'],
                    dependencies=item.get('dependencies', []),
                    rollback_procedure=item['rollback_procedure'],
                    verification_steps=item['verification_steps'],
                    estimated_duration_seconds=item['estimated_duration_seconds'],
                    network_requirements=item['network_requirements']
                )
                self.patterns.append(pattern)
    
    def _create_default_ota_kb(self):
        """Create default OTA knowledge base"""
        default_kb = {
            "patterns": [
                {
                    "id": "ota_infotainment_full",
                    "name": "Full OTA Update for Infotainment ECU",
                    "description": "Complete firmware update for infotainment system using A/B partitioning",
                    "use_case": "Major version upgrade of infotainment software with new UI features",
                    "metadata": {
                        "device_type": "infotainment",
                        "sw_version": "2.0.0",
                        "safety_class": "QM",
                        "region": "US",
                        "hardware_revision": "rev_B",
                        "deployment_mode": "A/B",
                        "min_sw_version": "1.5.0",
                        "max_sw_version": None,
                        "required_capabilities": ["Ethernet", "4G_LTE"]
                    },
                    "deployment_spec": {
                        "update_package": {
                            "name": "infotainment_v2.0.0",
                            "size_mb": 1200,
                            "checksum": "sha256:abc123...",
                            "signature": "RSA2048:def456...",
                            "compression": "zstd"
                        },
                        "pre_conditions": {
                            "battery_level_min": 50,
                            "vehicle_state": "parked",
                            "network_available": True,
                            "disk_space_mb": 2500
                        },
                        "installation": {
                            "target_partition": "partition_B",
                            "backup_current": True,
                            "verify_integrity": True,
                            "reboot_required": True
                        },
                        "post_conditions": {
                            "verify_boot": True,
                            "run_diagnostics": True,
                            "report_telemetry": True
                        }
                    },
                    "best_practices": [
                        "Always verify battery level before starting update",
                        "Use A/B partitioning for safe rollback",
                        "Implement progressive download with resume capability",
                        "Run full diagnostic suite after installation",
                        "Monitor vehicle state throughout update process"
                    ],
                    "common_issues": [
                        "Network interruption during download - implement chunked transfer with retry",
                        "Insufficient disk space - clean temp files before update",
                        "Boot verification failure - automatic rollback to partition A",
                        "Battery drain during installation - warn user to connect charger"
                    ],
                    "tags": ["infotainment", "full-update", "A/B", "major-version", "QM"],
                    "schema_fields": [
                        {
                            "name": "update_package.name",
                            "field_type": "string",
                            "required": True,
                            "validation_pattern": "^[a-z_]+_v\\d+\\.\\d+\\.\\d+$"
                        },
                        {
                            "name": "update_package.checksum",
                            "field_type": "string",
                            "required": True,
                            "validation_pattern": "^sha256:[a-f0-9]{64}$"
                        },
                        {
                            "name": "pre_conditions.battery_level_min",
                            "field_type": "integer",
                            "required": True,
                            "validation_pattern": None
                        }
                    ],
                    "last_updated": "2024-11-20T10:30:00Z",
                    "validation_rules": [
                        "battery_level_min must be >= 30",
                        "disk_space_mb must be >= 2x update size",
                        "signature verification must pass",
                        "hardware_revision must match target ECU"
                    ],
                    "dependencies": [],
                    "rollback_procedure": "If boot verification fails, bootloader automatically switches to partition A. Manual rollback via diagnostic port available for 72 hours.",
                    "verification_steps": [
                        "Verify package signature",
                        "Check disk space availability",
                        "Validate battery level",
                        "Confirm vehicle parked state",
                        "Post-install: Boot to new partition",
                        "Post-install: Run CAN diagnostics",
                        "Post-install: Verify UI functionality"
                    ],
                    "estimated_duration_seconds": 1800,
                    "network_requirements": {
                        "bandwidth_mbps": 10,
                        "timeout_seconds": 3600,
                        "retry_count": 3,
                        "connection_type": "4G_LTE or WiFi"
                    }
                },
                {
                    "id": "ota_adas_delta",
                    "name": "Delta OTA Update for ADAS ECU",
                    "description": "Incremental update for ADAS camera calibration and detection algorithms",
                    "use_case": "Patch update for improved object detection without full reflash",
                    "metadata": {
                        "device_type": "adas",
                        "sw_version": "3.2.1",
                        "safety_class": "ASIL_B",
                        "region": "EU",
                        "hardware_revision": "rev_C",
                        "deployment_mode": "delta",
                        "min_sw_version": "3.2.0",
                        "max_sw_version": "3.2.999",
                        "required_capabilities": ["CAN_FD", "Ethernet", "Camera_Interface"]
                    },
                    "deployment_spec": {
                        "update_package": {
                            "name": "adas_delta_v3.2.0_to_v3.2.1",
                            "size_mb": 45,
                            "checksum": "sha256:xyz789...",
                            "signature": "RSA4096:ghi012...",
                            "compression": "bsdiff",
                            "delta_base_version": "3.2.0"
                        },
                        "pre_conditions": {
                            "battery_level_min": 70,
                            "vehicle_state": "parked",
                            "network_available": True,
                            "current_version_verified": True,
                            "safety_diagnostics_passed": True
                        },
                        "installation": {
                            "apply_delta_patch": True,
                            "target_partition": "active",
                            "backup_critical_configs": True,
                            "atomic_update": True,
                            "reboot_required": True
                        },
                        "post_conditions": {
                            "verify_boot": True,
                            "run_adas_diagnostics": True,
                            "calibration_check": True,
                            "report_telemetry": True,
                            "safety_validation": True
                        }
                    },
                    "best_practices": [
                        "Verify base version before applying delta",
                        "Require higher battery threshold for safety-critical ECUs",
                        "Run comprehensive ADAS diagnostics after update",
                        "Perform camera recalibration verification",
                        "Implement atomic update to prevent partial application",
                        "Log all safety-related events during update"
                    ],
                    "common_issues": [
                        "Delta patch corruption - verify checksum before and after application",
                        "Camera calibration drift - run auto-calibration post-update",
                        "CAN bus timeout during reboot - implement watchdog with extended timeout",
                        "Version mismatch - strict base version validation required",
                        "Safety diagnostic failure - automatic rollback mandatory"
                    ],
                    "tags": ["adas", "delta-update", "ASIL-B", "safety-critical", "camera", "detection"],
                    "schema_fields": [
                        {
                            "name": "update_package.delta_base_version",
                            "field_type": "string",
                            "required": True,
                            "validation_pattern": "^\\d+\\.\\d+\\.\\d+$"
                        },
                        {
                            "name": "pre_conditions.safety_diagnostics_passed",
                            "field_type": "boolean",
                            "required": True
                        },
                        {
                            "name": "post_conditions.safety_validation",
                            "field_type": "boolean",
                            "required": True
                        }
                    ],
                    "last_updated": "2024-11-25T14:22:00Z",
                    "validation_rules": [
                        "battery_level_min must be >= 70 for ASIL-B",
                        "current_version must exactly match delta_base_version",
                        "signature must use RSA4096 or higher for ASIL-B",
                        "safety_diagnostics must pass before and after update",
                        "calibration_check must succeed post-update"
                    ],
                    "dependencies": [],
                    "rollback_procedure": "ASIL-B requires automatic rollback if any safety diagnostic fails. Rollback is triggered within 100ms of detection. Previous version restored from backup partition. Vehicle enters limp mode until manual inspection.",
                    "verification_steps": [
                        "Verify package signature (RSA4096)",
                        "Confirm base version matches exactly",
                        "Check battery level >= 70%",
                        "Run pre-update safety diagnostics",
                        "Apply delta patch atomically",
                        "Post-install: Verify boot",
                        "Post-install: Run ADAS diagnostic suite",
                        "Post-install: Camera calibration verification",
                        "Post-install: Object detection sanity test",
                        "Post-install: Safety validation complete"
                    ],
                    "estimated_duration_seconds": 600,
                    "network_requirements": {
                        "bandwidth_mbps": 5,
                        "timeout_seconds": 1200,
                        "retry_count": 5,
                        "connection_type": "Ethernet or 4G_LTE"
                    }
                },
                {
                    "id": "ota_powertrain_dual_bank",
                    "name": "Dual-Bank OTA Update for Powertrain ECU",
                    "description": "Safety-critical powertrain update using dual-bank flash memory",
                    "use_case": "Engine control unit firmware update for emissions compliance",
                    "metadata": {
                        "device_type": "powertrain",
                        "sw_version": "5.1.3",
                        "safety_class": "ASIL_D",
                        "region": "CN",
                        "hardware_revision": "rev_A",
                        "deployment_mode": "dual-bank",
                        "min_sw_version": "5.0.0",
                        "max_sw_version": "5.1.999",
                        "required_capabilities": ["CAN_FD", "FlexRay", "Dual_Bank_Flash"]
                    },
                    "deployment_spec": {
                        "update_package": {
                            "name": "powertrain_ecu_v5.1.3",
                            "size_mb": 8,
                            "checksum": "sha384:mno345...",
                            "signature": "ECDSA_P384:pqr678...",
                            "compression": "lzma",
                            "encryption": "AES256_GCM"
                        },
                        "pre_conditions": {
                            "battery_level_min": 90,
                            "vehicle_state": "parked_engine_off",
                            "network_available": True,
                            "ignition_off": True,
                            "no_dtc_codes": True,
                            "coolant_temp_normal": True
                        },
                        "installation": {
                            "target_bank": "bank_1",
                            "verify_inactive_bank": True,
                            "write_with_verification": True,
                            "switch_bank_on_success": True,
                            "reboot_required": True,
                            "keep_backup_bank": True
                        },
                        "post_conditions": {
                            "verify_boot_from_new_bank": True,
                            "run_powertrain_diagnostics": True,
                            "emissions_test": True,
                            "report_telemetry": True,
                            "safety_validation_asil_d": True
                        }
                    },
                    "best_practices": [
                        "Require 90%+ battery for ASIL-D updates",
                        "Ensure engine is off and cooled",
                        "Use dual-bank flash for atomic updates",
                        "Encrypt update package for security",
                        "Keep backup bank intact for 30 days",
                        "Run full emissions diagnostic post-update",
                        "Implement triple-redundant safety checks"
                    ],
                    "common_issues": [
                        "Flash write failure - automatically retry on backup bank",
                        "DTC codes present - abort update until cleared",
                        "Emissions test failure - automatic rollback mandatory",
                        "Bank switch failure - fallback to backup bank immediately",
                        "Watchdog timeout during flash - extended timeout for ASIL-D"
                    ],
                    "tags": ["powertrain", "dual-bank", "ASIL-D", "emissions", "engine-control", "safety-critical"],
                    "schema_fields": [
                        {
                            "name": "pre_conditions.ignition_off",
                            "field_type": "boolean",
                            "required": True
                        },
                        {
                            "name": "pre_conditions.no_dtc_codes",
                            "field_type": "boolean",
                            "required": True
                        },
                        {
                            "name": "post_conditions.safety_validation_asil_d",
                            "field_type": "boolean",
                            "required": True
                        }
                    ],
                    "last_updated": "2024-11-18T09:15:00Z",
                    "validation_rules": [
                        "battery_level_min must be >= 90 for ASIL-D",
                        "ignition must be off during entire update",
                        "no_dtc_codes must be true before starting",
                        "emissions_test must pass post-update",
                        "signature must use ECDSA_P384 or higher for ASIL-D",
                        "encryption must be AES256 minimum for powertrain"
                    ],
                    "dependencies": [],
                    "rollback_procedure": "ASIL-D requires immediate automatic rollback if any safety check fails. System switches back to backup bank within 50ms. Vehicle enters fail-safe mode with reduced power. OBD-II code logged. Manual technician inspection required before retry.",
                    "verification_steps": [
                        "Verify package signature (ECDSA_P384)",
                        "Decrypt package with AES256_GCM",
                        "Check battery >= 90%",
                        "Confirm ignition off",
                        "Verify no DTC codes",
                        "Check coolant temperature normal",
                        "Write to inactive bank with verification",
                        "Post-install: Switch to new bank",
                        "Post-install: Verify boot from new bank",
                        "Post-install: Run powertrain diagnostics",
                        "Post-install: Emissions compliance test",
                        "Post-install: ASIL-D safety validation"
                    ],
                    "estimated_duration_seconds": 300,
                    "network_requirements": {
                        "bandwidth_mbps": 2,
                        "timeout_seconds": 600,
                        "retry_count": 7,
                        "connection_type": "Wired_Ethernet_only"
                    }
                },
                {
                    "id": "ota_telematics_cloud",
                    "name": "Cloud-Connected Telematics OTA",
                    "description": "Over-the-air update for telematics control unit with cloud sync",
                    "use_case": "Update telematics for new connected services and security patches",
                    "metadata": {
                        "device_type": "telematics",
                        "sw_version": "4.5.2",
                        "safety_class": "QM",
                        "region": "US",
                        "hardware_revision": "rev_D",
                        "deployment_mode": "full",
                        "min_sw_version": "4.0.0",
                        "max_sw_version": None,
                        "required_capabilities": ["5G", "GPS", "Cloud_API"]
                    },
                    "deployment_spec": {
                        "update_package": {
                            "name": "telematics_v4.5.2",
                            "size_mb": 250,
                            "checksum": "sha256:stu901...",
                            "signature": "RSA2048:vwx234...",
                            "compression": "zstd",
                            "cloud_source": "https://ota.example.com/updates/"
                        },
                        "pre_conditions": {
                            "battery_level_min": 40,
                            "network_available": True,
                            "cloud_connectivity": True,
                            "disk_space_mb": 600
                        },
                        "installation": {
                            "download_from_cloud": True,
                            "progressive_download": True,
                            "verify_chunks": True,
                            "install_in_background": False,
                            "reboot_required": True
                        },
                        "post_conditions": {
                            "verify_boot": True,
                            "cloud_sync": True,
                            "gps_test": True,
                            "report_telemetry": True
                        }
                    },
                    "best_practices": [
                        "Use progressive download with resume capability",
                        "Verify each chunk before writing to disk",
                        "Sync with cloud after successful update",
                        "Test GPS functionality post-update",
                        "Implement bandwidth throttling to avoid data overage"
                    ],
                    "common_issues": [
                        "5G connection drop - implement resume from last chunk",
                        "Cloud API timeout - retry with exponential backoff",
                        "GPS signal loss after update - run GPS cold start",
                        "Disk space exhaustion - clean old logs before download"
                    ],
                    "tags": ["telematics", "cloud", "5G", "connected-services", "QM"],
                    "schema_fields": [
                        {
                            "name": "update_package.cloud_source",
                            "field_type": "string",
                            "required": True,
                            "validation_pattern": "^https://.*"
                        },
                        {
                            "name": "pre_conditions.cloud_connectivity",
                            "field_type": "boolean",
                            "required": True
                        }
                    ],
                    "last_updated": "2024-11-22T16:45:00Z",
                    "validation_rules": [
                        "cloud_source must use HTTPS",
                        "cloud_connectivity must be verified before download",
                        "disk_space_mb must be >= 2.5x update size",
                        "GPS must function post-update"
                    ],
                    "dependencies": [],
                    "rollback_procedure": "If cloud sync fails after update, keep local version but flag for manual review. GPS failure triggers automatic rollback. User can manually rollback via settings for 7 days.",
                    "verification_steps": [
                        "Verify cloud connectivity",
                        "Check disk space",
                        "Download update from cloud with chunk verification",
                        "Verify package signature",
                        "Post-install: Verify boot",
                        "Post-install: Sync with cloud",
                        "Post-install: GPS functionality test",
                        "Post-install: Connected services health check"
                    ],
                    "estimated_duration_seconds": 900,
                    "network_requirements": {
                        "bandwidth_mbps": 20,
                        "timeout_seconds": 2400,
                        "retry_count": 5,
                        "connection_type": "5G preferred, 4G_LTE fallback"
                    }
                }
            ]
        }
        
        with open(self.kb_path, 'w') as f:
            json.dump(default_kb, f, indent=2)
    
    def _compute_embeddings(self):
        """Compute embeddings for semantic search (Stage 2)"""
        texts = []
        for pattern in self.patterns:
            # Combine semantic fields for embedding
            text = f"{pattern.name} {pattern.description} {pattern.use_case} {' '.join(pattern.tags)} {' '.join(pattern.best_practices)}"
            texts.append(text)
        
        if texts:
            self.embeddings = self.encoder.encode(texts)
    
    # ==================== STAGE 1: METADATA FILTERING ====================
    
    def _version_compatible(self, target_version: str, pattern: OTADeploymentPattern) -> bool:
        """Check if target version is compatible with pattern's version range"""
        def parse_version(v: str) -> Tuple[int, int, int]:
            try:
                parts = v.split('.')
                return (int(parts[0]), int(parts[1]), int(parts[2]))
            except:
                return (0, 0, 0)
        
        target = parse_version(target_version)
        pattern_version = parse_version(pattern.metadata.sw_version)
        
        # Check min version
        if pattern.metadata.min_sw_version:
            min_ver = parse_version(pattern.metadata.min_sw_version)
            if target < min_ver:
                return False
        
        # Check max version
        if pattern.metadata.max_sw_version:
            max_ver = parse_version(pattern.metadata.max_sw_version)
            if target > max_ver:
                return False
        
        return True
    
    def stage1_metadata_filter(
        self,
        device_type: ECUType,
        sw_version: str,
        safety_class: SafetyClass,
        region: str,
        hardware_revision: str,
        deployment_mode: Optional[DeploymentMode] = None,
        required_capabilities: Optional[Set[str]] = None
    ) -> List[OTADeploymentPattern]:
        """
        Stage 1: Hard metadata filtering with fallback strategy

        Tries progressively relaxed matching if exact match fails:
        1. Exact match
        2. Relax region (allow GLOBAL or any region)
        3. Relax hardware_revision
        4. Relax deployment_mode
        5. Match only device_type + safety_class (last resort)
        """
        # Try exact match first
        filtered = self._filter_with_criteria(
            device_type, sw_version, safety_class, region,
            hardware_revision, deployment_mode, required_capabilities,
            strict=True
        )

        if filtered:
            return filtered

        # Fallback 1: Relax region (allow GLOBAL region as fallback)
        filtered = self._filter_with_criteria(
            device_type, sw_version, safety_class, None,  # region=None for relaxed matching
            hardware_revision, deployment_mode, required_capabilities,
            strict=False, allow_global_region=True, target_region=region
        )

        if filtered:
            return filtered

        # Fallback 2: Relax hardware_revision
        filtered = self._filter_with_criteria(
            device_type, sw_version, safety_class, None,
            None,  # hardware_revision=None
            deployment_mode, required_capabilities,
            strict=False, allow_global_region=True, target_region=region
        )

        if filtered:
            return filtered

        # Fallback 3: Relax deployment_mode
        filtered = self._filter_with_criteria(
            device_type, sw_version, safety_class, None,
            None, None,  # deployment_mode=None
            required_capabilities,
            strict=False, allow_global_region=True, target_region=region
        )

        if filtered:
            return filtered

        # Fallback 4: Match only device_type + safety_class (last resort)
        filtered = []
        for pattern in self.patterns:
            m = pattern.metadata
            if m.device_type == device_type and m.safety_class == safety_class:
                filtered.append(pattern)

        return filtered

    def _filter_with_criteria(
        self,
        device_type: ECUType,
        sw_version: str,
        safety_class: SafetyClass,
        region: Optional[str],
        hardware_revision: Optional[str],
        deployment_mode: Optional[DeploymentMode],
        required_capabilities: Optional[Set[str]],
        strict: bool = True,
        allow_global_region: bool = False,
        target_region: Optional[str] = None
    ) -> List[OTADeploymentPattern]:
        """Internal filtering with configurable strictness."""
        filtered = []

        for pattern in self.patterns:
            m = pattern.metadata

            # Hard filters - always required
            if m.device_type != device_type:
                continue

            if m.safety_class != safety_class:
                continue

            # Region filter (relaxed or strict)
            if region is not None:
                if m.region != region:
                    continue
            elif allow_global_region and target_region:
                # Allow GLOBAL region as fallback, or match target region
                if m.region not in [target_region, "GLOBAL"]:
                    continue

            # Hardware revision (optional filter)
            if hardware_revision is not None and strict:
                if m.hardware_revision != hardware_revision:
                    continue

            # Version compatibility check
            if not self._version_compatible(sw_version, pattern):
                continue

            # Deployment mode (optional filter)
            if deployment_mode is not None and strict:
                if m.deployment_mode != deployment_mode:
                    continue

            # Required capabilities (pattern must have all required)
            if required_capabilities and strict:
                if not required_capabilities.issubset(m.required_capabilities):
                    continue

            filtered.append(pattern)

        return filtered
    
    # ==================== STAGE 2: VECTOR SEMANTIC RETRIEVAL ====================
    
    def stage2_semantic_search(
        self,
        query: str,
        filtered_patterns: List[OTADeploymentPattern],
        top_k: int = 10
    ) -> List[Tuple[OTADeploymentPattern, float]]:
        """
        Stage 2: Semantic similarity search using vector embeddings
        
        Only searches within the metadata-filtered subset from Stage 1.
        """
        if not filtered_patterns:
            return []
        
        # Get indices of filtered patterns
        filtered_indices = [self.patterns.index(p) for p in filtered_patterns]
        
        # Embed query
        query_embedding = self.encoder.encode([query])[0]
        
        # Get embeddings only for filtered patterns
        filtered_embeddings = self.embeddings[filtered_indices]
        
        # Compute cosine similarity
        similarities = np.dot(filtered_embeddings, query_embedding) / (
            np.linalg.norm(filtered_embeddings, axis=1) * np.linalg.norm(query_embedding)
        )
        
        # Get top-k
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        results = [
            (filtered_patterns[i], float(similarities[i]))
            for i in top_indices
        ]
        
        return results
    
    # ==================== STAGE 3: SCHEMA-AWARE RE-RANKING ====================
    
    def _schema_completeness_score(self, pattern: OTADeploymentPattern, query: str) -> float:
        """Calculate how complete the pattern's schema is"""
        if not pattern.schema_fields:
            return 0.0
        
        # Score based on:
        # 1. Number of required fields defined
        # 2. Presence of validation patterns
        # 3. Matching field names with query terms
        
        required_count = sum(1 for f in pattern.schema_fields if f.required)
        validated_count = sum(1 for f in pattern.schema_fields if f.validation_pattern)
        
        query_lower = query.lower()
        matching_fields = sum(
            1 for f in pattern.schema_fields
            if any(term in f.name.lower() for term in query_lower.split())
        )
        
        # Normalize scores
        completeness = required_count / max(len(pattern.schema_fields), 1)
        validation_coverage = validated_count / max(len(pattern.schema_fields), 1)
        field_relevance = matching_fields / max(len(pattern.schema_fields), 1)
        
        return 0.4 * completeness + 0.3 * validation_coverage + 0.3 * field_relevance
    
    def _version_recency_score(self, pattern: OTADeploymentPattern) -> float:
        """Score based on how recent the pattern was updated"""
        try:
            updated = datetime.fromisoformat(pattern.last_updated.replace('Z', '+00:00'))
            now = datetime.now(updated.tzinfo)
            days_old = (now - updated).days
            
            # Decay score over 365 days
            return max(0.0, 1.0 - (days_old / 365.0))
        except:
            return 0.5  # Default for malformed dates
    
    def _validation_rule_score(self, pattern: OTADeploymentPattern) -> float:
        """Score based on number and specificity of validation rules"""
        if not pattern.validation_rules:
            return 0.0
        
        # More rules = more comprehensive
        rule_count_score = min(1.0, len(pattern.validation_rules) / 10.0)
        
        # Check for safety-specific rules (higher weight)
        safety_rules = sum(
            1 for rule in pattern.validation_rules
            if any(keyword in rule.lower() for keyword in ['safety', 'asil', 'critical', 'diagnostic'])
        )
        safety_score = min(1.0, safety_rules / 3.0)
        
        return 0.6 * rule_count_score + 0.4 * safety_score
    
    def stage3_schema_rerank(
        self,
        semantic_results: List[Tuple[OTADeploymentPattern, float]],
        query: str,
        top_k: int = 5
    ) -> List[Tuple[OTADeploymentPattern, float, Dict[str, float]]]:
        """
        Stage 3: Re-rank based on schema completeness, version recency, and validation rules
        
        Returns patterns with composite score and breakdown of sub-scores.
        """
        reranked = []
        
        for pattern, semantic_score in semantic_results:
            # Calculate sub-scores
            schema_score = self._schema_completeness_score(pattern, query)
            recency_score = self._version_recency_score(pattern)
            validation_score = self._validation_rule_score(pattern)
            
            # Composite score with weights
            composite_score = (
                0.35 * semantic_score +      # Semantic relevance
                0.30 * schema_score +         # Schema completeness
                0.20 * recency_score +        # Version freshness
                0.15 * validation_score       # Validation robustness
            )
            
            score_breakdown = {
                'semantic': semantic_score,
                'schema': schema_score,
                'recency': recency_score,
                'validation': validation_score,
                'composite': composite_score
            }
            
            reranked.append((pattern, composite_score, score_breakdown))
        
        # Sort by composite score
        reranked.sort(key=lambda x: x[1], reverse=True)
        
        return reranked[:top_k]
    
    # ==================== MAIN RETRIEVAL INTERFACE ====================
    
    def retrieve_ota_patterns(
        self,
        query: str,
        device_type: ECUType,
        sw_version: str,
        safety_class: SafetyClass,
        region: str,
        hardware_revision: str,
        deployment_mode: Optional[DeploymentMode] = None,
        required_capabilities: Optional[Set[str]] = None,
        top_k: int = 3
    ) -> List[Tuple[OTADeploymentPattern, float, Dict[str, float]]]:
        """
        Three-stage retrieval pipeline:
        
        1. Metadata filtering (deterministic)
        2. Semantic search (vector-based)
        3. Schema-aware re-ranking (structural + version)
        
        Returns: List of (pattern, score, score_breakdown) tuples
        """
        # Stage 1: Hard metadata filtering
        stage1_results = self.stage1_metadata_filter(
            device_type=device_type,
            sw_version=sw_version,
            safety_class=safety_class,
            region=region,
            hardware_revision=hardware_revision,
            deployment_mode=deployment_mode,
            required_capabilities=required_capabilities
        )
        
        if not stage1_results:
            return []  # No compatible patterns found
        
        # Stage 2: Semantic search on filtered subset
        stage2_results = self.stage2_semantic_search(
            query=query,
            filtered_patterns=stage1_results,
            top_k=min(10, len(stage1_results))  # Get more candidates for re-ranking
        )
        
        if not stage2_results:
            return []
        
        # Stage 3: Schema-aware re-ranking
        final_results = self.stage3_schema_rerank(
            semantic_results=stage2_results,
            query=query,
            top_k=top_k
        )
        
        return final_results
    
    def get_statistics(self) -> Dict:
        """Get knowledge base statistics"""
        device_types = {}
        safety_classes = {}
        deployment_modes = {}
        
        for pattern in self.patterns:
            dt = pattern.metadata.device_type.value
            sc = pattern.metadata.safety_class.value
            dm = pattern.metadata.deployment_mode.value
            
            device_types[dt] = device_types.get(dt, 0) + 1
            safety_classes[sc] = safety_classes.get(sc, 0) + 1
            deployment_modes[dm] = deployment_modes.get(dm, 0) + 1
        
        return {
            'total_patterns': len(self.patterns),
            'by_device_type': device_types,
            'by_safety_class': safety_classes,
            'by_deployment_mode': deployment_modes
        }