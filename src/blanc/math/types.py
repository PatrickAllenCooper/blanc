"""
Data types for the DeFAb-Math-Topology pipeline.

Mirrors the shape of blanc.core.theory but at the level of Lean 4 expressions
rather than Datalog literals.  A MathTheorem is the math analogue of a strict
rule; a Defeater is the analogue of a defeasible rule that overrides the
default conclusion under a stricter hypothesis subset.

Author: Patrick Cooper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LeanStatus(str, Enum):
    """Outcome of submitting a goal + tactic block to the Lean kernel."""

    PROVED = "proved"
    REFUTED = "refuted"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Hypothesis:
    """One named hypothesis on a Mathlib theorem.

    Attributes:
        name:     Lean binder name, e.g. "convex" or "h_finite".
        lean_expr: The Lean 4 type expression, e.g. "Convex \u211d S".
        critical: Heuristic flag set by the extractor; hypotheses marked
            critical are the ones the dropper preferentially ablates.
    """

    name: str
    lean_expr: str
    critical: bool = False


@dataclass(frozen=True)
class MathTheorem:
    """A theorem extracted from Mathlib (or the curated corpus).

    Attributes:
        identifier: Mathlib-style fully-qualified name, e.g.
            "EulerCharacteristic.convex_polytope_v_minus_e_plus_f".
        statement: The conclusion expression (RHS of ``:``).
        hypotheses: Ordered named hypotheses (LHS binders).
        source_path: Optional Mathlib path the theorem was lifted from.
        natural_language: Plain-English paraphrase used for prompts.
    """

    identifier: str
    statement: str
    hypotheses: tuple[Hypothesis, ...]
    source_path: Optional[str] = None
    natural_language: str = ""

    def hypothesis_names(self) -> tuple[str, ...]:
        return tuple(h.name for h in self.hypotheses)

    def hypothesis_by_name(self, name: str) -> Hypothesis:
        for h in self.hypotheses:
            if h.name == name:
                return h
        raise KeyError(f"no hypothesis named {name!r} on {self.identifier}")


@dataclass(frozen=True)
class Defeater:
    """A candidate defeater rule proposed by a model or harvested from corpus.

    A defeater is a Lean 4 hypothesis expression intended to *replace* a
    masked hypothesis on a parent theorem so the Lean kernel re-accepts the
    theorem statement.  In the defeasible-logic isomorphism (paper Section 14),
    this is the analogue of an exception rule.

    Attributes:
        lean_expr: The Lean expression for the proposed extra hypothesis.
        natural_language: Paraphrase of the defeater (optional, for prompts).
        provenance: Where this defeater came from -- "gold", "model:gpt5",
            "harvest:counterexamples", etc.
    """

    lean_expr: str
    natural_language: str = ""
    provenance: str = "unknown"


@dataclass(frozen=True)
class LeanResult:
    """Verdict from the Lean kernel for one (theorem, defeater) pair.

    Attributes:
        status: Lean kernel outcome.
        elapsed_ms: Wall time of the Lean call (for harness budgeting).
        message: Compiler / kernel diagnostic, if any.
        proof_term: Optional term-mode proof returned by the kernel.
    """

    status: LeanStatus
    elapsed_ms: int = 0
    message: str = ""
    proof_term: Optional[str] = None

    @property
    def accepted(self) -> bool:
        return self.status is LeanStatus.PROVED


@dataclass(frozen=True)
class NoveltyVerdict:
    """Output of the trivial-restoration / Mathlib-novelty filter.

    Attributes:
        is_trivial_restoration: True iff the defeater is the dropped
            hypothesis (or a definitional equivalent).
        matches_mathlib: True iff the defeater matches an existing
            Mathlib theorem statement (string + normalised form).
        matched_identifier: If matches_mathlib, which theorem matched.
        distance: A non-negative novelty distance score (larger is more
            novel).  See blanc.math.novelty.novelty_distance for the
            current operationalisation.
    """

    is_trivial_restoration: bool
    matches_mathlib: bool
    matched_identifier: Optional[str] = None
    distance: float = 0.0

    @property
    def is_novel(self) -> bool:
        return not self.is_trivial_restoration and not self.matches_mathlib


@dataclass(frozen=True)
class DefeaterScore:
    """Top-level score for one defeater on one ablation.

    Attributes:
        lean: Lean kernel verdict.
        novelty: Trivial-restoration + Mathlib-membership verdict.
        reward: A scalar in [0, 1] suitable for SFT/DPO/GRPO consumption.
            0 if Lean rejects or the defeater is trivial restoration; the
            graded reward in (0, 1] is set by ``DefeaterScorer.compute_reward``.
    """

    lean: LeanResult
    novelty: NoveltyVerdict
    reward: float = 0.0
    extras: dict[str, float] = field(default_factory=dict)
