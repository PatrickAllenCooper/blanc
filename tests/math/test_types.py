"""Tests for blanc.math.types."""

from __future__ import annotations

import pytest

from blanc.math.types import (
    Defeater,
    DefeaterScore,
    Hypothesis,
    LeanResult,
    LeanStatus,
    MathTheorem,
    NoveltyVerdict,
)


class TestMathTheorem:
    def test_hypothesis_lookup(self) -> None:
        thm = MathTheorem(
            identifier="t",
            statement="C",
            hypotheses=(
                Hypothesis(name="a", lean_expr="A"),
                Hypothesis(name="b", lean_expr="B", critical=True),
            ),
        )
        assert thm.hypothesis_names() == ("a", "b")
        assert thm.hypothesis_by_name("b").critical is True

    def test_hypothesis_lookup_missing_raises(self) -> None:
        thm = MathTheorem(identifier="t", statement="C", hypotheses=())
        with pytest.raises(KeyError):
            thm.hypothesis_by_name("nope")


class TestLeanResult:
    def test_accepted_property(self) -> None:
        ok = LeanResult(status=LeanStatus.PROVED)
        bad = LeanResult(status=LeanStatus.REFUTED)
        assert ok.accepted is True
        assert bad.accepted is False


class TestNoveltyVerdict:
    def test_is_novel_when_neither_flag_set(self) -> None:
        v = NoveltyVerdict(is_trivial_restoration=False, matches_mathlib=False)
        assert v.is_novel is True

    def test_is_novel_false_on_trivial_restoration(self) -> None:
        v = NoveltyVerdict(is_trivial_restoration=True, matches_mathlib=False)
        assert v.is_novel is False

    def test_is_novel_false_on_mathlib_match(self) -> None:
        v = NoveltyVerdict(is_trivial_restoration=False, matches_mathlib=True)
        assert v.is_novel is False


class TestDefeater:
    def test_defaults(self) -> None:
        d = Defeater(lean_expr="True")
        assert d.natural_language == ""
        assert d.provenance == "unknown"


class TestDefeaterScore:
    def test_extras_default_dict(self) -> None:
        s = DefeaterScore(
            lean=LeanResult(status=LeanStatus.UNKNOWN),
            novelty=NoveltyVerdict(is_trivial_restoration=False, matches_mathlib=False),
        )
        assert s.extras == {}
