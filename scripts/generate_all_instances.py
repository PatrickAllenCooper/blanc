"""
Generate instances from all 3 expert-curated knowledge bases.

Implements systematic instance generation across all 3 domains:
- Biology (YAGO + WordNet): 918 rules, 255 facts
- Legal (LKIF Core): 201 rules, 63 facts
- Materials (MatOnto): 1,190 rules, 86 facts

Author: Patrick Cooper  
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb import create_biology_kb
from examples.knowledge_bases.legal_kb import create_legal_kb
from examples.knowledge_bases.materials_kb import create_materials_kb
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level1_instance, generate_level2_instance
from blanc.generation.partition import (
    partition_leaf, partition_rule, partition_depth,
    partition_random, compute_dependency_depths
)
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


def generate_from_kb(kb_name, base_theory, max_per_partition=20):
    """Generate instances from a single KB with all partition strategies."""
    
    print("\n" + "=" * 70)
    print(f"Generating Instances: {kb_name}")
    print("=" * 70)
    
    all_instances = []
    partition_results = {}
    
    # Define all 13 partition strategies
    strategies = []
    strategies.append(("leaf", partition_leaf))
    strategies.append(("rule", partition_rule))
    
    depths_map = compute_dependency_depths(base_theory)
    for k in [1, 2, 3]:
        strategies.append((f"depth_{k}", partition_depth(k, depths_map)))
    
    for delta_int in range(1, 10):
        delta = delta_int / 10.0
        strategies.append((f"rand_{delta:.1f}", partition_random(delta, seed=42)))
    
    print(f"\nPartition strategies: {len(strategies)}")
    print(f"Base KB: {len(base_theory.rules)} rules, {len(base_theory.facts)} facts\n")
    
    # Get all derivable targets
    derivable_targets = []
    for fact in list(base_theory.facts)[:30]:  # Sample of facts
        if defeasible_provable(base_theory, fact):
            derivable_targets.append(fact)
    
    print(f"Derivable targets identified: {len(derivable_targets)}")
    
    # Generate from each partition strategy
    for i, (strat_name, partition_fn) in enumerate(strategies, 1):
        print(f"\nStrategy {i}/13: {strat_name}")
        print("-" * 60)
        
        converted = phi_kappa(base_theory, partition_fn)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        
        print(f"  Converted: {len(converted.facts)} facts, {len(defeasible_rules)} defeasible rules")
        
        instances_generated = 0
        
        # Try to generate Level 2 instances
        for target in derivable_targets:
            if instances_generated >= max_per_partition:
                break
            
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
                        k_distractors=5,
                        distractor_strategy="syntactic"
                    )
                    
                    all_instances.append(instance)
                    instances_generated += 1
            
            except Exception as e:
                continue
        
        print(f"  Generated: {instances_generated} instances")
        
        partition_results[strat_name] = {
            "instances": instances_generated,
            "facts": len(converted.facts),
            "defeasible_rules": len(defeasible_rules),
        }
        
    return all_instances, partition_results


def main():
    """Generate instances from all 3 expert KBs."""
    
    print("=" * 70)
    print("INSTANCE GENERATION FROM ALL 3 EXPERT KBs")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    all_results = {}
    
    # Biology
    print("\n" + "#" * 70)
    print("# DOMAIN 1: BIOLOGY")
    print("#" * 70)
    
    bio_kb = create_biology_kb()
    bio_instances, bio_results = generate_from_kb("Biology", bio_kb, max_per_partition=15)
    all_results['biology'] = {
        'instances': bio_instances,
        'partition_results': bio_results,
        'kb_stats': {
            'rules': len(bio_kb.rules),
            'facts': len(bio_kb.facts),
            'sources': ['YAGO 4.5', 'WordNet 3.0']
        }
    }
    
    # Legal
    print("\n" + "#" * 70)
    print("# DOMAIN 2: LEGAL")
    print("#" * 70)
    
    legal_kb = create_legal_kb()
    legal_instances, legal_results = generate_from_kb("Legal", legal_kb, max_per_partition=15)
    all_results['legal'] = {
        'instances': legal_instances,
        'partition_results': legal_results,
        'kb_stats': {
            'rules': len(legal_kb.rules),
            'facts': len(legal_kb.facts),
            'sources': ['LKIF Core']
        }
    }
    
    # Materials
    print("\n" + "#" * 70)
    print("# DOMAIN 3: MATERIALS")
    print("#" * 70)
    
    materials_kb = create_materials_kb()
    materials_instances, materials_results = generate_from_kb("Materials", materials_kb, max_per_partition=15)
    all_results['materials'] = {
        'instances': materials_instances,
        'partition_results': materials_results,
        'kb_stats': {
            'rules': len(materials_kb.rules),
            'facts': len(materials_kb.facts),
            'sources': ['MatOnto']
        }
    }
    
    # Overall summary
    total_instances = (len(bio_instances) + len(legal_instances) + len(materials_instances))
    
    print("\n" + "=" * 70)
    print("GENERATION COMPLETE")
    print("=" * 70)
    print(f"\nTotal instances generated: {total_instances}")
    print(f"  Biology: {len(bio_instances)}")
    print(f"  Legal: {len(legal_instances)}")
    print(f"  Materials: {len(materials_instances)}")
    
    # Save all results
    for domain, results in all_results.items():
        if results['instances']:
            output = {
                "metadata": {
                    "domain": domain,
                    "kb_stats": results['kb_stats'],
                    "partition_strategies": 13,
                    "total_instances": len(results['instances']),
                    "generation_date": datetime.now().isoformat(),
                },
                "partition_results": results['partition_results'],
                "instances": [inst.to_dict() for inst in results['instances']],
            }
            
            filename = f"{domain}_instances_expert.json"
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\nSaved {len(results['instances'])} {domain} instances to: {filename}")
    
    print("\n" + "=" * 70)
    print("ALL 3 EXPERT KBs INSTANCE GENERATION COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
