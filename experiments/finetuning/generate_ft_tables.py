"""
Phase B6: Generate LaTeX Tables 4-6 for fine-tuning results (Section 6.7).

Tables produced:
  Table 4 (tab:ft_main)       -- Main fine-tuning results: L2/L3 accuracy by
                                  model and method (DPO-std, DPO-margin, VITL).
  Table 5 (tab:ft_curriculum) -- Curriculum comparison: joint vs sequential vs
                                  weighted vs l12_only for each model.
  Table 6 (tab:ft_error)      -- Error taxonomy shift: E1-E5 distribution
                                  before and after the best fine-tuning variant.

Usage:
  python experiments/finetuning/generate_ft_tables.py \\
      --results-dir      experiments/results/ \\
      --base-results-dir experiments/results/ \\
      --output-dir       experiments/results/finetuned/tables/

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
sys.path.insert(0, str(ROOT / "experiments"))


# ---------------------------------------------------------------------------
# Result loading
# ---------------------------------------------------------------------------

def _load_result_file(path: Path) -> tuple[list[dict], dict]:
    """Return (evaluations, metadata) from a result JSON."""
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    return data.get("evaluations", []), data.get("metadata", {})


def _is_finetuned(metadata: dict) -> bool:
    return "checkpoint" in metadata


def _load_all_results(results_dir: Path) -> list[tuple[list[dict], dict]]:
    """Load all result JSONs from a directory tree, returning (evals, meta) pairs."""
    results = []
    for path in sorted(results_dir.rglob("*.json")):
        try:
            evals, meta = _load_result_file(path)
            if evals:
                results.append((evals, meta))
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def _load_training_config(checkpoint: str) -> dict:
    cfg_path = Path(checkpoint).parent / "training_config.json"
    if not cfg_path.exists():
        cfg_path = Path(checkpoint) / "training_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _model_short(base_model: str) -> str:
    """Shorten HuggingFace model ID for table display."""
    if "72b" in base_model.lower() or "72B" in base_model:
        return "Qwen-72B"
    if "32b" in base_model.lower() or "32B" in base_model:
        return "Qwen-32B"
    if "deepseek" in base_model.lower() or "r1" in base_model.lower():
        return "DS-R1-70B"
    return base_model.split("/")[-1][:15]


def _method_short(cfg: dict) -> str:
    """Identify DPO/RLHF variant from training config."""
    if "mode" in cfg:  # RLHF
        return "VITL" if cfg["mode"] == "vitl" else "RLHF-RM"
    variant = cfg.get("dpo_variant", "standard")
    if variant == "standard":
        return "DPO-std"
    if variant in ("margin", "margin-strict"):
        return "DPO-margin"
    return variant


def _curriculum_short(cfg: dict) -> str:
    return cfg.get("curriculum", "joint")


def _level(ev: dict) -> int:
    iid = ev.get("instance_id", "")
    if "l3" in iid.lower() or "-l3-" in iid:
        return 3
    return ev.get("level", 2)


def _accuracy(evals: list[dict], level: int | None = None) -> tuple[float, int]:
    """Return (accuracy, n) for given level (or all if None)."""
    subset = [e for e in evals if level is None or _level(e) == level]
    if not subset:
        return float("nan"), 0
    correct = sum(1 for e in subset if e.get("metrics", {}).get("correct", False))
    return correct / len(subset), len(subset)


def _wilson_ci(correct: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score confidence interval."""
    if n == 0:
        return float("nan"), float("nan")
    p = correct / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * (p * (1 - p) / n + z**2 / (4 * n**2)) ** 0.5 / denom
    return max(0.0, centre - half), min(1.0, centre + half)


# ---------------------------------------------------------------------------
# Table builders
# ---------------------------------------------------------------------------

def build_table4(results: list[tuple[list[dict], dict]]) -> str:
    """
    Table 4: Main fine-tuning results (tab:ft_main).
    Rows: Model x Method; Columns: L2 acc, L3 acc.
    """
    rows: dict[tuple[str, str], dict] = {}

    for evals, meta in results:
        if not _is_finetuned(meta):
            continue
        cfg = _load_training_config(meta.get("checkpoint", ""))
        model  = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        method = _method_short(cfg)
        curriculum = _curriculum_short(cfg)

        # Table 4 uses joint and weighted curricula (best variant); skip l12_only ablation
        if curriculum == "l12_only":
            continue

        key = (model, method)
        acc2, n2 = _accuracy(evals, level=2)
        acc3, n3 = _accuracy(evals, level=3)
        c2 = sum(1 for e in evals if _level(e) == 2 and e.get("metrics", {}).get("correct", False))
        c3 = sum(1 for e in evals if _level(e) == 3 and e.get("metrics", {}).get("correct", False))

        if key not in rows or rows[key].get("acc3", -1) < acc3:
            rows[key] = {"acc2": acc2, "n2": n2, "c2": c2,
                         "acc3": acc3, "n3": n3, "c3": c3}

    if not rows:
        return "% Table 4: No fine-tuned results found.\n"

    lines = [
        r"\begin{table}[t]",
        r"  \centering",
        r"  \caption{Fine-tuning results on held-out test split. "
        r"Best L3 per (model, method) shown. "
        r"95\% Wilson confidence intervals in brackets.}",
        r"  \label{tab:ft_main}",
        r"  \begin{tabular}{llcc}",
        r"    \toprule",
        r"    Model & Method & L2 Accuracy & L3 Accuracy \\",
        r"    \midrule",
    ]

    model_order = ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]
    method_order = ["DPO-std", "DPO-margin", "VITL", "RLHF-RM"]
    prev_model = None

    for model in model_order:
        for method in method_order:
            key = (model, method)
            if key not in rows:
                continue
            r = rows[key]
            if prev_model and prev_model != model:
                lines.append(r"    \midrule")
            prev_model = model

            lo2, hi2 = _wilson_ci(r["c2"], r["n2"])
            lo3, hi3 = _wilson_ci(r["c3"], r["n3"])

            l2_str = f"{r['acc2']:.1%} [{lo2:.0%}--{hi2:.0%}]" if r["n2"] else "---"
            l3_str = f"{r['acc3']:.1%} [{lo3:.0%}--{hi3:.0%}]" if r["n3"] else "---"

            lines.append(f"    {model} & {method} & {l2_str} & {l3_str} \\\\")

    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def build_table5(results: list[tuple[list[dict], dict]]) -> str:
    """
    Table 5: Curriculum comparison (tab:ft_curriculum).
    Rows: Model x Curriculum; Columns: L2, L3 accuracy.
    Using margin-DPO variant only for clean comparison.
    """
    rows: dict[tuple[str, str], dict] = {}

    for evals, meta in results:
        if not _is_finetuned(meta):
            continue
        cfg = _load_training_config(meta.get("checkpoint", ""))
        method = _method_short(cfg)
        if method not in ("DPO-margin", "DPO-std"):
            continue
        model      = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        curriculum = _curriculum_short(cfg)
        key = (model, curriculum)

        acc2, n2 = _accuracy(evals, level=2)
        acc3, n3 = _accuracy(evals, level=3)
        c2 = sum(1 for e in evals if _level(e) == 2 and e.get("metrics", {}).get("correct", False))
        c3 = sum(1 for e in evals if _level(e) == 3 and e.get("metrics", {}).get("correct", False))

        if key not in rows or rows[key].get("acc3", -1) < acc3:
            rows[key] = {"acc2": acc2, "n2": n2, "c2": c2,
                         "acc3": acc3, "n3": n3, "c3": c3}

    if not rows:
        return "% Table 5: No curriculum comparison results found.\n"

    lines = [
        r"\begin{table}[t]",
        r"  \centering",
        r"  \caption{Curriculum comparison under margin-weighted DPO. "
        r"All rows use DPO with $\gamma=2.0$.}",
        r"  \label{tab:ft_curriculum}",
        r"  \begin{tabular}{llcc}",
        r"    \toprule",
        r"    Model & Curriculum & L2 Accuracy & L3 Accuracy \\",
        r"    \midrule",
    ]

    model_order = ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]
    curr_order  = ["joint", "sequential", "weighted", "l12_only"]
    prev_model  = None

    for model in model_order:
        for curr in curr_order:
            key = (model, curr)
            if key not in rows:
                continue
            r = rows[key]
            if prev_model and prev_model != model:
                lines.append(r"    \midrule")
            prev_model = model

            lo3, hi3 = _wilson_ci(r["c3"], r["n3"])
            l2_str = f"{r['acc2']:.1%}" if r["n2"] else "---"
            l3_str = f"{r['acc3']:.1%} [{lo3:.0%}--{hi3:.0%}]" if r["n3"] else "---"
            curr_disp = curr.replace("_", "\\_")
            lines.append(f"    {model} & {curr_disp} & {l2_str} & {l3_str} \\\\")

    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


def build_table6(
    ft_results:   list[tuple[list[dict], dict]],
    base_results: list[tuple[list[dict], dict]],
) -> str:
    """
    Table 6: Error taxonomy shift (tab:ft_error).
    Columns: E1-E5 counts, before and after best FT variant.
    """
    def _error_dist(evals: list[dict]) -> dict[str, int]:
        dist: dict[str, int] = defaultdict(int)
        for ev in evals:
            et = ev.get("metrics", {}).get("error_type", None)
            if et:
                dist[str(et)] += 1
        return dict(dist)

    # Best FT result per model (by L3 accuracy)
    best_ft: dict[str, tuple[list[dict], dict]] = {}
    for evals, meta in ft_results:
        if not _is_finetuned(meta):
            continue
        cfg   = _load_training_config(meta.get("checkpoint", ""))
        model = _model_short(meta.get("base_model", cfg.get("base_model", "?")))
        acc3, _ = _accuracy(evals, level=3)
        if model not in best_ft or acc3 > _accuracy(best_ft[model][0], level=3)[0]:
            best_ft[model] = (evals, meta)

    # Base results per model
    base_by_model: dict[str, list[dict]] = defaultdict(list)
    for evals, meta in base_results:
        if _is_finetuned(meta):
            continue
        for ev in evals:
            model_name = ev.get("model", "unknown")
            base_by_model[_model_short(model_name)].extend([ev])

    if not best_ft:
        return "% Table 6: No fine-tuned results found for error taxonomy.\n"

    error_types = ["E1", "E2", "E3", "E4", "E5"]
    lines = [
        r"\begin{table}[t]",
        r"  \centering",
        r"  \caption{Error taxonomy shift after fine-tuning (Level~3 only). "
        r"E1=decoder failure, E2=derivation failure, E3=nonconservativity, "
        r"E4=support miss, E5=novel (correct).}",
        r"  \label{tab:ft_error}",
        r"  \begin{tabular}{ll" + "c" * len(error_types) + "}",
        r"    \toprule",
        r"    Model & Phase & " + " & ".join(error_types) + r" \\",
        r"    \midrule",
    ]

    for model in ["Qwen-72B", "Qwen-32B", "DS-R1-70B"]:
        if model in base_by_model:
            l3_base = [e for e in base_by_model[model] if _level(e) == 3]
            dist_b  = _error_dist(l3_base)
            n_b     = len(l3_base) or 1
            row = [f"{dist_b.get(e, 0)}/{n_b}" for e in error_types]
            lines.append(f"    {model} & Base & " + " & ".join(row) + r" \\")

        if model in best_ft:
            l3_ft  = [e for e in best_ft[model][0] if _level(e) == 3]
            dist_f = _error_dist(l3_ft)
            n_f    = len(l3_ft) or 1
            row = [f"{dist_f.get(e, 0)}/{n_f}" for e in error_types]
            lines.append(f"          & Fine-tuned & " + " & ".join(row) + r" \\")
            lines.append(r"    \midrule")

    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate LaTeX Tables 4-6 for Section 6.7.")
    p.add_argument("--results-dir",      default="experiments/results",
                   help="Directory with fine-tuned evaluation results.")
    p.add_argument("--base-results-dir", default="experiments/results",
                   help="Directory with base model evaluation results.")
    p.add_argument("--output-dir",       default=None,
                   help="Write .tex snippets here (default: print to stdout).")
    return p.parse_args()


def main() -> int:
    args = parse_args()

    results_dir      = ROOT / args.results_dir
    base_results_dir = ROOT / args.base_results_dir

    print("Loading fine-tuned results...")
    all_results  = _load_all_results(results_dir)
    ft_results   = [(e, m) for e, m in all_results if _is_finetuned(m)]
    base_results = _load_all_results(base_results_dir)
    base_results = [(e, m) for e, m in base_results if not _is_finetuned(m)]

    print(f"  Found {len(ft_results)} fine-tuned result sets, "
          f"{len(base_results)} base result sets")

    if not ft_results:
        print("\nNo fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    table4 = build_table4(ft_results)
    table5 = build_table5(ft_results)
    table6 = build_table6(ft_results, base_results)

    if args.output_dir:
        out = ROOT / args.output_dir
        out.mkdir(parents=True, exist_ok=True)
        (out / "table4_ft_main.tex").write_text(table4)
        (out / "table5_ft_curriculum.tex").write_text(table5)
        (out / "table6_ft_error.tex").write_text(table6)
        print(f"\nTeX snippets written to {out}/")
    else:
        print("\n--- Table 4 (tab:ft_main) ---")
        print(table4)
        print("--- Table 5 (tab:ft_curriculum) ---")
        print(table5)
        print("--- Table 6 (tab:ft_error) ---")
        print(table6)

    return 0


if __name__ == "__main__":
    sys.exit(main())
