"""
M1 Encoder: Narrative Modality

Encodes rules and facts in full natural language with linguistic hedging.
Paper Section 4.4 (M1: Narrative - hardest modality).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import Union
from blanc.core.theory import Rule, RuleType
from .nl_mapping import get_nl_mapping


def encode_m1(element: Union[str, Rule], nl_mapping=None, domain='biology') -> str:
    """
    Encode element in M1 (narrative) format.
    
    M1 format: Full natural language with implicit quantification and
    linguistic hedging for defeasibility.
    
    Args:
        element: Rule or fact to encode
        nl_mapping: NL mapping instance
        domain: Domain for default NL mapping
    
    Returns:
        M1 encoded string (natural language)
    
    Example:
        >>> rule = Rule(head="flies(X)", body=("bird(X)",),
        ...             rule_type=RuleType.DEFEASIBLE, label="r1")
        >>> encode_m1(rule)
        'Birds typically can fly.'
    """
    
    # Get NL mapping
    if nl_mapping is None:
        nl_mapping = get_nl_mapping(domain)
    
    if isinstance(element, Rule):
        return encode_m1_rule(element, nl_mapping)
    else:
        return encode_m1_fact(element, nl_mapping)


def encode_m1_rule(rule: Rule, nl_mapping) -> str:
    """Encode rule in narrative format."""
    
    # Extract predicates
    head_pred = extract_predicate(rule.head)
    body_preds = [extract_predicate(atom) for atom in rule.body]
    
    # Get NL versions
    head_nl = nl_mapping.to_nl(head_pred)
    body_nl = [nl_mapping.to_nl(pred) for pred in body_preds]
    
    # Pluralize predicates for general statements
    head_plural = pluralize_predicate(head_nl)
    body_plural = [pluralize_predicate(nl) for nl in body_nl]
    
    # Build narrative based on rule type
    if rule.rule_type == RuleType.DEFEASIBLE:
        # Defeasible: Use hedging ("typically", "usually", "generally")
        if len(body_plural) == 1:
            narrative = f"{capitalize(body_plural[0])} typically {head_nl}."
        else:
            body_str = " and ".join(body_plural)
            narrative = f"Things that {body_str} typically {head_nl}."
    else:
        # Strict: No hedging
        if len(body_plural) == 1:
            narrative = f"{capitalize(body_plural[0])} {head_nl}."
        else:
            body_str = " and ".join(body_plural)
            narrative = f"Things that {body_str} {head_nl}."
    
    return narrative


def encode_m1_fact(fact: str, nl_mapping) -> str:
    """Encode ground fact in narrative format."""
    
    # Extract predicate and constant
    predicate = extract_predicate(fact)
    constant = extract_constant(fact)
    
    # Get NL for predicate
    pred_nl = nl_mapping.to_nl(predicate)
    
    # Capitalize constant name
    constant_cap = capitalize(constant)
    
    # Construct narrative
    narrative = f"{constant_cap} {pred_nl}."
    
    return narrative


def extract_predicate(atom: str) -> str:
    """Extract predicate from atom."""
    if '(' in atom:
        return atom.split('(')[0]
    return atom


def extract_constant(fact: str) -> str:
    """Extract constant from ground fact."""
    if '(' in fact and ')' in fact:
        start = fact.index('(') + 1
        end = fact.index(')')
        return fact[start:end]
    return ""


def capitalize(text: str) -> str:
    """Capitalize first letter."""
    if not text:
        return text
    return text[0].upper() + text[1:]


def pluralize_predicate(predicate_nl: str) -> str:
    """
    Pluralize NL predicate for general statements.
    
    Examples:
        "is a bird" -> "are birds"
        "can fly" -> "can fly" (already works for plural)
    """
    
    # Handle "is a X" -> "are Xs"
    if predicate_nl.startswith("is a "):
        noun = predicate_nl[5:]  # Remove "is a "
        # Simple pluralization (would need proper NLP for production)
        if noun.endswith('s'):
            plural = noun + "es"
        else:
            plural = noun + "s"
        return f"are {plural}"
    
    # Handle "is an X" -> "are Xs"
    if predicate_nl.startswith("is an "):
        noun = predicate_nl[6:]  # Remove "is an "
        if noun.endswith('s'):
            plural = noun + "es"
        else:
            plural = noun + "s"
        return f"are {plural}"
    
    # Handle "can X" -> "can X" (already general)
    if predicate_nl.startswith("can "):
        return predicate_nl
    
    # Handle "has X" -> "have X"
    if predicate_nl.startswith("has "):
        return "have " + predicate_nl[4:]
    
    # Default: return as-is
    return predicate_nl


def encode_m1_theory(theory, domain='biology') -> str:
    """
    Encode entire theory in M1 (narrative) format.
    
    Args:
        theory: Theory object
        domain: Domain for NL mapping
    
    Returns:
        M1 encoded theory as natural language text
    """
    nl_mapping = get_nl_mapping(domain)
    
    lines = []
    
    # Encode facts
    for fact in theory.facts:
        lines.append(encode_m1(fact, nl_mapping, domain))
    
    # Encode rules
    for rule in theory.rules:
        lines.append(encode_m1(rule, nl_mapping, domain))
    
    return '\n'.join(lines)
