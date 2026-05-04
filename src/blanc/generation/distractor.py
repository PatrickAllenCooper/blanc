"""
Distractor generation for abductive instances.

Implements distractor sampling strategies from paper.tex Section 4.2.

Author: Anonymous Authors
Date: 2026-02-11
"""

import random
import re
from typing import List, Set
from blanc.core.theory import Theory, Rule, RuleType


def sample_fact_distractors(
    target_fact: str,
    theory: Theory,
    k: int,
    strategy: str = "syntactic"
) -> List[str]:
    """
    Sample k distractor facts for Level 1 instances.
    
    Paper.tex Section 4.2 (lines 348-349): Three distractor regimes.
    
    Strategies:
        - 'random': Uniformly sampled from F
        - 'syntactic': Share predicate symbols with target
        - 'adversarial': Satisfy subset of derivability conditions
    
    Args:
        target_fact: The gold fact (to avoid sampling)
        theory: Theory to sample from
        k: Number of distractors
        strategy: Sampling strategy
    
    Returns:
        List of k distractor facts
    
    Example:
        >>> theory = create_avian_biology_base()
        >>> distractors = sample_fact_distractors(
        ...     "bird(tweety)",
        ...     theory,
        ...     k=5,
        ...     strategy="syntactic"
        ... )
        >>> # Returns facts like bird(polly), bird(opus), etc.
    """
    if strategy == "random":
        return _sample_random_facts(target_fact, theory, k)
    elif strategy == "syntactic":
        return _sample_syntactic_facts(target_fact, theory, k)
    elif strategy == "adversarial":
        return _sample_adversarial_facts(target_fact, theory, k)
    else:
        raise ValueError(
            f"Unknown distractor strategy: {strategy}. "
            f"Available: 'random', 'syntactic', 'adversarial'"
        )


def sample_rule_distractors(
    target_rule: Rule,
    theory: Theory,
    k: int,
    strategy: str = "syntactic"
) -> List[Rule]:
    """
    Sample k distractor rules for Level 2 instances.
    
    Paper.tex Section 4.2 (lines 348-349): Three distractor regimes.
    
    Strategies:
        - 'random': Uniformly sampled from Rd
        - 'syntactic': Share predicate symbols or permute arguments
        - 'adversarial': Ablate proper subset of antecedents
    
    Args:
        target_rule: The gold rule (to avoid sampling)
        theory: Theory to sample from
        k: Number of distractors
        strategy: Sampling strategy
    
    Returns:
        List of k distractor rules
    
    Example:
        >>> theory = create_avian_biology_base()
        >>> target = next(r for r in theory.rules if r.label == "r1")
        >>> distractors = sample_rule_distractors(
        ...     target,
        ...     theory,
        ...     k=5,
        ...     strategy="syntactic"
        ... )
    """
    if strategy == "random":
        return _sample_random_rules(target_rule, theory, k)
    elif strategy == "syntactic":
        return _sample_syntactic_rules(target_rule, theory, k)
    elif strategy == "adversarial":
        return _sample_adversarial_rules(target_rule, theory, k)
    else:
        raise ValueError(
            f"Unknown distractor strategy: {strategy}. "
            f"Available: 'random', 'syntactic', 'adversarial'"
        )


# ===========================================================================
# FACT DISTRACTOR STRATEGIES
# ===========================================================================

def _sample_random_facts(target_fact: str, theory: Theory, k: int) -> List[str]:
    """Sample k random facts from theory (excluding target)."""
    available_facts = [f for f in theory.facts if f != target_fact]
    
    if not available_facts:
        return []
    
    # Sample up to k facts
    sample_size = min(k, len(available_facts))
    return random.sample(available_facts, sample_size)


def _sample_syntactic_facts(target_fact: str, theory: Theory, k: int) -> List[str]:
    """
    Sample k facts sharing predicate with target (syntactic similarity).
    
    Paper.tex line 349: "sharing predicate symbols with the ablated element"
    """
    target_pred = _extract_predicate(target_fact)
    
    # Find facts with same predicate
    same_pred_facts = [
        f for f in theory.facts
        if f != target_fact and _extract_predicate(f) == target_pred
    ]
    
    if not same_pred_facts:
        # Fallback to random if no same-predicate facts
        return _sample_random_facts(target_fact, theory, k)
    
    # Sample up to k
    sample_size = min(k, len(same_pred_facts))
    return random.sample(same_pred_facts, sample_size)


def _sample_adversarial_facts(target_fact: str, theory: Theory, k: int) -> List[str]:
    """
    Sample adversarial distractors (near-misses).
    
    Paper.tex line 349: "satisfying a strict subset of the conditions
    required for a valid hypothesis"
    
    For facts: Facts with similar predicates or partial matches.
    """
    # For MVP: Use syntactic as approximation
    # Full adversarial generation requires semantic analysis
    return _sample_syntactic_facts(target_fact, theory, k)


# ===========================================================================
# RULE DISTRACTOR STRATEGIES
# ===========================================================================

def _sample_random_rules(target_rule: Rule, theory: Theory, k: int) -> List[Rule]:
    """Sample k random defeasible rules from theory (excluding target)."""
    available_rules = [
        r for r in theory.get_rules_by_type(RuleType.DEFEASIBLE)
        if r != target_rule
    ]
    
    if not available_rules:
        return []
    
    sample_size = min(k, len(available_rules))
    return random.sample(available_rules, sample_size)


def _sample_syntactic_rules(target_rule: Rule, theory: Theory, k: int) -> List[Rule]:
    """
    Sample rules with predicate substitution or argument permutation.
    
    Paper.tex line 349: "substituting predicate symbols or permuting
    arguments in e"
    """
    distractors = []
    
    # Strategy 1: Sample rules with similar structure (same arity)
    target_arity = len(target_rule.body)
    similar_rules = [
        r for r in theory.get_rules_by_type(RuleType.DEFEASIBLE)
        if r != target_rule and len(r.body) == target_arity
    ]
    
    if similar_rules:
        sample_size = min(k, len(similar_rules))
        distractors.extend(random.sample(similar_rules, sample_size))
    
    # If we need more, generate synthetic variations
    while len(distractors) < k:
        # Create synthetic distractor via predicate substitution
        synthetic = _create_synthetic_rule_distractor(target_rule, theory)
        if synthetic and synthetic not in distractors:
            distractors.append(synthetic)
        else:
            # Can't generate more unique distractors
            break
    
    return distractors[:k]


def _sample_adversarial_rules(target_rule: Rule, theory: Theory, k: int) -> List[Rule]:
    """
    Sample adversarial rule distractors.
    
    Paper.tex line 349: "ablating a proper subset of the gold element's
    antecedents"
    
    For MVP: Generate rules with subset of body literals.
    """
    distractors = []
    
    # Generate rules with subsets of body
    if len(target_rule.body) >= 2:
        for i, body_lit in enumerate(target_rule.body):
            # Create rule with one body literal removed
            new_body = tuple(b for j, b in enumerate(target_rule.body) if j != i)
            
            distractor = Rule(
                head=target_rule.head,
                body=new_body,
                rule_type=RuleType.DEFEASIBLE,
                label=f"{target_rule.label}_adv{i}" if target_rule.label else None
            )
            
            distractors.append(distractor)
            
            if len(distractors) >= k:
                break
    
    # Fill remaining with syntactic distractors
    if len(distractors) < k:
        syntactic = _sample_syntactic_rules(target_rule, theory, k - len(distractors))
        distractors.extend(syntactic)
    
    return distractors[:k]


def _create_synthetic_rule_distractor(target_rule: Rule, theory: Theory) -> Rule:
    """
    Create synthetic distractor by modifying target rule.
    
    Modifications:
    - Substitute head predicate
    - Substitute body predicate
    - Change rule structure slightly
    """
    # For MVP: Create rule with swapped head/body predicates if possible
    if target_rule.body:
        # Swap first body predicate with head
        first_body = target_rule.body[0]
        
        return Rule(
            head=first_body,
            body=(target_rule.head,) + target_rule.body[1:],
            rule_type=RuleType.DEFEASIBLE,
            label=f"{target_rule.label}_syn" if target_rule.label else None
        )
    
    return None


def _extract_predicate(atom: str) -> str:
    """Extract predicate from atom."""
    if atom.startswith("~"):
        atom = atom[1:]
    if "(" in atom:
        return atom.split("(")[0]
    return atom
