# weaver/engine.py
import json
import os
from typing import Dict, Any, List

from rich.console import Console

console = Console()


def evolve_pattern(
    pattern_path: str,
    intent: str,
    iterations: int = 3
) -> Dict[str, Any]:
    """
    Core function to evolve a pattern: load JSON, run mock steps,
    return structured result (for CLI display, saving, or future extensions).
    """
    # 1. Validate file existence
    if not os.path.exists(pattern_path):
        raise FileNotFoundError(f"Pattern file not found: {pattern_path}")

    # 2. Load JSON
    try:
        with open(pattern_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in pattern file")
    except Exception as e:
        raise RuntimeError(f"Failed to load pattern: {str(e)}")

    # Display loading info
    console.print(f"[bold green]Pattern loaded successfully[/bold green] ({len(str(data))} chars)")
    if isinstance(data, dict):
        console.print(f"[bold]Top-level keys:[/bold] {list(data.keys())}")
    else:
        console.print("[bold]Data type:[/bold] [list or other]")
    console.print(f"[bold]Intent:[/bold] {intent}")
    console.print(f"[dim]Running {iterations} evolution steps...[/dim]\n")

    # 3. Mock evolution steps (placeholder for real mutations/reflection)
    steps: List[Dict[str, str]] = []
    for step_num in range(1, iterations + 1):
        step = {
            "step": step_num,
            "perceived": "current state",
            "planned": "injecting novelty",
            "acted": "swapped component with emerging alternative",
            "learned": "robustness +0.5, novelty +1.2 (mock scores)"
        }
        steps.append(step)

        console.print(f"[cyan]Step {step_num}/{iterations}[/cyan]")
        console.print(f"  Perceived {step['perceived']}...")
        console.print(f"  Planned mutation: {step['planned']}...")
        console.print(f"  Acted: {step['acted']}")
        console.print(f"  Learned: {step['learned']}\n")

    console.print("[bold green]Evolution complete![/bold green]")

    # Return structured result
    return {
        "original_data": data,
        "intent": intent,
        "iterations": iterations,
        "evolution_steps": steps,
        "status": "complete"
    }