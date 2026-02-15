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
    return (
        scores.get("security", 0) * 1.5 +
        scores.get("scalability", 0) * 1.2 +
        scores.get("novelty", 0) * 1.0 -
        scores.get("complexity", 0) * 1.0 -
        scores.get("cost", 0) * 0.8
    )


def run_reflection_on_variant(final_data: Dict, original_data: Dict, steps: List, intent: str) -> Dict:
    reflection_prompt = f"""
You are the Archivist of this pattern's evolution.
Review the full journey from original to final state.

Original pattern:
{json.dumps(original_data, indent=2)}

Final pattern:
{json.dumps(final_data, indent=2)}

All evolution steps:
{json.dumps(steps, indent=2)}

User intent: {intent}

Summarize in structured JSON:
{{
  "summary": "brief narrative overview",
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

    return reflection


def generate_visual_diff(original: Dict, top: Dict) -> Table:
    table = Table(title="Original vs Top Variant Diff")
    table.add_column("Component/Score", style="cyan")
    table.add_column("Original", style="white")
    table.add_column("Top Variant", style="green")
    table.add_column("Change", style="yellow")

    # Components diff
    all_components = set(original.get("components", {}).keys()) | set(top.get("components", {}).keys())
    for comp in sorted(all_components):
        orig_val = original.get("components", {}).get(comp, "-")
        top_val = top.get("components", {}).get(comp, "-")
        if orig_val == "-":
            change = "[green]+ Added[/green]"
        elif top_val == "-":
            change = "[red]- Removed[/red]"
        elif orig_val != top_val:
            change = f"[yellow]→ {top_val}[/yellow]"
        else:
            change = "-"
        table.add_row(f"Component: {comp}", str(orig_val), str(top_val), change)

    # Scores diff
    all_scores = set(original.get("scores", {}).keys()) | set(top.get("scores", {}).keys())
    for score in sorted(all_scores):
        orig_val = original.get("scores", {}).get(score, 0.0)
        top_val = top.get("scores", {}).get(score, 0.0)
        delta = top_val - orig_val
        if delta > 0:
            change = f"[green]+{delta:.1f}[/green]"
        elif delta < 0:
            change = f"[red]{delta:.1f}[/red]"
        else:
            change = "-"
        table.add_row(f"Score: {score}", f"{orig_val:.1f}", f"{top_val:.1f}", change)

    return table


def save_markdown_report(
    original_data: Dict,
    top_variant: Dict,
    all_variants_scores: List[float],
    reflection: Dict,
    intent: str,
    iterations: int,
    variants: int
):
    report = f"""# MagicalWeaver Evolution Report

**Intent**: {intent}
**Iterations per variant**: {iterations}
**Variants generated**: {variants}

## Variant Ranking
| Original Variant ID | Composite Score | Rank |
|---------------------|-----------------|------|
"""

    # Add ranking rows (you can copy from table logic if needed)
    for i, score in enumerate(sorted(all_variants_scores, reverse=True), 1):
        report += f"| Variant {i} | {score:.1f} | #{i} |\n"

    report += f"""

## Top Variant Selected
**Score**: {max(all_variants_scores):.1f}

## Visual Diff: Original vs Top Variant

| Component/Score | Original | Top Variant | Change |
|-----------------|----------|-------------|--------|
"""

    # Add diff rows
    all_components = set(original_data.get("components", {}).keys()) | set(top_variant.get("components", {}).keys())
    for comp in sorted(all_components):
        orig_val = original_data.get("components", {}).get(comp, "-")
        top_val = top_variant.get("components", {}).get(comp, "-")
        if orig_val == "-":
            change = "+ Added"
        elif top_val == "-":
            change = "- Removed"
        elif orig_val != top_val:
            change = f"→ {top_val}"
        else:
            change = "-"
        report += f"| Component: {comp} | {orig_val} | {top_val} | {change} |\n"

    all_scores = set(original_data.get("scores", {}).keys()) | set(top_variant.get("scores", {}).keys())
    for score in sorted(all_scores):
        orig_val = original_data.get("scores", {}).get(score, 0.0)
        top_val = top_variant.get("scores", {}).get(score, 0.0)
        delta = top_val - orig_val
        change = f"{delta:+.1f}" if delta != 0 else "-"
        report += f"| Score: {score} | {orig_val:.1f} | {top_val:.1f} | {change} |\n"

    report += f"""

## Archivist's Reflection on Top Variant

**Summary**  
{reflection.get('summary', 'No summary')}

**Strengths**  
{chr(10).join(f"- {s}" for s in reflection.get('strengths', [])) or '- None'}

**Risks/Tradeoffs**  
{chr(10).join(f"- {r}" for r in reflection.get('risks', [])) or '- None'}

**Overall Score Estimate**  
{reflection.get('overall_score_estimate', 0.0)}/10

**Confidence**  
{reflection.get('confidence', 0)}%

**Next Focus**  
{reflection.get('next_focus', 'No suggestion')}

Generated on {time.strftime("%Y-%m-%d %H:%M:%S")}
"""

    with open("evolution_report.md", "w", encoding="utf-8") as f:
        f.write(report)

    console.print("[bold green]Markdown report saved: evolution_report.md[/bold green]")


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
    sorted_results = sorted(enumerate(variant_results, 1), key=lambda x: x[1]["score"], reverse=True)

    table = Table(title="Variant Ranking")
    table.add_column("Original Variant ID", style="cyan")
    table.add_column("Composite Score", style="green")
    table.add_column("Rank", style="yellow")

    for rank, (orig_id, res) in enumerate(sorted_results, 1):
        style = "bold green" if rank == 1 else ""
        table.add_row(
            f"Variant {orig_id}",
            f"{res['score']:.1f}",
            f"#{rank}",
            style=style
        )

    console.print(table)

    winner_id = sorted_results[0][0]
    top_variant = sorted_results[0][1]
    console.print(f"[bold green]Top variant selected: Variant {winner_id} (score: {top_variant['score']:.1f})[/bold green]")

    # Visual diff
    diff_table = generate_visual_diff(original_data, top_variant["final_data"])
    console.print(diff_table)

    # Reflection on top variant
    console.print("\n[bold magenta]Final Reflection on Top Variant[/bold magenta]")
    reflection = run_reflection_on_variant(
        top_variant["final_data"],
        original_data,
        top_variant["steps"],
        intent
    )

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
        title="Archivist's Reflection (Top Variant)",
        border_style="magenta",
        expand=False
    ))

    # Save Markdown report
    save_markdown_report(
        original_data,
        top_variant["final_data"],
        [r["score"] for r in variant_results],
        reflection,
        intent,
        iterations,
        variants
    )

    return {
        "original_data": original_data,
        "top_variant": top_variant["final_data"],
        "all_variants_scores": [r["score"] for r in variant_results],
        "reflection": reflection,
        "status": "complete"
    }