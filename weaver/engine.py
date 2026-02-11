# weaver/engine.py
import json
import os
import ollama
from typing import Dict, Any, List

from rich.console import Console

console = Console()


def evolve_pattern(
    pattern_path: str,
    intent: str,
    iterations: int = 3
) -> Dict[str, Any]:
    """
    Core evolution function: loads pattern, runs varied mock steps,
    returns structured result.
    """
    # Validate file
    if not os.path.exists(pattern_path):
        raise FileNotFoundError(f"Pattern file not found: {pattern_path}")

    # Load JSON
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
        if "components" in data:
            console.print(f"[bold]Components found:[/bold] {list(data['components'].keys())}")
    else:
        console.print("[bold]Data type:[/bold] [list or other]")
    console.print(f"[bold]Intent:[/bold] {intent}")
    console.print(f"[dim]Running {iterations} evolution steps...[/dim]\n")

    # Prepare for mutations (safe access)
    components = data.get("components", {}) if isinstance(data, dict) else {}
    current_auth = components.get("auth", "unknown")

    # Possible mutation ideas (for variety)
    mutation_options = [
        f"upgrade auth from {current_auth} to Keycloak (better federation)",
        f"add observability layer (Prometheus + Grafana)",
        f"swap DB to PostgreSQL for better scalability",
        f"inject rate-limiting middleware (Redis-based)",
        f"replace caching with in-memory alternative"
    ]


    # Evolution steps with variety
    steps: List[Dict[str, str]] = []
    import random
    for step_num in range(1, iterations + 1):
        planned = random.choice(mutation_options)
        acted = f"applied mutation: {planned}"
        learned = f"robustness +{random.uniform(0.3, 0.8):.1f}, novelty +{random.uniform(0.8, 1.5):.1f} (mock)"
        step = {
            "step": step_num,
            "perceived": "current state",
            "planned": planned,
            "acted": acted,
            "learned": learned
        }
        steps.append(step)
        console.print(f"[cyan]Step {step_num}/{iterations}[/cyan]")
        console.print(f"  Perceived current state...")
        console.print(f"  Planned mutation: {planned}...")
        console.print(f"  Acted: {acted}")
        console.print(f"  Learned: {learned}\n") 

    return {
        "original_data": data,
        "intent": intent,
        "iterations": iterations,
        "evolution_steps": steps,
        "status": "complete"
    }