"""
Legal Knowledge Base - Expert-Curated from LKIF Core

Expert-curated legal ontology covering legal norms, actions, roles, and documents.
All rules extracted from LKIF Core (University of Amsterdam, ESTRELLA project).

Source:
- LKIF Core (University of Amsterdam) - 201 legal rules, depth 7

Total: 201 inference rules from expert legal scholars

Citation:
- Hoekstra, R., Boer, A., van den Berg, K.
  LKIF Core: Legal Knowledge Interchange Format.
  University of Amsterdam.

Author: Extracted and organized by Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory
from .lkif_legal_extracted import create_lkif_legal
from .legal_instances import add_legal_instances
from .legal_behavioral_rules import add_legal_behavioral_rules, add_legal_superiority_relations


def create_legal_kb(include_instances=True) -> Theory:
    """
    Create legal reasoning KB from expert sources.
    
    Uses:
    - LKIF Core: 201 legal rules (strict taxonomic)
    - Legal behavioral rules: defeasible defaults and defeaters
    
    Returns:
        Theory with legal knowledge
    """
    theory = create_lkif_legal()
    
    if include_instances:
        theory = add_legal_instances(theory)
    
    theory = add_legal_behavioral_rules(theory)
    add_legal_superiority_relations(theory)
    
    return theory


def get_legal_stats(theory=None):
    """Get statistics for legal KB."""
    if theory is None:
        theory = create_legal_kb()
    
    from blanc.generation.partition import compute_dependency_depths
    
    depths = compute_dependency_depths(theory)
    max_depth = max(depths.values()) if depths else 0
    
    return {
        'sources': ['LKIF Core'],
        'rules': len(theory.rules),
        'facts': len(theory.facts),
        'max_depth': max_depth,
        'predicates': len(set(r.head.split('(')[0] for r in theory.rules)),
        'legal_concepts': ['statute', 'contract', 'treaty', 'regulation', 'obligation', 'permission'],
    }
