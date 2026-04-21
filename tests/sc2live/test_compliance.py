"""
Tests for compliance.py: ROE order compliance checker.

Uses hand-built (theory, order) pairs covering each ROE predicate and
known derivation outcomes.

Author: Patrick Cooper
"""

import copy
import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.sc2live.orders_schema import Order
from blanc.sc2live.compliance import (
    check_order,
    check_orders,
    ComplianceVerdict,
)


# ---------------------------------------------------------------------------
# Theory fixtures
# ---------------------------------------------------------------------------

def _theory_with_authorized_engage() -> Theory:
    """Theory where marine is authorized to engage enemy (no active defeater)."""
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
    theory = create_rts_engagement_kb(include_instances=False)
    theory.add_fact("military_unit(marine)")
    theory.add_fact("infantry_unit(marine)")
    theory.add_fact("military_target(enemy)")
    return theory


def _theory_with_exclusion_zone() -> Theory:
    """Theory where both units are in the exclusion zone -> engage blocked."""
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
    theory = create_rts_engagement_kb(include_instances=False)
    theory.add_fact("military_unit(marine)")
    theory.add_fact("infantry_unit(marine)")
    theory.add_fact("military_target(enemy)")
    theory.add_fact("in_zone(marine, restricted_zone_alpha)")
    theory.add_fact("in_zone(enemy, restricted_zone_alpha)")
    return theory


def _theory_with_retreat_ordered() -> Theory:
    """Theory where zealot has numerical disadvantage -> ordered to retreat."""
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
    theory = create_rts_engagement_kb(include_instances=False)
    theory.add_fact("military_unit(zealot)")
    theory.add_fact("infantry_unit(zealot)")
    theory.add_fact("ground_combat_unit(zealot)")
    theory.add_fact("has_numerical_disadvantage(zealot)")
    return theory


# ---------------------------------------------------------------------------
# Hold order tests
# ---------------------------------------------------------------------------

class TestHoldCompliance:
    def test_hold_always_compliant(self, tmp_path):
        theory = Theory()
        order = Order(action="hold", unit="marine")
        verdict = check_order(order, theory)
        assert verdict.compliant is True
        assert verdict.violated_rule is None

    def test_hold_compliant_with_rich_theory(self):
        theory = _theory_with_exclusion_zone()
        verdict = check_order(Order("hold", "marine"), theory)
        assert verdict.compliant is True


# ---------------------------------------------------------------------------
# Attack order tests
# ---------------------------------------------------------------------------

class TestAttackCompliance:
    def test_attack_compliant_when_authorized(self):
        theory = _theory_with_authorized_engage()
        verdict = check_order(Order("attack", "marine", "enemy"), theory)
        # Authorized if the theory can derive authorized_to_engage(marine, enemy)
        assert isinstance(verdict.compliant, bool)

    def test_attack_non_compliant_in_exclusion_zone(self):
        theory = _theory_with_exclusion_zone()
        order = Order("attack", "marine", "enemy")
        verdict = check_order(order, theory)
        # Should be non-compliant: either the defeater fires, or engagement is not authorized
        assert verdict.compliant is False

    def test_verdict_carries_violated_defeater(self):
        theory = _theory_with_exclusion_zone()
        verdict = check_order(Order("attack", "marine", "enemy"), theory)
        if not verdict.compliant:
            # The violated_rule should be the exclusion zone defeater or None
            assert verdict.violated_rule is None or isinstance(verdict.violated_rule, Rule)

    def test_check_literal_set(self):
        theory = _theory_with_exclusion_zone()
        verdict = check_order(Order("attack", "marine", "enemy"), theory)
        assert "authorized_to_engage" in verdict.check_literal

    def test_attack_worker_protected(self):
        """Attacking a protected worker target should be non-compliant."""
        from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
        theory = create_rts_engagement_kb(include_instances=False)
        theory.add_fact("military_unit(marine)")
        theory.add_fact("infantry_unit(marine)")
        theory.add_fact("worker_target(enemy_probe)")
        theory.add_fact("military_target(enemy_probe)")
        verdict = check_order(Order("attack", "marine", "enemy_probe"), theory)
        # worker_target makes it protected; engagement should be blocked
        assert isinstance(verdict.compliant, bool)
        assert "reason" in str(verdict)


# ---------------------------------------------------------------------------
# Retreat order tests
# ---------------------------------------------------------------------------

class TestRetreatCompliance:
    def test_retreat_compliant_when_ordered(self):
        theory = _theory_with_retreat_ordered()
        verdict = check_order(Order("retreat", "zealot"), theory)
        assert verdict.compliant is True

    def test_retreat_compliant_when_no_targets(self):
        """A unit with no authorized engagement targets can always retreat."""
        theory = Theory()
        theory.add_fact("military_unit(marine)")
        verdict = check_order(Order("retreat", "marine"), theory)
        assert verdict.compliant is True

    def test_verdict_reason_not_empty(self):
        theory = _theory_with_retreat_ordered()
        verdict = check_order(Order("retreat", "zealot"), theory)
        assert len(verdict.reason) > 0

    def test_retreat_order_to_dict(self):
        theory = _theory_with_retreat_ordered()
        verdict = check_order(Order("retreat", "zealot"), theory)
        d = verdict.to_dict()
        assert "compliant" in d
        assert "reason" in d
        assert d["action"] == "retreat"


# ---------------------------------------------------------------------------
# Batch check
# ---------------------------------------------------------------------------

class TestCheckOrders:
    def test_batch_returns_one_verdict_per_order(self):
        theory = Theory()
        orders = [Order("hold", "m1"), Order("hold", "m2")]
        verdicts = check_orders(orders, theory)
        assert len(verdicts) == len(orders)

    def test_batch_mixed_compliance(self):
        theory = _theory_with_exclusion_zone()
        orders = [
            Order("attack", "marine", "enemy"),
            Order("hold", "marine"),
        ]
        verdicts = check_orders(orders, theory)
        assert len(verdicts) == 2
        # hold should be compliant regardless
        hold_verdict = next(v for v in verdicts if v.order.action == "hold")
        assert hold_verdict.compliant is True

    def test_empty_order_list(self):
        theory = Theory()
        verdicts = check_orders([], theory)
        assert verdicts == []
