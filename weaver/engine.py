# weaver/engine.py
import json
import os
import random
from typing import Dict, Any, List

import ollama
from rich.console import Console

console = Console()


def evolve_pattern(
    pattern_path: str,
    intent: str,
    iterations: int = 3
) -> Dict[str, Any]:
    """
    Core evolution function: loads pattern, runs LLM-powered steps,
    returns structured result.
    """
    console.print(f"[bold green]Starting evolution for intent:[/bold green] {intent}")

    # Validate file
    if not os.path.exists(pattern_path):
        raise FileNotFoundError(f"Pattern file not found: {pattern_path}")

    # Load JSON
    try:
        with open(pattern_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        original_data = data.copy()
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

    # Prepare summary for LLM
    current_state_summary = json.dumps(data, indent=2)[:1500]

    # Fallback mutation options
    components = data.get("components", {}) if isinstance(data, dict) else {}
    current_auth = components.get("auth", "unknown")
    mutation_options = [
        f"upgrade auth from {current_auth} to Keycloak (better federation)",
        f"add observability layer (Prometheus + Grafana)",
        f"swap DB to PostgreSQL for better scalability",
        f"inject rate-limiting middleware (Redis-based)",
        f"replace caching with in-memory alternative"
    ]

    steps: List[Dict[str, str]] = []

    console.print("[yellow]DEBUG: Entering evolution loop...[/yellow]")

    for step_num in range(1, iterations + 1):
        console.print(f"[yellow]DEBUG: Step {step_num} started[/yellow]")

        prompt = f"""
You are an expert OSS architecture agent evolving a pattern.
Current pattern state (JSON):
{current_state_summary}

User intent: {intent}

Previous mutations:
{json.dumps(steps, indent=2) if steps else "None yet"}

Suggest ONE focused, realistic next mutation.
Improve security, scalability, novelty, cost, etc. based on intent.
Output **JSON only**, no extra text or explanations:
{{
  "planned": "short clear description of the change",
  "acted": "how it was applied",
  "learned": "estimated impact (e.g. security +1.2, complexity +0.4)"
}}
"""
        console.print("[yellow]DEBUG: Calling Ollama...[/yellow]")
        try:
            response = ollama.chat(
                model='llama3.1:8b',
                messages=[{'role': 'user', 'content': prompt}]
            )
            llm_text = response['message']['content'].strip()
            console.print(f"[yellow]DEBUG: Raw LLM text (first 200 chars):[/yellow] {llm_text[:200]}...")

            # Super aggressive cleanup
            llm_text = llm_text.strip()
            # Remove code fences
            if llm_text.startswith('```json') or llm_text.startswith('```'):
                llm_text = llm_text.split('```', 2)[1].strip() if '```' in llm_text[3:] else llm_text
            # Remove trailing garbage
            llm_text = llm_text.split('\n\n', 1)[0].strip()  # cut after first double newline if present
            # Fix common trailing commas
            llm_text = llm_text.replace(',\n}', '\n}')

            start = llm_text.find('{')
            end = llm_text.rfind('}') + 1
            if start == -1 or end == 0:
                raise ValueError("No JSON block found in response")

            json_str = llm_text[start:end]
            console.print(f"[yellow]DEBUG: Cleaned JSON string:[/yellow] {json_str[:100]}...")

            mutation = json.loads(json_str)

            planned = mutation.get("planned", "No suggestion from LLM")
            acted = mutation.get("acted", "applied LLM suggestion")
            learned = mutation.get("learned", "impact estimated")

            console.print("[yellow]DEBUG: Mutation parsed OK[/yellow]")

        except Exception as e:
            console.print(f"[red bold]Ollama / parse error:[/red bold] {str(e)} — fallback to mock")
            planned = random.choice(mutation_options)
            acted = f"applied fallback: {planned}"
            learned = f"robustness +{random.uniform(0.3, 0.8):.1f}, novelty +{random.uniform(0.8, 1.5):.1f} (mock)"

        console.print(f"[cyan]Step {step_num}/{iterations}[/cyan]")
        console.print(f"  Perceived current state...")
        console.print(f"  Planned mutation: {planned}...")
        console.print(f"  Acted: {acted}")
        console.print(f"  Learned: {learned}\n")

        # Apply the mutation to the running data
        data = apply_llm_mutation(data, planned, learned)
        console.print(f"[dim]Updated components after step {step_num}: {data.get('components', {})}[/dim]")
        console.print(f"[dim]Updated scores: {data.get('scores', {})}[/dim]\n")

        current_state_summary += f"\nStep {step_num}: {planned}"
        steps.append({
            "step": step_num,
            "perceived": "current state",
            "planned": planned,
            "acted": acted,
            "learned": learned
        })

    console.print("[bold green]Evolution complete![/bold green]")

    return {
        "original_data": original_data,
        "final_data": data,
        "intent": intent,
        "iterations": iterations,
        "evolution_steps": steps,
        "status": "complete"
    }
 
def apply_llm_mutation(data: Dict, planned: str, learned: str) -> Dict:
    mutated = data.copy()
    if "components" not in mutated:
        mutated["components"] = {}

    planned_lower = planned.lower()

    # Keyword-based updates (expand as needed)
    if "redis" in planned_lower or "rate limit" in planned_lower:
        mutated["components"]["rate_limiter"] = "Redis"
    elif "opa" in planned_lower or "policy" in planned_lower:
        mutated["components"]["policy_engine"] = "OPA"
    elif "elk" in planned_lower or "logging" in planned_lower or "monitoring" in planned_lower:
        mutated["components"]["monitoring"] = "ELK Stack"
    elif "tls" in planned_lower or "encryption" in planned_lower or "hsm" in planned_lower:
        mutated["components"]["tls_hsm"] = "Hardware Security Module"
    elif "jwt" in planned_lower or "token" in planned_lower:
        mutated["components"]["token_auth"] = "JWT"

    # Parse learned for score updates
    if "scores" not in mutated:
        mutated["scores"] = {}
    try:
        import re
        for match in re.finditer(r'(\w+):?\s*([+-]?\d+\.?\d*)', learned):
            key = match.group(1).strip().lower()
            value = float(match.group(2))
            mutated["scores"][key] = mutated["scores"].get(key, 0) + value
    except Exception as e:
        console.print(f"[yellow]Score parse warning:[/yellow] {str(e)}")

    return mutated