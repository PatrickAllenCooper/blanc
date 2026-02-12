"""
Extract biological taxonomy and behavioral predicates from WordNet.

WordNet is an expert-curated lexical database from Princeton linguists.
Extract hypernym/hyponym chains for biological organisms and behavioral verbs.

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
from collections import defaultdict
import nltk
from nltk.corpus import wordnet as wn

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType


def extract_wordnet_biology():
    """Extract biological taxonomy and behavioral rules from WordNet."""
    
    print("=" * 70)
    print("Extracting Biology from WordNet")
    print("=" * 70)
    
    theory = Theory()
    rule_id = 0
    
    # Key biological synsets to explore
    bio_roots = [
        'organism.n.01',
        'animal.n.01',
        'bird.n.01',
        'mammal.n.01',
        'fish.n.02',
        'insect.n.01',
        'reptile.n.01',
        'amphibian.n.01',
    ]
    
    print("\nExtracting taxonomic hierarchy...")
    
    # Track synsets we've seen
    seen_synsets = set()
    synset_to_name = {}
    
    # Extract hypernym chains
    for root_name in bio_roots:
        try:
            root = wn.synset(root_name)
            
            # Get all hyponyms (specific types)
            hyponyms = list(root.closure(lambda s: s.hyponyms()))
            
            print(f"  {root.name()}: {len(hyponyms)} hyponyms")
            
            # Add hypernym rules: hyponym(X) -> hypernym(X)
            for hypo in hyponyms[:50]:  # Limit to avoid explosion
                if hypo in seen_synsets:
                    continue
                seen_synsets.add(hypo)
                
                # Get direct hypernyms
                for hyper in hypo.hypernyms():
                    # Create readable names
                    hypo_name = hypo.name().split('.')[0].replace('-', '_')
                    hyper_name = hyper.name().split('.')[0].replace('-', '_')
                    
                    synset_to_name[hypo] = hypo_name
                    synset_to_name[hyper] = hyper_name
                    
                    # Add rule: specific_type(X) -> general_type(X)
                    rule = Rule(
                        head=f"{hyper_name}(X)",
                        body=(f"{hypo_name}(X)",),
                        rule_type=RuleType.STRICT,
                        label=f"wn_r{rule_id}"
                    )
                    theory.add_rule(rule)
                    rule_id += 1
        
        except Exception as e:
            print(f"  [SKIP] {root_name}: {e}")
    
    print(f"\nExtracted {len(theory.rules)} taxonomic rules")
    
    # Extract behavioral verbs
    print("\nExtracting behavioral predicates...")
    
    behavioral_verbs = [
        'fly.v.01',      # travel through air
        'swim.v.01',     # travel through water
        'walk.v.01',     # locomotion
        'run.v.01',      # fast locomotion
        'hunt.v.01',     # predation
        'eat.v.01',      # feeding
        'migrate.v.02',  # seasonal movement
        'sing.v.01',     # vocalization
    ]
    
    verb_rules = []
    for verb_name in behavioral_verbs:
        try:
            verb = wn.synset(verb_name)
            verb_pred = verb.name().split('.')[0]
            verb_rules.append(verb_pred)
            print(f"  {verb_pred}: {verb.definition()}")
        except:
            pass
    
    print(f"\nExtracted {len(verb_rules)} behavioral predicates")
    
    return theory, synset_to_name, verb_rules


def main():
    """Main extraction pipeline."""
    
    print("Extracting WordNet biological knowledge...")
    
    theory, synset_names, behaviors = extract_wordnet_biology()
    
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"Taxonomic rules: {len(theory.rules)}")
    print(f"Unique synsets: {len(synset_names)}")
    print(f"Behavioral predicates: {len(behaviors)}")
    
    # Sample output
    print("\nSample rules:")
    for rule in list(theory.rules)[:20]:
        print(f"  {rule}")
    
    print("\nBehavioral predicates:")
    for behavior in behaviors:
        print(f"  {behavior}/1")
    
    # Save
    output_file = Path("examples/knowledge_bases/wordnet_biology_extracted.py")
    
    with open(output_file, 'w') as f:
        f.write('"""\n')
        f.write('WordNet Biology - Extracted Taxonomy\n')
        f.write('\n')
        f.write('Extracted from WordNet 3.0 (Princeton University experts).\n')
        f.write(f'Taxonomic rules: {len(theory.rules)}\n')
        f.write(f'Behavioral predicates: {len(behaviors)}\n')
        f.write('\n')
        f.write('Citation: Miller, G. A. (1995). WordNet: A lexical database for English.\n')
        f.write('\n')
        f.write('Author: Extracted by Patrick Cooper\n')
        f.write('Date: 2026-02-12\n')
        f.write('"""\n\n')
        f.write('from blanc.core.theory import Theory, Rule, RuleType\n\n\n')
        f.write('def create_wordnet_biology() -> Theory:\n')
        f.write('    """Create WordNet-extracted biology taxonomy."""\n')
        f.write('    theory = Theory()\n\n')
        
        # Write rules
        for rule in theory.rules:
            head = rule.head
            body = ', '.join(f'"{b}"' for b in rule.body)
            f.write(f'    theory.add_rule(Rule(\n')
            f.write(f'        head="{head}",\n')
            f.write(f'        body=({body},),\n')
            f.write(f'        rule_type=RuleType.STRICT,\n')
            f.write(f'        label="{rule.label}"\n')
            f.write(f'    ))\n')
        
        f.write('\n    return theory\n\n\n')
        
        # Add behavioral predicates as comment
        f.write('# Behavioral predicates extracted:\n')
        for behavior in behaviors:
            f.write(f'# - {behavior}/1\n')
    
    print(f"\nSaved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
