"""
Symbolic Baseline -- paper Section 4.7.

Evaluates an ASP / defeasible-logic solver on the same DeFAb instance sets,
providing a symbolic ceiling against which neural models are compared.

For Level 2 (rule abduction) the solver finds the minimal set of rules in
the candidate set that make the target literal defeasibly provable.

For Level 3 (defeater abduction) the solver enumerates candidate defeaters
and checks which ones (a) eliminate the anomaly and (b) are conservative.

The neural--symbolic gap per level is:
    gap_L = Acc_solver(L) - Acc_model_best(L)

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.author.loaders import load_instances_from_json
from blanc.reasoning.defeasible import defeasible_provable


# ---------------------------------------------------------------------------
# Solver core
# ---------------------------------------------------------------------------

@dataclass
class SolverResult:
    instance_id: str
    level: int
    correct: bool
    solved: bool           # True unless timeout
    elapsed: float         # seconds
    n_candidates_tried: int
    gold_found: Optional[str] = None


def solve_level2(
    theory: Theory,
    target: str,
    candidates: list[str],
    gold: list[str],
    timeout: float = 30.0,
) -> SolverResult:
    """
    Symbolic Level 2 solver: find the subset of candidates that, added to
    theory, makes `target` defeasibly provable.

    Strategy: iterate candidates (already sorted by simplicity) and try
    adding each.  Return the first that works.
    """
    t0 = time.time()

    for i, cand in enumerate(candidates):
        if time.time() - t0 > timeout:
            return SolverResult(
                instance_id="",
                level=2,
                correct=False,
                solved=False,
                elapsed=time.time() - t0,
                n_candidates_tried=i + 1,
            )
        try:
            D2 = _add_candidate_fact(theory, cand)
            if defeasible_provable(D2, target):
                is_gold = cand in gold
                return SolverResult(
                    instance_id="",
                    level=2,
                    correct=is_gold,
                    solved=True,
                    elapsed=time.time() - t0,
                    n_candidates_tried=i + 1,
                    gold_found=cand if is_gold else None,
                )
        except Exception:
            continue

    # Nothing worked
    return SolverResult(
        instance_id="",
        level=2,
        correct=False,
        solved=True,
        elapsed=time.time() - t0,
        n_candidates_tried=len(candidates),
    )


def solve_level3(
    theory: Theory,
    target: str,
    candidates: list[str],
    gold: str,
    preserved: list[str],
    timeout: float = 30.0,
) -> SolverResult:
    """
    Symbolic Level 3 solver: enumerate candidate defeaters that (a) eliminate
    `target` and (b) are conservative w.r.t. `preserved`.
    """
    from level3_evaluator import parse_rule_from_text, _add_rule_with_superiority, _deep_copy_theory

    t0 = time.time()

    for i, cand in enumerate(candidates):
        if time.time() - t0 > timeout:
            return SolverResult(
                instance_id="",
                level=3,
                correct=False,
                solved=False,
                elapsed=time.time() - t0,
                n_candidates_tried=i + 1,
            )

        parsed = parse_rule_from_text(cand)
        if parsed is None:
            continue

        try:
            D2 = _add_rule_with_superiority(theory, parsed, target)
            if defeasible_provable(D2, target):
                continue  # Doesn't resolve

            # Check conservativity
            from blanc.author.metrics import check_conservativity
            conservative, _ = check_conservativity(
                _deep_copy_theory(theory), D2, target, preserved
            )
            if conservative:
                is_gold = cand.strip() == gold.strip()
                return SolverResult(
                    instance_id="",
                    level=3,
                    correct=is_gold,
                    solved=True,
                    elapsed=time.time() - t0,
                    n_candidates_tried=i + 1,
                    gold_found=cand if is_gold else None,
                )
        except Exception:
            continue

    return SolverResult(
        instance_id="",
        level=3,
        correct=False,
        solved=True,
        elapsed=time.time() - t0,
        n_candidates_tried=len(candidates),
    )


def _add_candidate_fact(theory: Theory, candidate: str) -> Theory:
    """Add a candidate fact or rule string to a copy of theory."""
    import copy
    D2 = copy.deepcopy(theory)
    # Candidates in Level 2 are fact strings like 'df_bird(owl):  => bird(owl)'
    # Try to add it as a fact or rule
    if "=>" in candidate or "~>" in candidate:
        # It's a rule -- parse and add
        from level3_evaluator import parse_rule_from_text
        rule = parse_rule_from_text(candidate)
        if rule:
            D2.add_rule(rule)
    else:
        D2.add_fact(candidate)
    return D2


# ---------------------------------------------------------------------------
# Batch evaluation
# ---------------------------------------------------------------------------

def run_symbolic_baseline(
    instance_file: Path,
    level: int,
    timeout: float = 30.0,
) -> dict:
    """
    Run the symbolic baseline on all instances in a JSON file.

    Returns summary statistics.
    """
    with open(instance_file) as f:
        data = json.load(f)

    instances = data.get("instances", [])
    print(f"Loaded {len(instances)} instances from {instance_file.name}")

    results = []
    for i, inst in enumerate(instances):
        theory = _theory_from_dict(inst.get("theory", {}))
        target = inst.get("target", "")
        candidates = inst.get("candidates", [])
        gold = inst.get("gold", [])
        instance_id = inst.get("id", f"inst_{i:04d}")
        preserved = inst.get("metadata", {}).get("preserved_expectations", [])

        if level == 2:
            res = solve_level2(theory, target, candidates, gold if isinstance(gold, list) else [gold], timeout)
        else:
            gold_str = gold if isinstance(gold, str) else (gold[0] if gold else "")
            res = solve_level3(theory, target, candidates, gold_str, preserved, timeout)

        res.instance_id = instance_id
        results.append(res)

        if (i + 1) % 50 == 0:
            n_correct = sum(r.correct for r in results)
            print(f"  [{i+1}/{len(instances)}] acc={n_correct/(i+1):.1%}")

    n = len(results)
    n_correct = sum(r.correct for r in results)
    n_solved = sum(r.solved for r in results)
    avg_time = sum(r.elapsed for r in results) / n if n > 0 else 0.0

    summary = {
        "total": n,
        "correct": n_correct,
        "accuracy": n_correct / n if n > 0 else 0.0,
        "solved_rate": n_solved / n if n > 0 else 0.0,
        "avg_elapsed_s": avg_time,
    }

    print(f"\nSymbolic Baseline (Level {level})")
    print(f"  Accuracy  : {summary['accuracy']:.1%}  ({n_correct}/{n})")
    print(f"  Solved    : {summary['solved_rate']:.1%}")
    print(f"  Avg time  : {summary['avg_elapsed_s']:.3f}s")

    return summary


def _theory_from_dict(d: dict) -> Theory:
    """Reconstruct a Theory from the JSON representation in instance files."""
    facts = d.get("facts", [])
    rules_raw = d.get("rules", [])
    superiority = d.get("superiority", {})

    T = Theory()
    for f in facts:
        T.add_fact(f)
    for r in rules_raw:
        label = r.get("label")
        head = r.get("head", "")
        body = tuple(r.get("body", []))
        rt_str = r.get("rule_type", "DEFEASIBLE").upper()
        rt = RuleType[rt_str] if rt_str in RuleType.__members__ else RuleType.DEFEASIBLE
        T.add_rule(Rule(head=head, body=body, rule_type=rt, label=label))

    if isinstance(superiority, dict):
        for sup, infs in superiority.items():
            for inf in (infs if isinstance(infs, list) else [infs]):
                T.add_superiority(sup, inf)

    return T


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Run symbolic ceiling on DeFAb instances")
    parser.add_argument("--instances-dir", default=str(ROOT / "instances"))
    parser.add_argument("--level", type=int, choices=[2, 3], default=2)
    parser.add_argument("--timeout", type=float, default=30.0,
                        help="Per-instance timeout in seconds")
    parser.add_argument("--save", default=None,
                        help="Save summary JSON to this path")
    args = parser.parse_args()

    instances_dir = Path(args.instances_dir)

    print("=" * 70)
    print(f"Symbolic Baseline -- Level {args.level}")
    print("=" * 70)

    if args.level == 2:
        files = [
            instances_dir / "biology_dev_instances.json",
            instances_dir / "legal_dev_instances.json",
            instances_dir / "materials_dev_instances.json",
        ]
    else:
        files = [instances_dir / "level3_instances.json"]

    all_results = {}
    for f in files:
        if not f.exists():
            print(f"Skipping (not found): {f}")
            continue
        domain = f.stem.replace("_dev_instances", "").replace("_instances", "")
        summary = run_symbolic_baseline(f, args.level, timeout=args.timeout)
        all_results[domain] = summary

    # Overall
    total = sum(r["total"] for r in all_results.values())
    correct = sum(r["correct"] for r in all_results.values())
    if total > 0:
        print(f"\nOverall: {correct/total:.1%}  ({correct}/{total})")

    if args.save:
        with open(args.save, "w") as f:
            json.dump(all_results, f, indent=2)
        print(f"\nResults saved to: {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
