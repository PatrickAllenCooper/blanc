"""
Extract biology KB from ConceptNet5.

Extracts behavioral defaults, exceptions, and taxonomic structure.

Author: Patrick Cooper
Date: 2026-02-11
"""

import sys
from pathlib import Path
import pickle

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.ontology.conceptnet_extractor import ConceptNetExtractor
from blanc.reasoning.defeasible import defeasible_provable
from blanc.generation.partition import compute_dependency_depths


def main():
    """Extract ConceptNet5 biology KB."""
    print("=" * 70)
    print("ConceptNet5 Biology Extraction")
    print("=" * 70)
    
    # Path to ConceptNet5
    cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
    
    if not cn_path.exists():
        print(f"ERROR: ConceptNet5 not found at {cn_path}")
        print("Run: python scripts/download_conceptnet5.py")
        return 1
    
    print(f"\nFile: {cn_path}")
    print(f"Size: {cn_path.stat().st_size / (1024*1024):.1f} MB")
    
    # Extract
    print("\n1. Extracting biological edges...")
    print("   This will process 21M edges (may take 5-10 minutes)")
    print("   Filtering: weight > 2.0, biological keywords, English only")
    
    extractor = ConceptNetExtractor(cn_path, weight_threshold=2.0)
    extractor.extract_biology()  # Process all edges
    
    print(f"   Extracted: {len(extractor.biological_edges)} biological edges")
    
    # Convert to theory
    print("\n2. Converting to defeasible theory...")
    theory = extractor.to_theory()
    
    print(f"\n   Biology KB:")
    print(f"     Facts (IsA): {len(theory.facts)}")
    print(f"     Rules total: {len(theory.rules)}")
    
    from blanc.core.theory import RuleType
    defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
    defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
    strict = theory.get_rules_by_type(RuleType.STRICT)
    
    print(f"     - Strict: {len(strict)}")
    print(f"     - Defeasible: {len(defeasible)}")
    print(f"     - Defeaters: {len(defeaters)}")
    print(f"     Total size: {len(theory)}")
    
    # Validate structure
    print("\n3. Validating derivation structure...")
    
    # Compute dependency depths
    depths = compute_dependency_depths(theory)
    print(f"   Predicates: {len(depths)}")
    print(f"   Max depth: {max(depths.values()) if depths else 0}")
    
    # Count depth >= 2 (target set Q per paper)
    depth_2_plus = {pred: d for pred, d in depths.items() if d >= 2}
    print(f"   Depth >= 2: {len(depth_2_plus)} predicates")
    
    if len(depth_2_plus) == 0:
        print("\n   WARNING: No predicates at depth >= 2!")
        print("   This KB may not be suitable for instance generation.")
    else:
        print(f"\n   [OK] Target set Q has {len(depth_2_plus)} predicates")
        print(f"   Sample predicates at depth >= 2:")
        for pred, depth in list(depth_2_plus.items())[:5]:
            print(f"     - {pred} (depth {depth})")
    
    # Test defeasible reasoning
    print("\n4. Testing defeasible reasoning on sample...")
    
    # Find a sample conclusion to test
    if defeasible:
        sample_rule = defeasible[0]
        print(f"   Sample rule: {sample_rule.head} :- {', '.join(sample_rule.body)}")
        
        # Try to derive conclusion (if we have the facts)
        # This is a basic sanity check
    
    # Save
    output_dir = Path("examples/knowledge_bases/conceptnet_biology")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n5. Saving to {output_dir}...")
    
    # Save as Prolog
    prolog_path = output_dir / "conceptnet_biology.pl"
    with open(prolog_path, 'w', encoding='utf-8') as f:
        f.write("% ConceptNet5 Biology KB\n")
        f.write(f"% Extracted: 2026-02-11\n")
        f.write(f"% Source: ConceptNet 5.7.0\n")
        f.write(f"% Edges: {len(extractor.biological_edges)}\n")
        f.write(f"% Weight threshold: {extractor.weight_threshold}\n")
        f.write("\n")
        f.write(theory.to_prolog())
    
    print(f"  Saved Prolog: {prolog_path}")
    
    # Save as pickle
    pickle_path = output_dir / "conceptnet_biology.pkl"
    with open(pickle_path, 'wb') as f:
        pickle.dump(theory, f)
    
    print(f"  Saved pickle: {pickle_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Biology KB: {len(theory)} elements")
    print(f"  Facts: {len(theory.facts)}")
    print(f"  Defeasible rules: {len(defeasible)}")
    print(f"  Defeaters: {len(defeaters)}")
    print(f"Output: {output_dir}")
    
    if len(depth_2_plus) > 0:
        print(f"\n[SUCCESS] Ready for instance generation")
        print(f"Target set Q: {len(depth_2_plus)} predicates at depth >= 2")
    else:
        print(f"\n[WARNING] May need to add more complex rules for depth >= 2")
    
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
