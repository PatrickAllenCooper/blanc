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
    """Load and convert DEFREASING CSV to 3-way classification instances.

    DEFREASING (Allaway & McKeown, NAACL 2025) is a defeasible NLI dataset.
    Each row gives:
      premise   - generic rule + subtype membership ("Birds fly. Bafus are birds.")
      hypothesis - expected conclusion ("Bafus fly.")
      extra      - additional sentence that may strengthen/weaken/negate the conclusion
      label      - S (strengthens), W (weakens), or N (negates)

    We convert to a 3-way MCQ: given premise + hypothesis + extra, which of
    {S, W, N} best describes the effect of the extra information?
    Gold = the correct label.  Chance = 0.333.
    """
    import csv

    csv_path = defreasing_dir / "data" / "defreasing.csv"
    if not csv_path.exists():
        raise FileNotFoundError(
            f"DEFREASING CSV not found at {csv_path}. "
            "Clone with: git clone https://github.com/emilyallaway/DEFREASING data/defreasing"
        )

    rng = random.Random(seed)
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    rng.shuffle(rows)
    subset = rows[:n]

    # Candidate set is fixed for all instances (3-way classification)
    CANDIDATES = ["S", "W", "N"]
    CANDIDATE_TEXT = {
        "S": "strengthens the conclusion (the extra information supports it more strongly)",
        "W": "weakens the conclusion (the extra information makes it less certain)",
        "N": "negates the conclusion (the extra information overrides the expected conclusion)",
    }

    instances = []
    for i, row in enumerate(subset):
        premise    = row["premise"].strip()
        hypothesis = row["hypothesis"].strip()
        extra      = row["extra"].strip()
        gold_label = row["label"].strip()  # S, W, or N

        if gold_label not in CANDIDATES:
            continue

        # Format as a compact multiple-choice prompt string.
        # The EvaluationPipeline will wrap this in its standard prompt template.
        # We encode the task directly in the target string, and use candidates
        # that the decoder can match exactly.
        cand_texts = [f"{c}: {CANDIDATE_TEXT[c]}" for c in CANDIDATES]
        gold = [f"{gold_label}: {CANDIDATE_TEXT[gold_label]}"]

        # Use a lightweight dict matching EvaluationPipeline's expected shape.
        # We store the NLI context in the theory_facts/theory_rules fields
        # so the standard M4 renderer can display them.
        inst = {
            "id": f"defreasing_{i:04d}",
            "domain": "defreasing",
            "level": 2,
            "target": hypothesis,
            "candidates": cand_texts,
            "gold": gold,
            "theory_facts": [premise, f"extra: {extra}"],
            "theory_rules": [],
            "metadata": {
                "reasoning_type": row.get("reasoning_type", ""),
                "extra_type": row.get("extra_type", ""),
                "reasoning_steps": row.get("reasoning_steps", ""),
            },
        }
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

def _eval_defreasing_provider(instances: list, interface, results_dir: Path, provider: str) -> dict:
    """Run 3-way S/W/N classification on DEFREASING instances and return summary."""
    import re

    correct = 0
    total = 0
    per_label: dict[str, dict] = {"S": {"tp": 0, "fp": 0, "fn": 0},
                                   "W": {"tp": 0, "fp": 0, "fn": 0},
                                   "N": {"tp": 0, "fp": 0, "fn": 0}}

    LABEL_WORDS = {
        "S": ["strengthens", "strengthen", "supports", "support", "stronger"],
        "W": ["weakens", "weaken", "weakens", "undermines", "reduces", "uncertain"],
        "N": ["negates", "negate", "negated", "overrides", "defeats", "contradicts", "impossible"],
    }

    records = []
    for inst in instances:
        premise_lines = inst["theory_facts"]
        premise_text  = premise_lines[0] if premise_lines else ""
        extra_text    = premise_lines[1].replace("extra: ", "") if len(premise_lines) > 1 else ""
        hypothesis    = inst["target"]
        gold_cand     = inst["gold"][0]
        gold_label    = gold_cand.split(":")[0].strip()  # "S", "W", or "N"

        prompt = (
            "Defeasible reasoning classification task.\n\n"
            f"Generic rule + subtype membership: {premise_text}\n"
            f"Expected conclusion: {hypothesis}\n"
            f"Additional information: {extra_text}\n\n"
            "Does the additional information strengthen (S), weaken (W), or negate (N) the conclusion?\n"
            "Think briefly, then output one of: S, W, or N."
        )

        try:
            response = interface.query(prompt, max_tokens=256)
            text = response.text if hasattr(response, "text") else str(response)
        except Exception as exc:
            text = f"ERROR: {exc}"

        # Decode: look for explicit label letters first, then key words
        text_stripped = text.strip()
        pred_label = "?"

        # Priority 1: standalone label on its own line or at end of response
        for pattern in [r"(?m)^([SWN])\s*$", r"\bAnswer:\s*([SWN])\b", r"(?m)([SWN])\s*$"]:
            m = re.search(pattern, text_stripped, re.IGNORECASE)
            if m:
                pred_label = m.group(1).upper()
                break

        # Priority 2: look for label words
        if pred_label == "?":
            text_lower = text_stripped.lower()
            for lbl, words in LABEL_WORDS.items():
                if any(w in text_lower for w in words):
                    pred_label = lbl
                    break

        # Priority 3: look for any standalone S, W, or N letter
        if pred_label == "?":
            m = re.search(r"\b([SWN])\b", text_stripped, re.IGNORECASE)
            if m:
                pred_label = m.group(1).upper()

        is_correct = (pred_label == gold_label)
        correct += int(is_correct)
        total += 1

        for lbl in ["S", "W", "N"]:
            if gold_label == lbl:
                if pred_label == lbl:
                    per_label[lbl]["tp"] += 1
                else:
                    per_label[lbl]["fn"] += 1
            elif pred_label == lbl:
                per_label[lbl]["fp"] += 1

        records.append({
            "id": inst["id"],
            "gold": gold_label,
            "pred": pred_label,
            "correct": is_correct,
            "response": text[:200],
        })

    accuracy = correct / total if total else 0.0

    # Macro F1
    f1s = []
    for lbl in ["S", "W", "N"]:
        tp = per_label[lbl]["tp"]
        fp = per_label[lbl]["fp"]
        fn = per_label[lbl]["fn"]
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec  = tp / (tp + fn) if (tp + fn) else 0.0
        f1   = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        f1s.append(f1)
    macro_f1 = sum(f1s) / len(f1s)

    summary = {
        "provider": provider,
        "total": total,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "per_label": per_label,
    }
    out = {
        "summary": summary,
        "records": records,
    }
    out_path = results_dir / f"results_{provider}.json"
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2)

    return summary


def _eval_defab_l2_provider(instances: list, interface, results_dir: Path, provider: str) -> dict:
    """Run DeFAb L2 MCQ eval using the standard EvaluationPipeline."""
    from evaluation_pipeline import EvaluationPipeline

    pipeline = EvaluationPipeline(
        instances=instances,
        models={interface.model_name: interface},
        modalities=["M4"],
        strategies=["direct"],
        cache_dir=str(ROOT / "experiments" / "cache"),
        results_dir=str(results_dir),
    )
    res = pipeline.run()
    out_path = results_dir / f"results_{provider}.json"
    res.save(str(out_path))
    s = res.summary
    return {"provider": provider, "accuracy": s.get("accuracy", 0),
            "total": s.get("total_evaluations", 0)}


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

    defreasing_dir = Path(args.defreasing_dir)
    results_dir = Path(args.results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)

    foundry_key = os.environ.get("FOUNDRY_API_KEY", "")
    if not foundry_key:
        print("ERROR: FOUNDRY_API_KEY not set. Add to .env file.")
        return 1

    # Load instances
    print("Loading DEFREASING instances...")
    try:
        defreasing_insts = load_defreasing(defreasing_dir, n=args.n, seed=args.seed)
        print(f"  {len(defreasing_insts)} DEFREASING instances loaded.")
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 1

    print("Loading DeFAb Tier 0 L2 subset...")
    defab_insts = load_defab_subset(n=args.n, seed=args.seed)
    print(f"  {len(defab_insts)} DeFAb L2 instances loaded.")

    summary_rows = []

    for provider in args.providers:
        print(f"\n=== Evaluating {provider} ===")
        interface = create_model_interface(provider, api_key=foundry_key)

        # DEFREASING: 3-way classification
        dref_dir = results_dir / "defreasing"
        dref_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Running DEFREASING 3-way classification (n={len(defreasing_insts)})...")
        dref_s = _eval_defreasing_provider(defreasing_insts, interface, dref_dir, provider)
        print(f"  DEFREASING: acc={dref_s['accuracy']:.3f}  macro_f1={dref_s['macro_f1']:.3f}")

        # DeFAb L2: standard MCQ eval
        defab_dir = results_dir / "defab_l2"
        defab_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Running DeFAb L2 MCQ eval (n={len(defab_insts)})...")
        defab_s = _eval_defab_l2_provider(defab_insts, interface, defab_dir, provider)
        print(f"  DeFAb L2:   acc={defab_s['accuracy']:.3f}  n={defab_s['total']}")

        summary_rows.append({
            "provider": provider,
            "defreasing_acc": dref_s["accuracy"],
            "defreasing_macro_f1": dref_s["macro_f1"],
            "defab_l2_acc": defab_s["accuracy"],
        })

    # Write combined summary table
    summary_path = results_dir / "comparison_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary_rows, f, indent=2)

    print(f"\n{'Provider':<25} {'DEFREASING acc':>16} {'DEFREASING F1':>14} {'DeFAb-L2 acc':>13}")
    print("-" * 72)
    for row in summary_rows:
        print(f"  {row['provider']:<23} {row['defreasing_acc']:>16.3f} "
              f"{row['defreasing_macro_f1']:>14.3f} {row['defab_l2_acc']:>13.3f}")

    print(f"\nAll results saved to {results_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
