# weaver/engine.py
import json
import os
import random
import time
from typing import Dict, Any, List

import ollama
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def evolve_pattern(
    pattern_path: str,
    intent: str,
    iterations: int = 3,
    temperature: float = 0.3
) -> Dict[str, Any]:
    """
    Core evolution function: loads pattern, runs LLM-powered steps,
    adds final reflection, returns structured result.
    """
    console.print(f"[bold green]Starting evolution for intent:[/bold green] {intent} (temp={temperature})")

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

    console.print(f"[bold green]Pattern loaded successfully[/bold green] ({len(str(data))} chars)")
    if isinstance(data, dict):
        console.print(f"[bold]Top-level keys:[/bold] {list(data.keys())}")
        if "components" in data:
            console.print(f"[bold]Components found:[/bold] {list(data['components'].keys())}")
    else:
        console.print("[bold]Data type:[/bold] [list or other]")
    console.print(f"[bold]Intent:[/bold] {intent}")
    console.print(f"[dim]Running {iterations} evolution steps...[/dim]\n")

    # Smart summary for large patterns
    def summarize_pattern(d: Dict) -> str:
        summary = []
        if "components" in d:
            summary.append(f"Components: {list(d['components'].keys())}")
        if "scores" in d:
            summary.append(f"Scores: {d['scores']}")
        return "; ".join(summary) or json.dumps(d, indent=2)[:1500]

    current_state_summary = summarize_pattern(data)

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

    steps: List[Dict[str, Any]] = []

    console.print("[yellow]DEBUG: Entering evolution loop...[/yellow]")

    for step_num in range(1, iterations + 1):
        console.print(f"[yellow]DEBUG: Step {step_num} started[/yellow]")

        prompt = f"""
You are an expert OSS architecture agent evolving a pattern.
Current pattern state summary:
{current_state_summary}

User intent: {intent}

Previous mutations:
{json.dumps(steps, indent=2) if steps else "None yet"}

Suggest ONE focused, realistic next mutation.
Improve security, scalability, novelty, cost, etc. based on intent.

Output **JSON only** — no explanations, no markdown, no code fences, no extra text.
Use this exact schema (include only fields that apply):

{{
  "planned": "short clear description of the change",
  "acted": "how it was applied",
  "learned": "estimated impact string (e.g. security +1.2, complexity +0.4)",
  "add_component": {{"name": "component_name", "value": "details or config string"}}   // optional
  "update_score": {{"key1": +1.2, "key2": -0.5}}   // optional, deltas only
  "remove_component": "component_name_to_remove"   // optional
}}
"""

        console.print("[yellow]DEBUG: Prompt built[/yellow]")

        planned = "No suggestion"
        acted = "applied"
        learned = "impact estimated"

        mutation = None
        for attempt in range(2):
            try:
                console.print(f"[yellow]DEBUG: Calling Ollama (attempt {attempt+1})...[/yellow]")
                response = ollama.chat(
                    model='llama3.1:8b',
                    messages=[{'role': 'user', 'content': prompt}],
                    options={'temperature': temperature}
                )
                llm_text = response['message']['content'].strip()
                console.print(f"[yellow]DEBUG: Raw LLM text (first 200 chars):[/yellow] {llm_text[:200]}...")

                llm_text = llm_text.strip()
                if llm_text.startswith('```json') or llm_text.startswith('```'):
                    parts = llm_text.split('```', 2)
                    if len(parts) > 1:
                        llm_text = parts[1].strip()
                llm_text = llm_text.split('\n\n', 1)[0].strip()
                llm_text = llm_text.replace(',\n}', '\n}')

                start = llm_text.find('{')
                end = llm_text.rfind('}') + 1
                if start == -1 or end == 0:
                    raise ValueError("No JSON block found")

                json_str = llm_text[start:end]
                console.print(f"[yellow]DEBUG: Cleaned JSON string:[/yellow] {json_str[:100]}...")

                mutation = json.loads(json_str)

                planned = mutation.get("planned", "No suggestion")
                acted = mutation.get("acted", "applied")
                learned = mutation.get("learned", "impact estimated")

                console.print("[yellow]DEBUG: Mutation parsed OK[/yellow]")
                break

            except Exception as e:
                console.print(f"[red bold]Attempt {attempt+1} failed: {str(e)}[/red bold]")
                time.sleep(1)
                if attempt == 1:
                    console.print("[red bold]Giving up — using fallback[/red bold]")
                    planned = random.choice(mutation_options)
                    acted = f"applied fallback: {planned}"
                    learned = f"robustness +{random.uniform(0.3, 0.8):.1f}, novelty +{random.uniform(0.8, 1.5):.1f} (mock)"
                    mutation = {}

        console.print(f"[cyan]Step {step_num}/{iterations}[/cyan]")
        console.print(f"  Perceived current state...")
        console.print(f"  Planned mutation: {planned}...")
        console.print(f"  Acted: {acted}")
        console.print(f"  Learned: {learned}\n")

        data = apply_llm_mutation(data, mutation, planned, learned)
        console.print(f"[dim]Updated components after step {step_num}: {data.get('components', {})}[/dim]")
        console.print(f"[dim]Updated scores: {data.get('scores', {})}[/dim]\n")

        current_state_summary = summarize_pattern(data)
        steps.append({
            "step": step_num,
            "perceived": "current state",
            "planned": planned,
            "acted": acted,
            "learned": learned
        })

    # Final Reflection
    console.print("\n[bold magenta]Final Reflection[/bold magenta]")
    reflection_prompt = f"""
You are the Archivist of this pattern's evolution.
Review the full journey from original to final state.

Original pattern:
{json.dumps(original_data, indent=2)}

Final pattern:
{json.dumps(data, indent=2)}

All evolution steps:
{json.dumps(steps, indent=2)}

User intent: {intent}

Summarize in structured JSON:
{{
  "summary": "brief narrative overview of the evolution",
  "strengths": ["3-5 key emergent strengths"],
  "risks": ["2-4 main risks or tradeoffs"],
  "overall_score_estimate": 8.5,
  "confidence": 85,
  "next_focus": "recommended next mutation or direction"
}}
"""

    reflection = {
        "summary": "Reflection failed",
        "strengths": [],
        "risks": [],
        "overall_score_estimate": 0.0,
        "confidence": 0,
        "next_focus": "No suggestion"
    }

    try:
        response = ollama.chat(
            model='llama3.1:8b',
            messages=[{'role': 'user', 'content': reflection_prompt}],
            options={'temperature': 0.2}
        )
        text = response['message']['content'].strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end != 0:
            reflection = json.loads(text[start:end])
    except Exception as e:
        console.print(f"[red]Reflection error:[/red] {str(e)}")

    console.print(Panel(
        Text.assemble(
            ("Summary:\n", "bold magenta"),
            f"{reflection.get('summary', 'No summary')}\n\n",
            ("Strengths:\n", "bold green"),
            "\n".join(f"  • {s}" for s in reflection.get("strengths", [])) + "\n\n",
            ("Risks/Tradeoffs:\n", "bold red"),
            "\n".join(f"  • {r}" for r in reflection.get("risks", [])) + "\n\n",
            ("Overall Score Estimate:", "bold cyan"),
            f" {reflection.get('overall_score_estimate', 0.0)}/10\n",
            ("Confidence:", "bold cyan"),
            f" {reflection.get('confidence', 0)}%\n",
            ("Next Focus:", "bold yellow"),
            f" {reflection.get('next_focus', 'No suggestion')}"
        ),
        title="Archivist's Reflection",
        border_style="magenta",
        expand=False
    ))

    console.print("[bold green]Evolution complete![/bold green]")

    return {
        "original_data": original_data,
        "final_data": data,
        "intent": intent,
        "iterations": iterations,
        "evolution_steps": steps,
        "reflection": reflection,
        "status": "complete"
    }


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


def summarize_pattern(d: Dict) -> str:
    summary = []
    if "components" in d:
        summary.append(f"Components: {list(d['components'].keys())}")
    if "scores" in d:
        summary.append(f"Scores: {d['scores']}")
    return "; ".join(summary) or json.dumps(d, indent=2)[:1500]