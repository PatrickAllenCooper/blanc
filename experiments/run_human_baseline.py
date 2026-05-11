"""
Phase 4C: Human baseline on Tier 0 Level 3.

Simple interactive CLI that presents each L3 instance (at M4 formal modality)
to a human solver and records their selection and time. Can be run by multiple
solvers; results are appended to a shared JSONL file with a solver-id.

Usage (solver session):
  python experiments/run_human_baseline.py --solver-id alice --output data/human_baseline.jsonl

  # To see aggregate results:
  python experiments/run_human_baseline.py --aggregate data/human_baseline.jsonl

Instructions for solvers (include in email/Prolific):
  1. Run the script; instances are displayed one at a time.
  2. Each instance shows:
     - A defeasible theory (set of rules and facts).
     - An anomaly: a prediction the theory makes that should NOT hold.
     - 6 candidate defeater rules.
  3. Pick the ONE candidate that, when added, blocks the anomaly while
     preserving all other predictions. Enter the NUMBER (1-6).
  4. Type 's' to skip, 'q' to quit and save progress.

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from scipy import stats
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load_instances() -> list[dict]:
    path = ROOT / "instances" / "level3_instances.json"
    if not path.exists():
        raise FileNotFoundError(f"Tier 0 L3 file not found: {path}")
    with open(path) as f:
        return json.load(f).get("instances", [])


def _render_instance(inst: dict, idx: int, total: int) -> str:
    lines = [
        f"\n{'='*70}",
        f"Instance {idx+1}/{total}   Name: {inst['name']}   Domain: {inst['domain']}",
        f"{'='*70}",
        "",
        "THEORY (rules and facts):",
    ]
    for fact in inst.get("theory_facts", []):
        lines.append(f"  Fact:  {fact}")
    for rule in inst.get("theory_rules", []):
        lines.append(f"  Rule:  {rule}")
    lines += [
        "",
        f"ANOMALY (the theory incorrectly predicts this is true):",
        f"  {inst['anomaly']}",
        "",
        "CANDIDATES (pick the defeater that fixes the anomaly conservatively):",
    ]
    for i, c in enumerate(inst.get("candidates", []), 1):
        lines.append(f"  {i}. {c}")
    lines += ["", "Enter choice (1-6), 's' to skip, 'q' to quit: "]
    return "\n".join(lines)


def run_session(solver_id: str, output_file: Path, seed: int = 42) -> None:
    instances = _load_instances()
    rng = random.Random(seed)
    order = list(range(len(instances)))
    rng.shuffle(order)

    # Load already-answered to allow resume
    answered = set()
    if output_file.exists():
        with open(output_file) as f:
            for line in f:
                try:
                    rec = json.loads(line.strip())
                    if rec.get("solver_id") == solver_id:
                        answered.add(rec["name"])
                except Exception:
                    pass
        print(f"Resuming: {len(answered)} instances already answered by {solver_id}.")

    pending = [i for i in order if instances[i]["name"] not in answered]
    print(f"{len(pending)} instances remaining.")

    with open(output_file, "a") as fout:
        for i, idx in enumerate(pending):
            inst = instances[idx]
            print(_render_instance(inst, i, len(pending)), end="", flush=True)
            t_start = time.time()
            raw = input()
            elapsed = time.time() - t_start

            if raw.strip().lower() == "q":
                print("Session saved. Goodbye.")
                break
            if raw.strip().lower() == "s":
                print("Skipped.")
                continue

            try:
                choice_idx = int(raw.strip()) - 1
                chosen = inst["candidates"][choice_idx]
                correct = chosen == inst.get("gold", "")
                rec = {
                    "solver_id": solver_id,
                    "name": inst["name"],
                    "domain": inst["domain"],
                    "choice_idx": choice_idx,
                    "chosen": chosen,
                    "gold": inst.get("gold", ""),
                    "correct": correct,
                    "elapsed_s": round(elapsed, 2),
                    "nov": inst.get("nov", 0.0),
                }
                fout.write(json.dumps(rec) + "\n")
                fout.flush()
                print(f"  -> {'CORRECT' if correct else 'WRONG'}  (Gold: {inst.get('gold', '?')})")
            except (ValueError, IndexError):
                print("Invalid input. Instance skipped.")


def aggregate(output_file: Path) -> None:
    records = []
    with open(output_file) as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except Exception:
                pass

    if not records:
        print("No records found.")
        return

    solvers = set(r["solver_id"] for r in records)
    print(f"\n{'='*60}")
    print(f"Human Baseline Aggregate ({len(records)} responses, {len(solvers)} solvers)")
    print(f"{'='*60}")

    correct = [r["correct"] for r in records]
    n = len(correct)
    acc = sum(correct) / n

    # Wilson 95% CI
    ci = stats.proportion_confint(sum(correct), n, alpha=0.05, method="wilson")
    print(f"\nOverall accuracy:  {acc*100:.1f}%  (n={n})")
    print(f"Wilson 95% CI:     [{ci[0]*100:.1f}%, {ci[1]*100:.1f}%]")
    print(f"ASP ceiling:       100%")

    # By solver
    print(f"\n{'Solver':<20} {'N':>4} {'Acc':>7} {'95% CI':>20}")
    print("-" * 55)
    for sid in sorted(solvers):
        recs = [r for r in records if r["solver_id"] == sid]
        c = [r["correct"] for r in recs]
        a = sum(c) / len(c)
        ci_s = stats.proportion_confint(sum(c), len(c), alpha=0.05, method="wilson")
        print(f"{sid:<20} {len(c):>4} {a*100:>6.1f}%  [{ci_s[0]*100:.1f}%, {ci_s[1]*100:.1f}%]")

    # By domain
    domains = set(r["domain"] for r in records)
    print(f"\n{'Domain':<15} {'N':>4} {'Acc':>7}")
    print("-" * 30)
    for d in sorted(domains):
        recs = [r for r in records if r["domain"] == d]
        c = [r["correct"] for r in recs]
        print(f"{d:<15} {len(c):>4} {sum(c)/len(c)*100:>6.1f}%")

    # Mean time
    times = [r["elapsed_s"] for r in records if r.get("elapsed_s", 0) > 0]
    if times:
        print(f"\nMean response time: {np.mean(times):.1f}s  (median {np.median(times):.1f}s)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Human baseline on DeFAb Tier 0 L3")
    ap.add_argument("--solver-id", default=None,
                    help="Solver identifier (e.g., 'alice', 'prolific_001'). "
                         "Required unless --aggregate is used.")
    ap.add_argument("--output", default=str(ROOT / "data" / "human_baseline.jsonl"),
                    help="JSONL file to append responses to.")
    ap.add_argument("--aggregate", action="store_true",
                    help="Show aggregate statistics instead of running a session.")
    ap.add_argument("--seed", type=int, default=42,
                    help="Random seed for instance ordering.")
    args = ap.parse_args()

    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    if args.aggregate:
        aggregate(output_file)
        return 0

    if not args.solver_id:
        print("ERROR: --solver-id required for a solver session.")
        return 1

    print(f"\nDeFAb Human Baseline Session  (solver: {args.solver_id})")
    print("="*60)
    print("You will be shown 35 Level-3 defeater-abduction instances.")
    print("For each: select the candidate that conservatively resolves")
    print("the stated anomaly. The CORRECT answer is the gold defeater")
    print("that blocks the anomaly while preserving all other predictions.")
    print("\nPress Enter to begin...")
    input()

    run_session(args.solver_id, output_file, seed=args.seed)
    print(f"\nResults saved to {output_file}")
    print("To see aggregate stats: python experiments/run_human_baseline.py --aggregate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
