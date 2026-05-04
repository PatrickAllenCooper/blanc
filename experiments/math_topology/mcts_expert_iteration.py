"""
AlphaZero-style expert iteration scaffold for the M5 (deferred) phase.

The M5 milestone calls for neural-guided MCTS layered on the GRPO-trained
checkpoint, with Lean as the exact terminal reward.  Production training
of that loop is follow-on work; this module ships the data structures and
the abstract interfaces so the next session can plug in:

    1. a real value/policy head (the GRPO-trained foundation model);
    2. a real MCTS implementation with a search budget;
    3. an expert-iteration outer loop that distils MCTS rollouts back
       into the policy.

This module ships a deterministic ``UniformRolloutMCTS`` for contract
testing (no neural net needed) and a ``DeferredMCTS`` placeholder that
makes a ``NotImplementedError`` the only honest answer for production use.

The Lean kernel is reused as the terminal reward signal via the existing
:class:`blanc.math.lean_harness.LeanHarness`.

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import math
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

from blanc.math.defeater_scorer import DefeaterScorer
from blanc.math.hypothesis_dropper import ChallengeTheorem, HypothesisDropper
from blanc.math.types import Defeater, MathTheorem


def _build_challenge(theorem: MathTheorem, masked: Sequence[str]) -> ChallengeTheorem:
    """Construct a ChallengeTheorem for an arbitrary mask, bypassing policy."""
    masked_t = tuple(sorted(masked))
    retained = tuple(h.name for h in theorem.hypotheses if h.name not in masked_t)
    prompt = HypothesisDropper._render_prompt(theorem, masked_t)
    return ChallengeTheorem(
        parent=theorem,
        masked_hypotheses=masked_t,
        retained_hypotheses=retained,
        prompt=prompt,
    )


@dataclass(frozen=True)
class SearchNode:
    """One node in the MCTS tree.

    Defeater proposals are leaves; the action space at the root is the
    set of candidate defeaters proposed by the policy network.
    """

    defeater: Defeater
    visit_count: int
    value_sum: float
    prior: float

    @property
    def mean_value(self) -> float:
        return 0.0 if self.visit_count == 0 else self.value_sum / self.visit_count


@dataclass(frozen=True)
class SearchResult:
    theorem_identifier: str
    masked: tuple[str, ...]
    nodes: tuple[SearchNode, ...]
    best_defeater: Defeater
    best_reward: float


class MCTSPolicy(ABC):
    """Abstract policy/prior network."""

    @abstractmethod
    def propose(
        self,
        theorem: MathTheorem,
        masked: Sequence[str],
        n_candidates: int,
    ) -> list[tuple[Defeater, float]]:
        """Return n_candidates ``(defeater, prior)`` pairs."""


class MCTSExpert(ABC):
    """Abstract MCTS expert."""

    @abstractmethod
    def search(
        self,
        theorem: MathTheorem,
        masked: Sequence[str],
    ) -> SearchResult: ...


# ---------------------------------------------------------------------------
# Deterministic test backend
# ---------------------------------------------------------------------------


@dataclass
class _ListPolicy(MCTSPolicy):
    """A trivial policy that returns a fixed list of (defeater, prior)."""

    proposals: list[tuple[Defeater, float]]

    def propose(
        self,
        theorem: MathTheorem,
        masked: Sequence[str],
        n_candidates: int,
    ) -> list[tuple[Defeater, float]]:
        return list(self.proposals[:n_candidates])


@dataclass
class UniformRolloutMCTS(MCTSExpert):
    """PUCT-style search with uniform-random simulation.

    No neural net is required.  This is the contract-test backend; it
    guarantees the search loop, terminal-reward wiring, and visit-count
    bookkeeping all work, but it does not perform real expert iteration.
    """

    policy: MCTSPolicy
    scorer: DefeaterScorer
    n_simulations: int = 16
    n_candidates: int = 8
    c_puct: float = 1.0
    seed: int = 0

    def search(
        self,
        theorem: MathTheorem,
        masked: Sequence[str],
    ) -> SearchResult:
        rng = random.Random(self.seed)
        proposals = self.policy.propose(theorem, list(masked), self.n_candidates)
        if not proposals:
            raise ValueError("policy returned no proposals")

        challenge = _build_challenge(theorem, masked)

        nodes: list[dict[str, float]] = [
            {"visit_count": 0.0, "value_sum": 0.0, "prior": prior}
            for _, prior in proposals
        ]
        defeaters = [d for d, _ in proposals]

        for _ in range(self.n_simulations):
            total_visits = sum(int(n["visit_count"]) for n in nodes)
            scores = [
                (n["value_sum"] / n["visit_count"] if n["visit_count"] else 0.0)
                + self.c_puct * n["prior"] * math.sqrt(max(total_visits, 1))
                / (1.0 + n["visit_count"])
                for n in nodes
            ]
            best_idx = max(range(len(nodes)), key=lambda i: (scores[i], rng.random()))
            score = self.scorer.score(challenge, defeaters[best_idx])
            nodes[best_idx]["visit_count"] += 1.0
            nodes[best_idx]["value_sum"] += score.reward

        finalised = tuple(
            SearchNode(
                defeater=defeaters[i],
                visit_count=int(nodes[i]["visit_count"]),
                value_sum=nodes[i]["value_sum"],
                prior=nodes[i]["prior"],
            )
            for i in range(len(nodes))
        )
        best_idx = max(range(len(nodes)), key=lambda i: finalised[i].mean_value)
        return SearchResult(
            theorem_identifier=theorem.identifier,
            masked=tuple(masked),
            nodes=finalised,
            best_defeater=finalised[best_idx].defeater,
            best_reward=finalised[best_idx].mean_value,
        )


# ---------------------------------------------------------------------------
# Deferred placeholder
# ---------------------------------------------------------------------------


class DeferredMCTS(MCTSExpert):
    """Real M5 expert iteration is intentionally not implemented here.

    Production work requires (a) connecting the GRPO-trained checkpoint
    as policy/value head, (b) implementing the outer expert-iteration
    loop, and (c) a Lean-throughput-aware search budget.  Calling
    :meth:`search` here raises immediately so downstream code cannot
    silently treat it as a real expert.
    """

    def search(
        self,
        theorem: MathTheorem,
        masked: Sequence[str],
    ) -> SearchResult:
        raise NotImplementedError(
            "M5 AlphaZero-style expert iteration is deferred; use "
            "UniformRolloutMCTS for the contract path or wire a real "
            "policy/value head."
        )


# ---------------------------------------------------------------------------
# Expert-iteration data export (downstream training input)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExpertIterationRecord:
    theorem_identifier: str
    masked: tuple[str, ...]
    visit_distribution: tuple[float, ...]
    candidate_defeaters: tuple[str, ...]
    best_defeater: str
    best_reward: float

    def to_json(self) -> dict[str, object]:
        return {
            "theorem_identifier": self.theorem_identifier,
            "masked": list(self.masked),
            "visit_distribution": list(self.visit_distribution),
            "candidate_defeaters": list(self.candidate_defeaters),
            "best_defeater": self.best_defeater,
            "best_reward": self.best_reward,
        }


def search_to_record(result: SearchResult) -> ExpertIterationRecord:
    total = sum(n.visit_count for n in result.nodes) or 1
    return ExpertIterationRecord(
        theorem_identifier=result.theorem_identifier,
        masked=result.masked,
        visit_distribution=tuple(n.visit_count / total for n in result.nodes),
        candidate_defeaters=tuple(n.defeater.lean_expr for n in result.nodes),
        best_defeater=result.best_defeater.lean_expr,
        best_reward=result.best_reward,
    )


def write_records(records: Sequence[ExpertIterationRecord], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w") as f:
        for r in records:
            f.write(json.dumps(r.to_json()))
            f.write("\n")
