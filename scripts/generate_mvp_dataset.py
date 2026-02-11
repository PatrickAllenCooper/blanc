"""
Generate MVP dataset: 20 instances from Avian Biology.

Generates:
- 10 Level 1 instances (fact completion)
- 10 Level 2 instances (rule abduction)

Author: Patrick Cooper
Date: 2026-02-11
"""

import json
import sys
from pathlib import Path

# Add examples to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.author.generation import generate_level1_instance, generate_level2_instance
from blanc.author.conversion import convert_theory_to_defeasible
from blanc.author.support import full_theory_criticality
from blanc.core.theory import RuleType
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
)


def generate_level1_instances(theory, num_instances=10):
    """
    Generate Level 1 instances from Avian Biology.
    
    Strategy: Find all targets with critical facts, generate instances.
    """
    instances = []
    
    # Define targets to try
    targets = [
        "flies(tweety)",
        "flies(polly)",
        "flies(opus)",
        "flies(chirpy)",
        "migrates(tweety)",
        "migrates(polly)",
        "sings(tweety)",
        "sings(chirpy)",
        "swims(opus)",
        "swims(donald)",
    ]
    
    for target in targets[:num_instances]:
        try:
            # Find critical elements
            critical = full_theory_criticality(theory, target)
            
            # Find critical facts
            critical_facts = [e for e in critical if isinstance(e, str)]
            
            if critical_facts:
                # Use first critical fact
                critical_fact = critical_facts[0]
                
                instance = generate_level1_instance(
                    theory,
                    target,
                    critical_fact,
                    k_distractors=5,
                    distractor_strategy="syntactic"
                )
                
                instances.append(instance)
                print(f"[OK] Generated L1: {target} (ablated: {critical_fact})")
            
        except (ValueError, Exception) as e:
            print(f"[SKIP] L1 {target}: {e}")
            continue
    
    return instances


def generate_level2_instances(theory, num_instances=10):
    """
    Generate Level 2 instances from Avian Biology.
    
    Strategy: Find all targets with critical defeasible rules, generate instances.
    """
    instances = []
    
    # Define targets to try
    targets = [
        "flies(tweety)",
        "flies(polly)",
        "migrates(tweety)",
        "migrates(polly)",
        "sings(tweety)",
        "sings(chirpy)",
        "swims(opus)",
        "swims(donald)",
        "predator(opus)",
        "predator(donald)",
    ]
    
    for target in targets[:num_instances]:
        try:
            # Find critical elements
            critical = full_theory_criticality(theory, target)
            
            # Find critical defeasible rules
            from blanc.core.theory import Rule
            critical_rules = [
                e for e in critical
                if isinstance(e, Rule) and e.rule_type == RuleType.DEFEASIBLE
            ]
            
            if critical_rules:
                # Use first critical rule
                critical_rule = critical_rules[0]
                
                instance = generate_level2_instance(
                    theory,
                    target,
                    critical_rule,
                    k_distractors=5,
                    distractor_strategy="syntactic"
                )
                
                instances.append(instance)
                print(f"[OK] Generated L2: {target} (ablated: {critical_rule.label})")
            
        except (ValueError, Exception) as e:
            print(f"[SKIP] L2 {target}: {e}")
            continue
    
    return instances


def validate_instances(instances):
    """Validate all instances."""
    valid_count = 0
    invalid_instances = []
    
    for i, instance in enumerate(instances):
        if instance.is_valid():
            valid_count += 1
        else:
            invalid_instances.append((i, instance))
    
    return valid_count, invalid_instances


def main():
    """Generate and validate MVP dataset."""
    print("=" * 70)
    print("MVP Dataset Generation: Avian Biology")
    print("=" * 70)
    
    # Load and convert Avian Biology
    print("\n1. Loading Avian Biology KB...")
    base = create_avian_biology_base()
    theory = convert_theory_to_defeasible(base, "rule")
    print(f"   Theory: {len(theory.facts)} facts, {len(theory.rules)} rules")
    
    # Generate Level 1 instances
    print("\n2. Generating Level 1 instances (fact completion)...")
    level1_instances = generate_level1_instances(theory, num_instances=10)
    print(f"   Generated: {len(level1_instances)} Level 1 instances")
    
    # Generate Level 2 instances
    print("\n3. Generating Level 2 instances (rule abduction)...")
    level2_instances = generate_level2_instances(theory, num_instances=10)
    print(f"   Generated: {len(level2_instances)} Level 2 instances")
    
    # Combine
    all_instances = level1_instances + level2_instances
    
    # Validate
    print("\n4. Validating instances...")
    valid_count, invalid = validate_instances(all_instances)
    print(f"   Valid: {valid_count}/{len(all_instances)}")
    
    if invalid:
        print("\n   Invalid instances:")
        for idx, inst in invalid:
            print(f"     - Instance {idx}: {inst.target} (Level {inst.level})")
    
    # Save dataset
    print("\n5. Saving dataset...")
    dataset = {
        "metadata": {
            "name": "Avian Abduction Benchmark v0.1",
            "total_instances": len(all_instances),
            "level1_count": len(level1_instances),
            "level2_count": len(level2_instances),
            "valid_count": valid_count,
            "knowledge_base": "avian_biology",
            "partition_strategy": "rule",
        },
        "instances": [inst.to_dict() for inst in all_instances]
    }
    
    output_path = Path("avian_abduction_v0.1.json")
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"   Saved to: {output_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total instances:  {len(all_instances)}")
    print(f"Level 1 (facts):  {len(level1_instances)}")
    print(f"Level 2 (rules):  {len(level2_instances)}")
    print(f"Valid:            {valid_count}/{len(all_instances)} ({100*valid_count/len(all_instances):.0f}%)")
    print("=" * 70)
    
    return all_instances, valid_count == len(all_instances)


if __name__ == "__main__":
    instances, all_valid = main()
    
    if all_valid:
        print("\n[SUCCESS] All instances valid!")
        exit(0)
    else:
        print("\n[WARNING] Some instances invalid")
        exit(1)
