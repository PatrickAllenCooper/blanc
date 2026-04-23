"""Tests for blanc.math.defeater_scorer."""

from __future__ import annotations

import pytest

from blanc.math.defeater_scorer import DefeaterScorer, RewardWeights
from blanc.math.hypothesis_dropper import DropPolicy, HypothesisDropper
from blanc.math.lean_harness import MockLeanHarness
from blanc.math.novelty import NoveltyFilter
from blanc.math.types import Defeater, Hypothesis, LeanStatus, MathTheorem


@pytest.fixture
def thm() -> MathTheorem:
    return MathTheorem(
        identifier="t",
        statement="C",
        hypotheses=(
            Hypothesis(name="a", lean_expr="A"),
            Hypothesis(name="h", lean_expr="ConvexP", critical=True),
        ),
    )


@pytest.fixture
def challenge(thm: MathTheorem):
    return HypothesisDropper(DropPolicy.SINGLE_CRITICAL).drop(thm)[0]


class TestComputeReward:
    def test_zero_when_lean_rejects(self) -> None:
        s = DefeaterScorer(harness=MockLeanHarness())
        r = s.compute_reward(False, False, False, 0.5)
        assert r == 0.0

    def test_zero_on_trivial_restoration_even_if_accepted(self) -> None:
        s = DefeaterScorer(harness=MockLeanHarness())
        r = s.compute_reward(True, True, False, 0.9)
        assert r == 0.0

    def test_full_reward_on_lean_accept_and_novel(self) -> None:
        s = DefeaterScorer(
            harness=MockLeanHarness(),
            reward_weights=RewardWeights(
                w_lean_accept=0.6, w_distance=0.4, w_mathlib_known=0.5
            ),
        )
        r = s.compute_reward(True, False, False, 1.0)
        assert r == pytest.approx(1.0)

    def test_mathlib_known_dampens_reward(self) -> None:
        s = DefeaterScorer(
            harness=MockLeanHarness(),
            reward_weights=RewardWeights(
                w_lean_accept=0.6, w_distance=0.4, w_mathlib_known=0.5
            ),
        )
        r = s.compute_reward(True, False, True, 0.0)
        assert r == pytest.approx(0.6 * 0.5)

    def test_distance_capped_at_one(self) -> None:
        s = DefeaterScorer(harness=MockLeanHarness())
        r = s.compute_reward(True, False, False, 5.0)
        assert r == pytest.approx(1.0)


class TestEndToEndScoring:
    def test_full_pipeline_on_one_challenge(self, thm: MathTheorem, challenge) -> None:
        harness = MockLeanHarness()
        defeater_good = Defeater(lean_expr="Genus0", provenance="harvest")
        defeater_trivial = Defeater(lean_expr="ConvexP", provenance="adv")
        defeater_bad = Defeater(lean_expr="Garbage", provenance="adv")

        harness.register(thm, defeater_good, ("h",), LeanStatus.PROVED)
        harness.register(thm, defeater_trivial, ("h",), LeanStatus.PROVED)
        harness.register(thm, defeater_bad, ("h",), LeanStatus.REFUTED)

        scorer = DefeaterScorer(harness=harness, novelty=NoveltyFilter())

        s_good = scorer.score(challenge, defeater_good)
        s_trivial = scorer.score(challenge, defeater_trivial)
        s_bad = scorer.score(challenge, defeater_bad)

        assert s_good.reward > 0
        assert s_good.lean.status is LeanStatus.PROVED
        assert s_good.novelty.is_novel is True

        assert s_trivial.reward == 0.0
        assert s_trivial.novelty.is_trivial_restoration is True

        assert s_bad.reward == 0.0
        assert s_bad.lean.status is LeanStatus.REFUTED

    def test_score_batch_returns_one_score_per_defeater(
        self, thm: MathTheorem, challenge
    ) -> None:
        harness = MockLeanHarness()
        defs = [Defeater(lean_expr=f"x{i}") for i in range(3)]
        for d in defs:
            harness.register(thm, d, ("h",), LeanStatus.UNKNOWN)
        scorer = DefeaterScorer(harness=harness)
        results = scorer.score_batch(challenge, defs)
        assert len(results) == 3
