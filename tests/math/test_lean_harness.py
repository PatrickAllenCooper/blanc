"""Tests for blanc.math.lean_harness."""

from __future__ import annotations

import pytest

from blanc.math.lean_harness import (
    LeanHarnessError,
    MockLeanHarness,
    SubprocessLeanHarness,
    available_harness,
)
from blanc.math.types import Defeater, LeanStatus, MathTheorem, Hypothesis


@pytest.fixture
def thm() -> MathTheorem:
    return MathTheorem(
        identifier="T.foo",
        statement="C",
        hypotheses=(
            Hypothesis(name="a", lean_expr="A"),
            Hypothesis(name="b", lean_expr="B", critical=True),
        ),
    )


class TestMockLeanHarness:
    def test_unregistered_returns_unknown(self, thm: MathTheorem) -> None:
        h = MockLeanHarness()
        result = h.check(thm, Defeater(lean_expr="X"), masked_hypotheses=("b",))
        assert result.status is LeanStatus.UNKNOWN
        assert "no registered response" in result.message

    def test_register_and_lookup(self, thm: MathTheorem) -> None:
        h = MockLeanHarness()
        defeater = Defeater(lean_expr="B")
        h.register(thm, defeater, ("b",), LeanStatus.PROVED)
        result = h.check(thm, defeater, masked_hypotheses=("b",))
        assert result.status is LeanStatus.PROVED

    def test_registration_is_normalised_on_whitespace(self, thm: MathTheorem) -> None:
        h = MockLeanHarness()
        h.register(thm, Defeater(lean_expr="A   B  C"), ("b",), LeanStatus.PROVED)
        result = h.check(thm, Defeater(lean_expr="A B C"), masked_hypotheses=("b",))
        assert result.status is LeanStatus.PROVED

    def test_mask_order_does_not_matter(self, thm: MathTheorem) -> None:
        h = MockLeanHarness()
        h.register(thm, Defeater(lean_expr="X"), ("a", "b"), LeanStatus.PROVED)
        result = h.check(thm, Defeater(lean_expr="X"), masked_hypotheses=("b", "a"))
        assert result.status is LeanStatus.PROVED


class TestSubprocessLeanHarness:
    def test_raises_when_no_lean_binary(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _name: None)
        with pytest.raises(LeanHarnessError):
            SubprocessLeanHarness()


class TestAvailableHarness:
    def test_returns_mock_when_lean_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("shutil.which", lambda _name: None)
        h = available_harness(prefer_real=False)
        assert isinstance(h, MockLeanHarness)

    def test_returns_mock_when_real_unavailable_but_requested(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import sys
        import unittest.mock as mock

        monkeypatch.setattr("shutil.which", lambda _name: None)
        # Simulate lean_interact not being installed by temporarily hiding it
        with mock.patch.dict(sys.modules, {"lean_interact": None}):
            h = available_harness(prefer_real=True)
        assert isinstance(h, MockLeanHarness)
