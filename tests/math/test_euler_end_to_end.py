"""M0 end-to-end smoke test on the Euler V-E+F=2 / genus example.

This is the gating M0 deliverable: corpus + dropper + mock Lean kernel +
novelty filter + scorer all compose into a single working pipeline on the
canonical Lakatos example.

Author: Anonymous Authors
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from m0_euler_demo import build_mock_harness, run  # noqa: E402


class TestEulerEndToEnd:
    def test_demo_runs_clean(self) -> None:
        summary = run(real_lean=False, output=None)
        assert summary["theorem"] == "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"
        assert summary["passed_acceptance"] is True
        assert summary["n_rows"] > 0

    def test_genus_zero_defeater_scores_positive_on_every_ablation(self) -> None:
        summary = run(real_lean=False, output=None)
        rows = [r for r in summary["rows"] if "genus" in r["defeater_lean"].lower()]
        assert rows, "expected at least one genus-zero defeater row"
        assert all(r["reward"] > 0 for r in rows)
        assert all(r["lean_status"] == "proved" for r in rows)
        assert all(r["trivial_restoration"] is False for r in rows)

    def test_trivial_restoration_is_zero_reward_even_when_lean_accepts(self) -> None:
        summary = run(real_lean=False, output=None)
        rows = [r for r in summary["rows"] if r["trivial_restoration"]]
        assert rows, "expected trivial-restoration row(s)"
        for r in rows:
            assert r["reward"] == 0.0
            assert r["lean_status"] == "proved"

    def test_garbage_defeater_is_zero_reward(self) -> None:
        summary = run(real_lean=False, output=None)
        rows = [r for r in summary["rows"] if "17" in r["defeater_lean"]]
        assert rows, "expected garbage defeater row(s)"
        assert all(r["reward"] == 0.0 for r in rows)
        assert all(r["lean_status"] != "proved" for r in rows)

    def test_writes_summary_to_disk_when_path_given(self, tmp_path: Path) -> None:
        out = tmp_path / "summary.json"
        summary = run(real_lean=False, output=out)
        assert out.exists()
        assert out.stat().st_size > 0
        assert summary["passed_acceptance"] is True


class TestBuildMockHarness:
    def test_register_table_covers_all_critical_drops(self) -> None:
        harness = build_mock_harness(
            "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"
        )
        # Three critical hypotheses x three defeaters = 9 registrations.
        assert len(harness.responses) == 9
