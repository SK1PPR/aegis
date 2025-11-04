"""Run all four evaluations and generate complete comparison."""

from rich.console import Console
from rich.prompt import Confirm

console = Console()


def main():
    console.print("\n[bold cyan]╔══════════════════════════════════════════════════════╗[/bold cyan]")
    console.print("[bold cyan]║  Complete NL2DSL Evaluation Suite                   ║[/bold cyan]")
    console.print("[bold cyan]║  All Four Approaches                                 ║[/bold cyan]")
    console.print("[bold cyan]╚══════════════════════════════════════════════════════╝[/bold cyan]\n")
    
    console.print("[yellow]This will evaluate:[/yellow]")
    console.print("  1. Enhanced Conversational Agent (Multi-turn)")
    console.print("  2. Plain LLM (Single-shot)")
    console.print("  3. Template-Based (Jinja2)")
    console.print("  4. Grammar-Based (CFG + Lark)")
    console.print("  5. Generate comprehensive comparison")
    console.print("\n[yellow]Estimated time: 20-25 minutes[/yellow]\n")
    
    if not Confirm.ask("Continue?", default=True):
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Step 1: Conversational Agent
    console.print("\n[bold]═══ Step 1/5: Conversational Agent ═══[/bold]\n")
    try:
        from enhanced_metrics_evaluator import main as conv_main
        conv_main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Continuing with other evaluations...[/yellow]")
    
    # Step 2: Plain LLM
    console.print("\n[bold]═══ Step 2/5: Plain LLM ═══[/bold]\n")
    try:
        from plain_llm_evaluator import main as plain_main
        plain_main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Continuing with other evaluations...[/yellow]")
    
    # Step 3: Template-Based
    console.print("\n[bold]═══ Step 3/5: Template-Based ═══[/bold]\n")
    try:
        from template_evaluator import main as template_main
        template_main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Continuing with other evaluations...[/yellow]")
    
    # Step 4: Grammar-Based
    console.print("\n[bold]═══ Step 4/5: Grammar-Based (CFG) ═══[/bold]\n")
    try:
        from grammar_evaluator import main as grammar_main
        grammar_main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Continuing with comparison...[/yellow]")
    
    # Step 5: Comparison
    console.print("\n[bold]═══ Step 5/5: Complete Comparison ═══[/bold]\n")
    try:
        from compare_all_approaches_final import main as compare_main
        compare_main()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    
    console.print("\n[bold green]═══ Complete Evaluation Finished! ═══[/bold green]\n")
    console.print("[green]Generated files:[/green]")
    console.print("  📄 test_dataset.json")
    console.print("  📊 evaluation_summary.json (conversational)")
    console.print("  📊 plain_llm_evaluation_summary.json")
    console.print("  📊 template_evaluation_summary.json")
    console.print("  📊 grammar_evaluation_summary.json")
    console.print("  📈 complete_comparison.csv")
    console.print("\n[cyan]Ready for your research paper! 🎓[/cyan]\n")


if __name__ == "__main__":
    main()