"""
Materials Science Knowledge Base - Expert-Curated from MatOnto

Expert-curated materials science ontology based on BFO (Basic Formal Ontology).
All rules extracted from MatOnto (MatPortal community).

Source:
- MatOnto (MatPortal community, Bryan Miller) - 1,190 materials rules, depth 10

Total: 1,190 inference rules from expert materials scientists

Citation:
- Bryan Miller (contact). MatOnto: Materials Science Ontology.
  MatPortal. https://matportal.org/ontologies/MATONTO

REQUIRES DOMAIN EXPERT VALIDATION (per paper Section 4.1)

Author: Extracted and organized by Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory
from .matonto_materials_extracted import create_matonto_materials
from .materials_instances import add_materials_instances
from .materials_behavioral_rules import add_materials_behavioral_rules, add_materials_superiority_relations


def create_materials_kb(include_instances=True) -> Theory:
    """
    Create materials science KB from expert sources.
    
    Uses:
    - MatOnto: 1,190 materials science rules (strict taxonomic)
    - Materials behavioral rules: defeasible defaults and defeaters
    
    NOTE: Requires domain expert validation per paper requirements.
    
    Returns:
        Theory with materials science knowledge
    """
    theory = create_matonto_materials()
    
    if include_instances:
        theory = add_materials_instances(theory)
    
    theory = add_materials_behavioral_rules(theory)
    add_materials_superiority_relations(theory)
    
    return theory


def get_materials_stats(theory=None):
    """Get statistics for materials KB."""
    if theory is None:
        theory = create_materials_kb()
    
    from blanc.generation.partition import compute_dependency_depths
    
    depths = compute_dependency_depths(theory)
    max_depth = max(depths.values()) if depths else 0
    
    return {
        'sources': ['MatOnto'],
        'rules': len(theory.rules),
        'facts': len(theory.facts),
        'max_depth': max_depth,
        'predicates': len(set(r.head.split('(')[0] for r in theory.rules)),
        'materials_concepts': ['alloy', 'crystal', 'polymer', 'elastic_modulus', 'band_gap'],
        'expert_validation_required': True,
        'expert_contact': 'Bryan Miller, bryan.miller@nist.gov',
    }
