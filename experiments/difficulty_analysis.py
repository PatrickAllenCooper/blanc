"""
Difficulty Distribution Analysis -- paper Section 4.3.2.

Extracts structural difficulty tuples
    sigma(I) = (ell, |Supp|, |H*|, min|h|, Nov*)
from instances and produces the marginal distribution statistics and
histograms required by Section 4.3.2.

|Supp| is approximated as theory_size (total facts + rules in D^-).
min|h| is 1 for Level 2 (single fact/rule candidate), and for Level 3
is the number of body atoms in the gold defeater.
Nov* is 0 for Level 2 and inst['nov'] for Level 3.

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Tuple extraction
# ---------------------------------------------------------------------------

def _gold_body_size(gold_str: str) -> int:
    """
    Count body atoms in a rule string like 'label: body1(X), body2(X) ~> head'.
    Returns 1 if parsing fails.
    """
    try:
        # Strip label if present
        if ":" in gold_str and "~>" in gold_str:
            rest = gold_str.split(":", 1)[1].strip()
        else:
            rest = gold_str
        # Body is before ~> or =>
        for arrow in ("~>", "=>"):
            if arrow in rest:
                body = rest.split(arrow)[0].strip()
                return max(1, len([a for a in body.split(",") if a.strip()]))
        return 1
    except Exception:
        return 1


def extract_difficulty_tuples(instance_files: list) -> list[dict]:
    """
    Extract difficulty tuples sigma(I) from all instances.

    Returns a list of dicts with keys:
        level, support_size, gold_count, min_h_size, novelty, n_candidates
    """
    difficulties = []

    for filepath in instance_files:
        filepath = Path(filepath)
        if not filepath.exists():
            continue
        with open(filepath) as f:
            data = json.load(f)

        for inst in data.get("instances", []):
            level = inst.get("level", 2)

            support_size = inst.get("theory_size", 1)
            n_candidates = inst.get("num_candidates") or len(inst.get("candidates", []))

            if level == 2:
                gold_items = inst.get("gold", [])
                gold_count = (
                    inst.get("num_gold")
                    or (len(gold_items) if isinstance(gold_items, list) else 1)
                )
                min_h_size = 1  # Each Level 2 candidate is a single fact/rule
                novelty = 0.0

            else:  # Level 3
                gold_count = 1
                gold_str = inst.get("gold", "")
                if isinstance(gold_str, list):
                    gold_str = gold_str[0] if gold_str else ""
                min_h_size = _gold_body_size(gold_str)
                novelty = float(inst.get("nov") or 0.0)

            difficulties.append({
                "level": level,
                "support_size": support_size,
                "gold_count": gold_count,
                "min_h_size": min_h_size,
                "novelty": novelty,
                "n_candidates": n_candidates,
            })

    return difficulties


# ---------------------------------------------------------------------------
# Analysis and reporting
# ---------------------------------------------------------------------------

def _stats(vals: list) -> dict:
    n = len(vals)
    if n == 0:
        return {"n": 0}
    mean = sum(vals) / n
    variance = sum((v - mean) ** 2 for v in vals) / n
    std = variance ** 0.5
    return {
        "n": n,
        "mean": round(mean, 3),
        "std": round(std, 3),
        "min": min(vals),
        "max": max(vals),
    }


def analyze_difficulty_distributions(difficulties: list[dict]) -> dict:
    """
    Compute marginal statistics for each difficulty component and their
    cross-correlations.  Returns a dict suitable for JSON serialisation.
    """
    print("=" * 70)
    print("Section 4.3.2: Structural Difficulty Distributions")
    print("=" * 70)

    by_level: dict = {2: [], 3: []}
    for d in difficulties:
        by_level[d["level"]].append(d)

    print(f"\nTotal instances: {len(difficulties)}")
    print(f"  Level 2: {len(by_level[2])}")
    print(f"  Level 3: {len(by_level[3])}")
    print()

    results: dict = {}

    for lv in (2, 3):
        subset = by_level[lv]
        if not subset:
            continue

        support_sizes = [d["support_size"] for d in subset]
        gold_counts   = [d["gold_count"]   for d in subset]
        min_h_sizes   = [d["min_h_size"]   for d in subset]
        novelties     = [d["novelty"]       for d in subset]
        n_candidates  = [d["n_candidates"] for d in subset]

        print(f"Level {lv} (n={len(subset)}):")
        for label, vals in [
            ("|Supp| (theory_size)", support_sizes),
            ("|H*|   (gold_count)",  gold_counts),
            ("|H_cand|",             n_candidates),
            ("min|h| (body_size)",   min_h_sizes),
            ("Nov*   (novelty)",     novelties),
        ]:
            s = _stats(vals)
            print(f"  {label:<35}: mean={s['mean']:.2f}  std={s['std']:.2f}  "
                  f"range=[{s['min']}, {s['max']}]")

        # Cross-correlations
        def pearson(xs, ys):
            n = len(xs)
            if n < 2:
                return float("nan")
            mx, my = sum(xs) / n, sum(ys) / n
            cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / n
            sx = (sum((x - mx) ** 2 for x in xs) / n) ** 0.5
            sy = (sum((y - my) ** 2 for y in ys) / n) ** 0.5
            return cov / (sx * sy + 1e-12)

        print(f"  r(|H*|, |H_cand|) = {pearson(gold_counts, n_candidates):.3f}")
        print(f"  r(|Supp|, |H*|)   = {pearson(support_sizes, gold_counts):.3f}")
        if lv == 3:
            print(f"  r(Nov*, |h|)      = {pearson(novelties, min_h_sizes):.3f}")
        print()

        results[f"level{lv}"] = {
            "n": len(subset),
            "support_size": _stats(support_sizes),
            "gold_count":   _stats(gold_counts),
            "n_candidates": _stats(n_candidates),
            "min_h_size":   _stats(min_h_sizes),
            "novelty":      _stats(novelties),
        }

    return results


def plot_distributions(difficulties: list[dict], output_dir: str = "figures") -> None:
    """Save difficulty histograms to PNG (requires matplotlib)."""
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("matplotlib not available -- skipping plots")
        return

    Path(output_dir).mkdir(exist_ok=True)

    for lv in (2, 3):
        subset = [d for d in difficulties if d["level"] == lv]
        if not subset:
            continue

        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        fig.suptitle(f"Level {lv} Difficulty Distributions")

        configs = [
            (axes[0, 0], [d["support_size"] for d in subset], "|Supp| (theory size)"),
            (axes[0, 1], [d["n_candidates"] for d in subset], "|H_cand| (candidates)"),
            (axes[1, 0], [d["gold_count"]   for d in subset], "|H*| (gold count)"),
            (axes[1, 1], [d["novelty"]      for d in subset], "Nov* (predicate novelty)"),
        ]

        for ax, vals, xlabel in configs:
            n_bins = max(5, min(20, len(set(vals))))
            ax.hist(vals, bins=n_bins, edgecolor="black", color="steelblue", alpha=0.8)
            ax.set_xlabel(xlabel)
            ax.set_ylabel("Frequency")
            ax.grid(alpha=0.3)

        plt.tight_layout()
        out = Path(output_dir) / f"difficulty_level{lv}.png"
        plt.savefig(out, dpi=150)
        plt.close()
        print(f"Saved: {out}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Difficulty distribution analysis (Section 4.3.2)")
    parser.add_argument("--instances-dir", default=str(ROOT / "instances"))
    parser.add_argument("--save-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--plots", action="store_true", help="Generate PNG histograms")
    args = parser.parse_args()

    instances_dir = Path(args.instances_dir)
    files = [
        instances_dir / "biology_dev_instances.json",
        instances_dir / "legal_dev_instances.json",
        instances_dir / "materials_dev_instances.json",
        instances_dir / "level3_instances.json",
    ]

    difficulties = extract_difficulty_tuples([str(f) for f in files])
    results = analyze_difficulty_distributions(difficulties)

    if args.plots:
        plot_distributions(difficulties, output_dir=str(ROOT / "figures"))

    Path(args.save_dir).mkdir(parents=True, exist_ok=True)
    out = Path(args.save_dir) / "difficulty_distributions.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved to: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
