"""
RTS Engagement -- Defeasible ROE Rules and Defeaters

Defeasible rules encoding rules of engagement (ROE) for a generic RTS
environment modeled on StarCraft II.  These rules hold by default but admit
exceptions -- the defeaters below -- mirroring the structure of real-world ROE
as analyzed in the Newport Rules of Engagement Handbook (Stockton Center for
International Law, Naval War College).

ROE structure (from the Newport Handbook, Section 4):
    - Default rules: mission constraints that govern behavior under normal
      conditions (force protection, collateral avoidance, proportionality).
    - Defeaters: self-defense overrides, escalation triggers, commander
      discretion.  When a hostile act or hostile intent is detected, the
      relevant mission constraint is defeated, and the unit may respond with
      necessary and proportionate force.
    - Superiority relations: self-defense > mission constraints > general
      policy.  The Handbook states explicitly that limitations on mission
      accomplishment "have no impact on the commander's inherent right and
      obligation to exercise self-defense."

The conservativity requirement from DeFAb applies directly: a defeater that
activates self-defense must defeat only the specific constraint it overrides,
not the entire ROE framework.

Grounding in the literature:
- Newport ROE Handbook (Stockton Center for International Law, 2022, §4).
- "Planning in RTS Games with Incomplete Action Definitions via ASP"
  (AIIDE 2015) for SC2 behavioral rule patterns.
- Lockheed Martin StarCraft II ROE proxy (personal communication, Tom Lee,
  Lockheed Martin, April 2026).

Author: Anonymous Authors
"""

from blanc.core.theory import Theory, Rule, RuleType


def _r(theory: Theory, rid: int, head: str, body: tuple,
       rtype: RuleType = RuleType.DEFEASIBLE) -> int:
    """Add a rule and return the next rule id."""
    theory.add_rule(Rule(
        head=head, body=body, rule_type=rtype,
        label=f"rts_r{rid}",
    ))
    return rid + 1


def add_rts_behavioral_rules(theory: Theory) -> Theory:
    """
    Add defeasible ROE rules and defeaters to an RTS engagement KB.

    Rule label prefix: rts_r, starting at 3000.
    """

    rid = 3000

    # ────────────────────────────────────────────────────────────────────────
    # 1. ENGAGEMENT AUTHORITY -- DEFAULT: authorization to engage
    # ────────────────────────────────────────────────────────────────────────

    # A military unit may engage a military target by default
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "military_target(Y)"))

    # A unit in a designated engagement zone may engage
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "in_zone(X, engagement_zone_alpha)", "military_target(Y)"))

    # During an offensive operation all military units may engage
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "assigned_to_mission(X, op_thunderbolt)", "military_target(Y)"))

    # ── Engagement authority defeaters ────────────────────────────────────────

    # Prohibited: engage in an exclusion zone
    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("in_zone(X, restricted_zone_alpha)", "in_zone(Y, restricted_zone_alpha)"),
             RuleType.DEFEATER)

    # Prohibited: engage near allied base (collateral risk)
    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("in_zone(Y, main_base)",),
             RuleType.DEFEATER)

    # Prohibited: engage in civilian area
    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("in_zone(Y, worker_mining_area)",),
             RuleType.DEFEATER)

    # Stealth mission: no engagement while maintaining stealth posture
    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("assigned_to_mission(X, op_ghost_eye)", "stealth_posture_active(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 2. SELF-DEFENSE OVERRIDE -- defeats engagement restrictions when hostile
    #    act or hostile intent is detected (Newport Handbook §4.4)
    # ────────────────────────────────────────────────────────────────────────

    # Self-defense authorization: unit under direct fire may always respond
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "under_direct_fire(X)", "hostile_unit(Y)"))

    # Hostile act detected: nearby threat justifies engagement
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "hostile_act_detected_near(X,Y)"))

    # Critical threat overrides exclusion zone restriction
    rid = _r(theory, rid, "authorized_to_engage(X,Y)",
             ("military_unit(X)", "critical_threat(Y)", "under_direct_fire(X)"))

    # ── Self-defense defeaters (override the ROE defeaters above) ────────────

    # Self-defense defeats exclusion zone prohibition
    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("in_zone(X, restricted_zone_alpha)", "not_under_attack(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 3. WORKER PROTECTION -- default: do not attack worker units
    # ────────────────────────────────────────────────────────────────────────

    # Workers are noncombatants by default
    rid = _r(theory, rid, "protected_from_attack(W)", ("worker_target(W)",))
    rid = _r(theory, rid, "~authorized_to_engage(X,W)",
             ("protected_from_attack(W)",),
             RuleType.DEFEATER)

    # ── Worker protection defeaters ───────────────────────────────────────────

    # Exception: workers repairing a structure under attack may be targeted
    rid = _r(theory, rid, "~protected_from_attack(W)",
             ("worker_target(W)", "repairing_under_attack(W)"),
             RuleType.DEFEATER)

    # Exception: workers constructing siege positions may be targeted
    rid = _r(theory, rid, "~protected_from_attack(W)",
             ("worker_target(W)", "constructing_siege_position(W)"),
             RuleType.DEFEATER)

    # Exception: all-in rush -- economic base under existential threat
    rid = _r(theory, rid, "~protected_from_attack(W)",
             ("worker_target(W)", "all_in_rush_detected"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 4. PROPORTIONALITY -- default: use minimum force sufficient to resolve threat
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "must_use_minimum_force(X)",
             ("military_unit(X)", "low_threat_environment(X)"))
    rid = _r(theory, rid, "must_use_minimum_force(X)",
             ("military_unit(X)", "civilian_proximity(X)"))

    # If minimum force applies, splash-damage weapons are restricted
    rid = _r(theory, rid, "restricted_weapon_use(X,Y)",
             ("must_use_minimum_force(X)", "has_splash_damage(X)", "noncombatant_area(Y)"))

    # ── Proportionality defeaters ─────────────────────────────────────────────

    # High threat overrides minimum-force requirement
    rid = _r(theory, rid, "~must_use_minimum_force(X)",
             ("high_threat(T)", "force_under_attack_from(X,T)"),
             RuleType.DEFEATER)

    # Critical threat overrides minimum force and unrestricts all weapons
    rid = _r(theory, rid, "~must_use_minimum_force(X)",
             ("military_unit(X)", "critical_threat(T)", "requires_immediate_response(T)"),
             RuleType.DEFEATER)

    rid = _r(theory, rid, "~restricted_weapon_use(X,Y)",
             ("military_unit(X)", "critical_threat(T)", "requires_immediate_response(T)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 5. RETREAT AND FORCE PRESERVATION -- default: retreat when outnumbered
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "ordered_to_retreat(X)",
             ("military_unit(X)", "has_numerical_disadvantage(X)"))
    rid = _r(theory, rid, "ordered_to_retreat(X)",
             ("military_unit(X)", "is_isolated(X)", "no_reinforcement_available"))
    rid = _r(theory, rid, "ordered_to_retreat(X)",
             ("military_unit(X)", "critical_supply_shortage(X)"))

    # ── Retreat defeaters ─────────────────────────────────────────────────────

    # Holding a choke point: retreat is prohibited to preserve position
    rid = _r(theory, rid, "~ordered_to_retreat(X)",
             ("military_unit(X)", "holding_choke_point(X)"),
             RuleType.DEFEATER)

    # All-in rush: units retreating due to numerical disadvantage must hold to protect base.
    # Scoped to has_numerical_disadvantage so isolation-based or supply-shortage retreat
    # triggers remain active for units not in numerical jeopardy (conservativity).
    rid = _r(theory, rid, "~ordered_to_retreat(X)",
             ("military_unit(X)", "all_in_rush_detected", "has_numerical_disadvantage(X)"),
             RuleType.DEFEATER)

    # High-value target is in range and fleeing: pursue rather than retreat
    rid = _r(theory, rid, "~ordered_to_retreat(X)",
             ("military_unit(X)", "high_value_target_in_range(X)",
              "target_attempting_escape"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 6. STEALTH POSTURE -- default: maintain stealth during recon missions
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "stealth_posture_active(X)",
             ("military_unit(X)", "assigned_to_mission(X, op_ghost_eye)"))
    rid = _r(theory, rid, "stealth_posture_active(X)",
             ("military_unit(X)", "assigned_to_mission(X, op_safe_passage)"))

    # Stealth posture means: do not engage, avoid detection
    rid = _r(theory, rid, "must_avoid_engagement(X)",
             ("stealth_posture_active(X)",))
    rid = _r(theory, rid, "must_avoid_detection(X)",
             ("stealth_posture_active(X)",))

    # ── Stealth defeaters ──────────────────────────────────────────────────────

    # Unit under direct fire must break stealth to return fire
    rid = _r(theory, rid, "~stealth_posture_active(X)",
             ("under_direct_fire(X)",),
             RuleType.DEFEATER)

    # Asset being escorted is targeted: stealth broken to protect asset
    rid = _r(theory, rid, "~stealth_posture_active(X)",
             ("escorted_asset_under_attack(X)",),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 7. TARGET PRIORITIZATION -- default priority ordering
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "priority_target(X,Y)",
             ("military_unit(X)", "high_value_target(Y)", "authorized_to_engage(X,Y)"))
    rid = _r(theory, rid, "priority_target(X,Y)",
             ("military_unit(X)", "anti_air_target(Y)", "is_air_unit(X)"))
    rid = _r(theory, rid, "priority_target(X,Y)",
             ("military_unit(X)", "production_structure(Y)", "authorized_to_engage(X,Y)"))

    # Default: attack nearest threat
    rid = _r(theory, rid, "engage_nearest_threat(X)",
             ("military_unit(X)", "authorized_to_engage(X,Y)", "nearest_threat_identified(X)"))

    # ── Target priority defeaters ──────────────────────────────────────────────

    # If a critical threat is present, drop all other priority rules
    rid = _r(theory, rid, "~priority_target(X,Y)",
             ("critical_threat(T)", "critical_threat_closer_than(T,Y,X)"),
             RuleType.DEFEATER)

    # Do not engage infrastructure during ceasefire negotiation
    rid = _r(theory, rid, "~priority_target(X,Y)",
             ("production_structure(Y)", "ceasefire_in_effect"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 8. FORCE CONCENTRATION -- default tactical behaviors
    # ────────────────────────────────────────────────────────────────────────

    rid = _r(theory, rid, "concentrate_forces(X)",
             ("military_unit(X)", "has_numerical_advantage(X)"))
    rid = _r(theory, rid, "hold_formation(X)",
             ("military_unit(X)", "defensive_operation(M)", "assigned_to_mission(X,M)"))
    rid = _r(theory, rid, "advance_on_objective(X)",
             ("military_unit(X)", "offensive_operation(M)", "assigned_to_mission(X,M)",
              "path_to_objective_clear(X)"))
    rid = _r(theory, rid, "secure_high_ground(X)",
             ("military_unit(X)", "high_ground_available(X)", "no_enemy_presence(X)"))
    rid = _r(theory, rid, "establish_perimeter(X)",
             ("military_unit(X)", "at_objective(X)"))

    # ── Force concentration defeaters ──────────────────────────────────────────

    # Encircled force: concentrate is impossible, break out instead
    rid = _r(theory, rid, "~concentrate_forces(X)",
             ("is_encircled(X)",),
             RuleType.DEFEATER)

    # Air superiority threat: disperse to avoid splash damage
    rid = _r(theory, rid, "~hold_formation(X)",
             ("air_superiority_threat(X)",),
             RuleType.DEFEATER)

    # Enemy has high ground and we are advancing: hold until artillery available
    rid = _r(theory, rid, "~advance_on_objective(X)",
             ("enemy_holds_high_ground(X)", "no_artillery_support(X)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 9. INTELLIGENCE AND IDENTIFICATION -- default: require positive ID
    # ────────────────────────────────────────────────────────────────────────

    # Positive identification of hostile unit required before engagement
    rid = _r(theory, rid, "requires_positive_id(X,Y)",
             ("military_unit(X)", "is_target_type(Y)"))

    rid = _r(theory, rid, "~authorized_to_engage(X,Y)",
             ("requires_positive_id(X,Y)", "not_positively_identified(Y)"),
             RuleType.DEFEATER)

    # ── PID defeaters ──────────────────────────────────────────────────────────

    # Cloaked unit cannot be positively identified without sensor support;
    # but if sensor unit detects it, PID is satisfied
    rid = _r(theory, rid, "~requires_positive_id(X,Y)",
             ("sensor_detected(Y)",),
             RuleType.DEFEATER)

    # Under direct fire the attacking unit is automatically positively identified
    rid = _r(theory, rid, "~requires_positive_id(X,Y)",
             ("under_direct_fire(X)", "fire_originated_from(X,Y)"),
             RuleType.DEFEATER)

    # ────────────────────────────────────────────────────────────────────────
    # 10. COMPOUND ROE RULES -- combinations that reflect doctrine
    # ────────────────────────────────────────────────────────────────────────

    # A unit is cleared to engage iff authorized and positively identified
    rid = _r(theory, rid, "cleared_to_engage(X,Y)",
             ("authorized_to_engage(X,Y)", "not_requires_positive_id(X,Y)"))
    rid = _r(theory, rid, "cleared_to_engage(X,Y)",
             ("authorized_to_engage(X,Y)", "sensor_detected(Y)"))

    # Under-fire response: always cleared regardless of other constraints
    rid = _r(theory, rid, "cleared_to_engage(X,Y)",
             ("under_direct_fire(X)", "fire_originated_from(X,Y)"))

    # Mission success condition: objective secured and no active threats
    rid = _r(theory, rid, "mission_accomplished(M)",
             ("offensive_operation(M)", "objective_secured(M)", "no_active_threats(M)"))
    rid = _r(theory, rid, "mission_accomplished(M)",
             ("defensive_operation(M)", "perimeter_held(M)", "no_active_threats(M)"))

    # ── Compound defeaters ──────────────────────────────────────────────────────

    # Friendly fire risk defeats cleared_to_engage
    rid = _r(theory, rid, "~cleared_to_engage(X,Y)",
             ("friendly_unit_in_line_of_fire(X,Y)",),
             RuleType.DEFEATER)

    # Mission accomplished defeated if friendly casualties exceed threshold
    rid = _r(theory, rid, "~mission_accomplished(M)",
             ("excessive_friendly_casualties(M)",),
             RuleType.DEFEATER)

    return theory


def add_rts_superiority_relations(theory: Theory) -> None:
    """
    Register superiority relations among RTS ROE rules.

    Encoding the Newport Handbook hierarchy:
        self-defense > mission constraints > general engagement policy

    Self-defense rules (rts_r3008, rts_r3009, rts_r3010) override
    exclusion/civilian/stealth defeaters (rts_r3003, rts_r3004, rts_r3005).

    Worker protection defeaters (rts_r3017, rts_r3018, rts_r3019) override
    the worker protection default (rts_r3015).
    """

    # ── Self-defense overrides engagement restrictions ────────────────────────
    #
    # Rule ID trace (rid starts at 3000 in add_rts_behavioral_rules):
    #   rts_r3000 authorized_to_engage :- military_unit, military_target
    #   rts_r3001 authorized_to_engage :- military_unit, in_zone(engagement_zone), military_target
    #   rts_r3002 authorized_to_engage :- military_unit, assigned_to_mission(op_thunderbolt), military_target
    #   rts_r3003 ~authorized_to_engage :- in_zone(X, restricted_zone_alpha), in_zone(Y, restricted_zone_alpha)  [DEFEATER]
    #   rts_r3004 ~authorized_to_engage :- in_zone(Y, main_base)                                                  [DEFEATER]
    #   rts_r3005 ~authorized_to_engage :- in_zone(Y, worker_mining_area)                                         [DEFEATER]
    #   rts_r3006 ~authorized_to_engage :- assigned_to_mission(op_ghost_eye), stealth_posture_active              [DEFEATER]
    #   rts_r3007 authorized_to_engage :- military_unit, under_direct_fire(X), hostile_unit(Y)   <- SELF-DEFENSE
    #   rts_r3008 authorized_to_engage :- military_unit, hostile_act_detected_near(X,Y)          <- HOSTILE ACT
    #   rts_r3009 authorized_to_engage :- military_unit, critical_threat(Y), under_direct_fire(X) <- CRITICAL THREAT
    #
    # Self-defense (rts_r3007) beats all three restriction defeaters
    theory.add_superiority("rts_r3007", "rts_r3003")  # self-defense > exclusion zone
    theory.add_superiority("rts_r3007", "rts_r3004")  # self-defense > allied base restriction
    theory.add_superiority("rts_r3007", "rts_r3005")  # self-defense > civilian area restriction
    theory.add_superiority("rts_r3007", "rts_r3006")  # self-defense > stealth-mission restriction
    # Hostile act detected (rts_r3008) also beats exclusion and civilian restrictions
    theory.add_superiority("rts_r3008", "rts_r3003")  # hostile act > exclusion zone
    theory.add_superiority("rts_r3008", "rts_r3005")  # hostile act > civilian area
    theory.add_superiority("rts_r3008", "rts_r3006")  # hostile act > stealth restriction
    # Critical threat + direct fire (rts_r3009) beats exclusion zone
    theory.add_superiority("rts_r3009", "rts_r3003")  # critical threat > exclusion zone

    # ── Worker protection defeaters override protection default ──────────────
    # "~protected_from_attack(W) :- repairing_under_attack(W)" (rts_r3017)
    # beats "protected_from_attack(W) :- worker_target(W)" (rts_r3014)
    theory.add_superiority("rts_r3017", "rts_r3014")  # repair exception
    theory.add_superiority("rts_r3018", "rts_r3014")  # siege construction exception
    theory.add_superiority("rts_r3019", "rts_r3014")  # all-in rush exception

    # ── High/critical threat overrides proportionality defaults ─────────────
    # rts_r3019: ~must_use_minimum_force :- high_threat  (DEFEATER)
    # rts_r3020: ~must_use_minimum_force :- critical_threat (DEFEATER)
    # rts_r3016: must_use_minimum_force :- low_threat_environment (DEFEASIBLE)
    # rts_r3017: must_use_minimum_force :- civilian_proximity (DEFEASIBLE)
    theory.add_superiority("rts_r3019", "rts_r3017")  # high_threat > civilian_proximity
    theory.add_superiority("rts_r3020", "rts_r3017")  # critical_threat > civilian_proximity
    theory.add_superiority("rts_r3020", "rts_r3016")  # critical_threat > low_threat_env

    # ── Retreat defeaters override retreat defaults ───────────────────────────
    # "~ordered_to_retreat(X) :- holding_choke_point(X)" (rts_r3031)
    # beats "ordered_to_retreat(X) :- has_numerical_disadvantage(X)" (rts_r3027)
    theory.add_superiority("rts_r3031", "rts_r3027")  # hold choke > retreat
    theory.add_superiority("rts_r3032", "rts_r3027")  # all-in rush > retreat
    theory.add_superiority("rts_r3033", "rts_r3027")  # HVT escape > retreat
    theory.add_superiority("rts_r3032", "rts_r3028")  # all-in rush > isolated retreat
    theory.add_superiority("rts_r3032", "rts_r3029")  # all-in rush > supply shortage retreat

    # ── Stealth defeaters override stealth activation ────────────────────────
    theory.add_superiority("rts_r3036", "rts_r3034")  # direct fire breaks stealth
    theory.add_superiority("rts_r3037", "rts_r3034")  # escorted asset attack breaks stealth

    # ── PID defeaters override PID requirement ───────────────────────────────
    theory.add_superiority("rts_r3060", "rts_r3056")  # sensor detected > requires PID
    theory.add_superiority("rts_r3061", "rts_r3056")  # direct fire source > requires PID

    # ── Friendly fire defeats cleared_to_engage even under self-defense ──────
    theory.add_superiority("rts_r3067", "rts_r3062")  # friendly fire > cleared engagement
    theory.add_superiority("rts_r3067", "rts_r3064")  # friendly fire > under-fire clearance


def count_rts_behavioral_rules(theory: Theory) -> dict:
    """Return a breakdown of RTS ROE rule counts by type."""
    rts_rules = [r for r in theory.rules if r.label and r.label.startswith("rts_r")]
    defeasible = [r for r in rts_rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in rts_rules if r.rule_type == RuleType.DEFEATER]
    return {
        "total_roe_rules": len(rts_rules),
        "defeasible": len(defeasible),
        "defeaters": len(defeaters),
    }
