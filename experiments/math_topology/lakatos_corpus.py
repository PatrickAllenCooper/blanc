"""
Lakatos positive-control corpus.

The M2 gate: a trained model, given V-E+F=2 with convexity masked, must
propose the genus condition (or a strictly-weaker Lean-equivalent) at a
materially higher rate than baseline.

This module curates the Lakatos rediscovery family:

    -- The Euler V-E+F=2 theorem with named, separable critical hypotheses
       (convexity / boundedness / simply-connected boundary).
    -- Gold defeaters that the Lean kernel will accept after dropping each
       critical hypothesis.  These are the model's training targets.
    -- Distractors that look superficially plausible but the Lean kernel
       rejects.

The split keeps one critical hypothesis (h_convex) as the held-out
evaluation site so SFT / DPO training never sees the genus condition
plugged into a convexity-masked V-E+F=2 prompt.

Author: Anonymous Authors
"""

from __future__ import annotations

from dataclasses import dataclass, field

from blanc.math import builtin_corpus
from blanc.math.types import Defeater, MathTheorem


HELD_OUT_MASK: str = "h_convex"
"""Critical hypothesis withheld for the M2 pass-criterion check."""


@dataclass(frozen=True)
class LakatosFixture:
    """One (parent_theorem, masked_hypothesis, gold_defeaters, distractors)."""

    parent: MathTheorem
    masked: str
    gold_defeaters: tuple[Defeater, ...]
    distractors: tuple[Defeater, ...] = field(default_factory=tuple)

    @property
    def is_held_out(self) -> bool:
        return self.masked == HELD_OUT_MASK


def _euler_theorem() -> MathTheorem:
    return builtin_corpus().by_id(
        "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"
    )


def _genus_zero_family() -> tuple[Defeater, ...]:
    """Defeaters Lean accepts: V-E+F=2 holds when the boundary surface has genus 0."""
    return (
        Defeater(
            lean_expr="P.boundary.genus = 0",
            natural_language="The polytope's boundary surface has genus zero.",
            provenance="harvest:lakatos:genus",
        ),
        Defeater(
            lean_expr="EulerCharacteristic P.boundary = 2",
            natural_language="The boundary surface has Euler characteristic 2.",
            provenance="harvest:lakatos:euler_char",
        ),
        Defeater(
            lean_expr="IsHomeomorphTo P.boundary (Sphere 2)",
            natural_language="The boundary surface is homeomorphic to the 2-sphere.",
            provenance="harvest:lakatos:sphere",
        ),
    )


def _generic_topology_distractors() -> tuple[Defeater, ...]:
    """Plausible-looking but Lean-rejecting distractors."""
    return (
        Defeater(
            lean_expr="P.vertices.card = 17",
            natural_language="Polytope has 17 vertices.",
            provenance="adversarial:noise:cardinality",
        ),
        Defeater(
            lean_expr="P.faces.card \u2265 4",
            natural_language="Polytope has at least four faces.",
            provenance="adversarial:noise:lower_bound",
        ),
        Defeater(
            lean_expr="P.dim = 3",
            natural_language="Polytope is three-dimensional.",
            provenance="adversarial:noise:trivial_dimension",
        ),
    )


def lakatos_fixtures() -> tuple[LakatosFixture, ...]:
    """Build the full Lakatos fixture set.

    Each critical hypothesis on Euler V-E+F=2 yields one fixture.  The
    held-out fixture (h_convex) is intended for the M2 pass criterion;
    the other fixtures supply the SFT / DPO training signal.
    """
    parent = _euler_theorem()
    gold = _genus_zero_family()
    distractors = _generic_topology_distractors()
    return tuple(
        LakatosFixture(
            parent=parent,
            masked=h.name,
            gold_defeaters=gold,
            distractors=distractors,
        )
        for h in parent.hypotheses if h.critical
    )


def training_fixtures() -> tuple[LakatosFixture, ...]:
    """Fixtures usable for SFT / DPO -- everything except the held-out site."""
    return tuple(f for f in lakatos_fixtures() if not f.is_held_out)


def held_out_fixture() -> LakatosFixture:
    """The single held-out fixture used by the M2 pass criterion."""
    out = [f for f in lakatos_fixtures() if f.is_held_out]
    if len(out) != 1:
        raise RuntimeError(
            "expected exactly one held-out Lakatos fixture; "
            f"got {len(out)} ({HELD_OUT_MASK!r}) -- corpus drift?"
        )
    return out[0]
