"""
Support sets and criticality computation.

Implements Definitions 17-20 from paper.tex lines 603-625.

Author: Anonymous Authors
Date: 2026-02-11
"""

from typing import Set, List, Union, Dict
from blanc.core.theory import Theory, Rule
from blanc.reasoning.defeasible import defeasible_provable


# Element can be either a fact (str) or a rule (Rule)
Element = Union[str, Rule]


def full_theory_criticality(theory: Theory, target: str) -> List[Element]:
    r"""
    Compute full-theory criticality set Crit*(D, q).
    
    Definition 18 (paper.tex line 607):
    Crit*(D, q) = {e ∈ F ∪ Rs ∪ Rd | D \ {e} ⊬∂ q}
    
    Set of elements whose removal blocks derivation of target.
    
    Complexity: O(|D|² · |F|) per paper line 292.
    Algorithm:
    1. Verify D ⊢∂ q (target must be derivable)
    2. For each element e ∈ F ∪ Rs ∪ Rd:
       a. Form D' = D \ {e}
       b. Test if D' ⊢∂ q
       c. If not, e ∈ Crit*(D, q)
    
    This is the WORKHORSE for instance generation.
    Uses polynomial-time Crit* instead of NP-complete minimal support.
    
    Proposition 4 (line 767): Crit*(D, q) ⊆ Crit(D, q) (possibly strict).
    
    Args:
        theory: Defeasible theory D
        target: Goal literal q
    
    Returns:
        List of critical elements (facts and rules)
    
    Raises:
        ValueError: If target is not derivable from theory
    
    Example:
        >>> theory = create_avian_biology_base()
        >>> critical = full_theory_criticality(theory, "flies(tweety)")
        >>> # Returns: ["bird(tweety)", Rule(flies(X) :- bird(X))]
    """
    # First verify target is derivable
    if not defeasible_provable(theory, target):
        raise ValueError(
            f"Target '{target}' is not defeasibly provable from theory. "
            f"Cannot compute criticality for non-derivable literal."
        )
    
    critical_elements: List[Element] = []
    
    # Collect all elements: facts + rules
    all_elements: List[Element] = list(theory.facts) + theory.rules
    
    # Check each element
    for element in all_elements:
        # Create theory without this element
        theory_minus = _remove_element(theory, element)
        
        # Test if target still derivable
        if not defeasible_provable(theory_minus, target):
            # Element is critical
            critical_elements.append(element)
    
    return critical_elements


def redundancy_degree(element: Element, theory: Theory, target: str) -> int:
    """
    Compute redundancy degree red(e, D, q).
    
    Definition 19 (paper.tex line 611):
    red(e, D, q) = |{S ∈ Supp(D,q) | e ∉ S}|
    
    Number of support sets that do NOT contain element e.
    
    If red(e, D, q) = 0, then e ∈ Crit*(D, q).
    Higher redundancy means element is less critical.
    
    NOTE: Computing all support sets is NP-complete.
    For MVP, we use a heuristic: redundancy = 1 if e ∉ Crit*, 0 otherwise.
    Full support set enumeration deferred to future work.
    
    Args:
        element: Element to check
        theory: Defeasible theory
        target: Goal literal
    
    Returns:
        Redundancy degree (heuristic for MVP)
    
    Example:
        >>> theory = Theory()
        >>> theory.add_fact("bird(tweety)")
        >>> theory.add_fact("sparrow(tweety)")
        >>> theory.add_rule(Rule(head="bird(X)", body=("sparrow(X)",)))
        >>> theory.add_rule(Rule(head="flies(X)", body=("bird(X)",)))
        >>> 
        >>> # bird(tweety) has redundancy 1 (can derive from sparrow rule)
        >>> red = redundancy_degree("bird(tweety)", theory, "flies(tweety)")
    """
    # MVP heuristic: Use criticality as proxy
    critical_set = full_theory_criticality(theory, target)
    
    if element in critical_set:
        # Element is critical - no redundancy
        return 0
    else:
        # Element is not critical - has at least one alternative
        return 1
    
    # TODO: Implement full support set enumeration for exact redundancy
    # This requires solving NP-complete problem
    # Approaches: SAT encoding, constraint solving, or approximation


def _remove_element(theory: Theory, element: Element) -> Theory:
    """
    Create theory with element removed.
    
    Args:
        element: Fact (str) or Rule to remove
        theory: Source theory
    
    Returns:
        New theory without element
    """
    new_theory = Theory()
    
    # Copy facts (excluding removed element if it's a fact)
    for fact in theory.facts:
        if fact != element:
            new_theory.add_fact(fact)
    
    # Copy rules (excluding removed element if it's a rule)
    for rule in theory.rules:
        if rule != element:
            new_theory.add_rule(Rule(
                head=rule.head,
                body=rule.body,
                rule_type=rule.rule_type,
                priority=rule.priority,
                label=rule.label,
                metadata=rule.metadata.copy() if rule.metadata else {}
            ))
    
    # Copy superiority relations
    new_theory.superiority = {
        k: v.copy() for k, v in theory.superiority.items()
    }
    
    return new_theory


def partition_elements_by_type(theory: Theory) -> Dict[str, Set[Element]]:
    """
    Partition theory elements by type.
    
    Useful for stratified instance generation.
    
    Returns:
        Dictionary with keys 'facts', 'strict_rules', 'defeasible_rules', 'defeaters'
    """
    from blanc.core.theory import RuleType
    
    return {
        'facts': theory.facts.copy(),
        'strict_rules': set(theory.get_rules_by_type(RuleType.STRICT)),
        'defeasible_rules': set(theory.get_rules_by_type(RuleType.DEFEASIBLE)),
        'defeaters': set(theory.get_rules_by_type(RuleType.DEFEATER)),
    }
