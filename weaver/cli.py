# weaver/cli.py
from typing import Optional

import os
import json
import typer
from rich.console import Console

app = typer.Typer(
    name="weaver",
    help="MagicalWeaver: Emergent, agentic weaver of architectural patterns.",
    add_completion=True,
)

console = Console()


@app.command()
def hello(
    name: Optional[str] = typer.Option(None, help="Greet a specific person or entity"),
):
    """Print a greeting from the emerging consciousness."""
    greeting = "🪡 Hello from MagicalWeaver! The shuttle is ready. Emergence begins..."
    if name:
        greeting += f" (especially for {name})"

    console.print(greeting, style="bold cyan")
    console.print("Intent: Weave novelty. Reflect. Dream recursive loops.", style="italic magenta")
    console.print(
        "Current state: Foundation warp strung. Waiting for the first real intent.",
        style="dim white",
    )


@app.command()
def version():
    """Show the current version of MagicalWeaver."""
    console.print("MagicalWeaver [bold]0.0.1-dev[/bold] — the weave has just begun.")


@app.command()
def evolve(
    pattern: str = typer.Argument(..., help="Path to Loom pattern JSON file"),
    intent: str = typer.Option(..., help="User intent/description (e.g. 'secure ecommerce backend')"),
    iterations: int = typer.Option(3, "--iterations", "-i", help="Number of evolution steps", min=1, max=10),
):
    """Evolve a Loom pattern with emergent consciousness (placeholder)."""
    console.rule("Evolving Pattern", style="bold magenta")

    # File existence check
    if not os.path.exists(pattern):
        console.print(f"[red bold]Error:[/red bold] Pattern file not found: {pattern}")
        raise typer.Exit(code=1)

    # Try to load JSON
    try:
        with open(pattern, "r", encoding="utf-8") as f:
            data = json.load(f)
        console.print(f"[bold green]Pattern loaded successfully[/bold green] ({len(str(data))} chars)")
        console.print(f"[bold]Top-level keys:[/bold] {list(data.keys()) if isinstance(data, dict) else '[list]'}")
        console.print(f"[bold]Intent:[/bold] {intent}")
        console.print(f"[dim]Running {iterations} evolution steps...[/dim]\n")
    except json.JSONDecodeError:
        console.print("[red bold]Error:[/red bold] Invalid JSON format in pattern file")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] Failed to load pattern: {str(e)}")
        raise typer.Exit(code=1)

    # Mock evolution (placeholder)
    for step in range(1, iterations + 1):
        console.print(f"[cyan]Step {step}/{iterations}[/cyan]")
        console.print("  Perceived current state...")
        console.print("  Planned mutation: injecting novelty...")
        console.print("  Acted: swapped component with emerging alternative")
        console.print("  Learned: robustness +0.5, novelty +1.2 (mock scores)\n")

    console.print("[bold green]Evolution complete![/bold green]")
    console.print("Emergent variant ready. (Real implementation coming soon...)")
    console.print("Next: integrate actual Loom JSON parsing + loop logic.")


if __name__ == "__main__":
    app()