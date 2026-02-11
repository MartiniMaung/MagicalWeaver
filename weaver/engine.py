# weaver/engine.py
import json
import os
import ollama
import random
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


    # Evolution steps with Ollama LLM planning
    steps: List[Dict[str, str]] = []
    current_state_summary = json.dumps(data, indent=2)[:1500]  # safe truncate

    for step_num in range(1, iterations + 1):
        prompt = f"""
You are an expert OSS architecture agent evolving a pattern.
Current pattern state (JSON):
{current_state_summary}

User intent: {intent}

Previous mutations:
{json.dumps(steps, indent=2) if steps else "None yet"}

Suggest ONE focused, realistic next mutation.
Improve security, scalability, novelty, cost, etc. based on intent.
Output **JSON only**, no extra text:
{{
  "planned": "short clear description of the change",
  "acted": "how it was applied",
  "learned": "estimated impact (e.g. security +1.2, complexity +0.4)"
}}
"""

        try:
            response = ollama.chat(
                model='llama3.1:8b',
                messages=[{'role': 'user', 'content': prompt}]
            )
            llm_text = response['message']['content'].strip()

            # More robust parsing: try to extract JSON block if LLM adds extra text
            start = llm_text.find('{')
            end = llm_text.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = llm_text[start:end]
            else:
                json_str = llm_text

            mutation = json.loads(json_str)

            planned = mutation.get("planned", "No suggestion from LLM")
            acted = mutation.get("acted", "applied LLM suggestion")
            learned = mutation.get("learned", "impact estimated")

        except Exception as e:
            console.print(f"[yellow]Ollama error:[/yellow] {str(e)} — fallback to mock")
            planned = random.choice(mutation_options)
            acted = f"applied fallback: {planned}"
            learned = f"robustness +{random.uniform(0.3, 0.8):.1f}, novelty +{random.uniform(0.8, 1.5):.1f} (mock)"  
  
    return {
        "original_data": data,
        "intent": intent,
        "iterations": iterations,
        "evolution_steps": steps,
        "status": "complete"
    }