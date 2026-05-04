"""
Lux AI Season 3 Engagement Knowledge Base -- Factory

Assembles the complete Lux AI S3 defeasible behavioral theory from its
component modules:

    - Strict unit and environment rules   (lux_unit_rules.py)
    - Defeasible behavioral ROE rules     (lux_behavioral_rules.py)

This KB encodes the strategic norms of Lux AI Season 3 (NeurIPS 2024
competition) as a defeasible theory with the same structural properties
as the SC2 engagement KB (rts_engagement_kb.py):

    strict rules (game physics)
        > defeasible mission norms (default behavioral policy)
            > defeaters (self-preservation, win-condition, situational overrides)

The Lux AI S3 behavioral hierarchy mirrors the Newport ROE Handbook:
    self-preservation > scoring objectives > resource efficiency

Scale:
    - ~60 strict rules (unit taxonomy, terrain, physics, team membership)
    - ~40 defeasible behavioral rules (relic pursuit, energy harvesting,
           collision avoidance, nebula policy, stealth, meta-learning)
    - ~20 defeaters (self-preservation, win-condition, energy emergency,
                    laser evasion)
    - ~12 superiority relations

Visual rendering:
    The Lux Eye S3 web visualizer (https://s3vis.lux-ai.org) renders
    replay episodes as animated sci-fi strategy maps, providing visually
    compelling illustrations of exactly the scenarios in this KB:
    ships navigating nebulae, contesting relic nodes, and retreating
    when energy is critical.

Cross-environment comparison:
    Instances generated from this KB use the same DeFAb pipeline,
    the same DefeasibleEngine verifier, and the same model evaluation
    protocol as SC2 engagement instances. Cross-environment performance
    comparison tests whether the DeFAb verifier measures domain-general
    defeasible reasoning rather than SC2-specific vocabulary.

Author: Anonymous Authors
"""

from blanc.core.theory import Theory
from .lux_unit_rules import create_lux_unit_theory
from .lux_behavioral_rules import (
    add_lux_behavioral_rules,
    add_lux_superiority_relations,
    count_lux_behavioral_rules,
)


def create_lux_engagement_kb(include_instances: bool = True) -> Theory:
    """
    Create the Lux AI S3 engagement knowledge base.

    Parameters
    ----------
    include_instances : bool
        If True (default), ship, terrain, and match-state instances are
        included.  Set to False for the rule skeleton only.

    Returns
    -------
    Theory
        Complete defeasible theory suitable for DeFAb instance generation.
    """
    theory = create_lux_unit_theory() if include_instances else _rules_only()
    theory = add_lux_behavioral_rules(theory)
    add_lux_superiority_relations(theory)
    return theory


def _rules_only() -> Theory:
    """Return a Theory with strict rules but no ground instance facts."""
    full = create_lux_unit_theory()
    stripped = Theory()
    for rule in full.rules:
        stripped.add_rule(rule)
    return stripped


def get_lux_stats(theory=None) -> dict:
    """Return statistics for the Lux AI S3 KB."""
    if theory is None:
        theory = create_lux_engagement_kb()

    from blanc.generation.partition import compute_dependency_depths
    from blanc.core.theory import RuleType

    depths = compute_dependency_depths(theory)
    max_depth = max(depths.values()) if depths else 0

    strict    = [r for r in theory.rules if r.rule_type == RuleType.STRICT]
    defeas    = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in theory.rules if r.rule_type == RuleType.DEFEATER]

    lux_counts = count_lux_behavioral_rules(theory)

    return {
        "domain": "lux_ai_s3",
        "sources": [
            "Lux AI Season 3 (NeurIPS 2024)",
            "https://github.com/Lux-AI-Challenge/Lux-Design-S3",
            "Newport ROE Handbook structural mapping",
        ],
        "rules_total": len(theory.rules),
        "facts_total": len(theory.facts),
        "strict_rules": len(strict),
        "defeasible_rules": len(defeas),
        "defeater_rules": len(defeaters),
        "lux_behavioral": lux_counts["total_behavioral"],
        "lux_defeasible": lux_counts["defeasible"],
        "lux_defeaters":  lux_counts["defeaters"],
        "max_dependency_depth": max_depth,
        "behavioral_predicates": [
            "ordered_to_advance_on_relic",
            "ordered_to_harvest_energy",
            "must_avoid_tile",
            "must_avoid_nebula",
            "ordered_to_retreat_to_energy",
            "prohibited_from_firing",
            "maintain_visibility",
            "cleared_to_score",
            "optimal_position",
        ],
        "defeater_categories": [
            "self_preservation_override",
            "win_condition_push",
            "stealth_evasion",
            "laser_evasion",
            "meta_learning_probe",
            "energy_emergency",
            "no_alternative_path",
        ],
        "visual_source": "https://s3vis.lux-ai.org",
        "roe_hierarchy": "self_preservation > scoring_objectives > resource_efficiency",
    }


# Alias
create_lux_kb = create_lux_engagement_kb
