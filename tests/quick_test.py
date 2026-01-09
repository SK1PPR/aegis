#!/usr/bin/env python3
"""
Quick test script to verify the NL2DSL agent setup.
This runs a simple test without requiring OpenAI API key.
"""

import sys
from pathlib import Path

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    try:
        from src.agent import DSLAgent
        from src.knowledge_base import ECUType, SafetyClass, DeploymentMode, OTAKnowledgeBase
        print("✓ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_knowledge_base():
    """Test knowledge base loading."""
    print("\nTesting knowledge base...")
    try:
        from src.knowledge_base import OTAKnowledgeBase

        kb = OTAKnowledgeBase()
        stats = kb.get_statistics()

        print(f"✓ Knowledge base loaded successfully")
        print(f"  - Total patterns: {stats['total_patterns']}")
        print(f"  - Device types: {stats['by_device_type']}")
        print(f"  - Safety classes: {stats['by_safety_class']}")
        print(f"  - Deployment modes: {stats['by_deployment_mode']}")
        return True
    except Exception as e:
        print(f"❌ Error loading knowledge base: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_retrieval_pipeline():
    """Test the three-stage retrieval pipeline."""
    print("\nTesting three-stage retrieval pipeline...")
    try:
        from src.knowledge_base import OTAKnowledgeBase, ECUType, SafetyClass, DeploymentMode

        kb = OTAKnowledgeBase()

        # Test retrieval
        query = "Update ADAS camera firmware for EU vehicles"
        results = kb.retrieve_ota_patterns(
            query=query,
            device_type=ECUType.ADAS,
            sw_version="3.2.1",
            safety_class=SafetyClass.ASIL_B,
            region="EU",
            hardware_revision="rev_C",
            deployment_mode=DeploymentMode.DELTA,
            top_k=2
        )

        print(f"✓ Retrieval pipeline working")
        print(f"  - Query: '{query}'")
        print(f"  - Retrieved {len(results)} pattern(s)")

        for i, (pattern, score, breakdown) in enumerate(results, 1):
            print(f"\n  Pattern {i}: {pattern.name}")
            print(f"    Composite Score: {breakdown['composite']:.3f}")
            print(f"    - Semantic: {breakdown['semantic']:.3f}")
            print(f"    - Schema: {breakdown['schema']:.3f}")
            print(f"    - Recency: {breakdown['recency']:.3f}")
            print(f"    - Validation: {breakdown['validation']:.3f}")

        return True
    except Exception as e:
        print(f"❌ Error in retrieval pipeline: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_metadata_filtering():
    """Test Stage 1: Metadata filtering."""
    print("\nTesting Stage 1: Metadata Filtering...")
    try:
        from src.knowledge_base import OTAKnowledgeBase, ECUType, SafetyClass, DeploymentMode

        kb = OTAKnowledgeBase()

        # Test filtering
        filtered = kb.stage1_metadata_filter(
            device_type=ECUType.ADAS,
            sw_version="3.2.1",
            safety_class=SafetyClass.ASIL_B,
            region="EU",
            hardware_revision="rev_C",
            deployment_mode=DeploymentMode.DELTA
        )

        print(f"✓ Metadata filtering working")
        print(f"  - Total patterns in KB: {len(kb.patterns)}")
        print(f"  - Filtered to: {len(filtered)} pattern(s)")

        if filtered:
            print(f"\n  Filtered patterns:")
            for p in filtered:
                print(f"    - {p.name}")
                print(f"      Device: {p.metadata.device_type.value}, Safety: {p.metadata.safety_class.value}")

        return True
    except Exception as e:
        print(f"❌ Error in metadata filtering: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 70)
    print("NL2DSL Agent - Quick Test Suite")
    print("=" * 70)
    print("\nThis test verifies the setup without requiring OpenAI API key.\n")

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Knowledge Base", test_knowledge_base()))
    results.append(("Metadata Filtering", test_metadata_filtering()))
    results.append(("Retrieval Pipeline", test_retrieval_pipeline()))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    for test_name, passed in results:
        status = "✓ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")

    all_passed = all(result[1] for result in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nNext steps:")
        print("  1. Set up your .env file with OPENAI_API_KEY")
        print("  2. Run: python sample_run.py")
        print("  3. Or run: python main.py (for interactive mode)")
        print("  4. Or run: python run_ota_benchmark.py (for full evaluation)")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.")
        sys.exit(1)

    print()


if __name__ == "__main__":
    main()
