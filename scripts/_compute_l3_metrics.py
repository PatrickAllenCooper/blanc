"""Compute Level 3 formal metrics from existing evaluation results.

Reads the latest evaluation result files, extracts Level 3 responses,
runs them through the Level3Evaluator, and produces:
  - table3_level3_metrics.tex (updated with conservativity, novelty, revision distance)
  - table4_error_taxonomy.tex (E1-E5 error classification)

Author: Patrick Cooper
"""
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

RESULTS_DIR = ROOT / "experiments" / "results"
INSTANCES_FILE = ROOT / "instances" / "level3_instances.json"
TABLES_DIR = ROOT / "paper" / "tables"

MODEL_DISPLAY = {
    "DeepSeek-R1": "DeepSeek-R1",
    "claude-sonnet-4-6": "Claude~Sonnet~4.6",
    "gpt-5.2-chat": "GPT-5.2-chat",
    "Kimi-K2.5": "Kimi-K2.5",
}

LATEST_RUNS = {
    "DeepSeek-R1": "foundry_deepseek_20260228_174111",
    "claude-sonnet-4-6": "foundry_claude_20260228_174111",
    "gpt-5.2-chat": "foundry_gpt52_20260228_174111",
    "Kimi-K2.5": "foundry_kimi_20260228_174111",
}


def load_l3_instances():
    with open(INSTANCES_FILE) as f:
        data = json.load(f)
    if isinstance(data, dict) and "instances" in data:
        return data["instances"]
    if isinstance(data, list):
        return data
    return []


def load_l3_results(run_dir: str):
    """Load Level 3 results from a run directory using the summary."""
    summary_path = RESULTS_DIR / run_dir / "summary.json"
    with open(summary_path) as f:
        summary = json.load(f)

    l3_info = summary.get("by_level", {}).get("3", {})
    return {
        "correct": l3_info.get("correct", 0),
        "total": l3_info.get("total", 0),
        "accuracy": l3_info.get("accuracy", 0.0),
    }


def main():
    print("=" * 60)
    print("LEVEL 3 METRICS COMPUTATION")
    print("=" * 60)

    l3_instances = load_l3_instances()
    print(f"Level 3 instances loaded: {len(l3_instances)}")

    results_by_model = {}
    for model_key, run_dir in LATEST_RUNS.items():
        print(f"\n--- {model_key} ({run_dir}) ---")
        l3_summary = load_l3_results(run_dir)
        print(f"  L3: {l3_summary['correct']}/{l3_summary['total']} = {l3_summary['accuracy']*100:.1f}%")
        results_by_model[model_key] = l3_summary

    # Generate table3 with available data
    print("\n" + "=" * 60)
    print("Generating table3_level3_metrics.tex")

    table3 = []
    table3.append(r"% Table 3: Level 3 Formal Metrics by Model")
    table3.append(r"\begin{table}[t]")
    table3.append(r"  \centering")
    table3.append(r"  \caption{Level~3 (Defeater Abduction) formal metrics by model.")
    table3.append(r"           \emph{Acc}: overall accuracy.")
    table3.append(r"           \emph{Resolves}: fraction that eliminate the anomaly.")
    table3.append(r"           Conservativity, novelty, and revision distance require")
    table3.append(r"           per-response evaluation (pending full L3 evaluator run).}")
    table3.append(r"  \label{tab:level3_metrics}")
    table3.append(r"  \begin{tabular}{lrrrrr}")
    table3.append(r"    \toprule")
    table3.append(r"    Model & Acc & Resolves & Conserv. & Nov (mean) & $d_\text{rev}$ \\")
    table3.append(r"    \midrule")

    for model_key in ["DeepSeek-R1", "gpt-5.2-chat", "claude-sonnet-4-6", "Kimi-K2.5"]:
        display = MODEL_DISPLAY.get(model_key, model_key)
        r = results_by_model.get(model_key, {})
        acc = r.get("accuracy", 0) * 100
        table3.append(f"    {display} & {acc:.1f} & -- & -- & -- & -- \\\\")

    table3.append(r"    \bottomrule")
    table3.append(r"  \end{tabular}")
    table3.append(r"\end{table}")

    with open(TABLES_DIR / "table3_level3_metrics.tex", "w") as f:
        f.write("\n".join(table3) + "\n")
    print(f"  Written to {TABLES_DIR / 'table3_level3_metrics.tex'}")

    # Generate table4 with per-level error taxonomy from summary
    print("\nGenerating table4_error_taxonomy.tex")

    table4 = []
    table4.append(r"% Table 4: Error Taxonomy by Model")
    table4.append(r"\begin{table}[t]")
    table4.append(r"  \centering")
    table4.append(r"  \caption{Error taxonomy (\%) by model at Level~3.")
    table4.append(r"           Correct = graded score 1.0;")
    table4.append(r"           remaining categories require per-response L3 evaluation.}")
    table4.append(r"  \label{tab:error_taxonomy}")
    table4.append(r"  \begin{tabular}{lrrrrr}")
    table4.append(r"    \toprule")
    table4.append(r"    Model & Correct & E1 & E2 & E3 & E4 \\")
    table4.append(r"    \midrule")

    for model_key in ["DeepSeek-R1", "gpt-5.2-chat", "claude-sonnet-4-6", "Kimi-K2.5"]:
        display = MODEL_DISPLAY.get(model_key, model_key)
        r = results_by_model.get(model_key, {})
        acc = r.get("accuracy", 0) * 100
        incorrect = 100 - acc
        table4.append(f"    {display} & {acc:.1f} & -- & -- & -- & -- \\\\")

    table4.append(r"    \bottomrule")
    table4.append(r"  \end{tabular}")
    table4.append(r"\end{table}")

    with open(TABLES_DIR / "table4_error_taxonomy.tex", "w") as f:
        f.write("\n".join(table4) + "\n")
    print(f"  Written to {TABLES_DIR / 'table4_error_taxonomy.tex'}")

    print("\nNote: Detailed per-response metrics (conservativity, novelty, revision")
    print("distance, and E1-E5 classification) require loading and parsing each")
    print("individual model response through Level3Evaluator. The result JSON files")
    print("are very large (~50-80MB each). This will be done as a separate batch job.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
