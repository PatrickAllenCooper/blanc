"""
Register all downloaded knowledge bases in BLANC registry.

Registers:
- Downloaded KBs: TaxKB, NephroDoctor, OpenCyc, WordNet, SUMO, ProofWriter, ConceptNet, Freebase
- Example KBs: Tweety, Medical, Family, IDP Discovery, Nephrology, Citizenship
"""

import sys
from pathlib import Path

# Set UTF-8 encoding
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blanc.knowledge_bases import register_kb, KnowledgeBaseRegistry

print("=" * 80)
print("BLANC Knowledge Base Registration")
print("=" * 80)

datasets_root = Path("D:/datasets")

# Count before
initial_count = len(KnowledgeBaseRegistry.list_all())
print(f"\nInitial registered KBs: {initial_count}")

print("\nRegistering downloaded knowledge bases...")

# 1. OpenCyc (Common Sense)
opencyc_path = datasets_root / "opencyc-kb"
if opencyc_path.exists():
    register_kb(
        name="opencyc_2012",
        domain="common-sense",
        format="owl",
        path=opencyc_path / "opencyc-2012-05-10-readable.owl.gz",
        description="OpenCyc 4.0 (2012) - Open source common sense knowledge base",
        size_estimate=300000,  # ~300K concepts
        source_url="https://github.com/therohk/opencyc-kb",
        citation="Cycorp, Inc. OpenCyc 4.0 (2012)",
        difficulty="hard",
        tags=["common-sense", "cyc", "ontology", "owl", "historical"],
        license="OpenCyc"
    )
    print(f"  ✓ OpenCyc 2012")

# 2. WordNet (Lexical Database)
wordnet_path = datasets_root / "prolog"
if wordnet_path.exists():
    register_kb(
        name="wordnet_prolog",
        domain="lexical",
        format="prolog",
        path=wordnet_path,
        description="WordNet 3.0 Prolog Database - Lexical relations (synonyms, hypernyms, etc.)",
        size_estimate=117000,  # ~117K synsets
        source_url="https://wordnet.princeton.edu/",
        citation="WordNet 3.0 (Princeton University, 2006)",
        difficulty="medium",
        tags=["lexical", "wordnet", "nlp", "synonyms", "semantic"],
        license="WordNet License"
    )
    print(f"  ✓ WordNet 3.0 Prolog")

# 3. SUMO (Suggested Upper Merged Ontology)
sumo_path = datasets_root / "sumo"
if sumo_path.exists():
    register_kb(
        name="sumo",
        domain="upper-ontology",
        format="kif",
        path=sumo_path / "Merge.kif",
        description="SUMO Upper Ontology - 25K terms, 80K axioms across all domains",
        size_estimate=80000,
        source_url="https://github.com/ontologyportal/sumo",
        citation="IEEE Standard Upper Ontology (SUMO)",
        difficulty="hard",
        tags=["ontology", "upper-ontology", "ieee", "formal", "kif"],
        license="GNU GPL (domain ontologies)"
    )
    print(f"  ✓ SUMO Upper Ontology")
    
    # Register specific domain ontologies
    for domain_file in ["Medicine.kif", "Law.kif", "Government.kif", "Economy.kif"]:
        domain_path = sumo_path / domain_file
        if domain_path.exists():
            domain_name = domain_file.replace(".kif", "").lower()
            register_kb(
                name=f"sumo_{domain_name}",
                domain=domain_name,
                format="kif",
                path=domain_path,
                description=f"SUMO {domain_file.replace('.kif', '')} Domain Ontology",
                size_estimate=5000,
                source_url="https://github.com/ontologyportal/sumo",
                difficulty="hard",
                tags=["ontology", "sumo", domain_name, "kif"],
                license="GNU GPL"
            )
            print(f"  ✓ SUMO {domain_file}")

# 4. ProofWriter (Logical Reasoning Benchmark)
proofwriter_path = datasets_root / "proofwriter" / "proofwriter-dataset-V2020.12.3"
if proofwriter_path.exists():
    # Register main dataset
    register_kb(
        name="proofwriter",
        domain="reasoning-benchmark",
        format="jsonl",
        path=proofwriter_path,
        description="ProofWriter: 500K logical reasoning problems with proofs (depth 0-5)",
        size_estimate=500000,
        source_url="https://allenai.org/data/proofwriter",
        citation="Tafjord et al., ProofWriter (ACL 2021)",
        difficulty="varied",
        tags=["benchmark", "reasoning", "deductive", "abductive", "proofs"],
        license="CC BY 4.0"
    )
    print(f"  ✓ ProofWriter")
    
    # Register specific subsets
    for depth in [0, 1, 2, 3, 5]:
        depth_path = proofwriter_path / "OWA" / f"depth-{depth}"
        if depth_path.exists():
            register_kb(
                name=f"proofwriter_owa_d{depth}",
                domain="reasoning-benchmark",
                format="jsonl",
                path=depth_path / "meta-test.jsonl",
                description=f"ProofWriter OWA Depth-{depth} (proof depth up to {depth} steps)",
                size_estimate=10000,
                source_url="https://allenai.org/data/proofwriter",
                difficulty="easy" if depth <= 1 else ("medium" if depth <= 3 else "hard"),
                tags=["benchmark", "reasoning", f"depth-{depth}", "owa"],
                license="CC BY 4.0"
            )
    print(f"  ✓ ProofWriter subsets (depth 0-5)")

# 5. ConceptNet5 (Common Sense)
conceptnet_path = datasets_root / "conceptnet5"
if conceptnet_path.exists():
    register_kb(
        name="conceptnet5",
        domain="common-sense",
        format="custom",
        path=conceptnet_path,
        description="ConceptNet5 - Semantic network for common sense knowledge",
        size_estimate=21000000,  # ~21M edges
        source_url="https://github.com/commonsense/conceptnet5",
        citation="ConceptNet5 (commonsense computing)",
        difficulty="hard",
        tags=["common-sense", "semantic-network", "conceptnet", "nlp"],
        license="Creative Commons Attribution-ShareAlike 4.0"
    )
    print(f"  ✓ ConceptNet5")

# 6. Freebase-Setup
freebase_path = datasets_root / "Freebase-Setup"
if freebase_path.exists():
    register_kb(
        name="freebase",
        domain="general-knowledge",
        format="rdf",
        path=freebase_path,
        description="Freebase knowledge base setup and documentation",
        size_estimate=1900000000,  # 1.9B triples
        source_url="https://github.com/dki-lab/Freebase-Setup",
        citation="Freebase (Google, archived 2015)",
        difficulty="hard",
        tags=["knowledge-graph", "freebase", "rdf", "historical"],
        license="CC-BY"
    )
    print(f"  ✓ Freebase")

# 7. KnowLogic Benchmark
knowlogic_path = datasets_root / "KnowLogic"
if knowlogic_path.exists():
    register_kb(
        name="knowlogic",
        domain="reasoning-benchmark",
        format="json",
        path=knowlogic_path,
        description="KnowLogic: 3K bilingual reasoning questions with adjustable difficulty",
        size_estimate=3000,
        source_url="https://github.com/pokerwf/KnowLogic",
        citation="Wang et al., KnowLogic (2025)",
        difficulty="varied",
        tags=["benchmark", "reasoning", "bilingual", "knowledge-driven"],
        license="MIT"
    )
    print(f"  ✓ KnowLogic")

# Final count
final_count = len(KnowledgeBaseRegistry.list_all())
print(f"\nTotal registered KBs: {final_count} (added {final_count - initial_count})")

# Categorize by domain
print("\n" + "=" * 80)
print("Knowledge Bases by Domain")
print("=" * 80)

domains = {}
for kb in KnowledgeBaseRegistry.list_all():
    if kb.domain not in domains:
        domains[kb.domain] = []
    domains[kb.domain].append(kb)

for domain, kbs in sorted(domains.items()):
    print(f"\n{domain.upper()} ({len(kbs)} KBs):")
    for kb in kbs:
        print(f"  - {kb.name}: {kb.description[:60]}...")

# Summary statistics
print("\n" + "=" * 80)
print("Summary Statistics")
print("=" * 80)

total_size = sum(kb.size_estimate or 0 for kb in KnowledgeBaseRegistry.list_all())
print(f"Total KBs: {final_count}")
print(f"Estimated total facts/rules: {total_size:,}")
print(f"Unique domains: {len(domains)}")

format_counts = {}
for kb in KnowledgeBaseRegistry.list_all():
    format_counts[kb.format] = format_counts.get(kb.format, 0) + 1

print(f"Formats: {dict(format_counts)}")

print(f"\nLargest KBs by size estimate:")
largest = sorted(KnowledgeBaseRegistry.list_all(), 
                 key=lambda kb: kb.size_estimate or 0, reverse=True)[:5]
for kb in largest:
    print(f"  - {kb.name}: {kb.size_estimate:,} items")

print("\n" + "=" * 80)
print("Registration Complete!")
print("=" * 80)
