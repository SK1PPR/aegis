"""Quick script to run evaluation and generate report."""

from dataset_generator import DatasetGenerator
from metrics_evaluator import MetricsEvaluator
from rich.console import Console

console = Console()


def main():
    """Run full evaluation."""
    console.print("\n[bold cyan]╔════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║  NL2DSL Metrics Evaluation Suite      ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════╝[/bold cyan]\n")
    
    # Step 1: Generate dataset
    console.print("[1/3] Generating test dataset...")
    generator = DatasetGenerator()
    dataset = generator.get_all_cases()
    generator.save_to_json("test_dataset.json")
    
    stats = generator.get_statistics()
    console.print(f"  ✓ {stats['total_cases']} test cases generated")
    console.print(f"  ✓ {len(stats['by_category'])} categories")
    console.print(f"  ✓ {len(stats['by_complexity'])} complexity levels\n")
    
    # Step 2: Run evaluation
    console.print("[2/3] Running evaluation (this may take a while)...")
    evaluator = MetricsEvaluator()
    report = evaluator.evaluate_dataset(dataset, save_results=True)
    console.print("  ✓ Evaluation complete\n")
    
    # Step 3: Display results
    console.print("[3/3] Generating report...\n")
    evaluator.print_report(report)
    
    # Print comparison-ready summary
    console.print("\n[bold cyan]═══ METRICS SUMMARY FOR COMPARISON ═══[/bold cyan]\n")
    console.print(f"[bold]Validity:[/bold]          {report.validity_percentage:.2f}%")
    console.print(f"[bold]Completeness:[/bold]     {report.completeness_percentage:.2f}%")
    console.print(f"[bold]Extensibility:[/bold]    {report.extensibility_percentage:.2f}%")
    console.print(f"[bold]Avg Latency:[/bold]      {report.avg_latency:.3f}s")
    console.print()
    

if __name__ == "__main__":
    main()