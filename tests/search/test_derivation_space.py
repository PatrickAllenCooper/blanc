"""
Tests for the defeasible derivation search space adapter.

Validates action enumeration, state transitions, terminal detection,
and integration with the DefeasibleEngine.

Author: Patrick Cooper
"""

import pytest

from blanc.core.theory import Theory, Rule, RuleType
from blanc.search.derivation_space import (
    DerivationAction,
    DerivationSpace,
    DerivationState,
)
from blanc.search.mcts import MCTS, MCTSConfig
from blanc.search.reward import (
    derivation_strength_reward,
    novelty_reward,
    criticality_reward,
    composite_reward,
)


def _tweety_theory() -> Theory:
    """Minimal Tweety theory for testing."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    ))
    return t


def _chain_theory() -> Theory:
    """A -> B -> C chain."""
    t = Theory()
    t.add_fact("a(x)")
    t.add_rule(Rule(
        head="b(X)",
        body=("a(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    ))
    t.add_rule(Rule(
        head="c(X)",
        body=("b(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r2",
    ))
    return t


class TestDerivationState:
    def test_initial_state_contains_facts(self):
        theory = _tweety_theory()
        state = DerivationState.initial(theory)
        assert "bird(tweety)" in state.derived
        assert len(state.applied_rules) == 0

    def test_frozen(self):
        state = DerivationState(
            derived=frozenset(["a"]),
            applied_rules=frozenset(),
        )
        with pytest.raises(AttributeError):
            state.derived = frozenset(["b"])


class TestDerivationSpace:
    def test_legal_actions_from_initial(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        state = DerivationState.initial(theory)
        actions = space.get_legal_actions(state)
        assert len(actions) >= 1
        assert any(a.derived_literal == "flies(tweety)" for a in actions)

    def test_apply_action_extends_derived(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        state = DerivationState.initial(theory)
        actions = space.get_legal_actions(state)
        action = actions[0]
        new_state = space.apply_action(state, action)
        assert action.derived_literal in new_state.derived
        assert len(new_state.derived) > len(state.derived)

    def test_no_duplicate_actions(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        state = DerivationState.initial(theory)
        actions = space.get_legal_actions(state)
        action = actions[0]
        new_state = space.apply_action(state, action)
        follow_up = space.get_legal_actions(new_state)
        assert all(a.derived_literal != action.derived_literal for a in follow_up)

    def test_terminal_when_target_reached(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory, target="flies(tweety)")
        state = DerivationState.initial(theory)
        assert not space.is_terminal(state)
        actions = space.get_legal_actions(state)
        fly_action = next(a for a in actions if a.derived_literal == "flies(tweety)")
        new_state = space.apply_action(state, fly_action)
        assert space.is_terminal(new_state)

    def test_terminal_when_no_actions(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        state = DerivationState.initial(theory)
        actions = space.get_legal_actions(state)
        for a in actions:
            state = space.apply_action(state, a)
        assert space.is_terminal(state)

    def test_evaluate_with_target(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory, target="flies(tweety)")
        s0 = DerivationState.initial(theory)
        assert space.evaluate(s0) == 0.0
        actions = space.get_legal_actions(s0)
        fly_action = next(a for a in actions if a.derived_literal == "flies(tweety)")
        s1 = space.apply_action(s0, fly_action)
        assert space.evaluate(s1) == 1.0

    def test_evaluate_without_target(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        s0 = DerivationState.initial(theory)
        assert space.evaluate(s0) == 0.0

    def test_chain_derivation(self):
        theory = _chain_theory()
        space = DerivationSpace(theory, target="c(x)")
        state = DerivationState.initial(theory)
        actions = space.get_legal_actions(state)
        b_action = next(a for a in actions if a.derived_literal == "b(x)")
        state = space.apply_action(state, b_action)
        actions = space.get_legal_actions(state)
        c_action = next(a for a in actions if a.derived_literal == "c(x)")
        state = space.apply_action(state, c_action)
        assert space.is_terminal(state)

    def test_get_derived_beyond_facts(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory)
        state = DerivationState.initial(theory)
        assert len(space.get_derived_beyond_facts(state)) == 0
        actions = space.get_legal_actions(state)
        state = space.apply_action(state, actions[0])
        beyond = space.get_derived_beyond_facts(state)
        assert len(beyond) >= 1


class TestMCTSWithDerivationSpace:
    def test_mcts_finds_target(self):
        theory = _tweety_theory()
        space = DerivationSpace(theory, target="flies(tweety)")
        cfg = MCTSConfig(max_iterations=200, seed=42)
        mcts = MCTS(space, cfg)
        root = mcts.search(DerivationState.initial(theory))
        best = root.most_visited_child()
        assert best.action.derived_literal == "flies(tweety)"

    def test_mcts_chain_convergence(self):
        theory = _chain_theory()
        space = DerivationSpace(theory, target="c(x)")
        cfg = MCTSConfig(max_iterations=500, seed=42)
        mcts = MCTS(space, cfg)
        root = mcts.search(DerivationState.initial(theory))
        seq = mcts.get_best_sequence()
        derived = {a.derived_literal for a in seq}
        assert "b(x)" in derived or "c(x)" in derived


class TestRewardFunctions:
    def test_strength_reward_with_target(self):
        theory = _tweety_theory()
        fn = derivation_strength_reward(theory, target="flies(tweety)")
        s_no = DerivationState(
            derived=frozenset(["bird(tweety)"]),
            applied_rules=frozenset(),
        )
        s_yes = DerivationState(
            derived=frozenset(["bird(tweety)", "flies(tweety)"]),
            applied_rules=frozenset(),
        )
        assert fn(s_no) < fn(s_yes)
        assert fn(s_yes) == 1.0

    def test_novelty_reward(self):
        theory = _tweety_theory()
        fn = novelty_reward(theory)
        s0 = DerivationState(
            derived=frozenset(["bird(tweety)"]),
            applied_rules=frozenset(),
        )
        assert fn(s0) == 0.0
        s1 = DerivationState(
            derived=frozenset(["bird(tweety)", "flies(tweety)"]),
            applied_rules=frozenset(),
        )
        assert fn(s1) > 0.0

    def test_composite_reward(self):
        theory = _tweety_theory()
        strength = derivation_strength_reward(theory)
        nov = novelty_reward(theory)
        fn = composite_reward(
            {"strength": strength, "novelty": nov},
            {"strength": 0.5, "novelty": 0.5},
        )
        s = DerivationState(
            derived=frozenset(["bird(tweety)", "flies(tweety)"]),
            applied_rules=frozenset(),
        )
        val = fn(s)
        assert 0.0 <= val <= 1.0

    def test_composite_default_weights(self):
        theory = _tweety_theory()
        strength = derivation_strength_reward(theory)
        fn = composite_reward({"strength": strength})
        s = DerivationState(
            derived=frozenset(["bird(tweety)"]),
            applied_rules=frozenset(),
        )
        val = fn(s)
        assert 0.0 <= val <= 1.0

    def test_criticality_reward(self):
        theory = _tweety_theory()
        fn = criticality_reward(theory, "flies(tweety)")
        s = DerivationState(
            derived=frozenset(["bird(tweety)", "flies(tweety)"]),
            applied_rules=frozenset(),
        )
        val = fn(s)
        assert 0.0 <= val <= 1.0
