#!/usr/bin/env python3
"""Terminal-based conversational agent for OTA deployment specification generation with three-stage retrieval."""

import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.text import Text
import json
from src.agent import DSLAgent, AgentResponse
from src.knowledge_base import (
    OTAKnowledgeBase,
    OTADeploymentPattern,
    ECUType,
    SafetyClass,
    DeploymentMode
)


console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║     NL2OTA - Knowledge-Enabled OTA Deployment Generator         ║
║     Natural Language → Automotive OTA Specifications            ║
║     Three-Stage Retrieval: Metadata + Semantic + Schema         ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")
    console.print("Describe your OTA update requirements in natural language.")
    console.print("System uses three-stage retrieval: Metadata Filtering → Semantic Search → Schema Re-ranking")
    console.print("\nCommands: /show, /save, /knowledge, /stats, /reset, /help, /quit\n")


def print_help():
    """Print help information."""
    help_text = """
# Available Commands

- **/show** - Display current generated OTA deployment specification
- **/save <filename>** - Save deployment spec to JSON file
- **/knowledge** - Show knowledge base OTA patterns
- **/stats** - Show knowledge base statistics
- **/reset** - Start a new conversation
- **/help** - Show this help
- **/quit** - Exit the program

# How It Works

## Three-Stage Retrieval Pipeline

### Stage 1: Metadata Filtering (Deterministic)
- Filters by ECU type (infotainment, ADAS, powertrain, etc.)
- Filters by safety class (ASIL-A/B/C/D, QM)
- Filters by region (US, EU, CN)
- Filters by hardware revision and software version
- **Ensures ZERO cross-ECU contamination**

### Stage 2: Semantic Search (Vector-Based)
- Uses sentence-transformers embeddings
- Cosine similarity search within filtered subset
- Captures semantic intent beyond keywords

### Stage 3: Schema Re-Ranking (Structural + Version)
- Schema completeness score
- Version recency score
- Validation rule robustness
- Composite score with weighted combination

## Example Usage

```
You: I need to update ADAS camera firmware for EU region
System: [filters by ADAS + EU + safety class]
System: [semantic search for camera update]
System: [re-ranks by schema quality]
System: [generates OTA deployment spec]
You: /show
[displays deployment specification with safety checks]
You: /save adas_update.json
```

# Safety Features

✓ ASIL safety class enforcement
✓ Mandatory pre-conditions (battery, vehicle state)
✓ Rollback procedures for all updates
✓ Verification steps for safety-critical ECUs
✓ Version compatibility checks
✓ Hardware revision validation

# Metadata Filtering

Before query, you'll be asked for:
- **ECU Type**: infotainment, adas, powertrain, body_control, telematics, gateway
- **Software Version**: e.g., "3.2.1"
- **Safety Class**: QM, ASIL_A, ASIL_B, ASIL_C, ASIL_D
- **Region**: US, EU, CN
- **Hardware Revision**: e.g., "rev_C"
- **Deployment Mode** (optional): A/B, dual-bank, delta, full
"""
    console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))


def display_deployment_spec(spec: dict, title: str = "Generated OTA Deployment Specification"):
    """Display deployment specification as formatted JSON."""
    json_str = json.dumps(spec, indent=2)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title=title, border_style="green"))


def display_ota_patterns(patterns: list):
    """Display retrieved OTA patterns with scores."""
    if not patterns:
        return
    
    console.print("\n[bold cyan]📚 Retrieved OTA Patterns (Three-Stage Pipeline):[/bold cyan]\n")
    
    for i, (pattern, score, breakdown) in enumerate(patterns, 1):
        # Create score breakdown table
        score_table = Table(title=f"Pattern {i}: {pattern.name}", show_header=True, border_style="blue")
        score_table.add_column("Score Component", style="cyan", width=20)
        score_table.add_column("Value", style="yellow", justify="right", width=10)
        
        score_table.add_row("Composite Score", f"{breakdown['composite']:.3f}")
        score_table.add_row("├─ Semantic", f"{breakdown['semantic']:.3f}")
        score_table.add_row("├─ Schema", f"{breakdown['schema']:.3f}")
        score_table.add_row("├─ Recency", f"{breakdown['recency']:.3f}")
        score_table.add_row("└─ Validation", f"{breakdown['validation']:.3f}")
        
        console.print(score_table)
        
        # Metadata info
        meta_table = Table(show_header=False, border_style="dim")
        meta_table.add_column("Field", style="dim cyan", width=20)
        meta_table.add_column("Value", style="white")
        
        meta_table.add_row("Device Type", pattern.metadata.device_type.value)
        meta_table.add_row("SW Version", pattern.metadata.sw_version)
        meta_table.add_row("Safety Class", pattern.metadata.safety_class.value)
        meta_table.add_row("Region", pattern.metadata.region)
        meta_table.add_row("Deployment Mode", pattern.metadata.deployment_mode.value)
        meta_table.add_row("Hardware Rev", pattern.metadata.hardware_revision)
        
        console.print(meta_table)
        
        # Key details
        console.print(f"[dim]Use Case:[/dim] {pattern.use_case}")
        console.print(f"[dim]Duration:[/dim] ~{pattern.estimated_duration_seconds}s")
        console.print(f"[dim]Validation Rules:[/dim] {len(pattern.validation_rules)}")
        console.print()


def display_response(response: AgentResponse):
    """Display agent response with all information."""
    # Show retrieved patterns if available
    if response.retrieved_patterns:
        display_ota_patterns(response.retrieved_patterns)
    
    # Show main message
    console.print(Panel(response.message, title="Agent Response", border_style="blue"))
    
    # Show deployment spec if generated
    if response.deployment_spec:
        console.print()
        if response.is_valid:
            display_deployment_spec(response.deployment_spec, "✓ Valid OTA Deployment Specification")
        else:
            display_deployment_spec(response.deployment_spec, "⚠ OTA Deployment Specification (needs review)")
    
    # Show validation results if any
    if response.validation_results:
        console.print("\n[yellow]Validation Results:[/yellow]")
        for key, value in response.validation_results.items():
            console.print(f"  • {key}: {value}")


def show_knowledge_base(agent: DSLAgent):
    """Show all patterns in knowledge base."""
    patterns = agent.kb.patterns
    
    console.print(f"\n[bold cyan]OTA Knowledge Base: {len(patterns)} Patterns[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta", border_style="cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", style="cyan", width=35)
    table.add_column("Device", style="white", width=12)
    table.add_column("Safety", style="yellow", width=8)
    table.add_column("Mode", style="green", width=12)
    table.add_column("Region", style="blue", width=6)
    
    for i, pattern in enumerate(patterns, 1):
        table.add_row(
            str(i),
            pattern.name[:32] + "..." if len(pattern.name) > 35 else pattern.name,
            pattern.metadata.device_type.value,
            pattern.metadata.safety_class.value,
            pattern.metadata.deployment_mode.value,
            pattern.metadata.region
        )
    
    console.print(table)


def show_statistics(agent: DSLAgent):
    """Show knowledge base statistics."""
    stats = agent.kb.get_statistics()
    
    console.print(f"\n[bold cyan]Knowledge Base Statistics[/bold cyan]\n")
    console.print(f"Total Patterns: {stats['total_patterns']}\n")
    
    # Device types
    device_table = Table(title="By Device Type", show_header=True, border_style="blue")
    device_table.add_column("Device Type", style="cyan")
    device_table.add_column("Count", justify="right", style="yellow")
    
    for device, count in stats['by_device_type'].items():
        device_table.add_row(device, str(count))
    
    console.print(device_table)
    console.print()
    
    # Safety classes
    safety_table = Table(title="By Safety Class", show_header=True, border_style="green")
    safety_table.add_column("Safety Class", style="cyan")
    safety_table.add_column("Count", justify="right", style="yellow")
    
    for safety, count in stats['by_safety_class'].items():
        safety_table.add_row(safety, str(count))
    
    console.print(safety_table)
    console.print()
    
    # Deployment modes
    mode_table = Table(title="By Deployment Mode", show_header=True, border_style="magenta")
    mode_table.add_column("Deployment Mode", style="cyan")
    mode_table.add_column("Count", justify="right", style="yellow")
    
    for mode, count in stats['by_deployment_mode'].items():
        mode_table.add_row(mode, str(count))
    
    console.print(mode_table)


def save_deployment_spec(response: AgentResponse, filename: str):
    """Save deployment specification to JSON file."""
    if not response.deployment_spec:
        console.print("[yellow]No deployment specification to save. Generate one first![/yellow]")
        return

    try:
        with open(filename, "w") as f:
            json.dump(response.deployment_spec, f, indent=2)
        console.print(f"[green]✓ Saved to {filename}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving file: {e}[/red]")


def get_metadata_from_user():
    """Interactively collect metadata for Stage 1 filtering."""
    console.print("\n[bold cyan]Stage 1: Metadata Collection (for filtering)[/bold cyan]\n")
    
    # ECU Type
    console.print("[cyan]ECU Types:[/cyan] infotainment, adas, powertrain, body_control, telematics, gateway")
    device_type_str = Prompt.ask("Device Type", default="infotainment")
    try:
        device_type = ECUType(device_type_str.lower())
    except ValueError:
        console.print(f"[yellow]Invalid device type, using 'infotainment'[/yellow]")
        device_type = ECUType.INFOTAINMENT
    
    # Software Version
    sw_version = Prompt.ask("Software Version (e.g., 3.2.1)", default="3.2.1")
    
    # Safety Class
    console.print("[cyan]Safety Classes:[/cyan] QM, ASIL_A, ASIL_B, ASIL_C, ASIL_D")
    safety_class_str = Prompt.ask("Safety Class", default="QM")
    try:
        safety_class = SafetyClass(safety_class_str.upper())
    except ValueError:
        console.print(f"[yellow]Invalid safety class, using 'QM'[/yellow]")
        safety_class = SafetyClass.QM
    
    # Region
    console.print("[cyan]Regions:[/cyan] US, EU, CN")
    region = Prompt.ask("Region", default="US").upper()
    
    # Hardware Revision
    hardware_revision = Prompt.ask("Hardware Revision (e.g., rev_C)", default="rev_C")
    
    # Deployment Mode (optional)
    console.print("[cyan]Deployment Modes (optional):[/cyan] A/B, dual-bank, delta, full")
    deployment_mode_str = Prompt.ask("Deployment Mode (press Enter to skip)", default="")
    deployment_mode = None
    if deployment_mode_str:
        try:
            deployment_mode = DeploymentMode(deployment_mode_str)
        except ValueError:
            console.print(f"[yellow]Invalid deployment mode, skipping[/yellow]")
    
    # Required Capabilities (optional)
    console.print("[cyan]Required Capabilities (comma-separated, optional):[/cyan] CAN_FD, Ethernet, 5G, GPS, etc.")
    capabilities_str = Prompt.ask("Capabilities (press Enter to skip)", default="")
    required_capabilities = None
    if capabilities_str:
        required_capabilities = set(cap.strip() for cap in capabilities_str.split(','))
    
    console.print("\n[green]✓ Metadata collected[/green]\n")
    
    return {
        'device_type': device_type,
        'sw_version': sw_version,
        'safety_class': safety_class,
        'region': region,
        'hardware_revision': hardware_revision,
        'deployment_mode': deployment_mode,
        'required_capabilities': required_capabilities
    }


def main():
    """Main CLI loop."""
    print_banner()

    # Initialize agent
    try:
        with console.status("[cyan]Loading OTA knowledge base and initializing agent...[/cyan]"):
            agent = DSLAgent()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Please create a .env file with your OPENAI_API_KEY[/yellow]")
        console.print("Example: cp .env.example .env")
        console.print("Then edit .env and add your API key")
        sys.exit(1)

    stats = agent.kb.get_statistics()
    console.print(f"[green]✓ Agent initialized with {stats['total_patterns']} OTA patterns![/green]")
    console.print(f"[dim]Device types: {len(stats['by_device_type'])}, Safety classes: {len(stats['by_safety_class'])}[/dim]\n")

    # Store metadata and last response
    current_metadata = None
    last_response = None

    while True:
        try:
            # Get user input
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]")

            if not user_input.strip():
                continue

            # Handle commands
            if user_input.startswith("/"):
                command_parts = user_input.split(maxsplit=1)
                command = command_parts[0].lower()

                if command == "/quit" or command == "/exit":
                    if Confirm.ask("Are you sure you want to exit?"):
                        console.print("[yellow]Goodbye![/yellow]")
                        break
                    continue

                elif command == "/help":
                    print_help()
                    continue

                elif command == "/reset":
                    if Confirm.ask("Reset conversation and start over?"):
                        agent._initialize_conversation()
                        current_metadata = None
                        last_response = None
                        console.print("[green]✓ Conversation reset![/green]")
                    continue

                elif command == "/show":
                    if last_response and last_response.deployment_spec:
                        display_deployment_spec(last_response.deployment_spec)
                    else:
                        console.print("[yellow]No deployment spec generated yet. Describe your OTA update needs first![/yellow]")
                    continue

                elif command == "/save":
                    if len(command_parts) < 2:
                        filename = Prompt.ask("Filename", default="ota_deployment.json")
                    else:
                        filename = command_parts[1]
                    if last_response:
                        save_deployment_spec(last_response, filename)
                    else:
                        console.print("[yellow]No deployment spec to save.[/yellow]")
                    continue

                elif command == "/knowledge":
                    show_knowledge_base(agent)
                    continue

                elif command == "/stats":
                    show_statistics(agent)
                    continue

                else:
                    console.print(f"[red]Unknown command: {command}[/red]")
                    console.print("Type /help for available commands")
                    continue

            # Regular conversation - collect metadata first if not already done
            if current_metadata is None:
                current_metadata = get_metadata_from_user()
            
            # Ask if user wants to use same metadata or update
            if Confirm.ask("Use same metadata as before?", default=True) if last_response else False:
                pass  # Keep current metadata
            elif last_response:  # Only ask if not first time
                if Confirm.ask("Update metadata?"):
                    current_metadata = get_metadata_from_user()

            # Process query with three-stage retrieval
            with console.status("[cyan]🔍 Stage 1: Filtering by metadata...[/cyan]"):
                try:
                    response = agent.chat(
                        user_message=user_input,
                        **current_metadata
                    )
                    last_response = response
                    console.print()
                    display_response(response)
                    console.print()
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()