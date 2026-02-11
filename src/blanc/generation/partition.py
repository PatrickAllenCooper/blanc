"""
Partition functions for defeasible conversion.

Implements Definition 10 (structured partition classes) from paper.tex lines 586-593.

Author: Patrick Cooper
Date: 2026-02-11
"""

from typing import Callable, Dict, Optional, Set
import random as _random

from blanc.core.theory import Rule


# Type alias for partition functions
PartitionFunction = Callable[[Rule], str]


def partition_leaf(rule: Rule) -> str:
    """
    Definition 10(i): κ_leaf - facts defeasible, rules strict.
    
    Paper.tex line 589.
    
    Classification:
    - Facts (empty body) → 'd' (defeasible)
    - Rules (non-empty body) → 's' (strict)
    
    Intuition: Observations are revisable, generalizations are not.
    
    Args:
        rule: Rule to classify
    
    Returns:
        's' (strict) or 'd' (defeasible)
    
    Example:
        bird(tweety) → 'd' (defeasible fact)
        flies(X) :- bird(X) → 's' (strict rule)
    """
    return 'd' if rule.is_fact else 's'


def partition_rule(rule: Rule) -> str:
    """
    Definition 10(ii): κ_rule - rules defeasible, facts strict.
    
    Paper.tex line 590.
    
    Classification:
    - Facts (empty body) → 's' (strict)
    - Rules (non-empty body) → 'd' (defeasible)
    
    Intuition: Observations are fixed, generalizations are revisable.
    This is the natural choice for most domains.
    
    Args:
        rule: Rule to classify
    
    Returns:
        's' (strict) or 'd' (defeasible)
    
    Example:
        bird(tweety) → 's' (strict fact)
        flies(X) :- bird(X) → 'd' (defeasible rule)
    """
    return 's' if rule.is_fact else 'd'


def partition_depth(k: int, dependency_depths: Dict[str, int]) -> PartitionFunction:
    """
    Definition 10(iii): κ_depth(k) - clauses at depth ≤k strict, deeper defeasible.
    
    Paper.tex line 591.
    
    Requires dependency graph (Definition 8, line 582):
    G_Π = (P, E) where (p, q) ∈ E iff some clause has head predicate q
    and body predicate p.
    
    depth(p) = longest path from any source to p.
    
    Classification:
    - depth(head_predicate) ≤ k → 's' (strict)
    - depth(head_predicate) > k → 'd' (defeasible)
    
    Intuition: Foundational knowledge is strict, derived knowledge is revisable.
    
    Args:
        k: Depth threshold
        dependency_depths: Map from predicate name to depth in dependency graph
    
    Returns:
        Partition function
    
    Example:
        k=1, bird(tweety) at depth 0 → 's'
        k=1, flies(tweety) at depth 2 → 'd'
    """
    def partition(rule: Rule) -> str:
        # Extract head predicate
        head_pred = _extract_predicate(rule.head)
        
        # Get depth (default to 0 for unknown predicates)
        depth = dependency_depths.get(head_pred, 0)
        
        return 's' if depth <= k else 'd'
    
    return partition


def partition_random(delta: float, seed: Optional[int] = None) -> PartitionFunction:
    """
    Definition 10(iv): κ_rand(δ) - each clause defeasible with probability δ.
    
    Paper.tex line 592.
    
    Classification:
    - Each clause independently assigned 'd' with probability δ
    - Used to study yield as function of defeasibility ratio
    
    Proposition 3 (line 759): E[Y(κ_rand(δ), Q)] is non-decreasing in δ.
    
    Args:
        delta: Probability of defeasibility (0 ≤ δ ≤ 1)
        seed: Random seed for reproducibility
    
    Returns:
        Partition function
    
    Example:
        δ=0.0 → all strict (κ ≡ s)
        δ=1.0 → all defeasible (κ ≡ d)
        δ=0.5 → 50% defeasible on average
    """
    if not (0.0 <= delta <= 1.0):
        raise ValueError(f"delta must be in [0, 1], got {delta}")
    
    rng = _random.Random(seed)
    
    def partition(rule: Rule) -> str:
        return 'd' if rng.random() < delta else 's'
    
    return partition


def defeasibility_ratio(partition_fn: PartitionFunction, rules) -> float:
    """
    Compute defeasibility ratio δ(κ).
    
    Definition 9 (paper.tex line 597):
    δ(κ) = |{c ∈ Π | κ(c) = d}| / |Π|
    
    Fraction of clauses classified as defeasible.
    Controls the "revisability surface" of the converted theory.
    
    Args:
        partition_fn: Partition function κ
        rules: Set of rules in program Π
    
    Returns:
        Defeasibility ratio (0 ≤ δ ≤ 1)
    
    Example:
        All strict → δ = 0.0
        All defeasible → δ = 1.0
        Half-and-half → δ = 0.5
    """
    if not rules:
        return 0.0
    
    defeasible_count = sum(1 for rule in rules if partition_fn(rule) == 'd')
    return defeasible_count / len(rules)


def compute_dependency_depths(theory) -> Dict[str, int]:
    """
    Compute predicate depths in dependency graph.
    
    Definition 8 (paper.tex line 582):
    The dependency graph G_Π = (V, E) has V = P and (p, q) ∈ E iff
    some clause in Π has head predicate q and body predicate p.
    
    depth(p) = longest path from any source to p.
    Predicates in cycles have depth ∞.
    
    Args:
        theory: Theory object containing rules
    
    Returns:
        Map from predicate name to depth
    
    Algorithm:
        1. Build dependency graph
        2. Topological sort (detect cycles)
        3. Compute longest path from sources
    """
    from collections import defaultdict, deque
    
    # Build adjacency list: predicate → {predicates it depends on}
    depends_on = defaultdict(set)
    depended_by = defaultdict(set)
    all_predicates = set()
    
    # Extract from facts
    for fact in theory.facts:
        pred = _extract_predicate(fact)
        all_predicates.add(pred)
    
    # Extract from rules
    for rule in theory.rules:
        head_pred = _extract_predicate(rule.head)
        all_predicates.add(head_pred)
        
        for body_lit in rule.body:
            body_pred = _extract_predicate(body_lit)
            all_predicates.add(body_pred)
            
            # Edge: body_pred → head_pred (head depends on body)
            depends_on[head_pred].add(body_pred)
            depended_by[body_pred].add(head_pred)
    
    # Find sources (predicates with no dependencies)
    sources = {p for p in all_predicates if not depends_on[p]}
    
    # Compute depths via BFS
    depths = {}
    
    # Sources have depth 0
    queue = deque([(p, 0) for p in sources])
    
    while queue:
        pred, depth = queue.popleft()
        
        # Update depth if we found a longer path
        if pred not in depths or depth > depths[pred]:
            depths[pred] = depth
            
            # Propagate to dependents
            for dependent in depended_by[pred]:
                queue.append((dependent, depth + 1))
    
    # Predicates not reached have depth 0 (isolated)
    for pred in all_predicates:
        if pred not in depths:
            depths[pred] = 0
    
    return depths


def _extract_predicate(atom: str) -> str:
    """
    Extract predicate symbol from atom.
    
    Args:
        atom: Ground atom or atom with variables
    
    Returns:
        Predicate name
    
    Examples:
        "bird(tweety)" → "bird"
        "flies(X)" → "flies"
        "~flies(X)" → "flies" (strip negation)
    """
    # Handle negation
    if atom.startswith("~"):
        atom = atom[1:]
    
    # Extract predicate before parentheses
    if "(" in atom:
        return atom.split("(")[0]
    else:
        return atom
