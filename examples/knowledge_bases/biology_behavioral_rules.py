"""
Biology Behavioral Rules - Defeasible Defaults

Behavioral rules derived from biological knowledge in expert sources.
These represent defeasible defaults (typical behaviors with exceptions).

Based on WordNet behavioral predicates and biological knowledge.

Author: Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory, Rule, RuleType


def add_behavioral_rules(theory: Theory) -> Theory:
    """
    Add defeasible behavioral rules to biology KB.
    
    These rules represent biological defaults that admit exceptions.
    Based on behavioral predicates from WordNet expert source.
    """
    
    rule_id = 1000  # Start after extracted rules
    
    # Bird behaviors (defeasible - penguins, ostriches are exceptions)
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Aquatic behaviors
    theory.add_rule(Rule(
        head="swims(X)",
        body=("fish(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    theory.add_rule(Rule(
        head="swims(X)",
        body=("amphibian(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Insect behaviors
    theory.add_rule(Rule(
        head="flies(X)",
        body=("insect(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Locomotion
    theory.add_rule(Rule(
        head="walks(X)",
        body=("mammal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    theory.add_rule(Rule(
        head="runs(X)",
        body=("mammal(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Migration (not all birds migrate)
    theory.add_rule(Rule(
        head="migrates(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Predation
    theory.add_rule(Rule(
        head="hunts(X)",
        body=("mammal(X)", "carnivore(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    # Vocalization
    theory.add_rule(Rule(
        head="sings(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label=f"bio_r{rule_id}"
    ))
    rule_id += 1
    
    return theory
