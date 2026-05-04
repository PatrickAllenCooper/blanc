"""
Debate agents that use MCTS to propose and defend defeasible statements.

A ProponentAgent searches for strongly supported conclusions;
an OpponentAgent searches for defeaters or counter-conclusions.
Both wrap the generic MCTS with role-specific reward shaping.

Author: Anonymous Authors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import DefeasibleEngine
from blanc.reasoning.derivation_tree import (
    DerivationTree,
    build_derivation_tree,
)
from blanc.search.mcts import MCTS, MCTSConfig, MCTSNode
from blanc.search.derivation_space import (
    DerivationAction,
    DerivationSpace,
    DerivationState,
)
from blanc.search.reward import (
    composite_reward,
    derivation_strength_reward,
    novelty_reward,
)


@dataclass
class AgentProposal:
    """The output of an agent's MCTS-driven proposal phase."""

    statement: str
    proof_tree: Optional[DerivationTree]
    confidence: float
    derivation_path: List[DerivationAction]
    mcts_info: dict = field(default_factory=dict)


class DebateAgent:
    """
    Base class for a debate participant.

    Holds a shared knowledge base and MCTS configuration.
    Subclasses override ``_build_reward`` to tune exploration.
    """

    role: str = "base"

    def __init__(
        self,
        theory: Theory,
        mcts_config: Optional[MCTSConfig] = None,
    ):
        self.theory = theory
        self.mcts_config = mcts_config or MCTSConfig()
        self._engine = DefeasibleEngine(theory)

    def _build_reward(self, target: Optional[str] = None):
        return derivation_strength_reward(self.theory, target)

    def propose_statement(
        self, target: Optional[str] = None
    ) -> AgentProposal:
        """
        Run MCTS to convergence and propose the strongest reachable
        conclusion (or the best derivation of *target* if given).
        """
        space = DerivationSpace(
            self.theory, target=target, max_depth=50
        )
        reward = self._build_reward(target)
        engine = MCTS(space, config=self.mcts_config, reward_fn=reward)

        initial = DerivationState.initial(self.theory)
        root = engine.search(initial)

        best_state = root.state
        if root.children:
            best_node = root.most_visited_child()
            path = best_node.path_from_root()
            best_state = best_node.state
        else:
            path = [root]

        statement, confidence = self._pick_statement(
            best_state, space, target
        )

        proof_tree = None
        if statement:
            proof_tree = build_derivation_tree(self._engine, statement)

        actions = [
            n.action for n in path if n.action is not None
        ]

        return AgentProposal(
            statement=statement or "",
            proof_tree=proof_tree,
            confidence=confidence,
            derivation_path=actions,
            mcts_info=engine.get_convergence_info(),
        )

    def defend_position(
        self,
        statement: str,
        candidates: List,
        d_minus: Theory,
    ) -> Optional[str]:
        """
        Given an ablated theory and candidates, select the element
        that restores derivability of *statement*.

        Pure symbolic defense -- no LLM call.
        """
        from blanc.reasoning.defeasible import defeasible_provable
        from blanc.author.generation import _add_element

        for cand in candidates:
            augmented = _add_element(d_minus, cand)
            if defeasible_provable(augmented, statement):
                return cand if isinstance(cand, str) else str(cand)
        return None

    def _pick_statement(
        self,
        state: DerivationState,
        space: DerivationSpace,
        target: Optional[str],
    ) -> tuple:
        if target and target in state.derived:
            return target, 1.0
        novel = space.get_derived_beyond_facts(state)
        if novel:
            best = max(novel, key=lambda s: len(s))
            return best, 0.5
        return None, 0.0


class ProponentAgent(DebateAgent):
    """
    Searches for strongly grounded conclusions.

    Reward emphasises derivation strength: preferring derivations
    that traverse many defeasible rules and survive team-defeat.
    """

    role = "proponent"

    def _build_reward(self, target=None):
        strength = derivation_strength_reward(self.theory, target)
        nov = novelty_reward(self.theory)
        return composite_reward(
            {"strength": strength, "novelty": nov},
            {"strength": 0.7, "novelty": 0.3},
        )


class OpponentAgent(DebateAgent):
    """
    Searches for defeaters and counter-conclusions.

    Reward emphasises novelty and the ability to reach the complement
    of a proponent's claim.
    """

    role = "opponent"

    def __init__(
        self,
        theory: Theory,
        mcts_config: Optional[MCTSConfig] = None,
        opposing_target: Optional[str] = None,
    ):
        super().__init__(theory, mcts_config)
        self.opposing_target = opposing_target

    def _build_reward(self, target=None):
        effective_target = target or self.opposing_target
        if effective_target:
            complement = self._complement(effective_target)
            strength = derivation_strength_reward(
                self.theory, complement
            )
        else:
            strength = derivation_strength_reward(self.theory)
        nov = novelty_reward(self.theory)
        return composite_reward(
            {"strength": strength, "novelty": nov},
            {"strength": 0.4, "novelty": 0.6},
        )

    @staticmethod
    def _complement(literal: str) -> str:
        if literal.startswith("~"):
            return literal[1:]
        return f"~{literal}"
