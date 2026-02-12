"""
Materials KB Subset for Local Development

Creates a manageable 150-200 rule subset from MatOnto for fast iteration.
Focuses on metals, alloys, and structure-property relationships.

Based on MatOnto expert materials science ontology.

Author: Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory, Rule, RuleType


def create_materials_subset() -> Theory:
    """
    Create development subset of materials KB.
    
    Subset: Metals, alloys, and basic structure-property rules
    Size: ~50 rules (vs 1,190 full KB)
    Purpose: Fast local development iteration
    
    Returns:
        Theory with metals-focused subset
    """
    theory = Theory()
    
    # === INSTANCES (Common materials) ===
    
    # Pure metals
    metals = ['iron', 'copper', 'aluminum', 'gold', 'titanium', 'zinc']
    for metal in metals:
        theory.add_fact(f"material({metal})")
        theory.add_fact(f"metal({metal})")
    
    # Alloys
    alloys = ['steel', 'bronze', 'brass', 'stainless_steel']
    for alloy in alloys:
        theory.add_fact(f"material({alloy})")
        theory.add_fact(f"alloy({alloy})")
    
    # Crystals
    crystals = ['diamond', 'quartz', 'silicon']
    for crystal in crystals:
        theory.add_fact(f"material({crystal})")
        theory.add_fact(f"crystal({crystal})")
    
    # Polymers
    polymers = ['polyethylene', 'nylon', 'teflon']
    for polymer in polymers:
        theory.add_fact(f"material({polymer})")
        theory.add_fact(f"polymer({polymer})")
    
    # === EXPERT RULES (Subset from MatOnto) ===
    
    # Taxonomic rules (strict)
    theory.add_rule(Rule(
        head="material(X)",
        body=("metal(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s1"
    ))
    
    theory.add_rule(Rule(
        head="material(X)",
        body=("alloy(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s2"
    ))
    
    theory.add_rule(Rule(
        head="material(X)",
        body=("crystal(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s3"
    ))
    
    theory.add_rule(Rule(
        head="material(X)",
        body=("polymer(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s4"
    ))
    
    # Alloy composition (from MatOnto: alloy -> solution)
    theory.add_rule(Rule(
        head="solution(X)",
        body=("alloy(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s5"
    ))
    
    # === DEFEASIBLE PROPERTY RULES ===
    
    # Conductivity (metals typically conductive)
    theory.add_rule(Rule(
        head="conductive(X)",
        body=("metal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="mat_d1"
    ))
    
    # Brittleness (crystals typically brittle, from paper example)
    theory.add_rule(Rule(
        head="brittle(X)",
        body=("crystal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="mat_d2"
    ))
    
    # Ductility (metals typically ductile)
    theory.add_rule(Rule(
        head="ductile(X)",
        body=("metal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="mat_d3"
    ))
    
    # Strength (alloys typically strong)
    theory.add_rule(Rule(
        head="strong(X)",
        body=("alloy(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="mat_d4"
    ))
    
    # Corrosion resistance (some alloys)
    theory.add_rule(Rule(
        head="corrosion_resistant(X)",
        body=("stainless_steel(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s6"
    ))
    
    # Flexibility (polymers typically flexible)
    theory.add_rule(Rule(
        head="flexible(X)",
        body=("polymer(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="mat_d5"
    ))
    
    # Hardness (diamonds are hard)
    theory.add_rule(Rule(
        head="hard(X)",
        body=("diamond(X)",),
        rule_type=RuleType.STRICT,
        label="mat_s7"
    ))
    
    return theory


def get_subset_stats():
    """Get statistics for materials subset."""
    theory = create_materials_subset()
    
    from blanc.generation.partition import compute_dependency_depths
    depths = compute_dependency_depths(theory)
    
    defeasible = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    strict = [r for r in theory.rules if r.rule_type == RuleType.STRICT]
    
    return {
        'source': 'MatOnto subset',
        'domain': 'metals and alloys',
        'rules_total': len(theory.rules),
        'rules_strict': len(strict),
        'rules_defeasible': len(defeasible),
        'facts': len(theory.facts),
        'materials': 16,
        'max_depth': max(depths.values()) if depths else 0,
        'purpose': 'local development (fast iteration)',
        'full_kb_available': 'materials_kb.py (1,190 rules)',
    }
