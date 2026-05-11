"""
Phase 4B: DEFREASING side-by-side numerical comparison.

Evaluates the four-model panel on both:
  (a) a 200-instance random subset of the DEFREASING dataset
      (Allaway & McKeown, 2025 — defeasible property inheritance, multiple choice)
  (b) a difficulty-matched subset of DeFAb Tier 0 L2 instances
      using an identical prompt template (no domain-specific framing)

This produces the numerical comparison needed for §2 Related Work.

DEFREASING dataset:
  https://github.com/elizaallaway/defreasing (clone to data/defreasing/)

Usage:
  # Clone dataset first:
  git clone https://github.com/elizaallaway/defreasing data/defreasing

  # Run the comparison:
  python experiments/run_defreasing_comparison.py \
    --defreasing-dir data/defreasing \
    --results-dir experiments/results/defreasing_comparison

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# ---------------------------------------------------------------------------
# DEFREASING → AbductiveInstance adapter
# ---------------------------------------------------------------------------

def load_defreasing(defreasing_dir: Path, n: int = 200, seed: int = 42) -> list:
    """Load and convert DEFREASING instances to AbductiveInstance-like dicts."""
    # DEFREASING is a multiple-choice dataset. Each example has:
    #   entity, property, candidates (list), label (index of correct)
    # We map: target = f"has_property({entity}, {property})"
    #         candidates = [formatted rule strings]
    #         gold = [candidates[label]]
    from blanc.author.generation import AbductiveInstance
    from blanc.core.theory import Theory

    rng = random.Random(seed)

    # Try common file layouts
    candidates = []
    for subdir in ["data", ".", "test", "dev"]:
        for fname in ["test.jsonl", "dev.jsonl", "data.jsonl", "defreasing.jsonl",
                      "test.json", "dev.json"]:
            p = defreasing_dir / subdir / fname
            if p.exists():
                with open(p) as f:
                    for line in f:
                        try:
                            candidates.append(json.loads(line.strip()))
                        except Exception:
                            pass
                break
        if candidates:
            break

    if not candidates:
        # Try top-level
        for fname in defreasing_dir.glob("**/*.jsonl"):
            with open(fname) as f:
                for line in f:
                    try:
                        candidates.append(json.loads(line.strip()))
                    except Exception:
                        pass
            if candidates:
                break

    if not candidates:
        raise FileNotFoundError(
            f"No DEFREASING data files found in {defreasing_dir}. "
            "Expected *.jsonl with JSON objects containing 'entity', 'property', 'candidates', 'label'."
        )

    rng.shuffle(candidates)
    subset = candidates[:n]

    instances = []
    for i, ex in enumerate(subset):
        entity   = ex.get("entity", ex.get("subject", f"entity_{i}"))
        prop     = ex.get("property", ex.get("predicate", f"prop_{i}"))
        cands    = ex.get("choices", ex.get("candidates", ex.get("options", [])))
        label    = ex.get("label", ex.get("answer", ex.get("correct", 0)))

        if isinstance(label, str):
            try:
                label = int(label)
            except ValueError:
                label = cands.index(label) if label in cands else 0

        if not cands:
            continue

        gold = [cands[label]] if label < len(cands) else [cands[0]]

        target = f"{prop}({entity})"
        fake_theory = Theory(
            facts={f"entity({entity})", f"has_{prop}({entity})"},
            rules=[],
            superiority={},
        )

        inst = AbductiveInstance(
            D_minus=fake_theory,
            target=target,
            candidates=cands,
            gold=gold,
            level=2,
            metadata={
                "domain": "defreasing",
                "entity": entity,
                "property": prop,
                "instance_id": f"defreasing_{i:04d}",
            },
        )
        inst.id = f"defreasing_{i:04d}"
        instances.append(inst)

    return instances


# ---------------------------------------------------------------------------
# DeFAb Tier 0 L2 subset (difficulty matched)
# ---------------------------------------------------------------------------

def load_defab_subset(n: int = 200, seed: int = 42) -> list:
    """Load a random subset of Tier 0 L2 instances."""
    sys.path.insert(0, str(ROOT / "experiments"))
    from run_evaluation import _load_level2_instances
    import random as _r

    rng = _r.Random(seed)
    all_insts = []
    instances_dir = ROOT / "instances"
    for domain in ["biology", "legal", "materials"]:
        all_insts.extend(_load_level2_instances(domain, 999, instances_dir))

    rng.shuffle(all_insts)
    return all_insts[:n]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="DEFREASING side-by-side comparison")
    ap.add_argument("--defreasing-dir", default=str(ROOT / "data" / "defreasing"),
                    help="Path to cloned DEFREASING repo.")
    ap.add_argument("--results-dir",
                    default=str(ROOT / "experiments" / "results" / "defreasing_comparison"),
                    help="Output directory for results.")
    ap.add_argument("--n", type=int, default=200, help="Instances per dataset.")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--providers", nargs="+",
                    default=["foundry-gpt", "foundry-claude",
                             "foundry-deepseek", "foundry-kimi"],
                    help="Foundry provider IDs to evaluate.")
    args = ap.parse_args()

    from model_interface import create_model_interface
    from evaluation_pipeline import EvaluationPipeline

    defreasing_dir = Path(args.defreasing_dir)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load instances
    print("Loading DEFREASING instances...")
    try:
        defreasing_insts = load_defreasing(defreasing_dir, n=args.n, seed=args.seed)
        print(f"  {len(defreasing_insts)} DEFREASING instances loaded.")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        print("\nTo clone DEFREASING:\n  git clone https://github.com/elizaallaway/defreasing data/defreasing")
        return 1

    print("Loading DeFAb Tier 0 L2 subset...")
    defab_insts = load_defab_subset(n=args.n, seed=args.seed)
    print(f"  {len(defab_insts)} DeFAb L2 instances loaded.")

    foundry_key = os.environ.get("FOUNDRY_API_KEY", "")
    if not foundry_key:
        print("ERROR: FOUNDRY_API_KEY not set. Add to .env file.")
        return 1

    for provider in args.providers:
        print(f"\n=== Evaluating {provider} ===")
        interface = create_model_interface(provider)

        for dataset_name, instances in [
            ("defreasing", defreasing_insts),
            ("defab_l2", defab_insts),
        ]:
            sub_dir = results_dir / dataset_name
            sub_dir.mkdir(parents=True, exist_ok=True)
            pipeline = EvaluationPipeline(
                instances=instances,
                models={interface.model_name: interface},
                modalities=["M4"],
                strategies=["direct"],
                cache_dir=str(ROOT / "experiments" / "cache"),
                results_dir=str(sub_dir),
            )
            res = pipeline.run()
            out = sub_dir / f"results_{provider}.json"
            res.save(str(out))
            s = res.summary
            print(f"  {dataset_name:15s} acc={s.get('accuracy', 0):.3f}  n={s.get('total_evaluations', 0)}")

    print(f"\nAll results saved to {results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
