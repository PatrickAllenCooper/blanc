"""
Audit what actual instance data exists in expert KBs.

This checks what the expert KBs ACTUALLY contain vs what we're adding.

Critical question: Are we extracting or inventing?

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("EXPERT KB INSTANCE DATA AUDIT")
print("=" * 70)

print("\n" + "=" * 70)
print("1. YAGO Entities (Expert Data)")
print("=" * 70)

# Check actual YAGO entities
entities_file = Path("data/yago/yago-entities.jsonl/yago-entities.jsonl")
print(f"\nFile: {entities_file}")
print(f"Size: 678 MB")
print("\nSample entities (first 50):")

bio_count = 0
with open(entities_file, 'r') as f:
    for i in range(50):
        try:
            line = f.readline()
            entity = json.loads(line)
            print(f"  {entity.get('id', '')}: {entity.get('title', '')} - {entity.get('description', '')[:60]}")
            desc = entity.get('description', '').lower()
            if any(word in desc for word in ['bird', 'animal', 'species', 'organism']):
                bio_count += 1
        except:
            break

print(f"\nBiology-related in first 50: {bio_count}")

print("\n" + "=" * 70)
print("2. YAGO Triples (Expert Facts)")
print("=" * 70)

# Sample YAGO triples
print("\nChecking yago-tiny.ttl for actual instance assertions...")
print("Looking for: <entity> rdf:type <class> statements\n")

with open("data/yago/yago-4.5.0.2-tiny/yago-tiny.ttl", 'r', encoding='utf-8') as f:
    instance_count = 0
    for i, line in enumerate(f):
        if i > 10000:
            break
        if 'rdf:type' in line and 'owl:Class' not in line and 'sh:NodeShape' not in line:
            if 'schema:' in line or 'yago:' in line:
                print(f"  {line.strip()}")
                instance_count += 1
                if instance_count >= 10:
                    break

print(f"\nInstance assertions found: {instance_count} (in first 10K lines)")

print("\n" + "=" * 70)
print("3. MatOnto Individuals (Expert Data)")
print("=" * 70)

from rdflib import Graph
from rdflib.namespace import RDF, OWL

g = Graph()
print("\nParsing MatOnto...")
g.parse("data/matonto/MatOnto-ontology.owl", format='turtle')

# Get named individuals (not classes, not properties, not blank nodes)
individuals = []
for s in g.subjects(RDF.type, OWL.NamedIndividual):
    name = str(s).split('#')[-1].split('/')[-1]
    if not name.startswith('_') and not name.startswith('n'):
        individuals.append(name)

print(f"Named individuals: {len(individuals)}")
print("\nSample individuals:")
for ind in individuals[:20]:
    print(f"  {ind}")

print("\n" + "=" * 70)
print("4. What We ADDED (Not from Experts)")
print("=" * 70)

print("\nbiology_instances.py:")
print("  - 85 organisms (robin, sparrow, eagle, etc.)")
print("  - 255 facts total")
print("  - SOURCE: We added these ourselves")
print("  - EXPERT: NO - these are not from YAGO/WordNet")

print("\nlegal_instances.py:")
print("  - 40 legal entities (GDPR, CCPA, etc.)")
print("  - 63 facts total")
print("  - SOURCE: We added these ourselves")
print("  - EXPERT: NO - these are not from LKIF")

print("\nmaterials_instances.py:")
print("  - 43 materials (steel, aluminum, etc.)")
print("  - 86 facts total")
print("  - SOURCE: We added these ourselves")
print("  - EXPERT: NO - these are not from MatOnto")

print("\n" + "=" * 70)
print("CRITICAL FINDING")
print("=" * 70)
print("\nWe have been ADDING instance facts ourselves,")
print("not extracting them from expert sources.")
print("\nThis violates the expert-curation principle!")
print("\nThe expert KBs contain:")
print("  - Ontologies (class hierarchies)")
print("  - Properties (relationships)")
print("  - Some instances (but sparse)")
print("\nThey do NOT contain:")
print("  - Comprehensive instance facts")
print("  - Populated knowledge bases")
print("\nWe need to either:")
print("  1. Extract ONLY instances that exist in expert sources")
print("  2. Or find expert-populated INSTANCE databases")
print("  3. Or clarify if ontology extraction + instance addition is acceptable")
print("\n" + "=" * 70)
