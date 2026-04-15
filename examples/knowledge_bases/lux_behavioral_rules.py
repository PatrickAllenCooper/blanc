"""
Lux AI Season 3 -- Defeasible Behavioral Rules and Defeaters

Defeasible rules encoding ROE-style behavioral norms for Lux AI S3 ships.
The structure precisely mirrors the Newport ROE Handbook framework used for
the SC2 engagement KB -- default operational rules that hold by default,
defeaters that encode exceptions, and superiority relations encoding
the priority hierarchy.

Lux AI S3 ROE hierarchy:
    self-preservation (energy/collision survival) > scoring objectives
        > resource efficiency > general movement policy

This mirrors the Newport Handbook's:
    self-defense > mission constraints > general policy

The conservativity requirement from DeFAb applies directly: a defeater
activating self-preservation must override only the specific objective
rule it defeats, not the entire behavioral framework.

Visual analog for the demo: the s3vis.lux-ai.org web visualizer shows
ships navigating around relic nodes and nebulae -- exactly the situations
where these defeaters fire.

Lux AI S3 mechanics:
    - Ships gain energy on energy nodes, lose it in nebulae
    - Ships score points when adjacent to relic nodes
    - Two ships on the same tile collide (both destroyed)
    - Nebulae reduce sensor range and drain energy
    - Asteroids are impassable and drift across the map

Author: Patrick Cooper
"""

from blanc.core.theory import Theory, Rule, RuleType


def _r(theory: Theory, rid: int, head: str, body: tuple,
       rtype: RuleType = RuleType.DEFEASIBLE) -> int:
    """Add a rule and return the next rule id."""
    theory.add_rule(Rule(
        head=head, body=body, rule_type=rtype,
        label=f"lux_r{rid}",
    ))
    return rid + 1


def add_lux_behavioral_rules(theory: Theory) -> Theory:
    """
    Add defeasible ROE behavioral rules and defeaters to a Lux AI S3 KB.

    Rule label prefix: lux_r, starting at 5000.
    """

    rid = 5000

    # ────────────────────────────────────────────────────────────────────────
    # 1. MOVEMENT POLICY -- DEFAULT: move toward nearest relic node
    # ────────────────────────────────────────────────────────────────────────

    # Default operational objective: pursue relics to score points
    rid = _r(theory, rid, "ordered_to_advance_on_relic(X)",
             ("ship(X)", "relic_reachable(X)"))

    rid = _r(theory, rid, "ordered_to_advance_on_relic(X)",
             ("ship(X)", "early_match(M)", "current_match_phase(X,M)"))

    rid = _r(theory, rid, "ordered_to_advance_on_relic(X)",
             ("ship(X)", "mid_match(M)", "current_match_phase(X,M)",
              "score_deficit(X)"))

    # ── Relic advance defeaters ───────────────────────────────────────────────

    # Energy critical: abandon relic pursuit, recharge first
    rid = _r(theory, rid, "~ordered_to_advance_on_relic(X)",
             ("ship(X)", "critical_energy(X)"),
             RuleType.DEFEATER)

    # Low energy in nebula: retreat to energy node before advancing
    rid = _r(theory, rid, "~ordered_to_advance_on_relic(X)",
             ("ship(X)", "low_energy(X)", "ship_in_nebula(X)"),
             RuleType.DEFEATER)

    # Relic is contested by superior enemy force: avoid, seek uncontested relic
    rid = _r(theory, rid, "~ordered_to_advance_on_relic(X)",
             ("ship(X)", "contested_relic(R)", "nearest_relic_is(X,R)",
              "enemy_has_numerical_advantage_at(R)"),
             RuleType.DEFEATER)

    # Final match, losing on score: all units must push contested relics
    rid = _r(theory, rid, "~ordered_to_advance_on_relic(X)",
             ("ship(X)", "contested_relic(R)", "nearest_relic_is(X,R)",
              "final_match(M)", "current_match_phase(X,M)",
              "score_deficit(X)"),  # This is a double-negative: push anyway
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 2. ENERGY HARVESTING -- DEFAULT: collect energy when passing nodes
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "ordered_to_harvest_energy(X)",
             ("ship(X)", "energy_node_adjacent(X)"))

    rid = _r(theory, rid, "ordered_to_harvest_energy(X)",
             ("ship(X)", "low_energy(X)", "energy_node_reachable(X)"))

    rid = _r(theory, rid, "ordered_to_harvest_energy(X)",
             ("ship(X)", "critical_energy(X)"))

    # ── Energy harvesting defeaters ───────────────────────────────────────────

    # Relic scoring opportunity overrides energy harvesting (when energy healthy)
    rid = _r(theory, rid, "~ordered_to_harvest_energy(X)",
             ("ship(X)", "healthy_energy(X)", "relic_in_scoring_range(X)"),
             RuleType.DEFEATER)

    # Enemy about to contest a relic -- must defend position, not harvest
    rid = _r(theory, rid, "~ordered_to_harvest_energy(X)",
             ("ship(X)", "relic_under_immediate_threat(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 3. COLLISION AVOIDANCE -- DEFAULT: avoid occupied tiles
    #    This is the Lux AI S3 analog of "worker protection" / "civilian area"
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "must_avoid_tile(X,T)",
             ("ship(X)", "ship_on_tile(Y,T)", "is_allied(X,Y)"))

    rid = _r(theory, rid, "must_avoid_tile(X,T)",
             ("ship(X)", "ship_on_tile(Y,T)", "is_hostile(X,Y)",
              "not_in_attack_posture(X)"))

    rid = _r(theory, rid, "must_avoid_tile(X,T)",
             ("ship(X)", "asteroid_tile(T)"))

    # ── Collision avoidance defeaters ──────────────────────────────────────────

    # Intentional collision: use unit as weapon against enemy when score tied
    # and time is running out (the "kamikaze" exception)
    rid = _r(theory, rid, "~must_avoid_tile(X,T)",
             ("ship(X)", "ship_on_tile(Y,T)", "is_hostile(X,Y)",
              "score_tied", "final_match(M)", "current_match_phase(X,M)",
              "low_steps_remaining"),
             RuleType.DEFEATER)

    # Forced path: asteroid drift has closed all other routes
    rid = _r(theory, rid, "~must_avoid_tile(X,T)",
             ("ship(X)", "ship_on_tile(Y,T)", "is_allied(X,Y)",
              "no_alternative_path(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 4. NEBULA AVOIDANCE -- DEFAULT: avoid nebula tiles (drain energy + hide)
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "must_avoid_nebula(X)",
             ("ship(X)", "healthy_energy(X)"))

    rid = _r(theory, rid, "must_avoid_nebula(X)",
             ("ship(X)", "pursuing_relic(X)"))

    # ── Nebula avoidance defeaters ─────────────────────────────────────────────

    # Stealth posture: enter nebula to hide from enemy sensor range
    rid = _r(theory, rid, "~must_avoid_nebula(X)",
             ("ship(X)", "enemy_sensor_will_detect(X)",
              "stealth_needed(X)"),
             RuleType.DEFEATER)

    # Enemy laser incoming: dodge into nebula even at energy cost
    rid = _r(theory, rid, "~must_avoid_nebula(X)",
             ("ship(X)", "laser_incoming(X)"),
             RuleType.DEFEATER)

    # Relic node is in nebula: accept energy drain to score
    rid = _r(theory, rid, "~must_avoid_nebula(X)",
             ("ship(X)", "relic_in_nebula(R)", "nearest_relic_is(X,R)",
              "healthy_energy(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 5. SELF-PRESERVATION -- DEFAULT: retreat when energy critical
    #    This is the Lux AI S3 analog of "self-defense override"
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "ordered_to_retreat_to_energy(X)",
             ("ship(X)", "critical_energy(X)"))

    rid = _r(theory, rid, "ordered_to_retreat_to_energy(X)",
             ("ship(X)", "low_energy(X)", "immediate_threat(T)",
              "threat_affects(T,X)"))

    # Self-preservation overrides all objective rules above
    rid = _r(theory, rid, "all_objectives_suspended(X)",
             ("ordered_to_retreat_to_energy(X)",))

    # ── Self-preservation defeaters ────────────────────────────────────────────

    # Win condition overrides retreat: if retreating means losing the match,
    # fight on
    rid = _r(theory, rid, "~ordered_to_retreat_to_energy(X)",
             ("ship(X)", "critical_energy(X)", "final_match(M)",
              "current_match_phase(X,M)", "ship_adjacent_to_relic(X)",
              "score_tied"),
             RuleType.DEFEATER)

    # Spawn camping: ally can immediately respawn on your position
    rid = _r(theory, rid, "~ordered_to_retreat_to_energy(X)",
             ("ship(X)", "critical_energy(X)", "spawn_covered(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 6. LASER ENGAGEMENT POLICY -- DEFAULT: do not fire lasers at allies
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "prohibited_from_firing(X,Y)",
             ("ship(X)", "ship(Y)", "is_allied(X,Y)"))

    # Firing at an enemy costs energy; only fire if beneficial
    rid = _r(theory, rid, "prohibited_from_firing(X,Y)",
             ("ship(X)", "ship(Y)", "is_hostile(X,Y)",
              "not_in_attack_posture(X)"))

    # ── Laser firing defeaters ─────────────────────────────────────────────────

    # Enemy is blocking your relic path and has more energy
    rid = _r(theory, rid, "~prohibited_from_firing(X,Y)",
             ("ship(X)", "ship(Y)", "is_hostile(X,Y)",
              "blocking_relic_access(Y,X)", "healthy_energy(X)"),
             RuleType.DEFEATER)

    # Enemy adjacent and you have energy advantage
    rid = _r(theory, rid, "~prohibited_from_firing(X,Y)",
             ("ship(X)", "ship(Y)", "adjacent_enemy(X)",
              "is_hostile(X,Y)", "energy_advantage_over(X,Y)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 7. STEALTH POSTURE -- DEFAULT: stay visible when pursuing objectives
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "maintain_visibility(X)",
             ("ship(X)", "pursuing_relic(X)"))

    rid = _r(theory, rid, "maintain_visibility(X)",
             ("ship(X)", "healthy_energy(X)", "no_nearby_enemy(X)"))

    # ── Stealth defeaters ─────────────────────────────────────────────────────

    # Approaching enemy will detect and destroy: enter nebula
    rid = _r(theory, rid, "~maintain_visibility(X)",
             ("ship(X)", "approaching_enemy(X)", "nebula_reachable(X)"),
             RuleType.DEFEATER)

    # Under direct laser fire: take cover in nebula immediately
    rid = _r(theory, rid, "~maintain_visibility(X)",
             ("ship(X)", "laser_incoming(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 8. META-LEARNING POSTURE -- UNIQUE TO LUX AI S3
    #    In the 5-match sequence, game parameters change. The agent must
    #    probe to learn them.
    # ────────────────────────────────────────────────────────────────────────

    # In match 1 (no prior data), explore energy nodes to measure yields
    rid = _r(theory, rid, "should_probe_energy_node(X,N)",
             ("ship(X)", "energy_node(N)", "early_match(M)",
              "current_match_phase(X,M)", "energy_node_yield_unknown(N)"))

    # In match 1, probe nebula to measure energy drain rate
    rid = _r(theory, rid, "should_probe_nebula_tile(X,T)",
             ("ship(X)", "nebula_tile(T)", "early_match(M)",
              "current_match_phase(X,M)", "nebula_drain_unknown(T)"))

    # ── Meta-learning defeaters ────────────────────────────────────────────────

    # Known parameters: stop probing, exploit
    rid = _r(theory, rid, "~should_probe_energy_node(X,N)",
             ("energy_node_yield_known(N)",),
             RuleType.DEFEATER)

    rid = _r(theory, rid, "~should_probe_nebula_tile(X,T)",
             ("nebula_drain_known(T)",),
             RuleType.DEFEATER)

    # Combat emergency: don't probe when enemy is adjacent
    rid = _r(theory, rid, "~should_probe_energy_node(X,N)",
             ("ship(X)", "adjacent_enemy(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 9. COMPOUND BEHAVIORAL RULES
    # ────────────────────────────────────────────────────────────────────────

    # Cleared to score: ship can attempt to reach relic node
    rid = _r(theory, rid, "cleared_to_score(X)",
             ("ship(X)", "ordered_to_advance_on_relic(X)",
              "not_ordered_to_retreat_to_energy(X)"))

    # Cleared to score under self-defense: energy critical but adjacent to relic
    rid = _r(theory, rid, "cleared_to_score(X)",
             ("ship(X)", "ship_adjacent_to_relic(X)",
              "score_tied", "final_match(M)", "current_match_phase(X,M)"))

    # Optimal positioning: at energy node AND adjacent to relic
    rid = _r(theory, rid, "optimal_position(X)",
             ("ship(X)", "ship_on_energy_node(X)", "ship_adjacent_to_relic(X)"))

    # Mission accomplished for a match
    rid = _r(theory, rid, "match_won(T)",
             ("team(T)", "score_lead_at_end(T)"))

    # ── Compound defeaters ─────────────────────────────────────────────────────

    # Cannot score if ship is destroyed (obvious, but needed for completeness)
    rid = _r(theory, rid, "~cleared_to_score(X)",
             ("ship_destroyed(X)",),
             RuleType.DEFEATER)

    # Friendly fire risk: laser alignment with ally defeats firing clearance
    rid = _r(theory, rid, "~cleared_to_score(X)",
             ("ship(X)", "ally_in_laser_path(X)"),
             RuleType.DEFEATER)

    return theory


def add_lux_superiority_relations(theory: Theory) -> None:
    """
    Register superiority relations among Lux AI behavioral rules.

    Encoding the Lux AI S3 behavioral hierarchy:
        self-preservation > scoring objectives > resource efficiency > general movement

    Self-preservation rules (lux_r5021) override relic advance defeaters
    (lux_r5002, lux_r5003, lux_r5004).

    This is the structural analog of the Newport Handbook hierarchy:
        self-defense > mission constraints > general policy
    """

    # ── Self-preservation overrides relic advance ────────────────────────────
    # "ordered_to_retreat_to_energy(X)" (lux_r5021) beats
    # "ordered_to_advance_on_relic(X)" (lux_r5000)
    theory.add_superiority("lux_r5021", "lux_r5000")
    theory.add_superiority("lux_r5021", "lux_r5001")
    theory.add_superiority("lux_r5021", "lux_r5002")

    # ── Energy critical defeater overrides relic harvest ────────────────────
    # "~ordered_to_harvest_energy(X) :- healthy_energy, relic_in_range" (lux_r5013)
    # beaten by critical energy retreat (lux_r5021)
    theory.add_superiority("lux_r5021", "lux_r5013")

    # ── Self-preservation overrides nebula avoidance ─────────────────────────
    # "~must_avoid_nebula(X) :- laser_incoming(X)" (lux_r5020)
    # -- emergency evasion beats general nebula avoidance
    theory.add_superiority("lux_r5020", "lux_r5016")  # laser > general avoid
    theory.add_superiority("lux_r5019", "lux_r5016")  # stealth need > general avoid

    # ── Win condition override beats self-preservation ───────────────────────
    # "~ordered_to_retreat_to_energy(X) :- score_tied, final_match, adjacent_relic"
    # (lux_r5024) beats standard retreat (lux_r5021)
    theory.add_superiority("lux_r5024", "lux_r5021")

    # ── Relic scoring beats energy harvesting (when healthy) ─────────────────
    theory.add_superiority("lux_r5013", "lux_r5010")  # relic > harvest

    # ── Known parameters beat probing ────────────────────────────────────────
    theory.add_superiority("lux_r5036", "lux_r5030")  # known yield > probe
    theory.add_superiority("lux_r5037", "lux_r5031")  # known drain > probe

    # ── Laser engagement beats passive avoidance ─────────────────────────────
    theory.add_superiority("lux_r5034", "lux_r5027")  # blocking > no-fire
    theory.add_superiority("lux_r5035", "lux_r5028")  # energy advantage > no-fire


def count_lux_behavioral_rules(theory: Theory) -> dict:
    """Return a breakdown of Lux AI behavioral rule counts by type."""
    lux_rules = [r for r in theory.rules if r.label and r.label.startswith("lux_r")]
    defeasible = [r for r in lux_rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in lux_rules if r.rule_type == RuleType.DEFEATER]
    return {
        "total_behavioral": len(lux_rules),
        "defeasible": len(defeasible),
        "defeaters": len(defeaters),
    }
