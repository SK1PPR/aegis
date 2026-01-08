#!/usr/bin/env python3
"""
Simple sample script to run the NL2DSL agent.
This demonstrates how to use the agent programmatically.
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the agent and required types
from src.agent import DSLAgent
from src.knowledge_base import ECUType, SafetyClass, DeploymentMode

def main():
    """Run a simple example of the NL2DSL agent."""

    print("=" * 70)
    print("NL2DSL Agent - Sample Run")
    print("=" * 70)

    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("\n❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please create a .env file with your OpenAI API key:")
        print("  OPENAI_API_KEY=your_api_key_here")
        return

    # Initialize the agent
    print("\n📚 Initializing NL2DSL agent and loading knowledge base...")
    try:
        agent = DSLAgent()
        print("✓ Agent initialized successfully!")

        # Show knowledge base stats
        stats = agent.kb.get_statistics()
        print(f"✓ Loaded {stats['total_patterns']} OTA patterns")
        print(f"  - Device types: {len(stats['by_device_type'])}")
        print(f"  - Safety classes: {len(stats['by_safety_class'])}")
        print(f"  - Deployment modes: {len(stats['by_deployment_mode'])}")
    except Exception as e:
        print(f"❌ Error initializing agent: {e}")
        return

    # Example 1: ADAS Camera Update
    print("\n" + "=" * 70)
    print("Example 1: ADAS Camera Firmware Update for EU Market")
    print("=" * 70)

    try:
        print("\n🔍 Query: Update ADAS camera firmware to version 3.2.1 for EU vehicles")
        print("\n📋 Metadata:")
        print("  - Device Type: ADAS")
        print("  - Software Version: 3.2.1")
        print("  - Safety Class: ASIL-B")
        print("  - Region: EU")
        print("  - Hardware Revision: rev_C")
        print("  - Deployment Mode: Delta")

        print("\n⏳ Processing request through 3-stage retrieval pipeline...")

        response = agent.chat(
            user_message="Update ADAS camera firmware to version 3.2.1 for EU vehicles",
            device_type=ECUType.ADAS,
            sw_version="3.2.1",
            safety_class=SafetyClass.ASIL_B,
            region="EU",
            hardware_revision="rev_C",
            deployment_mode=DeploymentMode.DELTA
        )

        print("\n✓ Request processed!")

        # Show retrieved patterns
        if response.retrieved_patterns:
            print(f"\n📚 Retrieved {len(response.retrieved_patterns)} pattern(s):")
            for i, (pattern, score, breakdown) in enumerate(response.retrieved_patterns, 1):
                print(f"\n  Pattern {i}: {pattern.name}")
                print(f"    - Composite Score: {breakdown['composite']:.3f}")
                print(f"    - Semantic: {breakdown['semantic']:.3f}")
                print(f"    - Schema: {breakdown['schema']:.3f}")
                print(f"    - Recency: {breakdown['recency']:.3f}")
                print(f"    - Validation: {breakdown['validation']:.3f}")

        # Show agent message
        print(f"\n💬 Agent Response:")
        print(f"  {response.message}")

        # Show generated deployment spec
        if response.deployment_spec:
            print(f"\n📝 Generated Deployment Specification:")
            print(json.dumps(response.deployment_spec, indent=2))

            # Save to file
            output_file = Path("results") / "sample_adas_deployment.json"
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                json.dump(response.deployment_spec, f, indent=2)
            print(f"\n💾 Saved deployment spec to: {output_file}")
        else:
            print("\n⚠️  No deployment specification generated")

    except Exception as e:
        print(f"\n❌ Error processing request: {e}")
        import traceback
        traceback.print_exc()

    # Example 2: Infotainment Update
    print("\n" + "=" * 70)
    print("Example 2: Infotainment Full Update for US Market")
    print("=" * 70)

    try:
        print("\n🔍 Query: Deploy full infotainment system update with new UI features")
        print("\n📋 Metadata:")
        print("  - Device Type: Infotainment")
        print("  - Software Version: 2.0.0")
        print("  - Safety Class: QM (Quality Managed)")
        print("  - Region: US")
        print("  - Hardware Revision: rev_B")
        print("  - Deployment Mode: A/B")

        print("\n⏳ Processing request...")

        response = agent.chat(
            user_message="Deploy full infotainment system update with new UI features and navigation maps",
            device_type=ECUType.INFOTAINMENT,
            sw_version="2.0.0",
            safety_class=SafetyClass.QM,
            region="US",
            hardware_revision="rev_B",
            deployment_mode=DeploymentMode.A_B
        )

        print("\n✓ Request processed!")

        # Show retrieved patterns
        if response.retrieved_patterns:
            print(f"\n📚 Retrieved {len(response.retrieved_patterns)} pattern(s):")
            for i, (pattern, score, breakdown) in enumerate(response.retrieved_patterns, 1):
                print(f"\n  Pattern {i}: {pattern.name}")
                print(f"    - Composite Score: {breakdown['composite']:.3f}")

        # Show generated deployment spec
        if response.deployment_spec:
            print(f"\n📝 Generated Deployment Specification Preview:")
            # Just show the structure
            print(f"  - update_package: {list(response.deployment_spec.get('update_package', {}).keys())}")
            print(f"  - pre_conditions: {list(response.deployment_spec.get('pre_conditions', {}).keys())}")
            print(f"  - installation: {list(response.deployment_spec.get('installation', {}).keys())}")
            print(f"  - post_conditions: {list(response.deployment_spec.get('post_conditions', {}).keys())}")

            # Save to file
            output_file = Path("results") / "sample_infotainment_deployment.json"
            with open(output_file, 'w') as f:
                json.dump(response.deployment_spec, f, indent=2)
            print(f"\n💾 Saved deployment spec to: {output_file}")
        else:
            print("\n⚠️  No deployment specification generated")

    except Exception as e:
        print(f"\n❌ Error processing request: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 70)
    print("✓ Sample run completed!")
    print("=" * 70)
    print("\nNext steps:")
    print("  1. Check the results/ directory for generated deployment specs")
    print("  2. Run 'python main.py' for interactive mode")
    print("  3. Run 'python run_ota_benchmark.py' for full evaluation")
    print()


if __name__ == "__main__":
    main()
