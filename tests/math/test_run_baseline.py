"""Tests for experiments.math.run_baseline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.generate_benchmark import generate_benchmark  # noqa: E402
from math_topology.run_baseline import (  # noqa: E402
    LevelSummary,
    RowResult,
    _grade_l1_l2,
    _grade_l3,
    run_baseline,
    summarise,
)
from math_topology.topology_instance import write_jsonl  # noqa: E402

from blanc.math import (  # noqa: E402
    DefeaterScorer,
    LeanStatus,
    MockLeanHarness,
    NoveltyFilter,
    builtin_corpus,
)
from blanc.math.types import Defeater  # noqa: E402


CORPUS = builtin_corpus()


class TestGradeL1L2:
    def test_correct_response_scores_one(self) -> None:
        l1, _, _ = generate_baseline_fixtures()
        inst = l1[0]
        result = _grade_l1_l2(inst, inst.gold[0])
        assert result.correct is True
        assert result.reward == 1.0

    def test_incorrect_response_scores_zero(self) -> None:
        l1, _, _ = generate_baseline_fixtures()
        inst = l1[0]
        result = _grade_l1_l2(inst, "totally_wrong")
        assert result.correct is False
        assert result.reward == 0.0

    def test_normalisation_tolerates_whitespace(self) -> None:
        l1, _, _ = generate_baseline_fixtures()
        inst = l1[0]
        padded = "  " + inst.gold[0] + "  "
        result = _grade_l1_l2(inst, padded)
        assert result.correct is True


class TestGradeL3:
    def test_lean_accepted_novel_defeater_scores_positive(self) -> None:
        _, _, l3 = generate_baseline_fixtures()
        inst = next(r for r in l3
                    if "convex_polytope" in r.theorem_identifier
                    and r.masked_hypotheses == ("h_convex",))
        harness = MockLeanHarness()
        from math_topology.topology_instance import reconstruct_theorem
        parent = reconstruct_theorem(inst)
        defeater = Defeater(lean_expr="P.boundary.genus = 0")
        harness.register(parent, defeater, ("h_convex",), LeanStatus.PROVED)
        scorer = DefeaterScorer(harness=harness, novelty=NoveltyFilter())
        result = _grade_l3(inst, "P.boundary.genus = 0", scorer)
        assert result.lean_status == "proved"
        assert result.reward > 0
        assert result.trivial_restoration is False

    def test_trivial_restoration_scores_zero(self) -> None:
        _, _, l3 = generate_baseline_fixtures()
        inst = next(r for r in l3
                    if "convex_polytope" in r.theorem_identifier
                    and r.masked_hypotheses == ("h_convex",))
        harness = MockLeanHarness()
        from math_topology.topology_instance import reconstruct_theorem
        parent = reconstruct_theorem(inst)
        dropped_expr = parent.hypothesis_by_name("h_convex").lean_expr
        defeater = Defeater(lean_expr=dropped_expr)
        harness.register(parent, defeater, ("h_convex",), LeanStatus.PROVED)
        scorer = DefeaterScorer(harness=harness, novelty=NoveltyFilter())
        result = _grade_l3(inst, dropped_expr, scorer)
        assert result.trivial_restoration is True
        assert result.reward == 0.0

    def test_lean_rejection_scores_zero(self) -> None:
        _, _, l3 = generate_baseline_fixtures()
        inst = l3[0]
        harness = MockLeanHarness(default_status=LeanStatus.REFUTED)
        scorer = DefeaterScorer(harness=harness, novelty=NoveltyFilter())
        result = _grade_l3(inst, "Garbage", scorer)
        assert result.reward == 0.0


class TestSummarise:
    def test_per_level_summary(self) -> None:
        rows = [
            RowResult("a", 1, "t", "x", True,  1.0),
            RowResult("b", 1, "t", "x", False, 0.0),
            RowResult("c", 2, "t", "x", True,  1.0),
            RowResult("d", 3, "t", "x", True,  0.7,
                      lean_status="proved", trivial_restoration=False,
                      novelty_distance=0.4),
        ]
        s = summarise(rows)
        assert s[1].n_rows == 2
        assert s[1].accuracy == 0.5
        assert s[2].accuracy == 1.0
        assert s[3].n_rows == 1
        assert "pct_trivial_restoration" in s[3].extras


class TestRunBaselineEndToEnd:
    def test_mock_provider_end_to_end(self, tmp_path: Path) -> None:
        bench_dir = tmp_path / "bench"
        bench_dir.mkdir()
        l1, l2, l3 = generate_baseline_fixtures()
        write_jsonl(l1, bench_dir / "l1.jsonl")
        write_jsonl(l2, bench_dir / "l2.jsonl")
        write_jsonl(l3, bench_dir / "l3.jsonl")
        out = tmp_path / "results"
        payload = run_baseline(bench_dir, "mock", out)
        assert payload["provider"] == "mock"
        assert (out / "mock.rows.jsonl").exists()
        assert (out / "mock.summary.json").exists()
        loaded = json.loads((out / "mock.summary.json").read_text())
        assert "1" in loaded["summary"] and "2" in loaded["summary"]


def generate_baseline_fixtures():
    # No L3 cap so the convex-polytope ablation is always present.
    return generate_benchmark(CORPUS, seed=17, cap_l1=4, cap_l2=4, cap_l3=None)
