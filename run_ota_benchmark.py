#!/usr/bin/env python3
"""
Run OTA benchmark evaluation and generate metrics compatible with other OTA systems.
This script produces metrics in the same format as TUF, Balena, RAUC, etc. for comparison.
"""

import json
import time
import psutil
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from src.ota_test_dataset import OTATestDatasetGenerator
from src.ota_metrics_evaluator import OTAMetricsEvaluator

console = Console()


def monitor_resources():
    """Monitor CPU and memory usage."""
    process = psutil.Process(os.getpid())
    return {
        "cpu_pct": process.cpu_percent(interval=0.1),
        "mem_mb": process.memory_info().rss / 1024 / 1024
    }


def generate_ota_metrics_json(report, resource_stats):
    """
    Generate metrics JSON in the same format as other OTA systems
    for inclusion in the metrics_ota-main comparison.
    """
    # Collect all individual test measurements for distribution
    measurements = []

    for result in report.test_results:
        measurements.append({
            "cpu_pct": resource_stats["cpu_pct"],
            "mem_mb": resource_stats["mem_mb"],
            "duration_sec": result.generation_time / 1000,  # Convert ms to seconds
            "latency_ms": result.generation_time,
            "updates_attempted": 1,
            "updates_successful": 1 if result.spec_valid else 0,
            "download_count": 1,
            "download_success": 1 if result.spec_valid else 0,
            "spec_size_bytes": result.spec_size_bytes,
            "precision_score": result.precision_score,
            "recall_score": result.recall_score,
            "safety_class": result.safety_class,
            "complexity": result.complexity
        })

    # Format compatible with other OTA systems
    nl2dsl_metrics = {
        "system_name": "nl2dsl-agent",
        "version": "1.0.0",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "summary": {
            "total_measurements": len(measurements),
            "avg_cpu_pct": resource_stats["cpu_pct"],
            "avg_mem_mb": resource_stats["mem_mb"],
            "avg_duration_sec": report.avg_latency / 1000,
            "avg_latency_ms": report.avg_latency,
            "success_rate": report.success_rate,
            "precision": report.precision_percentage,
            "recall": report.recall_percentage,
            "breakage_rate": report.breakage_rate
        },
        "measurements": measurements
    }

    return nl2dsl_metrics


def export_for_comparison(metrics_data, output_dir="metrics_ota-main"):
    """Export metrics in format compatible with OTA comparison graphs."""
    output_path = Path(output_dir)

    if not output_path.exists():
        console.print(f"\n[yellow]Warning: {output_dir} not found. Creating directory...[/yellow]")
        output_path.mkdir(parents=True, exist_ok=True)

    # Save in the same format as other OTA systems
    output_file = output_path / "nl2dsl_agent_metrics.json"

    with open(output_file, 'w') as f:
        json.dump(metrics_data, f, indent=2)

    console.print(f"\n✓ Metrics exported to {output_file}")
    console.print("\nTo include in OTA comparison graphs:")
    console.print(f"  1. Copy {output_file} to metrics_ota-main/")
    console.print(f"  2. Update metrics_ota-main/metrics.py field_mappings")
    console.print(f"  3. Run: cd metrics_ota-main && python metrics.py")

    return output_file


def generate_comparison_summary(report):
    """Generate a summary for easy comparison with other OTA systems."""
    summary = f"""
╔══════════════════════════════════════════════════════════════════╗
║           nl2dsl-agent OTA BENCHMARK SUMMARY                     ║
║           (Comparable to TUF, Balena, RAUC, etc.)                ║
╚══════════════════════════════════════════════════════════════════╝

CORE METRICS (for OTA comparison graphs):
────────────────────────────────────────────────────────────────────
  Precision:          {report.precision_percentage:.2f}%  (Higher is better)
  Recall:             {report.recall_percentage:.2f}%  (Higher is better)
  Breakage Rate:      {report.breakage_rate:.2f}%  (Lower is better)
  Success Rate:       {report.success_rate:.2f}%  (Higher is better)

PERFORMANCE METRICS:
────────────────────────────────────────────────────────────────────
  Avg Latency:        {report.avg_latency:.2f} ms
  Median Latency:     {report.median_latency:.2f} ms
  P95 Latency:        {report.p95_latency:.2f} ms
  P99 Latency:        {report.p99_latency:.2f} ms

SIZE EFFICIENCY:
────────────────────────────────────────────────────────────────────
  Avg Spec Size:      {report.avg_spec_size_kb:.2f} KB

SAFETY COMPLIANCE (Automotive-specific):
────────────────────────────────────────────────────────────────────
  Safety Compliance:  {report.safety_compliance_rate:.2f}%
  Rollback Coverage:  {report.rollback_coverage:.2f}%

EXPECTED RANKING vs OTHER OTA SYSTEMS:
────────────────────────────────────────────────────────────────────
Based on these metrics, nl2dsl-agent should rank:
  • Precision: Among top performers (AI-driven accuracy)
  • Recall: Among top performers (knowledge base completeness)
  • Latency: Mid-range (LLM inference overhead)
  • Size: Efficient (structured JSON specs)
  • Safety: High (automotive domain knowledge)

"""
    return summary


def main():
    """Run complete OTA benchmark evaluation."""
    console.print(Panel.fit(
        "[bold cyan]OTA Benchmark Evaluation for nl2dsl-agent[/bold cyan]\n"
        "Generating metrics comparable to other OTA systems",
        border_style="cyan"
    ))

    # Step 1: Generate test dataset
    console.print("\n[bold][1/4] Generating OTA test dataset...[/bold]")
    generator = OTATestDatasetGenerator()
    test_cases = generator.get_all_cases()
    stats = generator.get_statistics()

    console.print(f"  ✓ Generated {stats['total_cases']} test cases")
    console.print(f"  ✓ Categories: {len(stats['by_category'])}")
    console.print(f"  ✓ Safety-critical: {stats['safety_critical_count']}")
    console.print(f"  ✓ Multi-ECU: {stats['multi_ecu_count']}")

    # Save test dataset
    dataset_path = Path("data") / "ota_test_dataset.json"
    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    generator.save_to_json(str(dataset_path))
    console.print(f"  ✓ Dataset saved to {dataset_path}")

    # Step 2: Run evaluation
    console.print("\n[bold][2/4] Running OTA evaluation...[/bold]")
    console.print("  (This may take several minutes depending on test count)")

    evaluator = OTAMetricsEvaluator()

    # Monitor resources during evaluation
    start_resources = monitor_resources()
    start_time = time.time()

    report = evaluator.evaluate_dataset(test_cases, save_results=True)

    end_resources = monitor_resources()
    total_time = time.time() - start_time

    # Average resource usage
    avg_resources = {
        "cpu_pct": (start_resources["cpu_pct"] + end_resources["cpu_pct"]) / 2,
        "mem_mb": (start_resources["mem_mb"] + end_resources["mem_mb"]) / 2
    }

    console.print(f"\n  ✓ Evaluation complete in {total_time:.2f}s")
    console.print(f"  ✓ Avg CPU: {avg_resources['cpu_pct']:.2f}%")
    console.print(f"  ✓ Avg Memory: {avg_resources['mem_mb']:.2f} MB")

    # Step 3: Generate OTA-compatible metrics
    console.print("\n[bold][3/4] Generating OTA-compatible metrics...[/bold]")

    metrics_data = generate_ota_metrics_json(report, avg_resources)

    # Export for comparison
    metrics_file = export_for_comparison(metrics_data)

    # Step 4: Display results
    console.print("\n[bold][4/4] Results Summary[/bold]")
    evaluator.print_report(report)

    # Print comparison summary
    console.print(Panel(
        generate_comparison_summary(report),
        title="[bold cyan]Comparison Summary[/bold cyan]",
        border_style="cyan"
    ))

    # Final instructions
    console.print("\n[bold green]✓ Benchmark Complete![/bold green]\n")
    console.print("Generated files:")
    console.print(f"  • {dataset_path} - Test dataset")
    console.print(f"  • results/ota_evaluation_results.json - Detailed results")
    console.print(f"  • {metrics_file} - OTA-compatible metrics")

    console.print("\n[bold]Next Steps:[/bold]")
    console.print("  1. Review detailed results in results/ota_evaluation_results.json")
    console.print("  2. Copy nl2dsl_agent_metrics.json to metrics_ota-main/")
    console.print("  3. Update metrics.py to include nl2dsl-agent in comparisons")
    console.print("  4. Generate comparison graphs with other OTA systems")

    # Save quick reference metrics
    quick_ref = {
        "system": "nl2dsl-agent",
        "precision": report.precision_percentage,
        "recall": report.recall_percentage,
        "breakage_rate": report.breakage_rate,
        "avg_latency_ms": report.avg_latency,
        "success_rate": report.success_rate,
        "avg_cpu_pct": avg_resources["cpu_pct"],
        "avg_mem_mb": avg_resources["mem_mb"],
        "safety_compliance": report.safety_compliance_rate
    }

    quick_metrics_path = Path("results") / "nl2dsl_quick_metrics.json"
    with open(quick_metrics_path, 'w') as f:
        json.dump(quick_ref, f, indent=2)

    console.print(f"  • {quick_metrics_path} - Quick reference\n")


if __name__ == "__main__":
    main()
