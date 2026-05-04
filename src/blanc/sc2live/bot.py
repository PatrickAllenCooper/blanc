"""
DeFAbBot: python-sc2 BotAI subclass for DeFAb live SC2 integration.

Orchestrates the per-step pipeline:

    1. ObservationLifter   converts BotAI.state -> ground Theory
    2. Policy              optionally proposes defeasible rules / defeaters
    3. DefeasibleEngine    derives ROE conclusions (+∂ literals)
    4. ActionCompiler      translates conclusions -> SC2 unit orders
    5. Issue orders        dispatches to python-sc2

The bot is designed to run with either ScriptedPolicy (E1, baseline) or
LLMPolicy (E4, self-play) interchangeably via the ``policy`` constructor arg.

Replay logging: every SNAPSHOT_INTERVAL steps the full lifted Theory and the
set of derived literals are appended to self.trace, which is serialized to a
.jsonl file on game end.  This trace feeds scripts/generate_sc2live_instances.py.

Usage (local, Windows/Mac)::

    import sc2
    from sc2.main import run_game
    from sc2.data import Race, Difficulty
    from sc2.player import Bot, Computer
    from blanc.sc2live.bot import DeFAbBot
    from blanc.sc2live.policies.scripted import ScriptedPolicy

    run_game(
        sc2.maps.get("Simple64"),
        [
            Bot(Race.Terran, DeFAbBot(policy=ScriptedPolicy())),
            Computer(Race.Random, Difficulty.Easy),
        ],
        realtime=False,
    )

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from blanc.sc2live.observation import ObservationLifter
from blanc.sc2live.orders import ActionCompiler

logger = logging.getLogger(__name__)

# How frequently to snapshot the full theory state for replay extraction.
SNAPSHOT_INTERVAL = 22   # every ~1 sec at fastest game speed


@dataclass
class FrameSnapshot:
    """
    A single snapshot of the game state for replay extraction.

    Stored in DeFAbBot.trace and serialized at game end.
    """
    step: int
    facts: list[str]
    derived: list[str]
    orders_issued: list[str]
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "step": self.step,
            "facts": self.facts,
            "derived": self.derived,
            "orders_issued": self.orders_issued,
            "timestamp": self.timestamp,
        }


class DeFAbBot:
    """
    python-sc2 BotAI subclass that uses the DeFAb ROE theory for decisions.

    This class inherits from sc2.bot_ai.BotAI at runtime if sc2 is installed.
    When sc2 is not installed (e.g. in CI), it falls back to a stub base class
    so unit tests can exercise the logic without a game binary.

    Parameters
    ----------
    kb_theory : Theory | None
        Pre-built knowledge base (strict + defeasible rules, no facts).
        If None, the standard RTS engagement KB is loaded automatically.
    policy : ScriptedPolicy | LLMPolicy
        Decision policy.  ScriptedPolicy for baseline; LLMPolicy for E4.
    trace_dir : Path | str | None
        Directory to write trace .jsonl files.  None disables tracing.
    """

    def __init__(
        self,
        kb_theory: Theory | None = None,
        policy: Any = None,
        trace_dir: Path | str | None = None,
    ) -> None:
        # Import sc2 lazily; falls back to stub if not installed.
        try:
            from sc2.bot_ai import BotAI  # type: ignore[import]
            self.__class__ = type(
                "DeFAbBot",
                (DeFAbBot, BotAI),
                {},
            )
            BotAI.__init__(self)  # type: ignore[misc]
        except ImportError:
            logger.warning("burnysc2 not installed; DeFAbBot runs in stub mode")

        if kb_theory is None:
            from examples.knowledge_bases.rts_engagement_kb import (
                create_rts_engagement_kb,
            )
            kb_theory = create_rts_engagement_kb(include_instances=False)

        self._kb_skeleton: Theory = kb_theory

        if policy is None:
            from blanc.sc2live.policies.scripted import ScriptedPolicy
            policy = ScriptedPolicy()
        self._policy = policy

        self._lifter = ObservationLifter()
        self._compiler: ActionCompiler = ActionCompiler()
        self.trace: list[FrameSnapshot] = []
        self._trace_dir: Path | None = Path(trace_dir) if trace_dir else None

    # ------------------------------------------------------------------
    # python-sc2 lifecycle callbacks
    # ------------------------------------------------------------------

    async def on_start(self) -> None:
        """Called once by python-sc2 before the first game step."""
        try:
            gi = self.game_info  # type: ignore[attr-defined]
            map_center = gi.map_center
            start = self.start_location  # type: ignore[attr-defined]
            enemy_start = self.enemy_start_locations[0]  # type: ignore[attr-defined]
            self._lifter.configure_map(
                allied_spawn=(start.x, start.y),
                enemy_spawn=(enemy_start.x, enemy_start.y),
                map_width=float(gi.map_size.width),
                map_height=float(gi.map_size.height),
            )
            # Initialize rally point as map center
            self._compiler.update_registry({}, rally_point=map_center)
            logger.info("DeFAbBot started on map %s", gi.map_name)
        except AttributeError:
            # Stub mode (no real BotAI attributes)
            pass

    async def on_step(self, iteration: int) -> None:
        """Called every game step by python-sc2."""
        # ── 1. Build current theory from KB skeleton + live facts ────────────
        theory = self._build_theory_for_tick()

        orders_issued: list[str] = []

        # ── 2. Dispatch on policy type ────────────────────────────────────────
        # CommanderPolicy exposes propose_orders(); rule-author policies expose
        # propose_defeaters().  Dispatch on whichever interface is available.
        if hasattr(self._policy, "propose_orders"):
            # Commander path: LLM issues high-level orders directly
            admitted_orders = self._policy.propose_orders(theory, iteration)
            registry = self._build_unit_registry()
            self._compiler.update_registry(registry)
            for order in admitted_orders:
                unit_obj = registry.get(order.unit)
                target_obj = registry.get(order.target) if order.target else None
                if unit_obj and order.action == "attack" and target_obj:
                    unit_obj.attack(target_obj)
                    orders_issued.append(f"attack({order.unit},{order.target})")
                elif unit_obj and order.action == "retreat" and self._compiler._rally:
                    unit_obj.move(self._compiler._rally)
                    orders_issued.append(f"retreat({order.unit})")
                elif unit_obj and order.action == "hold":
                    unit_obj.hold_position()
                    orders_issued.append(f"hold({order.unit})")
            derived: set[str] = set()  # no engine derivation in commander path

        else:
            # Rule-author path (ScriptedPolicy / LLMPolicy): propose defeasible rules
            proposed_rules = self._policy.propose_defeaters(theory, iteration)
            for rule_str in proposed_rules:
                rule = self._parse_rule_str(rule_str)
                if rule is not None:
                    theory.add_rule(rule)

            # ── 3. Derive ROE conclusions ────────────────────────────────────
            engine = DefeasibleEngine(theory)
            derived = self._derive_roe_conclusions(engine, theory)

            # ── 4. Update unit registry ──────────────────────────────────────
            registry = self._build_unit_registry()
            self._compiler.update_registry(registry)

            # ── 5. Compile and issue orders ──────────────────────────────────
            batch = self._compiler.compile(derived)
            try:
                allied = list(self.units)  # type: ignore[attr-defined]
                batch.apply(allied)
                orders_issued = [str(a) for a in batch.attacks[:5]]
            except AttributeError:
                orders_issued = []

        # ── 6. Snapshot for replay extraction ────────────────────────────────
        if iteration % SNAPSHOT_INTERVAL == 0:
            self.trace.append(FrameSnapshot(
                step=iteration,
                facts=sorted(theory.facts),
                derived=sorted(derived),
                orders_issued=orders_issued,
            ))

    async def on_end(self, game_result: Any) -> None:
        """Called by python-sc2 when the game ends; serialize trace."""
        if self._trace_dir and self.trace:
            self._trace_dir.mkdir(parents=True, exist_ok=True)
            fname = self._trace_dir / f"trace_{int(time.time())}.jsonl"
            with open(fname, "w") as f:
                for snap in self.trace:
                    f.write(json.dumps(snap.to_dict()) + "\n")
            logger.info("Wrote %d snapshots to %s", len(self.trace), fname)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_theory_for_tick(self) -> Theory:
        """Return a fresh Theory with KB rules + current ground facts."""
        import copy
        theory = copy.deepcopy(self._kb_skeleton)
        try:
            self._lifter.lift(self, theory)
        except AttributeError:
            pass  # stub mode
        return theory

    def _derive_roe_conclusions(
        self, engine: DefeasibleEngine, theory: Theory
    ) -> set[str]:
        """Return set of +∂ provable ROE-relevant literals."""
        roe_predicates = [
            "authorized_to_engage",
            "cleared_to_engage",
            "ordered_to_retreat",
            "stealth_posture_active",
            "must_use_minimum_force",
            "priority_target",
            "mission_accomplished",
        ]
        derived: set[str] = set()
        for fact in theory.facts:
            for pred in roe_predicates:
                if fact.startswith(pred) and defeasible_provable(theory, fact):
                    derived.add(fact)
        # Also check mission_accomplished (nullary)
        if defeasible_provable(theory, "mission_accomplished"):
            derived.add("mission_accomplished")
        return derived

    def _build_unit_registry(self) -> dict[str, Any]:
        """Build atom-name -> Unit mapping from live BotAI state."""
        registry: dict[str, Any] = {}
        try:
            for unit in list(self.units) + list(self.enemy_units):  # type: ignore[attr-defined]
                name = unit.type_id.name.lower()
                atom = f"{name}_{unit.tag:08x}"
                registry[atom] = unit
        except AttributeError:
            pass  # stub mode
        return registry

    @staticmethod
    def _parse_rule_str(rule_str: str) -> Rule | None:
        """
        Parse a rule string of the form ``"head :=> body1, body2."``
        back into a Rule object.  Returns None on parse failure.
        """
        import re
        m_def = re.match(r"^(.+?)\s*:=>>\s*(.+)\.$", rule_str.strip())
        m_dft = re.match(r"^(.+?)\s*:~>>\s*(.+)\.$", rule_str.strip())
        if m_def:
            head = m_def.group(1).strip()
            body = tuple(b.strip() for b in m_def.group(2).split(","))
            return Rule(head=head, body=body, rule_type=RuleType.DEFEASIBLE,
                        label="llm_admitted")
        if m_dft:
            head = m_dft.group(1).strip()
            body = tuple(b.strip() for b in m_dft.group(2).split(","))
            return Rule(head=head, body=body, rule_type=RuleType.DEFEATER,
                        label="llm_admitted")
        return None
