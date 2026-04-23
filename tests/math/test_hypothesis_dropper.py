"""Tests for blanc.math.hypothesis_dropper."""

from __future__ import annotations

import pytest

from blanc.math.hypothesis_dropper import (
    ChallengeTheorem,
    DropPolicy,
    HypothesisDropper,
)
from blanc.math.types import Hypothesis, MathTheorem


@pytest.fixture
def euler() -> MathTheorem:
    return MathTheorem(
        identifier="Euler.v_minus_e_plus_f",
        statement="V - E + F = 2",
        hypotheses=(
            Hypothesis(name="P", lean_expr="Polytope"),
            Hypothesis(name="h_convex", lean_expr="Convex P", critical=True),
            Hypothesis(name="h_bounded", lean_expr="Bounded P", critical=True),
            Hypothesis(name="h_misc", lean_expr="True"),
        ),
        natural_language="Euler's polyhedron formula.",
    )


class TestSingleCritical:
    def test_one_challenge_per_critical_hypothesis(self, euler: MathTheorem) -> None:
        dropper = HypothesisDropper(policy=DropPolicy.SINGLE_CRITICAL)
        challenges = dropper.drop(euler)
        assert len(challenges) == 2
        masked_names = {c.masked_hypotheses[0] for c in challenges}
        assert masked_names == {"h_convex", "h_bounded"}

    def test_retained_lists_exclude_masked(self, euler: MathTheorem) -> None:
        challenges = HypothesisDropper(DropPolicy.SINGLE_CRITICAL).drop(euler)
        for c in challenges:
            assert set(c.masked_hypotheses) & set(c.retained_hypotheses) == set()

    def test_prompt_lists_remaining_hypotheses(self, euler: MathTheorem) -> None:
        challenges = HypothesisDropper(DropPolicy.SINGLE_CRITICAL).drop(euler)
        c = challenges[0]
        for retained_name in c.retained_hypotheses:
            assert retained_name in c.prompt
        for masked_name in c.masked_hypotheses:
            assert masked_name in c.prompt


class TestSingleAny:
    def test_yields_all_singletons(self, euler: MathTheorem) -> None:
        dropper = HypothesisDropper(policy=DropPolicy.SINGLE_ANY)
        challenges = dropper.drop(euler)
        assert len(challenges) == len(euler.hypotheses)


class TestPairsCritical:
    def test_yields_critical_pairs(self, euler: MathTheorem) -> None:
        dropper = HypothesisDropper(policy=DropPolicy.PAIRS_CRITICAL)
        challenges = dropper.drop(euler)
        # 2 critical hypotheses => C(2,2) = 1 pair
        assert len(challenges) == 1
        masked = challenges[0].masked_hypotheses
        assert set(masked) == {"h_convex", "h_bounded"}


class TestChallengeTheoremMaskedExprs:
    def test_masked_exprs_match_theorem_lookup(self, euler: MathTheorem) -> None:
        c = HypothesisDropper(DropPolicy.SINGLE_CRITICAL).drop(euler)[0]
        assert c.masked_exprs[0] == euler.hypothesis_by_name(c.masked_hypotheses[0]).lean_expr
