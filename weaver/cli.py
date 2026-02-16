# weaver/cli.py
import typer
from weaver.engine import (
    evolve_pattern,
    list_history,
    resurrect_run
)

app = typer.Typer()


@app.command()
def evolve(
    pattern: str = typer.Argument(..., help="Path to starting pattern JSON"),
    intent: str = typer.Option(..., "--intent", "-i", help="User intent"),
    iterations: int = typer.Option(3, "--iterations", "-n", help="Steps per variant"),
    output: str = typer.Option("my-evolved.json", "--output", "-o", help="Output JSON")
):
    """Evolve a pattern with multi-variant generation."""
    result = evolve_pattern(pattern, intent, iterations=iterations)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    typer.echo(f"Evolved pattern saved to: {output}")


@app.command()
def history():
    """List past evolution runs from history DB."""
    list_history()


@app.command()
def resurrect(run_id: int):
    """Resurrect and display a past run from history DB."""
    resurrect_run(run_id)


if __name__ == "__main__":
    app()