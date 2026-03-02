"""
Phase B6: Error Taxonomy Shift Analysis (Conjecture 2, Section 6.8).

Conjecture 2: Fine-tuning shifts the error distribution from E1 (decoder failure)
and E2 (derivation failure) toward E4 (support miss, model makes a partial attempt)
and E5 (novel correct resolutions).

Tests via chi-squared test on error-type distribution before/after fine-tuning.

Error types (Section 5.3, paper):
  E1 -- Decoder failure: response cannot be parsed into a formal hypothesis
  E2 -- Derivation failure: hypothesis is syntactically valid but unsupported
  E3 -- Non-conservativity: defeats required expectations
  E4 -- Support miss: logically valid but fails the support condition
  E5 -- Novel correct: not in gold set, but verifier accepts as valid

Usage:
  python experiments/finetuning/analyze_error_shift.py \\
      --results-dir      experiments/results/ \\
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


def _error_distribution(evals: list[dict], level: int) -> dict[str, int]:
    """Count error types for given level."""
    dist: dict[str, int] = defaultdict(int)
    for ev in evals:
        if _level(ev) != level:
            continue
        et = ev.get("metrics", {}).get("error_type", None)
        if et:
            dist[str(et)] += 1
        elif ev.get("metrics", {}).get("correct", False):
            dist["E5"] += 1  # Correct = E5 / novel
    return dict(dist)


def _chi2_test(obs_a: list[int], obs_b: list[int]) -> dict:
    """Chi-squared test of independence between two count vectors."""
    try:
        from scipy.stats import chi2_contingency
        import numpy as np
        table = np.array([obs_a, obs_b])
        if table.sum() == 0 or table.min() == table.max() == 0:
            return {"chi2": 0.0, "p": 1.0}
        chi2, p, dof, _ = chi2_contingency(table)
        return {"chi2": float(chi2), "p": float(p), "dof": int(dof)}
    except (ImportError, Exception):
        return {"chi2": float("nan"), "p": float("nan"), "dof": 0}


def main() -> int:
    p = argparse.ArgumentParser(description="Analyze error taxonomy shift (Conjecture 2).")
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

    error_types = ["E1", "E2", "E3", "E4", "E5"]

    # --- Base error distributions by model ---
    base_dists: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for evals, _ in base_results:
        for ev in evals:
            if _level(ev) != 3:
                continue
            model = _model_short(ev.get("model", ""))
            et    = ev.get("metrics", {}).get("error_type", None)
            if ev.get("metrics", {}).get("correct", False):
                base_dists[model]["E5"] += 1
            elif et:
                base_dists[model][str(et)] += 1

    # --- Best FT result per model ---
    best_ft: dict[str, tuple[list[dict], dict]] = {}
    for evals, meta in ft_results:
        cfg   = _load_training_config(meta.get("checkpoint", ""))
        model = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        l3_evals = [e for e in evals if _level(e) == 3]
        acc   = sum(1 for e in l3_evals if e.get("metrics", {}).get("correct", False))
        if model not in best_ft or acc > sum(
            1 for e in best_ft[model][0] if _level(e) == 3
            and e.get("metrics", {}).get("correct", False)
        ):
            best_ft[model] = (evals, meta)

    print("=" * 72)
    print("Conjecture 2: Error Taxonomy Shift (E1/E2 -> E4/E5)")
    print("=" * 72)
    print(f"{'Model':<14} Phase      {'E1':>5} {'E2':>5} {'E3':>5} {'E4':>5} "
          f"{'E5':>5} {'chi2':>8} {'p':>7}")
    print("-" * 72)

    for model in ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]:
        # Base
        if model in base_dists:
            bd = base_dists[model]
            row = [f"{bd.get(e, 0):5d}" for e in error_types]
            print(f"  {model:<12} Base       " + " ".join(row))

        # FT
        if model in best_ft:
            cfg = _load_training_config(best_ft[model][1].get("checkpoint", ""))
            method = _method_short(cfg)
            l3_evals = [e for e in best_ft[model][0] if _level(e) == 3]
            fd = _error_distribution(l3_evals, 3)

            obs_base = [base_dists.get(model, {}).get(e, 0) for e in error_types]
            obs_ft   = [fd.get(e, 0) for e in error_types]
            stat     = _chi2_test(obs_base, obs_ft)

            row      = [f"{fd.get(e, 0):5d}" for e in error_types]
            chi2_str = f"{stat['chi2']:.2f}" if stat["chi2"] == stat["chi2"] else "---"
            p_str    = f"{stat['p']:.4f}"    if stat["p"] == stat["p"]    else "---"
            print(f"  {model:<12} FT({method:<8}) " + " ".join(row) +
                  f" {chi2_str:>8} {p_str:>7}")

            # Interpret shift
            e12_base = sum(base_dists.get(model, {}).get(e, 0) for e in ["E1", "E2"])
            e12_ft   = sum(fd.get(e, 0) for e in ["E1", "E2"])
            e45_base = sum(base_dists.get(model, {}).get(e, 0) for e in ["E4", "E5"])
            e45_ft   = sum(fd.get(e, 0) for e in ["E4", "E5"])
            n_base   = sum(base_dists.get(model, {}).values()) or 1
            n_ft     = sum(fd.values()) or 1
            print(f"    => E1+E2: {e12_base/n_base:.1%} -> {e12_ft/n_ft:.1%}  "
                  f"E4+E5: {e45_base/n_base:.1%} -> {e45_ft/n_ft:.1%}")
        else:
            print(f"  {model:<12} FT         (no results)")
        print()

    print("Conjecture 2 evaluation complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
