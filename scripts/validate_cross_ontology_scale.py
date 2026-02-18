"""
Cross-Ontology Scale Validation

GOAL: Prove we can 10-100x our ruleset by combining:
  - OpenCyc taxonomy (300K concepts)
  - ConceptNet properties (21M assertions)

This is a CRITICAL validation to determine if we should pursue large-scale extraction.

Method:
  1. Load sample from both sources
  2. Combine to generate defeasible rules
  3. Measure: rules generated, quality, instance yield
  4. Extrapolate to full scale

Expected results:
  - 10-100x rule increase (2,318 → 20,000-200,000)
  - 40-150x instance increase (374 → 15,000-56,000)

Runtime: 10-30 minutes

Author: Patrick Cooper
Date: 2026-02-13
"""

from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import gzip
import json

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.opencyc_extractor import OpenCycExtractor
from blanc.ontology.conceptnet_extractor import ConceptNetExtractor
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.generation.partition import partition_random


def combine_taxonomy_properties(
    taxonomy: Dict[str, Set[str]],  # concept -> {parent1, parent2, ...}
    properties: Dict[str, List[Tuple[str, str]]],  # concept -> [(relation, property), ...]
    verbose: bool = True
) -> Theory:
    """
    Generate defeasible rules by combining taxonomy with properties.
    
    Algorithm:
        For each concept:
          1. Inherit properties from all parent classes
          2. Create defeasible rules for inherited capabilities
          3. Add defeaters for NotCapableOf relations
          4. Create property rules for HasProperty relations
    
    Args:
        taxonomy: Concept → parent classes mapping
        properties: Concept → (relation, property) list
        verbose: Print progress
    
    Returns:
        Theory with generated defeasible rules
    """
    theory = Theory()
    rules_generated = defaultdict(int)
    
    # Add all concepts as facts
    for concept in taxonomy.keys():
        theory.add_fact(f"concept({concept})")
    
    # Generate rules for each concept
    for concept, parents in taxonomy.items():
        if verbose and len(theory.rules) % 1000 == 0:
            print(f"  Processing concept {len(theory.rules)}...")
        
        # Add taxonomic rules (strict)
        for parent in parents:
            theory.add_rule(Rule(
                head=f"{parent}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.STRICT,
                label=f"tax_{concept}_{parent}"
            ))
            rules_generated['taxonomic'] += 1
        
        # Collect inherited properties from parents
        inherited_properties = set()
        for parent in parents:
            for (relation, prop) in properties.get(parent, []):
                inherited_properties.add((relation, prop))
        
        # Add inherited properties as defeasible rules
        for (relation, prop) in inherited_properties:
            if relation == 'CapableOf':
                # Generate defeasible behavioral rule
                theory.add_rule(Rule(
                    head=f"{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"cap_{concept}_{prop}"
                ))
                rules_generated['capability_inherited'] += 1
            
            elif relation == 'HasProperty':
                # Generate defeasible property rule
                theory.add_rule(Rule(
                    head=f"has_{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"prop_{concept}_{prop}"
                ))
                rules_generated['property_inherited'] += 1
        
        # Add concept-specific properties/exceptions
        for (relation, prop) in properties.get(concept, []):
            if relation == 'CapableOf':
                # Specific capability
                theory.add_rule(Rule(
                    head=f"{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"cap_specific_{concept}_{prop}"
                ))
                rules_generated['capability_specific'] += 1
            
            elif relation == 'NotCapableOf':
                # DEFEATER - this is gold for Level 3!
                theory.add_rule(Rule(
                    head=f"~{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEATER,
                    label=f"defeater_{concept}_{prop}"
                ))
                rules_generated['defeater'] += 1
            
            elif relation == 'HasProperty':
                # Specific property
                theory.add_rule(Rule(
                    head=f"has_{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"prop_specific_{concept}_{prop}"
                ))
                rules_generated['property_specific'] += 1
    
    if verbose:
        print(f"\nRules generated by type:")
        for rule_type, count in sorted(rules_generated.items()):
            print(f"  {rule_type}: {count}")
    
    return theory


def test_instance_generation(theory: Theory, sample_size: int = 100) -> List[dict]:
    """
    Test instance generation on sample of rules.
    
    Args:
        theory: Generated theory
        sample_size: Number of targets to try
    
    Returns:
        List of generated instances
    """
    from blanc.reasoning.defeasible import defeasible_provable
    
    # Convert to defeasible theory
    converted = phi_kappa(theory, partition_random(0.5))
    
    # Find derivable targets at depth >= 2
    # Simple heuristic: try predicates that appear in multiple rules
    predicate_counts = defaultdict(int)
    for rule in converted.rules:
        pred = rule.head.split('(')[0]
        predicate_counts[pred] += 1
    
    # Try common predicates with sample instances
    targets = []
    facts_list = list(converted.facts)[:50]  # Sample facts
    
    for fact in facts_list:
        # Extract entity from fact
        if '(' in fact and ')' in fact:
            entity = fact.split('(')[1].split(')')[0]
            
            # Try each predicate
            for pred in list(predicate_counts.keys())[:20]:
                target = f"{pred}({entity})"
                if defeasible_provable(converted, target):
                    targets.append(target)
                    if len(targets) >= sample_size:
                        break
            
            if len(targets) >= sample_size:
                break
    
    return targets


def main():
    """Run cross-ontology scale validation."""
    
    print("=" * 70)
    print("CROSS-ONTOLOGY SCALE VALIDATION")
    print("=" * 70)
    print()
    
    # Configuration - paths relative to project root
    _project_root = Path(__file__).parent.parent
    OPENCYC_PATH = _project_root / "data" / "opencyc" / "opencyc-2012-05-10-readable.owl.gz"
    CONCEPTNET_PATH = _project_root / "data" / "conceptnet" / "conceptnet-assertions-5.7.0.csv.gz"
    
    SAMPLE_CONCEPTS = 1000  # Sample size for proof
    SAMPLE_EDGES = 100000   # Process 100K ConceptNet edges
    
    print("Configuration:")
    print(f"  OpenCyc path: {OPENCYC_PATH}")
    print(f"  ConceptNet path: {CONCEPTNET_PATH}")
    print(f"  Sample concepts: {SAMPLE_CONCEPTS}")
    print(f"  Sample edges: {SAMPLE_EDGES}")
    print()
    
    # Check if files exist
    if not OPENCYC_PATH.exists():
        print(f"ERROR: OpenCyc file not found at {OPENCYC_PATH}")
        print("  Please update path or download OpenCyc")
        return
    
    if not CONCEPTNET_PATH.exists():
        print(f"ERROR: ConceptNet file not found at {CONCEPTNET_PATH}")
        print("  Please update path or download ConceptNet 5.7")
        return
    
    # Step 1: Extract OpenCyc taxonomy
    print("Step 1: Extracting OpenCyc taxonomy...")
    print("-" * 70)
    
    try:
        opencyc = OpenCycExtractor(OPENCYC_PATH)
        opencyc.load()
        opencyc.extract_biology()
        
        # Build taxonomy dict
        taxonomy = defaultdict(set)
        for (child, parent) in opencyc.taxonomic_relations[:SAMPLE_CONCEPTS]:
            taxonomy[child].add(parent)
        
        print(f"  ✅ Taxonomy extracted:")
        print(f"     Concepts: {len(taxonomy)}")
        print(f"     Relations: {sum(len(parents) for parents in taxonomy.values())}")
        print()
        
    except Exception as e:
        print(f"  ❌ OpenCyc extraction failed: {e}")
        print("  Trying alternative: use existing biology KB taxonomy")
        
        # Fallback: use existing KB
        from examples.knowledge_bases.biology_kb import create_biology_kb
        kb = create_biology_kb()
        taxonomy = defaultdict(set)
        for rule in kb.rules:
            if rule.rule_type == RuleType.STRICT and '(' in rule.head:
                # Extract parent-child from strict rules
                head_pred = rule.head.split('(')[0]
                if len(rule.body) == 1:
                    body_pred = rule.body[0].split('(')[0]
                    taxonomy[body_pred].add(head_pred)
        
        print(f"  ⚠️ Using fallback taxonomy:")
        print(f"     Concepts: {len(taxonomy)}")
        print()
    
    # Step 2: Extract ConceptNet properties
    print("Step 2: Extracting ConceptNet properties...")
    print("-" * 70)
    
    try:
        conceptnet = ConceptNetExtractor(CONCEPTNET_PATH, weight_threshold=2.0)
        conceptnet.extract_biology(max_edges=SAMPLE_EDGES)
        
        # Build properties dict
        properties = defaultdict(list)
        for edge in conceptnet.biological_edges:
            concept = edge['start']
            relation = edge['relation']
            prop = edge['end']
            
            if relation in ['CapableOf', 'NotCapableOf', 'HasProperty']:
                properties[concept].append((relation, prop))
        
        print(f"  ✅ Properties extracted:")
        print(f"     Edges processed: {SAMPLE_EDGES:,}")
        print(f"     Biological edges: {len(conceptnet.biological_edges)}")
        print(f"     Concepts with properties: {len(properties)}")
        print(f"     CapableOf: {sum(1 for c in properties.values() for (r,p) in c if r == 'CapableOf')}")
        print(f"     NotCapableOf: {sum(1 for c in properties.values() for (r,p) in c if r == 'NotCapableOf')}")
        print(f"     HasProperty: {sum(1 for c in properties.values() for (r,p) in c if r == 'HasProperty')}")
        print()
        
    except Exception as e:
        print(f"  ❌ ConceptNet extraction failed: {e}")
        print("  Creating mock properties for proof-of-concept")
        
        # Mock for testing
        properties = {
            'bird': [('CapableOf', 'fly'), ('HasProperty', 'feathers')],
            'penguin': [('NotCapableOf', 'fly'), ('CapableOf', 'swim')],
            'mammal': [('CapableOf', 'walk'), ('HasProperty', 'hair')],
            'fish': [('CapableOf', 'swim'), ('HasProperty', 'gills')],
        }
        print(f"  ⚠️ Using mock properties for demonstration")
        print()
    
    # Step 3: Combine to generate rules
    print("Step 3: Generating defeasible rules...")
    print("-" * 70)
    
    combined_theory = combine_taxonomy_properties(taxonomy, properties, verbose=True)
    
    print(f"\n  ✅ Combined theory generated:")
    print(f"     Total facts: {len(combined_theory.facts)}")
    print(f"     Total rules: {len(combined_theory.rules)}")
    
    # Breakdown by rule type
    strict = len([r for r in combined_theory.rules if r.rule_type == RuleType.STRICT])
    defeasible = len([r for r in combined_theory.rules if r.rule_type == RuleType.DEFEASIBLE])
    defeaters = len([r for r in combined_theory.rules if r.rule_type == RuleType.DEFEATER])
    
    print(f"     Strict rules: {strict}")
    print(f"     Defeasible rules: {defeasible}")
    print(f"     Defeaters: {defeaters}")
    print()
    
    # Step 4: Test instance generation
    print("Step 4: Testing instance generation capacity...")
    print("-" * 70)
    
    try:
        targets = test_instance_generation(combined_theory, sample_size=50)
        print(f"  ✅ Found {len(targets)} derivable targets")
        
        # Test criticality on sample
        converted = phi_kappa(combined_theory, partition_random(0.5))
        instance_count = 0
        
        for target in targets[:10]:
            try:
                critical = full_theory_criticality(converted, target)
                instance_count += len(critical)
            except:
                pass
        
        avg_per_target = instance_count / min(10, len(targets)) if targets else 0
        print(f"  Average critical elements per target: {avg_per_target:.1f}")
        print(f"  Projected instances from {len(targets)} targets: {int(len(targets) * avg_per_target)}")
        print()
        
    except Exception as e:
        print(f"  ⚠️ Instance generation test failed: {e}")
        print()
    
    # Step 5: Calculate scale multipliers
    print("Step 5: Scale Analysis")
    print("=" * 70)
    
    current_rules = 2318
    current_instances = 374
    
    generated_rules = len(combined_theory.rules)
    
    print(f"\nCURRENT BENCHMARK:")
    print(f"  Rules: {current_rules:,}")
    print(f"  Instances: {current_instances:,}")
    
    print(f"\nSAMPLE EXTRACTION:")
    print(f"  Rules: {generated_rules:,}")
    print(f"  Multiplier: {generated_rules / current_rules:.1f}x")
    
    # Extrapolate to full extraction
    full_concepts = 50000  # Conservative estimate for biology
    full_edges = 1000000   # 1M ConceptNet biology edges (conservative)
    
    scale_factor = full_concepts / SAMPLE_CONCEPTS
    projected_rules = int(generated_rules * scale_factor)
    projected_instances = int(current_instances * (projected_rules / current_rules))
    
    print(f"\nPROJECTED FULL EXTRACTION:")
    print(f"  Biology concepts: {full_concepts:,}")
    print(f"  ConceptNet edges: {full_edges:,}")
    print(f"  Projected rules: {projected_rules:,}")
    print(f"  Rule multiplier: {projected_rules / current_rules:.1f}x")
    print(f"  Projected instances: {projected_instances:,}")
    print(f"  Instance multiplier: {projected_instances / current_instances:.1f}x")
    
    # Decision criteria
    print(f"\n" + "=" * 70)
    print("DECISION CRITERIA")
    print("=" * 70)
    
    proceed = False
    
    if generated_rules >= current_rules * 5:
        print("✅ CRITERION 1: Rules > 5x current (PASS)")
        proceed = True
    else:
        print(f"❌ CRITERION 1: Rules only {generated_rules / current_rules:.1f}x (FAIL - need 5x)")
    
    if defeaters >= 10:
        print(f"✅ CRITERION 2: Defeaters >= 10 (PASS - found {defeaters})")
        proceed = proceed and True
    else:
        print(f"❌ CRITERION 2: Defeaters < 10 (FAIL - only {defeaters})")
        proceed = False
    
    if projected_rules >= 20000:
        print(f"✅ CRITERION 3: Projected >= 20K rules (PASS - {projected_rules:,})")
    else:
        print(f"⚠️  CRITERION 3: Projected < 20K rules (MARGINAL - {projected_rules:,})")
    
    print()
    print("=" * 70)
    
    if proceed:
        print("✅ RECOMMENDATION: PROCEED WITH FULL EXTRACTION")
        print()
        print("Next steps:")
        print("  1. Allocate 1 week for full extraction (Week 8.6)")
        print("  2. Extract all 50K biology concepts from OpenCyc")
        print("  3. Extract all biology edges from ConceptNet")
        print("  4. Generate 20K-100K rules")
        print("  5. Regenerate development instances")
        print()
        print(f"Expected outcome:")
        print(f"  - Rules: {projected_rules:,} (vs {current_rules:,})")
        print(f"  - Instances: {projected_instances:,} (vs {current_instances:,})")
        print(f"  - This is a game-changer for the paper!")
    else:
        print("❌ RECOMMENDATION: STICK WITH CURRENT SOURCES")
        print()
        print("Reasons:")
        print("  - Sample extraction didn't achieve 5x scale")
        print("  - May not be worth 1 week investment")
        print("  - Current sources (YAGO, WordNet) may be sufficient")
        print()
        print("Alternative: Try different extraction parameters or sources")
    
    print("=" * 70)
    
    return {
        'current_rules': current_rules,
        'generated_rules': generated_rules,
        'projected_rules': projected_rules,
        'rule_multiplier': projected_rules / current_rules,
        'defeaters_found': defeaters,
        'recommendation': 'PROCEED' if proceed else 'RECONSIDER'
    }


if __name__ == '__main__':
    import sys
    
    print()
    print("Cross-Ontology Extraction Validation")
    print("Testing: Can we 10-100x our ruleset?")
    print()
    
    try:
        results = main()
        
        # Save results
        output_file = Path('results/cross_ontology_validation.json')
        output_file.parent.mkdir(exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
        # Exit code based on recommendation
        if results['recommendation'] == 'PROCEED':
            sys.exit(0)  # Success - should proceed
        else:
            sys.exit(1)  # Reconsider - not worth it
            
    except Exception as e:
        print(f"\n❌ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
