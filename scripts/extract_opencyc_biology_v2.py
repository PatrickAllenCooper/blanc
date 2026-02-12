"""
Extract biological knowledge from OpenCyc OWL file.

OpenCyc is the paper-cited source for biology KB (Section 4.1).
Extract BiologicalOrganism hierarchy and biological properties.

Source: OpenCyc 2012 (Cycorp expert ontologists)
Citation: Lenat, D. B. (1995). CYC: A Large-Scale Investment in Knowledge Infrastructure

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
import gzip
from collections import defaultdict
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType


def extract_opencyc_biology():
    """Extract biology from OpenCyc OWL."""
    
    print("=" * 70)
    print("Extracting Biology from OpenCyc")
    print("=" * 70)
    
    opencyc_file = Path("data/opencyc/opencyc-2012-05-10-readable.owl.gz")
    
    if not opencyc_file.exists():
        print(f"ERROR: OpenCyc file not found: {opencyc_file}")
        return None, {}
    
    print(f"\nParsing: {opencyc_file}")
    print("Size: 27 MB compressed")
    print("This will take several minutes...\n")
    
    # Parse compressed OWL
    theory = Theory()
    bio_classes = set()
    subclass_map = defaultdict(set)
    
    # Biology-related keywords
    bio_keywords = [
        'BiologicalOrganism', 'Animal', 'Plant', 'Organism',
        'Bird', 'Mammal', 'Fish', 'Insect', 'Reptile', 'Amphibian',
        'Species', 'Genus', 'Family', 'Order', 'Class', 'Phylum',
        'anatomy', 'physiology', 'behavior', 'morphology'
    ]
    
    line_count = 0
    
    try:
        with gzip.open(opencyc_file, 'rt', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line_count += 1
                if line_count % 100000 == 0:
                    print(f"  Processed {line_count // 1000}K lines...")
                
                # Look for rdfs:subClassOf relationships
                if 'rdfs:subClassOf' in line or 'SubClassOf' in line:
                    # Extract class URIs
                    uris = re.findall(r'#([A-Za-z0-9_-]+)', line)
                    if len(uris) >= 2:
                        # First is subclass, rest are superclasses
                        subclass = uris[0]
                        for superclass in uris[1:]:
                            if any(kw in subclass for kw in bio_keywords) or \
                               any(kw in superclass for kw in bio_keywords):
                                bio_classes.add(subclass)
                                bio_classes.add(superclass)
                                subclass_map[subclass].add(superclass)
                
                # Look for Class definitions
                elif 'owl:Class' in line:
                    uris = re.findall(r'#([A-Za-z0-9_-]+)', line)
                    for uri in uris:
                        if any(kw in uri for kw in bio_keywords):
                            bio_classes.add(uri)
        
        print(f"\nParsed {line_count} lines")
        print(f"Found {len(bio_classes)} biology classes")
        print(f"Found {len(subclass_map)} subclass relationships")
        
    except Exception as e:
        print(f"ERROR parsing file: {e}")
        return None, {}
    
    # Build rules
    print("\nBuilding inference rules...")
    rule_id = 0
    
    for subclass, superclasses in subclass_map.items():
        for superclass in superclasses:
            # Convert to predicate names
            sub_pred = to_predicate(subclass)
            super_pred = to_predicate(superclass)
            
            if sub_pred and super_pred and sub_pred != super_pred:
                rule = Rule(
                    head=f"{super_pred}(X)",
                    body=(f"{sub_pred}(X)",),
                    rule_type=RuleType.STRICT,
                    label=f"cyc_r{rule_id}"
                )
                theory.add_rule(rule)
                rule_id += 1
    
    print(f"Added {len(theory.rules)} rules")
    
    return theory, bio_classes


def to_predicate(class_uri):
    """Convert OpenCyc class URI to predicate name."""
    # Remove prefixes
    name = class_uri.replace('BiologicalOrganism', 'organism')
    
    # Convert CamelCase to snake_case
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
    name = name.lower()
    
    # Clean up
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    
    # Limit length
    if len(name) > 40:
        name = name[:40]
    
    return name if name else None


def main():
    """Main extraction."""
    
    theory, classes = extract_opencyc_biology()
    
    if theory is None:
        return 1
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Biology classes: {len(classes)}")
    print(f"Inference rules: {len(theory.rules)}")
    
    # Sample
    print("\nSample biology classes:")
    for cls in list(classes)[:20]:
        print(f"  {to_predicate(cls)}: {cls}")
    
    print("\nSample rules:")
    for rule in list(theory.rules)[:20]:
        print(f"  {rule}")
    
    # Save
    output_file = Path("examples/knowledge_bases/opencyc_biology_extracted.py")
    
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('OpenCyc Biology - Extracted Rules\n')
        f.write('\n')
        f.write('Extracted from OpenCyc 2012 (Cycorp expert ontologists).\n')
        f.write('Paper-cited source (Section 4.1).\n')
        f.write('\n')
        f.write(f'Classes: {len(classes)}\n')
        f.write(f'Rules: {len(theory.rules)}\n')
        f.write('\n')
        f.write('Citation: Lenat, D. B. (1995). CYC: A Large-Scale Investment\n')
        f.write('          in Knowledge Infrastructure. CACM 38(11).\n')
        f.write('\n')
        f.write('Author: Extracted by Patrick Cooper\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory, Rule, RuleType\n\n\n')
        f.write('def create_opencyc_biology() -> Theory:\n')
        f.write('    """Create OpenCyc-extracted biology KB."""\n')
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
