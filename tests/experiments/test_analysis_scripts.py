"""
Tests for experiments/analyze_results.py, error_taxonomy.py,
novelty_analysis.py, conservativity_analysis.py, difficulty_analysis.py.

All tests run against synthetic evaluation records so no files are needed.

Author: Patrick Cooper
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from analyze_results import accuracy_by, decoder_distribution, level3_metrics_summary
from error_taxonomy import build_error_taxonomy, _classify_level2
from novelty_analysis import analyze_novelty
from conservativity_analysis import analyze_conservativity
from difficulty_analysis import extract_difficulty_tuples, analyze_difficulty_distributions


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_ev(
    instance_id: str = "bio-l2-001",
    model: str = "gpt-4o",
    modality: str = "M4",
    strategy: str = "direct",
    correct: bool = True,
    decoder_stage: str = "D1",
    error_class: str = None,
    parse_success: bool = None,
    resolves_anomaly: bool = None,
    is_conservative: bool = None,
    nov: float = None,
    d_rev: int = None,
) -> dict:
    """Build a minimal evaluation record."""
    return {
        "instance_id": instance_id,
        "model": model,
        "modality": modality,
        "strategy": strategy,
        "metrics": {
            "correct": correct,
            "decoder_stage": decoder_stage,
            "error_class": error_class,
            "parse_success": parse_success,
            "resolves_anomaly": resolves_anomaly,
            "is_conservative": is_conservative,
            "nov": nov,
            "d_rev": d_rev,
        },
    }


@pytest.fixture
def mixed_evals():
    """10 evaluations: 5 Level 2 (bio), 5 Level 3."""
    evs = []
    # Level 2 -- biology
    for i in range(5):
        evs.append(_make_ev(
            instance_id=f"bio-l2-{i:03d}",
            model="gpt-4o",
            modality="M4",
            strategy="direct",
            correct=(i < 3),  # 3/5 correct
            decoder_stage="D1" if i < 3 else "D2",
        ))
    # Level 3
    for i in range(5):
        evs.append(_make_ev(
            instance_id=f"bio-l3-{i:03d}",
            model="gpt-4o",
            modality="M4",
            strategy="direct",
            correct=(i < 2),  # 2/5 correct
            decoder_stage="D1",
            error_class="E1_correct" if i < 2 else "E3_no_resolve",
            parse_success=True,
            resolves_anomaly=(i < 2),
            is_conservative=(i < 2),
            nov=0.0 if i < 3 else 0.5,
            d_rev=1 if i < 2 else None,
        ))
    return evs


# ---------------------------------------------------------------------------
# analyze_results
# ---------------------------------------------------------------------------

class TestAccuracyBy:
    def test_overall_accuracy(self, mixed_evals):
        by_level = accuracy_by(mixed_evals, "level")
        l2 = by_level.get(("2",), {})
        l3 = by_level.get(("3",), {})
        assert l2.get("correct") == 3
        assert l3.get("correct") == 2

    def test_by_model(self, mixed_evals):
        by_model = accuracy_by(mixed_evals, "model")
        assert ("gpt-4o",) in by_model
        assert by_model[("gpt-4o",)]["total"] == 10

    def test_by_modality(self, mixed_evals):
        by_mod = accuracy_by(mixed_evals, "modality")
        assert ("M4",) in by_mod

    def test_by_model_modality(self, mixed_evals):
        by_mm = accuracy_by(mixed_evals, "model", "modality")
        assert ("gpt-4o", "M4") in by_mm


class TestDecoderDistribution:
    def test_counts(self, mixed_evals):
        dist = decoder_distribution(mixed_evals)
        # Level 2: 3 D1, 2 D2; Level 3: all D1 (5)
        assert dist.get("D1", 0) == 8
        assert dist.get("D2", 0) == 2


class TestLevel3MetricsSummary:
    def test_returns_l3_only(self, mixed_evals):
        s = level3_metrics_summary(mixed_evals)
        assert s["n"] == 5

    def test_resolves_rate(self, mixed_evals):
        s = level3_metrics_summary(mixed_evals)
        assert "resolves_anomaly_rate" in s
        assert abs(s["resolves_anomaly_rate"] - 0.4) < 0.01

    def test_nov_nonzero(self, mixed_evals):
        s = level3_metrics_summary(mixed_evals)
        # 2 of 5 Level 3 evals have nov=0.5
        assert s.get("nov_nonzero", 0) == 2


# ---------------------------------------------------------------------------
# error_taxonomy
# ---------------------------------------------------------------------------

class TestBuildErrorTaxonomy:
    def test_overall_has_e1_and_e3(self, mixed_evals):
        tax = build_error_taxonomy(mixed_evals)
        overall = tax["overall"]
        assert overall.get("E1_correct", 0) > 0
        assert overall.get("E3_no_resolve", 0) > 0

    def test_by_level_keys(self, mixed_evals):
        tax = build_error_taxonomy(mixed_evals)
        assert "2" in tax["by_level"]
        assert "3" in tax["by_level"]

    def test_classify_level2_correct(self):
        ev = _make_ev(correct=True, decoder_stage="D1")
        assert _classify_level2(ev) == "E1_correct"

    def test_classify_level2_failed(self):
        ev = _make_ev(correct=False, decoder_stage="FAILED")
        assert _classify_level2(ev) == "E4_parse_failure"

    def test_classify_level2_wrong(self):
        ev = _make_ev(correct=False, decoder_stage="D2")
        assert _classify_level2(ev) == "E3_no_resolve"


# ---------------------------------------------------------------------------
# novelty_analysis
# ---------------------------------------------------------------------------

class TestAnalyzeNovelty:
    def test_basic_stats(self, mixed_evals):
        result = analyze_novelty(mixed_evals)
        assert result.get("n_level3") == 5
        assert result.get("n_with_nov") == 5

    def test_nonzero_rate(self, mixed_evals):
        result = analyze_novelty(mixed_evals)
        # 2 of 5 have nov=0.5
        assert abs(result["nov_nonzero_rate"] - 0.4) < 0.01

    def test_empty_returns_error(self):
        result = analyze_novelty([])
        assert "error" in result

    def test_no_level3_returns_error(self):
        evs = [_make_ev(instance_id="bio-l2-000", correct=True)]
        result = analyze_novelty(evs)
        assert "error" in result


# ---------------------------------------------------------------------------
# conservativity_analysis
# ---------------------------------------------------------------------------

class TestAnalyzeConservativity:
    def test_basic(self, mixed_evals):
        result = analyze_conservativity(mixed_evals)
        assert result.get("n_level3") == 5
        assert result.get("n_parsed") == 5

    def test_conservative_rate(self, mixed_evals):
        result = analyze_conservativity(mixed_evals)
        # 2 of 5 are conservative
        assert abs(result["conservativity_rate"] - 0.4) < 0.01

    def test_resolves_rate(self, mixed_evals):
        result = analyze_conservativity(mixed_evals)
        assert abs(result["resolves_rate"] - 0.4) < 0.01

    def test_empty_returns_error(self):
        result = analyze_conservativity([])
        assert "error" in result


# ---------------------------------------------------------------------------
# difficulty_analysis
# ---------------------------------------------------------------------------

class TestExtractDifficultyTuples:
    def test_extracts_from_real_level2(self):
        fpath = ROOT / "instances" / "biology_dev_instances.json"
        if not fpath.exists():
            pytest.skip("biology_dev_instances.json not found")
        tuples = extract_difficulty_tuples([str(fpath)])
        assert len(tuples) > 0
        for t in tuples:
            assert t["level"] == 2
            assert t["n_candidates"] >= 1
            assert t["support_size"] >= 1

    def test_extracts_from_real_level3(self):
        fpath = ROOT / "instances" / "level3_instances.json"
        if not fpath.exists():
            pytest.skip("level3_instances.json not found")
        tuples = extract_difficulty_tuples([str(fpath)])
        assert len(tuples) > 0
        for t in tuples:
            assert t["level"] == 3
            assert t["novelty"] >= 0.0

    def test_missing_file_skipped(self, tmp_path):
        tuples = extract_difficulty_tuples([str(tmp_path / "nonexistent.json")])
        assert tuples == []
