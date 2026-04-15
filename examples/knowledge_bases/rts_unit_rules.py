"""
RTS Engagement -- Strict Unit and Terrain Rules

Strict rules encoding inviolable game-mechanical facts about unit types,
capabilities, terrain, and resource mechanics in a generic real-time strategy
environment modeled on StarCraft II.  These rules cannot be overridden by
mission constraints or rules of engagement; they are the "physics" of the
battlespace.

These rules serve as the strict (necessary) layer of the defeasible theory.
Defeasible behavioral rules and ROE-style defeaters are in
rts_behavioral_rules.py.

Grounding in the literature:
- "Planning in RTS Games with Incomplete Action Definitions via Answer Set
  Programming" (AIIDE 2015, the paper shared by Tom Lee at Lockheed Martin).
- StarCraft II game mechanics documentation (Blizzard Entertainment).
- PySC2 observation space (Google DeepMind, github.com/google-deepmind/pysc2).

Author: Patrick Cooper
"""

from blanc.core.theory import Theory, Rule, RuleType


def _s(theory: Theory, rid: int, head: str, body: tuple) -> int:
    """Add a strict rule and return the next rule id."""
    theory.add_rule(Rule(
        head=head, body=body, rule_type=RuleType.STRICT,
        label=f"rts_s{rid}",
    ))
    return rid + 1


def create_rts_unit_theory() -> Theory:
    """
    Create a Theory with strict rules about RTS unit types and mechanics.

    Returns a Theory containing only strict rules and instance facts.
    Behavioral/ROE rules are added separately via rts_behavioral_rules.py.
    """
    theory = Theory()

    # ── Unit taxonomy (strict) ───────────────────────────────────────────────

    rid = 1
    rid = _s(theory, rid, "unit(X)", ("military_unit(X)",))
    rid = _s(theory, rid, "unit(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "unit(X)", ("support_unit(X)",))
    rid = _s(theory, rid, "military_unit(X)", ("ground_combat_unit(X)",))
    rid = _s(theory, rid, "military_unit(X)", ("air_combat_unit(X)",))
    rid = _s(theory, rid, "military_unit(X)", ("naval_unit(X)",))
    rid = _s(theory, rid, "ground_combat_unit(X)", ("infantry_unit(X)",))
    rid = _s(theory, rid, "ground_combat_unit(X)", ("armored_unit(X)",))
    rid = _s(theory, rid, "air_combat_unit(X)", ("fighter_unit(X)",))
    rid = _s(theory, rid, "air_combat_unit(X)", ("bomber_unit(X)",))
    rid = _s(theory, rid, "support_unit(X)", ("medic_unit(X)",))
    rid = _s(theory, rid, "support_unit(X)", ("transport_unit(X)",))
    rid = _s(theory, rid, "support_unit(X)", ("sensor_unit(X)",))

    # ── Attack capability (strict) ───────────────────────────────────────────

    rid = _s(theory, rid, "can_attack_ground(X)", ("infantry_unit(X)",))
    rid = _s(theory, rid, "can_attack_ground(X)", ("armored_unit(X)",))
    rid = _s(theory, rid, "can_attack_ground(X)", ("bomber_unit(X)",))
    rid = _s(theory, rid, "can_attack_air(X)", ("fighter_unit(X)",))
    rid = _s(theory, rid, "can_attack_air(X)", ("infantry_unit(X)",))
    rid = _s(theory, rid, "can_attack_air(X)", ("armored_unit(X)",))
    rid = _s(theory, rid, "has_ranged_attack(X)", ("infantry_unit(X)",))
    rid = _s(theory, rid, "has_ranged_attack(X)", ("fighter_unit(X)",))
    rid = _s(theory, rid, "has_ranged_attack(X)", ("bomber_unit(X)",))
    rid = _s(theory, rid, "has_melee_attack(X)", ("armored_unit(X)",))
    rid = _s(theory, rid, "has_splash_damage(X)", ("bomber_unit(X)",))
    rid = _s(theory, rid, "has_splash_damage(X)", ("armored_unit(X)",))
    rid = _s(theory, rid, "cannot_attack(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "cannot_attack(X)", ("medic_unit(X)",))
    rid = _s(theory, rid, "cannot_attack(X)", ("transport_unit(X)",))

    # ── Mobility (strict) ────────────────────────────────────────────────────

    rid = _s(theory, rid, "is_mobile(X)", ("unit(X)",))
    rid = _s(theory, rid, "traverses_terrain(X)", ("ground_combat_unit(X)",))
    rid = _s(theory, rid, "traverses_terrain(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "flies(X)", ("air_combat_unit(X)",))
    rid = _s(theory, rid, "flies(X)", ("transport_unit(X)",))
    rid = _s(theory, rid, "requires_passable_ground(X)", ("ground_combat_unit(X)",))
    rid = _s(theory, rid, "requires_passable_ground(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "can_transport_units(X)", ("transport_unit(X)",))

    # ── Detection and vision (strict) ────────────────────────────────────────

    rid = _s(theory, rid, "has_sight(X)", ("unit(X)",))
    rid = _s(theory, rid, "has_extended_detection(X)", ("sensor_unit(X)",))
    rid = _s(theory, rid, "detects_cloaked(X)", ("sensor_unit(X)",))
    rid = _s(theory, rid, "can_cloak(X)", ("fighter_unit(X)",))
    rid = _s(theory, rid, "is_invisible_to_basic_sight(X)", ("cloaked_unit(X)",))

    # ── Production and economy (strict) ──────────────────────────────────────

    rid = _s(theory, rid, "gathers_resources(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "constructs_buildings(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "repairs_units(X)", ("worker_unit(X)",))
    rid = _s(theory, rid, "heals_units(X)", ("medic_unit(X)",))
    rid = _s(theory, rid, "requires_supply(X)", ("unit(X)",))

    # ── Terrain and zone types (strict) ──────────────────────────────────────

    rid = _s(theory, rid, "is_terrain(X)", ("open_ground(X)",))
    rid = _s(theory, rid, "is_terrain(X)", ("choke_point(X)",))
    rid = _s(theory, rid, "is_terrain(X)", ("high_ground(X)",))
    rid = _s(theory, rid, "is_terrain(X)", ("impassable_cliff(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("allied_base(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("enemy_base(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("neutral_zone(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("exclusion_zone(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("engagement_zone(X)",))
    rid = _s(theory, rid, "is_zone(X)", ("civilian_area(X)",))
    rid = _s(theory, rid, "blocks_ground_movement(X)", ("impassable_cliff(X)",))
    rid = _s(theory, rid, "provides_vision_bonus(X)", ("high_ground(X)",))
    rid = _s(theory, rid, "is_tactically_critical(X)", ("choke_point(X)",))
    rid = _s(theory, rid, "is_tactically_critical(X)", ("high_ground(X)",))

    # ── Mission types (strict) ────────────────────────────────────────────────

    rid = _s(theory, rid, "is_mission_type(X)", ("offensive_operation(X)",))
    rid = _s(theory, rid, "is_mission_type(X)", ("defensive_operation(X)",))
    rid = _s(theory, rid, "is_mission_type(X)", ("reconnaissance_mission(X)",))
    rid = _s(theory, rid, "is_mission_type(X)", ("extraction_mission(X)",))
    rid = _s(theory, rid, "is_mission_type(X)", ("patrol_mission(X)",))
    rid = _s(theory, rid, "requires_stealth(X)", ("reconnaissance_mission(X)",))
    rid = _s(theory, rid, "requires_stealth(X)", ("extraction_mission(X)",))
    rid = _s(theory, rid, "allows_direct_combat(X)", ("offensive_operation(X)",))
    rid = _s(theory, rid, "allows_direct_combat(X)", ("defensive_operation(X)",))

    # ── Threat classification (strict) ────────────────────────────────────────

    rid = _s(theory, rid, "is_threat_level(X)", ("low_threat(X)",))
    rid = _s(theory, rid, "is_threat_level(X)", ("medium_threat(X)",))
    rid = _s(theory, rid, "is_threat_level(X)", ("high_threat(X)",))
    rid = _s(theory, rid, "is_threat_level(X)", ("critical_threat(X)",))
    rid = _s(theory, rid, "hostile_act_detected(X)", ("critical_threat(X)",))
    rid = _s(theory, rid, "hostile_act_detected(X)", ("high_threat(X)",))
    rid = _s(theory, rid, "requires_immediate_response(X)", ("critical_threat(X)",))

    # ── Force composition (strict) ────────────────────────────────────────────

    rid = _s(theory, rid, "has_numerical_advantage(X)", ("dominant_force(X)",))
    rid = _s(theory, rid, "has_numerical_disadvantage(X)", ("understrength_force(X)",))
    rid = _s(theory, rid, "is_isolated(X)", ("separated_unit(X)",))
    rid = _s(theory, rid, "has_supply_line(X)", ("connected_force(X)",))
    rid = _s(theory, rid, "is_encircled(X)", ("surrounded_unit(X)",))

    # ── Target classification (strict) ────────────────────────────────────────

    rid = _s(theory, rid, "is_target_type(X)", ("military_target(X)",))
    rid = _s(theory, rid, "is_target_type(X)", ("worker_target(X)",))
    rid = _s(theory, rid, "is_target_type(X)", ("structure_target(X)",))
    rid = _s(theory, rid, "is_target_type(X)", ("high_value_target(X)",))
    rid = _s(theory, rid, "is_combatant(X)", ("military_target(X)",))
    rid = _s(theory, rid, "is_noncombatant(X)", ("worker_target(X)",))
    rid = _s(theory, rid, "is_high_priority(X)", ("high_value_target(X)",))
    rid = _s(theory, rid, "is_infrastructure(X)", ("structure_target(X)",))

    # ── Add instance facts ────────────────────────────────────────────────────

    _add_unit_instances(theory)
    _add_terrain_instances(theory)
    _add_mission_instances(theory)
    _add_threat_instances(theory)
    _add_target_instances(theory)

    return theory


def _add_unit_instances(theory: Theory) -> None:
    """Add concrete unit instances as ground facts."""

    # Infantry units (SC2: Marine, Zealot, Zergling analogs)
    infantry = ['marine', 'zealot', 'zergling', 'stalker', 'roach', 'hydralisk']
    for u in infantry:
        theory.add_fact(f"unit({u})")
        theory.add_fact(f"military_unit({u})")
        theory.add_fact(f"ground_combat_unit({u})")
        theory.add_fact(f"infantry_unit({u})")

    # Armored units (SC2: Tank, Immortal, Ultralisk analogs)
    armored = ['siege_tank', 'immortal', 'ultralisk', 'hellion', 'colossus']
    for u in armored:
        theory.add_fact(f"unit({u})")
        theory.add_fact(f"military_unit({u})")
        theory.add_fact(f"ground_combat_unit({u})")
        theory.add_fact(f"armored_unit({u})")

    # Fighter units (SC2: Viking, Phoenix, Mutalisk analogs)
    fighters = ['viking', 'phoenix', 'mutalisk', 'battlecruiser', 'carrier']
    for u in fighters:
        theory.add_fact(f"unit({u})")
        theory.add_fact(f"military_unit({u})")
        theory.add_fact(f"air_combat_unit({u})")
        theory.add_fact(f"fighter_unit({u})")

    # Bomber units
    bombers = ['banshee', 'brood_lord', 'void_ray']
    for u in bombers:
        theory.add_fact(f"unit({u})")
        theory.add_fact(f"military_unit({u})")
        theory.add_fact(f"air_combat_unit({u})")
        theory.add_fact(f"bomber_unit({u})")

    # Worker units (SC2: SCV, Probe, Drone analogs)
    workers = ['scv', 'probe', 'drone']
    for u in workers:
        theory.add_fact(f"unit({u})")
        theory.add_fact(f"worker_unit({u})")

    # Support units
    theory.add_fact("unit(medivac)")
    theory.add_fact("support_unit(medivac)")
    theory.add_fact("medic_unit(medivac)")
    theory.add_fact("transport_unit(medivac)")
    theory.add_fact("unit(observer)")
    theory.add_fact("support_unit(observer)")
    theory.add_fact("sensor_unit(observer)")
    theory.add_fact("unit(raven)")
    theory.add_fact("support_unit(raven)")
    theory.add_fact("sensor_unit(raven)")


def _add_terrain_instances(theory: Theory) -> None:
    """Add terrain and zone instances."""
    terrains = [
        ('natural_ramp', 'choke_point'),
        ('third_base_cliff', 'high_ground'),
        ('center_plateau', 'high_ground'),
        ('gold_expansion', 'open_ground'),
        ('mineral_line', 'open_ground'),
        ('jungle_passage', 'choke_point'),
        ('lava_field', 'impassable_cliff'),
    ]
    for name, terrain_type in terrains:
        theory.add_fact(f"terrain({name})")
        theory.add_fact(f"{terrain_type}({name})")

    zones = [
        ('main_base', 'allied_base'),
        ('natural_expansion', 'allied_base'),
        ('enemy_main', 'enemy_base'),
        ('enemy_natural', 'enemy_base'),
        ('watch_tower_area', 'neutral_zone'),
        ('contested_center', 'engagement_zone'),
        ('restricted_zone_alpha', 'exclusion_zone'),
        ('worker_mining_area', 'civilian_area'),
    ]
    for name, zone_type in zones:
        theory.add_fact(f"zone({name})")
        theory.add_fact(f"{zone_type}({name})")


def _add_mission_instances(theory: Theory) -> None:
    """Add mission type instances."""
    missions = [
        ('op_thunderbolt', 'offensive_operation'),
        ('op_shield_wall', 'defensive_operation'),
        ('op_ghost_eye', 'reconnaissance_mission'),
        ('op_safe_passage', 'extraction_mission'),
        ('op_border_watch', 'patrol_mission'),
    ]
    for name, mtype in missions:
        theory.add_fact(f"mission({name})")
        theory.add_fact(f"{mtype}({name})")


def _add_threat_instances(theory: Theory) -> None:
    """Add threat classification instances."""
    threats = [
        ('enemy_scout_probe', 'low_threat'),
        ('enemy_harass_squad', 'medium_threat'),
        ('enemy_main_army', 'high_threat'),
        ('enemy_all_in_rush', 'critical_threat'),
        ('enemy_drop_attack', 'high_threat'),
        ('enemy_sneak_worker_kill', 'medium_threat'),
    ]
    for name, tlevel in threats:
        theory.add_fact(f"threat({name})")
        theory.add_fact(f"{tlevel}({name})")


def _add_target_instances(theory: Theory) -> None:
    """Add target instances."""
    targets = [
        ('enemy_marine_squad', 'military_target'),
        ('enemy_siege_tank', 'military_target'),
        ('enemy_carrier', 'military_target'),
        ('enemy_probe_line', 'worker_target'),
        ('enemy_scv_cluster', 'worker_target'),
        ('enemy_command_center', 'structure_target'),
        ('enemy_stargate', 'structure_target'),
        ('enemy_hero_unit', 'high_value_target'),
        ('enemy_mothership', 'high_value_target'),
    ]
    for name, ttype in targets:
        theory.add_fact(f"target({name})")
        theory.add_fact(f"{ttype}({name})")
