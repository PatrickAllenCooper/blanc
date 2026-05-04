"""
ObservationLifter: BotAI.state -> Theory (ground facts only).

Converts a python-sc2 observation frame into a set of ground atoms using
the same predicate vocabulary as examples/knowledge_bases/rts_unit_rules.py.
The strict rule KB from that module applies unchanged; we only add facts.

Predicate mapping (from rts_unit_rules.py vocabulary):

Unit taxonomy facts:
    military_unit(X)       unit is a combat unit
    worker_unit(X)         unit is a worker (SCV / Probe / Drone)
    support_unit(X)        unit is a support / spell-caster
    ground_combat_unit(X)  ground fighter
    air_combat_unit(X)     air fighter
    infantry_unit(X)       biological infantry
    armored_unit(X)        mechanical ground unit
    fighter_unit(X)        air fighter
    bomber_unit(X)         air unit with splash
    medic_unit(X)          healer / regenerator
    transport_unit(X)      passenger transport
    sensor_unit(X)         detection / observer unit

Capability facts (derived from unit type):
    can_attack_ground(X)
    can_attack_air(X)
    has_ranged_attack(X)
    has_melee_attack(X)
    has_splash_damage(X)
    cannot_attack(X)

Zone facts (from map geometry):
    in_zone(X, Z)

Status facts (from unit state):
    has_numerical_disadvantage(X)      army is outnumbered near X
    under_direct_fire(X)               X has been attacked this step
    all_in_rush_detected               enemy is all-in
    high_value_target_in_range(X)      HVT within attack range of X
    target_attempting_escape           enemy HVT is moving away
    military_target(Y)                 Y is a valid military target

Mission / assignment facts:
    assigned_to_mission(X, M)
    mission(M)
    reconnaissance_mission(M)

Unit identity naming convention:  <sc2_name>_<unit_tag_hex>
    e.g. marine_0x00000041, probe_0x00000002

Zone naming convention (map-grid based):
    main_base, enemy_base, engagement_zone_alpha, restricted_zone_alpha,
    worker_mining_area, neutral_zone

Author: Anonymous Authors
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from blanc.core.theory import Theory

if TYPE_CHECKING:
    pass  # sc2 imports are runtime-optional


# ---------------------------------------------------------------------------
# SC2 unit-type -> predicate mapping
# Keyed by sc2.ids.UnitTypeId.name (upper-case string).
# Each entry is a set of zero-arg predicate names that apply to units of
# that type.  Multi-level taxonomy is handled by the strict rules in
# rts_unit_rules.py; we only assert the most-specific leaf predicates here.
# ---------------------------------------------------------------------------

_UNIT_TYPE_PREDICATES: dict[str, list[str]] = {
    # Terran
    "SCV":              ["worker_unit"],
    "MARINE":           ["infantry_unit"],
    "MARAUDER":         ["infantry_unit"],
    "REAPER":           ["infantry_unit"],
    "GHOST":            ["infantry_unit"],
    "HELLION":          ["armored_unit"],
    "HELLIONTANK":      ["armored_unit"],
    "SIEGETANK":        ["armored_unit"],
    "SIEGETANKSIEGED":  ["armored_unit"],
    "THOR":             ["armored_unit"],
    "CYCLONE":          ["armored_unit"],
    "VIKINGFIGHTER":    ["fighter_unit"],
    "VIKINGASSAULT":    ["armored_unit"],
    "BANSHEE":          ["bomber_unit"],
    "BATTLECRUISER":    ["bomber_unit"],
    "MEDIVAC":          ["medic_unit"],
    "RAVEN":            ["sensor_unit"],
    "DROPSHIP":         ["transport_unit"],
    # Protoss
    "PROBE":            ["worker_unit"],
    "ZEALOT":           ["infantry_unit"],
    "STALKER":          ["infantry_unit"],
    "IMMORTAL":         ["armored_unit"],
    "COLOSSUS":         ["armored_unit"],
    "PHOENIX":          ["fighter_unit"],
    "VOIDRAY":          ["fighter_unit"],
    "CARRIER":          ["bomber_unit"],
    "MOTHERSHIP":       ["fighter_unit"],   # HVT in SC2 ROE paper
    "OBSERVER":         ["sensor_unit"],
    "WARPPRISM":        ["transport_unit"],
    "HIGHTEMPLAR":      ["support_unit"],
    "DARKTEMPLAR":      ["infantry_unit"],
    "SENTRY":           ["support_unit"],
    # Zerg
    "DRONE":            ["worker_unit"],
    "ZERGLING":         ["infantry_unit"],
    "BANELING":         ["infantry_unit"],
    "ROACH":            ["armored_unit"],
    "HYDRALISK":        ["infantry_unit"],
    "ULTRALISK":        ["armored_unit"],
    "BROODLORD":        ["bomber_unit"],
    "MUTALISK":         ["fighter_unit"],
    "CORRUPTOR":        ["fighter_unit"],
    "OVERSEER":         ["sensor_unit"],
    "OVERLORD":         ["transport_unit"],
    "QUEEN":            ["support_unit"],
    "INFESTOR":         ["support_unit"],
}

# Units whose weapons cannot attack air targets (supplement the strict rules)
_GROUND_ONLY: frozenset[str] = frozenset({
    "SCV", "PROBE", "DRONE", "COLOSSUS", "HELLION", "HELLIONTANK",
    "BANELING", "ROACH", "ULTRALISK", "SIEGETANK", "SIEGETANKSIEGED",
})

# Units whose weapons cannot attack ground targets
_AIR_ONLY: frozenset[str] = frozenset({"PHOENIX"})

# Splash-damage units (supplement strict rules)
_SPLASH: frozenset[str] = frozenset({
    "BANELING", "COLOSSUS", "THOR", "BATTLECRUISER",
    "BROODLORD", "CARRIER",
})

# Zone assignment thresholds (fraction of map width / height)
# We partition each map into a 3x3 grid and label cells by proximity to
# each player's spawn.
_ZONE_GRID_N = 3


def _unit_id(unit_type_name: str, tag: int) -> str:
    """Return a stable Prolog-safe atom for a unit."""
    return f"{unit_type_name.lower()}_{tag:08x}"


def _zone_for_position(
    x: float,
    y: float,
    map_width: float,
    map_height: float,
    allied_spawn: tuple[float, float],
    enemy_spawn: tuple[float, float],
) -> str:
    """
    Assign a zone atom based on proximity to spawn points and map position.

    Zones (priority order -- first match wins):
        main_base               near allied spawn
        enemy_base              near enemy spawn
        worker_mining_area      allied spawn quadrant, mining area
        restricted_zone_alpha   boundary / no-fire zone at map edge
        engagement_zone_alpha   front-line band
        neutral_zone            everywhere else
    """
    ax, ay = allied_spawn
    ex, ey = enemy_spawn

    dist_allied = ((x - ax) ** 2 + (y - ay) ** 2) ** 0.5
    dist_enemy  = ((x - ex) ** 2 + (y - ey) ** 2) ** 0.5
    map_diag    = (map_width ** 2 + map_height ** 2) ** 0.5

    if dist_allied < 0.12 * map_diag:
        return "main_base"
    if dist_enemy < 0.12 * map_diag:
        return "enemy_base"
    # Narrow band around map edge -> restricted zone
    border = 0.05 * min(map_width, map_height)
    if x < border or y < border or x > map_width - border or y > map_height - border:
        return "restricted_zone_alpha"
    # Front half between spawns -> engagement zone
    mid_x = (ax + ex) / 2
    mid_y = (ay + ey) / 2
    dist_mid = ((x - mid_x) ** 2 + (y - mid_y) ** 2) ** 0.5
    if dist_mid < 0.25 * map_diag:
        return "engagement_zone_alpha"
    # Worker patch near allied base
    if dist_allied < 0.25 * map_diag:
        return "worker_mining_area"
    return "neutral_zone"


class ObservationLifter:
    """
    Converts a python-sc2 BotAI step observation into a set of ground facts
    appended to an existing defeasible Theory.

    Usage (inside DeFAbBot.on_step):

        theory = self._kb_skeleton.copy()   # strict + defeasible rules
        self.lifter.lift(self, theory)       # adds ground facts for this tick
        engine = DefeasibleEngine(theory)
        ...

    The lifter never modifies rules, only appends facts to theory.facts.
    """

    def __init__(
        self,
        allied_spawn: tuple[float, float] | None = None,
        enemy_spawn: tuple[float, float] | None = None,
        map_width: float = 200.0,
        map_height: float = 200.0,
    ) -> None:
        self._allied_spawn = allied_spawn
        self._enemy_spawn = enemy_spawn
        self._map_width = map_width
        self._map_height = map_height

    def configure_map(
        self,
        allied_spawn: tuple[float, float],
        enemy_spawn: tuple[float, float],
        map_width: float,
        map_height: float,
    ) -> None:
        """Set map geometry.  Call once from DeFAbBot.on_start."""
        self._allied_spawn = allied_spawn
        self._enemy_spawn = enemy_spawn
        self._map_width = map_width
        self._map_height = map_height

    def lift(self, bot_state: "BotStateView", theory: Theory) -> None:
        """
        Append ground facts derived from bot_state to theory in place.

        bot_state is any object with attributes:
            .units        -> iterable of unit objects (allied units)
            .enemy_units  -> iterable of unit objects (enemy units)
            .game_info    -> game_info object (map dimensions)

        Unit objects expose:
            .tag                int  (unique unit ID)
            .type_id.name       str  (UnitTypeId name, upper-case)
            .position.x/.y      float
            .is_attacking       bool
            .weapon_cooldown    float (>0 means was attacked recently)

        This method is pure with respect to theory.rules; it only calls
        theory.add_fact().
        """
        if self._allied_spawn is None:
            return  # map not configured yet

        allied_tags: set[int] = set()
        enemy_tags:  set[int] = set()

        # ── Allied units ────────────────────────────────────────────────────
        allied_units = list(getattr(bot_state, "units", []))
        enemy_units  = list(getattr(bot_state, "enemy_units", []))

        for unit in allied_units:
            uid = _unit_id(unit.type_id.name, unit.tag)
            allied_tags.add(unit.tag)
            self._add_unit_facts(theory, uid, unit, allied=True)

        # ── Enemy units ─────────────────────────────────────────────────────
        for unit in enemy_units:
            uid = _unit_id(unit.type_id.name, unit.tag)
            enemy_tags.add(unit.tag)
            self._add_unit_facts(theory, uid, unit, allied=False)
            # Enemy units with weapons are military targets
            if self._is_military_type(unit.type_id.name):
                theory.add_fact(f"military_target({uid})")
            elif self._is_worker_type(unit.type_id.name):
                theory.add_fact(f"worker_target({uid})")

        # ── Army-wide state facts ────────────────────────────────────────────
        self._add_army_state_facts(theory, allied_units, enemy_units)

    # -----------------------------------------------------------------------
    # Private helpers
    # -----------------------------------------------------------------------

    def _add_unit_facts(
        self,
        theory: Theory,
        uid: str,
        unit: object,
        *,
        allied: bool,
    ) -> None:
        name = getattr(unit.type_id, "name", "UNKNOWN")  # type: ignore[attr-defined]
        predicates = _UNIT_TYPE_PREDICATES.get(name, ["military_unit"])

        for pred in predicates:
            theory.add_fact(f"{pred}({uid})")

        # Zone placement
        x = getattr(unit.position, "x", 0.0)  # type: ignore[attr-defined]
        y = getattr(unit.position, "y", 0.0)  # type: ignore[attr-defined]
        zone = _zone_for_position(
            x, y,
            self._map_width, self._map_height,
            self._allied_spawn,  # type: ignore[arg-type]
            self._enemy_spawn,   # type: ignore[arg-type]
        )
        theory.add_fact(f"in_zone({uid}, {zone})")

        # Under-fire status (weapon_cooldown > 0 indicates recent attack)
        cooldown = getattr(unit, "weapon_cooldown", 0.0)
        if cooldown > 0:
            theory.add_fact(f"under_direct_fire({uid})")

    @staticmethod
    def _is_military_type(name: str) -> bool:
        preds = _UNIT_TYPE_PREDICATES.get(name, [])
        return any(p in ("infantry_unit", "armored_unit", "fighter_unit",
                         "bomber_unit") for p in preds)

    @staticmethod
    def _is_worker_type(name: str) -> bool:
        return _UNIT_TYPE_PREDICATES.get(name, []) == ["worker_unit"]

    def _add_army_state_facts(
        self,
        theory: Theory,
        allied_units: list,
        enemy_units: list,
    ) -> None:
        allied_combat = [
            u for u in allied_units
            if self._is_military_type(getattr(u.type_id, "name", ""))  # type: ignore[attr-defined]
        ]
        enemy_combat = [
            u for u in enemy_units
            if self._is_military_type(getattr(u.type_id, "name", ""))  # type: ignore[attr-defined]
        ]

        # Numerical disadvantage for each allied unit in a numerically inferior army
        if len(enemy_combat) > len(allied_combat) * 1.5:
            for unit in allied_combat:
                uid = _unit_id(getattr(unit.type_id, "name", "unit"), unit.tag)  # type: ignore[attr-defined]
                theory.add_fact(f"has_numerical_disadvantage({uid})")

        # All-in rush heuristic: enemy has massed 80%+ of units and is moving
        if len(enemy_combat) >= 4 and len(enemy_combat) >= 0.8 * len(enemy_units):
            theory.add_fact("all_in_rush_detected")

        # High-value target detection (Mothership / Carrier)
        hvt_names = {"MOTHERSHIP", "CARRIER", "BATTLECRUISER"}
        for unit in enemy_units:
            name = getattr(unit.type_id, "name", "")  # type: ignore[attr-defined]
            if name in hvt_names:
                enemy_uid = _unit_id(name, unit.tag)
                # Check if any allied unit can reach it
                for a_unit in allied_combat:
                    a_uid = _unit_id(getattr(a_unit.type_id, "name", "unit"), a_unit.tag)  # type: ignore[attr-defined]
                    ax = getattr(a_unit.position, "x", 0.0)  # type: ignore[attr-defined]
                    ay = getattr(a_unit.position, "y", 0.0)  # type: ignore[attr-defined]
                    ex = getattr(unit.position, "x", 0.0)  # type: ignore[attr-defined]
                    ey = getattr(unit.position, "y", 0.0)  # type: ignore[attr-defined]
                    dist = ((ax - ex) ** 2 + (ay - ey) ** 2) ** 0.5
                    if dist < 10.0:
                        theory.add_fact(f"high_value_target_in_range({a_uid})")
                # Target-attempting-escape: HVT is far from its base
                map_diag = (self._map_width ** 2 + self._map_height ** 2) ** 0.5
                ex_ = getattr(unit.position, "x", 0.0)  # type: ignore[attr-defined]
                ey_ = getattr(unit.position, "y", 0.0)  # type: ignore[attr-defined]
                if self._enemy_spawn:
                    d_from_spawn = ((ex_ - self._enemy_spawn[0]) ** 2
                                    + (ey_ - self._enemy_spawn[1]) ** 2) ** 0.5
                    if d_from_spawn > 0.4 * map_diag:
                        theory.add_fact("target_attempting_escape")


class BotStateView:
    """
    Thin stub that mirrors the BotAI state API consumed by ObservationLifter.
    Used in tests without a live SC2 binary.
    """

    def __init__(
        self,
        units: list | None = None,
        enemy_units: list | None = None,
    ) -> None:
        self.units = units or []
        self.enemy_units = enemy_units or []
