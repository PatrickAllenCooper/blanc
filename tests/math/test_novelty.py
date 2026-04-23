"""Tests for blanc.math.novelty."""

from __future__ import annotations

from blanc.math.novelty import NoveltyFilter, normalised_lean_expr, novelty_distance
from blanc.math.types import Defeater, Hypothesis, MathTheorem


def make_theorem(masked_expr: str) -> MathTheorem:
    return MathTheorem(
        identifier="T.t",
        statement="C",
        hypotheses=(
            Hypothesis(name="a", lean_expr=masked_expr, critical=True),
        ),
    )


class TestNormalisedLeanExpr:
    def test_collapses_whitespace(self) -> None:
        assert normalised_lean_expr("a   b\n   c") == "a b c"

    def test_normalises_arrows(self) -> None:
        assert "->" in normalised_lean_expr("A \u2192 B")

    def test_strips_outer_whitespace(self) -> None:
        assert normalised_lean_expr("   x   ") == "x"


class TestNoveltyDistance:
    def test_zero_for_identical(self) -> None:
        assert novelty_distance("Foo", "Foo") == 0.0

    def test_positive_for_different(self) -> None:
        d = novelty_distance("Foo", "Bar")
        assert d > 0.0
        assert d <= 1.0

    def test_handles_empty(self) -> None:
        assert novelty_distance("", "") == 0.0


class TestTrivialRestoration:
    def test_exact_match_is_trivial(self) -> None:
        thm = make_theorem("Convex P")
        f = NoveltyFilter()
        v = f.evaluate(thm, Defeater(lean_expr="Convex P"), ("a",))
        assert v.is_trivial_restoration is True
        assert v.is_novel is False

    def test_whitespace_difference_is_trivial(self) -> None:
        thm = make_theorem("Convex P")
        f = NoveltyFilter()
        v = f.evaluate(thm, Defeater(lean_expr="  Convex   P  "), ("a",))
        assert v.is_trivial_restoration is True

    def test_alpha_renaming_is_trivial(self) -> None:
        thm = make_theorem("Convex P")
        f = NoveltyFilter()
        v = f.evaluate(thm, Defeater(lean_expr="Convex Q"), ("a",))
        assert v.is_trivial_restoration is True


class TestMathlibMembership:
    def test_known_statement_flagged(self) -> None:
        thm = make_theorem("Convex P")
        f = NoveltyFilter([("Mathlib.Topology.foo", "P.boundary.genus = 0")])
        v = f.evaluate(thm, Defeater(lean_expr="P.boundary.genus = 0"), ("a",))
        assert v.matches_mathlib is True
        assert v.matched_identifier == "Mathlib.Topology.foo"

    def test_unknown_statement_is_novel(self) -> None:
        thm = make_theorem("Convex P")
        f = NoveltyFilter([("Mathlib.Topology.foo", "Bounded P")])
        v = f.evaluate(thm, Defeater(lean_expr="P.boundary.genus = 0"), ("a",))
        assert v.matches_mathlib is False
        assert v.is_novel is True
        assert v.distance > 0.0


class TestMaskedNoveltyDistance:
    def test_distance_picks_minimum_over_masked(self) -> None:
        thm = MathTheorem(
            identifier="t",
            statement="C",
            hypotheses=(
                Hypothesis(name="a", lean_expr="Foo", critical=True),
                Hypothesis(name="b", lean_expr="Bar", critical=True),
            ),
        )
        f = NoveltyFilter()
        v = f.evaluate(thm, Defeater(lean_expr="Foox"), ("a", "b"))
        d_a = novelty_distance("Foox", "Foo")
        d_b = novelty_distance("Foox", "Bar")
        assert v.distance == min(d_a, d_b)
