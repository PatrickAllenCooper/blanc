"""
Extract biology-related inference rules from YAGO.

Extracts:
1. Taxonomic hierarchy (subClassOf chains) for biology
2. Property relationships  
3. Instance-class memberships

Builds derivation chains from YAGO's expert-curated ontology.

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
from collections import defaultdict
import re

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType


def parse_turtle_triple(line):
    """Parse a simple Turtle triple."""
    line = line.strip()
    if not line or line.startswith('@') or line.startswith('#'):
        return None
    
    # Simple parser for subject predicate object .
    parts = line.rstrip(' .').split(None, 2)
    if len(parts) < 3:
        return None
    
    subject, predicate, obj = parts
    obj = obj.rstrip(' ;.,')
    
    return subject, predicate, obj


def extract_bio_classes_and_rules(yago_file):
    """Extract biology-related classes and rules from YAGO."""
    
    print("=" * 70)
    print("Extracting Biology Rules from YAGO")
    print("=" * 70)
    
    # Collections
    classes = {}  # class_uri -> label
    subclass_of = defaultdict(set)  # subclass -> {superclasses}
    instances = defaultdict(set)  # instance -> {classes}
    properties = defaultdict(set)  # (subject, property) -> {objects}
    
    print(f"\nParsing: {yago_file}")
    print("This may take a few minutes...")
    
    line_count = 0
    bio_keywords = [
        'taxon', 'organism', 'species', 'animal', 'plant', 'bird',
        'mammal', 'fish', 'insect', 'reptile', 'amphibian',
        'biological', 'living', 'life', 'fauna', 'flora'
    ]
    
    with open(yago_file, 'r', encoding='utf-8') as f:
        current_subject = None
        
        for line in f:
            line_count += 1
            if line_count % 1000000 == 0:
                print(f"  Processed {line_count // 1000000}M lines...")
            
            line = line.strip()
            if not line or line.startswith('@'):
                continue
            
            # Handle multi-line triples (subject followed by properties)
            if line.endswith(';') or line.endswith(','):
                # Continuation - parse property
                parts = line.rstrip(' ;,').split(None, 1)
                if len(parts) >= 2 and current_subject:
                    predicate, obj = parts
                    obj = obj.rstrip(' ;,.')
                    
                    # Store relevant predicates
                    if 'rdfs:subClassOf' in predicate:
                        subclass_of[current_subject].add(obj)
                    elif 'rdf:type' in predicate and 'rdfs:Class' in obj:
                        classes[current_subject] = current_subject
                    elif 'rdfs:label' in predicate:
                        # Extract label
                        label_match = re.search(r'"([^"]+)"', obj)
                        if label_match and current_subject:
                            classes[current_subject] = label_match.group(1)
                
                continue
            
            # Full triple
            parts = line.rstrip(' .').split(None, 2)
            if len(parts) < 3:
                continue
            
            subject, predicate, obj = parts
            current_subject = subject
            obj = obj.rstrip(' ;,.')
            
            # Extract relevant triples
            if 'rdfs:subClassOf' in predicate:
                subclass_of[subject].add(obj)
                classes[subject] = subject
                classes[obj] = obj
            
            elif 'rdf:type' in predicate:
                if 'rdfs:Class' in obj:
                    classes[subject] = subject
                else:
                    instances[subject].add(obj)
            
            elif 'rdfs:label' in predicate:
                label_match = re.search(r'"([^"]+)"', obj)
                if label_match:
                    classes[subject] = label_match.group(1)
    
    print(f"\nParsed {line_count} lines")
    print(f"Found {len(classes)} classes")
    print(f"Found {len(subclass_of)} subclass relationships")
    print(f"Found {len(instances)} instances")
    
    # Filter for biology-related
    print("\nFiltering for biology-related content...")
    
    bio_classes = {}
    for class_uri, label in classes.items():
        label_lower = str(label).lower()
        if any(keyword in label_lower for keyword in bio_keywords):
            bio_classes[class_uri] = label
    
    print(f"Biology classes: {len(bio_classes)}")
    
    # Build rules
    print("\nBuilding inference rules...")
    theory = Theory()
    
    # Counter for unique IDs
    rule_id = 0
    
    # Add subclass rules: subclass(X) -> superclass(X)
    for subclass, superclasses in subclass_of.items():
        if subclass in bio_classes:
            for superclass in superclasses:
                if superclass in bio_classes:
                    # Create readable predicates
                    sub_name = simplify_name(bio_classes.get(subclass, subclass))
                    super_name = simplify_name(bio_classes.get(superclass, superclass))
                    
                    if sub_name and super_name and sub_name != super_name:
                        rule = Rule(
                            head=f"{super_name}(X)",
                            body=(f"{sub_name}(X)",),
                            rule_type=RuleType.STRICT,
                            label=f"r{rule_id}"
                        )
                        theory.add_rule(rule)
                        rule_id += 1
    
    print(f"Added {len(theory.rules)} rules")
    
    return theory, bio_classes


def simplify_name(uri_or_label):
    """Convert URI or label to simple predicate name."""
    name = str(uri_or_label)
    
    # Extract from URI
    if '#' in name:
        name = name.split('#')[-1]
    elif '/' in name:
        name = name.split('/')[-1]
    
    # Extract from label (remove quotes, language tags)
    name = re.sub(r'"([^"]+)".*', r'\1', name)
    
    # Clean up
    name = name.lower()
    name = re.sub(r'[^a-z0-9_]', '_', name)
    name = re.sub(r'_+', '_', name)
    name = name.strip('_')
    
    # Limit length
    if len(name) > 50:
        name = name[:50]
    
    return name if name else None


def main():
    """Main extraction pipeline."""
    
    yago_file = Path("data/yago/yago-4.5.0.2-tiny/yago-tiny.ttl")
    
    if not yago_file.exists():
        print(f"ERROR: YAGO file not found: {yago_file}")
        print("Run download_yago.py first")
        return 1
    
    # Extract rules
    theory, bio_classes = extract_bio_classes_and_rules(yago_file)
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Biology classes: {len(bio_classes)}")
    print(f"Inference rules: {len(theory.rules)}")
    
    # Sample of classes
    print("\nSample biology classes:")
    for i, (uri, label) in enumerate(list(bio_classes.items())[:20]):
        print(f"  {simplify_name(label)}: {label}")
    
    # Sample of rules
    print("\nSample inference rules:")
    for rule in list(theory.rules)[:20]:
        print(f"  {rule}")
    
    # Save theory
    output_file = Path("examples/knowledge_bases/yago_biology_extracted.py")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('YAGO Biology Knowledge Base - Extracted Rules\n')
        f.write('\n')
        f.write('Extracted from YAGO 4.5 expert-curated ontology.\n')
        f.write(f'Source: {yago_file}\n')
        f.write(f'Classes: {len(bio_classes)}\n')
        f.write(f'Rules: {len(theory.rules)}\n')
        f.write('\n')
        f.write('Author: Extracted by Patrick Cooper\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory, Rule, RuleType\n\n\n')
        f.write('def create_yago_biology() -> Theory:\n')
        f.write('    """Create YAGO-extracted biology KB."""\n')
        f.write('    theory = Theory()\n\n')
        
        # Write rules with proper formatting
        for rule in theory.rules:
            head = rule.head
            body = ', '.join(f'"{b}"' for b in rule.body)
            rule_type = 'RuleType.STRICT' if rule.rule_type == RuleType.STRICT else 'RuleType.DEFEASIBLE'
            label = rule.label
            
            f.write(f'    theory.add_rule(Rule(\n')
            f.write(f'        head="{head}",\n')
            f.write(f'        body=({body},),\n')
            f.write(f'        rule_type={rule_type},\n')
            f.write(f'        label="{label}"\n')
            f.write(f'    ))\n')
        
        f.write('\n    return theory\n')
    
    print(f"\nSaved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
