"""
Unit tests for ObservationLifter.

Uses frozen BotAI.state fixtures (plain Python objects mimicking the
burnysc2 Unit API) so no SC2 binary is needed.

Author: Patrick Cooper
"""

import pytest
from blanc.core.theory import Theory
from blanc.sc2live.observation import ObservationLifter, BotStateView, _unit_id


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

class _UnitTypeId:
    def __init__(self, name: str) -> None:
        self.name = name


class _Position:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y


class _FakeUnit:
    """Minimal stub matching the BotAI Unit API surface used by ObservationLifter."""

    def __init__(
        self,
        type_name: str,
        tag: int,
        x: float = 50.0,
        y: float = 50.0,
        weapon_cooldown: float = 0.0,
    ) -> None:
        self.type_id = _UnitTypeId(type_name)
        self.tag = tag
        self.position = _Position(x, y)
        self.weapon_cooldown = weapon_cooldown


@pytest.fixture
def lifter() -> ObservationLifter:
    """Lifter configured for a 200x200 map, standard spawn positions."""
    l = ObservationLifter()
    l.configure_map(
        allied_spawn=(10.0, 10.0),
        enemy_spawn=(190.0, 190.0),
        map_width=200.0,
        map_height=200.0,
    )
    return l


@pytest.fixture
def empty_theory() -> Theory:
    return Theory()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestObservationLifterUnitFacts:
    def test_marine_adds_infantry_fact(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x41, x=50.0, y=50.0)],
        )
        lifter.lift(state, empty_theory)
        assert "infantry_unit(marine_00000041)" in empty_theory.facts

    def test_scv_adds_worker_fact(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("SCV", 0x1, x=15.0, y=15.0)],
        )
        lifter.lift(state, empty_theory)
        assert "worker_unit(scv_00000001)" in empty_theory.facts

    def test_probe_adds_worker_fact(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("PROBE", 0x2, x=12.0, y=12.0)],
        )
        lifter.lift(state, empty_theory)
        assert "worker_unit(probe_00000002)" in empty_theory.facts

    def test_mothership_is_fighter(self, lifter, empty_theory):
        state = BotStateView(
            enemy_units=[_FakeUnit("MOTHERSHIP", 0xAA, x=190.0, y=190.0)],
        )
        lifter.lift(state, empty_theory)
        assert "fighter_unit(mothership_000000aa)" in empty_theory.facts

    def test_unknown_unit_gets_military_unit(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("UNKNOWN_MECH_99", 0x99)],
        )
        lifter.lift(state, empty_theory)
        assert "military_unit(unknown_mech_99_00000099)" in empty_theory.facts

    def test_multiple_units_all_added(self, lifter, empty_theory):
        state = BotStateView(
            units=[
                _FakeUnit("MARINE", 0x10),
                _FakeUnit("MARAUDER", 0x11),
                _FakeUnit("SCV", 0x12, x=12.0, y=12.0),
            ],
        )
        lifter.lift(state, empty_theory)
        assert "infantry_unit(marine_00000010)" in empty_theory.facts
        assert "infantry_unit(marauder_00000011)" in empty_theory.facts
        assert "worker_unit(scv_00000012)" in empty_theory.facts


class TestObservationLifterZoneFacts:
    def test_unit_near_allied_spawn_in_main_base(self, lifter, empty_theory):
        state = BotStateView(units=[_FakeUnit("MARINE", 0x1, x=12.0, y=12.0)])
        lifter.lift(state, empty_theory)
        assert "in_zone(marine_00000001, main_base)" in empty_theory.facts

    def test_unit_near_enemy_spawn_in_enemy_base(self, lifter, empty_theory):
        state = BotStateView(units=[_FakeUnit("MARINE", 0x2, x=188.0, y=188.0)])
        lifter.lift(state, empty_theory)
        assert "in_zone(marine_00000002, enemy_base)" in empty_theory.facts

    def test_unit_at_map_edge_in_restricted_zone(self, lifter, empty_theory):
        # x=1.0 is within border (0.05 * 200 = 10)
        state = BotStateView(units=[_FakeUnit("MARINE", 0x3, x=1.0, y=100.0)])
        lifter.lift(state, empty_theory)
        assert "in_zone(marine_00000003, restricted_zone_alpha)" in empty_theory.facts

    def test_unit_mid_map_in_engagement_zone(self, lifter, empty_theory):
        state = BotStateView(units=[_FakeUnit("MARINE", 0x4, x=100.0, y=100.0)])
        lifter.lift(state, empty_theory)
        assert "in_zone(marine_00000004, engagement_zone_alpha)" in empty_theory.facts


class TestObservationLifterStatusFacts:
    def test_unit_under_fire_when_cooldown_positive(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x5, weapon_cooldown=2.5)]
        )
        lifter.lift(state, empty_theory)
        assert "under_direct_fire(marine_00000005)" in empty_theory.facts

    def test_unit_not_under_fire_when_cooldown_zero(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x6, weapon_cooldown=0.0)]
        )
        lifter.lift(state, empty_theory)
        assert "under_direct_fire(marine_00000006)" not in empty_theory.facts

    def test_enemy_military_unit_is_military_target(self, lifter, empty_theory):
        state = BotStateView(
            enemy_units=[_FakeUnit("ZERGLING", 0x20, x=100.0, y=100.0)]
        )
        lifter.lift(state, empty_theory)
        assert "military_target(zergling_00000020)" in empty_theory.facts

    def test_enemy_worker_is_worker_target(self, lifter, empty_theory):
        state = BotStateView(
            enemy_units=[_FakeUnit("PROBE", 0x21, x=100.0, y=100.0)]
        )
        lifter.lift(state, empty_theory)
        assert "worker_target(probe_00000021)" in empty_theory.facts


class TestObservationLifterArmyStateFacts:
    def test_all_in_rush_detected_when_massed_enemy(self, lifter, empty_theory):
        # 6 combat units out of 6 total -> all-in
        enemy_combat = [
            _FakeUnit("ZERGLING", i, x=100.0, y=100.0) for i in range(6)
        ]
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0xFF, x=10.0, y=10.0)],
            enemy_units=enemy_combat,
        )
        lifter.lift(state, empty_theory)
        assert "all_in_rush_detected" in empty_theory.facts

    def test_no_all_in_rush_with_mixed_enemy(self, lifter, empty_theory):
        # 2 combat + 4 workers = not all-in
        enemy = [
            _FakeUnit("ZERGLING", 1),
            _FakeUnit("ZERGLING", 2),
            _FakeUnit("DRONE", 3),
            _FakeUnit("DRONE", 4),
            _FakeUnit("DRONE", 5),
            _FakeUnit("DRONE", 6),
        ]
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0xFF)],
            enemy_units=enemy,
        )
        lifter.lift(state, empty_theory)
        assert "all_in_rush_detected" not in empty_theory.facts

    def test_numerical_disadvantage_when_outnumbered(self, lifter, empty_theory):
        # 1 allied vs 3 enemy -> ratio > 1.5
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0xA0, x=10.0, y=10.0)],
            enemy_units=[
                _FakeUnit("ZERGLING", i, x=100.0, y=100.0) for i in range(3)
            ],
        )
        lifter.lift(state, empty_theory)
        assert "has_numerical_disadvantage(marine_000000a0)" in empty_theory.facts

    def test_no_disadvantage_when_equal(self, lifter, empty_theory):
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0xB0, x=10.0, y=10.0)],
            enemy_units=[_FakeUnit("ZERGLING", 1, x=100.0, y=100.0)],
        )
        lifter.lift(state, empty_theory)
        assert "has_numerical_disadvantage(marine_000000b0)" not in empty_theory.facts


class TestObservationLifterNotConfigured:
    def test_lift_before_configure_is_noop(self, empty_theory):
        """Lifter without configure_map should not raise and should add no facts."""
        lifter = ObservationLifter()
        state = BotStateView(units=[_FakeUnit("MARINE", 1)])
        lifter.lift(state, empty_theory)
        assert len(empty_theory.facts) == 0


class TestUnitIdHelper:
    def test_unit_id_format(self):
        uid = _unit_id("MARINE", 0x41)
        assert uid == "marine_00000041"

    def test_unit_id_zero_padded(self):
        uid = _unit_id("SCV", 0x1)
        assert uid == "scv_00000001"

    def test_unit_id_lowercase(self):
        uid = _unit_id("BATTLECRUISER", 0xFFFF)
        assert uid == "battlecruiser_0000ffff"
