"""
Scaling Analysis -- paper Section 4.9.

Two analyses:

A. Theory size scaling:
   For each source KB, generate subtheories of increasing size
   |D| in {50, 100, 200, 500, 1000} and evaluate accuracy as a
   function of |D|.  Characterises whether performance degradation
   is gradual or catastrophic.

B. Model scaling (Llama 8B vs 70B):
   Compare within-family models on identical instances to measure
   the scaling gradient delta_Acc / delta_log(params) per level.
   The paper predicts Level 3 may exhibit threshold behaviour.

This script processes completed evaluation results to extract scaling
curves.  The actual model calls are handled by run_evaluation.py;
this script analyses the saved JSON outputs.

Author: Anonymous Authors
Date: 2026-02-18
"""

import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from analyze_results import load_results, accuracy_by, _extract


# ---------------------------------------------------------------------------
# Theory size scaling
# ---------------------------------------------------------------------------

def theory_size_scaling(evaluations: list[dict]) -> dict:
    """
    Extract accuracy as a function of theory size.

    Requires that evaluation records contain ``theory_size`` in the instance
    metadata field.  Buckets theory sizes into the standard bins.

    Returns dict: {model: {size_bin: {correct, total, accuracy}}}
    """
    SIZE_BINS = [50, 100, 200, 500, 1000]

    def _bin(size: int) -> int:
        for b in SIZE_BINS:
            if size <= b:
                return b
        return SIZE_BINS[-1]

    by_model_size: dict = defaultdict(lambda: defaultdict(lambda: {"correct": 0, "total": 0}))

    for ev in evaluations:
        model = ev.get("model", "unknown")
        # theory_size may be in instance metadata (stored by the pipeline)
        theory_size = ev.get("theory_size") or ev.get("metadata", {}).get("theory_size")
        if theory_size is None:
            continue
        b = _bin(int(theory_size))
        by_model_size[model][b]["total"] += 1
        if ev.get("metrics", {}).get("correct", False):
            by_model_size[model][b]["correct"] += 1

    result = {}
    for model, sizes in by_model_size.items():
        result[model] = {}
        for size, counts in sorted(sizes.items()):
            n = counts["total"]
            result[model][size] = {
                "correct": counts["correct"],
                "total": n,
                "accuracy": counts["correct"] / n if n > 0 else None,
            }
    return result


def fit_scaling_curve(sizes: list[int], accuracies: list[float]) -> dict:
    """
    Fit linear and log-linear models to a (size, accuracy) curve.

    Returns fit parameters and which model fits better.
    """
    if len(sizes) < 2:
        return {"error": "Insufficient data points"}

    n = len(sizes)
    x = sizes
    y = accuracies
    log_x = [math.log(xi) if xi > 0 else 0.0 for xi in x]

    def _linear_fit(xs, ys):
        mx = sum(xs) / n
        my = sum(ys) / n
        cov = sum((xi - mx) * (yi - my) for xi, yi in zip(xs, ys)) / n
        var = sum((xi - mx) ** 2 for xi in xs) / n
        if var < 1e-12:
            return 0.0, my, float("nan")
        slope = cov / var
        intercept = my - slope * mx
        residuals = [(yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(xs, ys)]
        r2 = 1 - sum(residuals) / (sum((yi - my) ** 2 for yi in ys) + 1e-12)
        return slope, intercept, r2

    lin_slope, lin_int, lin_r2 = _linear_fit(x, y)
    log_slope, log_int, log_r2 = _linear_fit(log_x, y)

    return {
        "linear": {"slope": lin_slope, "intercept": lin_int, "r2": lin_r2},
        "log_linear": {"slope": log_slope, "intercept": log_int, "r2": log_r2},
        "best_fit": "log_linear" if log_r2 > lin_r2 else "linear",
    }


def print_theory_size_report(evaluations: list[dict]) -> None:
    print("=" * 70)
    print("Theory Size Scaling -- Section 4.9")
    print("=" * 70)

    scaling = theory_size_scaling(evaluations)
    if not scaling:
        print("No theory_size information in evaluation records.")
        print("Ensure run_evaluation.py stores theory_size in instance metadata.")
        return

    for model, sizes in sorted(scaling.items()):
        print(f"\n{model}:")
        print(f"  {'|D|':>6}  {'n':>5}  {'Acc':>7}")
        xs, ys = [], []
        for size, d in sorted(sizes.items()):
            acc_str = f"{d['accuracy']:.1%}" if d["accuracy"] is not None else "--"
            print(f"  {size:>6}  {d['total']:>5}  {acc_str:>7}")
            if d["accuracy"] is not None:
                xs.append(size)
                ys.append(d["accuracy"])

        if len(xs) >= 2:
            fit = fit_scaling_curve(xs, ys)
            print(f"  Best fit: {fit['best_fit']}  "
                  f"(linear R²={fit['linear']['r2']:.3f}, "
                  f"log-linear R²={fit['log_linear']['r2']:.3f})")
            if fit["best_fit"] == "log_linear":
                print(f"  log-linear slope: {fit['log_linear']['slope']:.4f} accuracy/ln(|D|)")


# ---------------------------------------------------------------------------
# Model scaling (Llama 8B vs 70B)
# ---------------------------------------------------------------------------

SCALING_PAIRS = [
    ("llama3:8b",  "llama3:70b",   8e9,  70e9),
    ("llama-3-8b", "llama-3-70b",  8e9,  70e9),
]


def model_scaling_analysis(evaluations: list[dict]) -> dict:
    """
    Compare accuracy between model pairs at different scales (8B vs 70B).

    Returns gradient delta_Acc / delta_log(params) per level.
    """
    result = {}

    for small_name, large_name, small_params, large_params in SCALING_PAIRS:
        small_evs = [ev for ev in evaluations
                     if small_name in ev.get("model", "").lower()]
        large_evs = [ev for ev in evaluations
                     if large_name in ev.get("model", "").lower()]

        if not small_evs or not large_evs:
            continue

        delta_log_params = math.log(large_params) - math.log(small_params)
        pair_key = f"{small_name}_vs_{large_name}"
        result[pair_key] = {}

        for level in ("2", "3"):
            small_l = [ev for ev in small_evs if _extract(ev, "level") == level]
            large_l = [ev for ev in large_evs if _extract(ev, "level") == level]

            if not small_l or not large_l:
                continue

            acc_small = sum(ev["metrics"]["correct"] for ev in small_l) / len(small_l)
            acc_large = sum(ev["metrics"]["correct"] for ev in large_l) / len(large_l)
            gradient = (acc_large - acc_small) / delta_log_params if delta_log_params > 0 else 0.0

            result[pair_key][level] = {
                "acc_small": acc_small,
                "acc_large": acc_large,
                "delta_acc": acc_large - acc_small,
                "delta_log_params": delta_log_params,
                "gradient": gradient,
                "n_small": len(small_l),
                "n_large": len(large_l),
            }

    return result


def print_model_scaling_report(evaluations: list[dict]) -> None:
    print("=" * 70)
    print("Model Scaling Analysis (Llama 8B vs 70B) -- Section 4.9")
    print("=" * 70)

    scaling = model_scaling_analysis(evaluations)
    if not scaling:
        print("No matched model pairs found in results.")
        print("Ensure both Llama 8B and 70B evaluations are present.")
        return

    for pair, levels in sorted(scaling.items()):
        print(f"\n{pair}:")
        for level, d in sorted(levels.items()):
            print(f"  Level {level}:")
            print(f"    Acc(small)={d['acc_small']:.1%}  Acc(large)={d['acc_large']:.1%}  "
                  f"delta={d['delta_acc']:+.1%}  gradient={d['gradient']:.4f}/ln-param")
            if d["gradient"] < 0.005 and level == "3":
                print("    NOTE: Near-zero gradient at Level 3 -- possible threshold behaviour.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Scaling analysis (Section 4.9)")
    parser.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--results-file", default=None)
    parser.add_argument("--save", default=None)
    args = parser.parse_args()

    path = Path(args.results_file) if args.results_file else Path(args.results_dir)
    if not path.exists():
        print(f"Error: {path} does not exist.")
        return 1

    evaluations = load_results(path)
    if not evaluations:
        print("No evaluations found.")
        return 1

    print_theory_size_report(evaluations)
    print()
    print_model_scaling_report(evaluations)

    if args.save:
        output = {
            "theory_size_scaling": theory_size_scaling(evaluations),
            "model_scaling": model_scaling_analysis(evaluations),
        }
        with open(args.save, "w") as f:
            json.dump(output, f, indent=2, default=str)
        print(f"\nSaved to: {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
