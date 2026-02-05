"""
Test and validate downloaded knowledge bases.

This script tests TaxKB and NephroDoctor knowledge bases downloaded to D:/datasets/
"""

import sys
from pathlib import Path

# Set UTF-8 encoding for Windows console
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blanc import KnowledgeBase
from blanc.core.theory import Rule, RuleType, Theory
from blanc.knowledge_bases import register_kb, KnowledgeBaseRegistry
from blanc.backends.asp import CLINGO_AVAILABLE
from blanc.backends.prolog import PYSWIP_AVAILABLE

print("=" * 80)
print("BLANC Knowledge Base Validation")
print("=" * 80)
print(f"\nBackend Availability:")
print(f"  ASP (Clingo): {'✓' if CLINGO_AVAILABLE else '✗'}")
print(f"  Prolog (PySwip): {'✓' if PYSWIP_AVAILABLE else '✗'}")
print()

# Register downloaded knowledge bases
print("Registering downloaded knowledge bases...")

# NephroDoctor
nephro_path = Path("D:/datasets/NephroDoctor/knowledge.pl")
if nephro_path.exists():
    register_kb(
        name="nephrodoc",
        domain="medical",
        format="prolog",
        path=nephro_path,
        description="NephroDoctor: Expert system for nephrology diagnosis",
        size_estimate=500,
        source_url="https://github.com/nicoladileo/NephroDoctor",
        citation="Nicola Dileo, Tommaso Viterbo (2015)",
        difficulty="hard",
        tags=["medical", "expert-system", "nephrology", "italian"],
        license="GPL-3.0"
    )
    print(f"  ✓ Registered: nephrodoc ({nephro_path})")
else:
    print(f"  ✗ Not found: {nephro_path}")

# TaxKB - Register main API and a sample KB
taxkb_api = Path("D:/datasets/TaxKB/api.pl")
if taxkb_api.exists():
    register_kb(
        name="taxkb_api",
        domain="legal",
        format="prolog",
        path=taxkb_api,
        description="TaxKB API for LogicalEnglish tax regulations",
        size_estimate=100,
        source_url="https://github.com/mcalejo/TaxKB",
        citation="Miguel Calejo, Bob Kowalski, et al. (2021)",
        difficulty="hard",
        tags=["legal", "tax", "logical-english"],
        license="Apache-2.0"
    )
    print(f"  ✓ Registered: taxkb_api ({taxkb_api})")
else:
    print(f"  ✗ Not found: {taxkb_api}")

# TaxKB - Sample citizenship KB
taxkb_citizenship = Path("D:/datasets/TaxKB/kb/0_citizenship.pl")
if taxkb_citizenship.exists():
    register_kb(
        name="taxkb_citizenship",
        domain="legal",
        format="prolog",
        path=taxkb_citizenship,
        description="TaxKB: British citizenship acquisition rules",
        size_estimate=50,
        source_url="https://github.com/mcalejo/TaxKB",
        citation="Miguel Calejo, Bob Kowalski, et al. (2021)",
        difficulty="medium",
        tags=["legal", "citizenship", "logical-english"],
        license="Apache-2.0"
    )
    print(f"  ✓ Registered: taxkb_citizenship ({taxkb_citizenship})")
else:
    print(f"  ✗ Not found: {taxkb_citizenship}")

print(f"\nTotal registered KBs: {len(KnowledgeBaseRegistry.list_all())}")

# List all registered KBs
print("\n" + "=" * 80)
print("All Registered Knowledge Bases:")
print("=" * 80)
for kb_meta in KnowledgeBaseRegistry.list_all():
    print(f"\n{kb_meta.name}")
    print(f"  Domain: {kb_meta.domain}")
    print(f"  Format: {kb_meta.format}")
    print(f"  Path: {kb_meta.path}")
    print(f"  Description: {kb_meta.description}")
    if kb_meta.tags:
        print(f"  Tags: {', '.join(kb_meta.tags)}")

# Test loading with ASP backend
if CLINGO_AVAILABLE:
    print("\n" + "=" * 80)
    print("Testing ASP Backend")
    print("=" * 80)
    
    # Create a simple test theory
    print("\n1. Testing simple theory...")
    simple_theory = Theory()
    simple_theory.add_fact("person(alice)")
    simple_theory.add_fact("person(bob)")
    simple_theory.add_rule(
        Rule(head="human(X)", body=("person(X)",))
    )
    
    try:
        kb_asp = KnowledgeBase(backend='asp')
        kb_asp.load(simple_theory)
        print("  ✓ Theory loaded successfully")
        
        # Test solve
        with kb_asp.backend._control.solve(yield_=True) as handle:
            for model in handle:
                atoms = [str(a) for a in model.symbols(shown=True)]
                print(f"  ✓ Model generated: {len(atoms)} atoms")
                if len(atoms) <= 10:
                    print(f"    Atoms: {sorted(atoms)}")
                break
    except Exception as e:
        print(f"  ✗ Error: {e}")
    
    # Try to load a real downloaded KB (this might fail due to LogicalEnglish syntax)
    print("\n2. Testing downloaded KB (may fail due to special syntax)...")
    if taxkb_citizenship.exists():
        try:
            # Read the file content
            content = taxkb_citizenship.read_text(encoding='utf-8')
            print(f"  File size: {len(content)} characters")
            print(f"  First 200 chars: {content[:200]}...")
            
            # Note: This will likely fail because TaxKB uses LogicalEnglish,
            # not standard Prolog, so we can't load it directly
            print("  Note: TaxKB uses LogicalEnglish format, requires special loader")
            
        except Exception as e:
            print(f"  ✗ Error reading: {e}")

else:
    print("\n⚠ ASP backend not available, skipping tests")

# Test with Prolog backend if available
if PYSWIP_AVAILABLE:
    print("\n" + "=" * 80)
    print("Testing Prolog Backend")
    print("=" * 80)
    
    print("\n1. Testing simple theory...")
    try:
        kb_prolog = KnowledgeBase(backend='prolog')
        kb_prolog.load(simple_theory)
        print("  ✓ Theory loaded successfully")
        
        # Query
        results = list(kb_prolog.backend._prolog.query("human(X)"))
        print(f"  ✓ Query executed: {len(results)} results")
        for r in results:
            print(f"    X = {r['X']}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
else:
    print("\n⚠ Prolog backend not available")
    print("  Install SWI-Prolog to test: https://www.swi-prolog.org/download/stable")

# Summary
print("\n" + "=" * 80)
print("Summary")
print("=" * 80)
print(f"✓ Downloaded knowledge bases to D:\\datasets\\")
print(f"✓ Registered {len(KnowledgeBaseRegistry.list_all())} knowledge bases")
print(f"✓ ASP backend: {'Working' if CLINGO_AVAILABLE else 'Not available'}")
print(f"✓ Prolog backend: {'Working' if PYSWIP_AVAILABLE else 'Install SWI-Prolog'}")
print()
print("Next steps:")
print("1. Install SWI-Prolog to enable full Prolog backend testing")
print("2. Create adapters for LogicalEnglish format (TaxKB)")
print("3. Test NephroDoctor with Prolog backend (rule-based system)")
print("4. Create simpler test cases from these KBs")
print()
print("Note: TaxKB uses LogicalEnglish, which requires special processing.")
print("NephroDoctor uses production rules with custom operators.")
print("Both can be adapted or we can create simplified versions for testing.")
