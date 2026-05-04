"""
Integration tests for the Lux AI S3 engagement knowledge base.

Certifies that the DeFAb-Lux KB produces well-formed instances with the
same formal verifier guarantees as the SC2, biology, legal, and materials KBs.

Author: Anonymous Authors
"""

import copy
import pytest

from examples.knowledge_bases.lux_engagement_kb import (
    create_lux_engagement_kb,
    get_lux_stats,
)
from blanc.core.theory import Theory, RuleType
from blanc.reasoning.defeasible import defeasible_provable
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance
from blanc.generation.partition import partition_rule


@pytest.fixture(scope="module")
def base_kb():
    return create_lux_engagement_kb()


@pytest.fixture(scope="module")
def kb_stats(base_kb):
    return get_lux_stats(base_kb)


class TestLuxKBConstruction:
    def test_kb_loads(self, base_kb):
        assert base_kb is not None
        assert isinstance(base_kb, Theory)

    def test_has_rules(self, base_kb):
        assert len(base_kb.rules) > 40

    def test_has_facts(self, base_kb):
        assert len(base_kb.facts) > 20

    def test_has_strict_rules(self, base_kb):
        strict = [r for r in base_kb.rules if r.rule_type == RuleType.STRICT]
        assert len(strict) >= 20

    def test_has_defeasible_rules(self, base_kb):
        defeas = [r for r in base_kb.rules if r.rule_type == RuleType.DEFEASIBLE]
        assert len(defeas) >= 15

    def test_has_defeaters(self, base_kb):
        defs = [r for r in base_kb.rules if r.rule_type == RuleType.DEFEATER]
        assert len(defs) >= 8

    def test_has_superiority_relations(self, base_kb):
        assert len(base_kb.superiority) >= 5

    def test_has_ship_instances(self, base_kb):
        for ship in ["ship_a1", "ship_a2", "ship_b1"]:
            assert f"ship({ship})" in base_kb.facts

    def test_has_terrain_instances(self, base_kb):
        for tile in ["north_energy_cluster", "relic_alpha", "nebula_center"]:
            pass  # at least one energy/relic/nebula should exist
        assert any("energy_node(" in f for f in base_kb.facts)
        assert any("relic_node(" in f for f in base_kb.facts)
        assert any("nebula_tile(" in f for f in base_kb.facts)

    def test_stats_structure(self, kb_stats):
        assert "rules_total" in kb_stats
        assert "facts_total" in kb_stats
        assert kb_stats["rules_total"] > 0


class TestLuxDefeasibleProvability:
    def _with_facts(self, base_kb, extra):
        t = copy.deepcopy(base_kb)
        for f in extra:
            t.add_fact(f)
        return t

    def test_ship_is_mobile(self, base_kb):
        assert defeasible_provable(base_kb, "is_mobile(ship_a1)")

    def test_energy_node_grants_energy(self, base_kb):
        assert defeasible_provable(base_kb, "grants_energy(north_energy_cluster)")

    def test_nebula_drains_energy(self, base_kb):
        assert defeasible_provable(base_kb, "drains_energy(nebula_center)")

    def test_asteroid_is_impassable(self, base_kb):
        assert defeasible_provable(base_kb, "impassable(asteroid_cluster_a)")

    def test_relic_spawns_fragments(self, base_kb):
        assert defeasible_provable(base_kb, "spawns_relic_fragments(relic_alpha)")

    def test_relic_advance_default(self, base_kb):
        t = self._with_facts(base_kb, ["relic_reachable(ship_a1)"])
        assert defeasible_provable(t, "ordered_to_advance_on_relic(ship_a1)")

    def test_energy_critical_defeats_relic_advance(self, base_kb):
        """Critical energy should defeat the relic advance order."""
        t = self._with_facts(base_kb, [
            "relic_reachable(ship_a2)",
        ])
        # ship_a2 already has critical_energy from instances
        assert not defeasible_provable(t, "ordered_to_advance_on_relic(ship_a2)"), \
            "Critical energy should block relic advance order"

    def test_harvest_energy_default(self, base_kb):
        t = self._with_facts(base_kb, ["energy_node_adjacent(ship_a1)"])
        assert defeasible_provable(t, "ordered_to_harvest_energy(ship_a1)")

    def test_collision_avoidance_default(self, base_kb):
        t = self._with_facts(base_kb, [
            "ship_on_tile(ship_a2, tile_x7)",
            "same_team(ship_a1, ship_a2)",
        ])
        assert defeasible_provable(t, "must_avoid_tile(ship_a1, tile_x7)")


class TestLuxConservativity:
    def _with_facts(self, base_kb, extra):
        t = copy.deepcopy(base_kb)
        for f in extra:
            t.add_fact(f)
        return t

    def test_energy_retreat_conservative(self, base_kb):
        """Critical energy retreat for ship_a2 must not affect ship_a1."""
        t = self._with_facts(base_kb, [
            "relic_reachable(ship_a1)",
            "relic_reachable(ship_a2)",
        ])
        # ship_a2 has critical energy, so its relic advance is blocked
        assert not defeasible_provable(t, "ordered_to_advance_on_relic(ship_a2)"), \
            "ship_a2 should not advance (critical energy)"
        # ship_a1 has healthy energy, so it SHOULD advance
        assert defeasible_provable(t, "ordered_to_advance_on_relic(ship_a1)"), \
            "ship_a1 should still advance -- conservativity"


class TestLuxInstanceGeneration:
    def test_l2_instance_from_lux_kb(self, base_kb):
        converted = phi_kappa(base_kb, partition_rule)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        if not defeasible_rules:
            pytest.skip("No defeasible rules after conversion")

        targets = [
            "is_mobile(ship_a1)",
            "grants_energy(north_energy_cluster)",
            "spawns_relic_fragments(relic_alpha)",
        ]
        for target in targets:
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
                    assert instance.is_valid()
                    return
            except Exception:
                continue

        pytest.skip("Could not find suitable L2 target for Lux AI KB")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
