"""
End-to-end defeater scoring for the DeFAb-Math-Topology pipeline.

Composes :class:`LeanHarness` with :class:`NoveltyFilter` to produce a single
scalar reward per (challenge, defeater) pair.  This is the signal consumed by
SFT (gold targets), DPO (margin-weighted preference pairs), and GRPO
(group-relative rewards) at M2 / M3.

Reward shape (default; configurable via ``reward_weights``):

    reward = 0                              if Lean rejects
    reward = 0                              if defeater is trivial restoration
    reward = w_lean                         if Lean accepts and novelty.is_novel
    reward = w_lean * w_mathlib_known       if Lean accepts but matches Mathlib
    reward = w_lean + w_distance * d_norm   bonus from novelty distance,
                                            capped at 1.0

Author: Patrick Cooper
"""

from __future__ import annotations

from dataclasses import dataclass, field

from blanc.math.hypothesis_dropper import ChallengeTheorem
from blanc.math.lean_harness import LeanHarness
from blanc.math.novelty import NoveltyFilter
from blanc.math.types import Defeater, DefeaterScore


@dataclass
class RewardWeights:
    """Coefficients used by :meth:`DefeaterScorer.compute_reward`.

    The defaults give:
        * Lean-accept + Mathlib-novel + max distance \u2192 1.0
        * Lean-accept + Mathlib-known                  \u2192 0.4
        * Lean-reject or trivial restoration           \u2192 0.0
    """

    w_lean_accept: float = 0.6
    w_distance:    float = 0.4
    w_mathlib_known: float = 0.5  # multiplier when defeater duplicates Mathlib


@dataclass
class DefeaterScorer:
    """Compose Lean kernel + novelty filter into one scoring call.

    Args:
        harness:          A :class:`LeanHarness`.
        novelty:          A :class:`NoveltyFilter`.
        reward_weights:   Reward coefficients.
        timeout_ms:       Per-Lean-call timeout (forwarded to harness.check).
    """

    harness: LeanHarness
    novelty: NoveltyFilter = field(default_factory=NoveltyFilter)
    reward_weights: RewardWeights = field(default_factory=RewardWeights)
    timeout_ms: int = 5_000

    def compute_reward(
        self,
        lean_accepted: bool,
        is_trivial_restoration: bool,
        matches_mathlib: bool,
        distance: float,
    ) -> float:
        if not lean_accepted or is_trivial_restoration:
            return 0.0
        w = self.reward_weights
        base = w.w_lean_accept
        if matches_mathlib:
            base *= w.w_mathlib_known
        bonus = w.w_distance * max(0.0, min(distance, 1.0))
        return min(1.0, base + bonus)

    def score(
        self,
        challenge: ChallengeTheorem,
        defeater: Defeater,
    ) -> DefeaterScore:
        lean_result = self.harness.check(
            challenge.parent,
            defeater,
            masked_hypotheses=challenge.masked_hypotheses,
            timeout_ms=self.timeout_ms,
        )
        novelty = self.novelty.evaluate(
            challenge.parent,
            defeater,
            challenge.masked_hypotheses,
        )
        reward = self.compute_reward(
            lean_accepted=lean_result.accepted,
            is_trivial_restoration=novelty.is_trivial_restoration,
            matches_mathlib=novelty.matches_mathlib,
            distance=novelty.distance,
        )
        return DefeaterScore(
            lean=lean_result,
            novelty=novelty,
            reward=reward,
            extras={
                "lean_elapsed_ms": float(lean_result.elapsed_ms),
                "novelty_distance": float(novelty.distance),
            },
        )

    def score_batch(
        self,
        challenge: ChallengeTheorem,
        defeaters: list[Defeater],
    ) -> list[DefeaterScore]:
        """Score every defeater against the same challenge."""
        return [self.score(challenge, d) for d in defeaters]
