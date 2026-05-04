"""
Generate Level 1 (fact completion) instances from biology KB.

Level 1 tests basic grounding by asking models to identify missing facts
needed to derive a target conclusion.

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_curated import create_biology_base, get_biology_stats
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level1_instance
from blanc.generation.partition import partition_rule, partition_depth, compute_dependency_depths
from blanc.core.theory import RuleType


def generate_level1_instances(base_theory, max_instances=50):
    """
    Generate Level 1 (fact completion) instances.
    
    Strategy: Use partition_rule (facts strict, rules defeasible)
    and select targets with critical facts in their support.
    """
    print("=" * 70)
    print("Generating Level 1 (Fact Completion) Instances")
    print("=" * 70)
    
    # Convert with partition_rule
    converted = phi_kappa(base_theory, partition_rule)
    
    print(f"\nConverted KB:")
    print(f"  Facts: {len(converted.facts)}")
    print(f"  Rules: {len([r for r in converted.rules if r.rule_type != RuleType.DEFEATER])}")
    print()
    
    instances = []
    
    # Target organisms and behaviors
    target_organisms = [
        'robin', 'sparrow', 'eagle', 'hawk', 'duck', 'penguin', 
        'parrot', 'dolphin', 'whale', 'salmon', 'bee', 'butterfly',
        'snake', 'frog', 'lion', 'dog'
    ]
    
    behaviors = [
        'flies', 'swims', 'warm_blooded', 'lays_eggs', 
        'migrates', 'predator', 'social', 'territorial'
    ]
    
    print("Generating instances...")
    generated = 0
    
    for organism in target_organisms:
        if generated >= max_instances:
            break
            
        for behavior in behaviors:
            if generated >= max_instances:
                break
                
            target = f"{behavior}({organism})"
            
            try:
                # Check if target is derivable
                from blanc.reasoning.defeasible import defeasible_provable
                if not defeasible_provable(converted, target):
                    continue
                
                # Find critical elements
                critical = full_theory_criticality(converted, target)
                
                # Find critical facts (not rules)
                critical_facts = [e for e in critical 
                                 if not hasattr(e, 'rule_type')]
                
                if critical_facts:
                    # Generate Level 1 instance
                    instance = generate_level1_instance(
                        converted,
                        target,
                        critical_facts[0],
                        k_distractors=5,
                        distractor_strategy="syntactic"
                    )
                    
                    instances.append(instance)
                    generated += 1
                    
                    if generated % 10 == 0:
                        print(f"  Generated: {generated} instances")
                    
            except Exception as e:
                # Skip if generation fails
                continue
    
    print(f"\nTotal Level 1 instances generated: {len(instances)}")
    return instances


def main():
    """Main generation pipeline."""
    print("Loading biology KB...")
    kb = create_biology_base()
    
    stats = get_biology_stats(kb)
    print(f"Biology KB: {stats['clauses']} rules, depth {stats['max_depth']}")
    print()
    
    # Generate Level 1 instances
    instances = generate_level1_instances(kb, max_instances=50)
    
    # Save instances
    if instances:
        output = {
            "metadata": {
                "kb": "biology_curated",
                "level": 1,
                "total_instances": len(instances),
                "kb_stats": get_biology_stats(kb),
            },
            "instances": [inst.to_dict() for inst in instances],
        }
        
        with open("biology_level1_instances.json", 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\nSaved {len(instances)} Level 1 instances to: biology_level1_instances.json")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
