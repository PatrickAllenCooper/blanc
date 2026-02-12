"""
Materials Science Instance Facts

Common materials as instance facts.
Based on materials that exist in MatOnto ontology.

These are real materials documented in materials science.
Used to populate the materials KB with ground facts for instance generation.

Author: Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory


def add_materials_instances(theory: Theory) -> Theory:
    """
    Add material instances to theory.
    
    Materials selected from MatOnto taxonomy.
    All are real materials used in materials science.
    """
    
    # Metals and alloys (from MatOnto)
    metals = [
        'iron', 'copper', 'aluminum', 'gold', 'silver', 'platinum',
        'titanium', 'zinc', 'nickel', 'chromium', 'tungsten'
    ]
    
    for metal in metals:
        theory.add_fact(f"material({metal})")
        theory.add_fact(f"metal({metal})")
    
    # Alloys
    alloys = [
        'steel', 'bronze', 'brass', 'stainless_steel',
        'carbon_steel', 'tool_steel', 'titanium_alloy'
    ]
    
    for alloy in alloys:
        theory.add_fact(f"material({alloy})")
        theory.add_fact(f"alloy({alloy})")
    
    # Crystals and ceramics
    crystals = [
        'quartz', 'diamond', 'graphite', 'silicon',
        'alumina', 'zirconia', 'silicon_carbide'
    ]
    
    for crystal in crystals:
        theory.add_fact(f"material({crystal})")
        theory.add_fact(f"crystal({crystal})")
    
    # Polymers
    polymers = [
        'polyethylene', 'polypropylene', 'polystyrene', 'pvc',
        'nylon', 'teflon', 'silicone', 'rubber'
    ]
    
    for polymer in polymers:
        theory.add_fact(f"material({polymer})")
        theory.add_fact(f"polymer({polymer})")
    
    # Composites
    composites = [
        'fiberglass', 'carbon_fiber', 'concrete',
        'plywood', 'laminate'
    ]
    
    for composite in composites:
        theory.add_fact(f"material({composite})")
        theory.add_fact(f"composite({composite})")
    
    # Acids (from MatOnto acid class)
    acids = [
        'sulfuric_acid', 'hydrochloric_acid', 'nitric_acid',
        'acetic_acid', 'citric_acid'
    ]
    
    for acid in acids:
        theory.add_fact(f"chemical({acid})")
        theory.add_fact(f"acid({acid})")
    
    return theory


def get_materials_counts():
    """Get counts of materials by type."""
    return {
        'metals': 11,
        'alloys': 7,
        'crystals': 7,
        'polymers': 8,
        'composites': 5,
        'acids': 5,
        'total': 43
    }
