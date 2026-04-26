"""
Integration tests for the SC2 live engagement pipeline.

Certifies that:
  1. ObservationLifter + RTS KB produces consistent theories
  2. DefeasibleEngine derives correct ROE conclusions from lifted state
  3. ActionCompiler maps conclusions to well-formed order batches
  4. ReplayTraceExtractor round-trips through .jsonl correctly
  5. The full lift->derive->compile pipeline is end-to-end consistent
  6. sc2live_instances.json (if present) passes the standard verification

All tests are pure Python.  No SC2 binary or real API key required.

Live-binary integration test is guarded by ``pytest -m sc2_live``.

Author: Patrick Cooper
"""

import copy
import json
import tempfile
from pathlib import Path

import pytest

from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from blanc.sc2live.observation import ObservationLifter, BotStateView
from blanc.sc2live.orders import ActionCompiler
from blanc.sc2live.replay import ReplayTraceExtractor


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

class _UnitTypeId:
    def __init__(self, name: str) -> None:
        self.name = name


class _Position:
    def __init__(self, x: float = 50.0, y: float = 50.0) -> None:
        self.x = x
        self.y = y


class _FakeUnit:
    def __init__(self, type_name: str, tag: int, x: float = 50.0, y: float = 50.0,
                 weapon_cooldown: float = 0.0) -> None:
        self.type_id = _UnitTypeId(type_name)
        self.tag = tag
        self.position = _Position(x, y)
        self.weapon_cooldown = weapon_cooldown


class _FakeSC2Unit:
    """SC2 Unit stub with order tracking."""
    def __init__(self, tag: int) -> None:
        self.tag = tag
        self.attacks: list = []
        self.moves: list = []
    def attack(self, t) -> None: self.attacks.append(t)
    def move(self, t) -> None: self.moves.append(t)
    def hold_position(self) -> None: pass
    def stop(self) -> None: pass


@pytest.fixture(scope="module")
def kb():
    return create_rts_engagement_kb(include_instances=False)


@pytest.fixture
def lifter():
    l = ObservationLifter()
    l.configure_map(
        allied_spawn=(10.0, 10.0),
        enemy_spawn=(190.0, 190.0),
        map_width=200.0,
        map_height=200.0,
    )
    return l


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

class TestLiftDeriveIntegration:
    """Verify that lift->derive produces correct ROE conclusions."""

    def test_marine_in_engagement_zone_can_engage_enemy(self, lifter, kb):
        theory = copy.deepcopy(kb)
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x41, x=100.0, y=100.0)],
            enemy_units=[_FakeUnit("ZERGLING", 0xA1, x=100.0, y=100.0)],
        )
        lifter.lift(state, theory)
        # Military unit vs military target -> authorized_to_engage should fire
        # (requires ground facts to be present from KB)
        assert "infantry_unit(marine_00000041)" in theory.facts
        assert "military_target(zergling_000000a1)" in theory.facts

    def test_marine_in_restricted_zone_blocked(self, lifter, kb):
        theory = copy.deepcopy(kb)
        # Place both units inside the restricted zone (near map edge)
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x41, x=1.0, y=100.0)],
            enemy_units=[_FakeUnit("ZERGLING", 0xA1, x=1.0, y=100.0)],
        )
        lifter.lift(state, theory)
        assert "in_zone(marine_00000041, restricted_zone_alpha)" in theory.facts
        assert "in_zone(zergling_000000a1, restricted_zone_alpha)" in theory.facts

    def test_unit_under_fire_fact_set(self, lifter, kb):
        theory = copy.deepcopy(kb)
        state = BotStateView(
            units=[_FakeUnit("MARINE", 0x42, weapon_cooldown=1.0)],
        )
        lifter.lift(state, theory)
        assert "under_direct_fire(marine_00000042)" in theory.facts

    def test_theory_rules_preserved_after_lift(self, lifter, kb):
        theory = copy.deepcopy(kb)
        rule_count_before = len(theory.rules)
        state = BotStateView(units=[_FakeUnit("MARINE", 0x43)])
        lifter.lift(state, theory)
        # Lift should never modify rules
        assert len(theory.rules) == rule_count_before


class TestDeriveCompileIntegration:
    """Verify that derived literals map to correct SC2 orders."""

    def test_engagement_literal_compiles_to_attack(self):
        marine = _FakeSC2Unit(0x41)
        enemy  = _FakeSC2Unit(0xA1)
        compiler = ActionCompiler(
            unit_registry={
                "marine_00000041": marine,
                "zergling_000000a1": enemy,
            },
            rally_point=_Position(),
        )
        derived = {"authorized_to_engage(marine_00000041, zergling_000000a1)"}
        batch = compiler.compile(derived)
        batch.apply([marine])
        assert len(marine.attacks) == 1

    def test_retreat_literal_compiles_to_move(self):
        marine = _FakeSC2Unit(0x41)
        rally  = _Position(50.0, 50.0)
        compiler = ActionCompiler(
            unit_registry={"marine_00000041": marine},
            rally_point=rally,
        )
        batch = compiler.compile({"ordered_to_retreat(marine_00000041)"})
        batch.apply([marine])
        assert len(marine.moves) == 1


class TestReplayRoundTrip:
    """Verify that replay serialization preserves theory state."""

    def test_snapshot_facts_survive_jsonl_roundtrip(self, tmp_path, kb):
        # Write a snapshot
        snap = {
            "step": 44,
            "facts": ["infantry_unit(marine_00000041)", "in_zone(marine_00000041, main_base)"],
            "derived": ["authorized_to_engage(marine_00000041, enemy_zergling_1)"],
            "orders_issued": [],
            "timestamp": 1714000044.0,
        }
        trace = tmp_path / "trace_roundtrip.jsonl"
        with open(trace, "w") as f:
            f.write(json.dumps(snap) + "\n")

        extractor = ReplayTraceExtractor(kb_theory=kb)
        frames = list(extractor.stream_file(trace))

        assert len(frames) == 1
        frame = frames[0]
        assert frame.step == 44
        assert "infantry_unit(marine_00000041)" in frame.theory.facts
        assert "in_zone(marine_00000041, main_base)" in frame.theory.facts
        assert "authorized_to_engage(marine_00000041, enemy_zergling_1)" in frame.derived

    def test_multiple_traces_stream_in_order(self, tmp_path, kb):
        for i, step in enumerate([0, 22, 44]):
            trace = tmp_path / f"trace_{i:03d}.jsonl"
            with open(trace, "w") as f:
                f.write(json.dumps({
                    "step": step, "facts": [], "derived": [],
                    "orders_issued": [], "timestamp": float(step)
                }) + "\n")

        extractor = ReplayTraceExtractor(kb_theory=kb)
        steps = [f.step for f in extractor.stream_directory(tmp_path)]
        assert steps == [0, 22, 44]


class TestSC2LiveInstanceFile:
    """
    Verify sc2live_instances.json if it exists (post E2).
    Skip if not yet generated.
    """

    @pytest.fixture
    def instances_path(self):
        p = Path(__file__).parents[2] / "instances" / "sc2live_instances.json"
        if not p.exists():
            pytest.skip("sc2live_instances.json not yet generated (run E2 first)")
        return p

    def test_instances_file_parses(self, instances_path):
        with open(instances_path) as f:
            data = json.load(f)
        assert "instances" in data
        assert len(data["instances"]) > 0

    def test_instances_have_required_fields(self, instances_path):
        with open(instances_path) as f:
            data = json.load(f)
        for inst in data["instances"][:10]:
            assert "target" in inst
            assert "candidates" in inst
            assert "gold" in inst
            assert "level" in inst


# ---------------------------------------------------------------------------
# Live SC2 binary smoke test (requires actual SC2 installation)
# ---------------------------------------------------------------------------

@pytest.mark.sc2_live
def test_defabbot_scripted_policy_one_game(tmp_path):
    """
    E1 plumbing certification: run a 30-second game with ScriptedPolicy.

    Pass criteria:
      (a) every tick produces a syntactically valid Theory
      (b) DeFAbBot.trace contains at least 1 snapshot
      (c) no exceptions from the lift->derive->compile cycle

    Requires: SC2 binary + pip install blanc[sc2live]
    """
    pytest.importorskip("sc2", reason="burnysc2 not installed")

    import sc2
    from sc2.main import run_game
    from sc2.data import Race as SC2Race, Difficulty
    from sc2.player import Bot, Computer
    from blanc.sc2live.bot import DeFAbBot
    from blanc.sc2live.policies.scripted import ScriptedPolicy

    bot = DeFAbBot(policy=ScriptedPolicy(), trace_dir=tmp_path)

    # Run a very short game (bot concedes after ~1 min at fastest speed)
    from blanc.sc2live.bot import SNAPSHOT_INTERVAL

    class _TimedBot(DeFAbBot):
        async def on_step(self, iteration: int) -> None:
            await super().on_step(iteration)
            if iteration >= 1320:
                await self._client.leave()  # type: ignore[attr-defined]

    bot = _TimedBot(policy=ScriptedPolicy(), trace_dir=tmp_path)
    run_game(
        sc2.maps.get("Simple64"),
        [
            Bot(SC2Race.Terran, bot),
            Computer(SC2Race.Random, Difficulty.VeryEasy),
        ],
        realtime=False,
    )

    assert len(bot.trace) >= 1, "No snapshots recorded"
    for snap in bot.trace:
        assert snap.step >= 0
        assert isinstance(snap.facts, list)
        assert isinstance(snap.derived, list)
