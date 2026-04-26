"""
Full ROE experiment panel: runs all locally feasible ROE experiments
across all four Foundry models.

Experiments:
    1. ROE compliance quiz (B0/B1/B2) for each model
    2. RTS L3 evaluation direct + CoT for each model
    3. sc2live instances evaluated with foundry-nano
    4. DPO preference data (16 samples, foundry-nano)
    5. ROE benchmark (SC2 + Lux) with foundry-nano
    6. Cross-provider compliance comparison summary

Models:
    foundry-nano (already done -- loads from cache if available)
    foundry-deepseek (already done)
    foundry-gpt
    foundry-claude
    foundry-kimi

Usage::

    python scripts/run_full_roe_panel.py
    python scripts/run_full_roe_panel.py --skip-done --budget-usd 30
    python scripts/run_full_roe_panel.py --models foundry-gpt foundry-claude foundry-kimi

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

# All four panel models in paper order
ALL_PANEL_MODELS = [
    "foundry-nano",
    "foundry-deepseek",
    "foundry-gpt",
    "foundry-claude",
    "foundry-kimi",
]

# Rough cost per 1K tokens (for budget tracking only)
_COST_PER_1K = {
    "foundry-nano":     0.000150,
    "foundry-deepseek": 0.0014,
    "foundry-gpt":      0.010,
    "foundry-claude":   0.003,
    "foundry-kimi":     0.0015,
}


def _run(cmd: list[str], log_path: Path, timeout: int = 1800) -> tuple[int, float]:
    """Run a subprocess, stream output, return (exit_code, elapsed_s)."""
    t0 = time.time()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([
        str(ROOT / "src"), str(ROOT / "experiments"),
        str(ROOT), str(ROOT / "scripts"),
        env.get("PYTHONPATH", ""),
    ])
    env["SC2PATH"] = env.get("SC2PATH", r"C:\Program Files (x86)\StarCraft II")

    with open(log_path, "w", encoding="utf-8", errors="replace") as f:
        try:
            result = subprocess.run(
                cmd, cwd=str(ROOT), env=env,
                stdout=f, stderr=subprocess.STDOUT,
                timeout=timeout, text=True,
            )
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = -2
            f.write(f"\n[TIMEOUT after {timeout}s]\n")

    elapsed = time.time() - t0
    return code, elapsed


def _already_evaluated(provider: str, strategy: str) -> bool:
    """Check if RTS evaluation for this provider+strategy already exists."""
    pattern = str(ROOT / "data" / "comprehensive_sc2_run_*" / "artifacts"
                  / f"rts_{provider}_*.json")
    for f in glob.glob(pattern):
        with open(f) as fh:
            d = json.load(fh)
        if strategy in d.get("strategies", []):
            return True
    return False


def _already_quizzed(provider: str) -> bool:
    """Check if ROE compliance quiz already ran for this provider."""
    pattern = str(ROOT / "data" / "comprehensive_sc2_run_*" / "artifacts"
                  / f"quiz_{provider}" / f"{provider}_quiz_*.jsonl")
    return bool(glob.glob(pattern))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run full ROE experiment panel across all Foundry models"
    )
    parser.add_argument(
        "--models", nargs="+", default=ALL_PANEL_MODELS,
        help="Models to evaluate (default: all 5)"
    )
    parser.add_argument(
        "--skip-done", action="store_true",
        help="Skip experiments where results already exist"
    )
    parser.add_argument(
        "--budget-usd", type=float, default=50.0,
        help="Soft USD budget cap (default: 50)"
    )
    parser.add_argument(
        "--sc2live-limit", type=int, default=20,
        help="Max sc2live instances to evaluate per model (default: 20)"
    )
    parser.add_argument(
        "--dpo-samples", type=int, default=16,
        help="Samples per DPO instance (default: 16)"
    )
    parser.add_argument(
        "--output-dir", default=None,
        help="Panel output directory (default: data/roe_panel_<timestamp>/)"
    )
    args = parser.parse_args()

    timestamp   = datetime.now().strftime("%Y%m%d_%H%M%S")
    panel_dir   = Path(args.output_dir) if args.output_dir else ROOT / "data" / f"roe_panel_{timestamp}"
    logs_dir    = panel_dir / "logs"
    artifacts   = panel_dir / "artifacts"
    summary_dir = panel_dir / "summary"
    for d in (panel_dir, logs_dir, artifacts, summary_dir):
        d.mkdir(parents=True, exist_ok=True)

    py = sys.executable
    results: dict[str, dict] = {}  # provider -> {quiz, rts_direct, rts_cot}
    est_spent = 0.0

    print("=" * 72)
    print("FULL ROE EXPERIMENT PANEL")
    print("=" * 72)
    print(f"Models    : {args.models}")
    print(f"Budget    : ${args.budget_usd:.2f}")
    print(f"Panel dir : {panel_dir}")
    print(f"Start     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # -- Per-model loop --------------------------------------------------------
    for provider in args.models:
        print(f"\n{'-'*72}".encode('ascii', 'replace').decode())
        print(f"MODEL: {provider}")
        print(f"{'-'*72}")

        if est_spent > args.budget_usd:
            print(f"  Budget cap ${args.budget_usd:.2f} reached, skipping {provider}")
            continue

        model_dir = artifacts / provider
        model_dir.mkdir(parents=True, exist_ok=True)
        results[provider] = {}

        # -- 1. ROE compliance quiz ------------------------------------------
        quiz_out = model_dir / "quiz"
        quiz_done = _already_quizzed(provider)
        if args.skip_done and quiz_done:
            print(f"  ROE quiz: SKIP (existing results found)")
            results[provider]["quiz"] = "cached"
        else:
            print(f"  ROE compliance quiz B0/B1/B2...")
            code, elapsed = _run(
                [py, "scripts/run_roe_compliance_experiment.py",
                 "--mode", "quiz",
                 "--provider", provider,
                 "--enforcement", "all",
                 "--output", str(quiz_out)],
                logs_dir / f"{provider}_quiz.log",
                timeout=600,
            )
            results[provider]["quiz"] = "PASS" if code == 0 else f"FAIL({code})"
            print(f"    -> {results[provider]['quiz']}  ({elapsed:.0f}s)")
            est_spent += _COST_PER_1K.get(provider, 0.003) * 50  # ~50K tokens for quiz

        # -- 2. RTS L3 direct -----------------------------------------------
        rts_dir = model_dir / "rts"
        rts_dir.mkdir(exist_ok=True)
        if args.skip_done and _already_evaluated(provider, "direct"):
            print(f"  RTS L3 direct: SKIP (existing results found)")
            results[provider]["rts_direct"] = "cached"
        else:
            print(f"  RTS L3 evaluation (direct)...")
            code, elapsed = _run(
                [py, "scripts/run_rts_evaluation.py",
                 "--provider", provider,
                 "--modalities", "M4",
                 "--strategies", "direct",
                 "--include-level3",
                 "--level3-limit", "6",
                 "--instance-limit", "0",
                 "--instances-file", "instances/rts_engagement_instances.json",
                 "--results-dir", str(rts_dir)],
                logs_dir / f"{provider}_rts_direct.log",
                timeout=1200,
            )
            results[provider]["rts_direct"] = "PASS" if code == 0 else f"FAIL({code})"
            print(f"    -> {results[provider]['rts_direct']}  ({elapsed:.0f}s)")
            est_spent += _COST_PER_1K.get(provider, 0.003) * 15

        # -- 3. RTS L3 CoT --------------------------------------------------
        if args.skip_done and _already_evaluated(provider, "cot"):
            print(f"  RTS L3 CoT: SKIP (existing results found)")
            results[provider]["rts_cot"] = "cached"
        else:
            print(f"  RTS L3 evaluation (cot)...")
            code, elapsed = _run(
                [py, "scripts/run_rts_evaluation.py",
                 "--provider", provider,
                 "--modalities", "M4",
                 "--strategies", "cot",
                 "--include-level3",
                 "--level3-limit", "6",
                 "--instance-limit", "0",
                 "--instances-file", "instances/rts_engagement_instances.json",
                 "--results-dir", str(rts_dir)],
                logs_dir / f"{provider}_rts_cot.log",
                timeout=1200,
            )
            results[provider]["rts_cot"] = "PASS" if code == 0 else f"FAIL({code})"
            print(f"    -> {results[provider]['rts_cot']}  ({elapsed:.0f}s)")
            est_spent += _COST_PER_1K.get(provider, 0.003) * 30

        # -- 4. sc2live evaluation (nano only for cost reasons) -----------
        if provider == "foundry-nano":
            sc2_out = artifacts / "sc2live_eval"
            sc2_out.mkdir(exist_ok=True)
            print(f"  sc2live instances evaluation ({args.sc2live_limit} instances)...")
            code, elapsed = _run(
                [py, "scripts/run_sc2_evaluation.py",
                 "--provider", provider,
                 "--modalities", "M4",
                 "--strategies", "direct",
                 "--instance-limit", str(args.sc2live_limit),
                 "--instances-path", "instances/sc2live_instances.json",
                 "--output-dir", str(sc2_out)],
                logs_dir / f"{provider}_sc2live.log",
                timeout=600,
            )
            results[provider]["sc2live"] = "PASS" if code == 0 else f"FAIL({code})"
            print(f"    -> {results[provider]['sc2live']}  ({elapsed:.0f}s)")

    # -- DPO preference data (foundry-nano, cheap) -----------------------------
    print(f"\n{'-'*72}")
    print("DPO PREFERENCE DATA (foundry-nano, 16 samples)")
    print(f"{'-'*72}")
    dpo_out = artifacts / "dpo"
    dpo_out.mkdir(exist_ok=True)

    # Seed conflicts first
    code, elapsed = _run(
        [py, "scripts/seed_roe_conflicts.py",
         "--output", "data/sc2_conflicts.jsonl"],
        logs_dir / "seed_conflicts.log",
        timeout=30,
    )
    print(f"  Seed conflicts -> {'PASS' if code == 0 else 'FAIL'}  ({elapsed:.0f}s)")

    code, elapsed = _run(
        [py, "experiments/finetuning/prepare_sc2live_preference_data.py",
         "--provider", "foundry-nano",
         "--conflicts-file", "data/sc2_conflicts.jsonl",
         "--num-samples", str(args.dpo_samples),
         "--output-dir", str(dpo_out)],
        logs_dir / "dpo_preference.log",
        timeout=1800,
    )
    results["dpo"] = "PASS" if code == 0 else f"FAIL({code})"
    print(f"  DPO pairs -> {results['dpo']}  ({elapsed:.0f}s)")

    # -- Compliance analysis for all collected quiz runs -----------------------
    print(f"\n{'-'*72}")
    print("GENERATING CROSS-MODEL COMPLIANCE SUMMARY")
    print(f"{'-'*72}")

    all_quiz_files = []
    for provider in args.models:
        quiz_dir = artifacts / provider / "quiz"
        all_quiz_files.extend(glob.glob(str(quiz_dir / "*.jsonl")))
    # Also pick up older runs
    all_quiz_files.extend(glob.glob(
        str(ROOT / "data" / "comprehensive_sc2_run_*" / "artifacts" / "quiz_*" / "*.jsonl")
    ))
    all_quiz_files = sorted(set(all_quiz_files))

    if all_quiz_files:
        code, elapsed = _run(
            [py, "experiments/roe_compliance_analysis.py",
             "--input"] + all_quiz_files +
            ["--output", str(summary_dir)],
            logs_dir / "compliance_summary.log",
            timeout=60,
        )
        print(f"  Analysis -> {'PASS' if code == 0 else 'FAIL'}  ({elapsed:.0f}s)")

    # -- Cross-env transfer with all available results -------------------------
    print(f"\n{'-'*72}")
    print("CROSS-ENVIRONMENT TRANSFER (foundry-nano)")
    print(f"{'-'*72}")
    code, elapsed = _run(
        [py, "experiments/cross_env_transfer.py",
         "--provider", "foundry-nano",
         "--modalities", "M4",
         "--strategies", "direct",
         "--instance-limit", "6",
         "--output-dir", str(artifacts / "cross_env")],
        logs_dir / "cross_env.log",
        timeout=900,
    )
    print(f"  Cross-env -> {'PASS' if code == 0 else 'FAIL'}  ({elapsed:.0f}s)")

    # -- Generate cross-model accuracy table ----------------------------------
    print(f"\n{'-'*72}")
    print("PANEL RESULTS TABLE")
    print(f"{'-'*72}")
    _print_panel_table(args.models, artifacts)

    # -- Write summary ---------------------------------------------------------
    summary_path = summary_dir / "roe_panel_summary.md"
    _write_panel_summary(summary_path, args.models, results, artifacts, timestamp, est_spent)

    print(f"\n{'='*72}")
    print("FULL ROE PANEL COMPLETE")
    print(f"{'='*72}")
    print(f"Est. spend   : ~${est_spent:.2f}")
    print(f"Summary      : {summary_path}")
    print(f"End          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return 0


def _print_panel_table(models: list[str], artifacts: Path) -> None:
    """Print cross-model accuracy table from RTS result files."""
    print(f"\n  {'Model':<22} {'Direct L3':>10} {'CoT L3':>10} {'Quiz B0':>8} {'Quiz B2':>8}")
    print("  " + "-" * 62)
    for model in models:
        rts_dir = artifacts / model / "rts"
        direct_acc = _get_rts_acc(rts_dir, "direct")
        cot_acc    = _get_rts_acc(rts_dir, "cot")
        # Also check older comprehensive runs
        if direct_acc is None:
            direct_acc = _get_rts_acc_from_runs(model, "direct")
        if cot_acc is None:
            cot_acc = _get_rts_acc_from_runs(model, "cot")
        quiz_b0, quiz_b2 = _get_quiz_rates(artifacts / model / "quiz")
        d  = f"{direct_acc*100:.0f}%" if direct_acc is not None else "--"
        c  = f"{cot_acc*100:.0f}%"    if cot_acc    is not None else "--"
        b0 = f"{quiz_b0*100:.0f}%"    if quiz_b0    is not None else "--"
        b2 = f"{quiz_b2*100:.0f}%"    if quiz_b2    is not None else "--"
        print(f"  {model:<22} {d:>10} {c:>10} {b0:>8} {b2:>8}")


def _get_rts_acc(rts_dir: Path, strategy: str):
    for f in sorted(rts_dir.glob("rts_*.json")):
        with open(f) as fh: d = json.load(fh)
        if strategy in d.get("strategies", []):
            return d.get("summary", {}).get("accuracy")
    return None


def _get_rts_acc_from_runs(provider: str, strategy: str):
    ROOT_ = Path(__file__).parent.parent
    for f in sorted(glob.glob(str(ROOT_ / "data" / "comprehensive_sc2_run_*"
                                   / "artifacts" / f"rts_{provider}_*.json"))):
        with open(f) as fh: d = json.load(fh)
        if strategy in d.get("strategies", []):
            return d.get("summary", {}).get("accuracy")
    return None


def _get_quiz_rates(quiz_dir: Path):
    """Return (B0_correct_abstain_rate, B2_correct_abstain_rate) or (None, None)."""
    files = sorted(quiz_dir.glob("*.jsonl")) if quiz_dir.exists() else []
    if not files:
        # Fall back to older comprehensive runs
        ROOT_ = Path(__file__).parent.parent
        prov = quiz_dir.parent.name
        for f in sorted(glob.glob(str(ROOT_ / "data" / "comprehensive_sc2_run_*"
                                       / "artifacts" / f"quiz_{prov}" / "*.jsonl"))):
            files.append(Path(f))
    if not files:
        return None, None
    b0_total = b0_correct = b2_total = b2_correct = 0
    with open(files[-1]) as fh:
        for line in fh:
            line = line.strip()
            if not line: continue
            rec = json.loads(line)
            mode = rec.get("mode", "")
            correct = rec.get("gold", {}).get("correct_abstain", True)
            if mode == "B0":
                b0_total += 1
                if correct: b0_correct += 1
            elif mode == "B2":
                b2_total += 1
                if correct: b2_correct += 1
    b0 = b0_correct / b0_total if b0_total else None
    b2 = b2_correct / b2_total if b2_total else None
    return b0, b2


def _write_panel_summary(path: Path, models: list[str], results: dict,
                          artifacts: Path, timestamp: str, est_spent: float) -> None:
    lines = [
        "# ROE Experiment Panel Summary",
        "",
        f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
        f"**Est. spend**: ~${est_spent:.2f}  ",
        "",
        "## Step Results",
        "",
        "| Model | ROE Quiz | RTS Direct | RTS CoT | sc2live |",
        "|-------|---------|------------|---------|---------|",
    ]
    for model in models:
        r = results.get(model, {})
        lines.append(
            f"| {model} | {r.get('quiz', '--')} | {r.get('rts_direct', '--')} "
            f"| {r.get('rts_cot', '--')} | {r.get('sc2live', '--')} |"
        )
    lines += [
        "",
        "## Accuracy Table",
        "",
        "| Model | RTS L3 Direct | RTS L3 CoT | ROE B0 Correct | ROE B2 Correct |",
        "|-------|------------|---------|-----------|-----------|",
    ]
    for model in models:
        rts_dir = artifacts / model / "rts"
        d_acc = _get_rts_acc(rts_dir, "direct") or _get_rts_acc_from_runs(model, "direct")
        c_acc = _get_rts_acc(rts_dir, "cot")    or _get_rts_acc_from_runs(model, "cot")
        b0, b2 = _get_quiz_rates(artifacts / model / "quiz")
        d  = f"{d_acc*100:.0f}%" if d_acc is not None else "--"
        c  = f"{c_acc*100:.0f}%" if c_acc is not None else "--"
        b0s = f"{b0*100:.0f}%"   if b0   is not None else "--"
        b2s = f"{b2*100:.0f}%"   if b2   is not None else "--"
        lines.append(f"| {model} | {d} | {c} | {b0s} | {b2s} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())

