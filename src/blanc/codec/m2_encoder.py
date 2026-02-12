"""
M2 Encoder: Semi-Formal Modality

Encodes rules and facts using logical operators with natural language predicates.
Paper Section 4.4 (M2: Semi-formal).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import Union
from blanc.core.theory import Rule, RuleType
from .nl_mapping import get_nl_mapping


def encode_m2(element: Union[str, Rule], nl_mapping=None, domain='biology') -> str:
    """
    Encode element in M2 (semi-formal) format.
    
    M2 format: Logical operators (∀, →, ⇒) with natural language predicates.
    
    Args:
        element: Rule or fact to encode
        nl_mapping: NL mapping instance
        domain: Domain for default NL mapping
    
    Returns:
        M2 encoded string
    
    Example:
        >>> rule = Rule(head="flies(X)", body=("bird(X)",),
        ...             rule_type=RuleType.DEFEASIBLE, label="r1")
        >>> encode_m2(rule)
        '∀X: is a bird(X) ⇒ can fly(X)'
    """
    
    # Get NL mapping
    if nl_mapping is None:
        nl_mapping = get_nl_mapping(domain)
    
    if isinstance(element, Rule):
        return encode_m2_rule(element, nl_mapping)
    else:
        return encode_m2_fact(element, nl_mapping)


def encode_m2_rule(rule: Rule, nl_mapping) -> str:
    """Encode rule in M2 format."""
    
    # Extract variables from rule
    variables = extract_variables(rule)
    
    # Encode body atoms with NL predicates
    body_encoded = []
    for atom in rule.body:
        pred = extract_predicate(atom)
        nl_pred = nl_mapping.to_nl(pred)
        # Replace predicate with NL version
        atom_nl = atom.replace(pred, nl_pred)
        body_encoded.append(atom_nl)
    
    # Encode head with NL predicate
    head_pred = extract_predicate(rule.head)
    head_nl = nl_mapping.to_nl(head_pred)
    head_encoded = rule.head.replace(head_pred, head_nl)
    
    # Combine with logical operators
    if len(variables) > 0:
        var_list = ', '.join(sorted(variables))
        quantifier = f"∀{var_list}: "
    else:
        quantifier = ""
    
    # Choose arrow based on rule type
    if rule.rule_type == RuleType.DEFEASIBLE:
        arrow = "⇒"  # Defeasible arrow
    else:
        arrow = "→"  # Strict arrow
    
    # Construct M2 encoding
    if len(body_encoded) == 1:
        body_str = body_encoded[0]
    else:
        body_str = " ∧ ".join(body_encoded)
    
    return f"{quantifier}{body_str} {arrow} {head_encoded}"


def encode_m2_fact(fact: str, nl_mapping) -> str:
    """Encode ground fact in M2 format."""
    
    pred = extract_predicate(fact)
    nl_pred = nl_mapping.to_nl(pred)
    
    # Replace predicate with NL version
    fact_nl = fact.replace(pred, nl_pred)
    
    return fact_nl


def extract_predicate(atom: str) -> str:
    """Extract predicate from atom."""
    if '(' in atom:
        return atom.split('(')[0]
    return atom


def extract_variables(rule: Rule) -> set:
    """Extract all variables from rule."""
    import re
    
    variables = set()
    
    # Find uppercase letters in head
    variables.update(re.findall(r'\b[A-Z][a-z]*\b', rule.head))
    
    # Find uppercase letters in body
    for atom in rule.body:
        variables.update(re.findall(r'\b[A-Z][a-z]*\b', atom))
    
    return variables


def encode_m2_theory(theory, domain='biology') -> str:
    """
    Encode entire theory in M2 format.
    
    Args:
        theory: Theory object
        domain: Domain for NL mapping
    
    Returns:
        M2 encoded theory as multi-line string
    """
    nl_mapping = get_nl_mapping(domain)
    
    lines = []
    
    # Encode facts
    for fact in theory.facts:
        lines.append(encode_m2(fact, nl_mapping, domain))
    
    # Encode rules
    for rule in theory.rules:
        lines.append(encode_m2(rule, nl_mapping, domain))
    
    return '\n'.join(lines)
