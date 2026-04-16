"""Compute Level 3 formal metrics from existing evaluation results.

Reads the latest evaluation result files, extracts Level 3 responses,
aggregates conservativity, novelty, revision distance, and error
classification, and produces:
  - table3_level3_metrics.tex (conservativity, novelty, revision distance)
  - table4_error_taxonomy.tex (E1-E5 error classification)

Author: Patrick Cooper
"""
import json
import sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "experiments" / "results"
TABLES_DIR = ROOT / "paper" / "tables"

MODEL_DISPLAY = {
    "DeepSeek-R1": "DeepSeek-R1",
    "claude-sonnet-4-6": r"Claude~Sonnet~4.6",
    "gpt-5.2-chat": "GPT-5.2-chat",
    "Kimi-K2.5": "Kimi-K2.5",
}

LATEST_RUNS = {
    "DeepSeek-R1": "foundry_deepseek_20260228_174111/results_foundry-deepseek.json",
    "claude-sonnet-4-6": "foundry_claude_20260228_174111/results_foundry-claude.json",
    "gpt-5.2-chat": "foundry_gpt52_20260228_174111/results_foundry-gpt.json",
    "Kimi-K2.5": "foundry_kimi_20260228_174111/results_foundry-kimi.json",
}

ERROR_ORDER = ["correct", "E1_decoder_failure", "E2_derivation_failure",
               "E5_strength_shortfall"]
ERROR_SHORT = {"correct": "Correct", "E1_decoder_failure": "E1",
               "E2_derivation_failure": "E2", "E5_strength_shortfall": "E5"}


def load_l3_evaluations(result_path: str):
    """Load Level 3 evaluations from a full results JSON."""
    with open(RESULTS_DIR / result_path) as f:
        data = json.load(f)
    evs = data.get("evaluations", data if isinstance(data, list) else [])
    return [e for e in evs
            if e.get("level") == 3 or "l3" in str(e.get("instance_id", ""))]


def aggregate_l3(l3_evals):
    """Compute aggregate L3 metrics from a list of evaluation dicts."""
    n = len(l3_evals)
    if n == 0:
        return {}

    correct = sum(1 for e in l3_evals if e.get("metrics", {}).get("correct"))
    resolves = sum(1 for e in l3_evals
                   if e.get("metrics", {}).get("resolves_anomaly"))
    conserv = sum(1 for e in l3_evals
                  if e.get("metrics", {}).get("conservativity"))

    novs = [e["metrics"]["novelty"] for e in l3_evals
            if e.get("metrics", {}).get("novelty") is not None]
    mean_nov = sum(novs) / len(novs) if novs else 0.0

    revs = [e["metrics"]["revision_distance"] for e in l3_evals
            if e.get("metrics", {}).get("revision_distance") is not None]
    mean_rev = sum(revs) / len(revs) if revs else 0.0

    errors = Counter(
        e.get("metrics", {}).get("error_class", "unknown") for e in l3_evals
    )

    return {
        "n": n,
        "correct": correct,
        "accuracy": correct / n,
        "resolves": resolves,
        "resolves_pct": resolves / n,
        "conserv": conserv,
        "conserv_pct": conserv / n,
        "mean_nov": mean_nov,
        "mean_rev": mean_rev,
        "errors": dict(errors),
    }


def main():
    print("=" * 60)
    print("LEVEL 3 METRICS COMPUTATION")
    print("=" * 60)

    all_results = {}
    for model_key, result_path in LATEST_RUNS.items():
        print(f"\n--- {model_key} ---")
        l3 = load_l3_evaluations(result_path)
        agg = aggregate_l3(l3)
        all_results[model_key] = agg
        print(f"  n={agg['n']}, acc={agg['accuracy']*100:.1f}%, "
              f"resolves={agg['resolves_pct']*100:.1f}%, "
              f"conserv={agg['conserv_pct']*100:.1f}%, "
              f"nov={agg['mean_nov']:.3f}, d_rev={agg['mean_rev']:.2f}")
        print(f"  errors: {agg['errors']}")

    # --- Table 3: Level 3 formal metrics ---
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    t3 = []
    t3.append(r"% Table 3: Level 3 Formal Metrics by Model")
    t3.append(r"\begin{table}[t]")
    t3.append(r"  \centering")
    t3.append(r"  \caption{Level~3 (Defeater Abduction) formal metrics by model.")
    t3.append(r"           \emph{Acc}: binary accuracy;")
    t3.append(r"           \emph{Res}: fraction resolving the anomaly;")
    t3.append(r"           \emph{Cons}: conservative (no retracting existing rules);")
    t3.append(r"           $\overline{\mathrm{Nov}}$: mean novelty;")
    t3.append(r"           $\overline{d_\text{rev}}$: mean revision distance.}")
    t3.append(r"  \label{tab:level3_metrics}")
    t3.append(r"  \begin{tabular}{lrrrrr}")
    t3.append(r"    \toprule")
    t3.append(r"    Model & Acc (\%) & Res (\%) & Cons (\%) "
              r"& $\overline{\mathrm{Nov}}$ & $\overline{d_\text{rev}}$ \\")
    t3.append(r"    \midrule")

    model_order = ["DeepSeek-R1", "gpt-5.2-chat", "claude-sonnet-4-6", "Kimi-K2.5"]
    for mk in model_order:
        d = MODEL_DISPLAY[mk]
        r = all_results[mk]
        t3.append(
            f"    {d} & {r['accuracy']*100:.1f} & {r['resolves_pct']*100:.1f} "
            f"& {r['conserv_pct']*100:.1f} & {r['mean_nov']:.2f} "
            f"& {r['mean_rev']:.2f} \\\\"
        )

    t3.append(r"    \bottomrule")
    t3.append(r"  \end{tabular}")
    t3.append(r"\end{table}")

    out3 = TABLES_DIR / "table3_level3_metrics.tex"
    with open(out3, "w") as f:
        f.write("\n".join(t3) + "\n")
    print(f"\nWritten {out3}")

    # --- Table 4: Error taxonomy ---
    t4 = []
    t4.append(r"% Table 4: Error Taxonomy by Model (Level 3)")
    t4.append(r"\begin{table}[t]")
    t4.append(r"  \centering")
    t4.append(r"  \caption{Error taxonomy (\%) by model at Level~3.")
    t4.append(r"           \emph{Correct}: graded score~1.0;")
    t4.append(r"           \emph{E1}: decoder failure;")
    t4.append(r"           \emph{E2}: derivation failure;")
    t4.append(r"           \emph{E5}: strength shortfall.}")
    t4.append(r"  \label{tab:error_taxonomy}")
    t4.append(r"  \begin{tabular}{lrrrr}")
    t4.append(r"    \toprule")
    t4.append(r"    Model & Correct & E1 & E2 & E5 \\")
    t4.append(r"    \midrule")

    for mk in model_order:
        d = MODEL_DISPLAY[mk]
        r = all_results[mk]
        n = r["n"]
        errs = r["errors"]
        cols = []
        for ekey in ERROR_ORDER:
            cnt = errs.get(ekey, 0)
            cols.append(f"{100*cnt/n:.1f}")
        t4.append(f"    {d} & " + " & ".join(cols) + r" \\")

    t4.append(r"    \bottomrule")
    t4.append(r"  \end{tabular}")
    t4.append(r"\end{table}")

    out4 = TABLES_DIR / "table4_error_taxonomy.tex"
    with open(out4, "w") as f:
        f.write("\n".join(t4) + "\n")
    print(f"Written {out4}")

    # --- Save raw aggregates for other scripts ---
    summary = {mk: all_results[mk] for mk in model_order}
    out_json = RESULTS_DIR / "l3_metrics_summary.json"
    with open(out_json, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Written {out_json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
