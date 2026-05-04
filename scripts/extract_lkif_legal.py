"""
Extract legal rules from LKIF Core ontology.

LKIF Core is an expert-curated legal ontology from University of Amsterdam.
Extract legal norms, actions, and role hierarchies.

Source: LKIF Core (U Amsterdam, ESTRELLA project)
Citation: Hoekstra, Boer, van den Berg
License: Open source

Author: Anonymous Authors
Date: 2026-02-12
"""

import sys
from pathlib import Path
from collections import defaultdict
import re
try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF, RDFS, OWL
except ImportError:
    print("ERROR: rdflib not installed. Run: pip install rdflib")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType


def extract_lkif_legal():
    """Extract legal rules from LKIF Core OWL files."""
    
    print("=" * 70)
    print("Extracting Legal Rules from LKIF Core")
    print("=" * 70)
    
    lkif_dir = Path("data/lkif-core")
    
    # Key LKIF modules for legal reasoning
    owl_files = [
        "norm.owl",           # Legal norms (obligations, permissions)
        "legal-action.owl",   # Legal actions
        "legal-role.owl",     # Legal roles
        "expression.owl",     # Legal expressions
        "action.owl",         # General actions
    ]
    
    theory = Theory()
    all_classes = set()
    subclass_map = defaultdict(set)
    rule_id = 0
    
    print(f"\nParsing {len(owl_files)} OWL modules...\n")
    
    for owl_file in owl_files:
        filepath = lkif_dir / owl_file
        
        if not filepath.exists():
            print(f"[SKIP] {owl_file} - not found")
            continue
        
        print(f"[PARSE] {owl_file}")
        
        try:
            g = Graph()
            g.parse(filepath, format='xml')
            
            # Extract subclass relationships
            for s, p, o in g.triples((None, RDFS.subClassOf, None)):
                subj = str(s).split('#')[-1].split('/')[-1]
                obj = str(o).split('#')[-1].split('/')[-1]
                
                if subj and obj and subj != obj:
                    all_classes.add(subj)
                    all_classes.add(obj)
                    subclass_map[subj].add(obj)
            
            # Extract class declarations
            for s, p, o in g.triples((None, RDF.type, OWL.Class)):
                cls = str(s).split('#')[-1].split('/')[-1]
                if cls:
                    all_classes.add(cls)
            
            print(f"  Found {len([s for s, p, o in g.triples((None, RDFS.subClassOf, None))])} subclass relations")
            
        except Exception as e:
            print(f"  [ERROR] Failed to parse: {e}")
    
    print(f"\nTotal classes: {len(all_classes)}")
    print(f"Total subclass relationships: {len(subclass_map)}")
    
    # Build rules
    print("\nBuilding inference rules...")
    
    for subclass, superclasses in subclass_map.items():
        for superclass in superclasses:
            sub_pred = to_predicate(subclass)
            super_pred = to_predicate(superclass)
            
            if sub_pred and super_pred and sub_pred != super_pred:
                rule = Rule(
                    head=f"{super_pred}(X)",
                    body=(f"{sub_pred}(X)",),
                    rule_type=RuleType.STRICT,
                    label=f"lkif_r{rule_id}"
                )
                theory.add_rule(rule)
                rule_id += 1
    
    print(f"Added {len(theory.rules)} rules")
    
    return theory, all_classes


def to_predicate(class_name):
    """Convert LKIF class name to predicate."""
    # Convert CamelCase to snake_case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', class_name)
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
    
    theory, classes = extract_lkif_legal()
    
    if theory is None:
        return 1
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Legal classes: {len(classes)}")
    print(f"Inference rules: {len(theory.rules)}")
    
    # Sample
    print("\nSample legal classes:")
    for cls in sorted(list(classes))[:20]:
        print(f"  {to_predicate(cls)}: {cls}")
    
    print("\nSample rules:")
    for rule in list(theory.rules)[:20]:
        print(f"  {rule}")
    
    # Save
    output_file = Path("examples/knowledge_bases/lkif_legal_extracted.py")
    
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('LKIF Core Legal KB - Extracted Rules\n')
        f.write('\n')
        f.write('Extracted from LKIF Core ontology (University of Amsterdam).\n')
        f.write('Expert-curated legal ontology from ESTRELLA project.\n')
        f.write('\n')
        f.write(f'Classes: {len(classes)}\n')
        f.write(f'Rules: {len(theory.rules)}\n')
        f.write('\n')
        f.write('Citation: Hoekstra, R., Boer, A., van den Berg, K.\n')
        f.write('          LKIF Core ontology.\n')
        f.write('\n')
        f.write('Author: Extracted by Anonymous Authors\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory, Rule, RuleType\n\n\n')
        f.write('def create_lkif_legal() -> Theory:\n')
        f.write('    """Create LKIF-extracted legal KB."""\n')
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
