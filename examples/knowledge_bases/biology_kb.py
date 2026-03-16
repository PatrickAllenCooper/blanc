"""
Biology Knowledge Base - Expert-Curated from Multiple Sources

Combines taxonomic hierarchy from YAGO 4.5 and WordNet 3.0.
All rules extracted from expert-populated knowledge bases.

Sources:
1. YAGO 4.5 (Télécom Paris, 2024) - 584 taxonomic rules, depth 7
2. WordNet 3.0 (Princeton, 1995+) - 334 taxonomic rules, 8 behavioral predicates

Total: 918 inference rules from expert sources

Citations:
- Suchanek et al. (2024). YAGO 4.5: A Large and Clean Knowledge Base
  with a Rich Taxonomy. SIGIR 2024.
- Miller, G. A. (1995). WordNet: A lexical database for English.
  CACM 38(11): 39-41.

Author: Extracted and organized by Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory
from .yago_biology_extracted import create_yago_biology
from .wordnet_biology_extracted import create_wordnet_biology
from .biology_instances import add_biology_instances
from .biology_behavioral_rules import add_behavioral_rules, add_bio_superiority_relations


def create_biology_kb(include_instances=True) -> Theory:
    """
    Create unified biology KB from expert sources.
    
    Combines:
    - YAGO 4.5: 584 taxonomic rules (strict)
    - WordNet 3.0: 334 taxonomic rules (strict)
    - Behavioral defaults: defeasible rules and defeaters
    
    Returns:
        Theory with combined biology knowledge
    """
    # Start with YAGO (primary source)
    theory = create_yago_biology()
    
    # Add WordNet taxonomy
    wordnet_theory = create_wordnet_biology()
    for rule in wordnet_theory.rules:
        theory.add_rule(rule)
    
    # Add organism instances
    if include_instances:
        theory = add_biology_instances(theory)
    
    # Add defeasible behavioral rules and superiority relations
    theory = add_behavioral_rules(theory)
    add_bio_superiority_relations(theory)
    
    return theory


def get_biology_stats(theory=None):
    """Get statistics for biology KB."""
    if theory is None:
        theory = create_biology_kb()
    
    from blanc.generation.partition import compute_dependency_depths
    
    depths = compute_dependency_depths(theory)
    max_depth = max(depths.values()) if depths else 0
    
    return {
        'sources': ['YAGO 4.5', 'WordNet 3.0'],
        'rules': len(theory.rules),
        'facts': len(theory.facts),
        'max_depth': max_depth,
        'predicates': len(set(r.head.split('(')[0] for r in theory.rules)),
        'behavioral_predicates': ['fly', 'swim', 'walk', 'run', 'hunt', 'eat', 'migrate', 'sing'],
    }


# For backward compatibility with existing scripts
create_biology_base = create_biology_kb
