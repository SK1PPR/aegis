#!/usr/bin/env python3
"""Simple test to check if the agent is working."""

from agent import DSLAgent
from knowledge_base import ECUType, SafetyClass, DeploymentMode


def test_agent():
    print("Testing DSL Agent...")
    print("=" * 70)

    try:
        # Initialize agent
        print("\n1. Initializing agent...")
        agent = DSLAgent()
        print("   ✓ Agent initialized")

        # Test a simple query
        print("\n2. Testing simple OTA update request...")
        response = agent.chat(
            user_message="Update infotainment firmware to version 2.5.1 for US market",
            device_type=ECUType.INFOTAINMENT,
            sw_version="2.5.1",
            safety_class=SafetyClass.QM,
            region="US",
            hardware_revision="rev_A",
            deployment_mode=DeploymentMode.A_B
        )

        print(f"\n3. Response received:")
        print(f"   - Message: {response.message[:100]}...")
        print(f"   - Is valid: {response.is_valid}")
        print(f"   - Has deployment_spec: {response.deployment_spec is not None}")
        print(f"   - Retrieved patterns: {len(response.retrieved_patterns) if response.retrieved_patterns else 0}")

        if response.deployment_spec:
            print(f"\n4. Deployment spec keys:")
            print(f"   {list(response.deployment_spec.keys())}")
        else:
            print(f"\n4. No deployment spec generated!")
            print(f"   Message: {response.message}")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_agent()
