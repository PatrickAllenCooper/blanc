"""
Extract biology KB from OpenCyc.

This script performs the complete extraction pipeline:
1. Load OpenCyc OWL
2. Extract biological concepts
3. Convert to definite LP
4. Save as Prolog + Theory pickle

Author: Patrick Cooper
Date: 2026-02-11
"""

import sys
from pathlib import Path
import pickle

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.ontology.opencyc_extractor import OpenCycExtractor


def main():
    """Execute OpenCyc biology extraction."""
    print("=" * 70)
    print("OpenCyc Biology Extraction")
    print("=" * 70)
    
    # Path to OpenCyc
    opencyc_path = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
    
    if not opencyc_path.exists():
        print(f"ERROR: OpenCyc not found at {opencyc_path}")
        print("Please ensure OpenCyc is downloaded to D:\\datasets\\opencyc-kb\\")
        return 1
    
    # Create extractor
    print("\n1. Initializing extractor...")
    extractor = OpenCycExtractor(opencyc_path)
    
    # Load OpenCyc
    print("\n2. Loading OpenCyc (this may take a few minutes)...")
    extractor.load()
    
    # Extract biology
    print("\n3. Extracting biological concepts...")
    extractor.extract_biology()
    
    # Convert to LP
    print("\n4. Converting to definite logic program...")
    theory = extractor.to_definite_lp()
    
    print(f"\nExtracted Biology KB:")
    print(f"  Facts: {len(theory.facts)}")
    print(f"  Rules: {len(theory.rules)}")
    print(f"  Total size: {len(theory)}")
    
    # Save
    output_dir = Path("examples/knowledge_bases/opencyc_biology")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n5. Saving to {output_dir}...")
    
    # Save as Prolog
    prolog_path = output_dir / "opencyc_biology.pl"
    with open(prolog_path, 'w') as f:
        f.write("% OpenCyc Biology KB\n")
        f.write(f"% Extracted: 2026-02-11\n")
        f.write(f"% Source: OpenCyc 4.0 (2012-05-10)\n")
        f.write(f"% Concepts: {len(extractor.biological_concepts)}\n")
        f.write(f"% Relations: {len(extractor.taxonomic_relations)}\n")
        f.write("\n")
        f.write(theory.to_prolog())
    
    print(f"  Saved Prolog: {prolog_path}")
    
    # Save as pickle for fast loading
    pickle_path = output_dir / "opencyc_biology.pkl"
    with open(pickle_path, 'wb') as f:
        pickle.dump(theory, f)
    
    print(f"  Saved pickle: {pickle_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Biology KB: {len(theory)} facts + rules")
    print(f"Output: {output_dir}")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
