"""
Novelty Analysis -- paper Section 5.2.

Analyses Nov(h, D^-) distributions for Level 3 model responses:
  - Distribution of predicted novelty values
  - Accuracy conditioned on novelty bucket
  - Correlation between Nov and correctness
  - Language bias detection (non-novel predicates in novel responses)

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))


def _is_level3(ev: dict) -> bool:
    iid = ev.get("instance_id", "")
    return "l3" in iid.lower() or "-l3-" in iid


def analyze_novelty(evaluations: list[dict]) -> dict:
    """
    Analyse novelty metrics across Level 3 evaluations.

    Returns a dict with:
      - nov_distribution: counts per bucket (0, (0,0.5], (0.5,1])
      - accuracy_by_nov_bucket: accuracy within each novelty bucket
      - correlation: Pearson r between nov and correct
      - gold_nov_distribution: distribution of gold_nov across instances
    """
    l3 = [ev for ev in evaluations if _is_level3(ev)]
    if not l3:
        return {"error": "No Level 3 evaluations found."}

    buckets: dict = {
        "0.0": {"correct": 0, "total": 0},
        "(0,0.5]": {"correct": 0, "total": 0},
        "(0.5,1]": {"correct": 0, "total": 0},
    }

    nov_vals, correct_vals = [], []

    for ev in l3:
        m = ev.get("metrics", {})
        nov = m.get("nov")
        correct = m.get("correct", False)

        if nov is None:
            continue

        nov_vals.append(nov)
        correct_vals.append(int(correct))

        if nov == 0.0:
            b = "0.0"
        elif nov <= 0.5:
            b = "(0,0.5]"
        else:
            b = "(0.5,1]"

        buckets[b]["total"] += 1
        if correct:
            buckets[b]["correct"] += 1

    # Accuracy per bucket
    accuracy_by_bucket = {}
    for b, d in buckets.items():
        n = d["total"]
        accuracy_by_bucket[b] = {
            "correct": d["correct"],
            "total": n,
            "accuracy": d["correct"] / n if n > 0 else None,
        }

    # Pearson correlation
    correlation = None
    if len(nov_vals) >= 3:
        n = len(nov_vals)
        mean_n = sum(nov_vals) / n
        mean_c = sum(correct_vals) / n
        cov = sum((x - mean_n) * (y - mean_c) for x, y in zip(nov_vals, correct_vals)) / n
        std_n = math.sqrt(sum((x - mean_n) ** 2 for x in nov_vals) / n) or 1e-9
        std_c = math.sqrt(sum((y - mean_c) ** 2 for y in correct_vals) / n) or 1e-9
        correlation = cov / (std_n * std_c)

    return {
        "n_level3": len(l3),
        "n_with_nov": len(nov_vals),
        "nov_mean": sum(nov_vals) / len(nov_vals) if nov_vals else None,
        "nov_nonzero_rate": sum(1 for v in nov_vals if v > 0) / len(nov_vals) if nov_vals else None,
        "accuracy_by_nov_bucket": accuracy_by_bucket,
        "pearson_r_nov_correct": correlation,
    }


def print_novelty_report(evaluations: list[dict]) -> None:
    print("=" * 70)
    print("Level 3 Novelty Analysis -- Section 5.2")
    print("=" * 70)

    result = analyze_novelty(evaluations)
    if "error" in result:
        print(result["error"])
        return

    print(f"Level 3 evaluations : {result['n_level3']}")
    print(f"With parsed Nov     : {result['n_with_nov']}")
    print(f"Mean predicted Nov  : {result['nov_mean']:.3f}" if result['nov_mean'] is not None else "Mean predicted Nov: N/A")
    print(f"Non-zero Nov rate   : {result['nov_nonzero_rate']:.1%}" if result['nov_nonzero_rate'] is not None else "")
    print(f"Pearson r(nov, acc) : {result['pearson_r_nov_correct']:.3f}" if result['pearson_r_nov_correct'] is not None else "Pearson r: N/A")
    print()

    print("Accuracy by Novelty Bucket:")
    for bucket, d in result["accuracy_by_nov_bucket"].items():
        if d["total"] > 0:
            print(f"  Nov {bucket:<10}: {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
        else:
            print(f"  Nov {bucket:<10}: --")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--results-file", default=None)
    args = parser.parse_args()

    path = Path(args.results_file) if args.results_file else Path(args.results_dir)
    evaluations = []
    if path.is_dir():
        for f in path.glob("*.json"):
            d = json.load(open(f))
            evaluations.extend(d.get("evaluations", []) if isinstance(d, dict) else d)
    else:
        d = json.load(open(path))
        evaluations = d.get("evaluations", []) if isinstance(d, dict) else d

    print_novelty_report(evaluations)
