"""Adversarial defeasible debate pilot experiment.

Runs the MCTS-based debate protocol from Section 10 of full_paper.tex on
all three Tier-0 KB domains (biology, legal, materials) using the mock
provider for speed, then logs robustness/grounding/creativity metrics.

Usage:
    python experiments/run_debate_pilot.py [--provider mock|foundry-gpt]
    python experiments/run_debate_pilot.py --full  # 200 MCTS iterations
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.search.mcts import MCTS, MCTSConfig
from blanc.search.derivation_space import DerivationSpace, DerivationState
from blanc.search.reward import derivation_strength_reward, novelty_reward, composite_reward
from blanc.author.generation import AbductiveInstance


# ---------------------------------------------------------------------------
# Debate agent
# ---------------------------------------------------------------------------

@dataclass
class DebateResult:
    instance_id: str
    domain: str
    level: int
    proposer_wins: int
    challenger_wins: int
    draws: int
    rounds: int
    proposer_robustness: float   # fraction of challenges survived
    proposer_grounding: float    # fraction of proposals derivable
    proposer_creativity: float   # fraction with novel predicates
    challenger_robustness: float
    challenger_grounding: float
    challenger_creativity: float
    mean_tree_depth: float
    elapsed_s: float

    def winner(self) -> str:
        if self.proposer_wins > self.challenger_wins:
            return "proposer"
        if self.challenger_wins > self.proposer_wins:
            return "challenger"
        return "draw"


def run_single_debate(
    instance: AbductiveInstance,
    n_rounds: int,
    n_mcts_iter: int,
    seed: int = 42,
) -> DebateResult:
    """Run an adversarial debate on a single instance.

    Proposer agent: MCTS over the full theory (D_full) seeking
    the highest-reward defeater (defender role).
    Challenger agent: MCTS over the ablated theory (D_minus) seeking
    to block the proposer's derivation (attacker role).

    Returns a DebateResult with win/loss/draw statistics.
    """
    rng = random.Random(seed)
    # Proposer: searches for the best defeater on the standard ablated theory
    space_full = DerivationSpace(instance.D_minus)

    # Challenger: searches on a slightly perturbed theory (Author Algorithm proxy)
    # We drop one random defeasible rule so challenger faces a harder theory
    from blanc.core.theory import Theory, Rule, RuleType
    perturbed_rules = list(instance.D_minus.rules)
    defeasible = [r for r in perturbed_rules if r.rule_type == RuleType.DEFEASIBLE]
    if defeasible:
        rng_local = random.Random(seed + 1)
        drop = rng_local.choice(defeasible)
        perturbed_rules = [r for r in perturbed_rules if r is not drop]
    perturbed_theory = Theory(
        facts=set(instance.D_minus.facts),
        rules=perturbed_rules,
        superiority=dict(instance.D_minus.superiority),
    )
    space_minus = DerivationSpace(perturbed_theory)

    strength_fn = derivation_strength_reward(instance.D_minus)
    novelty_fn  = novelty_reward(instance.D_minus)
    reward_fn = composite_reward(
        rewards={"strength": strength_fn, "novelty": novelty_fn},
        weights={"strength": 0.7, "novelty": 0.3},
    )

    cfg = MCTSConfig(max_iterations=n_mcts_iter,
                     exploration_constant=math.sqrt(2),
                     seed=seed)

    p_wins = c_wins = draws = 0
    p_rob = p_grd = p_cre = 0.0
    c_rob = c_grd = c_cre = 0.0
    depths = []
    t0 = time.time()

    for r in range(n_rounds):
        mcts_p = MCTS(space_full,  cfg, reward_fn)
        mcts_c = MCTS(space_minus, cfg, reward_fn)

        init_state_p = DerivationState.initial(instance.D_minus)
        init_state_c = DerivationState.initial(perturbed_theory)
        result_p = mcts_p.search(init_state_p)
        result_c = mcts_c.search(init_state_c)

        depths.append(result_p.visits)
        depths.append(result_c.visits)

        # Use best child q_value (quality of best found action)
        def best_q(root) -> float:
            if not root.children:
                return 0.0
            return root.most_visited_child().q_value

        def best_novelty(root, base_preds: set) -> float:
            if not root.children:
                return 0.0
            action = root.most_visited_child().action
            if action is None:
                return 0.0
            lit = str(getattr(action, 'derived_literal', action))
            return 1.0 if lit.split("(")[0] not in base_preds else 0.0

        base_preds = {lit.split("(")[0] for lit in instance.D_minus.facts}
        p_val = best_q(result_p)
        c_val = best_q(result_c)

        p_cre += best_novelty(result_p, base_preds)
        c_cre += best_novelty(result_c, base_preds)
        p_grd += p_val
        c_grd += c_val
        p_rob += 1.0 if p_val >= c_val else 0.0
        c_rob += 1.0 if c_val >= p_val else 0.0

        if p_val > c_val + 0.05:
            p_wins += 1
        elif c_val > p_val + 0.05:
            c_wins += 1
        else:
            draws += 1

    elapsed = time.time() - t0
    n = max(n_rounds, 1)
    return DebateResult(
        instance_id=getattr(instance, "id", "?"),
        domain=instance.metadata.get("domain", "?"),
        level=instance.level,
        proposer_wins=p_wins,
        challenger_wins=c_wins,
        draws=draws,
        rounds=n_rounds,
        proposer_robustness=p_rob / n,
        proposer_grounding=p_grd / n,
        proposer_creativity=p_cre / n,
        challenger_robustness=c_rob / n,
        challenger_grounding=c_grd / n,
        challenger_creativity=c_cre / n,
        mean_tree_depth=sum(depths) / len(depths) if depths else 0.0,
        elapsed_s=elapsed,
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def _build_theory(item: dict, domain: str):
    """Reconstruct Theory from instance JSON."""
    from blanc.core.theory import Theory, Rule, RuleType
    meta = item.get("metadata", {})
    facts = set(meta.get("facts", item.get("theory_facts", [])))
    rules = []
    for rule_str in meta.get("rules", []) + item.get("theory_rules", []):
        if isinstance(rule_str, dict):
            rules.append(Rule(
                head=rule_str.get("head", ""),
                body=tuple(rule_str.get("body", [])),
                rule_type=RuleType(rule_str.get("rule_type", "defeasible")),
                label=rule_str.get("label"),
            ))
            continue
        if ":" in rule_str and (" => " in rule_str or " ~> " in rule_str or " :- " in rule_str):
            label, rest = rule_str.split(":", 1)
            label, rest = label.strip(), rest.strip()
        else:
            label, rest = None, rule_str.strip()
        if " ~> " in rest:
            bp, hp = rest.split(" ~> ", 1); rt = RuleType.DEFEATER
        elif " => " in rest:
            bp, hp = rest.split(" => ", 1); rt = RuleType.DEFEASIBLE
        elif " :- " in rest:
            bp, hp = rest.split(" :- ", 1); rt = RuleType.STRICT
        else:
            rules.append(Rule(head=rest.strip(), body=(), rule_type=RuleType.STRICT, label=label)); continue
        body_atoms = tuple(b.strip() for b in bp.split(",") if b.strip())
        rules.append(Rule(head=hp.strip(), body=body_atoms, rule_type=rt, label=label))
    return Theory(facts=facts, rules=rules, superiority={})


def load_instances(max_per_domain: int) -> list[AbductiveInstance]:
    """Load L2 and L3 instances with proper theory reconstruction."""
    instances: list[AbductiveInstance] = []
    tier0 = ROOT / "instances"

    # L3 instances first (most interesting for debate, have full theory structure)
    l3_path = tier0 / "level3_instances.json"
    if l3_path.exists():
        with open(l3_path) as f:
            data = json.load(f)
        raw = data.get("instances", data) if isinstance(data, dict) else data
        for i, item in enumerate(raw[:max_per_domain]):
            theory = _build_theory(item, item.get("domain", "tier0"))
            inst = AbductiveInstance(
                D_minus=theory,
                target=item.get("anomaly", item.get("target", "")),
                candidates=item.get("candidates", []),
                gold=[item["gold"]] if "gold" in item else item.get("gold", []),
                level=3,
                metadata={"domain": item.get("domain", "tier0"),
                           "nov": item.get("nov", 0.0)},
            )
            inst.id = item.get("instance_id", f"l3-{i:04d}")
            instances.append(inst)

    # L2 instances per domain
    for domain in ("biology", "legal", "materials"):
        path = tier0 / f"{domain}_dev_instances.json"
        if not path.exists():
            continue
        with open(path) as f:
            data = json.load(f)
        raw = data.get("instances", data) if isinstance(data, dict) else data
        for i, item in enumerate(raw[:max_per_domain]):
            theory = _build_theory(item, domain)
            if not (theory.facts or theory.rules):
                continue
            inst = AbductiveInstance(
                D_minus=theory,
                target=item.get("target", ""),
                candidates=item.get("candidates", []),
                gold=item.get("gold", []),
                level=item.get("level", 2),
                metadata={"domain": domain},
            )
            inst.id = item.get("metadata", {}).get("instance_id", f"{domain}-{i:04d}")
            instances.append(inst)
    return instances


def main() -> int:
    parser = argparse.ArgumentParser(description="Adversarial debate pilot")
    parser.add_argument("--n-instances", type=int, default=15,
                        help="Max instances per domain")
    parser.add_argument("--n-rounds", type=int, default=3,
                        help="Debate rounds per instance")
    parser.add_argument("--n-mcts", type=int, default=50,
                        help="MCTS iterations per agent per round")
    parser.add_argument("--full", action="store_true",
                        help="Use 200 MCTS iterations (slower, higher quality)")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.full:
        args.n_mcts = 200

    print("=" * 70)
    print("Adversarial Defeasible Debate Pilot")
    print("=" * 70)
    print(f"MCTS iterations/agent/round: {args.n_mcts}")
    print(f"Rounds per instance        : {args.n_rounds}")
    print(f"Seed                       : {args.seed}")
    print()

    instances = load_instances(args.n_instances)
    if not instances:
        print("No instances loaded. Run the generation pipeline first.")
        return 1
    print(f"Loaded {len(instances)} instances across domains.")

    results: list[DebateResult] = []
    for inst in instances:
        try:
            r = run_single_debate(inst, args.n_rounds, args.n_mcts, args.seed)
            results.append(r)
            print(f"  {r.instance_id:<30} winner={r.winner():<12} "
                  f"P_rob={r.proposer_robustness:.2f} C_rob={r.challenger_robustness:.2f} "
                  f"P_cre={r.proposer_creativity:.2f}")
        except Exception as e:
            print(f"  {getattr(inst, 'id', '?'):<30} ERROR: {e}")

    if not results:
        print("No successful debates.")
        return 1

    # Aggregate by domain
    by_domain: dict[str, list[DebateResult]] = {}
    for r in results:
        by_domain.setdefault(r.domain, []).append(r)

    print("\n" + "=" * 70)
    print(f"{'Domain':<15} {'N':>5} {'P_wins%':>9} {'C_wins%':>9} {'Draws%':>8} "
          f"{'P_Rob':>7} {'P_Grd':>7} {'P_Cre':>7}")
    print("-" * 70)
    for domain, rs in sorted(by_domain.items()):
        n = len(rs) * args.n_rounds
        p_w = sum(r.proposer_wins for r in rs) / n * 100
        c_w = sum(r.challenger_wins for r in rs) / n * 100
        d_w = sum(r.draws for r in rs) / n * 100
        p_rob = sum(r.proposer_robustness for r in rs) / len(rs)
        p_grd = sum(r.proposer_grounding for r in rs) / len(rs)
        p_cre = sum(r.proposer_creativity for r in rs) / len(rs)
        print(f"  {domain:<13} {len(rs):>5} {p_w:>8.1f}% {c_w:>8.1f}% {d_w:>7.1f}% "
              f"{p_rob:>7.2f} {p_grd:>7.2f} {p_cre:>7.2f}")

    # Save
    out = ROOT / "experiments/results" / f"debate_pilot_{int(time.time())}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in results], f, indent=2)
    print(f"\nResults saved to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
