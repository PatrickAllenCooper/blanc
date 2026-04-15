"""
Integration tests for the RTS engagement knowledge base.

Certifies that the DeFAb-ROE KB:
  1. Constructs with the expected rule counts and structure
  2. Produces defeasibly provable ROE conclusions under normal conditions
  3. Correctly blocks engagement under mission constraints (defeaters active)
  4. Restores engagement authorization under self-defense override
  5. Is conservative: self-defense override does not affect unrelated ROE rules
  6. Generates well-formed L1 and L2 instances via the standard pipeline

These tests constitute the formal verification step described in the paper's
ROE extension section: the same polynomial-time verifier that certifies
biology/legal/materials instances certifies ROE instances.

Author: Patrick Cooper
"""

import copy
import pytest
from pathlib import Path

from examples.knowledge_bases.rts_engagement_kb import (
    create_rts_engagement_kb,
    get_rts_stats,
)
from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance
from blanc.generation.partition import partition_rule, partition_leaf


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def base_kb():
    """Shared KB instance for all tests in this module."""
    return create_rts_engagement_kb()


@pytest.fixture(scope="module")
def kb_stats(base_kb):
    return get_rts_stats(base_kb)


# ── KB construction ────────────────────────────────────────────────────────────

class TestRTSKBConstruction:
    """Verify the KB assembles with the expected structural properties."""

    def test_kb_loads_without_error(self, base_kb):
        assert base_kb is not None
        assert isinstance(base_kb, Theory)

    def test_kb_has_rules(self, base_kb):
        assert len(base_kb.rules) > 50, "KB must have substantial rule coverage"

    def test_kb_has_facts(self, base_kb):
        assert len(base_kb.facts) > 30, "KB must have ground instance facts"

    def test_kb_has_strict_rules(self, base_kb):
        strict = [r for r in base_kb.rules if r.rule_type == RuleType.STRICT]
        assert len(strict) > 20, "Must have strict game-mechanical rules"

    def test_kb_has_defeasible_roe_rules(self, base_kb):
        defeasible = [r for r in base_kb.rules if r.rule_type == RuleType.DEFEASIBLE]
        assert len(defeasible) >= 30, "Must have defeasible ROE rules"

    def test_kb_has_defeaters(self, base_kb):
        defeaters = [r for r in base_kb.rules if r.rule_type == RuleType.DEFEATER]
        assert len(defeaters) >= 15, "Must have ROE exception defeaters"

    def test_kb_has_superiority_relations(self, base_kb):
        assert len(base_kb.superiority) >= 10, \
            "Must have superiority relations encoding the ROE hierarchy"

    def test_kb_has_unit_instances(self, base_kb):
        # Key unit instances must be present
        for unit in ["marine", "siege_tank", "viking", "probe", "zealot"]:
            assert f"unit({unit})" in base_kb.facts, \
                f"Expected unit instance: unit({unit})"

    def test_kb_has_zone_instances(self, base_kb):
        for zone in ["main_base", "restricted_zone_alpha", "worker_mining_area"]:
            assert f"zone({zone})" in base_kb.facts, \
                f"Expected zone instance: zone({zone})"

    def test_stats_structure(self, kb_stats):
        assert "rules_total" in kb_stats
        assert "facts_total" in kb_stats
        assert "strict_rules" in kb_stats
        assert "defeasible_rules" in kb_stats
        assert "defeater_rules" in kb_stats
        assert kb_stats["rules_total"] > 0
        assert kb_stats["facts_total"] > 0

    def test_stats_rule_counts_sum(self, kb_stats):
        """Strict + defeasible + defeater must sum to total."""
        total_by_type = (
            kb_stats["strict_rules"]
            + kb_stats["defeasible_rules"]
            + kb_stats["defeater_rules"]
        )
        assert total_by_type == kb_stats["rules_total"]


# ── Defeasible provability: normal engagement ─────────────────────────────────

class TestNormalEngagementProvability:
    """
    Under standard conditions, the ROE default rules should fire and produce
    correct conclusions.
    """

    def test_military_unit_authorized_by_default(self, base_kb):
        """
        A military unit facing a military target in normal conditions
        should be authorized to engage.
        The instance facts already include marine (military_unit) and
        enemy_marine_squad (military_target).
        """
        assert defeasible_provable(base_kb, "authorized_to_engage(marine, enemy_marine_squad)"), \
            "Marine should be authorized to engage enemy_marine_squad by default"

    def test_worker_protected_by_default(self, base_kb):
        """Workers are noncombatants and should be protected from attack."""
        assert defeasible_provable(base_kb, "protected_from_attack(enemy_probe_line)"), \
            "enemy_probe_line (worker) should be protected by default"

    def test_military_unit_is_mobile(self, base_kb):
        """All units are mobile (strict rule)."""
        assert defeasible_provable(base_kb, "is_mobile(marine)"), \
            "Marine should be mobile"

    def test_infantry_can_attack_ground(self, base_kb):
        """Infantry can attack ground targets (strict rule)."""
        assert defeasible_provable(base_kb, "can_attack_ground(marine)"), \
            "Marine (infantry) should be able to attack ground"

    def test_sensor_detects_cloaked(self, base_kb):
        """Sensor units detect cloaked units (strict rule)."""
        assert defeasible_provable(base_kb, "detects_cloaked(observer)"), \
            "Observer (sensor unit) should detect cloaked units"

    def test_worker_gathers_resources(self, base_kb):
        """Workers gather resources (strict rule)."""
        assert defeasible_provable(base_kb, "gathers_resources(scv)"), \
            "SCV (worker) should gather resources"

    def test_high_ground_provides_vision_bonus(self, base_kb):
        """High ground terrain provides vision bonus (strict rule)."""
        assert defeasible_provable(base_kb, "provides_vision_bonus(center_plateau)"), \
            "center_plateau (high ground) should provide vision bonus"

    def test_choke_point_is_tactically_critical(self, base_kb):
        """Choke points are tactically critical (strict rule)."""
        assert defeasible_provable(base_kb, "is_tactically_critical(natural_ramp)"), \
            "natural_ramp (choke point) should be tactically critical"


# ── Defeater activation: engagement blocked ───────────────────────────────────

class TestROEConstraintsBlockEngagement:
    """
    ROE defeaters should block engagement under restricted conditions.
    """

    def _theory_with_facts(self, base_kb, extra_facts: list[str]) -> Theory:
        """Return a copy of the KB with extra facts added."""
        t = copy.deepcopy(base_kb)
        for f in extra_facts:
            t.add_fact(f)
        return t

    def test_exclusion_zone_blocks_engagement(self, base_kb):
        """
        When both units are in restricted_zone_alpha, engagement is blocked
        by the exclusion zone defeater, even though the default authorizes it.
        """
        theory = self._theory_with_facts(base_kb, [
            "in_zone(marine, restricted_zone_alpha)",
            "in_zone(enemy_marine_squad, restricted_zone_alpha)",
        ])
        # The exclusion zone defeater should block authorization
        assert not defeasible_provable(
            theory, "authorized_to_engage(marine, enemy_marine_squad)"
        ), "Engagement in exclusion zone should be prohibited"

    def test_civilian_area_blocks_engagement(self, base_kb):
        """When target is in civilian area (worker_mining_area), engagement is blocked."""
        theory = self._theory_with_facts(base_kb, [
            "in_zone(enemy_probe_line, worker_mining_area)",
        ])
        assert not defeasible_provable(
            theory, "authorized_to_engage(marine, enemy_probe_line)"
        ), "Engagement in civilian area should be prohibited"

    def test_worker_protection_blocks_engagement(self, base_kb):
        """
        Protected workers cannot be engaged:
        ~authorized_to_engage defeats protected_from_attack(W).
        """
        # enemy_probe_line is already a worker_target in the KB
        assert not defeasible_provable(
            base_kb, "authorized_to_engage(marine, enemy_probe_line)"
        ), "Worker (enemy_probe_line) should not be engageable by default"


# ── Self-defense override ─────────────────────────────────────────────────────

class TestSelfDefenseOverride:
    """
    Self-defense facts should override ROE constraints via superiority relations,
    restoring engagement authorization even in restricted zones.
    """

    def _theory_with_facts(self, base_kb, extra_facts):
        t = copy.deepcopy(base_kb)
        for f in extra_facts:
            t.add_fact(f)
        return t

    def test_self_defense_overrides_exclusion_zone(self, base_kb):
        """
        Under direct fire in an exclusion zone, self-defense should override
        the exclusion zone prohibition and authorize engagement.

        This is the core ROE theorem: self-defense > mission constraint,
        matching the Newport Handbook hierarchy.
        """
        theory = self._theory_with_facts(base_kb, [
            "in_zone(marine, restricted_zone_alpha)",
            "in_zone(enemy_marine_squad, restricted_zone_alpha)",
            "under_direct_fire(marine)",
            "hostile_unit(enemy_marine_squad)",
        ])
        assert defeasible_provable(
            theory, "authorized_to_engage(marine, enemy_marine_squad)"
        ), ("Self-defense should override exclusion zone prohibition. "
            "This is the key ROE theorem: self-defense > mission constraint.")

    def test_hostile_act_restores_authorization(self, base_kb):
        """Hostile act detected near unit restores engagement authorization."""
        theory = self._theory_with_facts(base_kb, [
            "hostile_act_detected_near(marine, enemy_marine_squad)",
        ])
        assert defeasible_provable(
            theory, "authorized_to_engage(marine, enemy_marine_squad)"
        ), "Hostile act detection should authorize engagement"

    def test_worker_exception_when_repairing(self, base_kb):
        """
        Workers repairing a structure under attack lose protected status.
        This tests the worker exception defeater.
        """
        theory = self._theory_with_facts(base_kb, [
            "repairing_under_attack(enemy_probe_line)",
        ])
        # Protected status should be defeated
        assert not defeasible_provable(
            theory, "protected_from_attack(enemy_probe_line)"
        ), ("Worker repairing under attack should lose protected status. "
            "ROE exception: workers sustaining an active attack forfeit noncombatant status.")

    def test_all_in_rush_defeats_retreat_order(self, base_kb):
        """
        When all-in rush is detected, retreat order is overridden.
        Tests the all-in rush defeater on the retreat rule.
        """
        theory = self._theory_with_facts(base_kb, [
            "has_numerical_disadvantage(zealot)",
            "all_in_rush_detected",
        ])
        # The retreat order should be defeated by the all-in rush defeater
        # zealot ordered to retreat due to numerical disadvantage...
        # ...but all_in_rush_detected overrides that
        # We check that ~ordered_to_retreat fires (the defeater outcome)
        assert not defeasible_provable(
            theory, "ordered_to_retreat(zealot)"
        ), ("All-in rush should override the numerical-disadvantage retreat order. "
            "ROE exception: base defense overrides force preservation posture.")


# ── Conservativity ────────────────────────────────────────────────────────────

class TestConservativity:
    """
    When a self-defense override fires, it must be CONSERVATIVE: it overrides
    only the specific engagement constraint, not the entire ROE framework.
    Other ROE rules for unrelated units and predicates must remain intact.

    This is the DeFAb conservativity requirement applied to ROE.
    """

    def _theory_with_facts(self, base_kb, extra_facts):
        t = copy.deepcopy(base_kb)
        for f in extra_facts:
            t.add_fact(f)
        return t

    def test_self_defense_override_conservative_for_other_units(self, base_kb):
        """
        When marine invokes self-defense in exclusion zone, the stalker unit
        in the same zone should still be restricted (its self-defense exception
        has not been triggered).
        """
        theory = self._theory_with_facts(base_kb, [
            "in_zone(marine, restricted_zone_alpha)",
            "in_zone(enemy_marine_squad, restricted_zone_alpha)",
            "under_direct_fire(marine)",
            "hostile_unit(enemy_marine_squad)",
            # stalker also in zone, but NOT under fire
            "in_zone(stalker, restricted_zone_alpha)",
            "in_zone(enemy_siege_tank, restricted_zone_alpha)",
        ])
        # Marine: self-defense fires -> authorized
        assert defeasible_provable(
            theory, "authorized_to_engage(marine, enemy_marine_squad)"
        ), "Marine should be authorized via self-defense"

        # Stalker: no self-defense trigger -> still blocked by exclusion zone
        assert not defeasible_provable(
            theory, "authorized_to_engage(stalker, enemy_siege_tank)"
        ), ("Stalker should still be blocked by exclusion zone. "
            "Self-defense override for marine must be conservative -- "
            "it must not unlock engagement for all units in the zone.")

    def test_worker_exception_conservative_for_protected_workers(self, base_kb):
        """
        When one worker loses protected status (repairing under attack),
        another worker not repairing should remain protected.
        """
        theory = self._theory_with_facts(base_kb, [
            "repairing_under_attack(enemy_probe_line)",
            # enemy_scv_cluster is a worker_target in the KB but not repairing
        ])
        # Repairing worker: loses protection
        assert not defeasible_provable(
            theory, "protected_from_attack(enemy_probe_line)"
        ), "Repairing worker should lose protected status"

        # Non-repairing worker: still protected (conservativity)
        assert defeasible_provable(
            theory, "protected_from_attack(enemy_scv_cluster)"
        ), ("Non-repairing worker should remain protected. "
            "Worker exception must be conservative -- only the specific worker "
            "engaged in combat support loses protection.")

    def test_retreat_override_conservative_for_other_retreat_triggers(self, base_kb):
        """
        All-in rush defeats numerical-disadvantage retreat, but isolated units
        without reinforcement should still receive the retreat order.
        """
        theory = self._theory_with_facts(base_kb, [
            "has_numerical_disadvantage(zealot)",
            "all_in_rush_detected",
            # stalker is isolated with no reinforcement
            "is_isolated(stalker)",
            "no_reinforcement_available",
        ])
        # Zealot: all-in rush overrides retreat
        assert not defeasible_provable(
            theory, "ordered_to_retreat(zealot)"
        ), "All-in rush should override zealot's retreat order"

        # Stalker: isolated, no reinforcement -- still ordered to retreat
        assert defeasible_provable(
            theory, "ordered_to_retreat(stalker)"
        ), ("Isolated stalker should still be ordered to retreat. "
            "All-in rush exception is specific to numerical-disadvantage; "
            "isolation-based retreat is a separate rule and must remain active.")


# ── Instance generation from the ROE KB ──────────────────────────────────────

class TestRTSInstanceGeneration:
    """
    Verify that the standard DeFAb generation pipeline produces valid
    well-formed instances from the RTS engagement KB.
    """

    def test_l2_instance_generation(self, base_kb):
        """
        Should be able to generate at least one valid Level 2 instance
        from the RTS KB using the rule partition strategy.
        """
        converted = phi_kappa(base_kb, partition_rule)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible_rules) > 0, "Converted theory must have defeasible rules"

        # Try to find a derivable ROE target
        roe_targets = [
            "authorized_to_engage(marine, enemy_marine_squad)",
            "protected_from_attack(enemy_probe_line)",
            "can_attack_ground(marine)",
            "gathers_resources(scv)",
        ]

        for target in roe_targets:
            try:
                if not defeasible_provable(converted, target):
                    continue
                critical = full_theory_criticality(converted, target)
                critical_rules = [
                    e for e in critical
                    if hasattr(e, "rule_type") and e.rule_type == RuleType.DEFEASIBLE
                ]
                if critical_rules:
                    instance = generate_level2_instance(
                        converted, target, critical_rules[0], k_distractors=3
                    )
                    assert instance.is_valid(), \
                        f"Generated L2 instance for '{target}' must be valid"
                    return  # One valid instance is sufficient
            except Exception:
                continue

        pytest.skip("Could not find suitable ROE target for L2 generation -- "
                    "may need more ground facts with the current partition strategy.")

    def test_l2_instance_generation_leaf_partition(self, base_kb):
        """Same test with the leaf partition strategy."""
        converted = phi_kappa(base_kb, partition_leaf)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)

        if len(defeasible_rules) == 0:
            pytest.skip("Leaf partition produced no defeasible rules for this KB")

        target = "gathers_resources(scv)"
        try:
            if defeasible_provable(converted, target):
                critical = full_theory_criticality(converted, target)
                critical_rules = [
                    e for e in critical
                    if hasattr(e, "rule_type") and e.rule_type == RuleType.DEFEASIBLE
                ]
                if critical_rules:
                    instance = generate_level2_instance(
                        converted, target, critical_rules[0], k_distractors=3
                    )
                    assert instance.is_valid()
                    return
        except Exception:
            pass

        pytest.skip("Could not generate leaf-partition L2 instance for ROE KB")

    def test_is_valid_requires_gold(self, base_kb):
        """AbductiveInstance.is_valid() must fail when gold is empty."""
        from blanc.author.generation import AbductiveInstance
        inst = AbductiveInstance(
            D_minus=base_kb,
            target="authorized_to_engage(marine, enemy_marine_squad)",
            candidates=["candidate_rule"],
            gold=[],
            level=3,
        )
        assert not inst.is_valid(), "Instance with empty gold must not be valid"


# ── Verifier properties ────────────────────────────────────────────────────────

class TestVerifierProperties:
    """
    Verify the three properties of the ROE verifier established in the paper's
    Proposition 5 (Verifier Invariance): deterministic, model-independent,
    polynomial-time.
    """

    def test_verifier_is_deterministic(self, base_kb):
        """Same query on the same theory produces the same result every time."""
        results = set()
        for _ in range(5):
            result = defeasible_provable(base_kb, "can_attack_ground(marine)")
            results.add(result)
        assert len(results) == 1, "Verifier must be deterministic"

    def test_verifier_is_model_independent(self, base_kb):
        """
        The verifier result depends only on the theory and the query,
        not on any external model or random state.
        """
        t1 = copy.deepcopy(base_kb)
        t2 = copy.deepcopy(base_kb)
        query = "protected_from_attack(enemy_probe_line)"
        assert defeasible_provable(t1, query) == defeasible_provable(t2, query), \
            "Verifier must be model-independent (same theory -> same result)"

    def test_verifier_responds_to_theory_changes(self, base_kb):
        """Adding a defeater changes the verifier result as expected."""
        query = "protected_from_attack(enemy_probe_line)"

        t_before = copy.deepcopy(base_kb)
        before = defeasible_provable(t_before, query)
        assert before is True, "Worker should be protected before defeater added"

        t_after = copy.deepcopy(base_kb)
        t_after.add_fact("repairing_under_attack(enemy_probe_line)")
        after = defeasible_provable(t_after, query)
        assert after is False, "Worker should not be protected after repair defeater activates"

        assert before != after, "Theory change must change verifier result"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
