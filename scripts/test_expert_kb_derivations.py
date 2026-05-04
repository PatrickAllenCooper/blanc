"""
Test derivation chains in expert KBs.

Find derivable conclusions that go through rule chains to verify
the expert KBs have sufficient depth for instance generation.

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_kb import create_biology_kb
from examples.knowledge_bases.legal_kb import create_legal_kb
from examples.knowledge_bases.materials_kb import create_materials_kb
from blanc.reasoning.defeasible import defeasible_provable
from blanc.generation.partition import compute_dependency_depths


def test_derivations(kb_name, theory):
    """Test what can be derived from a KB."""
    
    print(f"\n{'=' * 70}")
    print(f"Testing Derivations: {kb_name}")
    print('=' * 70)
    
    print(f"\nKB: {len(theory.rules)} rules, {len(theory.facts)} facts")
    
    # Compute depths
    depths = compute_dependency_depths(theory)
    print(f"Max depth: {max(depths.values()) if depths else 0}")
    
    # Test some derived conclusions
    print("\nTesting derived conclusions...")
    
    # For biology: test if organism instances inherit taxonomic properties
    if kb_name == "Biology":
        test_targets = [
            "animal(robin)",  # Should be derivable from bird(robin) -> animal(robin)
            "organism(robin)",  # Should be derivable
        ]
    elif kb_name == "Legal":
        test_targets = [
            "legal_document(gdpr)",  # Should be derivable from statute(gdpr) -> legal_document(gdpr)
        ]
    else:  # Materials
        test_targets = [
            "material(steel)",  # Should be derivable from alloy(steel) -> material(steel)
        ]
    
    for target in test_targets:
        try:
            result = defeasible_provable(theory, target)
            status = "[OK]" if result else "[NO]"
            print(f"  {status} {target}")
        except Exception as e:
            print(f"  [ERROR] {target}: {e}")
    
    # Show what facts we have
    print(f"\nSample facts ({len(theory.facts)} total):")
    for fact in list(theory.facts)[:10]:
        print(f"  {fact}")
    
    # Show what rules we have
    print(f"\nSample rules ({len(theory.rules)} total):")
    for rule in list(theory.rules)[:10]:
        print(f"  {rule}")
    
    return True


def main():
    """Test all 3 KBs."""
    
    print("=" * 70)
    print("DERIVATION CHAIN TESTING")
    print("=" * 70)
    
    # Test each KB
    bio_kb = create_biology_kb()
    test_derivations("Biology", bio_kb)
    
    legal_kb = create_legal_kb()
    test_derivations("Legal", legal_kb)
    
    materials_kb = create_materials_kb()
    test_derivations("Materials", materials_kb)
    
    print("\n" + "=" * 70)
    print("DERIVATION TEST COMPLETE")
    print("=" * 70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
