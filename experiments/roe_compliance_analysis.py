"""
ROE compliance analysis: aggregate .jsonl experiment output into tables.

Reads one or more .jsonl files produced by scripts/run_roe_compliance_experiment.py
and produces:

    1. Compliance rate by enforcement mode (mean +/- 95% CI via bootstrap)
    2. Correct-abstain rate by mode (quiz mode only -- gold-answer accuracy)
    3. Hard-violation breakdown by defeater label
    4. Reprompt distribution under B2 (histogram text)
    5. Hypothesis test table (H_GATE, H_COST, H_REPROMPT)

All tables are printed to stdout and written to:
    experiments/results/roe_compliance_{timestamp}.md

Usage::

    python experiments/roe_compliance_analysis.py \\
        --input data/roe_compliance/mock_quiz_*.jsonl

    python experiments/roe_compliance_analysis.py \\
        --input data/roe_compliance/foundry-deepseek_quiz_20260420.jsonl \\
        --output experiments/results/

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_records(paths: list[Path]) -> list[dict]:
    records: list[dict] = []
    for path in paths:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _bootstrap_ci(values: list[float], n_boot: int = 2000, ci: float = 0.95) -> tuple[float, float]:
    """Return (lower, upper) bootstrap CI for the mean of values."""
    if not values:
        return (float("nan"), float("nan"))
    rng = random.Random(42)
    n = len(values)
    boot_means = sorted(
        sum(rng.choices(values, k=n)) / n for _ in range(n_boot)
    )
    lo_idx = int((1 - ci) / 2 * n_boot)
    hi_idx = int((1 + ci) / 2 * n_boot)
    return boot_means[lo_idx], boot_means[min(hi_idx, n_boot - 1)]


def _compliance_rate(verdicts: list[dict]) -> float:
    if not verdicts:
        return float("nan")
    return sum(1 for v in verdicts if v.get("compliant", True)) / len(verdicts)


# ---------------------------------------------------------------------------
# Per-mode aggregation
# ---------------------------------------------------------------------------

def aggregate_by_mode(records: list[dict]) -> dict[str, dict]:
    """
    Returns {mode: {compliance_rate, correct_abstain_rate, reprompts, ...}}
    """
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_mode[rec.get("mode", "unknown")].append(rec)

    result: dict[str, dict] = {}
    for mode, mode_recs in sorted(by_mode.items()):
        all_verdicts = [v for r in mode_recs for v in r.get("verdicts", [])]
        compliance_vals = [1.0 if v.get("compliant", True) else 0.0
                           for v in all_verdicts]
        compliance_mean = (sum(compliance_vals) / len(compliance_vals)
                           if compliance_vals else float("nan"))
        ci_lo, ci_hi = _bootstrap_ci(compliance_vals)

        # Correct-abstain (quiz mode only)
        gold_records = [r for r in mode_recs if r.get("gold")]
        abstain_vals = [1.0 if r["gold"].get("correct_abstain", True) else 0.0
                        for r in gold_records]
        abstain_mean = (sum(abstain_vals) / len(abstain_vals)
                        if abstain_vals else float("nan"))

        # Reprompt counts (B2 only)
        reprompts = [r.get("reprompts", 0) for r in mode_recs]
        mean_reprompts = sum(reprompts) / len(reprompts) if reprompts else 0.0

        # Defeater violation breakdown
        violation_labels: Counter = Counter()
        for v in all_verdicts:
            if not v.get("compliant", True) and v.get("violated_defeater"):
                violation_labels[v["violated_defeater"]] += 1

        result[mode] = {
            "n_records": len(mode_recs),
            "n_verdicts": len(all_verdicts),
            "compliance_mean": compliance_mean,
            "compliance_ci_lo": ci_lo,
            "compliance_ci_hi": ci_hi,
            "correct_abstain_mean": abstain_mean,
            "mean_reprompts": mean_reprompts,
            "total_reprompts": sum(reprompts),
            "violation_labels": dict(violation_labels.most_common(10)),
        }
    return result


# ---------------------------------------------------------------------------
# Reprompt histogram
# ---------------------------------------------------------------------------

def reprompt_histogram(records: list[dict]) -> str:
    b2_recs = [r for r in records if r.get("mode") == "B2"]
    if not b2_recs:
        return "(no B2 records)"
    counts: Counter = Counter(r.get("reprompts", 0) for r in b2_recs)
    max_count = max(counts.values())
    bar_width = 20
    lines = ["Reprompts per tick (B2 only):"]
    for k in sorted(counts):
        bar = "#" * round(counts[k] / max_count * bar_width)
        lines.append(f"  {k:2d} reprompts  {bar:<{bar_width}}  {counts[k]:4d}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hypothesis test table
# ---------------------------------------------------------------------------

def hypothesis_table(agg: dict[str, dict]) -> str:
    b0 = agg.get("B0", {})
    b1 = agg.get("B1", {})
    b2 = agg.get("B2", {})

    def _fmt(v: float, pct: bool = True) -> str:
        if math.isnan(v):
            return "--"
        return f"{v*100:.1f}%" if pct else f"{v:.2f}"

    lines = [
        "HYPOTHESIS TESTS",
        "-" * 60,
        "",
        "H_GATE: compliance(B2) > compliance(B1) ~ compliance(B0)",
        f"  B0 compliance: {_fmt(b0.get('compliance_mean', float('nan')))}",
        f"  B1 compliance: {_fmt(b1.get('compliance_mean', float('nan')))}",
        f"  B2 compliance: {_fmt(b2.get('compliance_mean', float('nan')))}",
        "  Verdict: " + (
            "SUPPORTED (B2 > B1 ~ B0)"
            if (b2.get("compliance_mean", 0) > b1.get("compliance_mean", 0) and
                abs(b1.get("compliance_mean", 0) - b0.get("compliance_mean", 0)) < 0.05)
            else "NOT yet supported -- more data needed"
        ),
        "",
        "H_REPROMPT: mean reprompts decrease over course of game",
        f"  B2 mean reprompts/tick: {b2.get('mean_reprompts', float('nan')):.2f}",
        "  (Check per-tick records to assess trend -- requires live mode)",
        "",
        "H_COST: mission_success(B2) <= mission_success(B0)",
        "  (Requires live SC2 mode with win/loss tracking)",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def build_markdown_report(
    records: list[dict],
    agg: dict[str, dict],
    input_paths: list[Path],
) -> str:
    providers = sorted({r.get("game_id", "").split("_")[0] for r in records if r.get("game_id")})
    modes_present = sorted(agg.keys())

    lines: list[str] = [
        "# ROE Compliance Experiment Results",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Provider(s)**: {', '.join(providers) or 'unknown'}  ",
        f"**Records**: {len(records)}  ",
        f"**Input files**: {', '.join(p.name for p in input_paths)}  ",
        "",
        "## Compliance by Enforcement Mode",
        "",
        "| Mode | N ticks | N verdicts | Compliance | 95% CI | Correct-Abstain | Mean Reprompts |",
        "|------|---------|------------|------------|--------|-----------------|----------------|",
    ]

    def _pct(v: float) -> str:
        return f"{v*100:.1f}%" if not math.isnan(v) else "--"

    for mode in modes_present:
        m = agg[mode]
        ci = (f"[{_pct(m['compliance_ci_lo'])}, {_pct(m['compliance_ci_hi'])}]"
              if not math.isnan(m["compliance_ci_lo"]) else "--")
        lines.append(
            f"| {mode} | {m['n_records']} | {m['n_verdicts']} "
            f"| {_pct(m['compliance_mean'])} | {ci} "
            f"| {_pct(m['correct_abstain_mean'])} "
            f"| {m['mean_reprompts']:.2f} |"
        )

    lines += [
        "",
        "## Violation Breakdown by Defeater",
        "",
        "| Mode | Defeater label | Count |",
        "|------|---------------|-------|",
    ]
    for mode in modes_present:
        for label, count in agg[mode]["violation_labels"].items():
            lines.append(f"| {mode} | {label} | {count} |")

    lines += [
        "",
        "## Reprompt Distribution (B2)",
        "",
        "```",
        reprompt_histogram(records),
        "```",
        "",
        "## Hypothesis Tests",
        "",
        "```",
        hypothesis_table(agg),
        "```",
        "",
        "## Scenario-Level Results (Quiz Mode)",
        "",
        "| Scenario | Mode | Violations | Correct-Abstain | Reprompts |",
        "|----------|------|------------|-----------------|-----------|",
    ]

    for rec in records:
        scenario = rec.get("scenario_id", "--")
        mode     = rec.get("mode", "--")
        n_viol   = sum(1 for v in rec.get("verdicts", []) if not v.get("compliant", True))
        correct  = rec.get("gold", {}).get("correct_abstain", "--")
        reprompts = rec.get("reprompts", 0)
        lines.append(f"| {scenario} | {mode} | {n_viol} | {correct} | {reprompts} |")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyse ROE compliance experiment .jsonl output"
    )
    parser.add_argument("--input", nargs="+", required=True,
                        help="One or more .jsonl output files from run_roe_compliance_experiment.py")
    parser.add_argument("--output", default=None,
                        help="Output directory for .md report (default: experiments/results/)")
    args = parser.parse_args()

    input_paths = [Path(p) for p in args.input]
    for p in input_paths:
        if not p.exists():
            print(f"ERROR: {p} not found")
            return 1

    records = load_records(input_paths)
    if not records:
        print("No records loaded.")
        return 1

    print(f"Loaded {len(records)} records from {len(input_paths)} file(s)")

    agg = aggregate_by_mode(records)

    # Print summary
    print()
    print("=" * 70)
    print("COMPLIANCE BY MODE")
    print("=" * 70)
    for mode, m in sorted(agg.items()):
        print(f"  {mode}  compliance={m['compliance_mean']*100:.1f}%  "
              f"correct_abstain={m['correct_abstain_mean']*100:.1f}%  "
              f"reprompts/tick={m['mean_reprompts']:.2f}")

    print()
    print(reprompt_histogram(records))
    print()
    print(hypothesis_table(agg))

    # Write markdown report
    out_dir = Path(args.output) if args.output else ROOT / "experiments" / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_path = out_dir / f"roe_compliance_{timestamp}.md"
    md_content = build_markdown_report(records, agg, input_paths)
    md_path.write_text(md_content)
    print(f"\nMarkdown report: {md_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
