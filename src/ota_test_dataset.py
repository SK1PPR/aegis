#!/usr/bin/env python3
"""OTA-specific test dataset generator for benchmarking nl2dsl agent against other OTA systems."""

from typing import List, Dict, Any
from dataclasses import dataclass
from enum import Enum


class OTACategory(Enum):
    """OTA update categories."""
    SINGLE_ECU = "single_ecu"
    MULTI_ECU = "multi_ecu"
    SAFETY_CRITICAL = "safety_critical"
    INFOTAINMENT = "infotainment"
    ADAS = "adas"
    POWERTRAIN = "powertrain"
    REGIONAL = "regional"
    ROLLBACK = "rollback"
    DELTA_UPDATE = "delta_update"
    FULL_UPDATE = "full_update"


class OTAComplexity(Enum):
    """Complexity levels for OTA updates."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


@dataclass
class OTATestCase:
    """Test case for OTA deployment."""
    id: str
    category: OTACategory
    complexity: OTAComplexity
    prompt: str
    expected_ecus: List[str]
    expected_attributes: Dict[str, List[str]]
    safety_class: str
    region: str
    description: str


class OTATestDatasetGenerator:
    """Generate comprehensive OTA test scenarios."""

    def __init__(self):
        self.test_cases: List[OTATestCase] = []
        self._generate_all_cases()

    def _generate_all_cases(self):
        """Generate all test cases."""
        self._generate_single_ecu_cases()
        self._generate_multi_ecu_cases()
        self._generate_safety_critical_cases()
        self._generate_infotainment_cases()
        self._generate_adas_cases()
        self._generate_powertrain_cases()
        self._generate_regional_cases()
        self._generate_rollback_cases()
        self._generate_delta_update_cases()

    def _generate_single_ecu_cases(self):
        """Single ECU update scenarios."""
        cases = [
            OTATestCase(
                id="ota_001",
                category=OTACategory.SINGLE_ECU,
                complexity=OTAComplexity.SIMPLE,
                prompt="Update infotainment firmware to version 2.5.1 for US market",
                expected_ecus=["infotainment"],
                expected_attributes={
                    "infotainment": ["sw_version", "region", "deployment_mode", "update_package"]
                },
                safety_class="QM",
                region="US",
                description="Simple single ECU update for non-safety-critical system"
            ),
            OTATestCase(
                id="ota_002",
                category=OTACategory.SINGLE_ECU,
                complexity=OTAComplexity.MEDIUM,
                prompt="Deploy ADAS camera software v3.2.0 with pre-condition checks for EU vehicles",
                expected_ecus=["adas_camera"],
                expected_attributes={
                    "adas_camera": ["sw_version", "region", "pre_conditions", "verification"]
                },
                safety_class="ASIL-B",
                region="EU",
                description="Medium complexity with safety checks"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_multi_ecu_cases(self):
        """Multi-ECU update scenarios."""
        cases = [
            OTATestCase(
                id="ota_010",
                category=OTACategory.MULTI_ECU,
                complexity=OTAComplexity.COMPLEX,
                prompt="Update both ADAS radar and camera ECUs simultaneously for China market with coordinated rollout",
                expected_ecus=["adas_radar", "adas_camera"],
                expected_attributes={
                    "adas_radar": ["sw_version", "region", "deployment_order"],
                    "adas_camera": ["sw_version", "region", "deployment_order"]
                },
                safety_class="ASIL-B",
                region="CN",
                description="Coordinated multi-ECU update"
            ),
            OTATestCase(
                id="ota_011",
                category=OTACategory.MULTI_ECU,
                complexity=OTAComplexity.VERY_COMPLEX,
                prompt="Orchestrate gateway, telematics, and infotainment update with dependency management",
                expected_ecus=["gateway", "telematics", "infotainment"],
                expected_attributes={
                    "gateway": ["sw_version", "dependencies", "deployment_order"],
                    "telematics": ["sw_version", "dependencies", "deployment_order"],
                    "infotainment": ["sw_version", "dependencies", "deployment_order"]
                },
                safety_class="ASIL-A",
                region="US",
                description="Complex multi-ECU with dependencies"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_safety_critical_cases(self):
        """Safety-critical update scenarios."""
        cases = [
            OTATestCase(
                id="ota_020",
                category=OTACategory.SAFETY_CRITICAL,
                complexity=OTAComplexity.COMPLEX,
                prompt="Update powertrain control unit ASIL-D with full safety verification and rollback capability",
                expected_ecus=["powertrain_ecu"],
                expected_attributes={
                    "powertrain_ecu": [
                        "sw_version", "safety_class", "pre_conditions",
                        "verification", "rollback_procedure", "safety_checks"
                    ]
                },
                safety_class="ASIL-D",
                region="US",
                description="Highest safety level update"
            ),
            OTATestCase(
                id="ota_021",
                category=OTACategory.SAFETY_CRITICAL,
                complexity=OTAComplexity.VERY_COMPLEX,
                prompt="Deploy brake control ECU update ASIL-C with vehicle state validation and staged rollout",
                expected_ecus=["brake_ecu"],
                expected_attributes={
                    "brake_ecu": [
                        "sw_version", "safety_class", "pre_conditions",
                        "vehicle_state_check", "staged_deployment", "rollback_procedure"
                    ]
                },
                safety_class="ASIL-C",
                region="EU",
                description="Safety-critical brake system update"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_infotainment_cases(self):
        """Infotainment system scenarios."""
        cases = [
            OTATestCase(
                id="ota_030",
                category=OTACategory.INFOTAINMENT,
                complexity=OTAComplexity.SIMPLE,
                prompt="Push new UI theme to infotainment system for global markets",
                expected_ecus=["infotainment"],
                expected_attributes={
                    "infotainment": ["sw_version", "deployment_mode", "region"]
                },
                safety_class="QM",
                region="GLOBAL",
                description="Simple cosmetic update"
            ),
            OTATestCase(
                id="ota_031",
                category=OTACategory.INFOTAINMENT,
                complexity=OTAComplexity.MEDIUM,
                prompt="Update navigation maps and multimedia codecs for infotainment in EU region",
                expected_ecus=["infotainment"],
                expected_attributes={
                    "infotainment": ["sw_version", "data_packages", "region", "storage_requirements"]
                },
                safety_class="QM",
                region="EU",
                description="Data and software update"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_adas_cases(self):
        """ADAS system scenarios."""
        cases = [
            OTATestCase(
                id="ota_040",
                category=OTACategory.ADAS,
                complexity=OTAComplexity.COMPLEX,
                prompt="Deploy lane keeping assist algorithm update with sensor calibration for US vehicles ASIL-B",
                expected_ecus=["adas_lka"],
                expected_attributes={
                    "adas_lka": [
                        "sw_version", "safety_class", "calibration_required",
                        "pre_conditions", "verification"
                    ]
                },
                safety_class="ASIL-B",
                region="US",
                description="ADAS algorithm update with calibration"
            ),
            OTATestCase(
                id="ota_041",
                category=OTACategory.ADAS,
                complexity=OTAComplexity.VERY_COMPLEX,
                prompt="Update complete ADAS suite including radar, camera, and lidar fusion for autonomous driving L3",
                expected_ecus=["adas_radar", "adas_camera", "adas_lidar", "adas_fusion"],
                expected_attributes={
                    "adas_radar": ["sw_version", "safety_class", "synchronization"],
                    "adas_camera": ["sw_version", "safety_class", "synchronization"],
                    "adas_lidar": ["sw_version", "safety_class", "synchronization"],
                    "adas_fusion": ["sw_version", "safety_class", "dependencies"]
                },
                safety_class="ASIL-B",
                region="EU",
                description="Full ADAS stack update"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_powertrain_cases(self):
        """Powertrain system scenarios."""
        cases = [
            OTATestCase(
                id="ota_050",
                category=OTACategory.POWERTRAIN,
                complexity=OTAComplexity.COMPLEX,
                prompt="Update engine control unit with new fuel efficiency calibration ASIL-D",
                expected_ecus=["engine_ecu"],
                expected_attributes={
                    "engine_ecu": [
                        "sw_version", "safety_class", "calibration_data",
                        "pre_conditions", "rollback_procedure"
                    ]
                },
                safety_class="ASIL-D",
                region="US",
                description="Engine ECU calibration update"
            ),
            OTATestCase(
                id="ota_051",
                category=OTACategory.POWERTRAIN,
                complexity=OTAComplexity.VERY_COMPLEX,
                prompt="Deploy electric vehicle battery management and motor control update with thermal monitoring",
                expected_ecus=["battery_ecu", "motor_ecu"],
                expected_attributes={
                    "battery_ecu": ["sw_version", "safety_class", "thermal_limits", "rollback_procedure"],
                    "motor_ecu": ["sw_version", "safety_class", "dependencies", "verification"]
                },
                safety_class="ASIL-D",
                region="CN",
                description="EV powertrain update"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_regional_cases(self):
        """Region-specific scenarios."""
        cases = [
            OTATestCase(
                id="ota_060",
                category=OTACategory.REGIONAL,
                complexity=OTAComplexity.MEDIUM,
                prompt="Update telematics for China market with local connectivity protocols and compliance",
                expected_ecus=["telematics"],
                expected_attributes={
                    "telematics": ["sw_version", "region", "compliance_requirements", "connectivity"]
                },
                safety_class="QM",
                region="CN",
                description="China-specific telematics update"
            ),
            OTATestCase(
                id="ota_061",
                category=OTACategory.REGIONAL,
                complexity=OTAComplexity.MEDIUM,
                prompt="Deploy EU eCall emergency system update with GDPR compliance",
                expected_ecus=["emergency_call"],
                expected_attributes={
                    "emergency_call": ["sw_version", "region", "gdpr_compliance", "testing_required"]
                },
                safety_class="ASIL-B",
                region="EU",
                description="EU eCall system update"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_rollback_cases(self):
        """Rollback scenario testing."""
        cases = [
            OTATestCase(
                id="ota_070",
                category=OTACategory.ROLLBACK,
                complexity=OTAComplexity.COMPLEX,
                prompt="Rollback ADAS camera firmware from v3.2.0 to v3.1.5 due to detection issues",
                expected_ecus=["adas_camera"],
                expected_attributes={
                    "adas_camera": [
                        "sw_version", "rollback_version", "rollback_reason",
                        "safety_class", "verification"
                    ]
                },
                safety_class="ASIL-B",
                region="US",
                description="Safety-critical rollback scenario"
            ),
            OTATestCase(
                id="ota_071",
                category=OTACategory.ROLLBACK,
                complexity=OTAComplexity.VERY_COMPLEX,
                prompt="Emergency rollback of multi-ECU powertrain update with coordinated recovery",
                expected_ecus=["engine_ecu", "transmission_ecu"],
                expected_attributes={
                    "engine_ecu": ["sw_version", "rollback_version", "emergency_mode"],
                    "transmission_ecu": ["sw_version", "rollback_version", "synchronization"]
                },
                safety_class="ASIL-D",
                region="GLOBAL",
                description="Multi-ECU emergency rollback"
            ),
        ]
        self.test_cases.extend(cases)

    def _generate_delta_update_cases(self):
        """Delta/differential update scenarios."""
        cases = [
            OTATestCase(
                id="ota_080",
                category=OTACategory.DELTA_UPDATE,
                complexity=OTAComplexity.MEDIUM,
                prompt="Apply delta patch to infotainment v2.5.0->v2.5.1 to save bandwidth",
                expected_ecus=["infotainment"],
                expected_attributes={
                    "infotainment": [
                        "sw_version", "delta_patch", "bandwidth_optimization",
                        "checksum_verification"
                    ]
                },
                safety_class="QM",
                region="US",
                description="Bandwidth-efficient delta update"
            ),
            OTATestCase(
                id="ota_081",
                category=OTACategory.DELTA_UPDATE,
                complexity=OTAComplexity.COMPLEX,
                prompt="Deploy differential update for ADAS radar with A/B partition switching",
                expected_ecus=["adas_radar"],
                expected_attributes={
                    "adas_radar": [
                        "sw_version", "delta_patch", "partition_switching",
                        "rollback_partition", "safety_class"
                    ]
                },
                safety_class="ASIL-B",
                region="EU",
                description="Delta update with A/B partitioning"
            ),
        ]
        self.test_cases.extend(cases)

    def get_all_cases(self) -> List[OTATestCase]:
        """Get all test cases."""
        return self.test_cases

    def get_by_category(self, category: OTACategory) -> List[OTATestCase]:
        """Get test cases by category."""
        return [tc for tc in self.test_cases if tc.category == category]

    def get_by_complexity(self, complexity: OTAComplexity) -> List[OTATestCase]:
        """Get test cases by complexity."""
        return [tc for tc in self.test_cases if tc.complexity == complexity]

    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        return {
            "total_cases": len(self.test_cases),
            "by_category": {cat.value: len(self.get_by_category(cat))
                           for cat in OTACategory},
            "by_complexity": {comp.value: len(self.get_by_complexity(comp))
                            for comp in OTAComplexity},
            "safety_critical_count": len([tc for tc in self.test_cases
                                         if tc.safety_class.startswith("ASIL")]),
            "multi_ecu_count": len([tc for tc in self.test_cases
                                   if len(tc.expected_ecus) > 1]),
        }

    def save_to_json(self, filename: str):
        """Save dataset to JSON file."""
        import json
        from dataclasses import asdict

        data = {
            "metadata": {
                "version": "1.0",
                "description": "OTA test dataset for nl2dsl agent benchmarking",
                "total_cases": len(self.test_cases)
            },
            "statistics": self.get_statistics(),
            "test_cases": [
                {
                    **asdict(tc),
                    "category": tc.category.value,
                    "complexity": tc.complexity.value
                }
                for tc in self.test_cases
            ]
        }

        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)


if __name__ == "__main__":
    from rich.console import Console

    console = Console()

    console.print("\n[bold cyan]OTA Test Dataset Generator[/bold cyan]\n")

    generator = OTATestDatasetGenerator()
    stats = generator.get_statistics()

    console.print(f"Generated {stats['total_cases']} test cases")
    console.print(f"\nBy Category:")
    for cat, count in stats['by_category'].items():
        console.print(f"  {cat}: {count}")

    console.print(f"\nBy Complexity:")
    for comp, count in stats['by_complexity'].items():
        console.print(f"  {comp}: {count}")

    console.print(f"\nSafety-critical: {stats['safety_critical_count']}")
    console.print(f"Multi-ECU: {stats['multi_ecu_count']}")

    # Save to file
    generator.save_to_json("ota_test_dataset.json")
    console.print(f"\n✓ Saved to ota_test_dataset.json")
