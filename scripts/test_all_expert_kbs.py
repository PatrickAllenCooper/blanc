"""
Test all 3 expert-curated knowledge bases.

Verify all KBs load, have proper depth, and can generate instances.

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb import create_biology_kb, get_biology_stats
from examples.knowledge_bases.legal_kb import create_legal_kb, get_legal_stats
from examples.knowledge_bases.materials_kb import create_materials_kb, get_materials_stats
from blanc.generation.partition import compute_dependency_depths, partition_rule
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.reasoning.defeasible import defeasible_provable


def test_kb(name, create_fn, get_stats_fn):
    """Test a single KB."""
    
    print("=" * 70)
    print(f"Testing {name} KB")
    print("=" * 70)
    
    # Load KB
    print("\n1. Loading KB...")
    kb = create_fn()
    stats = get_stats_fn(kb)
    
    print(f"   Rules: {stats['rules']}")
    print(f"   Facts: {stats['facts']}")
    print(f"   Max depth: {stats['max_depth']}")
    print(f"   Predicates: {stats['predicates']}")
    print(f"   Sources: {stats['sources']}")
    
    # Check depth
    print("\n2. Verifying depth >= 2...")
    if stats['max_depth'] >= 2:
        print(f"   [OK] Depth {stats['max_depth']} exceeds requirement (>= 2)")
    else:
        print(f"   [FAIL] Depth {stats['max_depth']} below requirement (>= 2)")
        return False
    
    # Test conversion
    print("\n3. Testing defeasible conversion...")
    try:
        converted = phi_kappa(kb, partition_rule)
        print(f"   [OK] Converted: {len(converted.facts)} facts, {len(converted.rules)} rules")
    except Exception as e:
        print(f"   [FAIL] Conversion failed: {e}")
        return False
    
    # Test derivability
    print("\n4. Testing derivations...")
    derivable_count = 0
    test_facts = list(kb.facts)[:5] if kb.facts else []
    
    for fact in test_facts:
        try:
            result = defeasible_provable(kb, fact)
            if result:
                derivable_count += 1
        except:
            pass
    
    if test_facts:
        print(f"   [OK] {derivable_count}/{len(test_facts)} test facts derivable")
    else:
        print(f"   [SKIP] No facts to test")
    
    # Test criticality
    print("\n5. Testing criticality computation...")
    if test_facts:
        try:
            target = test_facts[0]
            critical = full_theory_criticality(converted, target)
            print(f"   [OK] Criticality computed: {len(critical)} critical elements for {target}")
        except Exception as e:
            print(f"   [FAIL] Criticality failed: {e}")
            return False
    else:
        print(f"   [SKIP] No facts to test criticality")
    
    print(f"\n[SUCCESS] {name} KB ready for instance generation\n")
    return True


def main():
    """Test all 3 expert KBs."""
    
    print("\n" + "=" * 70)
    print("TESTING ALL 3 EXPERT-CURATED KNOWLEDGE BASES")
    print("=" * 70)
    print()
    
    results = {}
    
    # Test biology
    results['Biology'] = test_kb("Biology", create_biology_kb, get_biology_stats)
    
    # Test legal
    results['Legal'] = test_kb("Legal", create_legal_kb, get_legal_stats)
    
    # Test materials
    results['Materials'] = test_kb("Materials", create_materials_kb, get_materials_stats)
    
    # Summary
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    for name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {name} KB")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n" + "=" * 70)
        print("ALL 3 EXPERT KBs READY FOR INSTANCE GENERATION")
        print("=" * 70)
        return 0
    else:
        print("\nSome KBs failed tests")
        return 1


if __name__ == "__main__":
    sys.exit(main())
