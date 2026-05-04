"""
Reward functions for MCTS over defeasible derivation spaces.

Each function scores a DerivationState, returning a float in [0, 1].
``composite_reward`` combines several into a weighted mixture.

Author: Anonymous Authors
"""

from __future__ import annotations

from typing import Callable, Dict, Optional, Set

from blanc.core.theory import Theory, Rule, RuleType
from blanc.search.derivation_space import DerivationState

RewardFunction = Callable[[DerivationState], float]


def derivation_strength_reward(
    theory: Theory,
    target: Optional[str] = None,
) -> RewardFunction:
    """
    Reward based on how many non-trivial conclusions a derivation reaches.

    If *target* is given, reaching it yields full reward; otherwise the
    score is the fraction of defeasible rules whose heads are derived.
    """
    defeasible_heads: Set[str] = set()
    for r in theory.get_rules_by_type(RuleType.DEFEASIBLE):
        defeasible_heads.add(r.head)

    base_facts = frozenset(theory.facts)

    def reward(state: DerivationState) -> float:
        if target and target in state.derived:
            return 1.0
        derived_beyond = state.derived - base_facts
        if not defeasible_heads:
            return min(1.0, len(derived_beyond) / max(1, len(theory.rules)))
        covered = sum(
            1
            for h in defeasible_heads
            if any(d.split("(")[0] == h.split("(")[0] for d in derived_beyond)
        )
        return covered / len(defeasible_heads)

    return reward


def novelty_reward(theory: Theory) -> RewardFunction:
    """
    Reward derived conclusions that introduce predicates absent from
    the theory's original fact base, mirroring Definition 14 (Nov).
    """
    fact_preds: Set[str] = set()
    for f in theory.facts:
        fact_preds.add(f.split("(")[0].lstrip("~"))

    def reward(state: DerivationState) -> float:
        derived_beyond = state.derived - frozenset(theory.facts)
        if not derived_beyond:
            return 0.0
        novel = sum(
            1
            for d in derived_beyond
            if d.split("(")[0].lstrip("~") not in fact_preds
        )
        return novel / len(derived_beyond)

    return reward


def criticality_reward(
    theory: Theory, target: str
) -> RewardFunction:
    """
    Reward derivations that traverse critical elements for *target*.

    A state that derives *target* through elements that belong to
    Crit*(D, q) is more interesting because those elements are
    non-redundant -- ablating any one breaks the proof.  Importing
    ``full_theory_criticality`` is deferred to first call to avoid
    the O(|D|^2 |F|) cost when the reward is never used.
    """
    _cache: Dict[str, bool] = {}

    def _is_critical(literal: str) -> bool:
        if literal not in _cache:
            from blanc.author.support import full_theory_criticality

            try:
                crit = full_theory_criticality(theory, target)
                crit_strs = {
                    e if isinstance(e, str) else (e.label or str(e))
                    for e in crit
                }
                for c in crit_strs:
                    _cache[c] = True
                _cache.setdefault(literal, False)
            except ValueError:
                _cache[literal] = False
        return _cache.get(literal, False)

    base_facts = frozenset(theory.facts)

    def reward(state: DerivationState) -> float:
        derived_beyond = state.derived - base_facts
        if not derived_beyond:
            return 0.0
        n_crit = sum(1 for d in derived_beyond if _is_critical(d))
        return n_crit / len(derived_beyond)

    return reward


def composite_reward(
    rewards: Dict[str, RewardFunction],
    weights: Optional[Dict[str, float]] = None,
) -> RewardFunction:
    """
    Weighted linear combination of reward functions.

    *weights* default to uniform.  The result is clipped to [0, 1].
    """
    if weights is None:
        weights = {k: 1.0 for k in rewards}
    total_w = sum(weights.get(k, 0.0) for k in rewards)
    if total_w == 0:
        total_w = 1.0

    def reward(state: DerivationState) -> float:
        val = sum(
            weights.get(k, 0.0) * fn(state) for k, fn in rewards.items()
        )
        return max(0.0, min(1.0, val / total_w))

    return reward
