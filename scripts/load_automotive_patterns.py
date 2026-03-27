#!/usr/bin/env python3
"""Load automotive OTA patterns into the knowledge base."""

import json
from knowledge_base import (
    OTAKnowledgeBase,
    OTADeploymentPattern,
    OTAMetadata,
    SchemaField,
    ECUType,
    SafetyClass,
    DeploymentMode
)


def map_device_type(device_str: str) -> ECUType:
    """Map string device type to ECUType enum."""
    mapping = {
        "infotainment": ECUType.INFOTAINMENT,
        "adas": ECUType.ADAS,
        "powertrain": ECUType.POWERTRAIN,
        "telematics": ECUType.TELEMATICS,
        "gateway": ECUType.GATEWAY,
        "body_control": ECUType.BODY_CONTROL
    }
    return mapping.get(device_str.lower(), ECUType.INFOTAINMENT)


def map_safety_class(safety_str: str) -> SafetyClass:
    """Map string safety class to SafetyClass enum."""
    mapping = {
        "QM": SafetyClass.QM,
        "ASIL-A": SafetyClass.ASIL_A,
        "ASIL-B": SafetyClass.ASIL_B,
        "ASIL-C": SafetyClass.ASIL_C,
        "ASIL-D": SafetyClass.ASIL_D
    }
    return mapping.get(safety_str, SafetyClass.QM)


def map_deployment_mode(mode_str: str) -> DeploymentMode:
    """Map string deployment mode to DeploymentMode enum."""
    mapping = {
        "A/B": DeploymentMode.A_B,
        "dual-bank": DeploymentMode.DUAL_BANK,
        "single-bank": DeploymentMode.SINGLE_BANK,
        "delta": DeploymentMode.DELTA,
        "full": DeploymentMode.FULL
    }
    return mapping.get(mode_str, DeploymentMode.A_B)


def load_automotive_patterns(patterns_file: str = "automotive_ota_patterns.json"):
    """Load automotive OTA patterns from JSON file."""

    print(f"Loading automotive OTA patterns from {patterns_file}...")

    with open(patterns_file, 'r') as f:
        data = json.load(f)

    kb = OTAKnowledgeBase()
    patterns_loaded = 0

    for pattern_data in data['patterns']:
        try:
            # Create metadata
            metadata = OTAMetadata(
                device_type=map_device_type(pattern_data['metadata']['device_type']),
                sw_version=pattern_data['metadata']['sw_version'],
                safety_class=map_safety_class(pattern_data['metadata']['safety_class']),
                region=pattern_data['metadata']['region'],
                hardware_revision=pattern_data['metadata']['hardware_revision'],
                deployment_mode=map_deployment_mode(pattern_data['metadata']['deployment_mode'])
            )

            # Create schema fields
            schema_fields = []
            for field_data in pattern_data.get('schema_fields', []):
                schema_field = SchemaField(
                    name=field_data['name'],
                    field_type=field_data['type'],
                    required=field_data['required'],
                    description=field_data.get('description', ''),
                    validation_pattern=field_data.get('validation_pattern')
                )
                schema_fields.append(schema_field)

            # Create pattern
            pattern = OTADeploymentPattern(
                name=pattern_data['name'],
                description=pattern_data['description'],
                metadata=metadata,
                deployment_spec=pattern_data['deployment_spec'],
                schema_fields=schema_fields,
                validation_rules=pattern_data.get('validation_rules', []),
                rollback_procedure=pattern_data['deployment_spec'].get('rollback_procedure', {}),
                best_practices=pattern_data.get('best_practices', [])
            )

            # Add to knowledge base
            kb.add_pattern(pattern)
            patterns_loaded += 1
            print(f"  ✓ Loaded: {pattern.name}")

        except Exception as e:
            print(f"  ✗ Error loading pattern '{pattern_data.get('name', 'unknown')}': {e}")
            continue

    print(f"\n✓ Successfully loaded {patterns_loaded} automotive OTA patterns")

    # Save the updated knowledge base
    kb.save_to_file("ota_knowledge_base.json")
    print(f"✓ Saved to ota_knowledge_base.json")

    return kb


if __name__ == "__main__":
    kb = load_automotive_patterns()

    # Display statistics
    print("\n" + "="*60)
    print("Knowledge Base Statistics:")
    print("="*60)
    print(f"Total patterns: {len(kb.patterns)}")

    by_device = {}
    by_safety = {}
    by_region = {}

    for pattern in kb.patterns:
        device = pattern.metadata.device_type.value
        safety = pattern.metadata.safety_class.value
        region = pattern.metadata.region

        by_device[device] = by_device.get(device, 0) + 1
        by_safety[safety] = by_safety.get(safety, 0) + 1
        by_region[region] = by_region.get(region, 0) + 1

    print(f"\nBy Device Type:")
    for device, count in sorted(by_device.items()):
        print(f"  {device}: {count}")

    print(f"\nBy Safety Class:")
    for safety, count in sorted(by_safety.items()):
        print(f"  {safety}: {count}")

    print(f"\nBy Region:")
    for region, count in sorted(by_region.items()):
        print(f"  {region}: {count}")

    print("\n" + "="*60)
    print("Automotive OTA patterns loaded successfully!")
    print("Ready to run benchmark: python run_ota_benchmark.py")
    print("="*60)
