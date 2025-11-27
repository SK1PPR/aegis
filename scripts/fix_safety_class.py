#!/usr/bin/env python3
"""
Fix safety_class format in ota_knowledge_base.json.
Convert ASIL-X to ASIL_X to match the SafetyClass enum.
"""

import json


def fix_safety_class():
    """Fix the safety_class format."""

    print("Fixing safety_class format in ota_knowledge_base.json...")

    # Load the knowledge base
    with open('ota_knowledge_base.json', 'r') as f:
        kb_data = json.load(f)

    # Fix each pattern
    fixed_count = 0
    for pattern in kb_data['patterns']:
        if 'metadata' in pattern and 'safety_class' in pattern['metadata']:
            safety_class = pattern['metadata']['safety_class']
            # Convert ASIL-X to ASIL_X
            if '-' in safety_class:
                pattern['metadata']['safety_class'] = safety_class.replace('-', '_')
                fixed_count += 1
                print(f"  Fixed: {safety_class} -> {pattern['metadata']['safety_class']}")

    # Save the fixed knowledge base
    with open('ota_knowledge_base.json', 'w') as f:
        json.dump(kb_data, f, indent=2)

    print(f"\n✓ Fixed {fixed_count} safety_class values")
    print(f"✓ Saved to ota_knowledge_base.json")


if __name__ == "__main__":
    fix_safety_class()
