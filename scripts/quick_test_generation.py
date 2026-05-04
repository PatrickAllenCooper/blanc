"""
Quick test of instance generation on expert KBs.

Test with minimal instances to verify pipeline works.

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb import create_biology_kb
from examples.knowledge_bases.legal_kb import create_legal_kb
from examples.knowledge_bases.materials_kb import create_materials_kb
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


def quick_test(kb_name, base_theory):
    """Quick test of instance generation."""
    
    print(f"\n{'=' * 70}")
    print(f"Quick Test: {kb_name}")
    print('=' * 70)
    
    print(f"KB: {len(base_theory.rules)} rules, {len(base_theory.facts)} facts")
    
    # Convert with partition_rule
    converted = phi_kappa(base_theory, partition_rule)
    defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
    
    print(f"Converted: {len(converted.facts)} facts, {len(defeasible_rules)} defeasible rules")
    
    # Try to generate 1 instance
    for target in list(base_theory.facts)[:10]:
        try:
            if not defeasible_provable(converted, target):
                continue
            
            critical = full_theory_criticality(converted, target)
            critical_rules = [e for e in critical 
                             if hasattr(e, 'rule_type') and e.rule_type == RuleType.DEFEASIBLE]
            
            if critical_rules:
                instance = generate_level2_instance(
                    converted,
                    target,
                    critical_rules[0],
                    k_distractors=3,
                    distractor_strategy="syntactic"
                )
                
                print(f"\n[SUCCESS] Generated instance for: {target}")
                print(f"  Hidden element: {instance.hidden_element}")
                print(f"  Target: {instance.target}")
                print(f"  Distractors: {len(instance.distractors)}")
                return True
        
        except Exception as e:
            continue
    
    print(f"\n[FAIL] Could not generate instance")
    return False


def main():
    """Quick test all 3 KBs."""
    
    print("=" * 70)
    print("QUICK INSTANCE GENERATION TEST")
    print("=" * 70)
    
    # Test biology
    bio_kb = create_biology_kb()
    bio_ok = quick_test("Biology", bio_kb)
    
    # Test legal
    legal_kb = create_legal_kb()
    legal_ok = quick_test("Legal", legal_kb)
    
    # Test materials
    materials_kb = create_materials_kb()
    materials_ok = quick_test("Materials", materials_kb)
    
    print("\n" + "=" * 70)
    print("QUICK TEST SUMMARY")
    print("=" * 70)
    print(f"  Biology: {'[PASS]' if bio_ok else '[FAIL]'}")
    print(f"  Legal: {'[PASS]' if legal_ok else '[FAIL]'}")
    print(f"  Materials: {'[PASS]' if materials_ok else '[FAIL]'}")
    
    if bio_ok and legal_ok and materials_ok:
        print("\n[SUCCESS] All 3 KBs can generate instances")
        return 0
    else:
        print("\n[PARTIAL] Some KBs cannot generate instances yet")
        return 1


if __name__ == "__main__":
    sys.exit(main())
