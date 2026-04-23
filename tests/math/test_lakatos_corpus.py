"""Tests for experiments.math_topology.lakatos_corpus."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.lakatos_corpus import (  # noqa: E402
    HELD_OUT_MASK,
    held_out_fixture,
    lakatos_fixtures,
    training_fixtures,
)


class TestFixtureSet:
    def test_one_fixture_per_critical_hypothesis(self) -> None:
        fixtures = lakatos_fixtures()
        critical_count = sum(
            1 for h in fixtures[0].parent.hypotheses if h.critical
        )
        assert len(fixtures) == critical_count

    def test_held_out_is_unique_and_correctly_named(self) -> None:
        f = held_out_fixture()
        assert f.masked == HELD_OUT_MASK
        assert f.is_held_out is True

    def test_training_fixtures_exclude_held_out(self) -> None:
        for f in training_fixtures():
            assert f.masked != HELD_OUT_MASK

    def test_every_fixture_has_gold_defeaters(self) -> None:
        for f in lakatos_fixtures():
            assert len(f.gold_defeaters) >= 1

    def test_every_fixture_has_distractors(self) -> None:
        for f in lakatos_fixtures():
            assert len(f.distractors) >= 1

    def test_held_out_distractors_dont_overlap_gold(self) -> None:
        f = held_out_fixture()
        gold_exprs = {d.lean_expr for d in f.gold_defeaters}
        distractor_exprs = {d.lean_expr for d in f.distractors}
        assert gold_exprs.isdisjoint(distractor_exprs)
