"""
RTS Engagement Knowledge Base -- Factory

Assembles the complete RTS engagement theory from its component modules:

    - Strict unit and terrain rules   (rts_unit_rules.py)
    - Defeasible ROE rules            (rts_behavioral_rules.py)

This knowledge base models rules of engagement (ROE) in a generic real-time
strategy environment inspired by StarCraft II, which Lockheed Martin has
adopted as an unclassified proxy environment for demonstrating ROE-aware
decision-making (personal communication, Thomas C. Lee, Lockheed Martin,
April 2026).

The structure follows the Newport Rules of Engagement Handbook model:
    strict rules (game physics)
        > defeasible mission constraints (default ROE)
            > defeaters (self-defense, escalation, commander override)

Scale (after assembly):
    - ~110 strict rules (unit taxonomy, capability, terrain, zones)
    - ~60  defeasible ROE rules (engagement authority, worker protection,
           proportionality, retreat, stealth, target priority, force
           concentration, PID requirements)
    - ~30  defeaters (self-defense overrides, escalation triggers,
           exception conditions)
    - ~15  superiority relations (encoding the Newport hierarchy)

This is comparable in scale to the legal KB (LKIF Core: 201 rules).

Author: Patrick Cooper
"""

from blanc.core.theory import Theory
from .rts_unit_rules import create_rts_unit_theory
from .rts_behavioral_rules import (
    add_rts_behavioral_rules,
    add_rts_superiority_relations,
    count_rts_behavioral_rules,
)


def create_rts_engagement_kb(include_instances: bool = True) -> Theory:
    """
    Create the RTS engagement knowledge base.

    Combines strict game-mechanical rules with defeasible ROE rules grounded
    in the Newport Rules of Engagement Handbook and StarCraft II tactical
    doctrine.

    Parameters
    ----------
    include_instances : bool
        If True (default), unit, terrain, mission, threat, and target
        instances are included.  Set to False to get the rule skeleton only
        (useful for synthetic theory generation).

    Returns
    -------
    Theory
        Complete defeasible theory suitable for DeFAb instance generation.
    """
    # Strict foundation (unit taxonomy, capabilities, terrain, zones)
    theory = create_rts_unit_theory() if include_instances else _create_rules_only()

    # Defeasible ROE layer
    theory = add_rts_behavioral_rules(theory)
    add_rts_superiority_relations(theory)

    return theory


def _create_rules_only() -> Theory:
    """Return a Theory with strict rules but no ground instance facts."""
    from .rts_unit_rules import (
        _s,
        create_rts_unit_theory,
    )
    # Re-create theory then strip all facts
    full = create_rts_unit_theory()
    stripped = Theory()
    for rule in full.rules:
        stripped.add_rule(rule)
    return stripped


def get_rts_stats(theory=None) -> dict:
    """Return statistics for the RTS engagement KB."""
    if theory is None:
        theory = create_rts_engagement_kb()

    from blanc.generation.partition import compute_dependency_depths
    from blanc.core.theory import RuleType

    depths = compute_dependency_depths(theory)
    max_depth = max(depths.values()) if depths else 0

    strict = [r for r in theory.rules if r.rule_type == RuleType.STRICT]
    defeasible = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in theory.rules if r.rule_type == RuleType.DEFEATER]

    roe_counts = count_rts_behavioral_rules(theory)

    return {
        "domain": "rts_engagement",
        "sources": ["StarCraft II game mechanics", "Newport ROE Handbook (2022)",
                    "AIIDE 2015 ASP RTS paper"],
        "rules_total": len(theory.rules),
        "facts_total": len(theory.facts),
        "strict_rules": len(strict),
        "defeasible_rules": len(defeasible),
        "defeater_rules": len(defeaters),
        "roe_behavioral": roe_counts["total_roe_rules"],
        "roe_defeasible": roe_counts["defeasible"],
        "roe_defeaters": roe_counts["defeaters"],
        "max_dependency_depth": max_depth,
        "roe_predicates": [
            "authorized_to_engage",
            "cleared_to_engage",
            "protected_from_attack",
            "must_use_minimum_force",
            "ordered_to_retreat",
            "stealth_posture_active",
            "priority_target",
            "requires_positive_id",
            "mission_accomplished",
        ],
        "top_level_defeater_categories": [
            "self_defense_override",
            "escalation_trigger",
            "worker_exception",
            "proportionality_override",
            "retreat_override",
            "stealth_break",
            "pid_waiver",
            "friendly_fire_block",
        ],
    }


# Backward compatibility alias
create_rts_kb = create_rts_engagement_kb
