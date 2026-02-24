"""
Local runner for the full Azure AI Foundry evaluation.

Runs all four Foundry models (gpt-5.2-chat, Kimi-K2.5, claude-sonnet-4-6,
DeepSeek-R1) locally without SLURM.  Intended for use when not connected to
CURC Alpine but the Foundry API key is available.

Environment
-----------
Set FOUNDRY_API_KEY in your .env file or export it before running:

    export FOUNDRY_API_KEY="<your-key>"
    python experiments/run_foundry_local.py

Or for a quick smoke test on the first 10 instances per domain:

    python experiments/run_foundry_local.py --instance-limit 10 --level3-limit 5

Usage
-----
    python experiments/run_foundry_local.py [OPTIONS]

Options
-------
--instance-limit N      Max Level 2 instances per domain (default: 120; full = all)
--level3-limit   N      Max Level 3 instances (default: 35; full = all)
--modalities     LIST   Space-separated modalities: M4 M2 M1 M3 (default: M4 M2 M1 M3)
--strategies     LIST   Space-separated strategies: direct cot (default: direct cot)
--skip-gpt              Skip gpt-5.2-chat
--skip-kimi             Skip Kimi-K2.5
--skip-claude           Skip claude-sonnet-4-6
--skip-deepseek         Skip DeepSeek-R1
--results-dir    DIR    Where to write results (default: experiments/results/)
--dry-run               Run with 3 instances to verify endpoints, then exit

After the run, generate LaTeX tables with:

    python experiments/generate_paper_tables.py --results-dir experiments/results/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Model configuration
# ---------------------------------------------------------------------------

MODELS = [
    {
        "key":      "gpt",
        "provider": "foundry-gpt",
        "label":    "gpt52",
        "display":  "gpt-5.2-chat",
        "rpm":      2500,
    },
    {
        "key":      "kimi",
        "provider": "foundry-kimi",
        "label":    "kimi",
        "display":  "Kimi-K2.5",
        "rpm":      250,
    },
    {
        "key":      "claude",
        "provider": "foundry-claude",
        "label":    "claude",
        "display":  "claude-sonnet-4-6",
        "rpm":      250,
    },
    {
        "key":      "deepseek",
        "provider": "foundry-deepseek",
        "label":    "deepseek",
        "display":  "DeepSeek-R1",
        "rpm":      5000,
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _header(msg: str) -> None:
    bar = "=" * 70
    print(f"\n{bar}\n{msg}\n{bar}")


def _section(msg: str) -> None:
    bar = "-" * 70
    print(f"\n{bar}\n{msg}\n{bar}")


def _check_api_key() -> str:
    key = os.environ.get("FOUNDRY_API_KEY", "")
    if not key:
        print("ERROR: FOUNDRY_API_KEY is not set.")
        print()
        print("  Set it in your .env file:")
        print("    FOUNDRY_API_KEY=<your-key>")
        print()
        print("  Or export it before running:")
        print("    export FOUNDRY_API_KEY=<your-key>")
        sys.exit(1)
    return key


def _validate_endpoint(provider: str, api_key: str) -> bool:
    """Fire a single 'Say test' query to verify the endpoint is reachable."""
    try:
        from model_interface import create_model_interface
        iface = create_model_interface(provider, api_key=api_key)
        resp = iface.query("Reply with exactly: OK", max_tokens=10)
        print(f"  Endpoint OK  ({resp.text.strip()[:40]})")
        return True
    except Exception as exc:
        print(f"  Endpoint FAIL: {exc}")
        return False


def _run_model(
    provider:      str,
    label:         str,
    display:       str,
    api_key:       str,
    args:          argparse.Namespace,
    timestamp:     str,
) -> int:
    """Invoke run_evaluation.py for a single Foundry model."""
    results_dir = Path(args.results_dir) / f"foundry_{label}_{timestamp}"
    cache_dir   = Path("experiments/cache") / f"foundry_{label}"
    checkpoint  = results_dir / "checkpoint.json"

    _section(f"Running: {display}  ({provider})")
    print(f"  Results  : {results_dir}")
    print(f"  Cache    : {cache_dir}")

    results_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(ROOT / "experiments" / "run_evaluation.py"),
        "--provider",       provider,
        "--api-key",        api_key,
        "--modalities",     *args.modalities,
        "--strategies",     *args.strategies,
        "--instance-limit", str(args.instance_limit),
        "--results-dir",    str(results_dir),
        "--cache-dir",      str(cache_dir),
        "--checkpoint",     str(checkpoint),
    ]
    if args.include_level3:
        cmd += ["--include-level3", "--level3-limit", str(args.level3_limit)]

    t0 = time.time()
    result = subprocess.run(cmd, cwd=str(ROOT))
    elapsed = time.time() - t0

    print(f"\n  Finished {display} in {elapsed/60:.1f} min (exit {result.returncode})")

    if result.returncode == 0:
        _run_analysis(results_dir)

    return result.returncode


def _run_analysis(results_dir: Path) -> None:
    """Run analyze_results.py on a completed results directory."""
    script = ROOT / "experiments" / "analyze_results.py"
    summary = results_dir / "summary.json"
    cmd = [
        sys.executable, str(script),
        "--results-dir", str(results_dir),
        "--save", str(summary),
    ]
    result = subprocess.run(cmd, cwd=str(ROOT), capture_output=True)
    if result.returncode == 0:
        print(f"  Summary written to {summary}")
    else:
        print(f"  Warning: analyze_results.py exited {result.returncode}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run the full DeFAb Foundry evaluation locally (no SLURM).",
    )
    p.add_argument("--instance-limit", type=int, default=120,
                   help="Max Level 2 instances per domain (default 120 = full).")
    p.add_argument("--level3-limit", type=int, default=35,
                   help="Max Level 3 instances (default 35 = full).")
    p.add_argument("--modalities", nargs="+", default=["M4", "M2", "M1", "M3"],
                   help="Modalities to evaluate.")
    p.add_argument("--strategies", nargs="+", default=["direct", "cot"],
                   help="Prompting strategies.")
    p.add_argument("--no-level3", dest="include_level3", action="store_false",
                   help="Skip Level 3 instances.")
    p.add_argument("--results-dir", default="experiments/results",
                   help="Root directory for results.")
    p.add_argument("--skip-gpt",      action="store_true")
    p.add_argument("--skip-kimi",     action="store_true")
    p.add_argument("--skip-claude",   action="store_true")
    p.add_argument("--skip-deepseek", action="store_true")
    p.add_argument("--dry-run",       action="store_true",
                   help="Validate endpoints and run 3 instances per domain, then exit.")
    p.set_defaults(include_level3=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    _header("DeFAb Azure AI Foundry Local Evaluation")
    print(f"  Start            : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Instance limit   : {args.instance_limit} per domain")
    print(f"  Level 3 limit    : {args.level3_limit}")
    print(f"  Modalities       : {' '.join(args.modalities)}")
    print(f"  Strategies       : {' '.join(args.strategies)}")
    print(f"  Include Level 3  : {args.include_level3}")
    if args.dry_run:
        print("  MODE             : DRY RUN (3 instances per domain)")
        args.instance_limit = 3
        args.level3_limit   = 3

    api_key = _check_api_key()

    skip = {
        "gpt":      args.skip_gpt,
        "kimi":     args.skip_kimi,
        "claude":   args.skip_claude,
        "deepseek": args.skip_deepseek,
    }
    active = [m for m in MODELS if not skip[m["key"]]]
    print(f"  Models           : {', '.join(m['display'] for m in active)}")

    # Validate all endpoints before starting expensive evaluation
    _header("Endpoint Validation")
    all_ok = True
    for m in active:
        print(f"\n  {m['display']} ...")
        ok = _validate_endpoint(m["provider"], api_key)
        if not ok:
            all_ok = False

    if not all_ok:
        print("\nERROR: one or more endpoints failed validation.")
        print("Check your FOUNDRY_API_KEY and model deployment status at ai.azure.com")
        return 1

    if args.dry_run:
        print("\nDry-run validation complete. All endpoints reachable.")
        return 0

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    overall_exit = 0

    for m in active:
        code = _run_model(
            provider=m["provider"],
            label=m["label"],
            display=m["display"],
            api_key=api_key,
            args=args,
            timestamp=timestamp,
        )
        if code != 0:
            overall_exit = code

    _header("All Foundry Evaluations Complete")
    print(f"  Finish : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Status : {'OK' if overall_exit == 0 else 'PARTIAL FAILURE'}")
    print()
    print("Next steps:")
    print(f"  python experiments/generate_paper_tables.py --results-dir {args.results_dir}/")
    print(f"  python experiments/novelty_analysis.py      --results-dir {args.results_dir}/")
    print(f"  python experiments/error_taxonomy.py        --results-dir {args.results_dir}/")

    return overall_exit


if __name__ == "__main__":
    sys.exit(main())
