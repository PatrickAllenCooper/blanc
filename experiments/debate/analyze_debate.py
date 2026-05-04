"""
Debate results analysis -- paper Section 7.6.

Processes raw debate output (produced by run_debate.py) and computes:
  - Robustness analysis: debate vs. non-debate baseline
  - Grounding analysis: hallucination rate reduction
  - Creativity analysis: novel resolution distribution
  - Convergence analysis: MCTS iterations vs. statement quality

Usage:
    python experiments/debate/analyze_debate.py
    python experiments/debate/analyze_debate.py --results-file experiments/results/debate_results.json

Author: Anonymous Authors
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


def load_debate_results(path: Path) -> list:
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Core analyses
# ---------------------------------------------------------------------------

def robustness_by_kb(results: list) -> dict:
    """Mean proponent/opponent robustness grouped by KB."""
    groups = defaultdict(lambda: {"p_rob": [], "o_rob": []})
    for r in results:
        groups[r["kb"]]["p_rob"].append(r["proponent_robustness"])
        groups[r["kb"]]["o_rob"].append(r["opponent_robustness"])
    out = {}
    for kb, vals in groups.items():
        out[kb] = {
            "proponent_mean": _mean(vals["p_rob"]),
            "opponent_mean": _mean(vals["o_rob"]),
            "n": len(vals["p_rob"]),
        }
    return out


def grounding_by_kb(results: list) -> dict:
    """Mean proponent/opponent grounding grouped by KB."""
    groups = defaultdict(lambda: {"p_gnd": [], "o_gnd": []})
    for r in results:
        groups[r["kb"]]["p_gnd"].append(r["proponent_grounding"])
        groups[r["kb"]]["o_gnd"].append(r["opponent_grounding"])
    out = {}
    for kb, vals in groups.items():
        out[kb] = {
            "proponent_mean": _mean(vals["p_gnd"]),
            "opponent_mean": _mean(vals["o_gnd"]),
            "n": len(vals["p_gnd"]),
        }
    return out


def creativity_by_kb(results: list) -> dict:
    """Mean creativity scores grouped by KB."""
    groups = defaultdict(lambda: {"p_cre": [], "o_cre": []})
    for r in results:
        groups[r["kb"]]["p_cre"].append(r["proponent_creativity"])
        groups[r["kb"]]["o_cre"].append(r["opponent_creativity"])
    out = {}
    for kb, vals in groups.items():
        out[kb] = {
            "proponent_mean": _mean(vals["p_cre"]),
            "opponent_mean": _mean(vals["o_cre"]),
            "n": len(vals["p_cre"]),
        }
    return out


def winner_distribution(results: list) -> dict:
    """Tally of wins by role across all experiments."""
    dist = defaultdict(int)
    for r in results:
        dist[r.get("winner") or "tie"] += 1
    return dict(dist)


def convergence_summary(results: list) -> dict:
    """Aggregate convergence statistics."""
    times = [r.get("elapsed_seconds", 0) for r in results]
    theory_sizes = [r.get("theory_size", 0) for r in results]
    return {
        "total_experiments": len(results),
        "mean_elapsed_seconds": _mean(times),
        "mean_theory_size": _mean(theory_sizes),
    }


def defense_rate_summary(results: list) -> dict:
    """Aggregate defense rates."""
    p_rates = [r["proponent_defense_rate"] for r in results]
    o_rates = [r["opponent_defense_rate"] for r in results]
    return {
        "proponent_mean_defense_rate": _mean(p_rates),
        "opponent_mean_defense_rate": _mean(o_rates),
    }


# ---------------------------------------------------------------------------
# LaTeX output
# ---------------------------------------------------------------------------

def generate_table7(results: list) -> str:
    """Table 7: Debate robustness by KB."""
    rob = robustness_by_kb(results)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Debate robustness by knowledge base (Section~7.6).}",
        r"\label{tab:debate-robustness}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"KB & Proponent & Opponent & $n$ \\",
        r"\midrule",
    ]
    for kb in sorted(rob):
        v = rob[kb]
        lines.append(
            f"  {kb.capitalize()} & {v['proponent_mean']:.3f} "
            f"& {v['opponent_mean']:.3f} & {v['n']} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def generate_table8(results: list) -> str:
    """Table 8: Debate grounding and creativity by KB."""
    gnd = grounding_by_kb(results)
    cre = creativity_by_kb(results)
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Grounding and creativity by knowledge base (Section~7.6).}",
        r"\label{tab:debate-grounding-creativity}",
        r"\begin{tabular}{lcccc}",
        r"\toprule",
        r"KB & \multicolumn{2}{c}{Grounding} & \multicolumn{2}{c}{Creativity} \\",
        r"\cmidrule(lr){2-3} \cmidrule(lr){4-5}",
        r" & Prop. & Opp. & Prop. & Opp. \\",
        r"\midrule",
    ]
    for kb in sorted(gnd):
        g = gnd[kb]
        c = cre.get(kb, {"proponent_mean": 0, "opponent_mean": 0})
        lines.append(
            f"  {kb.capitalize()} & {g['proponent_mean']:.3f} "
            f"& {g['opponent_mean']:.3f} "
            f"& {c['proponent_mean']:.3f} "
            f"& {c['opponent_mean']:.3f} \\\\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


def generate_table9(results: list) -> str:
    """Table 9: Winner distribution."""
    dist = winner_distribution(results)
    total = sum(dist.values())
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Debate winner distribution (Section~7.6).}",
        r"\label{tab:debate-winners}",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Outcome & Count & Fraction \\",
        r"\midrule",
    ]
    for outcome in ["proponent", "opponent", "tie"]:
        cnt = dist.get(outcome, 0)
        frac = cnt / max(1, total)
        lines.append(f"  {outcome.capitalize()} & {cnt} & {frac:.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mean(vals):
    return sum(vals) / max(1, len(vals))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Analyse debate experiment results"
    )
    parser.add_argument(
        "--results-file",
        default=str(ROOT / "experiments" / "results" / "debate_results.json"),
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "paper" / "tables"),
    )
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Results file not found: {results_path}")
        print("Run experiments/debate/run_debate.py first.")
        sys.exit(1)

    results = load_debate_results(results_path)
    print(f"Loaded {len(results)} debate experiment records.\n")

    print("Robustness by KB:")
    for kb, v in robustness_by_kb(results).items():
        print(f"  {kb}: prop={v['proponent_mean']:.3f}  "
              f"opp={v['opponent_mean']:.3f}  n={v['n']}")

    print("\nGrounding by KB:")
    for kb, v in grounding_by_kb(results).items():
        print(f"  {kb}: prop={v['proponent_mean']:.3f}  "
              f"opp={v['opponent_mean']:.3f}")

    print("\nCreativity by KB:")
    for kb, v in creativity_by_kb(results).items():
        print(f"  {kb}: prop={v['proponent_mean']:.3f}  "
              f"opp={v['opponent_mean']:.3f}")

    print(f"\nWinner distribution: {winner_distribution(results)}")
    print(f"Convergence: {convergence_summary(results)}")
    print(f"Defense rates: {defense_rate_summary(results)}")

    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)

    t7 = generate_table7(results)
    t8 = generate_table8(results)
    t9 = generate_table9(results)

    (out_dir / "table7_debate_robustness.tex").write_text(t7)
    (out_dir / "table8_debate_grounding_creativity.tex").write_text(t8)
    (out_dir / "table9_debate_winners.tex").write_text(t9)
    print(f"\nLaTeX tables written to {out_dir}/table7-9_*.tex")


if __name__ == "__main__":
    main()
