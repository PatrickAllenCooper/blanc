"""
Metrics for instance generation and analysis.

Implements yield computation (Definition 22) and other metrics.

Author: Patrick Cooper
Date: 2026-02-11
"""

from typing import Set
from blanc.core.theory import Theory
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
