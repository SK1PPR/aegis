#!/usr/bin/env python3
"""
Fix schema_fields in ota_knowledge_base.json to use 'field_type' instead of 'type'.
"""

import json


def fix_schema_fields():
    """Fix the schema_fields structure."""

    print("Fixing schema_fields in ota_knowledge_base.json...")

    # Load the knowledge base
    with open('ota_knowledge_base.json', 'r') as f:
        kb_data = json.load(f)

    # Fix each pattern
    fixed_count = 0
    for pattern in kb_data['patterns']:
        if 'schema_fields' in pattern:
            for field in pattern['schema_fields']:
                # If 'type' exists, rename it to 'field_type'
                if 'type' in field:
                    field['field_type'] = field.pop('type')
                    fixed_count += 1

    # Save the fixed knowledge base
    with open('ota_knowledge_base.json', 'w') as f:
        json.dump(kb_data, f, indent=2)

    print(f"✓ Fixed {fixed_count} schema fields")
    print(f"✓ Saved to ota_knowledge_base.json")


if __name__ == "__main__":
    fix_schema_fields()
