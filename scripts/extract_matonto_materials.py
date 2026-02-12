"""
Extract materials science rules from MatOnto ontology.

MatOnto is an expert-curated materials science ontology based on BFO.
Extract material class hierarchy and property relationships.

Source: MatPortal (materials science community)
Citation: matportal.org/ontologies/MATONTO
License: Open

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
from collections import defaultdict
import re
try:
    from rdflib import Graph
    from rdflib.namespace import RDF, RDFS, OWL
except ImportError:
    print("ERROR: rdflib not installed. Run: pip install rdflib")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType


def extract_matonto_materials():
    """Extract materials science rules from MatOnto."""
    
    print("=" * 70)
    print("Extracting Materials Science from MatOnto")
    print("=" * 70)
    
    matonto_file = Path("data/matonto/MatOnto-ontology.owl")
    
    if not matonto_file.exists():
        print(f"ERROR: MatOnto file not found: {matonto_file}")
        return None, {}
    
    print(f"\nParsing: {matonto_file}")
    print("Size: 1.3 MB")
    print("Expected: 848 classes, 96 properties, depth 10\n")
    
    theory = Theory()
    all_classes = set()
    subclass_map = defaultdict(set)
    properties = set()
    
    try:
        print("Loading OWL file (Turtle format)...")
        g = Graph()
        g.parse(matonto_file, format='turtle')
        
        print(f"Loaded {len(g)} triples")
        
        # Extract subclass relationships
        print("\nExtracting class hierarchy...")
        for s, p, o in g.triples((None, RDFS.subClassOf, None)):
            subj = str(s).split('#')[-1].split('/')[-1]
            obj = str(o).split('#')[-1].split('/')[-1]
            
            if subj and obj and subj != obj and not subj.startswith('_') and not obj.startswith('_'):
                all_classes.add(subj)
                all_classes.add(obj)
                subclass_map[subj].add(obj)
        
        # Extract properties
        print("Extracting properties...")
        for s, p, o in g.triples((None, RDF.type, OWL.ObjectProperty)):
            prop = str(s).split('#')[-1].split('/')[-1]
            if prop:
                properties.add(prop)
        
        for s, p, o in g.triples((None, RDF.type, OWL.DatatypeProperty)):
            prop = str(s).split('#')[-1].split('/')[-1]
            if prop:
                properties.add(prop)
        
        print(f"Found {len(all_classes)} classes")
        print(f"Found {len(subclass_map)} subclass relationships")
        print(f"Found {len(properties)} properties")
        
    except Exception as e:
        print(f"ERROR parsing file: {e}")
        return None, {}
    
    # Build rules
    print("\nBuilding inference rules...")
    rule_id = 0
    
    for subclass, superclasses in subclass_map.items():
        for superclass in superclasses:
            sub_pred = to_predicate(subclass)
            super_pred = to_predicate(superclass)
            
            if sub_pred and super_pred and sub_pred != super_pred:
                rule = Rule(
                    head=f"{super_pred}(X)",
                    body=(f"{sub_pred}(X)",),
                    rule_type=RuleType.STRICT,
                    label=f"mat_r{rule_id}"
                )
                theory.add_rule(rule)
                rule_id += 1
    
    print(f"Added {len(theory.rules)} rules")
    
    return theory, all_classes, properties


def to_predicate(class_name):
    """Convert MatOnto class name to predicate."""
    # Handle BFO prefixes
    name = class_name.replace('BFO_', '').replace('MATONTO_', '')
    
    # Convert to snake_case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    name = name.lower()
    
    # Clean up
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    
    if len(name) > 40:
        name = name[:40]
    
    return name if name else None


def main():
    """Main extraction."""
    
    result = extract_matonto_materials()
    
    if result[0] is None:
        return 1
    
    theory, classes, properties = result
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Materials classes: {len(classes)}")
    print(f"Properties: {len(properties)}")
    print(f"Inference rules: {len(theory.rules)}")
    
    # Sample
    print("\nSample materials classes:")
    for cls in sorted(list(classes))[:30]:
        pred = to_predicate(cls)
        print(f"  {pred}: {cls}")
    
    print("\nSample properties:")
    for prop in sorted(list(properties))[:20]:
        print(f"  {to_predicate(prop)}")
    
    print("\nSample rules:")
    for rule in list(theory.rules)[:20]:
        print(f"  {rule}")
    
    # Save
    output_file = Path("examples/knowledge_bases/matonto_materials_extracted.py")
    
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('MatOnto Materials Science KB - Extracted Rules\n')
        f.write('\n')
        f.write('Extracted from MatOnto ontology (MatPortal community).\n')
        f.write('Expert-curated materials science ontology based on BFO.\n')
        f.write('\n')
        f.write(f'Classes: {len(classes)}\n')
        f.write(f'Properties: {len(properties)}\n')
        f.write(f'Rules: {len(theory.rules)}\n')
        f.write('\n')
        f.write('Source: matportal.org/ontologies/MATONTO\n')
        f.write('Contact: Bryan Miller\n')
        f.write('\n')
        f.write('Author: Extracted by Patrick Cooper\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory, Rule, RuleType\n\n\n')
        f.write('def create_matonto_materials() -> Theory:\n')
        f.write('    """Create MatOnto-extracted materials KB."""\n')
        f.write('    theory = Theory()\n\n')
        
        for rule in theory.rules:
            head = rule.head
            body = ', '.join(f'"{b}"' for b in rule.body)
            f.write(f'    theory.add_rule(Rule(\n')
            f.write(f'        head="{head}",\n')
            f.write(f'        body=({body},),\n')
            f.write(f'        rule_type=RuleType.STRICT,\n')
            f.write(f'        label="{rule.label}"\n')
            f.write(f'    ))\n')
        
        f.write('\n    return theory\n')
    
    print(f"\nSaved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
