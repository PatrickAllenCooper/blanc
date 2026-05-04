"""
Legal Instance Facts

Legal entities and cases as instance facts.
Based on legal concepts from LKIF Core taxonomy.

These represent real legal entities that appear in legal reasoning.
Used to populate the legal KB with ground facts for instance generation.

Author: Anonymous Authors
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
    
    # Persons with legal capacity attributes
    persons = [
        'adult_citizen_1', 'adult_citizen_2', 'minor_1',
        'emancipated_minor_1', 'diplomat_1', 'sovereign_1',
    ]
    for p in persons:
        theory.add_fact(f"person({p})")

    theory.add_fact("adult(adult_citizen_1)")
    theory.add_fact("adult(adult_citizen_2)")
    theory.add_fact("adult_citizen(adult_citizen_1)")
    theory.add_fact("adult_citizen(adult_citizen_2)")
    theory.add_fact("minor(minor_1)")
    theory.add_fact("emancipated_minor(emancipated_minor_1)")
    theory.add_fact("diplomat(diplomat_1)")
    theory.add_fact("sovereign(sovereign_1)")

    # Legal entities
    entities = [
        'acme_corp', 'widget_llc', 'doe_trust',
    ]
    for e in entities:
        theory.add_fact(f"legal_person({e})")
        theory.add_fact(f"corporation({e})")

    theory.add_fact("trustee(doe_trust)")
    theory.add_fact("fiduciary(doe_trust)")

    # Criminal proceedings
    theory.add_fact("criminal_defendant(defendant)")
    theory.add_fact("criminal_charge(felony_1)")
    theory.add_fact("criminal_charge(misdemeanor_1)")
    theory.add_fact("criminal_offense(felony_1)")
    theory.add_fact("criminal_offense(misdemeanor_1)")

    # Employment entities
    theory.add_fact("employee(worker_1)")
    theory.add_fact("employee(worker_2)")
    theory.add_fact("employer(acme_corp)")
    theory.add_fact("non_exempt_employee(worker_1)")

    # Family law entities
    theory.add_fact("biological_parent(parent_1)")
    theory.add_fact("non_custodial_parent(parent_2)")
    theory.add_fact("legal_guardian(guardian_1)")

    return theory


def get_legal_counts():
    """Get counts of legal entities by type."""
    return {
        'statutes': 10,
        'contracts': 8,
        'treaties': 5,
        'legal_actions': 9,
        'legal_roles': 8,
        'persons': 6,
        'legal_entities': 3,
        'criminal_proceedings': 5,
        'employment': 4,
        'family': 3,
        'total': 61
    }
