"""
Phase B6: Data Scaling Projections (Section 6.8).

Fits a log-linear scaling curve to L3 accuracy as a function of preference data
fraction used during training (10%, 25%, 50%, 100%).

Requires models trained with different data fractions (use --data-fraction flag
in train_dpo.py). Results are identified by the 'data_fraction' field in their
training_config.json.

If only a single result is available, displays the point and warns about the
missing ablation runs.

Fitting model (log-linear):
  acc(f) = a * log(f) + b
where f in (0, 1] is the data fraction.

Usage:
  python experiments/finetuning/analyze_scaling_projections.py \\
      --results-dir experiments/results/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load_result_file(path: Path) -> tuple[list[dict], dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    return data.get("evaluations", []), data.get("metadata", {})


def _load_all_results(results_dir: Path) -> list[tuple[list[dict], dict]]:
    results = []
    for path in sorted(results_dir.rglob("*.json")):
        try:
            evals, meta = _load_result_file(path)
            if evals:
                results.append((evals, meta))
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def _is_finetuned(meta: dict) -> bool:
    return "checkpoint" in meta


def _load_training_config(checkpoint: str) -> dict:
    cfg_path = Path(checkpoint).parent / "training_config.json"
    if not cfg_path.exists():
        cfg_path = Path(checkpoint) / "training_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _model_short(base_model: str) -> str:
    if "72b" in base_model.lower():
        return "Qwen-72B"
    if "32b" in base_model.lower():
        return "Qwen-32B"
    if "deepseek" in base_model.lower() or "r1" in base_model.lower():
        return "DS-R1-70B"
    return base_model.split("/")[-1][:15]


def _level(ev: dict) -> int:
    iid = ev.get("instance_id", "")
    if "l3" in iid.lower() or "-l3-" in iid:
        return 3
    return ev.get("level", 2)


def _accuracy(evals: list[dict], level: int) -> float:
    subset  = [e for e in evals if _level(e) == level]
    correct = sum(1 for e in subset if e.get("metrics", {}).get("correct", False))
    return correct / len(subset) if subset else float("nan")


def _fit_loglinear(fractions: list[float], accuracies: list[float]) -> tuple[float, float, float]:
    """
    Fit acc = a * log(f) + b via ordinary least squares.
    Returns (a, b, r_squared).
    """
    n = len(fractions)
    if n < 2:
        return float("nan"), float("nan"), float("nan")
    xs = [math.log(f) for f in fractions]
    mean_x = sum(xs) / n
    mean_y = sum(accuracies) / n
    ss_xy = sum((xs[i] - mean_x) * (accuracies[i] - mean_y) for i in range(n))
    ss_xx = sum((xs[i] - mean_x) ** 2 for i in range(n))
    if ss_xx == 0:
        return 0.0, mean_y, float("nan")
    a = ss_xy / ss_xx
    b = mean_y - a * mean_x
    # R-squared
    ss_res = sum((accuracies[i] - (a * xs[i] + b)) ** 2 for i in range(n))
    ss_tot = sum((accuracies[i] - mean_y) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return a, b, r2


def main() -> int:
    p = argparse.ArgumentParser(description="Data scaling projections (Section 6.8).")
    p.add_argument("--results-dir", default="experiments/results")
    args = p.parse_args()

    results_dir = ROOT / args.results_dir
    all_results = _load_all_results(results_dir)
    ft_results  = [(e, m) for e, m in all_results if _is_finetuned(m)]

    if not ft_results:
        print("No fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    # --- Group by (model, data_fraction) ---
    by_model_frac: dict[str, dict[float, float]] = defaultdict(dict)
    for evals, meta in ft_results:
        cfg        = _load_training_config(meta.get("checkpoint", ""))
        model      = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        data_frac  = float(cfg.get("data_fraction", 1.0))
        curriculum = cfg.get("curriculum", "joint")
        # Only include full-curriculum runs for the scaling analysis
        if curriculum not in ("joint", "weighted"):
            continue
        acc3 = _accuracy(evals, level=3)
        if acc3 == acc3:  # not nan
            existing = by_model_frac[model].get(data_frac, float("nan"))
            if existing != existing or acc3 > existing:
                by_model_frac[model][data_frac] = acc3

    print("=" * 72)
    print("Data Scaling Projections (Section 6.8)")
    print("=" * 72)

    for model in ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]:
        if model not in by_model_frac:
            continue
        fracs = sorted(by_model_frac[model].keys())
        accs  = [by_model_frac[model][f] for f in fracs]

        print(f"\n  {model}")
        print(f"  {'Fraction':>10} {'L3 Accuracy':>12}")
        for f, a in zip(fracs, accs):
            print(f"  {f:>10.0%} {a:>12.1%}")

        if len(fracs) >= 2:
            a, b, r2 = _fit_loglinear(fracs, accs)
            print(f"\n  Log-linear fit: acc = {a:.4f} * log(f) + {b:.4f}  (R^2={r2:.3f})")
            for frac in [0.10, 0.25, 0.50, 1.0]:
                if frac not in by_model_frac[model]:
                    pred = a * math.log(frac) + b
                    print(f"  Projected at {frac:.0%}: {pred:.1%}")
        else:
            print("\n  Insufficient points for log-linear fit.")
            print("  Submit scaling ablation runs with --data-fraction 0.1 0.25 0.5")
            print("  Example:")
            print("    for F in 0.1 0.25 0.5; do")
            print("      sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-72B-Instruct-AWQ',"
                  "DPO_VARIANT=margin,DATA_FRACTION=$F hpc/slurm_train_dpo.sh")
            print("    done")

    return 0


if __name__ == "__main__":
    sys.exit(main())
