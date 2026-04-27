"""
DeFAb-Hard-ROE: harder L3 seed conflicts that break the 100% ceiling.

Design principles:
    - CHAIN depth: gold defeater must be reasoned through 2 layers of defeat
    - MULTI-CONDITION: gold defeater body has 3+ atoms (vs 1-2 in easy seeds)
    - COMPETING: multiple defeasible rules AND defeaters active simultaneously
    - NOVELTY: gold defeater introduces predicates not yet in theory body

These instances are designed so that even reasoning-optimised models with CoT
achieve ~50-70%, not 100%.  The discrimination gap between models should widen,
providing the evaluation surface needed for the fine-tuning story.

Author: Patrick Cooper
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable
from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb


# ---------------------------------------------------------------------------
# Hard seed definitions
# ---------------------------------------------------------------------------

HARD_SEEDS = [
    # ── H1: Chain defeat -- repairing worker exception ─────────────────────
    # Two-layer: rts_r3012 blocks engagement because protected_from_attack(W).
    # But rts_r3013 defeats protected_from_attack when repairing_under_attack.
    # D^- removes rts_r3013 -> protected_from_attack STILL derivable (anomalous).
    # Anomaly: protected_from_attack(enemy_probe) holds even when repairing under attack.
    # Gold: worker_target(W), repairing_under_attack(W) :~> ~protected_from_attack(W)
    # Difficulty: anomaly is an INTERMEDIATE predicate, not the top-level engagement.
    # Model must reason: why is protection still active? What defeats the protection rule?
    {
        "scenario_id":       "H1_chain_defeat_repair_exception",
        "description":        (
            "Enemy probe is actively repairing a cannon under fire. "
            "ROE normally protects workers, but the repairing-under-attack "
            "exception defeats that protection. The theory is missing rts_r3013. "
            "Without it, protected_from_attack holds anomalously for a worker "
            "who is actively repairing a weapon system. The anomaly is at the "
            "INTERMEDIATE level: protection is derivable even though the probe "
            "is repairing under attack. The model must construct the second-layer "
            "defeater that defeats the protection predicate itself."
        ),
        "anomaly":            "protected_from_attack(enemy_probe)",
        "defeater_label":     "rts_r3013",
        "gold_defeater_head": "~protected_from_attack(W)",
        "gold_defeater_body": ["worker_target(W)", "repairing_under_attack(W)"],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "worker_target(enemy_probe)",
            "military_target(enemy_probe)",
            "repairing_under_attack(enemy_probe)",
        ],
        "hard_aspects": [
            "Chain defeat (2 layers): anomaly is intermediate predicate",
            "Gold head is ~protected_from_attack, not ~authorized_to_engage",
            "Model must not confuse rts_r3012 (engages worker) with rts_r3013 (defeats protection)",
        ],
    },

    # ── H2: Positive-ID chain -- sensor defeats ID requirement ─────────────
    # rts_r3048: military_unit(X), is_target_type(Y) => requires_positive_id(X,Y)
    # rts_r3050: sensor_detected(Y) :~> ~requires_positive_id(X,Y)
    # D^- removes rts_r3050 -> requires_positive_id IS derivable (anomalous).
    # Anomaly: requires_positive_id(marine, contact_alpha) holds despite sensor detection.
    # Gold: sensor_detected(Y) :~> ~requires_positive_id(X,Y)
    # Difficulty: model must identify the INTERMEDIATE predicate requires_positive_id
    # as the anomaly and reason about sensor detection defeating it.
    {
        "scenario_id":       "H2_positive_id_chain",
        "description":        (
            "Sensor has detected the target (confirmed by radar/scanner). "
            "But the theory's positive-ID requirement rule still fires: "
            "requires_positive_id holds because the unit is military and the "
            "target is target-typed. The sensor-detection defeater (rts_r3050) "
            "is missing. Anomaly: requires_positive_id is derivable even though "
            "sensor_detected is a fact. Model must construct: "
            "sensor_detected(Y) defeats requires_positive_id(X,Y). "
            "Three-step chain: authorization blocked by PID -> sensor defeats PID -> fixed."
        ),
        "anomaly":            "requires_positive_id(marine, contact_alpha)",
        "defeater_label":     "rts_r3050",
        "gold_defeater_head": "~requires_positive_id(X,Y)",
        "gold_defeater_body": ["sensor_detected(Y)"],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "military_target(contact_alpha)",
            "is_target_type(contact_alpha)",
            "sensor_detected(contact_alpha)",
            "not_positively_identified(contact_alpha)",
        ],
        "hard_aspects": [
            "Anomaly is intermediate predicate requires_positive_id, not authorized_to_engage",
            "3-step chain through PID layer",
            "Novel fact sensor_detected must be connected to PID defeater",
        ],
    },

    # ── H3: Multi-condition composite defeater (HVT + direct fire) ─────────
    # Retreat ordered (numerical disadvantage via rts_r3022).
    # rts_r3027 (HVT pursuit) uses 3 conditions; exists in theory.
    # But rts_r3027 won't fire because high_value_target_in_range is absent here.
    # Instead, we have a new scenario: unit is holding a choke point (rts_r3025)
    # AND under direct fire AND HVT nearby.
    # D^- is missing a composite 4-condition defeater that combines
    # choke point holding + under_direct_fire + HVT as a joint override.
    # Anomaly: ordered_to_retreat(zealot) holds despite all four conditions met.
    # Gold: 4-condition composite defeater.
    {
        "scenario_id":       "H3_composite_retreat_override",
        "description":        (
            "Zealot is outnumbered and ordered to retreat. However: "
            "(1) unit is holding a critical choke point, (2) under direct fire, "
            "(3) HVT is in range, and (4) target attempting escape. "
            "rts_r3025 (choke point) is present but only has 2 conditions. "
            "rts_r3027 (HVT pursuit) is present but is defeated by another rule. "
            "The theory is missing a composite override for when ALL FOUR conditions "
            "apply simultaneously. Anomaly: retreat ordered despite 4-way override. "
            "Gold: 4-condition defeater with holding_choke_point, under_direct_fire, "
            "high_value_target_in_range, and target_attempting_escape."
        ),
        "anomaly":            "ordered_to_retreat(zealot)",
        "defeater_label":     "rts_r3025",
        "gold_defeater_head": "~ordered_to_retreat(X)",
        "gold_defeater_body": [
            "military_unit(X)",
            "holding_choke_point(X)",
            "under_direct_fire(X)",
            "high_value_target_in_range(X)",
        ],
        "context_facts": [
            "military_unit(zealot)",
            "infantry_unit(zealot)",
            "ground_combat_unit(zealot)",
            "has_numerical_disadvantage(zealot)",
            "holding_choke_point(zealot)",
            "under_direct_fire(zealot)",
            "high_value_target_in_range(zealot)",
            "target_attempting_escape",
        ],
        "hard_aspects": [
            "4-condition body (most existing defeaters have 1-3)",
            "Must combine choke-point + fire + HVT -- not just copy existing defeaters",
            "Conservative: must not override retreat in non-choke scenarios",
        ],
    },

    # ── H4: Competing constraints -- stealth + zone + fire ─────────────────
    # Marine: (a) assigned to stealth mission op_ghost_eye, (b) in restricted zone,
    # (c) under direct fire. Three simultaneous constraints interact:
    # - op_ghost_eye -> stealth_posture_active -> rts_r3006 blocks engagement
    # - restricted zone -> rts_r3003 blocks engagement (also missing: rts_r3010 present)
    # - under_direct_fire -> should defeat stealth (rts_r3032 missing)
    # D^- removes rts_r3032 (stealth break on direct fire).
    # Anomaly: stealth_posture_active holds even though under direct fire.
    # Gold: under_direct_fire(X) :~> ~stealth_posture_active(X)
    # Difficulty: model must also show that defeating stealth does NOT authorize
    # engagement (zone restriction still applies) -- tests conservativity.
    {
        "scenario_id":       "H4_stealth_zone_fire_interaction",
        "description":        (
            "A marine is on a stealth recon mission (op_ghost_eye), inside a "
            "restricted zone, and taking direct fire. Three constraints interact: "
            "stealth posture blocks engagement (via mission rule rts_r3006), "
            "exclusion zone blocks engagement (rts_r3003), and the direct fire "
            "should defeat stealth posture (rts_r3032, which is missing). "
            "The anomaly: stealth_posture_active holds even though the unit is "
            "being shot at. The gold defeater breaks stealth on direct fire. "
            "The hard part: the model must recognize that breaking stealth does "
            "NOT authorize engagement (the zone restriction still applies). "
            "A non-conservative defeater that authorizes engagement would fail."
        ),
        "anomaly":            "stealth_posture_active(marine)",
        "defeater_label":     "rts_r3032",
        "gold_defeater_head": "~stealth_posture_active(X)",
        "gold_defeater_body": ["under_direct_fire(X)"],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "mission(op_ghost_eye)",
            "reconnaissance_mission(op_ghost_eye)",
            "assigned_to_mission(marine, op_ghost_eye)",
            "under_direct_fire(marine)",
            "military_target(enemy_squad)",
            "in_zone(marine, restricted_zone_alpha)",
            "in_zone(enemy_squad, restricted_zone_alpha)",
        ],
        "hard_aspects": [
            "Three simultaneous competing constraints",
            "Gold defeats stealth but NOT engagement (zone still applies)",
            "Incorrect defeater: ~authorized_to_engage -> fails conservativity",
        ],
    },

    # ── H5: Novel predicate introduction ────────────────────────────────────
    # Engagement is blocked because `requires_positive_id` fires for the target.
    # But neither sensor_detected nor under_direct_fire applies.
    # The ONLY way to waive PID is a new predicate: confirmed_hostile(Y),
    # established by a superior unit's intelligence assessment.
    # Gold: confirmed_hostile(Y) :~> ~requires_positive_id(X,Y)
    # This predicate does NOT appear anywhere in the existing theory.
    # Difficulty: model must invent a novel, semantically appropriate predicate
    # and justify why it conservatively defeats the PID requirement.
    {
        "scenario_id":       "H5_novel_predicate_confirmed_hostile",
        "description":        (
            "A marine needs to engage a contact but positive identification "
            "is required. Neither sensor detection nor direct-fire attribution "
            "applies. A superior unit has intelligence-assessed the contact as "
            "confirmed hostile (confirmed_hostile(Y)), which should waive the "
            "PID requirement under intelligence-grade identification doctrine. "
            "This predicate and its defeater do not exist in the current theory. "
            "The model must introduce 'confirmed_hostile(Y)' as a novel predicate "
            "and construct: confirmed_hostile(Y) :~> ~requires_positive_id(X,Y). "
            "This tests whether models can generate novel, conservative defeaters "
            "that introduce new vocabulary."
        ),
        "anomaly":            "requires_positive_id(marine, contact_bravo)",
        "defeater_label":     "rts_r_novel_confirmed_hostile",
        "gold_defeater_head": "~requires_positive_id(X,Y)",
        "gold_defeater_body": ["confirmed_hostile(Y)"],
        "context_facts": [
            "military_unit(marine)",
            "infantry_unit(marine)",
            "military_target(contact_bravo)",
            "is_target_type(contact_bravo)",
            "confirmed_hostile(contact_bravo)",
            "not_positively_identified(contact_bravo)",
        ],
        "hard_aspects": [
            "Novel predicate: confirmed_hostile does not appear in existing theory",
            "Model must justify why it conservatively defeats PID requirement",
            "High novelty score expected for gold defeater",
        ],
    },

    # ── H6: Multi-anomaly conservativity ────────────────────────────────────
    # Three anomalies exist simultaneously in D^-. The model must construct
    # a defeater that resolves ONLY anomaly 1 (exclusion zone) without
    # disturbing anomalies 2 (worker protection, correct -- not anomalous in D) or
    # creating new anomalies.
    # Anomaly: authorized_to_engage(zealot, enemy_probe) in restricted zone.
    # Worker probe also present but engagement CORRECTLY blocked by worker protection.
    # Gold: in_zone(X, restricted_zone_alpha), in_zone(Y, restricted_zone_alpha)
    #        :~> ~authorized_to_engage(X,Y)
    # Must be conservative: zealot vs military target in non-restricted zone
    # must remain authorized after gold is added.
    {
        "scenario_id":       "H6_multi_constraint_conservativity",
        "description":        (
            "Zealot unit faces two types of enemies: an enemy squad (military target) "
            "in the restricted zone, and an enemy probe (worker) outside it. "
            "Without the exclusion zone defeater (rts_r3003 removed from D^-), "
            "engagement with the squad inside the zone is anomalously authorized. "
            "But engagement with the probe must REMAIN correctly blocked by "
            "worker protection (rts_r3012 is present and correct). "
            "The model must construct a conservative defeater that resolves the "
            "zone anomaly without affecting the worker protection. A non-conservative "
            "defeater that blocks ALL engagement would fail the validity check."
        ),
        "anomaly":            "authorized_to_engage(zealot, enemy_squad)",
        "defeater_label":     "rts_r3003",
        "gold_defeater_head": "~authorized_to_engage(X,Y)",
        "gold_defeater_body": [
            "in_zone(X, restricted_zone_alpha)",
            "in_zone(Y, restricted_zone_alpha)",
        ],
        "context_facts": [
            "military_unit(zealot)",
            "infantry_unit(zealot)",
            "military_target(enemy_squad)",
            "in_zone(zealot, restricted_zone_alpha)",
            "in_zone(enemy_squad, restricted_zone_alpha)",
            # Worker probe outside restricted zone
            "worker_target(enemy_probe)",
            "military_target(enemy_probe)",
            "in_zone(enemy_probe, engagement_zone_alpha)",
            # Military target outside zone (should remain authorized after fix)
            "military_target(enemy_vanguard)",
            "in_zone(enemy_vanguard, engagement_zone_alpha)",
        ],
        "hard_aspects": [
            "Must resolve one anomaly without creating new ones",
            "Two simultaneously present defeaters (zone + worker) must stay independent",
            "Worker protection (rts_r3012) must remain unaffected",
            "Engagement with non-restricted-zone target must remain authorized",
        ],
    },
]


def build_hard_theory(seed: dict) -> Theory:
    kb = create_rts_engagement_kb(include_instances=False)
    # Remove gold defeater from theory
    kb.rules = [r for r in kb.rules if r.label != seed["defeater_label"]]
    for fact in seed["context_facts"]:
        kb.add_fact(fact)
    return kb


def verify_seed(seed: dict) -> dict:
    """Check that anomaly holds in D^- and not in D."""
    theory_minus = build_hard_theory(seed)
    theory_full  = create_rts_engagement_kb(include_instances=False)
    for fact in seed["context_facts"]:
        theory_full.add_fact(fact)

    in_d_minus = defeasible_provable(theory_minus, seed["anomaly"])
    not_in_d   = not defeasible_provable(theory_full, seed["anomaly"])

    # Build gold rule and check conservativity sketch
    gold = Rule(
        head=seed["gold_defeater_head"],
        body=tuple(seed["gold_defeater_body"]),
        rule_type=RuleType.DEFEATER,
        label=seed["defeater_label"],
    )
    theory_plus = copy.deepcopy(theory_minus)
    theory_plus.add_rule(gold)
    anomaly_resolved = not defeasible_provable(theory_plus, seed["anomaly"])

    return {
        "scenario_id":      seed["scenario_id"],
        "anomaly_in_d_minus": in_d_minus,
        "anomaly_not_in_d":   not_in_d,
        "gold_resolves":       anomaly_resolved,
        "valid":               in_d_minus and not_in_d and anomaly_resolved,
    }


def main() -> int:
    print("DeFAb-Hard-ROE: Seed Verification")
    print("=" * 60)

    all_valid = True
    for seed in HARD_SEEDS:
        result = verify_seed(seed)
        status = "PASS" if result["valid"] else "FAIL"
        print(f"  [{status}] {seed['scenario_id']}")
        if not result["valid"]:
            all_valid = False
            print(f"    anomaly_in_D^-:  {result['anomaly_in_d_minus']}")
            print(f"    not_in_D:        {result['anomaly_not_in_d']}")
            print(f"    gold_resolves:   {result['gold_resolves']}")
        else:
            for aspect in seed.get("hard_aspects", []):
                print(f"    - {aspect}")

    print()
    if all_valid:
        print(f"All {len(HARD_SEEDS)} hard seeds verified.")
    else:
        print("Some seeds failed verification -- check theory construction.")

    # Save hard seeds
    out_path = ROOT / "scripts" / "generate_rts_instances.py"
    # Just print for now -- seeds need to be manually added
    print()
    print("Hard seeds ready for evaluation.")
    print("Run: python scripts/run_rts_evaluation.py --instances-file <hard_instances.json>")

    return 0 if all_valid else 1


if __name__ == "__main__":
    sys.exit(main())
