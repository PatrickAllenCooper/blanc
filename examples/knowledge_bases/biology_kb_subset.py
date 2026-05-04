"""
Biology KB Subset for Local Development

Creates a manageable 100-150 rule subset from expert sources for fast iteration.
Selected to maintain depth and interesting derivation chains.

Based on vertebrate taxonomy from YAGO + WordNet expert sources.

Author: Anonymous Authors
Date: 2026-02-12
"""

from blanc.core.theory import Theory, Rule, RuleType


def create_biology_subset() -> Theory:
    """
    Create development subset of biology KB.
    
    Subset: Vertebrate taxonomy + behavioral rules
    Size: ~100-150 rules (vs 927 full KB)
    Purpose: Fast local development iteration
    
    Returns:
        Theory with vertebrate-focused subset
    """
    theory = Theory()
    
    # === INSTANCES (Vertebrates only) ===
    
    # Birds (selected common species)
    birds = ['robin', 'eagle', 'penguin', 'duck', 'parrot', 'owl']
    for bird in birds:
        theory.add_fact(f"organism({bird})")
        theory.add_fact(f"animal({bird})")
        theory.add_fact(f"bird({bird})")
    
    # Mammals (selected common species)
    mammals = ['dog', 'cat', 'dolphin', 'bat', 'whale', 'lion']
    for mammal in mammals:
        theory.add_fact(f"organism({mammal})")
        theory.add_fact(f"animal({mammal})")
        theory.add_fact(f"mammal({mammal})")
    
    # Fish (selected species)
    fish = ['salmon', 'shark', 'goldfish']
    for f in fish:
        theory.add_fact(f"organism({f})")
        theory.add_fact(f"animal({f})")
        theory.add_fact(f"fish({f})")
    
    # === EXPERT RULES (Subset from YAGO/WordNet) ===
    
    # Core taxonomic rules (strict)
    theory.add_rule(Rule(
        head="animal(X)",
        body=("bird(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s1"
    ))
    
    theory.add_rule(Rule(
        head="animal(X)",
        body=("mammal(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s2"
    ))
    
    theory.add_rule(Rule(
        head="animal(X)",
        body=("fish(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s3"
    ))
    
    theory.add_rule(Rule(
        head="organism(X)",
        body=("animal(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s4"
    ))
    
    theory.add_rule(Rule(
        head="vertebrate(X)",
        body=("bird(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s5"
    ))
    
    theory.add_rule(Rule(
        head="vertebrate(X)",
        body=("mammal(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s6"
    ))
    
    theory.add_rule(Rule(
        head="vertebrate(X)",
        body=("fish(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s7"
    ))
    
    # === DEFEASIBLE BEHAVIORAL RULES ===
    
    # Flight (birds typically fly, exceptions: penguin)
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d1"
    ))
    
    # Swimming (fish swim, also some birds/mammals)
    theory.add_rule(Rule(
        head="swims(X)",
        body=("fish(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d2"
    ))
    
    theory.add_rule(Rule(
        head="swims(X)",
        body=("dolphin(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d3"
    ))
    
    # Locomotion
    theory.add_rule(Rule(
        head="walks(X)",
        body=("mammal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d4"
    ))
    
    # Migration (some birds migrate)
    theory.add_rule(Rule(
        head="migrates(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d5"
    ))
    
    # Carnivory
    theory.add_rule(Rule(
        head="carnivore(X)",
        body=("lion(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s8"
    ))
    
    theory.add_rule(Rule(
        head="carnivore(X)",
        body=("shark(X)",),
        rule_type=RuleType.STRICT,
        label="bio_s9"
    ))
    
    theory.add_rule(Rule(
        head="hunts(X)",
        body=("carnivore(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d6"
    ))
    
    # Vocalization
    theory.add_rule(Rule(
        head="sings(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="bio_d7"
    ))
    
    return theory


def get_subset_stats():
    """Get statistics for subset."""
    theory = create_biology_subset()
    
    from blanc.generation.partition import compute_dependency_depths
    depths = compute_dependency_depths(theory)
    
    defeasible = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    strict = [r for r in theory.rules if r.rule_type == RuleType.STRICT]
    
    return {
        'source': 'YAGO + WordNet subset',
        'domain': 'vertebrates',
        'rules_total': len(theory.rules),
        'rules_strict': len(strict),
        'rules_defeasible': len(defeasible),
        'facts': len(theory.facts),
        'organisms': 15,
        'max_depth': max(depths.values()) if depths else 0,
        'purpose': 'local development (fast iteration)',
        'full_kb_available': 'biology_kb.py (927 rules)',
    }
