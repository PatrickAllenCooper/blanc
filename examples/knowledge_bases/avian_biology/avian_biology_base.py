"""
Avian Biology Knowledge Base

Domain: Bird classification and behavior
Purpose: MVP for DeFAb benchmark generation
Author: Anonymous Authors

This KB demonstrates:
- Strict rules (taxonomic facts)
- Defeasible rules (behavioral defaults)
- Defeaters (exceptions to defaults)
- All 3 levels of abductive reasoning
"""

from blanc.core.theory import Theory, Rule, RuleType


def create_avian_biology_base() -> Theory:
    """
    Create base Avian Biology theory (D^-).
    
    This is the incomplete theory used for instance generation.
    Defeaters are in create_avian_biology_full().
    
    Returns:
        Theory with facts, strict rules, and defeasible rules (no defeaters)
    """
    theory = Theory()
    
    # =========================================================================
    # FACTS - Ground observations (depth 0)
    # =========================================================================
    
    # Bird individuals
    theory.add_fact("bird(tweety)")
    theory.add_fact("bird(polly)")
    theory.add_fact("bird(opus)")
    theory.add_fact("bird(chirpy)")
    theory.add_fact("bird(donald)")
    theory.add_fact("bird(daffy)")
    
    # Species classifications
    theory.add_fact("sparrow(tweety)")
    theory.add_fact("parrot(polly)")
    theory.add_fact("penguin(opus)")
    theory.add_fact("canary(chirpy)")
    theory.add_fact("duck(donald)")
    theory.add_fact("duck(daffy)")
    
    # Physical properties
    theory.add_fact("small(tweety)")
    theory.add_fact("small(chirpy)")
    theory.add_fact("large(opus)")
    theory.add_fact("large(donald)")
    
    # Environmental conditions
    theory.add_fact("aquatic_environment(opus)")
    theory.add_fact("aquatic_environment(donald)")
    theory.add_fact("aquatic_environment(daffy)")
    
    # Injuries (for defeater testing)
    theory.add_fact("wing_injury(chirpy)")
    
    # =========================================================================
    # STRICT RULES - Taxonomic facts (always true, depth 1)
    # =========================================================================
    
    # Taxonomy inheritance (species implies bird)
    theory.add_rule(Rule(
        head="bird(X)",
        body=("sparrow(X)",),
        rule_type=RuleType.STRICT,
        label="s1",
        metadata={"description": "Sparrows are birds"}
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("parrot(X)",),
        rule_type=RuleType.STRICT,
        label="s2",
        metadata={"description": "Parrots are birds"}
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("penguin(X)",),
        rule_type=RuleType.STRICT,
        label="s3",
        metadata={"description": "Penguins are birds"}
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("canary(X)",),
        rule_type=RuleType.STRICT,
        label="s4",
        metadata={"description": "Canaries are birds"}
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("duck(X)",),
        rule_type=RuleType.STRICT,
        label="s5",
        metadata={"description": "Ducks are birds"}
    ))
    
    # Size inheritance
    theory.add_rule(Rule(
        head="small(X)",
        body=("sparrow(X)",),
        rule_type=RuleType.STRICT,
        label="s6",
        metadata={"description": "Sparrows are small"}
    ))
    
    theory.add_rule(Rule(
        head="small(X)",
        body=("canary(X)",),
        rule_type=RuleType.STRICT,
        label="s7",
        metadata={"description": "Canaries are small"}
    ))
    
    # =========================================================================
    # DEFEASIBLE RULES - Behavioral defaults (depth 2)
    # =========================================================================
    
    # r1: Birds typically fly
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
        metadata={"description": "Birds typically fly"}
    ))
    
    # r2: Flying birds typically migrate
    theory.add_rule(Rule(
        head="migrates(X)",
        body=("bird(X)", "flies(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r2",
        metadata={"description": "Flying birds typically migrate"}
    ))
    
    # r3: Small birds typically sing
    theory.add_rule(Rule(
        head="sings(X)",
        body=("bird(X)", "small(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r3",
        metadata={"description": "Small birds typically sing"}
    ))
    
    # r4: Aquatic birds typically swim
    theory.add_rule(Rule(
        head="swims(X)",
        body=("bird(X)", "aquatic_environment(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r4",
        metadata={"description": "Aquatic birds typically swim"}
    ))
    
    # r5: Large birds are typically predators
    theory.add_rule(Rule(
        head="predator(X)",
        body=("bird(X)", "large(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r5",
        metadata={"description": "Large birds are typically predators"}
    ))
    
    return theory


def create_avian_biology_full() -> Theory:
    """
    Create complete Avian Biology theory (D^full).
    
    Includes defeaters that will be ablated for Level 3 instances.
    
    Returns:
        Theory with all rules including defeaters and superiority relations
    """
    # Start with base theory
    theory = create_avian_biology_base()
    
    # =========================================================================
    # DEFEATERS - Exceptions to defaults
    # =========================================================================
    
    # d1: Penguins don't fly (flightless birds)
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d1",
        metadata={"description": "Penguins are flightless"}
    ))
    theory.add_superiority("d1", "r1")
    
    # d2: Injured birds may not fly
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("wing_injury(X)",),
        rule_type=RuleType.DEFEATER,
        label="d2",
        metadata={"description": "Wing injury prevents flight"}
    ))
    theory.add_superiority("d2", "r1")
    
    # d3: Ducks don't migrate (resident waterfowl)
    theory.add_rule(Rule(
        head="~migrates(X)",
        body=("duck(X)",),
        rule_type=RuleType.DEFEATER,
        label="d3",
        metadata={"description": "Ducks are non-migratory"}
    ))
    theory.add_superiority("d3", "r2")
    
    # d4: Parrots are not predators (despite some being large)
    # Note: polly is a parrot but not large, so this won't affect polly
    # This defeater is for potential large parrots
    theory.add_rule(Rule(
        head="~predator(X)",
        body=("parrot(X)",),
        rule_type=RuleType.DEFEATER,
        label="d4",
        metadata={"description": "Parrots are herbivores"}
    ))
    theory.add_superiority("d4", "r5")
    
    return theory
