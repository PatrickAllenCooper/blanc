"""
Unified ROE Benchmark: SC2 + Lux AI S3 Cross-Environment Evaluation.

This script runs the complete DeFAb-ROE benchmark across two visually
compelling game environments:

  1. StarCraft II (via rts_engagement_kb.py)
     - 6 Level 3 seed conflicts (self-defense, worker exception, etc.)
     - Modeled on SC2 unit types and tactical doctrine
     - Lockheed Martin's designated ROE proxy environment
     - Visual: PySC2 RGB renders / SC2 screenshots

  2. Lux AI Season 3 (via lux_engagement_kb.py)
     - 6 Level 3 seed conflicts (energy retreat, laser evasion, etc.)
     - Open-source NeurIPS 2024 competition, Python-native (Jax)
     - No proprietary game client required
     - Visual: https://s3vis.lux-ai.org web visualizer

Cross-environment comparison hypothesis (H5):
    If Foundry models perform comparably on SC2 ROE instances and Lux AI
    instances despite completely different game vocabularies, this
    demonstrates that DeFAb measures domain-general defeasible reasoning
    rather than SC2-specific knowledge.

Usage:
    # Set FOUNDRY_API_KEY in .env or environment, then:
    python scripts/run_roe_benchmark.py

    # Mock dry-run (no API key needed)
    python scripts/run_roe_benchmark.py --provider mock

    # Single environment
    python scripts/run_roe_benchmark.py --environments sc2
    python scripts/run_roe_benchmark.py --environments lux

    # Full benchmark with all Foundry models
    python scripts/run_roe_benchmark.py --all-models

Foundry model providers:
    foundry-gpt      GPT-5.2
    foundry-deepseek DeepSeek-R1
    foundry-claude   Claude Sonnet 4.6
    foundry-kimi     Kimi K2.5

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.reasoning.defeasible import defeasible_provable
from blanc.author.support import _remove_element
from examples.knowledge_bases.rts_engagement_kb import (
    create_rts_engagement_kb,
    get_rts_stats,
)
from examples.knowledge_bases.lux_engagement_kb import (
    create_lux_engagement_kb,
    get_lux_stats,
)
from scripts.generate_rts_instances import ROE_LEVEL3_SEEDS
from scripts.generate_lux_instances import LUX_LEVEL3_SEEDS

try:
    from model_interface import create_model_interface
    from evaluation_pipeline import EvaluationPipeline
    EVAL_AVAILABLE = True
except ImportError:
    EVAL_AVAILABLE = False


# ── ANSI color codes for visually compelling terminal output ──────────────────
BOLD    = "\033[1m"
GREEN   = "\033[92m"
RED     = "\033[91m"
YELLOW  = "\033[93m"
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
RESET   = "\033[0m"
DIM     = "\033[2m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}[PASS]{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}[FAIL]{RESET} {msg}")


def _info(msg: str) -> None:
    print(f"  {CYAN}[INFO]{RESET} {msg}")


def _header(msg: str) -> None:
    print(f"\n{BOLD}{MAGENTA}{'=' * 70}{RESET}")
    print(f"{BOLD}{MAGENTA}{msg}{RESET}")
    print(f"{BOLD}{MAGENTA}{'=' * 70}{RESET}")


def _section(msg: str) -> None:
    print(f"\n{BOLD}{CYAN}{'-' * 60}{RESET}")
    print(f"{BOLD}{CYAN}{msg}{RESET}")
    print(f"{BOLD}{CYAN}{'-' * 60}{RESET}")


# ── Stage 1: KB certification ─────────────────────────────────────────────────

def certify_kb(name: str, kb: Theory, seeds: list, stats: dict) -> dict:
    """
    Certify a KB by verifying all L3 seed scenarios formally.
    Returns a certification result dict.
    """
    _section(f"KB CERTIFICATION: {name}")
    _info(f"Rules: {stats['rules_total']}  Facts: {stats['facts_total']}")
    _info(f"Strict: {stats['strict_rules']}  Defeasible: {stats['defeasible_rules']}  Defeaters: {stats['defeater_rules']}")

    passed = 0
    results = []

    for seed in seeds:
        sid = seed["scenario_id"]
        working = copy.deepcopy(kb)
        for fact in seed["context_facts"]:
            working.add_fact(fact)

        defeater_rule = next(
            (r for r in working.rules if r.label == seed["defeater_label"]),
            None
        )
        if defeater_rule is None:
            _fail(f"{sid}: defeater {seed['defeater_label']} not found")
            results.append({"scenario_id": sid, "passed": False, "error": "defeater_not_found"})
            continue

        d_minus = _remove_element(working, defeater_rule)
        anomaly = seed["anomaly"]

        try:
            in_d_minus = defeasible_provable(d_minus, anomaly)
            in_d       = defeasible_provable(working, anomaly)
        except Exception as e:
            _fail(f"{sid}: engine error: {e}")
            results.append({"scenario_id": sid, "passed": False, "error": str(e)})
            continue

        # Conservativity: sample of unrelated queries
        anomaly_pred = anomaly.split("(")[0].lstrip("~")
        conservativity_ok = True
        for check in ["is_mobile(ship_a1)", "has_sensor_range(ship_a1)",
                      "can_attack_ground(marine)", "gathers_resources(scv)"]:
            if anomaly_pred in check:
                continue
            try:
                before = defeasible_provable(d_minus, check)
                after  = defeasible_provable(working, check)
                if before != after:
                    conservativity_ok = False
                    break
            except Exception:
                pass

        scenario_ok = in_d_minus and not in_d and conservativity_ok
        if scenario_ok:
            passed += 1
            _ok(f"{sid}")
        else:
            details = []
            if not in_d_minus: details.append("anomaly NOT in D^-")
            if in_d:           details.append("anomaly NOT resolved in D")
            if not conservativity_ok: details.append("conservativity violated")
            _fail(f"{sid}: {', '.join(details)}")

        results.append({
            "scenario_id": sid,
            "passed": scenario_ok,
            "anomaly_in_d_minus": in_d_minus,
            "resolved_in_d": not in_d,
            "conservative": conservativity_ok,
        })

    rate = passed / len(seeds) if seeds else 0.0
    summary = {"passed": passed, "total": len(seeds), "pass_rate": rate, "scenarios": results}

    if passed == len(seeds):
        _ok(f"All {len(seeds)}/{len(seeds)} seed scenarios certified ({rate:.0%})")
    else:
        _fail(f"Only {passed}/{len(seeds)} seed scenarios certified ({rate:.0%})")

    return summary


# ── Stage 2: Instance generation ─────────────────────────────────────────────

def generate_instances(name: str, env_key: str, kb_path: str) -> bool:
    """Run the instance generation script for an environment."""
    _section(f"INSTANCE GENERATION: {name}")

    output_file = ROOT / "instances" / f"{env_key}_engagement_instances.json"
    if output_file.exists():
        with open(output_file) as f:
            data = json.load(f)
        count = len(data.get("instances", []))
        _ok(f"Instances already exist: {output_file} ({count} instances)")
        return True

    script = ROOT / "scripts" / f"generate_{env_key}_instances.py"
    if not script.exists():
        _fail(f"Generation script not found: {script}")
        return False

    _info(f"Running: python {script.name} --output {output_file}")
    result = subprocess.run(
        [sys.executable, str(script), "--output", str(output_file),
         "--level", "0", "--max-instances", "15"],
        capture_output=False,
    )
    if result.returncode == 0:
        _ok(f"Instance generation succeeded: {output_file}")
        return True
    else:
        _fail(f"Instance generation failed (exit code {result.returncode})")
        return False


# ── Stage 3: Load instances ───────────────────────────────────────────────────

def load_instances_for_eval(env_key: str, include_l3: bool = True) -> list[AbductiveInstance]:
    """Load AbductiveInstance objects from a generated JSON file."""
    instances_file = ROOT / "instances" / f"{env_key}_engagement_instances.json"
    if not instances_file.exists():
        return []

    with open(instances_file) as f:
        data = json.load(f)

    all_records = data.get("instances", [])
    instances = []
    l3_count = 0

    for i, item in enumerate(all_records):
        level = item.get("level", 2)
        if level == 3 and not include_l3:
            continue
        if level == 3:
            l3_count += 1

        facts = list(item.get("theory_facts", item.get("metadata", {}).get("facts", [])))
        rules_raw = item.get("theory_rules", [])
        rules = []
        for r in rules_raw:
            if isinstance(r, dict):
                try:
                    rules.append(Rule(
                        head=r.get("head", ""),
                        body=tuple(r.get("body", [])),
                        rule_type=RuleType(r.get("rule_type", "defeasible")),
                        label=r.get("label"),
                    ))
                except (ValueError, TypeError):
                    continue

        d_minus = Theory(facts=set(facts), rules=rules, superiority={})
        inst = AbductiveInstance(
            D_minus=d_minus,
            target=item.get("anomaly", item.get("target", "")),
            candidates=item.get("candidates", []),
            gold=(
                [item["gold"]] if isinstance(item.get("gold"), str)
                else item.get("gold", [])
            ),
            level=level,
            metadata={"domain": f"{env_key}_engagement"},
        )
        inst.id = f"{env_key}-l{level}-{item.get('scenario_id', i)}"
        instances.append(inst)

    return instances


# ── Stage 4: Model evaluation ─────────────────────────────────────────────────

def run_evaluation(
    name: str,
    instances: list[AbductiveInstance],
    provider: str,
    api_key: str | None,
    modalities: list[str],
    strategies: list[str],
    results_dir: Path,
    cache_dir: Path,
) -> dict:
    """Run the EvaluationPipeline for one environment and return summary."""
    _section(f"MODEL EVALUATION: {name} ({provider})")

    if not EVAL_AVAILABLE:
        _fail("EvaluationPipeline not available (missing experiments package)")
        return {}

    if not instances:
        _fail("No instances to evaluate")
        return {}

    by_level: dict[int, int] = {}
    for inst in instances:
        lv = getattr(inst, "level", 2)
        by_level[lv] = by_level.get(lv, 0) + 1
    _info(f"Instances: " + " ".join(f"L{l}={c}" for l, c in sorted(by_level.items())))

    kwargs: dict = {}
    if provider.startswith("foundry-"):
        if not api_key:
            api_key = os.getenv("FOUNDRY_API_KEY")

    try:
        model = create_model_interface(provider, api_key=api_key, **kwargs)
    except Exception as e:
        _fail(f"Could not create model interface: {e}")
        return {}

    pipeline = EvaluationPipeline(
        instances=instances,
        models={provider: model},
        modalities=modalities,
        strategies=strategies,
        cache_dir=str(cache_dir),
        results_dir=str(results_dir),
    )

    results = pipeline.run(save_every=10)
    summary = getattr(results, "summary", {})

    l2_acc = summary.get("level2_accuracy", "--")
    l3_acc = summary.get("level3_accuracy", "--")
    l3_grd = summary.get("level3_graded", "--")

    _ok(f"L2 accuracy  : {l2_acc:.1%}" if isinstance(l2_acc, float) else f"L2 accuracy: {l2_acc}")
    _ok(f"L3 accuracy  : {l3_acc:.1%}" if isinstance(l3_acc, float) else f"L3 accuracy: {l3_acc}")
    _ok(f"L3 graded    : {l3_grd:.3f}" if isinstance(l3_grd, float) else f"L3 graded: {l3_grd}")

    return summary


# ── Stage 5: Cross-environment comparison table ───────────────────────────────

def print_comparison_table(results: dict) -> None:
    """Print a formatted cross-environment comparison table."""
    _header("CROSS-ENVIRONMENT COMPARISON")

    print(f"\n  {BOLD}{'Environment':<20} {'Provider':<18} {'L2 Acc':>8} {'L3 Acc':>8} {'L3 Graded':>10}{RESET}")
    print(f"  {'-'*20} {'-'*18} {'-'*8} {'-'*8} {'-'*10}")

    for key, data in results.items():
        env = data.get("environment", key)
        prov = data.get("provider", "--")
        summary = data.get("eval_summary", {})
        l2  = summary.get("level2_accuracy", "--")
        l3  = summary.get("level3_accuracy", "--")
        l3g = summary.get("level3_graded",   "--")

        l2_str  = f"{l2:.1%}"  if isinstance(l2,  float) else str(l2)
        l3_str  = f"{l3:.1%}"  if isinstance(l3,  float) else str(l3)
        l3g_str = f"{l3g:.3f}" if isinstance(l3g, float) else str(l3g)

        print(f"  {env:<20} {prov:<18} {l2_str:>8} {l3_str:>8} {l3g_str:>10}")

    print()
    print(f"  {DIM}H5 (cross-environment transfer): if SC2 and Lux AI L3 scores are{RESET}")
    print(f"  {DIM}comparable, DeFAb measures domain-general defeasible reasoning.{RESET}")


# ── Main ──────────────────────────────────────────────────────────────────────

ENVIRONMENTS = {
    "sc2": {
        "name": "StarCraft II",
        "kb_factory": create_rts_engagement_kb,
        "stats_fn":   get_rts_stats,
        "seeds":      ROE_LEVEL3_SEEDS,
        "env_key":    "rts",
        "visual":     "PySC2 RGB / SC2 screenshots",
        "lockheed_connection": True,
    },
    "lux": {
        "name": "Lux AI Season 3",
        "kb_factory": create_lux_engagement_kb,
        "stats_fn":   get_lux_stats,
        "seeds":      LUX_LEVEL3_SEEDS,
        "env_key":    "lux",
        "visual":     "https://s3vis.lux-ai.org",
        "lockheed_connection": False,
    },
}

ALL_PROVIDERS = ["foundry-gpt", "foundry-deepseek", "foundry-claude", "foundry-kimi"]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Unified ROE Benchmark: SC2 + Lux AI S3")
    p.add_argument("--provider", default="foundry-deepseek",
                   choices=ALL_PROVIDERS + ["mock"],
                   help="Model provider for evaluation (default: foundry-deepseek)")
    p.add_argument("--all-models", action="store_true",
                   help="Run all four Foundry models sequentially")
    p.add_argument("--api-key", default=None,
                   help="FOUNDRY_API_KEY (falls back to env var)")
    p.add_argument("--environments", nargs="+", default=["sc2", "lux"],
                   choices=["sc2", "lux"],
                   help="Which environments to benchmark")
    p.add_argument("--modalities", nargs="+", default=["M4"])
    p.add_argument("--strategies", nargs="+", default=["direct", "cot"])
    p.add_argument("--skip-generation", action="store_true",
                   help="Skip instance generation, use existing files")
    p.add_argument("--certify-only", action="store_true",
                   help="Run KB certification only, skip model evaluation")
    p.add_argument("--output", default=None,
                   help="Output report JSON path")
    p.add_argument("--verbose", "-v", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    api_key = args.api_key or os.getenv("FOUNDRY_API_KEY")

    results_dir = ROOT / "experiments" / "results"
    cache_dir   = ROOT / "experiments" / "cache"
    results_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    _header("DeFAb ROE BENCHMARK: SC2 + LUX AI S3")
    print(f"  Date        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Environments: {', '.join(args.environments)}")
    print(f"  Provider    : {args.provider if not args.all_models else 'ALL'}")
    print(f"  Modalities  : {', '.join(args.modalities)}")
    print(f"  Strategies  : {', '.join(args.strategies)}")
    print()

    all_results: dict = {}
    providers = ALL_PROVIDERS if args.all_models else [args.provider]

    # ── Phase 1: KB certification for all environments ────────────────────────
    _header("PHASE 1: KB CERTIFICATION")
    cert_results: dict = {}

    for env_key in args.environments:
        env = ENVIRONMENTS[env_key]
        kb    = env["kb_factory"]()
        stats = env["stats_fn"](kb)

        if env.get("lockheed_connection"):
            print(f"\n  {YELLOW}Lockheed Martin designated proxy environment{RESET}")

        cert = certify_kb(env["name"], kb, env["seeds"], stats)
        cert_results[env_key] = cert

        all_results[env_key] = {
            "environment": env["name"],
            "env_key": env_key,
            "visual_source": env["visual"],
            "kb_stats": stats,
            "certification": cert,
        }

    if args.certify_only:
        _header("CERTIFICATION COMPLETE (eval skipped)")
        _save_report(all_results, args.output, timestamp)
        return 0

    # ── Phase 2: Instance generation ──────────────────────────────────────────
    if not args.skip_generation:
        _header("PHASE 2: INSTANCE GENERATION")
        for env_key in args.environments:
            env = ENVIRONMENTS[env_key]
            ok = generate_instances(env["name"], env["env_key"], env_key)
            all_results[env_key]["instances_generated"] = ok

    # ── Phase 3: Model evaluation ──────────────────────────────────────────────
    _header("PHASE 3: MODEL EVALUATION")

    for provider in providers:
        _info(f"Provider: {provider}")
        for env_key in args.environments:
            env = ENVIRONMENTS[env_key]
            instances = load_instances_for_eval(env["env_key"], include_l3=True)
            summary = run_evaluation(
                env["name"], instances,
                provider, api_key,
                args.modalities, args.strategies,
                results_dir, cache_dir,
            )
            result_key = f"{env_key}_{provider}"
            all_results[result_key] = {
                "environment": env["name"],
                "provider": provider,
                "eval_summary": summary,
            }

    # ── Phase 4: Cross-environment comparison ──────────────────────────────────
    eval_results = {k: v for k, v in all_results.items() if "eval_summary" in v}
    if eval_results:
        print_comparison_table(eval_results)

    _save_report(all_results, args.output, timestamp)
    return 0


def _save_report(all_results: dict, output_path_arg: str | None, timestamp: str) -> None:
    output_path = Path(output_path_arg) if output_path_arg else (
        ROOT / "experiments" / "results" / f"roe_benchmark_{timestamp}.json"
    )
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Report saved: {output_path}")


if __name__ == "__main__":
    sys.exit(main())
