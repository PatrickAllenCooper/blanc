"""
ActionCompiler: derived literals -> async python-sc2 unit orders.

Takes the set of derived ROE conclusions produced by DefeasibleEngine and
translates them into concrete python-sc2 unit-order calls.  The compiler is
intentionally thin: it only maps well-known ROE predicates to standard SC2
actions.  Tactical micro (kiting, formation) is out of scope.

Supported ROE conclusions -> actions:

    +∂ authorized_to_engage(X, Y)   ->  unit_X.attack(unit_Y)
    +∂ ordered_to_retreat(X)        ->  unit_X.move(allied_rally)
    +∂ stealth_posture_active(X)    ->  (do nothing / hold position)
    +∂ must_use_minimum_force(X)    ->  unit_X.hold_position()
    +∂ cleared_to_engage(X, Y)      ->  unit_X.attack(unit_Y) (same as engage)
    +∂ priority_target(Y)           ->  focus fire from all units on Y
    +∂ mission_accomplished         ->  stop all aggressive orders

Conclusions that have no direct SC2 action are silently dropped; the bot
continues to issue only positively derived orders, never suppresses default
SC2 AI behavior unless a conclusion explicitly overrides it.

Author: Anonymous Authors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Minimal SC2 type stubs (replaced by real sc2 objects at runtime)
# ---------------------------------------------------------------------------

@runtime_checkable
class UnitLike(Protocol):
    """Minimal interface for a python-sc2 Unit object."""

    tag: int

    def attack(self, target: Any) -> None: ...
    def move(self, target: Any) -> None: ...
    def hold_position(self) -> None: ...
    def stop(self) -> None: ...


@dataclass
class OrderBatch:
    """
    A resolved set of SC2 orders to issue this game tick.

    Collected by ActionCompiler, then submitted via DeFAbBot.
    """
    attacks:        list[tuple[UnitLike, UnitLike]] = field(default_factory=list)
    retreats:       list[tuple[UnitLike, Any]]      = field(default_factory=list)
    holds:          list[UnitLike]                   = field(default_factory=list)
    focus_targets:  list[UnitLike]                   = field(default_factory=list)
    stop_all:       bool                             = False

    def apply(self, all_allied_units: list[UnitLike]) -> None:
        """Issue all collected orders to the SC2 game engine."""
        if self.stop_all:
            for unit in all_allied_units:
                unit.stop()
            return

        for attacker, target in self.attacks:
            attacker.attack(target)

        for unit, rally in self.retreats:
            unit.move(rally)

        for unit in self.holds:
            unit.hold_position()

        if self.focus_targets:
            primary = self.focus_targets[0]
            for unit in all_allied_units:
                if not any(unit.tag == r[0].tag for r in self.retreats):
                    unit.attack(primary)


# ---------------------------------------------------------------------------
# Pattern matching helpers
# ---------------------------------------------------------------------------

_UNARY_RE  = re.compile(r"^(\w+)\((\w+)\)$")
_BINARY_RE = re.compile(r"^(\w+)\((\w+),\s*(\w+)\)$")


def _parse_literal(lit: str) -> tuple[str, list[str]]:
    """Return (predicate, [args]) from a ground atom string."""
    m = _BINARY_RE.match(lit)
    if m:
        return m.group(1), [m.group(2), m.group(3)]
    m = _UNARY_RE.match(lit)
    if m:
        return m.group(1), [m.group(2)]
    return lit, []


# ---------------------------------------------------------------------------
# ActionCompiler
# ---------------------------------------------------------------------------

class ActionCompiler:
    """
    Translates a set of derived ROE literals into an OrderBatch.

    Usage::

        compiler = ActionCompiler(unit_registry, rally_point)
        derived = engine.derive_all()   # set[str]
        batch = compiler.compile(derived)
        batch.apply(allied_units)

    The unit_registry maps unit-atom names (e.g. "marine_00000041") to
    live UnitLike objects.  It is updated each tick by DeFAbBot.
    """

    def __init__(
        self,
        unit_registry: dict[str, UnitLike] | None = None,
        rally_point: Any = None,
    ) -> None:
        self._units: dict[str, UnitLike] = unit_registry or {}
        self._rally = rally_point

    def update_registry(
        self,
        unit_registry: dict[str, UnitLike],
        rally_point: Any = None,
    ) -> None:
        """Refresh mapping from atom names to live Unit objects."""
        self._units = unit_registry
        if rally_point is not None:
            self._rally = rally_point

    def compile(self, derived_literals: set[str]) -> OrderBatch:
        """
        Convert a set of +∂ derived literals to an OrderBatch.

        Parameters
        ----------
        derived_literals : set[str]
            Strings of the form "predicate(arg)" or "predicate(arg1, arg2)"
            that the DefeasibleEngine has proved +∂.

        Returns
        -------
        OrderBatch
        """
        batch = OrderBatch()

        for lit in derived_literals:
            pred, args = _parse_literal(lit)

            if pred == "mission_accomplished":
                batch.stop_all = True
                return batch  # nothing else matters

            if pred in ("authorized_to_engage", "cleared_to_engage") and len(args) == 2:
                attacker = self._units.get(args[0])
                target   = self._units.get(args[1])
                if attacker and target:
                    batch.attacks.append((attacker, target))

            elif pred == "ordered_to_retreat" and len(args) == 1:
                unit = self._units.get(args[0])
                if unit and self._rally is not None:
                    batch.retreats.append((unit, self._rally))

            elif pred in ("must_use_minimum_force", "stealth_posture_active") and len(args) == 1:
                unit = self._units.get(args[0])
                if unit:
                    batch.holds.append(unit)

            elif pred == "priority_target" and len(args) == 1:
                target = self._units.get(args[0])
                if target:
                    batch.focus_targets.append(target)

        return batch
