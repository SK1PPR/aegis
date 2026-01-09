#!/usr/bin/env python3
"""
Expand OTA knowledge base with missing patterns to improve coverage.
This script adds patterns for gaps identified in the evaluation.
"""

import json
from pathlib import Path
from datetime import datetime

# New patterns to add
new_patterns = [
    # 1. ASIL-C Brake ECU (body_control) - Critical Gap!
    {
        "id": "ota_brake_asil_c",
        "name": "Brake Control ECU Update - ASIL-C",
        "description": "Safety-critical brake control unit firmware update with ASIL-C compliance",
        "use_case": "Update brake ECU with improved ABS algorithms and safety verification",
        "metadata": {
            "device_type": "body_control",
            "sw_version": "4.1.0",
            "safety_class": "ASIL_C",
            "region": "EU",
            "hardware_revision": "rev_A",
            "deployment_mode": "dual-bank",
            "min_sw_version": "4.0.0",
            "max_sw_version": "4.9.999",
            "required_capabilities": ["CAN_FD", "Brake_System", "Dual_Bank_Flash"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "brake_ecu_v4.1.0",
                "size_mb": 12,
                "checksum": "sha384:brake123...",
                "signature": "RSA4096:brake456...",
                "compression": "lzma",
                "encryption": "AES256_GCM"
            },
            "pre_conditions": {
                "battery_level_min": 85,
                "vehicle_state": "parked_brake_engaged",
                "network_available": True,
                "ignition_off": True,
                "no_dtc_codes": True,
                "brake_fluid_ok": True
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
                "run_brake_diagnostics": True,
                "abs_test": True,
                "report_telemetry": True,
                "safety_validation_asil_c": True
            }
        },
        "best_practices": [
            "Require 85%+ battery for ASIL-C brake updates",
            "Ensure vehicle is parked with brake engaged",
            "Use dual-bank flash for atomic updates",
            "Encrypt update package for security",
            "Keep backup bank intact for 60 days",
            "Run comprehensive brake diagnostics post-update",
            "Implement triple-redundant safety checks",
            "Validate ABS and brake assist functionality"
        ],
        "common_issues": [
            "Flash write failure - automatically retry on backup bank",
            "DTC codes present - abort update until cleared",
            "ABS test failure - automatic rollback mandatory",
            "Bank switch failure - fallback to backup bank immediately",
            "Brake fluid low - abort update for safety"
        ],
        "tags": ["body_control", "brake", "dual-bank", "ASIL-C", "safety-critical", "abs"],
        "schema_fields": [
            {
                "name": "pre_conditions.brake_fluid_ok",
                "field_type": "boolean",
                "required": True,
                "validation_pattern": None
            },
            {
                "name": "post_conditions.safety_validation_asil_c",
                "field_type": "boolean",
                "required": True,
                "validation_pattern": None
            },
            {
                "name": "post_conditions.abs_test",
                "field_type": "boolean",
                "required": True,
                "validation_pattern": None
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "battery_level_min must be >= 85 for ASIL-C brake systems",
            "ignition must be off during entire update",
            "no_dtc_codes must be true before starting",
            "abs_test must pass post-update",
            "signature must use RSA4096 or higher for ASIL-C",
            "encryption must be AES256 minimum for brake systems"
        ],
        "dependencies": [],
        "rollback_procedure": "ASIL-C requires immediate automatic rollback if any safety check fails. System switches back to backup bank within 50ms. Vehicle enters limp mode with reduced braking power. Manual technician inspection required before retry.",
        "verification_steps": [
            "Verify package signature (RSA4096)",
            "Decrypt package with AES256_GCM",
            "Check battery >= 85%",
            "Confirm ignition off",
            "Verify no DTC codes",
            "Check brake fluid level OK",
            "Write to inactive bank with verification",
            "Post-install: Switch to new bank",
            "Post-install: Verify boot from new bank",
            "Post-install: Run brake system diagnostics",
            "Post-install: ABS functionality test",
            "Post-install: ASIL-C safety validation"
        ],
        "estimated_duration_seconds": 400,
        "network_requirements": {
            "bandwidth_mbps": 3,
            "timeout_seconds": 800,
            "retry_count": 7,
            "connection_type": "Wired_Ethernet_preferred"
        }
    },

    # 2. Battery ECU - EV powertrain ASIL-D
    {
        "id": "ota_battery_ecu_asil_d",
        "name": "Battery Management ECU Update - ASIL-D",
        "description": "Electric vehicle battery management system update with ASIL-D safety",
        "use_case": "Update BMS firmware with improved thermal management and cell balancing",
        "metadata": {
            "device_type": "powertrain",
            "sw_version": "6.2.0",
            "safety_class": "ASIL_D",
            "region": "CN",
            "hardware_revision": "rev_A",
            "deployment_mode": "dual-bank",
            "min_sw_version": "6.0.0",
            "max_sw_version": "6.9.999",
            "required_capabilities": ["CAN_FD", "Battery_BMS", "Dual_Bank_Flash"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "battery_bms_v6.2.0",
                "size_mb": 10,
                "checksum": "sha512:batt789...",
                "signature": "ECDSA_P384:batt012...",
                "compression": "lzma",
                "encryption": "AES256_GCM"
            },
            "pre_conditions": {
                "battery_level_min": 95,
                "vehicle_state": "parked_charging",
                "network_available": True,
                "ignition_off": True,
                "no_dtc_codes": True,
                "battery_temp_normal": True,
                "soc_within_range": True
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
                "run_bms_diagnostics": True,
                "cell_balancing_test": True,
                "thermal_monitoring_test": True,
                "report_telemetry": True,
                "safety_validation_asil_d": True
            }
        },
        "best_practices": [
            "Require 95%+ battery for BMS updates",
            "Ensure vehicle is parked and charging",
            "Monitor battery temperature during update",
            "Validate cell balancing post-update",
            "Keep backup bank for extended period"
        ],
        "common_issues": [
            "Temperature out of range - abort update",
            "Cell imbalance detected - automatic rollback",
            "BMS communication failure - retry with extended timeout"
        ],
        "tags": ["powertrain", "battery", "BMS", "ASIL-D", "EV", "thermal"],
        "schema_fields": [
            {
                "name": "pre_conditions.battery_temp_normal",
                "field_type": "boolean",
                "required": True
            },
            {
                "name": "post_conditions.cell_balancing_test",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "battery_level_min must be >= 95 for BMS updates",
            "battery temperature must be within 15-45°C",
            "cell balancing must pass post-update",
            "signature must use ECDSA_P384 or higher"
        ],
        "dependencies": [],
        "rollback_procedure": "Immediate rollback if any safety check fails. Vehicle enters reduced power mode. Charging disabled until manual inspection.",
        "verification_steps": [
            "Verify package signature",
            "Check battery SOC >= 95%",
            "Verify battery temperature normal",
            "Write to inactive bank",
            "Post-install: Verify boot",
            "Post-install: BMS diagnostics",
            "Post-install: Cell balancing test",
            "Post-install: ASIL-D validation"
        ],
        "estimated_duration_seconds": 500,
        "network_requirements": {
            "bandwidth_mbps": 2,
            "timeout_seconds": 900,
            "retry_count": 7,
            "connection_type": "Wired_Ethernet_only"
        }
    },

    # 3. Emergency Call System (eCall) - ASIL-B
    {
        "id": "ota_emergency_call_asil_b",
        "name": "Emergency Call System Update - ASIL-B",
        "description": "EU eCall emergency communication system with GDPR compliance",
        "use_case": "Update emergency call system with improved location accuracy and EU compliance",
        "metadata": {
            "device_type": "telematics",
            "sw_version": "3.5.0",
            "safety_class": "ASIL_B",
            "region": "EU",
            "hardware_revision": "rev_A",
            "deployment_mode": "A/B",
            "min_sw_version": "3.0.0",
            "max_sw_version": "3.9.999",
            "required_capabilities": ["4G_LTE", "GPS", "eCall_Module"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "ecall_v3.5.0_eu",
                "size_mb": 85,
                "checksum": "sha256:ecall123...",
                "signature": "RSA4096:ecall456...",
                "compression": "zstd"
            },
            "pre_conditions": {
                "battery_level_min": 70,
                "vehicle_state": "parked",
                "network_available": True,
                "gps_available": True,
                "lte_signal_strength_ok": True
            },
            "installation": {
                "target_partition": "partition_B",
                "backup_current": True,
                "verify_integrity": True,
                "reboot_required": True
            },
            "post_conditions": {
                "verify_boot": True,
                "run_ecall_diagnostics": True,
                "gps_test": True,
                "lte_connectivity_test": True,
                "gdpr_compliance_check": True,
                "report_telemetry": True,
                "safety_validation": True
            }
        },
        "best_practices": [
            "Verify LTE and GPS before update",
            "Test emergency call functionality post-update",
            "Ensure GDPR compliance for EU region",
            "Verify location accuracy within 100m"
        ],
        "common_issues": [
            "GPS signal loss - run cold start",
            "LTE connection failure - retry with fallback",
            "GDPR validation failure - rollback required"
        ],
        "tags": ["telematics", "ecall", "emergency", "ASIL-B", "EU", "GDPR"],
        "schema_fields": [
            {
                "name": "post_conditions.gdpr_compliance_check",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "gps_available must be true",
            "lte_signal_strength must be adequate",
            "gdpr_compliance_check must pass for EU region",
            "emergency call test must succeed"
        ],
        "dependencies": [],
        "rollback_procedure": "If eCall test fails, automatic rollback within 100ms. System reverts to previous version. Manual validation required.",
        "verification_steps": [
            "Verify package signature",
            "Check LTE and GPS availability",
            "Post-install: eCall functionality test",
            "Post-install: GPS accuracy verification",
            "Post-install: GDPR compliance validation"
        ],
        "estimated_duration_seconds": 600,
        "network_requirements": {
            "bandwidth_mbps": 5,
            "timeout_seconds": 1200,
            "retry_count": 5,
            "connection_type": "4G_LTE"
        }
    },

    # 4. ADAS Lane Keeping Assist - ASIL-B
    {
        "id": "ota_adas_lka_asil_b",
        "name": "ADAS Lane Keeping Assist Update - ASIL-B",
        "description": "Lane keeping assist system firmware update with camera calibration",
        "use_case": "Update LKA algorithm with improved lane detection for varying road conditions",
        "metadata": {
            "device_type": "adas",
            "sw_version": "2.8.0",
            "safety_class": "ASIL_B",
            "region": "US",
            "hardware_revision": "rev_A",
            "deployment_mode": "dual-bank",
            "min_sw_version": "2.5.0",
            "max_sw_version": "2.9.999",
            "required_capabilities": ["CAN_FD", "Camera_Interface", "ADAS_ECU"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "lka_v2.8.0",
                "size_mb": 65,
                "checksum": "sha256:lka789...",
                "signature": "RSA4096:lka012...",
                "compression": "bsdiff"
            },
            "pre_conditions": {
                "battery_level_min": 75,
                "vehicle_state": "parked",
                "network_available": True,
                "current_version_verified": True,
                "safety_diagnostics_passed": True,
                "camera_calibrated": True
            },
            "installation": {
                "apply_update": True,
                "target_partition": "bank_1",
                "backup_critical_configs": True,
                "atomic_update": True,
                "reboot_required": True
            },
            "post_conditions": {
                "verify_boot": True,
                "run_adas_diagnostics": True,
                "camera_calibration_check": True,
                "lane_detection_test": True,
                "report_telemetry": True,
                "safety_validation": True
            }
        },
        "best_practices": [
            "Verify camera calibration before update",
            "Test lane detection in various lighting conditions",
            "Run comprehensive ADAS diagnostics",
            "Ensure safety validation passes"
        ],
        "common_issues": [
            "Camera calibration drift - run auto-calibration",
            "Lane detection failure - automatic rollback",
            "Safety diagnostic failure - immediate rollback"
        ],
        "tags": ["adas", "lka", "lane-keeping", "ASIL-B", "camera"],
        "schema_fields": [
            {
                "name": "pre_conditions.camera_calibrated",
                "field_type": "boolean",
                "required": True
            },
            {
                "name": "post_conditions.lane_detection_test",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "camera_calibrated must be true before update",
            "lane_detection_test must pass post-update",
            "safety_diagnostics must pass"
        ],
        "dependencies": [],
        "rollback_procedure": "Automatic rollback if lane detection test fails. Previous version restored immediately.",
        "verification_steps": [
            "Verify camera calibration",
            "Post-install: Lane detection test",
            "Post-install: ADAS diagnostics",
            "Post-install: Safety validation"
        ],
        "estimated_duration_seconds": 550,
        "network_requirements": {
            "bandwidth_mbps": 8,
            "timeout_seconds": 1000,
            "retry_count": 5,
            "connection_type": "Ethernet or 4G_LTE"
        }
    },

    # 5. Motor ECU for EV - ASIL-D
    {
        "id": "ota_motor_ecu_asil_d",
        "name": "Motor Control ECU Update - ASIL-D",
        "description": "Electric motor control unit firmware update with torque vectoring",
        "use_case": "Update motor ECU with improved efficiency and torque control algorithms",
        "metadata": {
            "device_type": "powertrain",
            "sw_version": "5.3.0",
            "safety_class": "ASIL_D",
            "region": "CN",
            "hardware_revision": "rev_A",
            "deployment_mode": "dual-bank",
            "min_sw_version": "5.0.0",
            "max_sw_version": "5.9.999",
            "required_capabilities": ["CAN_FD", "Motor_Control", "Dual_Bank_Flash"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "motor_ecu_v5.3.0",
                "size_mb": 9,
                "checksum": "sha384:motor345...",
                "signature": "ECDSA_P384:motor678...",
                "compression": "lzma",
                "encryption": "AES256_GCM"
            },
            "pre_conditions": {
                "battery_level_min": 90,
                "vehicle_state": "parked_motor_off",
                "network_available": True,
                "ignition_off": True,
                "no_dtc_codes": True,
                "motor_temp_normal": True
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
                "run_motor_diagnostics": True,
                "torque_control_test": True,
                "efficiency_test": True,
                "report_telemetry": True,
                "safety_validation_asil_d": True
            }
        },
        "best_practices": [
            "Require 90%+ battery for motor ECU updates",
            "Ensure motor is off and cooled",
            "Verify torque control post-update",
            "Run efficiency validation tests"
        ],
        "common_issues": [
            "Motor temperature high - wait for cooling",
            "Torque control failure - automatic rollback",
            "Efficiency degradation - rollback required"
        ],
        "tags": ["powertrain", "motor", "EV", "ASIL-D", "torque-control"],
        "schema_fields": [
            {
                "name": "pre_conditions.motor_temp_normal",
                "field_type": "boolean",
                "required": True
            },
            {
                "name": "post_conditions.torque_control_test",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "motor_temp_normal must be true",
            "torque_control_test must pass",
            "efficiency must not degrade"
        ],
        "dependencies": [],
        "rollback_procedure": "Immediate rollback if motor control test fails. Vehicle enters limp mode. Manual inspection required.",
        "verification_steps": [
            "Verify motor temperature normal",
            "Post-install: Motor diagnostics",
            "Post-install: Torque control test",
            "Post-install: ASIL-D validation"
        ],
        "estimated_duration_seconds": 350,
        "network_requirements": {
            "bandwidth_mbps": 2,
            "timeout_seconds": 700,
            "retry_count": 7,
            "connection_type": "Wired_Ethernet_only"
        }
    },

    # 6. Transmission ECU - ASIL-D (for hybrid/ICE vehicles)
    {
        "id": "ota_transmission_ecu_asil_d",
        "name": "Transmission Control ECU Update - ASIL-D",
        "description": "Transmission control unit firmware update with shift optimization",
        "use_case": "Update TCU with improved shift timing and fuel efficiency",
        "metadata": {
            "device_type": "powertrain",
            "sw_version": "7.1.0",
            "safety_class": "ASIL_D",
            "region": "GLOBAL",
            "hardware_revision": "rev_A",
            "deployment_mode": "dual-bank",
            "min_sw_version": "7.0.0",
            "max_sw_version": "7.9.999",
            "required_capabilities": ["CAN_FD", "Transmission_Control", "Dual_Bank_Flash"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "transmission_v7.1.0",
                "size_mb": 7,
                "checksum": "sha384:trans123...",
                "signature": "ECDSA_P384:trans456...",
                "compression": "lzma",
                "encryption": "AES256_GCM"
            },
            "pre_conditions": {
                "battery_level_min": 90,
                "vehicle_state": "parked_engine_off",
                "network_available": True,
                "ignition_off": True,
                "no_dtc_codes": True,
                "transmission_temp_normal": True
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
                "run_transmission_diagnostics": True,
                "shift_pattern_test": True,
                "report_telemetry": True,
                "safety_validation_asil_d": True
            }
        },
        "best_practices": [
            "Ensure transmission fluid is at proper level",
            "Verify temperature is within normal range",
            "Test shift patterns post-update",
            "Run full diagnostic suite"
        ],
        "common_issues": [
            "Transmission temperature high - abort update",
            "Shift pattern test failure - automatic rollback",
            "Fluid level low - abort for safety"
        ],
        "tags": ["powertrain", "transmission", "ASIL-D", "shift-control"],
        "schema_fields": [
            {
                "name": "pre_conditions.transmission_temp_normal",
                "field_type": "boolean",
                "required": True
            },
            {
                "name": "post_conditions.shift_pattern_test",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "transmission_temp_normal must be true",
            "shift_pattern_test must pass",
            "no degradation in shift quality"
        ],
        "dependencies": [],
        "rollback_procedure": "Automatic rollback if shift test fails. Vehicle enters fail-safe mode with fixed gear. Manual inspection required.",
        "verification_steps": [
            "Verify transmission temperature",
            "Post-install: Transmission diagnostics",
            "Post-install: Shift pattern test",
            "Post-install: ASIL-D validation"
        ],
        "estimated_duration_seconds": 300,
        "network_requirements": {
            "bandwidth_mbps": 2,
            "timeout_seconds": 600,
            "retry_count": 7,
            "connection_type": "Wired_Ethernet_only"
        }
    },

    # 7. Infotainment GLOBAL region variant
    {
        "id": "ota_infotainment_global",
        "name": "Infotainment Update - Global Markets",
        "description": "Multi-region infotainment update with localization support",
        "use_case": "Deploy UI theme and features to all global markets simultaneously",
        "metadata": {
            "device_type": "infotainment",
            "sw_version": "2.5.1",
            "safety_class": "QM",
            "region": "GLOBAL",
            "hardware_revision": "rev_A",
            "deployment_mode": "A/B",
            "min_sw_version": "2.0.0",
            "max_sw_version": None,
            "required_capabilities": ["Ethernet", "4G_LTE"]
        },
        "deployment_spec": {
            "update_package": {
                "name": "infotainment_global_v2.5.1",
                "size_mb": 1400,
                "checksum": "sha256:global123...",
                "signature": "RSA2048:global456...",
                "compression": "zstd"
            },
            "pre_conditions": {
                "battery_level_min": 50,
                "vehicle_state": "parked",
                "network_available": True,
                "disk_space_mb": 3000
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
                "localization_test": True,
                "report_telemetry": True
            }
        },
        "best_practices": [
            "Verify sufficient disk space for multi-language packs",
            "Test localization for all supported regions",
            "Implement progressive download",
            "Monitor for region-specific issues"
        ],
        "common_issues": [
            "Disk space exhaustion - clean cache before download",
            "Localization loading failure - fallback to English",
            "Network interruption - resume from last chunk"
        ],
        "tags": ["infotainment", "global", "multi-region", "localization", "QM"],
        "schema_fields": [
            {
                "name": "post_conditions.localization_test",
                "field_type": "boolean",
                "required": True
            }
        ],
        "last_updated": datetime.now().isoformat() + "Z",
        "validation_rules": [
            "disk_space_mb must be >= 2x update size",
            "localization files must load correctly",
            "UI must render in all supported languages"
        ],
        "dependencies": [],
        "rollback_procedure": "If localization fails, rollback to previous version. User can manually trigger rollback via settings.",
        "verification_steps": [
            "Verify package signature",
            "Check disk space",
            "Post-install: Localization test",
            "Post-install: UI functionality verification"
        ],
        "estimated_duration_seconds": 2000,
        "network_requirements": {
            "bandwidth_mbps": 15,
            "timeout_seconds": 4000,
            "retry_count": 5,
            "connection_type": "4G_LTE or WiFi"
        }
    }
]

def expand_knowledge_base():
    """Add new patterns to the knowledge base."""
    kb_path = Path("data/ota_knowledge_base.json")

    # Load existing KB
    with open(kb_path, 'r') as f:
        kb_data = json.load(f)

    print(f"Current KB has {len(kb_data['patterns'])} patterns")

    # Add new patterns
    kb_data['patterns'].extend(new_patterns)

    print(f"Adding {len(new_patterns)} new patterns...")
    print(f"New total: {len(kb_data['patterns'])} patterns")

    # Save updated KB
    with open(kb_path, 'w') as f:
        json.dump(kb_data, f, indent=2)

    print(f"✓ Knowledge base expanded and saved to {kb_path}")

    # Print new patterns
    print("\nNew patterns added:")
    for i, pattern in enumerate(new_patterns, 1):
        print(f"{i}. {pattern['name']}")
        print(f"   - Device: {pattern['metadata']['device_type']}")
        print(f"   - Safety: {pattern['metadata']['safety_class']}")
        print(f"   - Region: {pattern['metadata']['region']}")

if __name__ == "__main__":
    expand_knowledge_base()
