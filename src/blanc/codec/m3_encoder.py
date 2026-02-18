"""
M3 Encoder: Annotated Formal Modality

Encodes rules and facts in formal syntax with natural language comments.
Paper Section 4.4 (M3: Annotated formal).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import Optional, Union
from blanc.core.theory import Rule, RuleType
from blanc.utils.predicates import extract_constant, extract_predicate
from .encoder import PureFormalEncoder
from .nl_mapping import get_nl_mapping


def encode_m3(element: Union[str, Rule], nl_mapping=None, domain='biology') -> str:
    """
    Encode element in M3 (annotated formal) format.
    
    M3 format: Formal syntax with natural language comments explaining meaning.
    
    Args:
        element: Rule or fact to encode
        nl_mapping: NL mapping instance (or None to get from domain)
        domain: Domain for default NL mapping
    
    Returns:
        M3 encoded string with annotation
    
    Example:
        >>> rule = Rule(head="flies(X)", body=("bird(X)",), 
        ...             rule_type=RuleType.DEFEASIBLE, label="r1")
        >>> encode_m3(rule)
        'r1: bird(X) => flies(X)  # Birds typically can fly'
    """
    
    # Get NL mapping
    if nl_mapping is None:
        nl_mapping = get_nl_mapping(domain)
    
    # Get formal encoding (for M3, use arrow notation not Prolog)
    if isinstance(element, Rule):
        formal = encode_rule_arrow_notation(element)
    else:
        # For facts, just use the fact itself
        formal = element
    
    # Generate natural language comment
    comment = generate_comment(element, nl_mapping)
    
    # Combine: formal syntax + comment
    # Remove any trailing periods before adding comment
    formal = formal.rstrip('.')
    return f"{formal}  # {comment}"


def generate_comment(element: Union[str, Rule], nl_mapping) -> str:
    """
    Generate natural language comment for element.
    
    Args:
        element: Rule or fact
        nl_mapping: NL mapping instance
    
    Returns:
        Natural language explanation
    """
    
    if isinstance(element, Rule):
        # Generate comment for rule
        return generate_rule_comment(element, nl_mapping)
    else:
        # Generate comment for fact
        return generate_fact_comment(element, nl_mapping)


def generate_rule_comment(rule: Rule, nl_mapping) -> str:
    """Generate comment for rule."""
    
    # Extract predicate from head
    head_pred = extract_predicate(rule.head)
    head_nl = nl_mapping.to_nl(head_pred)
    
    # Extract predicates from body
    body_preds = [extract_predicate(atom) for atom in rule.body]
    body_nl = [nl_mapping.to_nl(pred) for pred in body_preds]
    
    # Construct comment based on rule type
    if rule.rule_type == RuleType.DEFEASIBLE:
        # Defeasible: "If X, then typically Y"
        if len(body_nl) == 1:
            comment = f"If {body_nl[0]}, then typically {head_nl}"
        else:
            body_str = " and ".join(body_nl)
            comment = f"If {body_str}, then typically {head_nl}"
    else:
        # Strict: "If X, then Y"
        if len(body_nl) == 1:
            comment = f"If {body_nl[0]}, then {head_nl}"
        else:
            body_str = " and ".join(body_nl)
            comment = f"If {body_str}, then {head_nl}"
    
    return comment


def generate_fact_comment(fact: str, nl_mapping) -> str:
    """Generate comment for fact."""
    
    # Extract predicate and constant
    predicate = extract_predicate(fact)
    constant = extract_constant(fact)
    
    # Get NL for predicate
    pred_nl = nl_mapping.to_nl(predicate)
    
    # Construct comment: "{constant} {pred_nl}"
    comment = f"{constant} {pred_nl}"
    
    return comment




def encode_rule_arrow_notation(rule: Rule) -> str:
    """
    Encode rule using arrow notation (not Prolog syntax).
    
    For M3 annotated formal, use mathematical arrow notation:
    - Strict: bird(X) -> animal(X)
    - Defeasible: bird(X) => flies(X)
    """
    # Build body
    if len(rule.body) == 1:
        body_str = rule.body[0]
    else:
        body_str = ", ".join(rule.body)
    
    # Choose arrow based on rule type
    if rule.rule_type == RuleType.DEFEASIBLE:
        arrow = "=>"
    elif rule.rule_type == RuleType.DEFEATER:
        arrow = "~>"
    else:
        arrow = "->"
    
    # Add label if present
    if rule.label:
        return f"{rule.label}: {body_str} {arrow} {rule.head}"
    else:
        return f"{body_str} {arrow} {rule.head}"


def encode_m3_theory(theory, domain='biology') -> str:
    """
    Encode entire theory in M3 format.
    
    Args:
        theory: Theory object
        domain: Domain for NL mapping
    
    Returns:
        M3 encoded theory as multi-line string
    """
    nl_mapping = get_nl_mapping(domain)
    
    lines = []
    
    # Encode facts
    for fact in theory.facts:
        lines.append(encode_m3(fact, nl_mapping, domain))
    
    # Encode rules
    for rule in theory.rules:
        lines.append(encode_m3(rule, nl_mapping, domain))
    
    return '\n'.join(lines)
