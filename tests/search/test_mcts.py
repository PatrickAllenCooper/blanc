"""
Tests for the domain-agnostic Monte Carlo Tree Search engine.

Validates UCB1 correctness, convergence on toy problems, and the
exploration-exploitation balance.

Author: Anonymous Authors
"""

import math
import pytest

from blanc.search.mcts import MCTS, MCTSConfig, MCTSNode


# ---------------------------------------------------------------------------
# Tiny deterministic search space for testing
# ---------------------------------------------------------------------------

class _CountingState:
    """State is just the running total."""

    def __init__(self, value: int = 0, depth: int = 0, max_depth: int = 4):
        self.value = value
        self.depth = depth
        self.max_depth = max_depth

    def __repr__(self):
        return f"CS(v={self.value}, d={self.depth})"


class _CountingSpace:
    """
    Toy space: at each step choose +1 or +2.
    Terminal when depth reaches max_depth.
    Reward = value / (2 * max_depth).
    """

    def get_legal_actions(self, state):
        if state.depth >= state.max_depth:
            return []
        return [1, 2]

    def apply_action(self, state, action):
        return _CountingState(
            state.value + action,
            state.depth + 1,
            state.max_depth,
        )

    def is_terminal(self, state):
        return state.depth >= state.max_depth

    def evaluate(self, state):
        return state.value / (2 * state.max_depth)


class TestMCTSNode:
    def test_ucb1_unvisited_is_infinity(self):
        parent = MCTSNode(state=None)
        parent.visits = 10
        child = MCTSNode(state=None, parent=parent)
        child.visits = 0
        assert child.ucb1(1.414) == float("inf")

    def test_ucb1_formula(self):
        parent = MCTSNode(state=None)
        parent.visits = 100
        child = MCTSNode(state=None, parent=parent)
        child.visits = 10
        child.total_value = 7.0
        c = 1.414
        expected = 0.7 + c * math.sqrt(math.log(100) / 10)
        assert abs(child.ucb1(c) - expected) < 1e-6

    def test_q_value_zero_visits(self):
        node = MCTSNode(state=None)
        assert node.q_value == 0.0

    def test_q_value_with_visits(self):
        node = MCTSNode(state=None)
        node.visits = 4
        node.total_value = 2.0
        assert node.q_value == pytest.approx(0.5)

    def test_is_fully_expanded(self):
        node = MCTSNode(state=None, untried_actions=[1, 2])
        assert not node.is_fully_expanded
        node.untried_actions.clear()
        assert node.is_fully_expanded

    def test_depth(self):
        root = MCTSNode(state=None)
        child = MCTSNode(state=None, parent=root)
        grandchild = MCTSNode(state=None, parent=child)
        assert root.depth() == 0
        assert child.depth() == 1
        assert grandchild.depth() == 2

    def test_path_from_root(self):
        root = MCTSNode(state=None)
        child = MCTSNode(state=None, parent=root, action=1)
        grandchild = MCTSNode(state=None, parent=child, action=2)
        path = grandchild.path_from_root()
        assert len(path) == 3
        assert path[0] is root
        assert path[-1] is grandchild

    def test_best_child_selects_highest_ucb(self):
        parent = MCTSNode(state=None)
        parent.visits = 20
        c1 = MCTSNode(state=None, parent=parent)
        c1.visits = 10
        c1.total_value = 5.0
        c2 = MCTSNode(state=None, parent=parent)
        c2.visits = 10
        c2.total_value = 8.0
        parent.children = [c1, c2]
        assert parent.best_child(1.414) is c2

    def test_most_visited_child(self):
        parent = MCTSNode(state=None)
        c1 = MCTSNode(state=None, parent=parent)
        c1.visits = 30
        c2 = MCTSNode(state=None, parent=parent)
        c2.visits = 70
        parent.children = [c1, c2]
        assert parent.most_visited_child() is c2


class TestMCTSSearch:
    def test_search_returns_root(self):
        space = _CountingSpace()
        mcts = MCTS(space, MCTSConfig(max_iterations=50, seed=42))
        root = mcts.search(_CountingState())
        assert root is not None
        assert root.visits > 0

    def test_optimal_action_is_plus_two(self):
        """The greedy optimum always picks +2, so MCTS should converge there."""
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=500, seed=42)
        mcts = MCTS(space, cfg)
        root = mcts.search(_CountingState())
        best = root.most_visited_child()
        assert best.action == 2

    def test_convergence_stops_early(self):
        space = _CountingSpace()
        cfg = MCTSConfig(
            max_iterations=5000,
            convergence_threshold=20,
            seed=42,
        )
        mcts = MCTS(space, cfg)
        mcts.search(_CountingState())
        assert mcts.iterations_run < 5000

    def test_get_best_sequence(self):
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=300, seed=42)
        mcts = MCTS(space, cfg)
        mcts.search(_CountingState())
        seq = mcts.get_best_sequence()
        assert len(seq) >= 1
        assert all(a in (1, 2) for a in seq)

    def test_get_convergence_info(self):
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=100, seed=42)
        mcts = MCTS(space, cfg)
        mcts.search(_CountingState())
        info = mcts.get_convergence_info()
        assert "iterations" in info
        assert "root_visits" in info
        assert "children" in info
        assert info["root_visits"] > 0

    def test_custom_reward_fn(self):
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=200, seed=42)
        mcts = MCTS(space, cfg, reward_fn=lambda s: 1.0 if s.value >= 6 else 0.0)
        root = mcts.search(_CountingState())
        best = root.most_visited_child()
        assert best.action == 2

    def test_deterministic_with_seed(self):
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=200, seed=123)
        root_a = MCTS(space, cfg).search(_CountingState())
        root_b = MCTS(space, cfg).search(_CountingState())
        assert root_a.visits == root_b.visits

    def test_terminal_initial_state(self):
        space = _CountingSpace()
        cfg = MCTSConfig(max_iterations=10, seed=42)
        mcts = MCTS(space, cfg)
        terminal = _CountingState(value=8, depth=4, max_depth=4)
        root = mcts.search(terminal)
        assert root.visits > 0
        assert len(root.children) == 0
