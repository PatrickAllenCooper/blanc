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


def create_legal_kb() -> Theory:
    """
    Create legal reasoning KB from expert sources.
    
    Uses:
    - LKIF Core: 201 legal rules covering:
      - Legal norms (obligations, permissions, prohibitions)
      - Legal actions (statutes, contracts, treaties)
      - Legal roles (jurisdictional hierarchies)
      - Legal documents (regulations, decrees)
    
    Total: 201 expert-curated inference rules
    
    Returns:
        Theory with legal knowledge
    """
    # LKIF Core is primary source
    theory = create_lkif_legal()
    
    # Future: Can add DAPRECO GDPR rules when parser is complete
    # dapreco_theory = create_dapreco_legal()
    # for rule in dapreco_theory.rules:
    #     theory.add_rule(rule)
    
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
