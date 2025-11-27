#!/usr/bin/env python3
"""Verify OTA benchmark setup is complete and ready to run."""

import sys
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists."""
    path = Path(filepath)
    exists = path.exists()

    if exists:
        size = path.stat().st_size
        return True, f"{size:,} bytes"
    else:
        return False, "Missing"


def check_dependencies():
    """Check if required Python packages are installed."""
    deps = {
        "rich": "Console output formatting",
        "psutil": "Resource monitoring",
        "matplotlib": "Graph generation",
        "seaborn": "Statistical visualization",
        "numpy": "Numerical operations",
        "pandas": "Data analysis",
        "openai": "LLM API access",
        "dotenv": "Environment variables"
    }

    results = {}
    for pkg, desc in deps.items():
        try:
            __import__(pkg.replace("-", "_"))
            results[pkg] = ("✓", "Installed", desc)
        except ImportError:
            results[pkg] = ("✗", "Missing", desc)

    return results


def check_env_vars():
    """Check if required environment variables are set."""
    import os
    from dotenv import load_dotenv

    load_dotenv()

    required = {
        "OPENAI_API_KEY": "OpenAI API access"
    }

    results = {}
    for var, desc in required.items():
        value = os.getenv(var)
        if value:
            # Mask the key
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            results[var] = ("✓", masked, desc)
        else:
            results[var] = ("✗", "Not set", desc)

    return results


def main():
    """Run all verification checks."""
    console.print("\n")
    console.print(Panel.fit(
        "[bold cyan]OTA Benchmark Setup Verification[/bold cyan]\n"
        "Checking all components...",
        border_style="cyan"
    ))

    all_ok = True

    # Check core files
    console.print("\n[bold]1. Core Implementation Files[/bold]")
    files_table = Table()
    files_table.add_column("File", style="cyan")
    files_table.add_column("Status", style="green")
    files_table.add_column("Size", justify="right")

    core_files = {
        "ota_test_dataset.py": "Test case generator",
        "ota_metrics_evaluator.py": "Metrics evaluator",
        "run_ota_benchmark.py": "Main benchmark runner",
        "update_ota_metrics_graph.py": "Graph updater"
    }

    for filename, desc in core_files.items():
        exists, size = check_file_exists(filename, desc)
        status = "✓" if exists else "✗ MISSING"
        if not exists:
            all_ok = False
        files_table.add_row(filename, status, size)

    console.print(files_table)

    # Check documentation
    console.print("\n[bold]2. Documentation Files[/bold]")
    docs_table = Table()
    docs_table.add_column("File", style="cyan")
    docs_table.add_column("Status", style="green")
    docs_table.add_column("Size", justify="right")

    doc_files = {
        "QUICKSTART_OTA_BENCHMARK.md": "Quick start guide",
        "OTA_BENCHMARK_SUMMARY.md": "Complete summary",
        "verify_ota_setup.py": "This verification script"
    }

    for filename, desc in doc_files.items():
        exists, size = check_file_exists(filename, desc)
        status = "✓" if exists else "✗ MISSING"
        if not exists:
            all_ok = False
        docs_table.add_row(filename, status, size)

    console.print(docs_table)

    # Check dependencies
    console.print("\n[bold]3. Python Dependencies[/bold]")
    deps_table = Table()
    deps_table.add_column("Package", style="cyan")
    deps_table.add_column("Status")
    deps_table.add_column("Description")

    deps = check_dependencies()
    for pkg, (status, state, desc) in deps.items():
        color = "green" if status == "✓" else "red"
        deps_table.add_row(pkg, f"[{color}]{status} {state}[/{color}]", desc)
        if status == "✗":
            all_ok = False

    console.print(deps_table)

    # Check environment variables
    console.print("\n[bold]4. Environment Configuration[/bold]")
    env_table = Table()
    env_table.add_column("Variable", style="cyan")
    env_table.add_column("Status")
    env_table.add_column("Value")

    env_vars = check_env_vars()
    for var, (status, value, desc) in env_vars.items():
        color = "green" if status == "✓" else "red"
        env_table.add_row(var, f"[{color}]{status}[/{color}]", value)
        if status == "✗":
            all_ok = False

    console.print(env_table)

    # Check metrics_ota-main directory
    console.print("\n[bold]5. OTA Comparison Directory[/bold]")
    ota_dir_table = Table()
    ota_dir_table.add_column("Component", style="cyan")
    ota_dir_table.add_column("Status")

    ota_dir_exists = Path("metrics_ota-main").exists()
    ota_metrics_py_exists = Path("metrics_ota-main/metrics.py").exists()

    ota_dir_table.add_row(
        "metrics_ota-main/ directory",
        f"[{'green' if ota_dir_exists else 'red'}]{'✓ Found' if ota_dir_exists else '✗ Not found'}[/]"
    )
    ota_dir_table.add_row(
        "metrics_ota-main/metrics.py",
        f"[{'green' if ota_metrics_py_exists else 'red'}]{'✓ Found' if ota_metrics_py_exists else '✗ Not found'}[/]"
    )

    console.print(ota_dir_table)

    if not ota_metrics_py_exists:
        console.print("[yellow]Note: metrics.py will be updated when you run update_ota_metrics_graph.py[/yellow]")

    # Check agent and knowledge base
    console.print("\n[bold]6. nl2dsl-agent Components[/bold]")
    agent_table = Table()
    agent_table.add_column("Component", style="cyan")
    agent_table.add_column("Status")

    agent_files = {
        "agent.py": "DSL Agent",
        "knowledge_base.py": "Knowledge Base",
    }

    for filename, desc in agent_files.items():
        exists, _ = check_file_exists(filename, desc)
        status_text = f"[{'green' if exists else 'red'}]{'✓ ' + desc if exists else '✗ Missing'}[/]"
        agent_table.add_row(filename, status_text)
        if not exists:
            all_ok = False

    console.print(agent_table)

    # Final summary
    console.print("\n")
    if all_ok:
        console.print(Panel(
            "[bold green]✓ All checks passed![/bold green]\n\n"
            "Your OTA benchmark setup is complete and ready to use.\n\n"
            "[bold]Next steps:[/bold]\n"
            "  1. python run_ota_benchmark.py\n"
            "  2. python update_ota_metrics_graph.py\n"
            "  3. cd metrics_ota-main && python metrics.py\n\n"
            "See QUICKSTART_OTA_BENCHMARK.md for detailed instructions.",
            title="[bold green]Setup Complete[/bold green]",
            border_style="green"
        ))
        return 0
    else:
        console.print(Panel(
            "[bold red]✗ Some checks failed[/bold red]\n\n"
            "Please fix the issues above before running the benchmark.\n\n"
            "[bold]Common fixes:[/bold]\n"
            "  • Missing dependencies: pip install rich psutil matplotlib seaborn numpy pandas openai python-dotenv\n"
            "  • Missing API key: Create .env file with OPENAI_API_KEY=your-key\n"
            "  • Missing files: Re-run setup or check file paths\n\n"
            "See QUICKSTART_OTA_BENCHMARK.md for troubleshooting.",
            title="[bold red]Setup Incomplete[/bold red]",
            border_style="red"
        ))
        return 1


if __name__ == "__main__":
    sys.exit(main())
