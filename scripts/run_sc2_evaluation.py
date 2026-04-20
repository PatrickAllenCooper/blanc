"""
Evaluate foundation models on DeFAb sc2live instances.

Mirrors scripts/run_rts_evaluation.py but operates on sc2live_instances.json.
All hypotheses (H1-H5) from the cross-environment transfer test (E5) are
reported here.

Usage::

    python scripts/run_sc2_evaluation.py --provider mock --instance-limit 6
    python scripts/run_sc2_evaluation.py --provider foundry-deepseek --modalities M4 --include-level3

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance


def _build_theory_from_record(item: dict) -> Theory:
    meta = item.get("metadata", {})
    facts = meta.get("facts", [])
    rules_raw = meta.get("rules", [])
    rules = []
    for r in rules_raw:
        if isinstance(r, dict):
            try:
                rt = RuleType[r.get("rule_type", "STRICT").upper()]
                rules.append(Rule(
                    head=r["head"],
                    body=tuple(r.get("body", [])),
                    rule_type=rt,
                    label=r.get("label"),
                ))
            except (KeyError, ValueError):
                continue
    theory = Theory()
    for fact in facts:
        theory.add_fact(fact)
    for rule in rules:
        theory.add_rule(rule)
    return theory


def load_sc2live_instances(
    instances_path: Path,
    level_filter: list[int] | None = None,
    max_instances: int | None = None,
) -> list[AbductiveInstance]:
    """Load sc2live instances from JSON file."""
    if not instances_path.exists():
        print(f"  Instance file not found: {instances_path}")
        print("  Run: python scripts/generate_sc2live_instances.py first.")
        return []

    with open(instances_path) as f:
        data = json.load(f)

    instances_raw = data.get("instances", data if isinstance(data, list) else [])
    instances = []
    for i, item in enumerate(instances_raw):
        level = item.get("level", 2)
        if level_filter and level not in level_filter:
            continue
        if max_instances and len(instances) >= max_instances:
            break
        theory = _build_theory_from_record(item)
        inst = AbductiveInstance(
            D_minus=theory,
            target=item.get("target", ""),
            candidates=item.get("candidates", []),
            gold=item.get("gold", []),
            level=level,
            metadata={
                "domain": item.get("domain", "sc2live"),
                "scenario_id": item.get("scenario_id", f"sc2live-l{level}-{i:04d}"),
            },
        )
        inst.id = f"sc2live-l{level}-{i:04d}"
        instances.append(inst)

    return instances


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate foundation models on DeFAb sc2live instances"
    )
    parser.add_argument("--provider", default="mock",
                        help="Model provider (mock, foundry-*, curc)")
    parser.add_argument("--modalities", nargs="+", default=["M4"],
                        choices=["M1", "M2", "M3", "M4"])
    parser.add_argument("--strategies", nargs="+", default=["direct", "cot"],
                        choices=["direct", "cot"])
    parser.add_argument("--include-level3", action="store_true")
    parser.add_argument("--instance-limit", type=int, default=None)
    parser.add_argument("--instances-path", default=None,
                        help="Path to sc2live_instances.json")
    parser.add_argument("--output-dir", default="experiments/results/",
                        help="Directory for results JSON")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--model", default=None,
                        help="Model name (for curc vLLM)")
    parser.add_argument("--curc-base-url", default=None)
    args = parser.parse_args()

    default_path = ROOT / "instances" / "sc2live_instances.json"
    instances_path = Path(args.instances_path) if args.instances_path else default_path

    print(f"Loading sc2live instances from: {instances_path}")

    level_filter = [1, 2]
    if args.include_level3:
        level_filter.append(3)

    instances = load_sc2live_instances(
        instances_path,
        level_filter=level_filter,
        max_instances=args.instance_limit,
    )

    if not instances:
        print("No instances available. Generate traces first.")
        return 1

    print(f"Loaded {len(instances)} instances")

    try:
        from model_interface import create_model_interface
        from evaluation_pipeline import EvaluationPipeline
    except ImportError:
        print("WARNING: evaluation_pipeline not importable; printing instance summary only")
        for inst in instances[:3]:
            print(f"  {inst.id}: level={inst.level}, target={inst.target}")
        return 0

    model_iface = create_model_interface(
        provider=args.provider,
        model_name=args.model,
        base_url=args.curc_base_url,
    )

    results_dir = ROOT / args.output_dir
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = results_dir / f"sc2live_{args.provider}_{timestamp}.json"

    pipeline = EvaluationPipeline(
        model=model_iface,
        modalities=args.modalities,
        strategies=args.strategies,
        verbose=args.verbose,
    )
    results = pipeline.evaluate(instances)

    with open(results_file, "w") as f:
        json.dump(results.to_dict() if hasattr(results, "to_dict") else results, f, indent=2)
    print(f"Results saved to: {results_file}")

    summary = getattr(results, "summary", {})
    print(f"\nSummary:")
    print(f"  L2 accuracy: {summary.get('level2_accuracy', '--')}")
    print(f"  L3 accuracy: {summary.get('level3_accuracy', '--')}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
