"""
Extract organism instances from YAGO entities.

Parse the YAGO entities JSONL file to extract biological organism instances
and add them as facts to the biology KB.

Source: yago-entities.jsonl (678 MB, 49M entities)
Focus: Biological organisms for instance generation

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory


def extract_organism_instances(max_organisms=100):
    """
    Extract organism instances from YAGO entities.
    
    Args:
        max_organisms: Maximum number of organisms to extract
    
    Returns:
        List of organism facts
    """
    
    print("=" * 70)
    print("Extracting Organism Instances from YAGO")
    print("=" * 70)
    
    entities_file = Path("data/yago/yago-entities.jsonl/yago-entities.jsonl")
    
    if not entities_file.exists():
        print(f"ERROR: YAGO entities file not found: {entities_file}")
        return []
    
    print(f"\nParsing: {entities_file}")
    print(f"Size: 678 MB (49M entities)")
    print(f"Target: {max_organisms} biological organisms\n")
    
    organisms = []
    bio_classes = [
        'Animal', 'Bird', 'Mammal', 'Fish', 'Insect', 'Reptile', 'Amphibian',
        'Plant', 'Organism', 'Species', 'Taxon'
    ]
    
    line_count = 0
    
    print("Parsing (this may take a few minutes)...")
    
    try:
        with open(entities_file, 'r', encoding='utf-8') as f:
            for line in f:
                line_count += 1
                
                if line_count % 1000000 == 0:
                    print(f"  Processed {line_count // 1000000}M entities, found {len(organisms)} organisms...")
                
                if len(organisms) >= max_organisms:
                    break
                
                try:
                    entity = json.loads(line)
                    
                    # Check if biological organism
                    entity_types = entity.get('type', [])
                    if not isinstance(entity_types, list):
                        entity_types = [entity_types]
                    
                    # Look for bio classes in types
                    is_bio = any(any(bio_class in str(t) for bio_class in bio_classes) 
                                for t in entity_types)
                    
                    if is_bio:
                        entity_id = entity.get('id', '')
                        entity_label = entity.get('label', {}).get('en', '')
                        
                        if entity_id:
                            # Simplify ID to organism name
                            name = entity_id.replace('http://yago-knowledge.org/resource/', '')
                            name = name.replace('_', ' ').strip()
                            
                            # Get primary type
                            primary_type = None
                            for t in entity_types:
                                t_str = str(t)
                                for bio_class in bio_classes:
                                    if bio_class in t_str:
                                        primary_type = bio_class.lower()
                                        break
                                if primary_type:
                                    break
                            
                            if primary_type and len(name) > 2 and len(name) < 50:
                                organisms.append({
                                    'name': name,
                                    'label': entity_label,
                                    'type': primary_type,
                                    'id': entity_id
                                })
                
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    continue
    
    except Exception as e:
        print(f"ERROR: {e}")
        return []
    
    print(f"\nProcessed {line_count} entities")
    print(f"Found {len(organisms)} biological organisms")
    
    return organisms


def main():
    """Main extraction."""
    
    # Extract organisms
    organisms = extract_organism_instances(max_organisms=200)
    
    if not organisms:
        print("No organisms extracted")
        return 1
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Total organisms: {len(organisms)}")
    
    # Group by type
    by_type = defaultdict(list)
    for org in organisms:
        by_type[org['type']].append(org)
    
    print("\nOrganisms by type:")
    for org_type, orgs in sorted(by_type.items()):
        print(f"  {org_type}: {len(orgs)} organisms")
    
    print("\nSample organisms:")
    for org in organisms[:30]:
        print(f"  {org['name']}: {org['type']} ({org['label'][:50] if org['label'] else 'no label'})")
    
    # Save as Python facts
    output_file = Path("examples/knowledge_bases/yago_organisms.py")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('YAGO Organism Instances\n')
        f.write('\n')
        f.write(f'Extracted from YAGO 4.5 entities (49M entities).\n')
        f.write(f'Total organisms: {len(organisms)}\n')
        f.write('\n')
        f.write('Source: yago-entities.jsonl\n')
        f.write('Citation: Suchanek et al. (2024), YAGO 4.5, SIGIR 2024\n')
        f.write('\n')
        f.write('Author: Extracted by Patrick Cooper\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory\n\n\n')
        f.write('def add_organism_facts(theory: Theory) -> Theory:\n')
        f.write('    """Add organism instance facts to theory."""\n')
        f.write('    \n')
        
        # Group organisms by type
        for org_type, orgs in sorted(by_type.items()):
            f.write(f'    # {org_type.capitalize()} instances ({len(orgs)})\n')
            for org in orgs[:50]:  # Limit per type
                # Create safe predicate name
                name = org['name'].lower().replace(' ', '_').replace('-', '_')
                name = ''.join(c for c in name if c.isalnum() or c == '_')
                if name and name[0].isalpha():
                    f.write(f'    theory.add_fact("organism({name})")\n')
                    f.write(f'    theory.add_fact("{org_type}({name})")\n')
            f.write('\n')
        
        f.write('    return theory\n\n\n')
        f.write('# Organism data for reference\n')
        f.write(f'ORGANISMS = {organisms!r}\n')
    
    print(f"\nSaved to: {output_file}")
    print(f"Usage: from yago_organisms import add_organism_facts")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
