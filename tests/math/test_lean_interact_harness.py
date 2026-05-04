"""
Tests for LeanInteractHarness.

All tests in this module are marked ``lean_real`` and are skipped when
``lean_interact`` is not importable or when the marker is not selected.
This keeps CI (which has no Lean install) green while still validating
the real harness locally.

Run the real-Lean tests:

    pytest tests/math/test_lean_interact_harness.py -m lean_real -v

Author: Anonymous Authors
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
LEAN_DIR = ROOT / "lean"

lean_interact_available = False
try:
    import lean_interact  # noqa: F401
    lean_interact_available = True
except ImportError:
    pass

pytestmark = pytest.mark.lean_real

if not lean_interact_available:
    pytest.skip("lean_interact not installed", allow_module_level=True)

sys.path.insert(0, str(ROOT / "src"))

from blanc.math.lean_harness import LeanInteractHarness  # noqa: E402
from blanc.math.topology_extractor import builtin_corpus  # noqa: E402
from blanc.math.types import Defeater, LeanStatus, MathTheorem  # noqa: E402


@pytest.fixture(scope="module")
def harness() -> LeanInteractHarness:
    """Module-scoped harness so the REPL process is reused across tests."""
    h = LeanInteractHarness(
        lean_version="v4.25.0",
        project_dir=LEAN_DIR if LEAN_DIR.exists() else None,
        use_mathlib=True,
    )
    yield h
    h.close()


@pytest.fixture
def euler_theorem() -> MathTheorem:
    return next(
        t for t in builtin_corpus().theorems
        if t.identifier == "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"
    )


class TestLeanInteractHarnessBasic:
    def test_true_theorem_is_proved(self, harness: LeanInteractHarness) -> None:
        """A trivially true theorem with sorry must return PROVED."""
        from blanc.math.types import Hypothesis
        thm = MathTheorem(
            identifier="blanc_test_true",
            statement="True",
            hypotheses=(),
            natural_language="True is provable",
        )
        defeater = Defeater(lean_expr="True", provenance="test")
        result = harness.check(thm, defeater, masked_hypotheses=())
        assert result.status is LeanStatus.PROVED, result.message
        assert result.elapsed_ms >= 0

    def test_syntax_error_defeater_returns_error(self, harness: LeanInteractHarness) -> None:
        """A defeater whose Lean expression has a syntax error must return ERROR."""
        thm = MathTheorem(
            identifier="blanc_test_syntax_err",
            statement="True",
            hypotheses=(),
            natural_language="",
        )
        defeater = Defeater(lean_expr="( invalid @ lean @@ syntax ???", provenance="test")
        result = harness.check(thm, defeater, masked_hypotheses=())
        assert result.status is LeanStatus.ERROR, (
            f"Expected ERROR for syntactically invalid defeater, got "
            f"{result.status}: {result.message}"
        )

    def test_elapsed_ms_is_recorded(self, harness: LeanInteractHarness) -> None:
        thm = MathTheorem(
            identifier="blanc_timing_test",
            statement="True",
            hypotheses=(),
        )
        result = harness.check(thm, Defeater(lean_expr="True"), masked_hypotheses=())
        assert result.elapsed_ms > 0

    def test_server_reuse_is_fast(self, harness: LeanInteractHarness) -> None:
        """Second call on the same server should be much faster than first."""
        thm = MathTheorem(
            identifier="blanc_reuse_test",
            statement="True",
            hypotheses=(),
        )
        d = Defeater(lean_expr="True")
        r1 = harness.check(thm, d, masked_hypotheses=())
        r2 = harness.check(thm, d, masked_hypotheses=())
        assert r1.status is LeanStatus.PROVED
        assert r2.status is LeanStatus.PROVED
        # Second call should not require a full Lean startup (< 5 s is generous)
        assert r2.elapsed_ms < 5_000, f"Server reuse was slow: {r2.elapsed_ms}ms"


class TestLeanInteractHarnessAvailable:
    def test_available_harness_returns_lean_interact(self) -> None:
        from blanc.math.lean_harness import available_harness
        h = available_harness(prefer_real=True)
        assert isinstance(h, LeanInteractHarness)
