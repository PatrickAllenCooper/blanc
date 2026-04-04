"""Coverage tests for search/reward.py uncovered paths.

Targets: derivation_reward with no defeasible heads, novelty_reward
with no novel predicates, criticality_reward ValueError path,
composite_reward zero weights.
"""

import pytest

from blanc.core.theory import Rule, RuleType, Theory
from blanc.search.derivation_space import DerivationState
from blanc.search.reward import (
    composite_reward,
    criticality_reward,
    derivation_strength_reward,
    novelty_reward,
)


def _make_state(derived=frozenset()):
    return DerivationState(
        derived=derived,
        applied_rules=frozenset(),
    )


class TestDerivationStrengthReward:
    def test_target_derived_gives_one(self):
        theory = Theory()
        theory.add_fact("p(a)")
        theory.add_rule(Rule(head="q(X)", body=("p(X)",),
                             rule_type=RuleType.DEFEASIBLE))
        fn = derivation_strength_reward(theory, target="q(a)")
        state = _make_state(derived=frozenset({"p(a)", "q(a)"}))
        assert fn(state) == 1.0

    def test_no_defeasible_heads_fallback(self):
        theory = Theory()
        theory.add_fact("p(a)")
        theory.add_rule(Rule(head="q(X)", body=("p(X)",),
                             rule_type=RuleType.STRICT))
        fn = derivation_strength_reward(theory, target="missing(x)")
        state = _make_state(derived=frozenset({"p(a)", "q(a)"}))
        reward = fn(state)
        assert 0.0 <= reward <= 1.0

    def test_empty_derived_beyond(self):
        theory = Theory()
        theory.add_fact("p(a)")
        fn = derivation_strength_reward(theory)
        state = _make_state(derived=frozenset({"p(a)"}))
        reward = fn(state)
        assert reward == 0.0


class TestNoveltyReward:
    def test_no_novel_predicates(self):
        theory = Theory()
        theory.add_fact("p(a)")
        fn = novelty_reward(theory)
        state = _make_state(derived=frozenset({"p(a)", "p(b)"}))
        assert fn(state) == 0.0

    def test_novel_predicate_present(self):
        theory = Theory()
        theory.add_fact("p(a)")
        fn = novelty_reward(theory)
        state = _make_state(derived=frozenset({"p(a)", "q(b)"}))
        assert fn(state) > 0.0

    def test_empty_derived(self):
        theory = Theory()
        theory.add_fact("p(a)")
        fn = novelty_reward(theory)
        state = _make_state(derived=frozenset({"p(a)"}))
        assert fn(state) == 0.0


class TestCriticalityReward:
    def test_critical_literal_scored(self):
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r1"))
        fn = criticality_reward(theory, "flies(tweety)")
        state = _make_state(derived=frozenset({"bird(tweety)", "flies(tweety)"}))
        reward = fn(state)
        assert 0.0 <= reward <= 1.0

    def test_no_derived_beyond_gives_zero(self):
        theory = Theory()
        theory.add_fact("bird(tweety)")
        fn = criticality_reward(theory, "flies(tweety)")
        state = _make_state(derived=frozenset({"bird(tweety)"}))
        assert fn(state) == 0.0


class TestCompositeReward:
    def test_uniform_weights(self):
        theory = Theory()
        theory.add_fact("p(a)")
        r1 = derivation_strength_reward(theory)
        r2 = novelty_reward(theory)
        fn = composite_reward({"d": r1, "n": r2})
        state = _make_state(derived=frozenset({"p(a)", "q(b)"}))
        reward = fn(state)
        assert 0.0 <= reward <= 1.0

    def test_zero_total_weight(self):
        theory = Theory()
        theory.add_fact("p(a)")
        r1 = derivation_strength_reward(theory)
        fn = composite_reward({"d": r1}, weights={"d": 0.0})
        state = _make_state(derived=frozenset({"p(a)", "q(b)"}))
        reward = fn(state)
        assert reward == 0.0
