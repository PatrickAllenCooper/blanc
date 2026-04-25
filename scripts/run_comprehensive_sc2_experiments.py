"""
Comprehensive SC2 experiment orchestrator.

Runs all StarCraft-related experiments that can execute locally (no SC2 binary
required) across two tiers:

    Tier A  Free, deterministic (~10-15 min)
            Tests, KB certification, instance generation, mock-LLM quiz,
            synthetic self-play, analysis.

    Tier B  Foundry DeepSeek-R1 (~30-75 min, ~$5-15)
            Real-model ROE compliance quiz, RTS/Lux L3 evaluation,
            cross-environment transfer, LLM-vs-LLM synthetic self-play.

Each step runs as a subprocess.  The first non-zero exit code stops execution
and prints the last 40 lines of the failing step's log.

Usage::

    python scripts/run_comprehensive_sc2_experiments.py
    python scripts/run_comprehensive_sc2_experiments.py --tier A
    python scripts/run_comprehensive_sc2_experiments.py --budget-usd 10 --verbose
    python scripts/run_comprehensive_sc2_experiments.py --provider foundry-gpt

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Approximate cost per 1K tokens for Foundry models (USD).
# Used only for the budget-guard soft warning.
_COST_PER_1K_TOKENS = {
    "foundry-deepseek": 0.0014,
    "foundry-gpt":      0.010,
    "foundry-claude":   0.003,
    "foundry-kimi":     0.0015,
    "mock":             0.0,
}

# ── Step descriptor ────────────────────────────────────────────────────────────


@dataclass
class Step:
    name:     str
    cmd:      list[str]            # sys.executable + script + args
    tier:     str                  # "A" or "B"
    expected_output: str | None = None  # path glob for artifact existence check
    timeout:  int = 1800           # seconds (default 30 min)
    # Runtime state (filled in during execution)
    exit_code:  int  = field(default=-1, compare=False)
    elapsed_s:  float = field(default=0.0, compare=False)
    log_file:   str   = field(default="", compare=False)
    skipped:    bool  = field(default=False, compare=False)


# ── Step catalog ───────────────────────────────────────────────────────────────


def _build_steps(
    run_dir: Path,
    provider: str,
    tier: str,
) -> list[Step]:
    """Return the ordered list of experiment steps for the requested tier(s)."""

    artifacts = run_dir / "artifacts"
    py = sys.executable

    steps: list[Step] = []

    # ─────────────────────────────────────────────────────────────────────────
    # Tier A: free, deterministic
    # ─────────────────────────────────────────────────────────────────────────

    if tier in ("A", "AB"):

        # A1 -- health tests
        steps.append(Step(
            name="A1_health_tests",
            tier="A",
            cmd=[
                py, "-m", "pytest",
                "tests/sc2live/",
                "tests/integration/test_rts_engagement_kb.py",
                "tests/integration/test_lux_engagement_kb.py",
                "tests/integration/test_sc2live_engagement_kb.py",
                "tests/integration/test_roe_compliance_quiz.py",
                "-q", "--no-cov", "--tb=short",
            ],
            timeout=600,
        ))

        # A2 -- certify RTS KB
        steps.append(Step(
            name="A2_cert_rts",
            tier="A",
            cmd=[
                py, "scripts/certify_rts_kb.py",
                "--output", str(artifacts / "cert_rts.json"),
                "--max-per-partition", "2",
            ],
            expected_output=str(artifacts / "cert_rts.json"),
            timeout=600,
        ))

        # A3 -- generate RTS L3 instances (uses the 6 hand-crafted seeds)
        steps.append(Step(
            name="A3_gen_rts_l3",
            tier="A",
            cmd=[
                py, "scripts/generate_rts_instances.py",
                "--level", "3",
                "--output", str(artifacts / "rts_l3.json"),
            ],
            expected_output=str(artifacts / "rts_l3.json"),
            timeout=300,
        ))

        # A4 -- generate Lux L1/L2 instances (writes to instances/ for B4/B5 as well)
        steps.append(Step(
            name="A4_gen_lux_l12",
            tier="A",
            cmd=[
                py, "scripts/generate_lux_instances.py",
                "--level", "0",
                "--max-instances", "3",
                "--output", str(ROOT / "instances" / "lux_engagement_instances.json"),
            ],
            expected_output=str(ROOT / "instances" / "lux_engagement_instances.json"),
            timeout=300,
        ))

        # A5 -- ROE compliance quiz with mock LLM (all three modes)
        steps.append(Step(
            name="A5_quiz_mock",
            tier="A",
            cmd=[
                py, "scripts/run_roe_compliance_experiment.py",
                "--mode", "quiz",
                "--provider", "mock",
                "--enforcement", "all",
                "--output", str(artifacts / "quiz_mock"),
            ],
            expected_output=str(artifacts / "quiz_mock" / "*.jsonl"),
            timeout=120,
        ))

        # A6 -- synthetic self-play (no SC2 binary)
        steps.append(Step(
            name="A6_selfplay_mock",
            tier="A",
            cmd=[
                py, "scripts/run_sc2_selfplay.py",
                "--games", "2",
                "--provider", "mock",
                "--no-sc2",
                "--output", str(artifacts / "selfplay_mock.jsonl"),
            ],
            expected_output=str(artifacts / "selfplay_mock.jsonl"),
            timeout=120,
        ))

        # A7 -- analyze mock quiz output
        steps.append(Step(
            name="A7_analyze_mock",
            tier="A",
            cmd=[
                py, "experiments/roe_compliance_analysis.py",
                "--input", str(artifacts / "quiz_mock" / "mock_quiz_*.jsonl"),
                "--output", str(artifacts),
            ],
            timeout=60,
        ))

    # ─────────────────────────────────────────────────────────────────────────
    # Tier B: Foundry model
    # ─────────────────────────────────────────────────────────────────────────

    if tier in ("B", "AB"):

        # B1 -- ROE compliance quiz with real model (all three modes)
        steps.append(Step(
            name="B1_quiz_realmodel",
            tier="B",
            cmd=[
                py, "scripts/run_roe_compliance_experiment.py",
                "--mode", "quiz",
                "--provider", provider,
                "--enforcement", "all",
                "--output", str(artifacts / f"quiz_{provider}"),
            ],
            expected_output=str(artifacts / f"quiz_{provider}" / "*.jsonl"),
            timeout=1800,
        ))

        # B2 -- RTS evaluation with real model (all available instances = L3 seeds)
        steps.append(Step(
            name="B2_eval_rts_l3_direct",
            tier="B",
            cmd=[
                py, "scripts/run_rts_evaluation.py",
                "--provider", provider,
                "--modalities", "M4",
                "--strategies", "direct",
                "--include-level3",
                "--level3-limit", "6",
                "--instance-limit", "0",
                "--instances-file", "instances/rts_engagement_instances.json",
                "--results-dir", str(artifacts),
            ],
            timeout=1800,
        ))

        # B3 -- RTS evaluation CoT strategy (same L3 seeds, CoT prompting)
        steps.append(Step(
            name="B3_eval_rts_l3_cot",
            tier="B",
            cmd=[
                py, "scripts/run_rts_evaluation.py",
                "--provider", provider,
                "--modalities", "M4",
                "--strategies", "cot",
                "--include-level3",
                "--level3-limit", "6",
                "--instance-limit", "0",
                "--instances-file", "instances/rts_engagement_instances.json",
                "--results-dir", str(artifacts),
            ],
            timeout=1800,
        ))

        # B4 -- cross-environment transfer evaluation (Lux + knowledge-base domains)
        steps.append(Step(
            name="B4_cross_env_transfer",
            tier="B",
            cmd=[
                py, "experiments/cross_env_transfer.py",
                "--provider", provider,
                "--modalities", "M4",
                "--strategies", "direct",
                "--instance-limit", "2",
                "--output-dir", str(artifacts),
            ],
            timeout=2400,
        ))

        # B6 -- LLM-vs-LLM synthetic self-play
        steps.append(Step(
            name="B6_selfplay_llm",
            tier="B",
            cmd=[
                py, "scripts/run_sc2_selfplay.py",
                "--games", "2",
                "--provider", provider,
                "--provider-b", "foundry-gpt" if provider != "foundry-gpt"
                                else "foundry-deepseek",
                "--no-sc2",
                "--output", str(artifacts / f"selfplay_{provider}_vs_gpt.jsonl"),
            ],
            expected_output=str(artifacts / f"selfplay_{provider}_vs_gpt.jsonl"),
            timeout=600,
        ))

        # B7 -- analyze real-model quiz output
        steps.append(Step(
            name="B7_analyze_realmodel",
            tier="B",
            cmd=[
                py, "experiments/roe_compliance_analysis.py",
                "--input",
                str(artifacts / f"quiz_{provider}" / f"{provider}_quiz_*.jsonl"),
                "--output", str(artifacts),
            ],
            timeout=60,
        ))

    return steps


# ── Runner ─────────────────────────────────────────────────────────────────────


def _glob_expand(cmd: list[str]) -> list[str]:
    """
    Expand any glob pattern in the command argument list.
    Used for --input arguments that may contain wildcards.
    """
    expanded = []
    for arg in cmd:
        if "*" in arg or "?" in arg:
            matches = sorted(glob.glob(arg))
            if matches:
                expanded.extend(matches)
            else:
                expanded.append(arg)  # keep as-is; let the script handle the error
        else:
            expanded.append(arg)
    return expanded


def run_step(step: Step, logs_dir: Path, env: dict, verbose: bool) -> bool:
    """
    Execute one step.  Returns True on success, False on failure.
    Logs stdout+stderr to logs_dir/<step.name>.log.
    """
    log_path = logs_dir / f"{step.name}.log"
    step.log_file = str(log_path)

    cmd = _glob_expand(step.cmd)
    print(f"\n[{step.tier}] {step.name}")
    print(f"  cmd: {' '.join(str(c) for c in cmd)}")

    t0 = time.time()
    try:
        with open(log_path, "w", encoding="utf-8", errors="replace") as log_f:
            result = subprocess.run(
                cmd,
                cwd=str(ROOT),
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                timeout=step.timeout,
                text=True,
            )
        step.exit_code  = result.returncode
        step.elapsed_s  = time.time() - t0
    except subprocess.TimeoutExpired:
        step.exit_code  = -2
        step.elapsed_s  = time.time() - t0
        _append_log(log_path, f"\n[ORCHESTRATOR] TIMEOUT after {step.timeout}s")
    except Exception as exc:
        step.exit_code  = -3
        step.elapsed_s  = time.time() - t0
        _append_log(log_path, f"\n[ORCHESTRATOR] Exception: {exc}")

    elapsed_str = f"{step.elapsed_s:.1f}s"

    if step.exit_code == 0:
        print(f"  PASS  ({elapsed_str})")
        if verbose:
            _print_tail(log_path, n=10)
        return True

    # ── Failure ───────────────────────────────────────────────────────────────
    timeout_msg = " (TIMEOUT)" if step.exit_code == -2 else ""
    print(f"  FAIL  exit={step.exit_code}{timeout_msg}  ({elapsed_str})")
    print(f"  Log   : {log_path}")
    print(f"  Last 40 lines of log:")
    print("  " + "-" * 60)
    _print_tail(log_path, n=40, indent="  ")
    return False


def _append_log(log_path: Path, text: str) -> None:
    with open(log_path, "a", encoding="utf-8", errors="replace") as f:
        f.write(text + "\n")


def _print_tail(log_path: Path, n: int = 40, indent: str = "") -> None:
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        for line in lines[-n:]:
            print(indent + line, end="")
        if not lines[-1].endswith("\n"):
            print()
    except FileNotFoundError:
        print(f"{indent}(log file not found)")


# ── Budget guard ───────────────────────────────────────────────────────────────


def _estimate_cost(steps_done: list[Step], provider: str) -> float:
    """
    Very rough cost estimate: assume 1500 tokens per LLM call,
    10 calls per Tier-B step.
    """
    cost_per_1k = _COST_PER_1K_TOKENS.get(provider, 0.01)
    b_steps = sum(1 for s in steps_done if s.tier == "B" and s.exit_code == 0)
    estimated_tokens = b_steps * 10 * 1500
    return estimated_tokens / 1000 * cost_per_1k


# ── Summary generation ─────────────────────────────────────────────────────────


def _extract_compliance_metrics(artifacts_dir: Path, provider: str) -> dict:
    """Extract key compliance metrics from quiz output files."""
    metrics: dict = {}
    for quiz_dir_pattern in [
        str(artifacts_dir / "quiz_mock"),
        str(artifacts_dir / f"quiz_{provider}"),
    ]:
        for jsonl_file in sorted(glob.glob(quiz_dir_pattern + "/*.jsonl")):
            records = []
            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
            if not records:
                continue
            src = "mock" if "mock" in jsonl_file else provider
            by_mode: dict[str, dict] = {}
            for rec in records:
                mode = rec.get("mode", "?")
                if mode not in by_mode:
                    by_mode[mode] = {"total": 0, "correct": 0, "reprompts": 0}
                by_mode[mode]["total"] += 1
                if rec.get("gold", {}).get("correct_abstain", True):
                    by_mode[mode]["correct"] += 1
                by_mode[mode]["reprompts"] += rec.get("reprompts", 0)
            metrics[src] = by_mode
    return metrics


def _extract_eval_metrics(artifacts_dir: Path, provider: str) -> list[dict]:
    """Extract model evaluation metrics from RTS/cross-env results JSONs."""
    rows: list[dict] = []
    for json_file in sorted(list(artifacts_dir.glob("rts_*.json")) + list(artifacts_dir.glob("cross_env_*.json"))):
        try:
            with open(json_file) as f:
                data = json.load(f)
            summary = data.get("summary", data.get("results_summary", {}))
            if summary:
                # Support both old key names and new ones
                l2 = summary.get("level2_accuracy", summary.get("l2_accuracy"))
                l3 = summary.get("level3_accuracy", summary.get("accuracy"))
                n  = summary.get("total_instances",
                                  data.get("instance_counts", {}).get("3",
                                  summary.get("total_evaluations")))
                rows.append({
                    "source": json_file.name,
                    "l2_acc": f"{l2*100:.1f}%" if isinstance(l2, float) else (l2 or "--"),
                    "l3_acc": f"{l3*100:.1f}%" if isinstance(l3, float) else (l3 or "--"),
                    "n": n or "--",
                })
        except Exception:
            continue
    return rows


def write_summary(
    run_dir: Path,
    steps: list[Step],
    provider: str,
    git_sha: str,
    start_time: str,
) -> Path:
    """Write the comprehensive_summary.md file and return its path."""
    summary_dir = run_dir / "summary"
    summary_dir.mkdir(parents=True, exist_ok=True)
    out_path = summary_dir / "comprehensive_summary.md"
    artifacts = run_dir / "artifacts"

    n_pass = sum(1 for s in steps if s.exit_code == 0 and not s.skipped)
    n_fail = sum(1 for s in steps if s.exit_code != 0 and not s.skipped)
    n_skip = sum(1 for s in steps if s.skipped)

    compliance_metrics = _extract_compliance_metrics(artifacts, provider)
    eval_metrics       = _extract_eval_metrics(artifacts, provider)

    lines: list[str] = [
        "# Comprehensive SC2 Experiment Run Summary",
        "",
        f"**Date**: {start_time}  ",
        f"**Git commit**: `{git_sha}`  ",
        f"**Foundry model**: `{provider}`  ",
        f"**Run directory**: `{run_dir}`  ",
        "",
        f"**Result**: {n_pass} passed, {n_fail} failed, {n_skip} skipped",
        "",
        "---",
        "",
        "## Step Status",
        "",
        "| Step | Tier | Status | Elapsed |",
        "|------|------|--------|---------|",
    ]
    for step in steps:
        if step.skipped:
            status = "SKIP"
        elif step.exit_code == 0:
            status = "PASS"
        elif step.exit_code == -2:
            status = "TIMEOUT"
        else:
            status = f"FAIL({step.exit_code})"
        elapsed = f"{step.elapsed_s:.1f}s" if step.elapsed_s > 0 else "--"
        lines.append(f"| `{step.name}` | {step.tier} | {status} | {elapsed} |")

    lines += [
        "",
        "---",
        "",
        "## ROE Compliance Results",
        "",
    ]

    for src, by_mode in compliance_metrics.items():
        lines.append(f"### Provider: `{src}`")
        lines += [
            "",
            "| Mode | Scenarios | Correct Abstain | Reprompts |",
            "|------|-----------|-----------------|-----------|",
        ]
        for mode in sorted(by_mode):
            m = by_mode[mode]
            total    = m["total"]
            correct  = m["correct"]
            reprompts = m["reprompts"]
            lines.append(f"| {mode} | {total} | {correct}/{total} | {reprompts} |")
        lines.append("")

    if not compliance_metrics:
        lines += ["*(No compliance quiz output found)*", ""]

    lines += [
        "---",
        "",
        "## Evaluation Results (RTS / Lux / Cross-Env)",
        "",
        "| Source file | L2 Accuracy | L3 Accuracy | N |",
        "|-------------|-------------|-------------|---|",
    ]
    for row in eval_metrics:
        lines.append(
            f"| {row['source']} | {row['l2_acc']} | {row['l3_acc']} | {row['n']} |"
        )
    if not eval_metrics:
        lines += ["*(No evaluation results found)*", ""]

    lines += [
        "",
        "---",
        "",
        "## Log Files",
        "",
    ]
    for step in steps:
        if step.log_file:
            lines.append(f"- `{step.name}`: [{step.log_file}]({step.log_file})")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


# ── Main ───────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run comprehensive SC2 experiments (Tier A and/or B)"
    )
    parser.add_argument(
        "--tier", default="AB", choices=["A", "B", "AB"],
        help="Which tier(s) to run (default: AB)",
    )
    parser.add_argument(
        "--provider", default="foundry-deepseek",
        choices=list(_COST_PER_1K_TOKENS.keys()),
        help="Foundry model provider for Tier B (default: foundry-deepseek)",
    )
    parser.add_argument(
        "--budget-usd", type=float, default=20.0,
        help="Soft USD budget cap for Tier B (default: 20)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print last 10 lines of each passing step's log",
    )
    args = parser.parse_args()

    # ── Set up run directory ──────────────────────────────────────────────────
    timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir    = ROOT / "data" / f"comprehensive_sc2_run_{timestamp}"
    logs_dir   = run_dir / "logs"
    artifacts  = run_dir / "artifacts"
    for d in (run_dir, logs_dir, artifacts):
        d.mkdir(parents=True, exist_ok=True)

    # Per-step output subdirs
    (artifacts / "quiz_mock").mkdir(parents=True, exist_ok=True)
    (artifacts / f"quiz_{args.provider}").mkdir(parents=True, exist_ok=True)

    # ── Git SHA ───────────────────────────────────────────────────────────────
    try:
        git_sha = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT), text=True,
        ).strip()
    except Exception:
        git_sha = "unknown"

    # ── Environment ───────────────────────────────────────────────────────────
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT / "src"),
        str(ROOT / "experiments"),
        str(ROOT),
        str(ROOT / "scripts"),
        env.get("PYTHONPATH", ""),
    ])
    # Load .env if dotenv is available (force-set so subprocesses get the keys)
    try:
        from dotenv import dotenv_values
        for k, v in dotenv_values(ROOT / ".env").items():
            if v:   # only propagate non-empty values from .env
                env[k] = v
    except ImportError:
        pass

    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("=" * 70)
    print("COMPREHENSIVE SC2 EXPERIMENT RUN")
    print("=" * 70)
    print(f"Tier     : {args.tier}")
    print(f"Provider : {args.provider}")
    print(f"Budget   : ${args.budget_usd:.2f} (soft cap)")
    print(f"Git SHA  : {git_sha}")
    print(f"Run dir  : {run_dir}")
    print(f"Start    : {start_time}")
    print("=" * 70)

    # ── Build and run steps ───────────────────────────────────────────────────
    steps = _build_steps(run_dir, args.provider, args.tier)
    print(f"\n{len(steps)} steps defined.\n")

    for step in steps:
        if step.tier == "B":
            est_cost = _estimate_cost(
                [s for s in steps if s.exit_code == 0], args.provider
            )
            if est_cost > args.budget_usd:
                print(
                    f"\nBUDGET CAP: estimated spend ~${est_cost:.2f} > "
                    f"${args.budget_usd:.2f}.  Stopping before {step.name}."
                )
                step.skipped = True
                continue

        ok = run_step(step, logs_dir, env, args.verbose)
        if not ok:
            # Write partial summary and exit
            summary_path = write_summary(
                run_dir, steps, args.provider, git_sha, start_time
            )
            print(f"\nRun FAILED at step {step.name}.")
            print(f"Partial summary: {summary_path}")
            return 1

    # ── Final summary ─────────────────────────────────────────────────────────
    summary_path = write_summary(
        run_dir, steps, args.provider, git_sha, start_time
    )
    est_cost = _estimate_cost(steps, args.provider)

    print("\n" + "=" * 70)
    print("ALL STEPS PASSED")
    print("=" * 70)
    n_pass = sum(1 for s in steps if s.exit_code == 0)
    n_skip = sum(1 for s in steps if s.skipped)
    print(f"  Steps passed : {n_pass}")
    print(f"  Steps skipped: {n_skip}")
    print(f"  Est. cost    : ~${est_cost:.2f}")
    print(f"  Run dir      : {run_dir}")
    print(f"  Summary      : {summary_path}")
    print()
    print("To view the full summary:")
    print(f"  type {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
