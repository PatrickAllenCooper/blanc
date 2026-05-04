"""
Materials Science Instance Facts

Common materials as instance facts.
Based on materials that exist in MatOnto ontology.

These are real materials documented in materials science.
Used to populate the materials KB with ground facts for instance generation.

Author: Anonymous Authors
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

    # Special metals referenced in behavioral rules
    special_metals = ['lead', 'cadmium', 'mercury', 'cobalt', 'magnesium']
    for m in special_metals:
        theory.add_fact(f"material({m})")
        theory.add_fact(f"metal({m})")

    # Special alloys
    special_alloys = ['cast_iron', 'metallic_glass', 'high_carbon_steel']
    for a in special_alloys:
        theory.add_fact(f"material({a})")
        theory.add_fact(f"alloy({a})")

    # Ceramics with special properties
    special_ceramics = ['alumina', 'zirconia', 'ceramic_superconductor']
    for c in special_ceramics:
        theory.add_fact(f"material({c})")
        theory.add_fact(f"ceramic({c})")

    # Special glasses
    theory.add_fact("material(tempered_glass)")
    theory.add_fact("glass(tempered_glass)")
    theory.add_fact("material(frosted_glass)")
    theory.add_fact("glass(frosted_glass)")

    # Semiconductors
    semiconductors = ['silicon', 'gallium_arsenide', 'germanium']
    for s in semiconductors:
        theory.add_fact(f"material({s})")
        theory.add_fact(f"semiconductor({s})")

    # Special polymers
    theory.add_fact("material(conductive_polymer)")
    theory.add_fact("polymer(conductive_polymer)")
    theory.add_fact("material(fluoropolymer)")
    theory.add_fact("polymer(fluoropolymer)")

    # Aerogels and foams
    theory.add_fact("material(aerogel)")
    theory.add_fact("material(carbon_fiber)")
    theory.add_fact("composite(carbon_fiber)")

    # Natural materials
    theory.add_fact("material(wood)")
    theory.add_fact("material(paper)")

    return theory


def get_materials_counts():
    """Get counts of materials by type."""
    return {
        'metals': 16,
        'alloys': 10,
        'crystals': 7,
        'polymers': 10,
        'composites': 6,
        'acids': 5,
        'ceramics': 3,
        'glasses': 2,
        'semiconductors': 3,
        'other': 3,
        'total': 65
    }
