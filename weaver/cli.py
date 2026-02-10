# weaver/cli.py
from typing import Optional

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

if __name__ == "__main__":
    app()