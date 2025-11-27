#!/usr/bin/env python3
"""
Convert automotive OTA patterns to knowledge base format.
This script reads automotive_ota_patterns.json and converts it to the format
required by ota_knowledge_base.json for the retrieval database.
"""

import json
from datetime import datetime
from typing import Dict, List, Any


def extract_tags(pattern: Dict) -> List[str]:
    """Extract tags from pattern metadata and description."""
    tags = []

    # Add device type
    device_type = pattern['metadata']['device_type']
    tags.append(device_type)

    # Add safety class
    safety_class = pattern['metadata']['safety_class']
    tags.append(safety_class)

    # Add deployment mode
    deployment_mode = pattern['metadata']['deployment_mode']
    tags.append(deployment_mode)

    # Add region
    region = pattern['metadata']['region']
    tags.append(region)

    # Extract keywords from description
    description_lower = pattern['description'].lower()

    if 'update' in description_lower:
        if 'full' in description_lower or 'complete' in description_lower:
            tags.append('full-update')
        elif 'delta' in description_lower or 'incremental' in description_lower or 'patch' in description_lower:
            tags.append('delta-update')

    if 'safety' in description_lower or 'critical' in description_lower:
        tags.append('safety-critical')

    if 'multi' in description_lower or 'coordinated' in description_lower:
        tags.append('multi-ecu')

    if 'rollback' in description_lower or 'emergency' in description_lower:
        tags.append('rollback')

    # Add specific ECU types
    if 'camera' in description_lower:
        tags.append('camera')
    if 'radar' in description_lower:
        tags.append('radar')
    if 'engine' in description_lower:
        tags.append('engine-control')
    if 'emissions' in description_lower:
        tags.append('emissions')
    if 'cloud' in description_lower:
        tags.append('cloud')

    return list(set(tags))  # Remove duplicates


def extract_common_issues(pattern: Dict) -> List[str]:
    """Extract common issues from deployment spec or create generic ones."""
    issues = []

    device_type = pattern['metadata']['device_type']
    deployment_mode = pattern['metadata']['deployment_mode']
    safety_class = pattern['metadata']['safety_class']

    # Generic issues based on device type
    if device_type == 'infotainment':
        issues.append("Network interruption during download - implement chunked transfer with retry")
        issues.append("Insufficient disk space - clean temp files before update")
        issues.append("Boot verification failure - automatic rollback to previous partition")

    elif device_type == 'adas':
        issues.append("Camera calibration drift - run auto-calibration post-update")
        issues.append("Sensor fusion mismatch - verify inter-ECU communication")
        issues.append("CAN bus timeout during reboot - implement watchdog with extended timeout")

    elif device_type == 'powertrain':
        issues.append("Flash write failure - automatically retry on backup bank")
        issues.append("DTC codes present - abort update until cleared")
        issues.append("Emissions test failure - automatic rollback mandatory")

    elif device_type == 'telematics':
        issues.append("Network connection drop - implement resume from last chunk")
        issues.append("Cloud API timeout - retry with exponential backoff")
        issues.append("GPS signal loss after update - run GPS cold start")

    elif device_type == 'gateway':
        issues.append("ECU communication loss - verify all nodes responsive")
        issues.append("Routing table corruption - restore from backup")
        issues.append("CAN bus timeout - implement extended watchdog")

    # Safety-specific issues
    if safety_class in ['ASIL-B', 'ASIL-C', 'ASIL-D']:
        issues.append("Safety diagnostic failure - automatic rollback mandatory")
        issues.append("Version mismatch - strict version validation required")

    # Deployment mode specific
    if deployment_mode == 'delta':
        issues.append("Delta patch corruption - verify checksum before and after application")
        issues.append("Base version mismatch - strict base version validation required")

    return issues


def extract_verification_steps(pattern: Dict) -> List[str]:
    """Extract verification steps from deployment spec."""
    steps = []

    deployment_spec = pattern['deployment_spec']

    # Pre-conditions checks
    if 'pre_conditions' in deployment_spec:
        pre_cond = deployment_spec['pre_conditions']

        steps.append("Verify package signature")

        if 'battery_level_min' in pre_cond:
            steps.append(f"Check battery level >= {pre_cond['battery_level_min']}%")

        if 'vehicle_state' in pre_cond:
            steps.append(f"Confirm vehicle in {pre_cond['vehicle_state']} state")

        if 'available_storage_mb' in pre_cond:
            steps.append("Check disk space availability")

        if 'safety_checks' in pre_cond:
            steps.append("Run pre-update safety diagnostics")

        if 'no_dtc_codes' in pre_cond.get('safety_checks', {}):
            steps.append("Verify no DTC codes")

    # Installation steps
    if 'installation' in deployment_spec:
        install = deployment_spec['installation']

        if install.get('method') == 'delta':
            steps.append("Apply delta patch atomically")
        elif install.get('method') in ['A/B', 'dual-bank']:
            steps.append("Write to inactive partition/bank with verification")

    # Post-conditions checks
    if 'post_conditions' in deployment_spec:
        post_cond = deployment_spec['post_conditions']

        steps.append("Post-install: Verify boot")

        if 'verification' in post_cond:
            verif = post_cond['verification']

            if 'functional_test' in verif:
                for test in verif['functional_test']:
                    steps.append(f"Post-install: Test {test}")

            if 'safety_validation' in verif:
                steps.append("Post-install: Safety validation complete")

            if 'calibration_check' in verif:
                steps.append("Post-install: Calibration verification")

    return steps


def calculate_estimated_duration(pattern: Dict) -> int:
    """Estimate update duration in seconds based on package size and complexity."""
    deployment_spec = pattern['deployment_spec']

    # Get package size
    package_size = deployment_spec['update_package'].get('package_size_mb', 100)

    # Base time for download (assuming 10 Mbps)
    download_time = (package_size * 8) / 10  # seconds

    # Installation time (varies by type)
    installation_time = 300  # default 5 minutes

    device_type = pattern['metadata']['device_type']
    if device_type == 'infotainment':
        installation_time = 600  # 10 minutes
    elif device_type in ['adas', 'powertrain']:
        installation_time = 300  # 5 minutes
    elif device_type == 'telematics':
        installation_time = 400  # ~7 minutes

    # Add verification time
    verification_time = 120  # 2 minutes

    return int(download_time + installation_time + verification_time)


def convert_pattern(pattern: Dict, pattern_id: str) -> Dict:
    """Convert a single automotive pattern to knowledge base format."""

    kb_pattern = {
        "id": pattern_id,
        "name": pattern['name'],
        "description": pattern['description'],
        "use_case": pattern['description'],  # Use description as use case
        "metadata": {
            "device_type": pattern['metadata']['device_type'],
            "sw_version": pattern['metadata']['sw_version'],
            "safety_class": pattern['metadata']['safety_class'],
            "region": pattern['metadata']['region'],
            "hardware_revision": pattern['metadata']['hardware_revision'],
            "deployment_mode": pattern['metadata']['deployment_mode'],
            "min_sw_version": None,
            "max_sw_version": None,
            "required_capabilities": []
        },
        "deployment_spec": pattern['deployment_spec'],
        "best_practices": pattern.get('best_practices', []),
        "common_issues": extract_common_issues(pattern),
        "tags": extract_tags(pattern),
        "schema_fields": pattern.get('schema_fields', []),
        "last_updated": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "validation_rules": pattern.get('validation_rules', []),
        "dependencies": [],
        "rollback_procedure": pattern['deployment_spec'].get('rollback_procedure', {}).get('enabled', False),
        "verification_steps": extract_verification_steps(pattern),
        "estimated_duration_seconds": calculate_estimated_duration(pattern),
        "network_requirements": {
            "bandwidth_mbps": 10,
            "timeout_seconds": 1800,
            "retry_count": 3,
            "connection_type": "4G_LTE or WiFi"
        }
    }

    # Convert rollback_procedure from dict/bool to string
    if isinstance(kb_pattern['rollback_procedure'], bool):
        if kb_pattern['rollback_procedure']:
            safety_class = pattern['metadata']['safety_class']
            if safety_class in ['ASIL-B', 'ASIL-C', 'ASIL-D']:
                kb_pattern['rollback_procedure'] = f"{safety_class} requires automatic rollback if any safety check fails. Previous version restored from backup partition. Vehicle enters safe mode until validation."
            else:
                kb_pattern['rollback_procedure'] = "Automatic rollback enabled on failure. Previous version restored from backup partition within specified timeout."
        else:
            kb_pattern['rollback_procedure'] = "Manual rollback only."
    elif isinstance(kb_pattern['rollback_procedure'], dict):
        # Convert dict to descriptive string
        rollback_dict = kb_pattern['rollback_procedure']
        if rollback_dict.get('enabled'):
            max_attempts = rollback_dict.get('max_attempts', 3)
            fallback_version = rollback_dict.get('fallback_version', 'previous')
            kb_pattern['rollback_procedure'] = f"Automatic rollback enabled with max {max_attempts} attempts. Falls back to version {fallback_version}."
        else:
            kb_pattern['rollback_procedure'] = "Rollback not enabled."

    return kb_pattern


def main():
    """Main conversion function."""
    print("Converting automotive OTA patterns to knowledge base format...")
    print("=" * 70)

    # Load automotive patterns
    with open('automotive_ota_patterns.json', 'r') as f:
        automotive_data = json.load(f)

    # Load existing knowledge base (if exists)
    try:
        with open('ota_knowledge_base.json', 'r') as f:
            kb_data = json.load(f)
    except FileNotFoundError:
        kb_data = {"patterns": []}

    print(f"Found {len(automotive_data['patterns'])} automotive patterns")
    print(f"Existing knowledge base has {len(kb_data['patterns'])} patterns")

    # Get existing pattern IDs to avoid duplicates
    existing_ids = {p['id'] for p in kb_data['patterns']}

    # Convert and add new patterns
    new_patterns = []
    for i, pattern in enumerate(automotive_data['patterns'], 1):
        # Generate pattern ID
        device_type = pattern['metadata']['device_type']
        pattern_id = f"ota_{device_type}_{pattern['name'].lower().replace(' ', '_').replace('-', '_')}"

        # Check for duplicates
        if pattern_id in existing_ids:
            print(f"  ⊙ Skipping duplicate: {pattern['name']}")
            continue

        # Convert pattern
        kb_pattern = convert_pattern(pattern, pattern_id)
        new_patterns.append(kb_pattern)
        print(f"  ✓ Converted: {kb_pattern['name']}")

    # Add new patterns to knowledge base
    kb_data['patterns'].extend(new_patterns)

    # Save updated knowledge base
    with open('ota_knowledge_base.json', 'w') as f:
        json.dump(kb_data, f, indent=2)

    print("\n" + "=" * 70)
    print(f"✓ Successfully added {len(new_patterns)} new patterns")
    print(f"✓ Total patterns in knowledge base: {len(kb_data['patterns'])}")
    print(f"✓ Saved to ota_knowledge_base.json")

    # Display statistics
    print("\n" + "=" * 70)
    print("Knowledge Base Statistics:")
    print("=" * 70)

    by_device = {}
    by_safety = {}
    by_region = {}

    for pattern in kb_data['patterns']:
        device = pattern['metadata']['device_type']
        safety = pattern['metadata']['safety_class']
        region = pattern['metadata']['region']

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

    print("\n" + "=" * 70)
    print("Conversion complete! OTA patterns ready for retrieval database.")
    print("=" * 70)


if __name__ == "__main__":
    main()
