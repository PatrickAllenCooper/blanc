"""
Generate DeFAb instances from the RTS engagement knowledge base.

This script demonstrates applying the DeFAb defeasible abduction pipeline to
rules of engagement (ROE) modeled in a StarCraft II-style RTS environment --
the proxy environment suggested by Thomas C. Lee (Lockheed Martin, April 2026)
for testing ROE-aware AI without access to controlled operational materials.

Produces Level 1, Level 2, and Level 3 instances:

    Level 1: A critical observation (fact) is missing. The model must
             identify, e.g., "hostile_act_detected_near(marine, enemy_marine_squad)"
             as the missing fact that allows engagement.

    Level 2: A critical ROE rule is missing from the theory. The model must
             reconstruct, e.g., the self-defense override rule that authorizes
             engagement when under direct fire.

    Level 3 (primary target): Given a theory with an anomaly -- where the ROE
             framework produces an unexpected engagement outcome -- the model
             must construct a conservative defeater that resolves the anomaly.
             This directly tests ROE exception reasoning: the same cognitive
             task as determining whether a self-defense exception overrides a
             mission constraint.

Usage:
    python scripts/generate_rts_instances.py
    python scripts/generate_rts_instances.py --output data/rts_instances.json
    python scripts/generate_rts_instances.py --level 3 --max-instances 50

Author: Patrick Cooper
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.rts_engagement_kb import (
    create_rts_engagement_kb,
    get_rts_stats,
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
# Each entry describes a scenario where the ROE framework generates an anomaly:
# the theory without the defeater produces an unexpected result, and the model
# must construct the defeater that resolves it conservatively.
#
# This directly encodes the Newport Handbook's structure:
#   default ROE rule (produces anomaly when context changes)
#   -> defeater (exception that resolves the anomaly)
#   -> superiority relation (ensures the exception is authoritative)
#
# Format: {
#   "scenario_id": str,
#   "description": str,         -- English description of the ROE scenario
#   "anomaly": str,             -- The fact that is anomalous given D^-
#   "defeater_label": str,      -- Label of the defeater to remove for D^-
#   "gold_defeater_head": str,  -- Head of the gold defeater
#   "gold_defeater_body": list, -- Body of the gold defeater
#   "context_facts": list,      -- Additional ground facts needed for scenario
# }

ROE_LEVEL3_SEEDS = [
    {
        "scenario_id": "self_defense_exclusion_zone",
        "description": (
            "A marine unit is under direct fire inside restricted_zone_alpha. "
            "The ROE prohibit engagement in the exclusion zone by default. "
            "But the self-defense override -- ~authorized_to_engage defeated "
            "by under_direct_fire -- is missing from the theory. "
            "Anomaly: the unit cannot be authorized to respond. "
            "The model must construct the self-defense defeater that overrides "
            "the exclusion zone prohibition."
        ),
        "anomaly": "authorized_to_engage(marine, enemy_marine_squad)",
        "defeater_label": "rts_r3008",
        "gold_defeater_head": "authorized_to_engage(X,Y)",
        "gold_defeater_body": [
            "military_unit(X)", "under_direct_fire(X)", "hostile_unit(Y)"
        ],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "military_target(enemy_marine_squad)",
            "in_zone(marine, restricted_zone_alpha)",
            "in_zone(enemy_marine_squad, restricted_zone_alpha)",
            "under_direct_fire(marine)",
            "hostile_unit(enemy_marine_squad)",
        ],
    },
    {
        "scenario_id": "worker_exception_repair",
        "description": (
            "Enemy workers (probes) are actively repairing a damaged cannon "
            "that is firing on allied forces. "
            "The default ROE protect workers as noncombatants. "
            "The repair-under-attack defeater is missing from the theory. "
            "Anomaly: the theory concludes workers are protected even while "
            "actively sustaining an attacking structure. "
            "The model must construct the exception: workers repairing a "
            "structure under attack lose protected status."
        ),
        "anomaly": "~protected_from_attack(enemy_probe_line)",
        "defeater_label": "rts_r3017",
        "gold_defeater_head": "~protected_from_attack(W)",
        "gold_defeater_body": [
            "worker_target(W)", "repairing_under_attack(W)"
        ],
        "context_facts": [
            "unit(enemy_probe_line)",
            "worker_unit(enemy_probe_line)",
            "worker_target(enemy_probe_line)",
            "repairing_under_attack(enemy_probe_line)",
        ],
    },
    {
        "scenario_id": "all_in_rush_retreat_override",
        "description": (
            "Allied forces are numerically outnumbered and the default ROE "
            "order retreat. However, the enemy is executing an all-in rush "
            "on the main base. The all-in rush defeater on the retreat rule "
            "is missing from the theory. "
            "Anomaly: the theory still orders retreat even though base "
            "abandonment would mean mission failure. "
            "The model must construct the exception: all-in rush detected "
            "means the force must hold regardless of numerical disadvantage."
        ),
        "anomaly": "~ordered_to_retreat(zealot)",
        "defeater_label": "rts_r3032",
        "gold_defeater_head": "~ordered_to_retreat(X)",
        "gold_defeater_body": [
            "military_unit(X)", "all_in_rush_detected"
        ],
        "context_facts": [
            "military_unit(zealot)",
            "ground_combat_unit(zealot)",
            "infantry_unit(zealot)",
            "has_numerical_disadvantage(zealot)",
            "all_in_rush_detected",
        ],
    },
    {
        "scenario_id": "stealth_break_direct_fire",
        "description": (
            "A ghost unit is on a reconnaissance mission with stealth posture "
            "active. It is then taken under direct fire by enemy units. "
            "The stealth-break defeater (triggered by direct fire) is missing "
            "from the theory. "
            "Anomaly: the theory continues to require stealth posture even "
            "though the unit is under attack and cannot evade while cloaked. "
            "The model must construct the exception: direct fire on the unit "
            "suspends the stealth posture obligation."
        ),
        "anomaly": "~stealth_posture_active(marine)",
        "defeater_label": "rts_r3036",
        "gold_defeater_head": "~stealth_posture_active(X)",
        "gold_defeater_body": ["under_direct_fire(X)"],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "mission(op_ghost_eye)",
            "reconnaissance_mission(op_ghost_eye)",
            "assigned_to_mission(marine, op_ghost_eye)",
            "under_direct_fire(marine)",
        ],
    },
    {
        "scenario_id": "hvt_retreat_override",
        "description": (
            "A Viking unit is ordered to retreat due to numerical disadvantage. "
            "However, a high-value enemy mothership is within attack range and "
            "attempting to escape. The HVT-escape defeater on the retreat "
            "order is missing from the theory. "
            "Anomaly: the unit retreats even though engaging the HVT would "
            "secure a decisive strategic objective. "
            "The model must construct the exception: a high-value target in "
            "range and fleeing overrides the retreat order."
        ),
        "anomaly": "~ordered_to_retreat(viking)",
        "defeater_label": "rts_r3033",
        "gold_defeater_head": "~ordered_to_retreat(X)",
        "gold_defeater_body": [
            "military_unit(X)", "high_value_target_in_range(X)",
            "target_attempting_escape"
        ],
        "context_facts": [
            "military_unit(viking)",
            "air_combat_unit(viking)",
            "fighter_unit(viking)",
            "has_numerical_disadvantage(viking)",
            "high_value_target_in_range(viking)",
            "target_attempting_escape",
        ],
    },
    {
        "scenario_id": "proportionality_critical_threat",
        "description": (
            "A siege tank is operating near a civilian mining area and is "
            "subject to the minimum-force requirement (no splash damage in "
            "civilian proximity). A critical threat -- an enemy all-in rush "
            "army -- is attacking. "
            "The critical-threat proportionality override is missing from the "
            "theory. "
            "Anomaly: the siege tank cannot use splash damage even as the "
            "base is being overrun. "
            "The model must construct the exception: critical threat requiring "
            "immediate response overrides the minimum-force requirement."
        ),
        "anomaly": "~must_use_minimum_force(siege_tank)",
        "defeater_label": "rts_r3026",
        "gold_defeater_head": "~must_use_minimum_force(X)",
        "gold_defeater_body": [
            "critical_threat(T)", "requires_immediate_response(T)"
        ],
        "context_facts": [
            "military_unit(siege_tank)",
            "armored_unit(siege_tank)",
            "has_splash_damage(siege_tank)",
            "civilian_proximity(siege_tank)",
            "threat(enemy_all_in_rush)",
            "critical_threat(enemy_all_in_rush)",
        ],
    },
]


def generate_from_rts_kb(
    base_theory,
    level: int = 2,
    max_per_partition: int = 20,
):
    """Generate Level 1 or Level 2 instances using partition strategies."""

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
    print(f"KB: {len(base_theory.rules)} rules, {len(base_theory.facts)} facts")

    # Collect derivable targets -- ROE conclusions
    roe_targets = []
    for fact in list(base_theory.facts)[:50]:
        if defeasible_provable(base_theory, fact):
            roe_targets.append(fact)
    # Also probe ROE predicates directly
    roe_probe_predicates = [
        "authorized_to_engage", "cleared_to_engage", "ordered_to_retreat",
        "stealth_posture_active", "priority_target", "mission_accomplished",
    ]
    for pred in roe_probe_predicates:
        for fact in base_theory.facts:
            if pred in fact:
                if defeasible_provable(base_theory, fact):
                    roe_targets.append(fact)
    roe_targets = list(dict.fromkeys(roe_targets))  # deduplicate
    print(f"Derivable ROE targets: {len(roe_targets)}")

    for i, (strat_name, partition_fn) in enumerate(strategies, 1):
        print(f"\nStrategy {i}/{len(strategies)}: {strat_name}")
        converted = phi_kappa(base_theory, partition_fn)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        print(f"  Converted: {len(converted.facts)} facts, "
              f"{len(defeasible_rules)} defeasible rules")

        count = 0
        for target in roe_targets:
            if count >= max_per_partition:
                break
            try:
                if not defeasible_provable(converted, target):
                    continue
                critical = full_theory_criticality(converted, target)
                if level == 1:
                    critical_facts = [e for e in critical
                                      if isinstance(e, str)]
                    if critical_facts:
                        instance = generate_level1_instance(
                            converted, target, critical_facts[0],
                            k_distractors=5,
                            distractor_strategy="syntactic",
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
                            k_distractors=5,
                            distractor_strategy="syntactic",
                        )
                        all_instances.append(instance)
                        count += 1
            except Exception:
                continue

        print(f"  Generated: {count} Level {level} instances")
        partition_results[strat_name] = {"instances": count}

    return all_instances, partition_results


def generate_level3_from_seeds(theory):
    """Generate Level 3 instances from the hand-crafted ROE seed conflicts."""
    instances = []
    print(f"\nGenerating Level 3 from {len(ROE_LEVEL3_SEEDS)} ROE seed conflicts...")

    for seed in ROE_LEVEL3_SEEDS:
        print(f"\n  Scenario: {seed['scenario_id']}")
        try:
            # Add context facts
            import copy
            working_theory = copy.deepcopy(theory)
            for fact in seed["context_facts"]:
                working_theory.add_fact(fact)

            # Find the defeater rule to remove (D^- = theory without defeater)
            defeater_rule = None
            for rule in working_theory.rules:
                if rule.label == seed["defeater_label"]:
                    defeater_rule = rule
                    break

            if defeater_rule is None:
                print(f"    WARNING: defeater label {seed['defeater_label']} "
                      f"not found, skipping")
                continue

            instance = generate_level3_instance(
                theory=working_theory,
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
        description="Generate DeFAb instances from the RTS engagement KB"
    )
    parser.add_argument(
        "--level", type=int, choices=[1, 2, 3, 0], default=0,
        help="Level to generate (0 = all levels, default)"
    )
    parser.add_argument(
        "--max-instances", type=int, default=20,
        help="Max instances per partition strategy for L1/L2 (default: 20)"
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output JSON file path (default: rts_engagement_instances.json)"
    )
    parser.add_argument(
        "--stats-only", action="store_true",
        help="Print KB statistics and exit without generating instances"
    )
    args = parser.parse_args()

    print("=" * 70)
    print("RTS ENGAGEMENT KB -- DeFAb INSTANCE GENERATION")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load KB and print stats
    print("\nLoading RTS engagement knowledge base...")
    kb = create_rts_engagement_kb()
    stats = get_rts_stats(kb)

    print(f"\nKB Statistics:")
    print(f"  Domain        : {stats['domain']}")
    print(f"  Total rules   : {stats['rules_total']}")
    print(f"  Total facts   : {stats['facts_total']}")
    print(f"  Strict rules  : {stats['strict_rules']}")
    print(f"  Defeasible    : {stats['defeasible_rules']}")
    print(f"  Defeaters     : {stats['defeater_rules']}")
    print(f"  ROE behavioral: {stats['roe_behavioral']}")
    print(f"  Max dep. depth: {stats['max_dependency_depth']}")
    print(f"  Sources       : {', '.join(stats['sources'])}")

    if args.stats_only:
        return 0

    all_instances = []
    generation_log = {
        "domain": "rts_engagement",
        "kb_stats": stats,
        "generation_date": datetime.now().isoformat(),
        "levels": {},
    }

    # ── Level 1 ──────────────────────────────────────────────────────────────
    if args.level in (0, 1):
        print("\n" + "-" * 70)
        print("LEVEL 1 -- Missing observation (critical fact)")
        print("-" * 70)
        l1_instances, l1_results = generate_from_rts_kb(
            kb, level=1, max_per_partition=args.max_instances
        )
        all_instances.extend(l1_instances)
        generation_log["levels"]["level1"] = {
            "count": len(l1_instances),
            "partition_results": l1_results,
        }
        print(f"\nTotal Level 1 instances: {len(l1_instances)}")

    # ── Level 2 ──────────────────────────────────────────────────────────────
    if args.level in (0, 2):
        print("\n" + "-" * 70)
        print("LEVEL 2 -- Missing ROE rule (critical defeasible rule)")
        print("-" * 70)
        l2_instances, l2_results = generate_from_rts_kb(
            kb, level=2, max_per_partition=args.max_instances
        )
        all_instances.extend(l2_instances)
        generation_log["levels"]["level2"] = {
            "count": len(l2_instances),
            "partition_results": l2_results,
        }
        print(f"\nTotal Level 2 instances: {len(l2_instances)}")

    # ── Level 3 ──────────────────────────────────────────────────────────────
    if args.level in (0, 3):
        print("\n" + "-" * 70)
        print("LEVEL 3 -- ROE exception construction (defeater abduction)")
        print("-" * 70)
        print(
            "\nThis level tests the model's ability to construct a conservative "
            "exception to a default ROE rule -- the same cognitive task as "
            "determining when a self-defense override or escalation clause "
            "applies under the Newport ROE Handbook framework."
        )
        l3_instances = generate_level3_from_seeds(kb)
        all_instances.extend(l3_instances)
        generation_log["levels"]["level3"] = {
            "count": len(l3_instances),
            "seeds": [s["scenario_id"] for s in ROE_LEVEL3_SEEDS],
        }
        print(f"\nTotal Level 3 instances: {len(l3_instances)}")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("GENERATION SUMMARY")
    print("=" * 70)
    total = len(all_instances)
    print(f"Total instances generated: {total}")
    for level_key, info in generation_log["levels"].items():
        print(f"  {level_key}: {info['count']}")

    if total == 0:
        print("\nNo instances generated. The KB may need more ground facts or "
              "different partition strategies.")
        return 1

    # ── Save output ────────────────────────────────────────────────────────────
    output_path = args.output or "rts_engagement_instances.json"
    output = {
        "metadata": generation_log,
        "instances": [inst.to_dict() for inst in all_instances],
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {total} instances to: {output_path}")

    print("\n" + "=" * 70)
    print("RTS ENGAGEMENT INSTANCE GENERATION COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
