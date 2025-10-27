#!/usr/bin/env python3
"""Terminal-based conversational agent for container-lang DSL generation."""

import sys
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.text import Text
from agent import DSLAgent


console = Console()


def print_banner():
    """Print welcome banner."""
    banner = """
╔══════════════════════════════════════════════════════════╗
║                                                          ║
║     Container-Lang DSL Conversational Agent              ║
║     Natural Language → DSL Code                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")
    console.print("Type your requirements in natural language.")
    console.print("Commands: /show, /validate, /save, /reset, /help, /quit\n")


def print_help():
    """Print help information."""
    help_text = """
# Available Commands

- **/show** - Display current generated DSL code
- **/validate** - Validate code with Rust parser
- **/save <filename>** - Save DSL code to file
- **/reset** - Start a new conversation
- **/help** - Show this help
- **/quit** - Exit the program

# Example Usage

```
You: I need a web server and database
Agent: [asks clarifying questions]
You: nginx on port 80 and postgres on 5432
Agent: [generates code]
You: /show
[displays DSL code]
You: /save myapp.container
```

# Tips

- Be specific about what you want to deploy
- Mention ports, environment variables, and volumes if needed
- The agent will ask for clarification when needed
- You can iterate on the design through conversation
"""
    console.print(Panel(Markdown(help_text), title="Help", border_style="blue"))


def display_code(code: str):
    """Display DSL code with syntax highlighting."""
    syntax = Syntax(code, "rust", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="Generated DSL Code", border_style="green"))


def display_response(response):
    """Display agent response."""
    # Print the message
    console.print(Panel(response.message, title="Agent", border_style="blue"))

    # If there's a program, show it
    if response.program:
        console.print()
        from dsl_generator import generate_dsl
        code = generate_dsl(response.program)
        display_code(code)


def save_code(agent: DSLAgent, filename: str):
    """Save current code to file."""
    code = agent.generate_code()
    if not code:
        console.print("[yellow]No code to save. Generate some DSL code first![/yellow]")
        return

    if "Validation errors" in code:
        console.print(f"[red]{code}[/red]")
        return

    try:
        with open(filename, "w") as f:
            f.write(code)
        console.print(f"[green]Saved to {filename}[/green]")
    except Exception as e:
        console.print(f"[red]Error saving file: {e}[/red]")


def find_parser():
    """Find the Rust parser executable."""
    # Look in the container-lang directory
    parser_paths = [
        "../container-lang/target/release/container-lang",
        "../container-lang/target/debug/container-lang",
    ]

    for path in parser_paths:
        full_path = Path(path).resolve()
        if full_path.exists():
            return str(full_path)

    return None


def validate_code(agent: DSLAgent):
    """Validate current code with Rust parser."""
    code = agent.generate_code()
    if not code:
        console.print("[yellow]No code to validate. Generate some DSL code first![/yellow]")
        return

    if "Validation errors" in code:
        console.print(f"[red]{code}[/red]")
        return

    parser_path = find_parser()
    if not parser_path:
        console.print("[yellow]Rust parser not found. Build it first:[/yellow]")
        console.print("  cd ../container-lang && cargo build --release")
        console.print("\n[cyan]Showing code without parser validation:[/cyan]")
        display_code(code)
        return

    is_valid, message = agent.validate_with_parser(code, parser_path)

    if is_valid:
        console.print(f"[green]{message}[/green]")
        display_code(code)
    else:
        console.print(f"[red]{message}[/red]")


def main():
    """Main CLI loop."""
    print_banner()

    # Initialize agent
    try:
        agent = DSLAgent()
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("[yellow]Please create a .env file with your OPENAI_API_KEY[/yellow]")
        console.print("Example: cp .env.example .env")
        console.print("Then edit .env and add your API key")
        sys.exit(1)

    console.print("[green]Agent initialized successfully![/green]\n")

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
                        agent.reset()
                        console.print("[green]Conversation reset![/green]")
                    continue

                elif command == "/show":
                    code = agent.generate_code()
                    if code:
                        if "Validation errors" in code:
                            console.print(f"[red]{code}[/red]")
                        else:
                            display_code(code)
                    else:
                        console.print("[yellow]No code generated yet. Have a conversation first![/yellow]")
                    continue

                elif command == "/validate":
                    validate_code(agent)
                    continue

                elif command == "/save":
                    if len(command_parts) < 2:
                        filename = Prompt.ask("Filename", default="output.container")
                    else:
                        filename = command_parts[1]
                    save_code(agent, filename)
                    continue

                else:
                    console.print(f"[red]Unknown command: {command}[/red]")
                    console.print("Type /help for available commands")
                    continue

            # Regular conversation
            with console.status("[cyan]Thinking...[/cyan]"):
                try:
                    response = agent.chat(user_input)
                    console.print()
                    display_response(response)
                    console.print()
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
                    console.print("[yellow]Please check your API key and internet connection[/yellow]")

        except KeyboardInterrupt:
            console.print("\n[yellow]Use /quit to exit[/yellow]")
            continue
        except EOFError:
            break


if __name__ == "__main__":
    main()
