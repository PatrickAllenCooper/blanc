"""
Test instance generation with defeasible behavioral rules.

Now that biology KB has defeasible rules, test if instance generation works.

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb import create_biology_kb
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


def test_generation():
    """Test instance generation on biology KB with behavioral rules."""
    
    print("=" * 70)
    print("Testing Instance Generation with Behavioral Rules")
    print("=" * 70)
    
    # Load biology KB
    kb = create_biology_kb()
    print(f"\nBiology KB: {len(kb.rules)} rules, {len(kb.facts)} facts")
    
    # Count defeasible rules
    defeasible_rules = [r for r in kb.rules if r.rule_type == RuleType.DEFEASIBLE]
    print(f"Defeasible rules: {len(defeasible_rules)}")
    
    # Convert with partition_rule (facts strict, rules defeasible)
    converted = phi_kappa(kb, partition_rule)
    conv_defeasible = converted.get_rules_by_type(RuleType.DEFEASIBLE)
    
    print(f"\nConverted: {len(converted.facts)} strict facts, {len(conv_defeasible)} defeasible rules")
    
    # Test targets that should be derivable via defeasible rules
    test_targets = [
        "flies(robin)",      # bird(robin) => flies(robin)
        "swims(salmon)",     # fish(salmon) => swims(salmon)
        "walks(cat)",        # mammal(cat) => walks(cat)
    ]
    
    print("\nTesting derivability of behavioral targets:")
    for target in test_targets:
        try:
            result = defeasible_provable(converted, target)
            print(f"  {'[OK]' if result else '[NO]'} {target}")
        except Exception as e:
            print(f"  [ERROR] {target}: {e}")
    
    # Try to generate an instance
    print("\nAttempting instance generation...")
    
    for target in test_targets:
        try:
            if not defeasible_provable(converted, target):
                print(f"  [SKIP] {target} - not derivable")
                continue
            
            critical = full_theory_criticality(converted, target)
            critical_rules = [e for e in critical 
                             if hasattr(e, 'rule_type') and e.rule_type == RuleType.DEFEASIBLE]
            
            print(f"  {target}: {len(critical)} critical elements, {len(critical_rules)} critical rules")
            
            if critical_rules:
                instance = generate_level2_instance(
                    converted,
                    target,
                    critical_rules[0],
                    k_distractors=3,
                    distractor_strategy="syntactic"
                )
                
                print(f"\n  [SUCCESS] Generated instance!")
                print(f"    Target: {instance.target}")
                print(f"    Hidden: {instance.hidden_element}")
                print(f"    Gold hypotheses: {len(instance.gold_hypotheses)}")
                print(f"    Distractors: {len(instance.distractors)}")
                return True
        
        except Exception as e:
            print(f"  [ERROR] {target}: {e}")
            continue
    
    print("\n[FAIL] Could not generate instance")
    return False


if __name__ == "__main__":
    success = test_generation()
    sys.exit(0 if success else 1)
