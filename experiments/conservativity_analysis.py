"""
Conservativity / Belief Revision Analysis -- paper Section 5.3.

Analyzes:
  - What fraction of model hypotheses are conservative (is_conservative)
  - Distribution of revision distance d_rev
  - Accuracy vs conservativity trade-off
  - Does correctness require conservativity? (cross-tabulation)
  - AGM minimal-change adherence: do models prefer low d_rev solutions?

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))


def _is_level3(ev: dict) -> bool:
    iid = ev.get("instance_id", "")
    return "l3" in iid.lower() or "-l3-" in iid


def analyze_conservativity(evaluations: list[dict]) -> dict:
    """
    Compute conservativity statistics for Level 3 evaluations.

    Returns:
      - conservativity_rate: fraction of parsed responses that are conservative
      - resolves_rate: fraction of parsed responses that resolve the anomaly
      - conservative_and_resolves_rate: fraction that are both
      - d_rev_distribution: counts per d_rev value
      - accuracy_by_conservative: accuracy split by conservativity value
    """
    l3 = [ev for ev in evaluations if _is_level3(ev)]
    if not l3:
        return {"error": "No Level 3 evaluations found."}

    parsed = [ev for ev in l3 if ev.get("metrics", {}).get("parse_success") is True]
    n_parsed = len(parsed)

    if n_parsed == 0:
        return {"error": "No successfully parsed Level 3 responses."}

    conservative_vals = [ev["metrics"].get("is_conservative") for ev in parsed]
    resolves_vals = [ev["metrics"].get("resolves_anomaly") for ev in parsed]
    d_rev_vals = [ev["metrics"].get("d_rev") for ev in parsed if ev["metrics"].get("d_rev") is not None]
    correct_vals = [ev["metrics"].get("correct", False) for ev in parsed]

    n_conservative = sum(1 for v in conservative_vals if v is True)
    n_resolves     = sum(1 for v in resolves_vals if v is True)
    n_both = sum(
        1 for cv, rv in zip(conservative_vals, resolves_vals)
        if cv is True and rv is True
    )

    # d_rev distribution
    d_rev_dist: dict = defaultdict(int)
    for v in d_rev_vals:
        d_rev_dist[v] += 1

    # Accuracy by conservativity
    acc_by_cons: dict = {"conservative": {"c": 0, "t": 0}, "non_conservative": {"c": 0, "t": 0}, "unknown": {"c": 0, "t": 0}}
    for ev in parsed:
        m = ev["metrics"]
        cv = m.get("is_conservative")
        correct = m.get("correct", False)
        key = "conservative" if cv is True else ("non_conservative" if cv is False else "unknown")
        acc_by_cons[key]["t"] += 1
        if correct:
            acc_by_cons[key]["c"] += 1

    return {
        "n_level3": len(l3),
        "n_parsed": n_parsed,
        "conservativity_rate": n_conservative / n_parsed,
        "resolves_rate": n_resolves / n_parsed,
        "conservative_and_resolves_rate": n_both / n_parsed,
        "d_rev_mean": sum(d_rev_vals) / len(d_rev_vals) if d_rev_vals else None,
        "d_rev_distribution": dict(sorted(d_rev_dist.items())),
        "accuracy_by_conservative": {
            k: {"accuracy": v["c"] / v["t"] if v["t"] > 0 else None, **v}
            for k, v in acc_by_cons.items()
        },
    }


def print_conservativity_report(evaluations: list[dict]) -> None:
    print("=" * 70)
    print("Level 3 Conservativity / Belief Revision Analysis -- Section 5.3")
    print("=" * 70)

    result = analyze_conservativity(evaluations)
    if "error" in result:
        print(result["error"])
        return

    print(f"Level 3 evaluations      : {result['n_level3']}")
    print(f"Parsed responses         : {result['n_parsed']}")
    print(f"Resolve rate             : {result['resolves_rate']:.1%}")
    print(f"Conservativity rate      : {result['conservativity_rate']:.1%}")
    print(f"Conservative + resolves  : {result['conservative_and_resolves_rate']:.1%}")
    d_rev_mean = result.get("d_rev_mean")
    if d_rev_mean is not None:
        print(f"Mean revision distance   : {d_rev_mean:.2f}")
    print()

    print("d_rev Distribution:")
    for v, count in result["d_rev_distribution"].items():
        print(f"  d_rev = {v}: {count}")
    print()

    print("Accuracy by Conservativity:")
    for label, d in result["accuracy_by_conservative"].items():
        acc = d["accuracy"]
        if acc is None:
            print(f"  {label:<25}: -- (n=0)")
        else:
            print(f"  {label:<25}: {acc:.1%}  ({d['c']}/{d['t']})")


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

    print_conservativity_report(evaluations)
