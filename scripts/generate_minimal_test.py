"""
Minimal test of instance generation using only behavioral rules.

Create a small KB with just behavioral rules to verify generation works.

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import phi_kappa
from blanc.generation.partition import partition_rule
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance


def create_minimal_bio_kb():
    """Create minimal biology KB for testing."""
    theory = Theory()
    
    # Add just a few organisms
    theory.add_fact("organism(robin)")
    theory.add_fact("bird(robin)")
    
    theory.add_fact("organism(penguin)")
    theory.add_fact("bird(penguin)")
    
    theory.add_fact("organism(salmon)")
    theory.add_fact("fish(salmon)")
    
    # Add strict rule: bird(X) -> organism(X)
    theory.add_rule(Rule(
        head="organism(X)",
        body=("bird(X)",),
        rule_type=RuleType.STRICT,
        label="r1"
    ))
    
    # Add defeasible behavioral rule: bird(X) => flies(X)
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r2"
    ))
    
    theory.add_rule(Rule(
        head="swims(X)",
        body=("fish(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r3"
    ))
    
    return theory


def main():
    """Test minimal instance generation."""
    
    print("=" * 70)
    print("Minimal Instance Generation Test")
    print("=" * 70)
    
    # Create minimal KB
    kb = create_minimal_bio_kb()
    print(f"\nMinimal KB: {len(kb.rules)} rules, {len(kb.facts)} facts")
    
    # Convert
    converted = phi_kappa(kb, partition_rule)
    print(f"Converted: {len(converted.facts)} facts, {len(converted.rules)} rules")
    
    defeasible = converted.get_rules_by_type(RuleType.DEFEASIBLE)
    print(f"Defeasible rules: {len(defeasible)}")
    for r in defeasible:
        print(f"  {r}")
    
    # Test target
    target = "flies(robin)"
    print(f"\nTarget: {target}")
    
    from blanc.reasoning.defeasible import defeasible_provable
    derivable = defeasible_provable(converted, target)
    print(f"Derivable: {derivable}")
    
    if derivable:
        print("\nComputing criticality...")
        critical = full_theory_criticality(converted, target)
        print(f"Critical elements: {len(critical)}")
        for c in critical:
            print(f"  {c}")
        
        critical_rules = [e for e in critical 
                         if hasattr(e, 'rule_type') and e.rule_type == RuleType.DEFEASIBLE]
        
        if critical_rules:
            print(f"\nGenerating instance...")
            instance = generate_level2_instance(
                converted,
                target,
                critical_rules[0],
                k_distractors=3,
                distractor_strategy="syntactic"
            )
            
            print(f"\n[SUCCESS] Instance generated!")
            print(f"  Target: {instance.target}")
            print(f"  Level: {instance.level}")
            print(f"  Gold: {instance.gold}")
            print(f"  Candidates: {len(instance.candidates)}")
            
            # Save
            output = {
                "test": "minimal",
                "kb": "biology_minimal",
                "instance": instance.to_dict()
            }
            
            with open("minimal_test_instance.json", 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\nSaved to: minimal_test_instance.json")
            return 0
    
    print("\n[FAIL] Could not generate instance")
    return 1


if __name__ == "__main__":
    sys.exit(main())
