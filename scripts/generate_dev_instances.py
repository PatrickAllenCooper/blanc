"""
Generate development instances from KB subsets.

Fast local generation for development iteration.
Uses manageable KB subsets (100-200 rules) for quick feedback.

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb_subset import create_biology_subset
from examples.knowledge_bases.legal_kb import create_legal_kb  # Full KB is manageable
from examples.knowledge_bases.materials_kb_subset import create_materials_subset
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance, generate_level1_instance
from blanc.generation.partition import (
    partition_leaf, partition_rule, partition_random, compute_dependency_depths, partition_depth
)
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


def generate_from_kb_dev(kb_name, base_theory, partition_strategies, max_per_strategy=10):
    """Generate instances for development (small batches)."""
    
    print(f"\n{'=' * 70}")
    print(f"Development Generation: {kb_name}")
    print('=' * 70)
    
    print(f"\nKB: {len(base_theory.rules)} rules, {len(base_theory.facts)} facts")
    
    all_instances = []
    partition_results = {}
    
    # Get derivable targets
    derivable_targets = []
    for fact in base_theory.facts:
        if defeasible_provable(base_theory, fact):
            derivable_targets.append(fact)
    
    print(f"Derivable targets: {len(derivable_targets)}")
    print(f"Partition strategies: {len(partition_strategies)}\n")
    
    # Generate from each partition
    for i, (strat_name, partition_fn) in enumerate(partition_strategies, 1):
        print(f"[{i}/{len(partition_strategies)}] {strat_name}...", end=' ')
        
        converted = phi_kappa(base_theory, partition_fn)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        
        instances_generated = 0
        
        # Try each target
        for target in derivable_targets[:max_per_strategy * 3]:
            if instances_generated >= max_per_strategy:
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
            
            except Exception:
                continue
        
        print(f"{instances_generated} instances")
        
        partition_results[strat_name] = {
            "instances": instances_generated,
            "defeasible_rules": len(defeasible_rules),
        }
    
    return all_instances, partition_results


def main():
    """Generate development instances from KB subsets."""
    
    print("=" * 70)
    print("DEVELOPMENT INSTANCE GENERATION (Local)")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Purpose: Fast local development iteration")
    print()
    
    # Define all 13 partition strategies for development
    strategies = [
        ("leaf", partition_leaf),
        ("rule", partition_rule),
        ("rand_0.1", partition_random(0.1, seed=42)),
        ("rand_0.2", partition_random(0.2, seed=42)),
        ("rand_0.3", partition_random(0.3, seed=42)),
        ("rand_0.4", partition_random(0.4, seed=42)),
        ("rand_0.5", partition_random(0.5, seed=42)),
        ("rand_0.6", partition_random(0.6, seed=42)),
        ("rand_0.7", partition_random(0.7, seed=42)),
        ("rand_0.8", partition_random(0.8, seed=42)),
        ("rand_0.9", partition_random(0.9, seed=42)),
    ]
    
    all_results = {}
    
    # === BIOLOGY SUBSET ===
    print("\n" + "#" * 70)
    print("# BIOLOGY SUBSET (Vertebrates)")
    print("#" * 70)
    
    bio_subset = create_biology_subset()
    
    # Add depth strategies
    bio_depths = compute_dependency_depths(bio_subset)
    bio_strategies = strategies + [
        ("depth_1", partition_depth(1, bio_depths)),
        ("depth_2", partition_depth(2, bio_depths)),
    ]
    
    bio_instances, bio_results = generate_from_kb_dev(
        "Biology Subset",
        bio_subset,
        bio_strategies,
        max_per_strategy=20  # Increased for more instances
    )
    
    all_results['biology'] = {
        'instances': bio_instances,
        'partition_results': bio_results,
        'kb_stats': {
            'rules': len(bio_subset.rules),
            'facts': len(bio_subset.facts),
            'subset': 'vertebrates',
        }
    }
    
    # === LEGAL KB (Full - manageable size) ===
    print("\n" + "#" * 70)
    print("# LEGAL KB (Full - 201 rules)")
    print("#" * 70)
    
    legal_kb = create_legal_kb()
    
    legal_depths = compute_dependency_depths(legal_kb)
    legal_strategies = strategies + [
        ("depth_1", partition_depth(1, legal_depths)),
    ]
    
    legal_instances, legal_results = generate_from_kb_dev(
        "Legal KB",
        legal_kb,
        legal_strategies,
        max_per_strategy=20  # Increased for more instances
    )
    
    all_results['legal'] = {
        'instances': legal_instances,
        'partition_results': legal_results,
        'kb_stats': {
            'rules': len(legal_kb.rules),
            'facts': len(legal_kb.facts),
            'subset': 'full',
        }
    }
    
    # === MATERIALS SUBSET ===
    print("\n" + "#" * 70)
    print("# MATERIALS SUBSET (Metals/Alloys)")
    print("#" * 70)
    
    materials_subset = create_materials_subset()
    
    materials_depths = compute_dependency_depths(materials_subset)
    materials_strategies = strategies + [
        ("depth_1", partition_depth(1, materials_depths)),
    ]
    
    materials_instances, materials_results = generate_from_kb_dev(
        "Materials Subset",
        materials_subset,
        materials_strategies,
        max_per_strategy=20  # Increased for more instances
    )
    
    all_results['materials'] = {
        'instances': materials_instances,
        'partition_results': materials_results,
        'kb_stats': {
            'rules': len(materials_subset.rules),
            'facts': len(materials_subset.facts),
            'subset': 'metals_alloys',
        }
    }
    
    # === SUMMARY ===
    total_instances = len(bio_instances) + len(legal_instances) + len(materials_instances)
    
    print("\n" + "=" * 70)
    print("DEVELOPMENT GENERATION COMPLETE")
    print("=" * 70)
    print(f"Total instances: {total_instances}")
    print(f"  Biology subset: {len(bio_instances)}")
    print(f"  Legal full: {len(legal_instances)}")
    print(f"  Materials subset: {len(materials_instances)}")
    
    # Save results
    for domain, results in all_results.items():
        if results['instances']:
            output = {
                "metadata": {
                    "domain": domain,
                    "purpose": "local development",
                    "kb_stats": results['kb_stats'],
                    "total_instances": len(results['instances']),
                    "generation_date": datetime.now().isoformat(),
                },
                "partition_results": results['partition_results'],
                "instances": [inst.to_dict() for inst in results['instances']],
            }
            
            filename = f"{domain}_dev_instances.json"
            with open(filename, 'w') as f:
                json.dump(output, f, indent=2)
            
            print(f"\nSaved {len(results['instances'])} {domain} instances to: {filename}")
    
    print("\n" + "=" * 70)
    print("Ready for local development iteration!")
    print("=" * 70)
    print(f"\nNote: Using subsets for fast development.")
    print(f"Full-scale HPC generation deferred to Weeks 13-14.")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
