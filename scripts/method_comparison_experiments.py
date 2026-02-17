"""
Method Comparison: Taxonomy → Rules → Defeasible Rules

Experiments with 5 different approaches to test which works best.

Methods tested:
  1. Cross-Ontology (OpenCyc + ConceptNet) - RECOMMENDED
  2. Property Inheritance with Templates
  3. Closed World Assumption (CWA)
  4. YAGO Full Extraction
  5. ConceptNet Standalone

For each method, measure:
  - Rules generated
  - Defeaters generated (for Level 3)
  - Instance yield
  - Quality (sample validation)
  - Extraction time

Author: Patrick Cooper
Date: 2026-02-13
"""

from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict
import time

from blanc.core.theory import Theory, Rule, RuleType


# ============================================================================
# METHOD 1: Cross-Ontology (OpenCyc Taxonomy + ConceptNet Properties)
# ============================================================================

def method1_cross_ontology(
    opencyc_path: Path,
    conceptnet_path: Path,
    sample_size: int = 1000
) -> Dict:
    """
    Combine OpenCyc taxonomy with ConceptNet properties.
    
    Pros:
      - Leverages both large-scale sources
      - ConceptNet has explicit defeaters (NotCapableOf)
      - Fully automated from expert sources
    
    Cons:
      - Requires ontology alignment
      - Two dependencies
    """
    print("\n" + "=" * 70)
    print("METHOD 1: Cross-Ontology (OpenCyc + ConceptNet)")
    print("=" * 70)
    
    start_time = time.time()
    theory = Theory()
    
    try:
        # Extract taxonomy from OpenCyc
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        opencyc = OpenCycExtractor(opencyc_path)
        opencyc.load()
        opencyc.extract_biology()
        
        # Extract properties from ConceptNet
        from blanc.ontology.conceptnet_extractor import ConceptNetExtractor
        conceptnet = ConceptNetExtractor(conceptnet_path)
        conceptnet.extract_biology(max_edges=100000)
        
        # Combine (using function from validation script)
        # For now, create simple version
        
        for concept in list(opencyc.biological_concepts)[:sample_size]:
            theory.add_fact(f"concept({concept})")
        
        for (child, parent) in opencyc.taxonomic_relations[:sample_size]:
            theory.add_rule(Rule(
                head=f"{parent}(X)",
                body=(f"{child}(X)",),
                rule_type=RuleType.STRICT,
                label=f"tax_{child}_{parent}"
            ))
        
        # Add ConceptNet behavioral rules
        for edge in conceptnet.biological_edges[:sample_size]:
            concept = edge['start']
            relation = edge['relation']
            prop = edge['end']
            
            if relation == 'CapableOf':
                theory.add_rule(Rule(
                    head=f"{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"cap_{concept}_{prop}"
                ))
            elif relation == 'NotCapableOf':
                theory.add_rule(Rule(
                    head=f"~{prop}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEATER,
                    label=f"def_{concept}_{prop}"
                ))
        
        elapsed = time.time() - start_time
        
        defeaters = len([r for r in theory.rules if r.rule_type == RuleType.DEFEATER])
        
        return {
            'method': 'Cross-Ontology',
            'rules': len(theory.rules),
            'defeaters': defeaters,
            'facts': len(theory.facts),
            'time_seconds': elapsed,
            'status': 'SUCCESS',
            'theory': theory
        }
        
    except Exception as e:
        return {
            'method': 'Cross-Ontology',
            'rules': 0,
            'defeaters': 0,
            'status': f'FAILED: {e}',
            'time_seconds': time.time() - start_time
        }


# ============================================================================
# METHOD 2: Property Templates
# ============================================================================

def method2_property_templates(sample_size: int = 1000) -> Dict:
    """
    Use predefined templates for each taxonomic class.
    
    Templates define typical behaviors for high-level categories.
    
    Pros:
      - Simple, deterministic
      - Can encode domain expertise
      - Works with taxonomy alone
    
    Cons:
      - Requires manual template curation
      - Limited to predefined properties
      - Not fully automated
    """
    print("\n" + "=" * 70)
    print("METHOD 2: Property Templates")
    print("=" * 70)
    
    start_time = time.time()
    theory = Theory()
    
    # Define templates (these would come from expert sources)
    TEMPLATES = {
        'bird': {
            'CapableOf': ['fly', 'sing', 'nest', 'migrate'],
            'HasProperty': ['feathers', 'beak', 'wings']
        },
        'mammal': {
            'CapableOf': ['walk', 'nurse_young'],
            'HasProperty': ['hair', 'warm_blooded']
        },
        'fish': {
            'CapableOf': ['swim'],
            'HasProperty': ['gills', 'scales', 'fins']
        },
        'reptile': {
            'CapableOf': ['crawl'],
            'HasProperty': ['scales', 'cold_blooded']
        }
    }
    
    # Exception templates
    EXCEPTIONS = {
        'penguin': {'NotCapableOf': ['fly']},
        'ostrich': {'NotCapableOf': ['fly']},
        'whale': {'NotCapableOf': ['walk']},
        'dolphin': {'NotCapableOf': ['walk']},
        'bat': {'CapableOf': ['fly']}  # Exception to mammal template
    }
    
    # Simple taxonomy
    taxonomy = {
        'robin': ['bird'],
        'penguin': ['bird'],
        'eagle': ['bird'],
        'dog': ['mammal'],
        'whale': ['mammal'],
        'dolphin': ['mammal'],
        'salmon': ['fish'],
    }
    
    # Generate rules from templates
    for concept, parents in taxonomy.items():
        theory.add_fact(f"concept({concept})")
        
        # Add taxonomic rules
        for parent in parents:
            theory.add_rule(Rule(
                head=f"{parent}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.STRICT,
                label=f"tax_{concept}_{parent}"
            ))
            
            # Inherit template properties
            for cap in TEMPLATES.get(parent, {}).get('CapableOf', []):
                theory.add_rule(Rule(
                    head=f"{cap}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"cap_{concept}_{cap}"
                ))
        
        # Add exceptions
        if concept in EXCEPTIONS:
            for cap in EXCEPTIONS[concept].get('NotCapableOf', []):
                theory.add_rule(Rule(
                    head=f"~{cap}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.DEFEATER,
                    label=f"def_{concept}_{cap}"
                ))
    
    elapsed = time.time() - start_time
    defeaters = len([r for r in theory.rules if r.rule_type == RuleType.DEFEATER])
    
    return {
        'method': 'Property Templates',
        'rules': len(theory.rules),
        'defeaters': defeaters,
        'facts': len(theory.facts),
        'time_seconds': elapsed,
        'status': 'SUCCESS',
        'theory': theory,
        'note': 'Templates require expert curation'
    }


# ============================================================================
# METHOD 3: Closed World Assumption
# ============================================================================

def method3_closed_world(sample_size: int = 1000) -> Dict:
    """
    Use CWA: absence of assertion = evidence of absence.
    
    If 'flies(penguin)' not asserted → generate ~flies(X) :- penguin(X)
    
    Pros:
      - Automatic exception discovery
      - Works with incomplete KBs
    
    Cons:
      - CWA can be too strong
      - Requires negative examples or corpus validation
    """
    print("\n" + "=" * 70)
    print("METHOD 3: Closed World Assumption")
    print("=" * 70)
    
    start_time = time.time()
    theory = Theory()
    
    # Would require full implementation
    # Placeholder for now
    
    return {
        'method': 'Closed World Assumption',
        'rules': 0,
        'defeaters': 0,
        'status': 'NOT IMPLEMENTED (requires corpus validation)',
        'time_seconds': time.time() - start_time
    }


# ============================================================================
# METHOD 4: YAGO Full Extraction
# ============================================================================

def method4_yago_full() -> Dict:
    """
    Extract from full YAGO 4.5 (109M facts).
    
    YAGO has both taxonomy AND properties in one source.
    
    Pros:
      - Single source (simpler)
      - Already has behavioral properties
      - Proven to work (we use YAGO subset)
    
    Cons:
      - Still limited compared to Cyc + ConceptNet combo
      - May not have NotCapableOf explicitly
    """
    print("\n" + "=" * 70)
    print("METHOD 4: YAGO Full Extraction")
    print("=" * 70)
    
    start_time = time.time()
    
    # We already use YAGO - could just extract MORE
    from examples.knowledge_bases.biology_kb import create_biology_kb
    
    # Current YAGO extraction
    kb = create_biology_kb()
    
    print(f"  Current YAGO extraction: {len(kb.rules)} rules")
    print(f"  Full YAGO has 109M facts")
    print(f"  Potential: Extract 10-100x more")
    
    return {
        'method': 'YAGO Full',
        'rules': len(kb.rules),
        'defeaters': len([r for r in kb.rules if r.rule_type == RuleType.DEFEATER]),
        'status': 'CURRENT APPROACH (can scale)',
        'time_seconds': time.time() - start_time,
        'potential': '10-100x via full extraction'
    }


# ============================================================================
# METHOD 5: ConceptNet Standalone
# ============================================================================

def method5_conceptnet_standalone(conceptnet_path: Path, sample_size: int = 10000) -> Dict:
    """
    Use only ConceptNet (no OpenCyc).
    
    ConceptNet has IsA (taxonomy) AND behavioral relations.
    
    Pros:
      - Single source
      - Has both taxonomy and properties
      - Explicit defeaters (NotCapableOf)
      - Already validated (we tested this Week 1)
    
    Cons:
      - Crowdsourced (less authoritative than Cyc)
      - May have quality issues
    """
    print("\n" + "=" * 70)
    print("METHOD 5: ConceptNet Standalone")
    print("=" * 70)
    
    start_time = time.time()
    theory = Theory()
    
    try:
        from blanc.ontology.conceptnet_extractor import ConceptNetExtractor
        
        conceptnet = ConceptNetExtractor(conceptnet_path)
        conceptnet.extract_biology(max_edges=sample_size)
        theory = conceptnet.to_definite_lp()
        
        elapsed = time.time() - start_time
        defeaters = len([r for r in theory.rules if r.rule_type == RuleType.DEFEATER])
        
        return {
            'method': 'ConceptNet Standalone',
            'rules': len(theory.rules),
            'defeaters': defeaters,
            'facts': len(theory.facts),
            'time_seconds': elapsed,
            'status': 'SUCCESS',
            'theory': theory
        }
        
    except Exception as e:
        return {
            'method': 'ConceptNet Standalone',
            'rules': 0,
            'status': f'FAILED: {e}',
            'time_seconds': time.time() - start_time
        }


# ============================================================================
# COMPARISON RUNNER
# ============================================================================

def run_all_methods():
    """Run all methods and compare results."""
    
    print()
    print("*" * 70)
    print("TAXONOMY → RULES → DEFEASIBLE RULES")
    print("Method Comparison Experiments")
    print("*" * 70)
    
    # Paths (adjust as needed)
    OPENCYC_PATH = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
    CONCEPTNET_PATH = Path(r"D:\datasets\conceptnet5\conceptnet-assertions-5.7.0.csv.gz")
    
    results = []
    
    # Run all methods
    methods = [
        ('Method 1', lambda: method1_cross_ontology(OPENCYC_PATH, CONCEPTNET_PATH, 1000)),
        ('Method 2', lambda: method2_property_templates(1000)),
        ('Method 3', lambda: method3_closed_world(1000)),
        ('Method 4', lambda: method4_yago_full()),
        ('Method 5', lambda: method5_conceptnet_standalone(CONCEPTNET_PATH, 10000)),
    ]
    
    for name, method_fn in methods:
        try:
            result = method_fn()
            results.append(result)
        except Exception as e:
            results.append({
                'method': name,
                'status': f'ERROR: {e}',
                'rules': 0,
                'defeaters': 0
            })
    
    # Print comparison table
    print("\n\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)
    print()
    print(f"{'Method':<25} {'Rules':>10} {'Defeaters':>10} {'Time':>8} {'Status':<20}")
    print("-" * 70)
    
    current_benchmark = 2318
    
    for result in results:
        method = result['method']
        rules = result.get('rules', 0)
        defeaters = result.get('defeaters', 0)
        time_s = result.get('time_seconds', 0)
        status = result.get('status', 'UNKNOWN')
        
        multiplier = f"({rules / current_benchmark:.1f}x)" if rules > 0 else ""
        
        print(f"{method:<25} {rules:>10} {defeaters:>10} {time_s:>7.1f}s {status:<20}")
        if multiplier:
            print(f"{'':25} {multiplier:>10}")
    
    print()
    print("=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)
    
    # Find best method
    valid_results = [r for r in results if 'SUCCESS' in r.get('status', '')]
    
    if not valid_results:
        print("❌ No methods succeeded")
        print("   Recommendation: Debug and retry")
        return results
    
    # Sort by rules generated
    best = max(valid_results, key=lambda r: r.get('rules', 0))
    
    print(f"\n✅ BEST METHOD: {best['method']}")
    print(f"   Rules: {best['rules']:,}")
    print(f"   Defeaters: {best.get('defeaters', 0):,}")
    print(f"   Multiplier: {best['rules'] / current_benchmark:.1f}x vs current")
    
    if best['rules'] >= current_benchmark * 5:
        print(f"\n✅ PROCEED: Scale increase >= 5x")
        print(f"   Recommended: Implement full extraction (Week 8.6)")
    elif best['rules'] >= current_benchmark * 2:
        print(f"\n⚠️  MARGINAL: Scale increase 2-5x")
        print(f"   Recommended: Consider if worth time investment")
    else:
        print(f"\n❌ NOT WORTH: Scale increase < 2x")
        print(f"   Recommended: Stick with current sources")
    
    return results


if __name__ == '__main__':
    import sys
    
    try:
        results = run_all_methods()
        
        # Save results
        import json
        output_file = Path('results/method_comparison.json')
        output_file.parent.mkdir(exist_ok=True)
        
        # Convert Theory objects to dict for JSON
        for r in results:
            if 'theory' in r:
                r['theory'] = f"<Theory with {len(r['theory'].rules)} rules>"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Experiment failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
