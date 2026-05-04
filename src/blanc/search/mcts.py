"""
Domain-agnostic Monte Carlo Tree Search.

Provides a clean MCTS implementation parameterised by a search space
protocol. The defeasible-reasoning domain adapter lives in
derivation_space.py; this module knows nothing about logic.

Author: Anonymous Authors
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Generic,
    List,
    Optional,
    Protocol,
    TypeVar,
)


S = TypeVar("S")  # state
A = TypeVar("A")  # action


class SearchSpace(Protocol[S, A]):
    """Protocol that any domain must implement to plug into MCTS."""

    def get_legal_actions(self, state: S) -> List[A]: ...
    def apply_action(self, state: S, action: A) -> S: ...
    def is_terminal(self, state: S) -> bool: ...
    def evaluate(self, state: S) -> float: ...


@dataclass
class MCTSConfig:
    """Tuning knobs for a single MCTS run."""

    exploration_constant: float = 1.414
    max_iterations: int = 1000
    convergence_threshold: int = 50
    rollout_depth: int = 100
    seed: Optional[int] = None


@dataclass
class MCTSNode(Generic[S, A]):
    """Node in the MCTS search tree."""

    state: S
    parent: Optional["MCTSNode[S, A]"] = None
    action: Optional[A] = None
    children: List["MCTSNode[S, A]"] = field(default_factory=list)
    untried_actions: List[A] = field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0

    @property
    def q_value(self) -> float:
        if self.visits == 0:
            return 0.0
        return self.total_value / self.visits

    def ucb1(self, exploration_constant: float) -> float:
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else self.visits
        exploit = self.q_value
        explore = exploration_constant * math.sqrt(
            math.log(parent_visits) / self.visits
        )
        return exploit + explore

    def best_child(self, exploration_constant: float) -> "MCTSNode[S, A]":
        return max(self.children, key=lambda c: c.ucb1(exploration_constant))

    def most_visited_child(self) -> "MCTSNode[S, A]":
        return max(self.children, key=lambda c: c.visits)

    @property
    def is_fully_expanded(self) -> bool:
        return len(self.untried_actions) == 0

    @property
    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def depth(self) -> int:
        d = 0
        node: Optional[MCTSNode[S, A]] = self.parent
        while node is not None:
            d += 1
            node = node.parent
        return d

    def path_from_root(self) -> List["MCTSNode[S, A]"]:
        path: List[MCTSNode[S, A]] = []
        node: Optional[MCTSNode[S, A]] = self
        while node is not None:
            path.append(node)
            node = node.parent
        path.reverse()
        return path


class MCTS(Generic[S, A]):
    """
    Monte Carlo Tree Search engine.

    Parameterised by a ``SearchSpace`` that defines the domain
    (legal actions, transitions, terminal test, evaluation).
    """

    def __init__(
        self,
        space: SearchSpace[S, A],
        config: Optional[MCTSConfig] = None,
        reward_fn: Optional[Callable[[S], float]] = None,
    ):
        self.space = space
        self.config = config or MCTSConfig()
        self.reward_fn = reward_fn or space.evaluate
        self._rng = random.Random(self.config.seed)
        self.root: Optional[MCTSNode[S, A]] = None
        self.iterations_run: int = 0

    def search(self, initial_state: S) -> MCTSNode[S, A]:
        """
        Run MCTS from *initial_state* and return the root after convergence.

        The best action is ``root.most_visited_child().action``.
        """
        actions = self.space.get_legal_actions(initial_state)
        self.root = MCTSNode(
            state=initial_state,
            untried_actions=list(actions),
        )

        best_action_streak = 0
        prev_best: Optional[MCTSNode[S, A]] = None

        for i in range(self.config.max_iterations):
            node = self._select(self.root)
            node = self._expand(node)
            value = self._simulate(node)
            self._backpropagate(node, value)
            self.iterations_run = i + 1

            if self.root.children:
                cur_best = self.root.most_visited_child()
                if prev_best is not None and cur_best is prev_best:
                    best_action_streak += 1
                else:
                    best_action_streak = 1
                prev_best = cur_best

                if best_action_streak >= self.config.convergence_threshold:
                    break

        return self.root

    def _select(self, node: MCTSNode[S, A]) -> MCTSNode[S, A]:
        while not self.space.is_terminal(node.state):
            if not node.is_fully_expanded:
                return node
            node = node.best_child(self.config.exploration_constant)
        return node

    def _expand(self, node: MCTSNode[S, A]) -> MCTSNode[S, A]:
        if self.space.is_terminal(node.state):
            return node
        if not node.untried_actions:
            return node

        idx = self._rng.randrange(len(node.untried_actions))
        action = node.untried_actions.pop(idx)
        new_state = self.space.apply_action(node.state, action)
        child_actions = self.space.get_legal_actions(new_state)
        child = MCTSNode(
            state=new_state,
            parent=node,
            action=action,
            untried_actions=list(child_actions),
        )
        node.children.append(child)
        return child

    def _simulate(self, node: MCTSNode[S, A]) -> float:
        state = node.state
        depth = 0
        while (
            not self.space.is_terminal(state)
            and depth < self.config.rollout_depth
        ):
            actions = self.space.get_legal_actions(state)
            if not actions:
                break
            action = self._rng.choice(actions)
            state = self.space.apply_action(state, action)
            depth += 1
        return self.reward_fn(state)

    def _backpropagate(self, node: MCTSNode[S, A], value: float) -> None:
        current: Optional[MCTSNode[S, A]] = node
        while current is not None:
            current.visits += 1
            current.total_value += value
            current = current.parent

    def get_best_sequence(self) -> List[A]:
        """Return the action sequence along the most-visited spine."""
        if self.root is None:
            return []
        actions: List[A] = []
        node = self.root
        while node.children:
            node = node.most_visited_child()
            if node.action is not None:
                actions.append(node.action)
        return actions

    def get_convergence_info(self) -> dict:
        """Diagnostic summary of the completed search."""
        if self.root is None:
            return {}
        child_stats = [
            {
                "action": str(c.action),
                "visits": c.visits,
                "q_value": round(c.q_value, 4),
            }
            for c in sorted(
                self.root.children, key=lambda c: c.visits, reverse=True
            )
        ]
        return {
            "iterations": self.iterations_run,
            "root_visits": self.root.visits,
            "children": child_stats,
        }
