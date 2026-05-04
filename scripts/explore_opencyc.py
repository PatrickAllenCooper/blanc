"""
Explore OpenCyc structure to understand format.

Author: Anonymous Authors
Date: 2026-02-11
"""

import gzip
import sys
from pathlib import Path

def explore_opencyc(opencyc_path: Path, max_lines: int = 100):
    """
    Load and explore OpenCyc OWL file.
    
    Args:
        opencyc_path: Path to .owl.gz file
        max_lines: Number of lines to examine
    """
    print("=" * 70)
    print("OpenCyc Structure Exploration")
    print("=" * 70)
    
    print(f"\nFile: {opencyc_path}")
    print(f"Size: {opencyc_path.stat().st_size / (1024*1024):.1f} MB")
    
    # Read first N lines
    print(f"\nFirst {max_lines} lines:\n")
    
    with gzip.open(opencyc_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i >= max_lines:
                break
            print(f"{i+1:4d}: {line.rstrip()[:120]}")
    
    print("\n" + "=" * 70)
    
    # Look for biology-related terms
    print("\nSearching for biology-related terms (sample)...\n")
    
    bio_terms = []
    with gzip.open(opencyc_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f):
            if i > 100000:  # Check first 100K lines
                break
            
            line_lower = line.lower()
            if any(term in line_lower for term in ['bird', 'animal', 'organism', 'species', 'biological']):
                bio_terms.append(line.rstrip()[:150])
                if len(bio_terms) >= 20:
                    break
    
    print(f"Found {len(bio_terms)} biology-related lines:")
    for i, term in enumerate(bio_terms[:10], 1):
        print(f"  {i}. {term}")
    
    if len(bio_terms) > 10:
        print(f"  ... and {len(bio_terms) - 10} more")
    
    print("\n" + "=" * 70)


if __name__ == "__main__":
    opencyc_path = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
    
    if not opencyc_path.exists():
        print(f"ERROR: OpenCyc file not found at {opencyc_path}")
        sys.exit(1)
    
    explore_opencyc(opencyc_path, max_lines=100)
    
    print("\n[SUCCESS] Exploration complete")
    print("\nNext steps:")
    print("  1. Understand OWL/RDF format")
    print("  2. Identify biological concept patterns")
    print("  3. Design extraction strategy")
