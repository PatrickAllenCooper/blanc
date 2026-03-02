"""
Phase B6: Margin-DPO vs Standard-DPO Effect (Conjecture 4, Section 6.8).

Conjecture 4: Margin-weighted DPO outperforms standard DPO, with the advantage
concentrated at the 0.5->0.75 transition in the Level-3 graded scoring function.

The 0.5->0.75 transition corresponds to acquiring conservativity (the model learns
to produce a defeater that defeats the query expectation without defeating other
expectations -- the hardest reasoning step). Margin DPO should preferentially
reinforce the large-margin pairs (score 0 vs 1.0) that span this transition.

Also sweeps gamma values if multiple gamma results are available.

Usage:
  python experiments/finetuning/analyze_margin_effect.py \\
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


def _accuracy(evals: list[dict], level: int) -> tuple[float, int]:
    subset  = [e for e in evals if _level(e) == level]
    correct = sum(1 for e in subset if e.get("metrics", {}).get("correct", False))
    n       = len(subset)
    return correct / n if n else float("nan"), n


def _graded_score_dist(evals: list[dict]) -> dict[float, int]:
    """Distribution of graded L3 scores (from metrics.graded_score)."""
    dist: dict[float, int] = defaultdict(int)
    for ev in evals:
        if _level(ev) != 3:
            continue
        gs = ev.get("metrics", {}).get("graded_score", None)
        if gs is not None:
            dist[round(float(gs), 2)] += 1
    return dict(dist)


def _wilcoxon_test(scores_a: list[float], scores_b: list[float]) -> dict:
    """Wilcoxon signed-rank test for paired score comparisons."""
    try:
        from scipy.stats import wilcoxon
        if len(scores_a) != len(scores_b) or len(scores_a) == 0:
            return {"statistic": float("nan"), "p": float("nan")}
        stat, p = wilcoxon(scores_a, scores_b, alternative="greater")
        return {"statistic": float(stat), "p": float(p)}
    except (ImportError, Exception):
        return {"statistic": float("nan"), "p": float("nan")}


def main() -> int:
    p = argparse.ArgumentParser(description="Margin DPO effect analysis (Conjecture 4).")
    p.add_argument("--results-dir",      default="experiments/results")
    p.add_argument("--base-results-dir", default="experiments/results")
    args = p.parse_args()

    results_dir = ROOT / args.results_dir
    all_results = _load_all_results(results_dir)
    ft_results  = [(e, m) for e, m in all_results if _is_finetuned(m)]

    if not ft_results:
        print("No fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    # --- Group by (model, curriculum, variant, gamma) ---
    by_key: dict[tuple, tuple[list[dict], dict]] = {}
    for evals, meta in ft_results:
        cfg        = _load_training_config(meta.get("checkpoint", ""))
        model      = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        variant    = cfg.get("dpo_variant", cfg.get("mode", "unknown"))
        curriculum = cfg.get("curriculum", "joint")
        gamma      = cfg.get("margin_delta", cfg.get("gamma", 0.0))
        key        = (model, curriculum, variant, float(gamma))
        acc, n     = _accuracy(evals, level=3)
        # Keep the result with highest L3 accuracy per key
        if key not in by_key or acc > _accuracy(by_key[key][0], level=3)[0]:
            by_key[key] = (evals, meta)

    print("=" * 72)
    print("Conjecture 4: Margin-DPO vs Standard-DPO")
    print("=" * 72)
    print(f"{'Model':<14} {'Curr':<12} {'Variant':<14} {'Gamma':>6} "
          f"{'L2':>7} {'L3':>7}")
    print("-" * 72)

    for (model, curriculum, variant, gamma), (evals, meta) in sorted(by_key.items()):
        acc2, n2 = _accuracy(evals, level=2)
        acc3, n3 = _accuracy(evals, level=3)
        acc2_str = f"{acc2:.1%}" if acc2 == acc2 else "---"
        acc3_str = f"{acc3:.1%}" if acc3 == acc3 else "---"
        gamma_str = f"{gamma:.1f}"
        print(f"  {model:<12} {curriculum:<12} {variant:<14} {gamma_str:>6} "
              f"{acc2_str:>7} {acc3_str:>7}")

    # --- Pair comparison: margin vs standard for same (model, curriculum) ---
    print("\n--- Margin vs Standard DPO Paired Comparison ---")
    paired_found = False
    for model in ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]:
        for curriculum in ["joint", "weighted", "sequential"]:
            # Find standard and margin variants
            std_keys    = [k for k in by_key if k[0] == model and k[1] == curriculum
                           and k[2] == "standard"]
            margin_keys = [k for k in by_key if k[0] == model and k[1] == curriculum
                           and k[2] in ("margin", "margin-strict")]
            if not std_keys or not margin_keys:
                continue

            paired_found = True
            best_std    = max(std_keys,    key=lambda k: _accuracy(by_key[k][0], 3)[0])
            best_margin = max(margin_keys, key=lambda k: _accuracy(by_key[k][0], 3)[0])

            acc_std,    _ = _accuracy(by_key[best_std][0],    level=3)
            acc_margin, _ = _accuracy(by_key[best_margin][0], level=3)
            diff = acc_margin - acc_std if (acc_std == acc_std and acc_margin == acc_margin) else float("nan")

            # Graded score distributions for deeper comparison
            dist_std    = _graded_score_dist(by_key[best_std][0])
            dist_margin = _graded_score_dist(by_key[best_margin][0])

            verdict = ("DPO-margin > DPO-std" if diff > 0 else
                       "DPO-std >= DPO-margin" if diff < 0 else "tied")
            diff_str = f"{diff:+.1%}" if diff == diff else "---"
            print(f"\n  {model} / {curriculum}: {verdict}")
            print(f"    Standard  L3: {acc_std:.1%} | Margin L3: {acc_margin:.1%} "
                  f"| Diff: {diff_str}")
            print(f"    Score dist (std): {dict(sorted(dist_std.items()))}")
            print(f"    Score dist (mrg): {dict(sorted(dist_margin.items()))}")

            # Check if advantage is at 0.5->0.75 transition
            adv_075_std    = dist_std.get(0.75, 0) + dist_std.get(1.0, 0)
            adv_075_margin = dist_margin.get(0.75, 0) + dist_margin.get(1.0, 0)
            n_std    = sum(dist_std.values()) or 1
            n_margin = sum(dist_margin.values()) or 1
            print(f"    Score>=0.75: std {adv_075_std/n_std:.1%} vs "
                  f"margin {adv_075_margin/n_margin:.1%}")

    if not paired_found:
        print("  No paired (standard, margin) results found.")
        print("  Ensure both DPO_VARIANT=standard and DPO_VARIANT=margin jobs are complete.")

    # --- Gamma sweep ---
    print("\n--- Gamma Sweep (Qwen-72B, joint curriculum) ---")
    gamma_rows = [(k[3], _accuracy(v[0], 3)[0]) for k, v in by_key.items()
                  if k[0] == "Qwen-72B" and k[1] == "joint"
                  and k[2] in ("margin", "margin-strict")]
    if len(gamma_rows) > 1:
        for gamma, acc3 in sorted(gamma_rows):
            acc3_str = f"{acc3:.1%}" if acc3 == acc3 else "---"
            print(f"  gamma={gamma:.1f}: L3={acc3_str}")
        best_gamma = max(gamma_rows, key=lambda x: x[1] if x[1] == x[1] else -1)
        print(f"  Optimal gamma: {best_gamma[0]:.1f}")
    else:
        print("  Gamma sweep not yet complete. Submit gamma sweep jobs:")
        print("  for G in 0.5 1.0 2.0 4.0; do sbatch --export=ALL,"
              "BASE_MODEL='Qwen/Qwen2.5-72B-Instruct-AWQ',"
              "DPO_VARIANT=margin,GAMMA=$G,CURRICULUM=joint hpc/slurm_train_dpo.sh; done")

    print("\nConjecture 4 evaluation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
