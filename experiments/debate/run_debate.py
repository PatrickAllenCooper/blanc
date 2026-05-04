"""
CLI entry point for the adversarial defeasible debate experiments.

Runs the debate protocol across knowledge bases, recording per-round
proposals, challenges, defenses, and resolution scores.

Usage examples:

    # Quick test with biology KB
    python experiments/debate/run_debate.py --kb biology --rounds 3

    # All KBs, more MCTS iterations
    python experiments/debate/run_debate.py --kb all --rounds 5 --mcts-iterations 500

    # With explicit target
    python experiments/debate/run_debate.py --kb biology --target "flies(tweety)" --rounds 3

Author: Anonymous Authors
"""

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.debate.protocol import DebateConfig, DebateProtocol
from blanc.debate.resolution import debate_outcome
from blanc.search.mcts import MCTSConfig


# ---------------------------------------------------------------------------
# Knowledge base loaders (reuse existing KB modules)
# ---------------------------------------------------------------------------

def _load_kb(name: str) -> tuple:
    """Return (Theory, list_of_targets) for a named KB."""
    if name == "biology":
        return _biology_kb()
    elif name == "legal":
        return _legal_kb()
    elif name == "materials":
        return _materials_kb()
    elif name == "tweety":
        return _tweety_kb()
    else:
        raise ValueError(f"Unknown KB: {name}")


def _tweety_kb():
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_fact("sparrow(tweety)")
    t.add_fact("bird(opus)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule(
        head="bird(X)", body=("sparrow(X)",),
        rule_type=RuleType.STRICT, label="r_sparrow",
    ))
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r_flies",
    ))
    t.add_rule(Rule(
        head="~flies(X)", body=("penguin(X)",),
        rule_type=RuleType.DEFEATER, label="d_penguin",
    ))
    t.add_superiority("d_penguin", "r_flies")
    targets = ["flies(tweety)"]
    return t, targets


def _biology_kb():
    try:
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb()
        targets = _derivable_targets(theory, limit=5)
        return theory, targets
    except Exception:
        return _tweety_kb()


def _legal_kb():
    try:
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb()
        targets = _derivable_targets(theory, limit=5)
        return theory, targets
    except Exception:
        return _tweety_kb()


def _materials_kb():
    try:
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb()
        targets = _derivable_targets(theory, limit=5)
        return theory, targets
    except Exception:
        return _tweety_kb()


def _derivable_targets(theory: Theory, limit: int = 5) -> list:
    """Find a handful of defeasibly provable literals to use as targets."""
    from blanc.reasoning.defeasible import DefeasibleEngine
    engine = DefeasibleEngine(theory)
    targets = []
    for rule in theory.get_rules_by_type(RuleType.DEFEASIBLE):
        constants = engine._extract_constants()
        for sub in engine._generate_substitutions(rule, constants):
            lit = engine._substitute(rule.head, sub)
            if engine.is_defeasibly_provable(lit):
                targets.append(lit)
                if len(targets) >= limit:
                    return targets
    return targets


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run_debate_experiment(args):
    kbs = (
        ["biology", "legal", "materials"]
        if args.kb == "all"
        else [args.kb]
    )

    all_results = []

    for kb_name in kbs:
        print(f"\n{'='*60}")
        print(f"Knowledge Base: {kb_name}")
        print(f"{'='*60}")

        theory, default_targets = _load_kb(kb_name)
        targets = [args.target] if args.target else default_targets
        if not targets:
            print(f"  No derivable targets found for {kb_name}, skipping.")
            continue

        mcts_config = MCTSConfig(
            max_iterations=args.mcts_iterations,
            exploration_constant=args.explore_constant,
            convergence_threshold=args.convergence_threshold,
            seed=args.seed,
        )
        debate_config = DebateConfig(
            rounds=args.rounds,
            mcts_config=mcts_config,
            distractor_count=args.distractors,
            distractor_strategy=args.distractor_strategy,
        )

        for target in targets:
            print(f"\n  Target: {target}")
            t0 = time.time()
            protocol = DebateProtocol(theory, debate_config)
            result = protocol.run(target=target)
            elapsed = time.time() - t0

            scores = debate_outcome(result)

            record = {
                "kb": kb_name,
                "target": target,
                "rounds": args.rounds,
                "mcts_iterations": args.mcts_iterations,
                "elapsed_seconds": round(elapsed, 2),
                "proponent_robustness": scores.proponent_robustness,
                "opponent_robustness": scores.opponent_robustness,
                "proponent_grounding": scores.proponent_grounding,
                "opponent_grounding": scores.opponent_grounding,
                "proponent_creativity": scores.proponent_creativity,
                "opponent_creativity": scores.opponent_creativity,
                "winner": scores.winner,
                "margin": scores.margin,
                "proponent_defense_rate": result.proponent_defense_rate,
                "opponent_defense_rate": result.opponent_defense_rate,
                "theory_size": result.theory_size,
                "round_details": [],
            }

            for rnd in result.rounds:
                rd = {
                    "round": rnd.round_number,
                    "proponent_statement": rnd.proponent_proposal.statement,
                    "proponent_confidence": rnd.proponent_proposal.confidence,
                    "opponent_statement": rnd.opponent_proposal.statement,
                    "opponent_confidence": rnd.opponent_proposal.confidence,
                    "challenges": len(rnd.challenges),
                    "defenses_success": sum(
                        1 for d in rnd.defenses if d.success
                    ),
                    "defenses_total": len(rnd.defenses),
                }
                record["round_details"].append(rd)

            all_results.append(record)

            print(f"    Winner: {scores.winner or 'tie'} "
                  f"(margin={scores.margin:.3f})")
            print(f"    Proponent robustness={scores.proponent_robustness:.3f} "
                  f"grounding={scores.proponent_grounding:.3f}")
            print(f"    Opponent  robustness={scores.opponent_robustness:.3f} "
                  f"grounding={scores.opponent_grounding:.3f}")
            print(f"    Elapsed: {elapsed:.2f}s")

    out_dir = ROOT / "experiments" / "results"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "debate_results.json"
    with open(out_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults written to {out_path}")
    return all_results


def main():
    parser = argparse.ArgumentParser(
        description="Run adversarial defeasible debate experiments"
    )
    parser.add_argument(
        "--kb", default="tweety",
        choices=["tweety", "biology", "legal", "materials", "all"],
        help="Knowledge base to use",
    )
    parser.add_argument("--target", default=None, help="Target literal")
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--mcts-iterations", type=int, default=200)
    parser.add_argument("--explore-constant", type=float, default=1.414)
    parser.add_argument("--convergence-threshold", type=int, default=30)
    parser.add_argument("--distractors", type=int, default=5)
    parser.add_argument(
        "--distractor-strategy", default="syntactic",
        choices=["random", "syntactic", "adversarial"],
    )
    parser.add_argument("--seed", type=int, default=42)

    args = parser.parse_args()
    run_debate_experiment(args)


if __name__ == "__main__":
    main()
