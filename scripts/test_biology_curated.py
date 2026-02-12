"""Test curated biology KB."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_curated import (
    create_biology_base,
    create_biology_full,
    get_biology_stats,
)
from blanc.reasoning.defeasible import defeasible_provable
from blanc.author.conversion import convert_theory_to_defeasible

def main():
    print("=" * 70)
    print("Curated Biology KB Validation")
    print("=" * 70)
    
    # Load
    print("\n1. Creating curated biology KB...")
    kb = create_biology_base()
    
    stats = get_biology_stats(kb)
    print(f"   Constants: {stats['constants']}")
    print(f"   Predicates: {stats['predicates']}")
    print(f"   Clauses: {stats['clauses']}")
    print(f"   Max depth: {stats['max_depth']}")
    print(f"   Herbrand base (approx): {stats['herbrand_base_approx']}")
    
    # Test derivations
    print("\n2. Testing derivations...")
    
    test_conclusions = [
        ("organism(robin)", "Organism fact"),
        ("passerine(robin)", "Species fact"),
        ("bird(robin)", "Taxonomy (depth 1)"),
        ("has_wings(robin)", "Anatomy (depth 2)"),
        ("flies(robin)", "Behavior (depth 3)"),
    ]
    
    for conclusion, description in test_conclusions:
        result = defeasible_provable(kb, conclusion)
        status = "[OK]" if result else "[FAIL]"
        print(f"   {status} {conclusion:30s} - {description}")
    
    # Check depth
    if stats['max_depth'] >= 2:
        print(f"\n   [SUCCESS] Has depth >= 2 derivations (depth = {stats['max_depth']})")
    else:
        print(f"\n   [WARNING] Max depth only {stats['max_depth']} (need >= 2)")
    
    # Convert to defeasible
    print("\n3. Converting with partition_rule...")
    defeasible_kb = convert_theory_to_defeasible(kb, "rule")
    
    from blanc.core.theory import RuleType
    print(f"   Defeasible rules: {len(defeasible_kb.get_rules_by_type(RuleType.DEFEASIBLE))}")
    print(f"   Strict rules: {len(defeasible_kb.get_rules_by_type(RuleType.STRICT))}")
    
    print("\n" + "=" * 70)
    print("VALIDATION COMPLETE")
    print("=" * 70)
    print(f"Biology KB ready for instance generation")
    print(f"Size: {len(kb)} elements")
    print(f"Depth: {stats['max_depth']} (target: >= 2)")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
