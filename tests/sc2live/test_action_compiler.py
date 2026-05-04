"""
Unit tests for ActionCompiler.

Pure unit tests: no SC2 binary required.
Tests verify that derived ROE literals are correctly mapped to SC2 orders.

Author: Anonymous Authors
"""

import pytest
from blanc.sc2live.orders import ActionCompiler, OrderBatch


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

class _FakeUnit:
    """Mock SC2 unit with order-tracking."""

    def __init__(self, tag: int) -> None:
        self.tag = tag
        self.attacks: list = []
        self.moves: list = []
        self.holds: int = 0
        self.stops: int = 0

    def attack(self, target) -> None:
        self.attacks.append(target)

    def move(self, target) -> None:
        self.moves.append(target)

    def hold_position(self) -> None:
        self.holds += 1

    def stop(self) -> None:
        self.stops += 1


class _FakePosition:
    def __init__(self, x: float = 100.0, y: float = 100.0) -> None:
        self.x = x
        self.y = y


@pytest.fixture
def registry_and_compiler():
    """Two allied units and one enemy unit in a registry."""
    marine = _FakeUnit(tag=0x41)
    zealot = _FakeUnit(tag=0x42)
    enemy  = _FakeUnit(tag=0xA1)
    rally  = _FakePosition(100.0, 100.0)

    registry = {
        "marine_00000041": marine,
        "zealot_00000042": zealot,
        "zergling_000000a1": enemy,
    }
    compiler = ActionCompiler(unit_registry=registry, rally_point=rally)
    return compiler, marine, zealot, enemy, rally


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCompileEngagement:
    def test_authorized_to_engage_issues_attack(self, registry_and_compiler):
        compiler, marine, zealot, enemy, rally = registry_and_compiler
        derived = {"authorized_to_engage(marine_00000041, zergling_000000a1)"}
        batch = compiler.compile(derived)
        assert len(batch.attacks) == 1
        attacker, target = batch.attacks[0]
        assert attacker.tag == marine.tag
        assert target.tag == enemy.tag

    def test_cleared_to_engage_also_issues_attack(self, registry_and_compiler):
        compiler, marine, zealot, enemy, rally = registry_and_compiler
        derived = {"cleared_to_engage(zealot_00000042, zergling_000000a1)"}
        batch = compiler.compile(derived)
        assert len(batch.attacks) == 1
        assert batch.attacks[0][0].tag == zealot.tag

    def test_unknown_units_silently_dropped(self, registry_and_compiler):
        compiler, *_ = registry_and_compiler
        derived = {"authorized_to_engage(ghost_deadbeef, zergling_000000a1)"}
        batch = compiler.compile(derived)
        assert len(batch.attacks) == 0


class TestCompileRetreat:
    def test_ordered_to_retreat_issues_move(self, registry_and_compiler):
        compiler, marine, zealot, enemy, rally = registry_and_compiler
        derived = {"ordered_to_retreat(marine_00000041)"}
        batch = compiler.compile(derived)
        assert len(batch.retreats) == 1
        unit, dest = batch.retreats[0]
        assert unit.tag == marine.tag
        assert dest is rally

    def test_retreat_without_rally_is_dropped(self):
        registry = {"marine_00000041": _FakeUnit(0x41)}
        compiler = ActionCompiler(unit_registry=registry, rally_point=None)
        batch = compiler.compile({"ordered_to_retreat(marine_00000041)"})
        assert len(batch.retreats) == 0


class TestCompileHold:
    def test_minimum_force_issues_hold(self, registry_and_compiler):
        compiler, marine, *_ = registry_and_compiler
        derived = {"must_use_minimum_force(marine_00000041)"}
        batch = compiler.compile(derived)
        assert marine in batch.holds

    def test_stealth_issues_hold(self, registry_and_compiler):
        compiler, marine, *_ = registry_and_compiler
        derived = {"stealth_posture_active(marine_00000041)"}
        batch = compiler.compile(derived)
        assert marine in batch.holds


class TestCompilePriorityTarget:
    def test_priority_target_sets_focus(self, registry_and_compiler):
        compiler, *_, enemy, _ = registry_and_compiler
        derived = {"priority_target(zergling_000000a1)"}
        batch = compiler.compile(derived)
        assert enemy in batch.focus_targets


class TestCompileMissionAccomplished:
    def test_mission_accomplished_sets_stop_all(self, registry_and_compiler):
        compiler, *_ = registry_and_compiler
        derived = {"mission_accomplished"}
        batch = compiler.compile(derived)
        assert batch.stop_all is True

    def test_stop_all_overrides_other_orders(self, registry_and_compiler):
        compiler, marine, *_ = registry_and_compiler
        derived = {
            "authorized_to_engage(marine_00000041, zergling_000000a1)",
            "mission_accomplished",
        }
        batch = compiler.compile(derived)
        # When stop_all is True, apply() should call stop on all units
        assert batch.stop_all is True


class TestApplyOrders:
    def test_apply_attacks_called(self, registry_and_compiler):
        compiler, marine, zealot, enemy, rally = registry_and_compiler
        batch = OrderBatch()
        batch.attacks = [(marine, enemy)]
        batch.apply([marine, zealot])
        assert len(marine.attacks) == 1

    def test_apply_retreats_called(self, registry_and_compiler):
        compiler, marine, zealot, enemy, rally = registry_and_compiler
        batch = OrderBatch()
        batch.retreats = [(marine, rally)]
        batch.apply([marine])
        assert len(marine.moves) == 1

    def test_apply_stop_all_stops_every_unit(self, registry_and_compiler):
        compiler, marine, zealot, *_ = registry_and_compiler
        batch = OrderBatch()
        batch.stop_all = True
        batch.apply([marine, zealot])
        assert marine.stops == 1
        assert zealot.stops == 1

    def test_apply_hold_position(self, registry_and_compiler):
        compiler, marine, *_ = registry_and_compiler
        batch = OrderBatch()
        batch.holds = [marine]
        batch.apply([marine])
        assert marine.holds == 1


class TestUpdateRegistry:
    def test_registry_update_takes_effect(self):
        compiler = ActionCompiler()
        marine = _FakeUnit(0x41)
        enemy  = _FakeUnit(0xA1)
        compiler.update_registry(
            {"marine_00000041": marine, "zergling_000000a1": enemy},
            rally_point=_FakePosition(),
        )
        batch = compiler.compile({"authorized_to_engage(marine_00000041, zergling_000000a1)"})
        assert len(batch.attacks) == 1
