"""
blanc.math -- DeFAb-Math-Topology pipeline.

Implements the math-side analogue of the polynomial-time defeasible verifier
loop from the main project.  The Lean 4 kernel replaces the polynomial-time
engine as the exact, sound, complete reward signal.

Public surfaces:

    LeanHarness            Abstract Lean kernel adapter
    MockLeanHarness        Deterministic in-memory backend (tests, M0 demo)
    SubprocessLeanHarness  Talks to a real Lean 4 install if present
    MathlibExtractor       Pulls theorems + structured hypotheses from .lean
    HypothesisDropper      Generates challenge theorems by masking hypotheses
    NoveltyFilter          Trivial-restoration mask + Mathlib-membership check
    DefeaterScorer         End-to-end defeater scoring (Lean accept * novelty)

Anchors:
    paper/paper.tex Section 14 (extension to formalised mathematics)
    paper/ai_for_math_abstract.tex (DeFAb-Math design)
    .cursor/plans/defab-math-topology_research_agenda_56424d51.plan.md

Author: Patrick Cooper
"""

from blanc.math.types import (
    Defeater,
    DefeaterScore,
    Hypothesis,
    LeanResult,
    LeanStatus,
    MathTheorem,
    NoveltyVerdict,
)
from blanc.math.lean_harness import (
    LeanHarness,
    LeanHarnessError,
    LeanInteractHarness,
    MockLeanHarness,
    SubprocessLeanHarness,
    available_harness,
)
from blanc.math.topology_extractor import (
    MathlibExtractor,
    TopologyCorpus,
    builtin_corpus,
)
from blanc.math.hypothesis_dropper import (
    ChallengeTheorem,
    HypothesisDropper,
)
from blanc.math.novelty import (
    NoveltyFilter,
    normalised_lean_expr,
    novelty_distance,
)
from blanc.math.defeater_scorer import DefeaterScorer

__all__ = [
    "Defeater",
    "DefeaterScore",
    "Hypothesis",
    "LeanResult",
    "LeanStatus",
    "MathTheorem",
    "NoveltyVerdict",
    "LeanHarness",
    "LeanHarnessError",
    "LeanInteractHarness",
    "MockLeanHarness",
    "SubprocessLeanHarness",
    "available_harness",
    "MathlibExtractor",
    "TopologyCorpus",
    "builtin_corpus",
    "ChallengeTheorem",
    "HypothesisDropper",
    "NoveltyFilter",
    "normalised_lean_expr",
    "novelty_distance",
    "DefeaterScorer",
]
