"""
M3 Encoder: Annotated Formal Modality

Encodes rules and facts in formal syntax with natural language comments.
Paper Section 4.4 (M3: Annotated formal).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import Union
from blanc.core.theory import Rule, RuleType
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
    
    # Get formal encoding (M4)
    m4_encoder = PureFormalEncoder()
    if isinstance(element, Rule):
        formal = m4_encoder.encode_rule(element)
    else:
        formal = m4_encoder.encode_fact(element)
    
    # Remove trailing period for cleaner annotation
    formal = formal.rstrip('.')
    
    # Generate natural language comment
    comment = generate_comment(element, nl_mapping)
    
    # Combine: formal syntax + comment
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


def extract_predicate(atom: str) -> str:
    """Extract predicate from atom."""
    # atom format: "predicate(args)"
    if '(' in atom:
        return atom.split('(')[0]
    return atom


def extract_constant(fact: str) -> str:
    """Extract constant from ground fact."""
    # fact format: "predicate(constant)"
    if '(' in fact and ')' in fact:
        start = fact.index('(') + 1
        end = fact.index(')')
        return fact[start:end]
    return ""


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
