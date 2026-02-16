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
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

console = Console()

Base = declarative_base()


class EvolutionRun(Base):
    __tablename__ = "evolution_runs"

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=func.now())
    intent = Column(String)
    iterations = Column(Integer)
    variants = Column(Integer)
    top_score = Column(Integer)
    top_variant_components = Column(Text)  # JSON string
    reflection_summary = Column(Text)
    reflection_json = Column(Text)  # full reflection dict as JSON

    def __repr__(self):
        return f"<Run {self.id}: {self.intent} - {self.timestamp}>"


# SQLite setup
DB_PATH = "weaver_history.db"
engine = create_engine(f"sqlite:///{DB_PATH}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


def save_run_to_db(
    original_data: Dict,
    top_variant: Dict,
    all_variants_scores: List[float],
    reflection: Dict,
    intent: str,
    iterations: int,
    variants: int
):
    try:
        session = Session()
        run = EvolutionRun(
            intent=intent,
            iterations=iterations,
            variants=variants,
            top_score=max(all_variants_scores) if all_variants_scores else 0,
            top_variant_components=json.dumps(top_variant.get("components", {})),
            reflection_summary=reflection.get("summary", "No summary"),
            reflection_json=json.dumps(reflection)
        )
        session.add(run)
        session.commit()
        console.print(f"[bold green]Run saved to history DB (ID: {run.id})[/bold green]")
    except SQLAlchemyError as e:
        console.print(f"[red]DB save failed: {str(e)}[/red]")
    finally:
        session.close()


def list_history(limit: int = 10):
    try:
        session = Session()
        runs = session.query(EvolutionRun).order_by(EvolutionRun.timestamp.desc()).limit(limit).all()
        if not runs:
            console.print("[yellow]No history yet.[/yellow]")
            return

        table = Table(title="Evolution History")
        table.add_column("ID", style="cyan")
        table.add_column("Date", style="magenta")
        table.add_column("Intent", style="green")
        table.add_column("Top Score", style="yellow")
        table.add_column("Summary", style="white")

        for run in runs:
            table.add_row(
                str(run.id),
                run.timestamp.strftime("%Y-%m-%d %H:%M"),
                run.intent[:40] + "..." if len(run.intent) > 40 else run.intent,
                f"{run.top_score:.1f}",
                run.reflection_summary[:60] + "..." if len(run.reflection_summary) > 60 else run.reflection_summary
            )

        console.print(table)
    except SQLAlchemyError as e:
        console.print(f"[red]History query failed: {str(e)}[/red]")
    finally:
        session.close()


def resurrect_run(run_id: int):
    try:
        session = Session()
        run = session.query(EvolutionRun).filter_by(id=run_id).first()
        if not run:
            console.print(f"[red]Run ID {run_id} not found.[/red]")
            return

        console.print(f"[bold magenta]Resurrecting Run #{run.id} ({run.timestamp})[/bold magenta]")
        console.print(f"Intent: {run.intent}")
        console.print(f"Top Score: {run.top_score:.1f}")
        console.print(f"\nTop Variant Components:\n{json.dumps(json.loads(run.top_variant_components), indent=2)}")
        console.print(f"\nReflection Summary: {run.reflection_summary}")
        console.print(f"\nFull Reflection JSON:\n{json.dumps(json.loads(run.reflection_json), indent=2)}")
    except SQLAlchemyError as e:
        console.print(f"[red]Resurrect failed: {str(e)}[/red]")
    finally:
        session.close()

def summarize_pattern(d: Dict) -> str:
    """
    Smart summary of pattern state for LLM prompt (limits size).
    """
    summary = []
    if "components" in d:
        comps = list(d["components"].keys())
        summary.append(f"Components: {comps}")
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

    # Variant flavor/temp
    flavor = ""
    if variant_id == 1:
        flavor = "Focus on reliable, proven solutions with low risk."
        temp = 0.1
    elif variant_id == 2:
        flavor = "Balance security, performance, and maintainability."
        temp = 0.4
    else:
        flavor = "Push for novelty, cutting-edge ideas, and maximum emergence."
        temp = 0.7

    console.print(f"[bold cyan]Variant {variant_id} starting...[/bold cyan] (flavor: {flavor}, temp={temp})")

    novelty_count = 0

    for step_num in range(1, iterations + 1):
        prompt = f"""
You are an expert OSS architecture agent evolving a pattern.
Current pattern state summary:
{current_state_summary}

User intent: {intent}

Previous mutations:
{json.dumps(steps, indent=2) if steps else "None yet"}

Flavor for this variant: {flavor}

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
                    options={'temperature': temp}
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

        if is_novel_mutation(planned, learned):
            novelty_count += 1
            console.print(f"[yellow dim]Novel step detected (bonus potential)[/yellow dim]")

        current_state_summary = summarize_pattern(data)
        steps.append({"step": step_num, "planned": planned, "acted": acted, "learned": learned})

        console.print(f"[dim]Variant {variant_id} step {step_num}: {planned[:60]}...[/dim]")

    base_score = calculate_composite_score(data.get("scores", {}))
    novelty_bonus = novelty_count * 1.0
    final_score = base_score + novelty_bonus
    console.print(f"[bold cyan]Variant {variant_id} finished. Base: {base_score:.1f} + novelty bonus: {novelty_bonus:.1f} = {final_score:.1f}[/bold cyan]")

    return {
        "final_data": data,
        "steps": steps,
        "score": final_score,
        "novelty_count": novelty_count
    }

def is_novel_mutation(planned: str, learned: Any) -> bool:
    """Check if this step was novel/creative. Handles learned as str or dict."""
    text_parts = [planned.lower()]

    if isinstance(learned, str):
        text_parts.append(learned.lower())
    elif isinstance(learned, dict):
        # Convert dict to string representation for keyword search
        learned_str = " ".join(f"{k} {v}" for k, v in learned.items())
        text_parts.append(learned_str.lower())

    full_text = " ".join(text_parts)

    novelty_keywords = [
        "novel", "cutting-edge", "experimental", "emergent", "innovative",
        "eBPF", "cilium", "falco", "tdx", "sev", "spiffe", "spire",
        "linkerd", "rust", "confidential", "oauth 2.1", "par", "rar", "dpop",
        "wasm", "ai-driven", "machine learning", "zero-trust", "spiffe/spire"
    ]

    return any(kw.lower() in full_text for kw in novelty_keywords)   

def calculate_composite_score(scores: Dict) -> float:
    return (
        scores.get("security", 0) * 1.5 +
        scores.get("scalability", 0) * 1.2 +
        scores.get("novelty", 0) * 1.0 -
        scores.get("complexity", 0) * 1.0 -
        scores.get("cost", 0) * 0.8
    )

def save_all_variants(variant_results: List[Dict], output_path: str = "all-variants.json"):
    all_data = []
    for v, res in enumerate(variant_results, 1):
        all_data.append({
            "variant_id": v,
            "final_data": res["final_data"],
            "steps": res["steps"],
            "score": res["score"],
            "novelty_count": res["novelty_count"]
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2)

    console.print(f"[bold green]All {len(variant_results)} variants saved to {output_path}[/bold green]")

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
        console.print(f"[red]Reflection error: {str(e)}[/red]")

    return reflection


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

    sorted_results = sorted(enumerate(variant_results, 1), key=lambda x: x[1]["score"], reverse=True)

    table = Table(title="Variant Ranking")
    table.add_column("Original Variant ID", style="cyan")
    table.add_column("Composite Score", style="green")
    table.add_column("Novelty Bonus", style="magenta")
    table.add_column("Rank", style="yellow")

    for rank, (orig_id, res) in enumerate(sorted_results, 1):
        style = "bold green" if rank == 1 else ""
        table.add_row(
            f"Variant {orig_id}",
            f"{res['score']:.1f}",
            f"+{res.get('novelty_count', 0) * 1.0:.1f}",
            f"#{rank}",
            style=style
        )

    console.print(table)

    winner_id = sorted_results[0][0]
    top_variant = sorted_results[0][1]
    console.print(f"[bold green]Top variant selected: Variant {winner_id} (score: {top_variant['score']:.1f})[/bold green]")

    # Save all variants
    save_all_variants(variant_results)

 
    # Reflection on top variant
    console.print("\n[bold magenta]Final Reflection on Top Variant[/bold magenta]")
    reflection = run_reflection_on_variant(
        top_variant["final_data"],
        original_data,
        top_variant["steps"],
        intent
    )

    # Save to history DB
    save_run_to_db(
        original_data,
        top_variant["final_data"],
        [r["score"] for r in variant_results],
        reflection,
        intent,
        iterations,
        variants
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

    return {
        "original_data": original_data,
        "top_variant": top_variant["final_data"],
        "all_variants_scores": [r["score"] for r in variant_results],
        "reflection": reflection,
        "status": "complete"
    }


# (keep evolve_single_variant, calculate_composite_score, is_novel_mutation, save_all_variants, run_reflection_on_variant as before)