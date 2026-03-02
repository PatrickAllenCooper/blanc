"""
Phase B6: Analyze Level-3 Accuracy Lift (Conjecture 1, Section 6.8).

Conjecture 1: Fine-tuning via DPO and VITL produces a positive lift on Level-3
defeater abduction accuracy, and VITL lift > DPO lift.

Tests:
  - H1: acc_L3(FT) > acc_L3(base)  for each (model, method)
  - H2: lift_VITL > lift_DPO        for each model
  Statistical test: McNemar's chi-squared on paired correct/incorrect predictions.

Usage:
  python experiments/finetuning/analyze_ft_lift.py \\
      --results-dir experiments/results/ \\
      --base-results-dir experiments/results/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Utilities (shared with generate_ft_tables.py)
# ---------------------------------------------------------------------------

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
    return correct / len(subset) if subset else float("nan"), correct, len(subset)


def _mcnemar(correct_a: set, correct_b: set, total_ids: set) -> dict:
    """
    McNemar's test: A correct, B wrong vs A wrong, B correct.
    Returns {"b": int, "c": int, "chi2": float, "p": float}.
    """
    b = sum(1 for i in total_ids if i in correct_a and i not in correct_b)
    c = sum(1 for i in total_ids if i not in correct_a and i in correct_b)

    if b + c == 0:
        return {"b": b, "c": c, "chi2": 0.0, "p": 1.0}

    chi2 = (abs(b - c) - 1) ** 2 / (b + c)

    try:
        from scipy.stats import chi2 as chi2_dist
        p = float(chi2_dist.sf(chi2, df=1))
    except ImportError:
        p = float("nan")

    return {"b": b, "c": c, "chi2": chi2, "p": p}


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def main() -> int:
    p = argparse.ArgumentParser(description="Analyze L3 lift (Conjecture 1).")
    p.add_argument("--results-dir",      default="experiments/results",
                   help="Directory with fine-tuned evaluation results.")
    p.add_argument("--base-results-dir", default="experiments/results",
                   help="Directory with base model evaluation results.")
    args = p.parse_args()

    results_dir      = ROOT / args.results_dir
    base_results_dir = ROOT / args.base_results_dir

    all_results  = _load_all_results(results_dir)
    ft_results   = [(e, m) for e, m in all_results if _is_finetuned(m)]
    base_results = [(e, m) for e, m in _load_all_results(base_results_dir)
                    if not _is_finetuned(m)]

    if not ft_results:
        print("No fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    # --- Build base model accuracy by (model, instance_id) ---
    base_correct_by_model: dict[str, set] = defaultdict(set)
    base_acc_l3: dict[str, tuple] = {}
    for evals, _ in base_results:
        for ev in evals:
            if _level(ev) != 3:
                continue
            model = _model_short(ev.get("model", ""))
            iid   = ev.get("instance_id", "")
            if ev.get("metrics", {}).get("correct", False):
                base_correct_by_model[model].add(iid)

    for model, correct_set in base_correct_by_model.items():
        n    = max(1, len(correct_set))  # lower bound; real n from FT evals
        base_acc_l3[model] = (len(correct_set), n)

    # --- Analyze each FT result ---
    print("=" * 72)
    print("Conjecture 1: Level-3 Accuracy Lift from Fine-Tuning")
    print("=" * 72)
    print(f"{'Model':<14} {'Method':<12} {'Base L3':>8} {'FT L3':>8} "
          f"{'Lift':>8} {'p-value':>9}")
    print("-" * 72)

    lifts: dict[str, list] = defaultdict(list)  # model -> list of (method, lift)

    for evals, meta in sorted(ft_results, key=lambda x: x[1].get("checkpoint", "")):
        cfg    = _load_training_config(meta.get("checkpoint", ""))
        model  = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        method = _method_short(cfg)

        ft_acc, ft_c, ft_n = _accuracy(evals, level=3)
        if ft_n == 0:
            print(f"  {model:<12} {method:<12} -- no L3 instances in results")
            continue

        # Compute lift vs base model
        ft_correct  = {ev.get("instance_id") for ev in evals
                       if _level(ev) == 3 and ev.get("metrics", {}).get("correct", False)}
        base_correct = base_correct_by_model.get(model, set())
        all_ids      = {ev.get("instance_id") for ev in evals if _level(ev) == 3}

        if base_correct:
            base_acc_val = len(base_correct) / max(ft_n, len(base_correct))
        else:
            base_acc_val = float("nan")

        lift = ft_acc - base_acc_val if base_correct else float("nan")

        if base_correct:
            stat = _mcnemar(ft_correct, base_correct & all_ids, all_ids)
            p_str = f"{stat['p']:.4f}" if stat['p'] is not float("nan") else "---"
        else:
            p_str = "---"

        base_str = f"{base_acc_val:.1%}" if base_correct else "---"
        lift_str = f"{lift:+.1%}" if base_correct else "---"
        print(f"  {model:<12} {method:<12} {base_str:>8} {ft_acc:.1%} "
              f"{lift_str:>8} {p_str:>9}")

        if not any(m.isnan() for m in [lift]) if base_correct else False:
            lifts[model].append((method, lift))

    # --- Test H2: VITL lift > DPO lift ---
    print("\n--- H2: VITL vs DPO Lift Comparison ---")
    for model, entries in lifts.items():
        vitl_lifts = [l for m, l in entries if m == "VITL"]
        dpo_lifts  = [l for m, l in entries if "DPO" in m]
        if vitl_lifts and dpo_lifts:
            vitl_l = max(vitl_lifts)
            dpo_l  = max(dpo_lifts)
            direction = "VITL > DPO" if vitl_l > dpo_l else "DPO >= VITL"
            print(f"  {model}: VITL lift={vitl_l:+.1%}, best DPO lift={dpo_l:+.1%} => {direction}")
        else:
            print(f"  {model}: insufficient data for VITL vs DPO comparison")

    print("\nConjecture 1 evaluation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
