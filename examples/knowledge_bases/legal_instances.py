"""
Legal Instance Facts

Legal entities and cases as instance facts.
Based on legal concepts from LKIF Core taxonomy.

These represent real legal entities that appear in legal reasoning.
Used to populate the legal KB with ground facts for instance generation.

Author: Patrick Cooper
Date: 2026-02-12
"""

from blanc.core.theory import Theory


def add_legal_instances(theory: Theory) -> Theory:
    """
    Add legal entity instances to theory.
    
    Entities match LKIF Core legal taxonomy.
    Real legal concepts used in jurisprudence.
    """
    
    # Statutes and regulations
    statutes = [
        'gdpr', 'ccpa', 'hipaa', 'ferpa', 'coppa',
        'ada', 'civil_rights_act', 'voting_rights_act',
        'clean_air_act', 'clean_water_act'
    ]
    
    for statute in statutes:
        theory.add_fact(f"legal_document({statute})")
        theory.add_fact(f"statute({statute})")
    
    # Contracts
    contracts = [
        'employment_contract', 'sales_contract', 'lease_agreement',
        'nda', 'partnership_agreement', 'licensing_agreement',
        'service_agreement', 'purchase_order'
    ]
    
    for contract in contracts:
        theory.add_fact(f"legal_document({contract})")
        theory.add_fact(f"contract({contract})")
    
    # Treaties
    treaties = [
        'geneva_convention', 'paris_agreement', 'treaty_of_rome',
        'kyoto_protocol', 'nuclear_non_proliferation_treaty'
    ]
    
    for treaty in treaties:
        theory.add_fact(f"legal_document({treaty})")
        theory.add_fact(f"treaty({treaty})")
    
    # Legal actions
    actions = [
        'filing', 'motion', 'appeal', 'judgment', 'ruling',
        'injunction', 'subpoena', 'warrant', 'summons'
    ]
    
    for action in actions:
        theory.add_fact(f"legal_action({action})")
    
    # Legal roles
    roles = [
        'plaintiff', 'defendant', 'judge', 'prosecutor',
        'attorney', 'witness', 'jury', 'magistrate'
    ]
    
    for role in roles:
        theory.add_fact(f"legal_role({role})")
    
    return theory


def get_legal_counts():
    """Get counts of legal entities by type."""
    return {
        'statutes': 10,
        'contracts': 8,
        'treaties': 5,
        'legal_actions': 9,
        'legal_roles': 8,
        'total': 40
    }
