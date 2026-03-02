"""
Phase B6: Level-Transfer Analysis (Conjecture 3, Section 6.8).

Conjecture 3: Training on Level-1/2 instances alone (l12_only curriculum)
produces a positive lift on Level-3 accuracy, demonstrating that rule-abduction
training partially teaches the reasoning structure required for defeater abduction.

Compares:
  - Base model L3 accuracy
  - l12_only fine-tuned model L3 accuracy (level-transfer lift)
  - Full curriculum fine-tuned model L3 accuracy

This quantifies how much of the fine-tuning benefit can be attributed to the
shared deductive structure of grounding and abduction, vs. the L3-specific
preference signal.

Usage:
  python experiments/finetuning/analyze_level_transfer.py \\
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


def _accuracy_l3(evals: list[dict]) -> tuple[float, int, int]:
    subset  = [e for e in evals if _level(e) == 3]
    correct = sum(1 for e in subset if e.get("metrics", {}).get("correct", False))
    n       = len(subset)
    return correct / n if n else float("nan"), correct, n


def main() -> int:
    p = argparse.ArgumentParser(description="Level-transfer analysis (Conjecture 3).")
    p.add_argument("--results-dir",      default="experiments/results")
    p.add_argument("--base-results-dir", default="experiments/results")
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

    # --- Base L3 accuracy per model ---
    base_acc: dict[str, tuple] = {}
    for evals, _ in base_results:
        for ev in evals:
            if _level(ev) != 3:
                continue
            model = _model_short(ev.get("model", ""))
            if model not in base_acc:
                base_acc[model] = _accuracy_l3(
                    [e for e in evals if _model_short(e.get("model", "")) == model]
                )

    # --- Categorize FT results by curriculum ---
    by_model_curriculum: dict[str, dict[str, tuple]] = defaultdict(dict)
    for evals, meta in ft_results:
        cfg        = _load_training_config(meta.get("checkpoint", ""))
        model      = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        curriculum = cfg.get("curriculum", "joint")
        acc, c, n  = _accuracy_l3(evals)
        # Keep best (highest L3 accuracy) for each (model, curriculum)
        if curriculum not in by_model_curriculum[model] or \
                acc > by_model_curriculum[model][curriculum][0]:
            by_model_curriculum[model][curriculum] = (acc, c, n)

    print("=" * 72)
    print("Conjecture 3: Level Transfer -- L1/L2 Training -> L3 Lift")
    print("=" * 72)
    print(f"{'Model':<14} {'Curriculum':<14} {'L3 Acc':>8} {'Lift vs Base':>14}")
    print("-" * 72)

    model_order = ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]
    curr_order  = ["joint", "sequential", "weighted", "l12_only"]

    for model in model_order:
        if model not in by_model_curriculum:
            continue
        base_val = base_acc.get(model, (float("nan"), 0, 0))[0]
        base_str = f"{base_val:.1%}" if base_val == base_val else "---"
        print(f"  {model:<12} {'Base':<14} {base_str:>8}")

        for curriculum in curr_order:
            if curriculum not in by_model_curriculum[model]:
                continue
            acc, c, n = by_model_curriculum[model][curriculum]
            lift      = acc - base_val if base_val == base_val else float("nan")
            acc_str   = f"{acc:.1%}" if acc == acc else "---"
            lift_str  = f"{lift:+.1%}" if lift == lift else "---"
            marker    = " *" if curriculum == "l12_only" else ""
            print(f"  {model:<12} {curriculum:<14} {acc_str:>8} {lift_str:>14}{marker}")
        print()

    print("* l12_only: trained only on Level-1/2 pairs (B4 ablation)")
    print("\nKey question: Is l12_only lift > 0? (Conjecture 3)")
    found_l12 = False
    for model in model_order:
        if "l12_only" in by_model_curriculum.get(model, {}):
            found_l12 = True
            acc, _, _ = by_model_curriculum[model]["l12_only"]
            base_val  = base_acc.get(model, (float("nan"),))[0]
            if base_val == base_val and acc == acc:
                lift = acc - base_val
                verdict = "CONFIRMED" if lift > 0 else "NOT CONFIRMED"
                print(f"  {model}: lift={lift:+.1%} => Conjecture 3 {verdict}")

    if not found_l12:
        print("  l12_only results not yet available. Submit B4 ablation first:")
        print("  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-72B-Instruct-AWQ',"
              "DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=l12_only hpc/slurm_train_dpo.sh")

    return 0


if __name__ == "__main__":
    sys.exit(main())
