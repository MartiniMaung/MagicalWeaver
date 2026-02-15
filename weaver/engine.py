# weaver/engine.py
import json
import os
import random
import time
from typing import Dict, Any, List

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def summarize_pattern(d: Dict) -> str:
    summary = []
    if "components" in d:
        summary.append(f"Components: {list(d['components'].keys())}")
    if "scores" in d:
        summary.append(f"Scores: {d['scores']}")
    return "; ".join(summary) or json.dumps(d, indent=2)[:1500]


def apply_llm_mutation(data: Dict, mutation: Dict = None, planned: str = "", learned: str = "") -> Dict:
    mutated = data.copy()
    if "components" not in mutated:
        mutated["components"] = {}
    if "scores" not in mutated:
        mutated["scores"] = {}

    if mutation:
        if "add_component" in mutation:
            add = mutation["add_component"]
            name = add.get("name")
            value = add.get("value", "added")
            if name:
                mutated["components"][name] = value
                console.print(f"[dim]Added component: {name} = {value}[/dim]")

        if "remove_component" in mutation:
            remove = mutation["remove_component"]
            if remove in mutated["components"]:
                del mutated["components"][remove]
                console.print(f"[dim]Removed component: {remove}[/dim]")

        if "update_score" in mutation:
            for key, delta in mutation["update_score"].items():
                try:
                    mutated["scores"][key] = mutated["scores"].get(key, 0) + float(delta)
                    console.print(f"[dim]Updated score {key}: {mutated['scores'][key]} (delta {delta})[/dim]")
                except:
                    pass

    planned_lower = planned.lower()
    if "redis" in planned_lower or "rate limit" in planned_lower:
        mutated["components"]["rate_limiter"] = "Redis"
    elif "opa" in planned_lower or "policy" in planned_lower:
        mutated["components"]["policy_engine"] = "OPA"
    elif "elk" in planned_lower or "logging" in planned_lower or "monitoring" in planned_lower:
        mutated["components"]["monitoring"] = "ELK Stack"
    elif "tls" in planned_lower or "encryption" in planned_lower or "hsm" in planned_lower:
        mutated["components"]["tls_hsm"] = "Hardware Security Module"
    elif "istio" in planned_lower or "service mesh" in planned_lower:
        mutated["components"]["service_mesh"] = "Istio"

    try:
        import re
        for match in re.finditer(r'(\w+):?\s*([+-]?\d+\.?\d*)', learned):
            key = match.group(1).strip().lower()
            value = float(match.group(2))
            mutated["scores"][key] = mutated["scores"].get(key, 0) + value
    except:
        pass

    return mutated


def evolve_single_variant(
    original_data: Dict,
    intent: str,
    iterations: int,
    temperature: float = 0.3,
    variant_id: int = 1
) -> Dict[str, Any]:
    """Run one independent evolution variant."""
    data = original_data.copy()
    current_state_summary = summarize_pattern(data)
    steps = []
    mutation_options = [
        "upgrade auth to Keycloak",
        "add observability (Prometheus + Grafana)",
        "swap DB to PostgreSQL",
        "inject Redis rate-limiting",
        "add Istio service mesh"
    ]

    console.print(f"[bold cyan]Variant {variant_id} starting...[/bold cyan]")

    for step_num in range(1, iterations + 1):
        prompt = f"""
You are an expert OSS architecture agent evolving a pattern.
Current pattern state summary:
{current_state_summary}

User intent: {intent}

Previous mutations:
{json.dumps(steps, indent=2) if steps else "None yet"}

Suggest ONE focused, realistic next mutation.

Output **JSON only**:

{{
  "planned": "short description",
  "acted": "how applied",
  "learned": "impact (e.g. security +1.2)",
  "add_component": {{"name": "name", "value": "details"}}   // optional
  "update_score": {{"key": +value}}   // optional
  "remove_component": "name"   // optional
}}
"""

        planned = "No suggestion"
        acted = "applied"
        learned = "impact estimated"

        mutation = None
        for attempt in range(2):
            try:
                response = ollama.chat(
                    model='llama3.1:8b',
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'temperature': temperature}
                )
                llm_text = response['message']['content'].strip()

                llm_text = llm_text.strip()
                if llm_text.startswith('```'):
                    llm_text = llm_text.split('```', 2)[1].strip()
                llm_text = llm_text.split('\n\n', 1)[0].strip()

                start = llm_text.find('{')
                end = llm_text.rfind('}') + 1
                if start == -1 or end == 0:
                    raise ValueError("No JSON")

                json_str = llm_text[start:end]
                mutation = json.loads(json_str)

                planned = mutation.get("planned", "No suggestion")
                acted = mutation.get("acted", "applied")
                learned = mutation.get("learned", "impact estimated")
                break
            except Exception as e:
                console.print(f"[dim]Variant {variant_id} attempt {attempt+1} failed: {str(e)}[/dim]")
                if attempt == 1:
                    planned = random.choice(mutation_options)
                    acted = f"fallback: {planned}"
                    learned = "robustness +0.5, novelty +1.0 (mock)"
                    mutation = {}

        data = apply_llm_mutation(data, mutation, planned, learned)
        current_state_summary = summarize_pattern(data)
        steps.append({"step": step_num, "planned": planned, "acted": acted, "learned": learned})

        console.print(f"[dim]Variant {variant_id} step {step_num}: {planned[:60]}...[/dim]")

    final_score = calculate_composite_score(data.get("scores", {}))
    console.print(f"[bold cyan]Variant {variant_id} finished. Composite score: {final_score:.1f}[/bold cyan]")

    return {
        "final_data": data,
        "steps": steps,
        "score": final_score
    }


def calculate_composite_score(scores: Dict) -> float:
    """Higher = better. Weights can be tuned later."""
    return (
        scores.get("security", 0) * 1.5 +
        scores.get("scalability", 0) * 1.2 +
        scores.get("novelty", 0) * 1.0 -
        scores.get("complexity", 0) * 1.0 -
        scores.get("cost", 0) * 0.8
    )


def evolve_pattern(
    pattern_path: str,
    intent: str,
    iterations: int = 3,
    variants: int = 3,
    temperature: float = 0.3
) -> Dict[str, Any]:
    if not os.path.exists(pattern_path):
        raise FileNotFoundError(f"Pattern file not found: {pattern_path}")

    try:
        with open(pattern_path, "r", encoding="utf-8") as f:
            original_data = json.load(f)
    except Exception as e:
        raise RuntimeError(f"Failed to load pattern: {str(e)}")

    console.print(f"[bold green]Starting multi-variant evolution[/bold green] ({variants} variants, intent: {intent})")

    variant_results = []

    for v in range(1, variants + 1):
        result = evolve_single_variant(original_data, intent, iterations, temperature, v)
        variant_results.append(result)

    # Rank and select top
    variant_results.sort(key=lambda x: x["score"], reverse=True)
    top_variant = variant_results[0]

    table = Table(title="Variant Ranking")
    table.add_column("Variant", style="cyan")
    table.add_column("Composite Score", style="green")
    for i, res in enumerate(variant_results, 1):
        table.add_row(f"Variant {i}", f"{res['score']:.1f}")
    console.print(table)

    console.print(f"[bold green]Top variant selected (score: {top_variant['score']:.1f})[/bold green]")

    return {
        "original_data": original_data,
        "top_variant": top_variant["final_data"],
        "all_variants_scores": [r["score"] for r in variant_results],
        "status": "complete"
    }