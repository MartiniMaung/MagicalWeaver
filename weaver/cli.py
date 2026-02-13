# weaver/cli.py
from typing import Optional

import os
import json
import typer
from rich.console import Console
from weaver.engine import evolve_pattern   # we'll remove this later when using proper imports

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
    intent: str = typer.Option(..., help="User intent/description"),
    iterations: int = typer.Option(3, "--iterations", "-i", min=1, max=10),
    output: str = typer.Option("evolved.json", "--output", "-o", help="Save evolved pattern to this file")
):
    """Evolve a Loom pattern with emergent consciousness."""
    console.rule("Evolving Pattern", style="bold magenta")
    try:
        from weaver.engine import evolve_pattern
        result = evolve_pattern(pattern, intent, iterations)

        if result is None:
            console.print("[red]Error: No result returned from engine[/red]")
            raise typer.Exit(code=1)

        # Save result
        import json
        import os
        console.print(f"[yellow]DEBUG: Saving result (type: {type(result)})[/yellow]")
        with open(output, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        console.print(f"[bold green]Evolved pattern saved to:[/bold green] {output}")
        console.print(f"[dim]File size: {os.path.getsize(output)} bytes[/dim]")
        with open(output, "r", encoding="utf-8") as f:
            console.print("[dim]File preview (first 200 chars):[/dim]")
            console.print(f.read(200) + "...")

        console.print("Emergent variant ready.")
    except Exception as e:
        console.print(f"[red bold]Error:[/red bold] {str(e)}")
        raise typer.Exit(code=1)
           
if __name__ == "__main__":
    app()