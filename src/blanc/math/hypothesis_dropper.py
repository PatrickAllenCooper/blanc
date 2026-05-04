"""
Hypothesis-dropping ablations for DeFAb-Math-Topology.

Given a parent theorem T = (H_1, \u2026, H_n \u22a2 C), the dropper produces
``ChallengeTheorem`` instances where one or more hypotheses have been
masked away.  Each challenge is an L3 prompt: the model must propose a
defeater that, re-introduced as an extra hypothesis, lets Lean re-prove C.

The dropping policy is configurable:

    POLICY_SINGLE_CRITICAL   -- one critical hypothesis at a time (M0/M1 default)
    POLICY_SINGLE_ANY        -- one arbitrary hypothesis at a time
    POLICY_PAIRS_CRITICAL    -- all 2-subsets of critical hypotheses (M3)

Author: Anonymous Authors
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import combinations
from typing import Iterator

from blanc.math.types import Hypothesis, MathTheorem


class DropPolicy(str, Enum):
    SINGLE_CRITICAL = "single_critical"
    SINGLE_ANY = "single_any"
    PAIRS_CRITICAL = "pairs_critical"


@dataclass(frozen=True)
class ChallengeTheorem:
    """A parent theorem with some hypotheses masked.

    The model is asked to provide an extra Lean hypothesis (a defeater) that,
    re-introduced, makes Lean re-prove ``parent.statement``.

    Attributes:
        parent: The original theorem.
        masked_hypotheses: Names of removed hypotheses (sorted, immutable).
        retained_hypotheses: Names of hypotheses that remain available.
        prompt: A natural-language prompt suitable for the L3 protocol.
    """

    parent: MathTheorem
    masked_hypotheses: tuple[str, ...]
    retained_hypotheses: tuple[str, ...]
    prompt: str

    @property
    def masked_exprs(self) -> tuple[str, ...]:
        return tuple(self.parent.hypothesis_by_name(n).lean_expr
                     for n in self.masked_hypotheses)


@dataclass
class HypothesisDropper:
    """Generates ``ChallengeTheorem`` ablations from a parent theorem.

    Args:
        policy: One of :class:`DropPolicy`.
    """

    policy: DropPolicy = DropPolicy.SINGLE_CRITICAL

    @staticmethod
    def _render_prompt(parent: MathTheorem, masked: tuple[str, ...]) -> str:
        retained = [h for h in parent.hypotheses if h.name not in masked]
        retained_str = "; ".join(f"{h.name} : {h.lean_expr}" for h in retained) or "(none)"
        nl = parent.natural_language or parent.identifier
        return (
            "You are a Lean 4 mathematician.\n"
            "Theorem under consideration: "
            f"{nl}\n"
            f"Conclusion: {parent.statement}\n"
            f"Available hypotheses: {retained_str}\n"
            f"Removed hypotheses: {', '.join(masked)}.\n"
            "Propose one strictly weaker extra hypothesis (a defeater) that "
            "the Lean 4 kernel will accept.  Do not simply restate the removed "
            "hypotheses.\n\n"
            "IMPORTANT: Reply with ONLY a single Lean 4 proposition expression "
            "on one line -- no explanation, no code fences, no comments.  "
            "Example output: P.boundary.genus = 0"
        )

    def _candidate_subsets(self, theorem: MathTheorem) -> Iterator[tuple[Hypothesis, ...]]:
        critical = tuple(h for h in theorem.hypotheses if h.critical)
        if self.policy is DropPolicy.SINGLE_CRITICAL:
            for h in critical:
                yield (h,)
        elif self.policy is DropPolicy.SINGLE_ANY:
            for h in theorem.hypotheses:
                yield (h,)
        elif self.policy is DropPolicy.PAIRS_CRITICAL:
            for pair in combinations(critical, 2):
                yield pair
        else:  # pragma: no cover  (Enum is exhaustive)
            raise ValueError(f"unknown drop policy {self.policy!r}")

    def drop(self, theorem: MathTheorem) -> list[ChallengeTheorem]:
        """Produce all ablations for one theorem under the active policy."""
        out: list[ChallengeTheorem] = []
        for subset in self._candidate_subsets(theorem):
            masked = tuple(sorted(h.name for h in subset))
            retained = tuple(
                h.name for h in theorem.hypotheses if h.name not in masked
            )
            out.append(
                ChallengeTheorem(
                    parent=theorem,
                    masked_hypotheses=masked,
                    retained_hypotheses=retained,
                    prompt=self._render_prompt(theorem, masked),
                )
            )
        return out
