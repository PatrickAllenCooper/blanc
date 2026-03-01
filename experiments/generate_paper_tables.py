"""
Paper Table Generator -- Section 5.

Produces LaTeX table code (and optionally Markdown) for the main results
tables in the paper.  Tables require real evaluation results; when results
are absent a placeholder is emitted for easy fill-in.

Tables generated:
  Table 1 -- Accuracy by model x level (primary results)
  Table 2 -- Accuracy by model x modality (rendering robustness)
  Table 3 -- Level 3 formal metrics by model (novelty + conservativity)
  Table 4 -- Error taxonomy by model (E1-E5)

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from analyze_results import load_results, accuracy_by, level3_metrics_summary
from error_taxonomy import build_error_taxonomy


# ---------------------------------------------------------------------------
# LaTeX helpers
# ---------------------------------------------------------------------------

def _pct(val: Optional[float]) -> str:
    if val is None:
        return "--"
    return f"{val * 100:.1f}"


def _bold(s: str) -> str:
    return f"\\textbf{{{s}}}"


def _best_model(rows: dict, metric: str = "accuracy") -> Optional[str]:
    """Return the model key with the highest value for `metric`."""
    best_key, best_val = None, -1.0
    for key, d in rows.items():
        val = d.get(metric)
        if val is not None and val > best_val:
            best_val, best_key = val, key
    return best_key


# ---------------------------------------------------------------------------
# Table 1: Accuracy by model x level
# ---------------------------------------------------------------------------

def table1_accuracy_by_model_level(evaluations: list[dict]) -> str:
    """Table 1: Model vs level accuracy (main results)."""
    by_ml = accuracy_by(evaluations, "model", "level")

    models = sorted({k[0] for k in by_ml})
    levels = ["2", "3"]

    lines = []
    lines.append("% Table 1: DeFAb Accuracy by Model and Level")
    lines.append(r"\begin{table}[t]")
    lines.append(r"  \centering")
    lines.append(r"  \caption{Accuracy (\%) on the DeFAb benchmark by model and task level.")
    lines.append(r"           Level~2 = rule abduction; Level~3 = defeater abduction.")
    lines.append(r"           Best result per column in \textbf{bold}.}")
    lines.append(r"  \label{tab:main_results}")
    lines.append(r"  \begin{tabular}{l" + "r" * len(levels) + "}")
    lines.append(r"    \toprule")
    lines.append("    Model & " + " & ".join(f"Level~{l}" for l in levels) + r" \\")
    lines.append(r"    \midrule")

    # Find best per level
    best: dict = {}
    for lv in levels:
        best_model, best_val = None, -1.0
        for model in models:
            val = by_ml.get((model, lv), {}).get("accuracy")
            if val is not None and val > best_val:
                best_val, best_model = val, model
        best[lv] = best_model

    for model in models:
        cells = []
        for lv in levels:
            d = by_ml.get((model, lv), {})
            val = _pct(d.get("accuracy"))
            if model == best.get(lv):
                val = _bold(val)
            cells.append(val)
        lines.append(f"    {model} & " + " & ".join(cells) + r" \\")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table 2: Accuracy by model x modality
# ---------------------------------------------------------------------------

def table2_accuracy_by_model_modality(evaluations: list[dict]) -> str:
    """Table 2: Model vs modality (rendering robustness)."""
    by_mm = accuracy_by(evaluations, "model", "modality")

    models = sorted({k[0] for k in by_mm})
    modalities = ["M1", "M2", "M3", "M4"]
    modalities = [m for m in modalities if any((model, m) in by_mm for model in models)]

    lines = []
    lines.append("% Table 2: Rendering Robustness (accuracy by model x modality)")
    lines.append(r"\begin{table}[t]")
    lines.append(r"  \centering")
    lines.append(r"  \caption{Rendering robustness: accuracy (\%) across prompt modalities.")
    lines.append(r"           M1 = narrative; M2 = semi-formal; M3 = structured; M4 = pure formal.}")
    lines.append(r"  \label{tab:rendering_robustness}")
    lines.append(r"  \begin{tabular}{l" + "r" * len(modalities) + "}")
    lines.append(r"    \toprule")
    lines.append("    Model & " + " & ".join(modalities) + r" \\")
    lines.append(r"    \midrule")

    for model in models:
        cells = [_pct(by_mm.get((model, m), {}).get("accuracy")) for m in modalities]
        lines.append(f"    {model} & " + " & ".join(cells) + r" \\")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table 3: Level 3 formal metrics by model
# ---------------------------------------------------------------------------

def table3_level3_metrics_by_model(evaluations: list[dict]) -> str:
    """Table 3: Novelty and conservativity by model (Level 3 only)."""
    models = sorted({ev.get("model", "unknown") for ev in evaluations})

    header_cols = ["Acc", "Resolves", "Conserv.", "Nov (mean)", r"$d_\text{rev}$"]

    lines = []
    lines.append("% Table 3: Level 3 Formal Metrics by Model")
    lines.append(r"\begin{table}[t]")
    lines.append(r"  \centering")
    lines.append(r"  \caption{Level~3 (Defeater Abduction) formal metrics by model.")
    lines.append(r"           \emph{Resolves}: fraction of responses that eliminate the anomaly.")
    lines.append(r"           \emph{Conserv.}: fraction that are also conservative (Definition~\ref{def:conservativity}).")
    lines.append(r"           \emph{Nov}: mean predicate novelty $\mathrm{Nov}(h, D^-)$.")
    lines.append(r"           $d_\text{rev}$: mean revision distance.}")
    lines.append(r"  \label{tab:level3_metrics}")
    lines.append(r"  \begin{tabular}{l" + "r" * len(header_cols) + "}")
    lines.append(r"    \toprule")
    lines.append("    Model & " + " & ".join(header_cols) + r" \\")
    lines.append(r"    \midrule")

    for model in models:
        l3_evs = [ev for ev in evaluations
                  if ev.get("model") == model and ("l3" in ev.get("instance_id", "").lower())]
        if not l3_evs:
            continue

        acc = accuracy_by(l3_evs, "model").get((model,), {}).get("accuracy")
        m_agg = level3_metrics_summary(l3_evs)
        resolves = m_agg.get("resolves_anomaly_rate")
        conserv = m_agg.get("is_conservative_rate")
        nov = m_agg.get("nov_mean")
        d_rev = m_agg.get("d_rev_mean")

        cells = [_pct(acc), _pct(resolves), _pct(conserv),
                 f"{nov:.3f}" if nov is not None else "--",
                 f"{d_rev:.2f}" if d_rev is not None else "--"]
        lines.append(f"    {model} & " + " & ".join(cells) + r" \\")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Table 4: Error taxonomy
# ---------------------------------------------------------------------------

def table4_error_taxonomy(evaluations: list[dict]) -> str:
    """Table 4: Error taxonomy (E1-E5) by model."""
    taxonomy = build_error_taxonomy(evaluations)
    models = sorted(taxonomy["by_model"])
    error_codes = ["E1_correct", "E2_non_conservative", "E3_no_resolve",
                   "E4_parse_failure", "E5_wrong_but_conservative"]
    short_labels = ["E1", "E2", "E3", "E4", "E5"]

    lines = []
    lines.append("% Table 4: Error Taxonomy by Model")
    lines.append(r"\begin{table}[t]")
    lines.append(r"  \centering")
    lines.append(r"  \caption{Error taxonomy (\%) by model.")
    lines.append(r"           E1~=~Correct; E2~=~Non-conservative; E3~=~Anomaly persists;")
    lines.append(r"           E4~=~Parse failure; E5~=~Wrong but conservative.}")
    lines.append(r"  \label{tab:error_taxonomy}")
    lines.append(r"  \begin{tabular}{l" + "r" * len(short_labels) + "}")
    lines.append(r"    \toprule")
    lines.append("    Model & " + " & ".join(short_labels) + r" \\")
    lines.append(r"    \midrule")

    for model in models:
        m_counts = taxonomy["by_model"][model]
        m_total = sum(m_counts.values())
        cells = [
            _pct(m_counts.get(code, 0) / m_total if m_total > 0 else None)
            for code in error_codes
        ]
        lines.append(f"    {model} & " + " & ".join(cells) + r" \\")

    lines.append(r"    \bottomrule")
    lines.append(r"  \end{tabular}")
    lines.append(r"\end{table}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Generate LaTeX tables for paper Section 5")
    parser.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--results-file", default=None,
                        help="Single results JSON (one model). Overrides --results-dir.")
    parser.add_argument("--results-files", nargs="+", default=None,
                        help="Multiple results JSON files (one per model). Produces combined "
                             "multi-model tables. Example: "
                             "--results-files results/foundry_gpt52_*/results_foundry-gpt.json "
                             "results/foundry_claude_*/results_foundry-claude.json")
    parser.add_argument("--canonical", action="store_true",
                        help="Auto-discover canonical result files: latest run per provider "
                             "in experiments/results/. Selects foundry_gpt52_*, "
                             "foundry_claude_*, foundry_deepseek_* (newest), "
                             "foundry_kimi_* (newest).")
    parser.add_argument("--output-dir", default=str(ROOT / "paper" / "tables"))
    parser.add_argument("--tables", nargs="+", default=["1", "2", "3", "4"],
                        help="Which tables to generate (1-4)")
    args = parser.parse_args()

    results_root = ROOT / "experiments" / "results"

    if args.canonical:
        # Auto-discover the newest result file per provider.
        import glob, re
        providers = {
            "gpt":      "foundry_gpt52_*",
            "claude":   "foundry_claude_*",
            "deepseek": "foundry_deepseek_*",
            "kimi":     "foundry_kimi_*",
        }
        paths = []
        for key, pattern in providers.items():
            # Pick the latest run directory (alphabetically last = newest timestamp)
            dirs = sorted(results_root.glob(pattern))
            # Skip pilot dirs
            dirs = [d for d in dirs if "pilot" not in d.name]
            if not dirs:
                print(f"  WARNING: no results found for pattern {pattern}")
                continue
            latest = dirs[-1]
            # Find the results JSON inside
            jsons = list(latest.glob("results_*.json"))
            if not jsons:
                print(f"  WARNING: no results_*.json in {latest}")
                continue
            paths.append(jsons[0])
            print(f"  {key}: {jsons[0].relative_to(ROOT)}")
        if not paths:
            print("No canonical results found.")
            return 1
        all_evaluations = []
        for p in paths:
            evs = load_results(p)
            all_evaluations.extend(evs)
            print(f"  Loaded {len(evs)} evaluations from {p.name}")
        evaluations = all_evaluations

    elif args.results_files:
        all_evaluations = []
        for fpath in args.results_files:
            p = Path(fpath)
            if not p.exists():
                print(f"  WARNING: {p} does not exist, skipping.")
                continue
            evs = load_results(p)
            all_evaluations.extend(evs)
            print(f"  Loaded {len(evs)} evaluations from {p.name}")
        evaluations = all_evaluations
        if not evaluations:
            print("No evaluations found in provided files.")
            return 1

    else:
        path = Path(args.results_file) if args.results_file else Path(args.results_dir)
        if not path.exists():
            print(f"Error: {path} does not exist. Run evaluation first.")
            return 1
        evaluations = load_results(path)
        if not evaluations:
            print("No evaluations found.")
            return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    generators = {
        "1": ("table1_main_results.tex", table1_accuracy_by_model_level),
        "2": ("table2_rendering_robustness.tex", table2_accuracy_by_model_modality),
        "3": ("table3_level3_metrics.tex", table3_level3_metrics_by_model),
        "4": ("table4_error_taxonomy.tex", table4_error_taxonomy),
    }

    for table_id in args.tables:
        if table_id not in generators:
            print(f"Unknown table id: {table_id}")
            continue
        fname, gen_fn = generators[table_id]
        tex = gen_fn(evaluations)
        out_path = output_dir / fname
        with open(out_path, "w") as f:
            f.write(tex + "\n")
        print(f"Table {table_id} written to {out_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
