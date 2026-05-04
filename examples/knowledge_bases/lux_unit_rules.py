"""
Lux AI Season 3 -- Strict Unit and Environment Rules

Strict rules encoding inviolable physics of the Lux AI S3 game environment.
Lux AI S3 is a NeurIPS 2024 competition game: a 1v1 multi-agent strategy
on a 24x24 grid.  Units (ships) collect energy, pursue relic nodes to earn
points, and must manage partial observability.

These strict rules define what units ARE and CAN DO -- the physics layer.
Defeasible ROE-style behavioral rules and their defeaters live in
lux_behavioral_rules.py.

Game mechanics source:
    Lux AI Challenge Season 3, NeurIPS 2024.
    https://github.com/Lux-AI-Challenge/Lux-Design-S3
    Lux AI S3 paper: "Multi-Agent Meta Learning at Scale" (OpenReview 2024).

Visual rendering: https://s3vis.lux-ai.org (web-based replay visualizer)

Author: Anonymous Authors
"""

from blanc.core.theory import Theory, Rule, RuleType


def _s(theory: Theory, rid: int, head: str, body: tuple) -> int:
    """Add a strict rule and return the next rule id."""
    theory.add_rule(Rule(
        head=head, body=body, rule_type=RuleType.STRICT,
        label=f"lux_s{rid}",
    ))
    return rid + 1


def create_lux_unit_theory() -> Theory:
    """
    Create a Theory with strict rules about Lux AI S3 units and map objects.

    Returns a Theory containing strict rules and ground instance facts.
    Behavioral/ROE rules are added separately via lux_behavioral_rules.py.
    """
    theory = Theory()

    # ── Unit taxonomy (strict) ────────────────────────────────────────────────
    rid = 1
    rid = _s(theory, rid, "game_object(X)", ("unit(X)",))
    rid = _s(theory, rid, "game_object(X)", ("map_tile(X)",))
    rid = _s(theory, rid, "unit(X)", ("ship(X)",))
    rid = _s(theory, rid, "map_tile(X)", ("energy_node(X)",))
    rid = _s(theory, rid, "map_tile(X)", ("relic_node(X)",))
    rid = _s(theory, rid, "map_tile(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "map_tile(X)", ("asteroid_tile(X)",))
    rid = _s(theory, rid, "map_tile(X)", ("empty_tile(X)",))

    # ── Unit properties (strict) ──────────────────────────────────────────────
    rid = _s(theory, rid, "is_mobile(X)", ("ship(X)",))
    rid = _s(theory, rid, "can_move(X)", ("ship(X)",))
    rid = _s(theory, rid, "can_fire_laser(X)", ("ship(X)",))
    rid = _s(theory, rid, "has_sensor_range(X)", ("ship(X)",))
    rid = _s(theory, rid, "requires_energy(X)", ("ship(X)",))
    rid = _s(theory, rid, "can_collect_energy(X)", ("ship(X)",))
    rid = _s(theory, rid, "can_score_relics(X)", ("ship(X)",))
    rid = _s(theory, rid, "can_be_destroyed(X)", ("ship(X)",))
    rid = _s(theory, rid, "respawns_after_destruction(X)", ("ship(X)",))

    # ── Terrain and hazard properties (strict) ────────────────────────────────
    rid = _s(theory, rid, "passable(X)", ("empty_tile(X)",))
    rid = _s(theory, rid, "passable(X)", ("energy_node(X)",))
    rid = _s(theory, rid, "passable(X)", ("relic_node(X)",))
    rid = _s(theory, rid, "passable(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "impassable(X)", ("asteroid_tile(X)",))
    rid = _s(theory, rid, "grants_energy(X)", ("energy_node(X)",))
    rid = _s(theory, rid, "drains_energy(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "provides_cover(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "reduces_vision(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "spawns_relic_fragments(X)", ("relic_node(X)",))
    rid = _s(theory, rid, "blocks_movement(X)", ("asteroid_tile(X)",))
    rid = _s(theory, rid, "drifts_across_map(X)", ("nebula_tile(X)",))
    rid = _s(theory, rid, "drifts_across_map(X)", ("asteroid_tile(X)",))

    # ── Collision physics (strict) ────────────────────────────────────────────
    # Two ships on the same tile collide and are both destroyed
    rid = _s(theory, rid, "collision_destroys(X)", ("ship(X)",))
    rid = _s(theory, rid, "asteroid_impact_destroys(X)", ("ship(X)",))

    # ── Energy physics (strict) ───────────────────────────────────────────────
    rid = _s(theory, rid, "gains_energy_per_step(X)", ("ship_on_energy_node(X)",))
    rid = _s(theory, rid, "loses_energy_per_step(X)", ("ship_on_nebula(X)",))
    rid = _s(theory, rid, "loses_energy_on_move(X)", ("ship(X)",))
    rid = _s(theory, rid, "dies_at_zero_energy(X)", ("ship(X)",))

    # ── Scoring mechanics (strict) ────────────────────────────────────────────
    rid = _s(theory, rid, "scores_point_when_adjacent(X)", ("ship(X)",))
    rid = _s(theory, rid, "earns_team_point(X)", ("ship_adjacent_to_relic(X)",))

    # ── Sensor and vision physics (strict) ────────────────────────────────────
    rid = _s(theory, rid, "observes_tiles_in_range(X)", ("ship(X)",))
    rid = _s(theory, rid, "hidden_from_opponent(X)", ("ship_in_nebula(X)",))

    # ── Team membership (strict) ──────────────────────────────────────────────
    rid = _s(theory, rid, "is_allied(X,Y)", ("same_team(X,Y)",))
    rid = _s(theory, rid, "is_hostile(X,Y)", ("opposing_team(X,Y)",))

    # ── Match state types (strict) ────────────────────────────────────────────
    rid = _s(theory, rid, "is_match_phase(X)", ("early_match(X)",))
    rid = _s(theory, rid, "is_match_phase(X)", ("mid_match(X)",))
    rid = _s(theory, rid, "is_match_phase(X)", ("late_match(X)",))
    rid = _s(theory, rid, "is_match_phase(X)", ("final_match(X)",))

    # ── Energy state types (strict) ───────────────────────────────────────────
    rid = _s(theory, rid, "is_energy_state(X)", ("critical_energy(X)",))
    rid = _s(theory, rid, "is_energy_state(X)", ("low_energy(X)",))
    rid = _s(theory, rid, "is_energy_state(X)", ("healthy_energy(X)",))
    rid = _s(theory, rid, "is_energy_state(X)", ("full_energy(X)",))
    rid = _s(theory, rid, "needs_recharge(X)", ("critical_energy(X)",))
    rid = _s(theory, rid, "needs_recharge(X)", ("low_energy(X)",))

    # ── Threat types (strict) ─────────────────────────────────────────────────
    rid = _s(theory, rid, "is_threat(X)", ("adjacent_enemy(X)",))
    rid = _s(theory, rid, "is_threat(X)", ("approaching_enemy(X)",))
    rid = _s(theory, rid, "is_threat(X)", ("laser_incoming(X)",))
    rid = _s(theory, rid, "is_threat(X)", ("contested_relic(X)",))
    rid = _s(theory, rid, "immediate_threat(X)", ("adjacent_enemy(X)",))
    rid = _s(theory, rid, "immediate_threat(X)", ("laser_incoming(X)",))

    # ── Add instance facts ────────────────────────────────────────────────────
    _add_unit_instances(theory)
    _add_terrain_instances(theory)
    _add_match_instances(theory)

    return theory


def _add_unit_instances(theory: Theory) -> None:
    """Add concrete ship and unit instances."""
    # Team A ships (player 1)
    for i in range(1, 6):
        theory.add_fact(f"game_object(ship_a{i})")
        theory.add_fact(f"unit(ship_a{i})")
        theory.add_fact(f"ship(ship_a{i})")
        theory.add_fact(f"same_team(ship_a{i}, ship_a{i})")

    # Team B ships (player 2)
    for i in range(1, 6):
        theory.add_fact(f"game_object(ship_b{i})")
        theory.add_fact(f"unit(ship_b{i})")
        theory.add_fact(f"ship(ship_b{i})")
        theory.add_fact(f"same_team(ship_b{i}, ship_b{i})")

    # Cross-team hostility
    for i in range(1, 4):
        for j in range(1, 4):
            theory.add_fact(f"opposing_team(ship_a{i}, ship_b{j})")
            theory.add_fact(f"opposing_team(ship_b{j}, ship_a{i})")


def _add_terrain_instances(theory: Theory) -> None:
    """Add map tile instances representing key terrain features."""
    energy_nodes = [
        'north_energy_cluster', 'south_energy_cluster',
        'center_energy_node', 'flank_energy_node',
    ]
    for name in energy_nodes:
        theory.add_fact(f"map_tile({name})")
        theory.add_fact(f"energy_node({name})")

    relic_nodes = [
        'relic_alpha', 'relic_beta', 'relic_gamma',
        'relic_delta', 'relic_epsilon',
    ]
    for name in relic_nodes:
        theory.add_fact(f"map_tile({name})")
        theory.add_fact(f"relic_node({name})")

    nebula_tiles = [
        'nebula_north', 'nebula_center', 'nebula_south',
    ]
    for name in nebula_tiles:
        theory.add_fact(f"map_tile({name})")
        theory.add_fact(f"nebula_tile({name})")

    asteroid_tiles = ['asteroid_cluster_a', 'asteroid_cluster_b']
    for name in asteroid_tiles:
        theory.add_fact(f"map_tile({name})")
        theory.add_fact(f"asteroid_tile({name})")


def _add_match_instances(theory: Theory) -> None:
    """Add match phase and energy state instances."""
    phases = [
        ('match_phase_1', 'early_match'),
        ('match_phase_2', 'mid_match'),
        ('match_phase_3', 'mid_match'),
        ('match_phase_4', 'late_match'),
        ('match_phase_5', 'final_match'),
    ]
    for name, phase_type in phases:
        theory.add_fact(f"match_phase({name})")
        theory.add_fact(f"{phase_type}({name})")

    energy_states = [
        ('ship_a1', 'healthy_energy'),
        ('ship_a2', 'critical_energy'),
        ('ship_a3', 'low_energy'),
        ('ship_b1', 'healthy_energy'),
        ('ship_b2', 'full_energy'),
    ]
    for ship, estate in energy_states:
        theory.add_fact(f"{estate}({ship})")

    # Threat instances
    theory.add_fact("adjacent_enemy(ship_a2)")
    theory.add_fact("laser_incoming(ship_a3)")
    theory.add_fact("contested_relic(relic_alpha)")
    theory.add_fact("approaching_enemy(ship_a1)")
