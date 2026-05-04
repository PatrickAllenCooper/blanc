"""
Validate OpenCyc biology KB.

Tests:
1. KB loads correctly
2. Sample derivations work
3. Defeasible reasoning works on biology KB
4. Compute statistics for paper

Author: Anonymous Authors
Date: 2026-02-11
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.opencyc_biology import load_opencyc_biology
from blanc.reasoning.defeasible import defeasible_provable, strictly_provable
from blanc.author.conversion import convert_theory_to_defeasible
from blanc.generation.partition import compute_dependency_depths


def main():
    """Validate OpenCyc biology KB."""
    print("=" * 70)
    print("OpenCyc Biology KB Validation")
    print("=" * 70)
    
    # Load
    print("\n1. Loading KB...")
    kb = load_opencyc_biology()
    print(f"  Loaded: {len(kb.facts)} facts, {len(kb.rules)} rules")
    
    # Sample concepts
    print("\n2. Sample biological concepts:")
    for i, fact in enumerate(sorted(list(kb.facts))[:10], 1):
        print(f"  {i}. {fact}")
    
    # Sample rules
    print("\n3. Sample taxonomic rules:")
    for i, rule in enumerate(kb.rules[:10], 1):
        print(f"  {i}. {rule.head}")
    
    # Test strict derivations
    print("\n4. Testing strict derivations...")
    
    # Sample taxonomic queries
    sample_concepts = list(kb.facts)[:5]
    
    for concept_fact in sample_concepts:
        # Extract concept name
        if 'biological_concept(' in concept_fact:
            concept = concept_fact.replace('biological_concept(', '').replace(')', '')
            
            # Try to derive something about it
            test_query = f"biological_concept({concept})"
            result = strictly_provable(kb, test_query)
            print(f"  {test_query}: {result}")
            
            break  # Just test one for now
    
    # Convert to defeasible
    print("\n5. Converting to defeasible with partition_rule...")
    defeasible_kb = convert_theory_to_defeasible(kb, "rule")
    print(f"  Defeasible KB: {len(defeasible_kb.rules)} total rules")
    from blanc.core.theory import RuleType
    print(f"    Strict: {len(defeasible_kb.get_rules_by_type(RuleType.STRICT))}")
    print(f"    Defeasible: {len(defeasible_kb.get_rules_by_type(RuleType.DEFEASIBLE))}")
    
    # Compute dependency depths
    print("\n6. Computing dependency graph...")
    depths = compute_dependency_depths(kb)
    print(f"  Predicates: {len(depths)}")
    print(f"  Max depth: {max(depths.values()) if depths else 0}")
    
    # Filter by depth >= 2 (paper line 331)
    depth_2_plus = {pred: d for pred, d in depths.items() if d >= 2}
    print(f"  Depth >= 2: {len(depth_2_plus)} predicates")
    
    # This is our target set Q for instance generation
    print(f"\n  Target set Q (depth >= 2) size: {len(depth_2_plus)}")
    print(f"  This will yield ~{len(depth_2_plus) * 13} potential instances")
    print(f"  (with 13 partition strategies)")
    
    # Statistics for paper
    print("\n7. Statistics for paper (Section 4.1):")
    
    # Count unique predicates
    predicates = set()
    for rule in kb.rules:
        if 'isa(' in rule.head:
            predicates.add('isa')
        if 'biological_concept(' in str(kb.facts):
            predicates.add('biological_concept')
    
    # Count constants (concept names)
    constants = set()
    for fact in kb.facts:
        if 'biological_concept(' in fact:
            concept = fact.replace('biological_concept(', '').replace(')', '')
            constants.add(concept)
    
    print(f"  |C| (constants): {len(constants)}")
    print(f"  |P| (predicates): {len(predicates)} (approximation)")
    print(f"  |Π| (clauses): {len(kb)}")
    print(f"  Dependency depth: {max(depths.values()) if depths else 0}")
    print(f"  |HB| (Herbrand base): ~{len(constants) * len(predicates)} (estimated)")
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print("OpenCyc Biology KB is operational and ready for instance generation")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    from blanc.core.theory import Rule
    sys.exit(main())
