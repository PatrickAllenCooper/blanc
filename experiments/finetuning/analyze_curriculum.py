"""
Phase B6: Curriculum Strategy Comparison (Section 6.7).

Compares four curriculum schedules for DPO fine-tuning:
  - joint:      All level pairs mixed uniformly (Section 6.5, Equation 8a)
  - sequential: Level-1/2 pairs first, then Level-3 pairs
  - weighted:   Level-3 pairs repeated 5x relative to Level-1/2
  - l12_only:   Level-1/2 pairs only (B4 ablation baseline)

Reports L2 and L3 accuracy for each schedule across all three models.
Performs Friedman test for within-model curriculum differences.

Usage:
  python experiments/finetuning/analyze_curriculum.py \\
      --results-dir experiments/results/

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
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


def _method_short(cfg: dict) -> str:
    if "mode" in cfg:
        return "VITL" if cfg["mode"] == "vitl" else "RLHF-RM"
    variant = cfg.get("dpo_variant", "standard")
    return "DPO-margin" if variant in ("margin", "margin-strict") else "DPO-std"


def _level(ev: dict) -> int:
    iid = ev.get("instance_id", "")
    if "l3" in iid.lower() or "-l3-" in iid:
        return 3
    return ev.get("level", 2)


def _accuracy(evals: list[dict], level: int) -> tuple[float, int, int]:
    subset  = [e for e in evals if _level(e) == level]
    correct = sum(1 for e in subset if e.get("metrics", {}).get("correct", False))
    n       = len(subset)
    return correct / n if n else float("nan"), correct, n


def _friedman_test(data: list[list[float]]) -> dict:
    """Friedman test for k related samples (rows=subjects/models, cols=treatments/curricula)."""
    try:
        from scipy.stats import friedmanchisquare
        if not data or len(data[0]) < 3:
            return {"chi2": float("nan"), "p": float("nan")}
        args = list(zip(*data))
        stat, p = friedmanchisquare(*[list(a) for a in args])
        return {"chi2": float(stat), "p": float(p)}
    except (ImportError, Exception):
        return {"chi2": float("nan"), "p": float("nan")}


def main() -> int:
    p = argparse.ArgumentParser(description="Curriculum comparison (Section 6.7).")
    p.add_argument("--results-dir", default="experiments/results")
    args = p.parse_args()

    results_dir = ROOT / args.results_dir
    all_results = _load_all_results(results_dir)
    ft_results  = [(e, m) for e, m in all_results if _is_finetuned(m)]

    if not ft_results:
        print("No fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    # --- Group by (model, curriculum, method) and keep best ---
    # Use margin-DPO for curriculum comparison (same variant across all curricula)
    by_key: dict[tuple, tuple] = {}
    for evals, meta in ft_results:
        cfg        = _load_training_config(meta.get("checkpoint", ""))
        model      = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        curriculum = cfg.get("curriculum", "joint")
        method     = _method_short(cfg)
        key        = (model, curriculum, method)
        acc3, _, _ = _accuracy(evals, level=3)
        if key not in by_key or acc3 > _accuracy(by_key[key][0], 3)[0]:
            by_key[key] = (evals, meta)

    print("=" * 72)
    print("Curriculum Strategy Comparison (Section 6.7)")
    print("=" * 72)

    model_order = ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]
    curr_order  = ["joint", "sequential", "weighted", "l12_only"]
    method_order = ["DPO-std", "DPO-margin", "VITL"]

    # One table per method for clarity
    for method in method_order:
        keys_for_method = [(k, v) for k, v in by_key.items() if k[2] == method]
        if not keys_for_method:
            continue

        print(f"\n  Method: {method}")
        print(f"  {'Model':<14} {'Curriculum':<14} {'L2':>7} {'L3':>7}")
        print("  " + "-" * 44)

        l3_by_model_curr: dict[str, dict[str, float]] = defaultdict(dict)

        for model in model_order:
            for curriculum in curr_order:
                key = (model, curriculum, method)
                if key not in by_key:
                    continue
                evals, _ = by_key[key]
                acc2, _, _ = _accuracy(evals, level=2)
                acc3, _, _ = _accuracy(evals, level=3)
                l3_by_model_curr[model][curriculum] = acc3
                acc2_str = f"{acc2:.1%}" if acc2 == acc2 else "---"
                acc3_str = f"{acc3:.1%}" if acc3 == acc3 else "---"
                print(f"  {model:<14} {curriculum:<14} {acc2_str:>7} {acc3_str:>7}")

        # Friedman test: rows=models, cols=curricula
        common_currs = None
        for model, currs in l3_by_model_curr.items():
            if common_currs is None:
                common_currs = set(currs.keys())
            else:
                common_currs &= set(currs.keys())

        if common_currs and len(common_currs) >= 3:
            sorted_currs = [c for c in curr_order if c in common_currs]
            matrix = [
                [l3_by_model_curr[m].get(c, float("nan")) for c in sorted_currs]
                for m in model_order if m in l3_by_model_curr
            ]
            # Filter out rows with nan
            matrix = [r for r in matrix if all(x == x for x in r)]
            if matrix:
                stat = _friedman_test(matrix)
                print(f"\n  Friedman test (L3, curricula={sorted_currs}):")
                print(f"    chi2={stat['chi2']:.3f}, p={stat['p']:.4f}")
                if stat['p'] == stat['p'] and stat['p'] < 0.05:
                    best_curr = sorted_currs[
                        max(range(len(sorted_currs)),
                            key=lambda i: sum(r[i] for r in matrix))
                    ]
                    print(f"    Significant difference. Best curriculum: {best_curr}")
                elif stat['p'] == stat['p']:
                    print("    No significant difference between curricula (p >= 0.05).")

    print("\nCurriculum comparison complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
