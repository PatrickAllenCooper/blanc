"""
Metrics for instance generation and analysis.

Implements yield computation (Definition 22), predicate novelty (Definition 14),
conservativity verification (Definition 15), and revision distance (Definition 16).

Author: Anonymous Authors
Date: 2026-02-11
"""

from typing import List, Set, Tuple
from blanc.core.theory import Theory, Rule
from blanc.author.support import full_theory_criticality
from blanc.generation.partition import PartitionFunction


def defeasible_yield(
    partition_fn: PartitionFunction,
    target_set: Set[str],
    source_theory: Theory
) -> int:
    """
    Compute defeasible yield Y(κ, Q).
    
    Definition 22 (paper.tex line 623):
    Y(κ, Q) = Σ_{q∈Q} |Crit*(D_κ, q)|
    
    Total number of ablatable elements across target set Q.
    
    Measures instance generation capacity:
    - Higher yield → more instances can be generated
    - Proposition 3 (line 759): E[Y(κ_rand(δ), Q)] non-decreasing in δ
    
    Args:
        partition_fn: Partition function κ
        target_set: Set of target literals Q
        source_theory: Source theory Π (before conversion)
    
    Returns:
        Total yield (number of potential instances)
    
    Example:
        >>> from blanc.generation.partition import partition_rule
        >>> theory = create_avian_biology_base()
        >>> targets = {"flies(tweety)", "flies(opus)", "migrates(tweety)"}
        >>> yield_val = defeasible_yield(partition_rule, targets, theory)
        >>> # Returns: sum of |Crit*(D_κ, q)| for each q ∈ targets
    """
    from blanc.author.conversion import phi_kappa
    
    # Convert theory using partition function
    defeasible_theory = phi_kappa(source_theory, partition_fn)
    
    total_yield = 0
    
    for target in target_set:
        try:
            # Compute criticality for this target
            critical_set = full_theory_criticality(defeasible_theory, target)
            total_yield += len(critical_set)
        except ValueError:
            # Target not derivable - contributes 0 to yield
            pass
    
    return total_yield


def _theory_predicates(theory: Theory) -> Set[str]:
    """Collect all predicate symbols appearing in a theory."""
    preds: Set[str] = set()
    for fact in theory.facts:
        preds.add(fact.split("(")[0].lstrip("~"))
    for rule in theory.rules:
        for atom in [rule.head] + list(rule.body):
            preds.add(atom.split("(")[0].lstrip("~"))
    return preds


def predicate_novelty(rule: Rule, theory: Theory) -> float:
    """
    Predicate novelty Nov(r, D^-).

    Definition 14 (paper.tex): fraction of predicate symbols in rule r
    that are absent from D^-.  A value of 0 means the rule uses only
    predicates already known to the theory; 1 means every predicate is new.

    Args:
        rule:   The candidate defeater rule.
        theory: The challenge theory D^-.

    Returns:
        Float in [0, 1].
    """
    existing = _theory_predicates(theory)
    rule_preds: Set[str] = set()
    for atom in [rule.head] + list(rule.body):
        rule_preds.add(atom.split("(")[0].lstrip("~"))
    if not rule_preds:
        return 0.0
    novel = rule_preds - existing
    return round(len(novel) / len(rule_preds), 3)


def check_conservativity(
    D_minus: Theory,
    D_full: Theory,
    anomaly: str,
    preserved: List[str],
) -> Tuple[bool, List[str]]:
    """
    Conservativity check (Definition 15, paper.tex).

    D_full is conservative with respect to D_minus when every defeasible
    consequence of D_minus, other than the anomaly itself, remains a
    defeasible consequence of D_full.

    Args:
        D_minus:   Challenge theory (pre-defeater).
        D_full:    Revised theory (post-defeater).
        anomaly:   The incorrect prediction that the defeater resolves.
        preserved: Explicit list of literals expected to survive.

    Returns:
        (is_conservative, list_of_lost_expectations)
    """
    from blanc.reasoning.defeasible import defeasible_provable

    lost: List[str] = []
    for exp in preserved:
        if exp == anomaly:
            continue
        if defeasible_provable(D_minus, exp) and not defeasible_provable(D_full, exp):
            lost.append(exp)
    return (len(lost) == 0), lost


def revision_distance(
    D_minus: Theory,
    D_full: Theory,
    anomaly: str,
    preserved: List[str],
) -> int:
    """
    Revision distance d_rev(D^-, D^full).

    Definition 16 (paper.tex): number of elements added to D^- to form D^full
    plus the number of formerly-derived expectations that are lost.

    A conservative defeater adds exactly one element and loses zero expectations,
    giving d_rev = 1.

    Args:
        D_minus:   Challenge theory.
        D_full:    Revised theory.
        anomaly:   The resolved anomaly (excluded from loss count).
        preserved: Explicit preservation set.

    Returns:
        Non-negative integer revision distance.
    """
    added = max(0, len(D_full) - len(D_minus))
    _, lost = check_conservativity(D_minus, D_full, anomaly, preserved)
    return added + len(lost)
