"""
Verify all required knowledge bases are present and accessible.

Checks:
1. ConceptNet5 5.7.0
2. TaxKB
3. WordNet 3.0 Prolog
4. Backup resources

Author: Anonymous Authors
Date: 2026-02-11
"""

from pathlib import Path
import sys


def check_kb(name: str, path: Path, required: bool = True) -> bool:
    """Check if KB is present."""
    exists = path.exists()
    status = "[OK]" if exists else "[MISSING]"
    req_str = "REQUIRED" if required else "OPTIONAL"
    
    print(f"  {status} {name:30s} [{req_str}]")
    
    if exists:
        if path.is_file():
            size_mb = path.stat().st_size / (1024 * 1024)
            print(f"      Path: {path}")
            print(f"      Size: {size_mb:.1f} MB")
        else:
            files = list(path.glob('*'))[:5]
            print(f"      Path: {path}")
            print(f"      Files: {len(list(path.glob('*')))} total")
            if files:
                print(f"      Sample: {[f.name for f in files]}")
    else:
        if required:
            print(f"      *** MISSING: {path}")
    
    print()
    return exists


def main():
    """Verify all KBs."""
    print("=" * 70)
    print("Knowledge Base Verification")
    print("=" * 70)
    print()
    
    all_ok = True
    
    # Primary KBs (REQUIRED)
    print("PRIMARY KNOWLEDGE BASES (Required for NeurIPS):")
    print("-" * 70)
    print()
    
    kb1 = check_kb(
        "ConceptNet5 5.7.0",
        Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz"),
        required=True
    )
    
    kb2 = check_kb(
        "TaxKB",
        Path("D:/datasets/TaxKB"),
        required=True
    )
    
    kb3 = check_kb(
        "WordNet 3.0 Prolog",
        Path("D:/datasets/prolog"),
        required=True
    )
    
    all_ok = all_ok and kb1 and kb2 and kb3
    
    # Backup KBs (OPTIONAL)
    print("BACKUP/SUPPLEMENTARY RESOURCES (Optional):")
    print("-" * 70)
    print()
    
    check_kb(
        "OpenCyc 4.0",
        Path("D:/datasets/opencyc-kb/opencyc-2012-05-10-readable.owl.gz"),
        required=False
    )
    
    check_kb(
        "SUMO",
        Path("D:/datasets/sumo"),
        required=False
    )
    
    check_kb(
        "ProofWriter",
        Path("D:/datasets/proofwriter"),
        required=False
    )
    
    check_kb(
        "NephroDoctor",
        Path("D:/datasets/NephroDoctor"),
        required=False
    )
    
    # Local KBs
    print("LOCAL KNOWLEDGE BASES (Created):")
    print("-" * 70)
    print()
    
    check_kb(
        "Avian Biology (MVP)",
        Path("examples/knowledge_bases/avian_biology/avian_biology_base.py"),
        required=False
    )
    
    check_kb(
        "OpenCyc Biology (Extracted)",
        Path("examples/knowledge_bases/opencyc_biology/opencyc_biology.pkl"),
        required=False
    )
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    if all_ok:
        print("[SUCCESS] ALL REQUIRED KNOWLEDGE BASES PRESENT")
        print()
        print("Ready for:")
        print("  - Week 1: ConceptNet5 biology extraction")
        print("  - Week 2: TaxKB legal extraction")  
        print("  - Week 3: WordNet integration")
        print()
        print("No blockers identified.")
        return 0
    else:
        print("[ERROR] MISSING REQUIRED KNOWLEDGE BASES")
        print()
        print("Action needed:")
        if not kb1:
            print("  - Download ConceptNet5 5.7.0")
        if not kb2:
            print("  - Download TaxKB")
        if not kb3:
            print("  - Download WordNet 3.0 Prolog")
        return 1


if __name__ == "__main__":
    sys.exit(main())
