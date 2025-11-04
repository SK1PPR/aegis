"""Compare all four approaches: Conversational, Plain LLM, Template-Based, and Grammar-Based."""

import json
from typing import Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import csv

console = Console()


def load_metrics(approach: str) -> Dict[str, Any]:
    """Load metrics from JSON file."""
    file_mapping = {
        "conversational": "evaluation_summary.json",
        "plain_llm": "plain_llm_evaluation_summary.json",
        "template": "template_evaluation_summary.json",
        "grammar": "grammar_evaluation_summary.json"
    }
    
    filepath = file_mapping.get(approach)
    if not filepath or not Path(filepath).exists():
        console.print(f"[yellow]Warning: {filepath} not found[/yellow]")
        return None
    
    with open(filepath, "r") as f:
        return json.load(f)


def generate_comparison_table(conv: Dict, plain: Dict, template: Dict, grammar: Dict) -> Table:
    """Generate comprehensive comparison table."""
    table = Table(
        title="Complete Approach Comparison",
        show_header=True,
        header_style="bold magenta"
    )
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Conversational", justify="right", style="green")
    table.add_column("Plain LLM", justify="right", style="blue")
    table.add_column("Template", justify="right", style="yellow")
    table.add_column("Grammar (CFG)", justify="right", style="magenta")
    table.add_column("Best", justify="center")
    
    metrics = [
        ("Validity (%)", "validity_percentage"),
        ("Grammar Pass (%)", "grammar_pass_rate"),
        ("Parser Pass (%)", "parser_pass_rate"),
        ("Completeness (%)", "completeness_percentage"),
        ("Extensibility (%)", "extensibility_percentage"),
        ("Avg Latency (s)", "avg_latency_seconds"),
        ("Median Latency (s)", "median_latency_seconds"),
        ("P95 Latency (s)", "p95_latency_seconds"),
    ]
    
    for metric_name, metric_key in metrics:
        values = {}
        if conv:
            values["Conv"] = conv.get(metric_key, 0)
        if plain:
            values["Plain"] = plain.get(metric_key, 0)
        if template:
            values["Tmpl"] = template.get(metric_key, 0)
        if grammar:
            values["CFG"] = grammar.get(metric_key, 0)
        
        # Determine best (lower is better for latency)
        if "latency" in metric_key.lower():
            best_val = min(values.values())
        else:
            best_val = max(values.values())
        
        best = [k for k, v in values.items() if v == best_val]
        
        table.add_row(
            metric_name,
            f"{values.get('Conv', 0):.3f}" if conv else "N/A",
            f"{values.get('Plain', 0):.3f}" if plain else "N/A",
            f"{values.get('Tmpl', 0):.3f}" if template else "N/A",
            f"{values.get('CFG', 0):.3f}" if grammar else "N/A",
            "+".join(best) if best else "-"
        )
    
    return table


def export_comparison_csv(conv: Dict, plain: Dict, template: Dict, grammar: Dict):
    """Export comparison to CSV."""
    with open("complete_comparison.csv", "w", newline='') as f:
        writer = csv.writer(f)
        writer.writerow([
            "Metric",
            "Conversational_Agent",
            "Plain_LLM",
            "Template_Based",
            "Grammar_CFG",
            "Best_Approach"
        ])
        
        metrics = [
            ("Validity_%", "validity_percentage"),
            ("Grammar_Pass_%", "grammar_pass_rate"),
            ("Parser_Pass_%", "parser_pass_rate"),
            ("Completeness_%", "completeness_percentage"),
            ("Extensibility_%", "extensibility_percentage"),
            ("Avg_Latency_s", "avg_latency_seconds"),
            ("Median_Latency_s", "median_latency_seconds"),
            ("P95_Latency_s", "p95_latency_seconds"),
        ]
        
        for metric_name, metric_key in metrics:
            values = {
                "Conversational": conv.get(metric_key, 0) if conv else 0,
                "Plain_LLM": plain.get(metric_key, 0) if plain else 0,
                "Template": template.get(metric_key, 0) if template else 0,
                "Grammar_CFG": grammar.get(metric_key, 0) if grammar else 0
            }
            
            # Determine best
            if "latency" in metric_key.lower():
                best_val = min(v for v in values.values() if v > 0)
            else:
                best_val = max(values.values())
            
            best = [k for k, v in values.items() if v == best_val and v > 0]
            
            writer.writerow([
                metric_name,
                f"{values['Conversational']:.3f}",
                f"{values['Plain_LLM']:.3f}",
                f"{values['Template']:.3f}",
                f"{values['Grammar_CFG']:.3f}",
                "+".join(best)
            ])
    
    console.print("\n[green]Comparison exported to: complete_comparison.csv[/green]")


def generate_insights(conv: Dict, plain: Dict, template: Dict, grammar: Dict) -> str:
    """Generate detailed insights."""
    insights = []
    
    approaches = {}
    if conv:
        approaches["Conversational Agent"] = conv
    if plain:
        approaches["Plain LLM"] = plain
    if template:
        approaches["Template-Based"] = template
    if grammar:
        approaches["Grammar (CFG)"] = grammar
    
    # Validity
    validity_vals = {name: data.get('validity_percentage', 0) for name, data in approaches.items()}
    best_validity = max(validity_vals, key=validity_vals.get)
    insights.append(f"✓ **Best Validity**: {best_validity} ({validity_vals[best_validity]:.1f}%)")
    
    # Completeness
    comp_vals = {name: data.get('completeness_percentage', 0) for name, data in approaches.items()}
    best_comp = max(comp_vals, key=comp_vals.get)
    insights.append(f"✓ **Best Completeness**: {best_comp} ({comp_vals[best_comp]:.1f}%)")
    
    # Extensibility
    ext_vals = {name: data.get('extensibility_percentage', 0) for name, data in approaches.items()}
    best_ext = max(ext_vals, key=ext_vals.get)
    insights.append(f"✓ **Best Extensibility**: {best_ext} ({ext_vals[best_ext]:.1f}%)")
    
    # Latency
    lat_vals = {name: data.get('avg_latency_seconds', float('inf')) for name, data in approaches.items()}
    best_lat = min(lat_vals, key=lat_vals.get)
    insights.append(f"✓ **Fastest**: {best_lat} ({lat_vals[best_lat]:.3f}s)")
    
    # Overall score
    scores = {}
    for name in approaches.keys():
        score = 0
        if validity_vals.get(name, 0) == max(validity_vals.values()):
            score += 1
        if comp_vals.get(name, 0) == max(comp_vals.values()):
            score += 1
        if ext_vals.get(name, 0) == max(ext_vals.values()):
            score += 1
        if lat_vals.get(name, float('inf')) == min(lat_vals.values()):
            score += 1
        scores[name] = score
    
    winner = max(scores, key=scores.get)
    insights.append(f"\n🏆 **Overall Winner**: {winner} (best in {scores[winner]}/4 metrics)")
    
    # Specific insights
    insights.append("\n**Key Findings:**")
    
    # Compare CFG vs LLM approaches
    if grammar and plain:
        cfg_complete = grammar.get('completeness_percentage', 0)
        llm_complete = plain.get('completeness_percentage', 0)
        if cfg_complete > llm_complete:
            diff = cfg_complete - llm_complete
            insights.append(f"• CFG outperforms Plain LLM by {diff:.1f}% in completeness")
        else:
            diff = llm_complete - cfg_complete
            insights.append(f"• Plain LLM outperforms CFG by {diff:.1f}% in completeness")
    
    # Template speed advantage
    if template:
        tmpl_lat = template.get('avg_latency_seconds', 0)
        if tmpl_lat < 0.1:
            insights.append(f"• Template-based is extremely fast ({tmpl_lat:.3f}s avg)")
    
    # Conversational advantage
    if conv:
        conv_ext = conv.get('extensibility_percentage', 0)
        if conv_ext > 50:
            insights.append(f"• Conversational handles complex cases well ({conv_ext:.1f}% extensibility)")
    
    return "\n".join(insights)


def main():
    """Main comparison function."""
    console.print("\n[bold cyan]╔════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║  Complete NL2DSL Comparison                        ║[/bold cyan]")
    console.print("[bold cyan]║  All Four Approaches                               ║[/bold cyan]")
    console.print("[bold cyan]╚════════════════════════════════════════════════════╝[/bold cyan]\n")
    
    # Load all metrics
    console.print("[yellow]Loading evaluation results...[/yellow]\n")
    
    conv = load_metrics("conversational")
    plain = load_metrics("plain_llm")
    template = load_metrics("template")
    grammar = load_metrics("grammar")
    
    if not any([conv, plain, template, grammar]):
        console.print("\n[red]Error: No evaluation results found[/red]")
        console.print("[yellow]Please run evaluations first:[/yellow]")
        console.print("  1. python enhanced_metrics_evaluator.py")
        console.print("  2. python plain_llm_evaluator.py")
        console.print("  3. python template_evaluator.py")
        console.print("  4. python grammar_evaluator.py")
        return
    
    # Generate comparison table
    table = generate_comparison_table(conv, plain, template, grammar)
    console.print(table)
    
    # Generate insights
    console.print("\n[bold cyan]═══ Key Insights ═══[/bold cyan]\n")
    insights = generate_insights(conv, plain, template, grammar)
    console.print(Panel(insights, title="Analysis", border_style="green"))
    
    # Export to CSV
    export_comparison_csv(conv, plain, template, grammar)
    
    # Print approach summaries
    console.print("\n[bold cyan]═══ Approach Summaries ═══[/bold cyan]\n")
    
    if conv:
        console.print("[cyan]1. Conversational Agent:[/cyan]")
        console.print(f"   Multi-turn conversations for requirements gathering")
        console.print(f"   Validity: {conv.get('validity_percentage', 0):.1f}% | Completeness: {conv.get('completeness_percentage', 0):.1f}%\n")
    
    if plain:
        console.print("[blue]2. Plain LLM:[/blue]")
        console.print(f"   Single-shot generation without conversation")
        console.print(f"   Validity: {plain.get('validity_percentage', 0):.1f}% | Completeness: {plain.get('completeness_percentage', 0):.1f}%\n")
    
    if template:
        console.print("[yellow]3. Template-Based:[/yellow]")
        console.print(f"   Pattern matching with Jinja2 templates")
        console.print(f"   Validity: {template.get('validity_percentage', 0):.1f}% | Completeness: {template.get('completeness_percentage', 0):.1f}%\n")
    
    if grammar:
        console.print("[magenta]4. Grammar-Based (CFG):[/magenta]")
        console.print(f"   Context-Free Grammar with Lark parser")
        console.print(f"   Validity: {grammar.get('validity_percentage', 0):.1f}% | Completeness: {grammar.get('completeness_percentage', 0):.1f}%\n")


if __name__ == "__main__":
    main()