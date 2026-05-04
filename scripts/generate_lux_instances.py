"""
Generate DeFAb instances from the Lux AI Season 3 engagement KB.

Lux AI S3 is a NeurIPS 2024 competition game with a clean sci-fi aesthetic.
Web visualizer: https://s3vis.lux-ai.org

The game mechanics map onto defeasible ROE precisely:
    - Strict rules: unit physics, collision, energy gain/loss
    - Defeasible rules: relic pursuit, energy harvesting, stealth posture
    - Defeaters: self-preservation overrides, win-condition push, evasion
    - Superiority: self-preservation > scoring > resource efficiency

This mirrors the SC2 ROE KB structure, enabling cross-environment
comparison of defeasible reasoning capability.

Level 3 seeds encode the six most visually compelling Lux AI S3 scenarios
where a behavioral exception must be constructed:

    1. energy_critical_retreat_override
       Ship is adjacent to relic and about to score, but energy is critical.
       The win-condition exception overrides the self-preservation retreat.

    2. stealth_break_laser_incoming
       Ship is maintaining stealth posture in nebula, but laser is incoming.
       The laser-evasion defeater overrides the nebula-stay order.

    3. kamikaze_collision_override
       Ship must avoid ally tile by default. In final match with score tie,
       collision with enemy is a valid (but extreme) tactic.

    4. relic_in_nebula_entry
       Ship must avoid nebulae by default. But the target relic is inside
       a nebula. The relic-access defeater overrides nebula avoidance.

    5. probe_suspended_by_combat
       Ship should probe energy node yield in match 1. But an adjacent
       enemy overrides the probing order.

    6. contested_relic_final_push
       Ship would normally avoid a contested relic (enemy numerical advantage).
       In the final match with score deficit, the team must push anyway.

Author: Anonymous Authors
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from examples.knowledge_bases.lux_engagement_kb import (
    create_lux_engagement_kb,
    get_lux_stats,
)
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import (
    generate_level1_instance,
    generate_level2_instance,
    generate_level3_instance,
)
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    partition_depth,
    partition_random,
    compute_dependency_depths,
)
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


# ── Level 3 seed conflicts ────────────────────────────────────────────────────

LUX_LEVEL3_SEEDS = [
    {
        "scenario_id": "energy_critical_retreat_override",
        "description": (
            "Ship A2 is adjacent to relic_alpha and about to score a point. "
            "But it has critical energy and the default retreat rule fires. "
            "The win-condition defeater -- which overrides retreat when the ship "
            "is adjacent to a relic in the final match with score tied -- is "
            "missing from the theory. "
            "Anomaly: the ship retreats and loses the scoring opportunity. "
            "The model must construct the exception: final match, score tied, "
            "adjacent to relic -> do not retreat."
        ),
        "anomaly": "~ordered_to_retreat_to_energy(ship_a2)",
        "defeater_label": "lux_r5024",
        "gold_defeater_head": "~ordered_to_retreat_to_energy(X)",
        "gold_defeater_body": [
            "ship(X)", "critical_energy(X)", "ship_adjacent_to_relic(X)",
            "score_tied", "final_match(M)", "current_match_phase(X,M)"
        ],
        "context_facts": [
            "ship(ship_a2)", "critical_energy(ship_a2)",
            "ship_adjacent_to_relic(ship_a2)",
            "match_phase(match_phase_5)", "final_match(match_phase_5)",
            "current_match_phase(ship_a2, match_phase_5)",
            "score_tied",
        ],
    },
    {
        "scenario_id": "stealth_break_laser_incoming",
        "description": (
            "Ship A3 is maintaining stealth posture (staying visible is default "
            "when pursuing a relic). The ship is currently in pursuit. "
            "But a laser is incoming -- the immediate threat defeater that "
            "breaks stealth posture is missing from the theory. "
            "Anomaly: the ship stays visible and is destroyed by the laser. "
            "The model must construct: laser incoming -> stop maintaining visibility."
        ),
        "anomaly": "~maintain_visibility(ship_a3)",
        "defeater_label": "lux_r5033",
        "gold_defeater_head": "~maintain_visibility(X)",
        "gold_defeater_body": ["ship(X)", "laser_incoming(X)"],
        "context_facts": [
            "ship(ship_a3)", "pursuing_relic(ship_a3)",
            "laser_incoming(ship_a3)",
        ],
    },
    {
        "scenario_id": "relic_inside_nebula",
        "description": (
            "Ship A1 must pursue relic_beta, which is inside nebula_center. "
            "The default rule prohibits entering nebulae. "
            "The relic-in-nebula defeater is missing. "
            "Anomaly: the ship cannot advance on the relic because it must "
            "avoid the nebula. "
            "The model must construct the exception: if the nearest relic is "
            "inside a nebula and the ship has healthy energy, the nebula "
            "avoidance rule is overridden."
        ),
        "anomaly": "~must_avoid_nebula(ship_a1)",
        "defeater_label": "lux_r5021",
        "gold_defeater_head": "~must_avoid_nebula(X)",
        "gold_defeater_body": [
            "ship(X)", "relic_in_nebula(R)", "nearest_relic_is(X,R)",
            "healthy_energy(X)"
        ],
        "context_facts": [
            "ship(ship_a1)", "healthy_energy(ship_a1)",
            "relic_in_nebula(relic_beta)",
            "nearest_relic_is(ship_a1, relic_beta)",
            "relic_node(relic_beta)", "nebula_tile(nebula_center)",
        ],
    },
    {
        "scenario_id": "probe_suspended_combat",
        "description": (
            "Ship A1 is in the first match (early_match) and should probe "
            "the north_energy_cluster to learn its energy yield -- the default "
            "meta-learning rule. An adjacent enemy ship (ship_b1) is present. "
            "The combat-emergency defeater on probing is missing. "
            "Anomaly: the ship probes the energy node while the enemy is "
            "adjacent and gets destroyed. "
            "The model must construct: adjacent enemy -> do not probe."
        ),
        "anomaly": "~should_probe_energy_node(ship_a1, north_energy_cluster)",
        "defeater_label": "lux_r5038",
        "gold_defeater_head": "~should_probe_energy_node(X,N)",
        "gold_defeater_body": ["ship(X)", "adjacent_enemy(X)"],
        "context_facts": [
            "ship(ship_a1)",
            "match_phase(match_phase_1)", "early_match(match_phase_1)",
            "current_match_phase(ship_a1, match_phase_1)",
            "energy_node_yield_unknown(north_energy_cluster)",
            "energy_node(north_energy_cluster)",
            "adjacent_enemy(ship_a1)",
        ],
    },
    {
        "scenario_id": "laser_engagement_blocked_path",
        "description": (
            "Ship A1 wants to fire its laser at ship_b1, which is blocking "
            "its path to relic_alpha. By default, a ship not in attack posture "
            "is prohibited from firing. "
            "The blocking-relic-access defeater is missing. "
            "Anomaly: the ship cannot clear the path to the relic. "
            "The model must construct: enemy blocking relic access and ship "
            "has healthy energy -> the no-fire prohibition is overridden."
        ),
        "anomaly": "~prohibited_from_firing(ship_a1, ship_b1)",
        "defeater_label": "lux_r5034",
        "gold_defeater_head": "~prohibited_from_firing(X,Y)",
        "gold_defeater_body": [
            "ship(X)", "ship(Y)", "is_hostile(X,Y)",
            "blocking_relic_access(Y,X)", "healthy_energy(X)"
        ],
        "context_facts": [
            "ship(ship_a1)", "ship(ship_b1)",
            "opposing_team(ship_a1, ship_b1)",
            "is_hostile(ship_a1, ship_b1)",
            "not_in_attack_posture(ship_a1)",
            "blocking_relic_access(ship_b1, ship_a1)",
            "healthy_energy(ship_a1)",
        ],
    },
    {
        "scenario_id": "contested_relic_final_push",
        "description": (
            "Ship A1 would normally avoid relic_alpha because it is contested "
            "and the enemy has numerical advantage there. "
            "But this is the final match and team A has a score deficit. "
            "The final-match score-deficit defeater that overrides the "
            "'avoid contested relic' rule is missing. "
            "Anomaly: the ship avoids the contested relic and the team loses. "
            "The model must construct: final match + score deficit -> push "
            "the contested relic despite numerical disadvantage."
        ),
        "anomaly": "~ordered_to_advance_on_relic(ship_a1)",
        "defeater_label": "lux_r5004",
        "gold_defeater_head": "~ordered_to_advance_on_relic(X)",
        "gold_defeater_body": [
            "ship(X)", "contested_relic(R)", "nearest_relic_is(X,R)",
            "final_match(M)", "current_match_phase(X,M)", "score_deficit(X)"
        ],
        "context_facts": [
            "ship(ship_a1)", "relic_reachable(ship_a1)",
            "contested_relic(relic_alpha)",
            "nearest_relic_is(ship_a1, relic_alpha)",
            "enemy_has_numerical_advantage_at(relic_alpha)",
            "match_phase(match_phase_5)", "final_match(match_phase_5)",
            "current_match_phase(ship_a1, match_phase_5)",
            "score_deficit(ship_a1)",
        ],
    },
]


def generate_from_lux_kb(base_theory, level: int = 2, max_per_partition: int = 20):
    """Generate Level 1 or Level 2 instances from the Lux AI KB."""
    all_instances = []
    partition_results = {}

    strategies = [("leaf", partition_leaf), ("rule", partition_rule)]
    depths_map = compute_dependency_depths(base_theory)
    for k in [1, 2, 3]:
        strategies.append((f"depth_{k}", partition_depth(k, depths_map)))
    for delta_int in range(1, 7):
        delta = delta_int / 10.0
        strategies.append((f"rand_{delta:.1f}", partition_random(delta, seed=42)))

    print(f"\nPartition strategies: {len(strategies)}")
    print(f"Lux AI KB: {len(base_theory.rules)} rules, {len(base_theory.facts)} facts")

    # Collect derivable Lux AI targets
    lux_targets = []
    for fact in list(base_theory.facts)[:50]:
        if defeasible_provable(base_theory, fact):
            lux_targets.append(fact)

    lux_probe_predicates = [
        "ordered_to_advance_on_relic", "ordered_to_harvest_energy",
        "must_avoid_nebula", "cleared_to_score", "maintain_visibility",
    ]
    for pred in lux_probe_predicates:
        for fact in base_theory.facts:
            if pred in fact:
                try:
                    if defeasible_provable(base_theory, fact):
                        lux_targets.append(fact)
                except Exception:
                    pass

    lux_targets = list(dict.fromkeys(lux_targets))
    print(f"Derivable Lux AI targets: {len(lux_targets)}")

    for i, (strat_name, partition_fn) in enumerate(strategies, 1):
        print(f"\nStrategy {i}/{len(strategies)}: {strat_name}")
        try:
            converted = phi_kappa(base_theory, partition_fn)
        except Exception as e:
            print(f"  Partition failed: {e}")
            partition_results[strat_name] = {"instances": 0, "error": str(e)}
            continue

        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        print(f"  Converted: {len(converted.facts)} facts, "
              f"{len(defeasible_rules)} defeasible rules")

        count = 0
        for target in lux_targets:
            if count >= max_per_partition:
                break
            try:
                if not defeasible_provable(converted, target):
                    continue
                critical = full_theory_criticality(converted, target)
                if level == 1:
                    critical_facts = [e for e in critical if isinstance(e, str)]
                    if critical_facts:
                        instance = generate_level1_instance(
                            converted, target, critical_facts[0],
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        all_instances.append(instance)
                        count += 1
                elif level == 2:
                    critical_rules = [e for e in critical
                                      if hasattr(e, "rule_type")
                                      and e.rule_type == RuleType.DEFEASIBLE]
                    if critical_rules:
                        instance = generate_level2_instance(
                            converted, target, critical_rules[0],
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        all_instances.append(instance)
                        count += 1
            except Exception:
                continue

        print(f"  Generated: {count} Level {level} instances")
        partition_results[strat_name] = {"instances": count}

    return all_instances, partition_results


def generate_level3_from_seeds(theory):
    """Generate Level 3 instances from the Lux AI L3 seed conflicts."""
    import copy
    instances = []
    print(f"\nGenerating Level 3 from {len(LUX_LEVEL3_SEEDS)} Lux AI seed scenarios...")

    for seed in LUX_LEVEL3_SEEDS:
        print(f"\n  Scenario: {seed['scenario_id']}")
        try:
            working = copy.deepcopy(theory)
            for fact in seed["context_facts"]:
                working.add_fact(fact)

            defeater_rule = None
            for rule in working.rules:
                if rule.label == seed["defeater_label"]:
                    defeater_rule = rule
                    break

            if defeater_rule is None:
                print(f"    WARNING: defeater {seed['defeater_label']} not found")
                continue

            instance = generate_level3_instance(
                theory=working,
                anomaly=seed["anomaly"],
                defeater_rule=defeater_rule,
                k_distractors=5,
                distractor_strategy="syntactic",
            )
            if instance is not None:
                instances.append(instance)
                print(f"    OK: Level 3 instance generated")
            else:
                print(f"    SKIP: generate_level3_instance returned None")
        except Exception as e:
            print(f"    ERROR: {e}")
            continue

    print(f"\nLevel 3 instances generated: {len(instances)}")
    return instances


def main():
    parser = argparse.ArgumentParser(
        description="Generate DeFAb instances from the Lux AI S3 KB"
    )
    parser.add_argument("--level", type=int, choices=[1, 2, 3, 0], default=0,
                        help="Level to generate (0 = all, default)")
    parser.add_argument("--max-instances", type=int, default=20)
    parser.add_argument("--output", type=str, default=None)
    parser.add_argument("--stats-only", action="store_true")
    args = parser.parse_args()

    print("=" * 70)
    print("LUX AI S3 ENGAGEMENT KB -- DeFAb INSTANCE GENERATION")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Visual: https://s3vis.lux-ai.org")

    print("\nLoading Lux AI S3 engagement KB...")
    kb = create_lux_engagement_kb()
    stats = get_lux_stats(kb)

    print(f"\nKB Statistics:")
    print(f"  Domain        : {stats['domain']}")
    print(f"  Total rules   : {stats['rules_total']}")
    print(f"  Total facts   : {stats['facts_total']}")
    print(f"  Strict rules  : {stats['strict_rules']}")
    print(f"  Defeasible    : {stats['defeasible_rules']}")
    print(f"  Defeaters     : {stats['defeater_rules']}")
    print(f"  ROE hierarchy : {stats['roe_hierarchy']}")

    if args.stats_only:
        return 0

    all_instances = []
    generation_log = {
        "domain": "lux_ai_s3",
        "kb_stats": stats,
        "generation_date": datetime.now().isoformat(),
        "levels": {},
        "visual_source": "https://s3vis.lux-ai.org",
    }

    if args.level in (0, 1):
        print("\n" + "-" * 70)
        print("LEVEL 1 -- Missing observation (critical fact)")
        print("-" * 70)
        l1_instances, l1_results = generate_from_lux_kb(
            kb, level=1, max_per_partition=args.max_instances
        )
        all_instances.extend(l1_instances)
        generation_log["levels"]["level1"] = {
            "count": len(l1_instances),
            "partition_results": l1_results,
        }
        print(f"\nTotal Level 1 instances: {len(l1_instances)}")

    if args.level in (0, 2):
        print("\n" + "-" * 70)
        print("LEVEL 2 -- Missing behavioral rule")
        print("-" * 70)
        l2_instances, l2_results = generate_from_lux_kb(
            kb, level=2, max_per_partition=args.max_instances
        )
        all_instances.extend(l2_instances)
        generation_log["levels"]["level2"] = {
            "count": len(l2_instances),
            "partition_results": l2_results,
        }
        print(f"\nTotal Level 2 instances: {len(l2_instances)}")

    if args.level in (0, 3):
        print("\n" + "-" * 70)
        print("LEVEL 3 -- Lux AI behavioral exception construction")
        print("-" * 70)
        print(
            "\nLevel 3 tests whether the model can construct the exception that "
            "resolves an anomalous behavioral outcome -- for example, identifying "
            "that a ship should not retreat when adjacent to a relic in the final "
            "match with a score tie. This is the structural analog of ROE "
            "self-defense override in the SC2 engagement KB."
        )
        l3_instances = generate_level3_from_seeds(kb)
        all_instances.extend(l3_instances)
        generation_log["levels"]["level3"] = {
            "count": len(l3_instances),
            "seeds": [s["scenario_id"] for s in LUX_LEVEL3_SEEDS],
        }
        print(f"\nTotal Level 3 instances: {len(l3_instances)}")

    print("\n" + "=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)
    total = len(all_instances)
    print(f"Total instances: {total}")
    for level_key, info in generation_log["levels"].items():
        print(f"  {level_key}: {info['count']}")

    if total == 0:
        print("\nNo instances generated.")
        return 1

    output_path = args.output or str(ROOT / "instances" / "lux_engagement_instances.json")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    output = {
        "metadata": generation_log,
        "instances": [inst.to_dict() for inst in all_instances],
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {total} instances to: {output_path}")

    print("\n" + "=" * 70)
    print("LUX AI S3 INSTANCE GENERATION COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
