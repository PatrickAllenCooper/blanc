"""
Tests for all B6 fine-tuning analysis scripts.

These scripts live in experiments/finetuning/ (not in src/blanc, so not
tracked by coverage). Tests verify:
  - Pure helper functions that need no GPU or data files
  - Result loading and filtering
  - Table building with mock data
  - Graceful handling of missing data

Author: Patrick Cooper
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "finetuning"))


# ---------------------------------------------------------------------------
# Fixtures: mock result data
# ---------------------------------------------------------------------------

def _make_ft_eval(
    instance_id: str = "bio-l2-001",
    model: str = "finetuned:final",
    correct: bool = True,
    level: int = 2,
    error_type: str = None,
    graded_score: float = None,
    modality: str = "M4",
    strategy: str = "direct",
) -> dict:
    metrics: dict = {"correct": correct}
    if error_type:
        metrics["error_type"] = error_type
    if graded_score is not None:
        metrics["graded_score"] = graded_score
    return {
        "instance_id": instance_id,
        "model": model,
        "modality": modality,
        "strategy": strategy,
        "level": level,
        "metrics": metrics,
    }


def _make_ft_result_json(
    tmp_path: Path,
    evals: list[dict],
    checkpoint: str = "checkpoints/dpo_standard_joint_Qwen/final",
    base_model: str = "Qwen/Qwen2.5-72B-Instruct-AWQ",
    label: str = "final",
) -> Path:
    data = {
        "evaluations": evals,
        "metadata": {
            "checkpoint": checkpoint,
            "base_model": base_model,
            "split": "test",
            "label": label,
            "timestamp": "20260302_120000",
        },
    }
    path = tmp_path / f"results_finetuned_{label}.json"
    path.write_text(json.dumps(data))
    return path


def _make_training_config(
    tmp_path: Path,
    dpo_variant: str = "standard",
    curriculum: str = "joint",
    base_model: str = "Qwen/Qwen2.5-72B-Instruct-AWQ",
    gamma: float = 2.0,
    data_fraction: float = 1.0,
) -> Path:
    cfg = {
        "dpo_variant": dpo_variant,
        "curriculum": curriculum,
        "base_model": base_model,
        "margin_delta": gamma,
        "data_fraction": data_fraction,
    }
    cfg_path = tmp_path / "training_config.json"
    cfg_path.write_text(json.dumps(cfg))
    return cfg_path


# ---------------------------------------------------------------------------
# Shared helpers (imported from generate_ft_tables / analyze_ft_lift)
# ---------------------------------------------------------------------------

class TestSharedHelpers:
    def test_model_short_qwen72(self):
        from generate_ft_tables import _model_short
        assert _model_short("Qwen/Qwen2.5-72B-Instruct-AWQ") == "Qwen-72B"

    def test_model_short_qwen32(self):
        from generate_ft_tables import _model_short
        assert _model_short("Qwen/Qwen2.5-32B-Instruct-AWQ") == "Qwen-32B"

    def test_model_short_deepseek(self):
        from generate_ft_tables import _model_short
        assert _model_short("casperhansen/deepseek-r1-distill-llama-70b-awq") == "DS-R1-70B"

    def test_model_short_unknown(self):
        from generate_ft_tables import _model_short
        name = _model_short("some/unknown-model-xyz")
        assert isinstance(name, str) and len(name) > 0

    def test_method_short_dpo_standard(self):
        from generate_ft_tables import _method_short
        cfg = {"dpo_variant": "standard"}
        assert _method_short(cfg) == "DPO-std"

    def test_method_short_dpo_margin(self):
        from generate_ft_tables import _method_short
        assert _method_short({"dpo_variant": "margin"}) == "DPO-margin"

    def test_method_short_vitl(self):
        from generate_ft_tables import _method_short
        assert _method_short({"mode": "vitl"}) == "VITL"

    def test_method_short_rlhf_rm(self):
        from generate_ft_tables import _method_short
        assert _method_short({"mode": "reward-model"}) == "RLHF-RM"

    def test_level_from_instance_id_l3(self):
        from generate_ft_tables import _level
        assert _level({"instance_id": "bio-l3-001"}) == 3

    def test_level_from_instance_id_l2(self):
        from generate_ft_tables import _level
        assert _level({"instance_id": "bio-l2-001"}) == 2

    def test_level_from_level_field_fallback(self):
        from generate_ft_tables import _level
        # No "l3" in instance_id -> falls back to ev.get("level", 2) = 3
        assert _level({"instance_id": "xyz", "level": 3}) == 3

    def test_level_defaults_to_2(self):
        from generate_ft_tables import _level
        assert _level({"instance_id": "xyz"}) == 2

    def test_accuracy_all_correct(self):
        from generate_ft_tables import _accuracy
        evals = [_make_ft_eval(correct=True), _make_ft_eval(correct=True)]
        acc, n = _accuracy(evals, level=2)
        assert acc == pytest.approx(1.0)
        assert n == 2

    def test_accuracy_none_correct(self):
        from generate_ft_tables import _accuracy
        evals = [_make_ft_eval(correct=False), _make_ft_eval(correct=False)]
        acc, n = _accuracy(evals, level=2)
        assert acc == pytest.approx(0.0)

    def test_accuracy_empty_level(self):
        from generate_ft_tables import _accuracy
        evals = [_make_ft_eval(instance_id="bio-l3-001", correct=True)]
        acc, n = _accuracy(evals, level=2)
        assert math.isnan(acc)
        assert n == 0

    def test_is_finetuned_with_checkpoint(self):
        from generate_ft_tables import _is_finetuned
        assert _is_finetuned({"checkpoint": "some/path"}) is True

    def test_is_finetuned_without_checkpoint(self):
        from generate_ft_tables import _is_finetuned
        assert _is_finetuned({"model": "gpt"}) is False

    def test_wilson_ci_valid(self):
        from generate_ft_tables import _wilson_ci
        lo, hi = _wilson_ci(80, 100)
        assert 0.7 < lo < 0.85
        assert 0.85 < hi < 0.95

    def test_wilson_ci_zero_n(self):
        from generate_ft_tables import _wilson_ci
        lo, hi = _wilson_ci(0, 0)
        assert math.isnan(lo)
        assert math.isnan(hi)


# ---------------------------------------------------------------------------
# generate_ft_tables.py — table builders
# ---------------------------------------------------------------------------

class TestGenerateFtTables:
    def test_build_table4_no_results(self):
        from generate_ft_tables import build_table4
        result = build_table4([])
        assert "%" in result  # LaTeX comment for no data

    def test_build_table4_with_results(self, tmp_path):
        from generate_ft_tables import build_table4, _load_training_config

        cfg_path = _make_training_config(tmp_path, dpo_variant="standard")
        checkpoint = str(tmp_path)
        evals = [
            _make_ft_eval(correct=True, level=2),
            _make_ft_eval(instance_id="bio-l3-001", correct=True, level=3),
        ]
        meta = {
            "checkpoint": checkpoint,
            "base_model": "Qwen/Qwen2.5-72B-Instruct-AWQ",
        }
        result = build_table4([(evals, meta)])
        assert "tabular" in result or "%" in result

    def test_build_table5_no_results(self):
        from generate_ft_tables import build_table5
        result = build_table5([])
        assert "%" in result

    def test_build_table6_no_ft_results(self):
        from generate_ft_tables import build_table6
        result = build_table6([], [])
        assert "%" in result

    def test_load_result_file_list_format(self, tmp_path):
        from generate_ft_tables import _load_result_file
        path = tmp_path / "results.json"
        path.write_text(json.dumps([_make_ft_eval()]))
        evals, meta = _load_result_file(path)
        assert len(evals) == 1
        assert meta == {}

    def test_load_result_file_dict_format(self, tmp_path):
        from generate_ft_tables import _load_result_file
        path = _make_ft_result_json(tmp_path, [_make_ft_eval()])
        evals, meta = _load_result_file(path)
        assert len(evals) == 1
        assert "checkpoint" in meta

    def test_load_all_results_from_dir(self, tmp_path):
        from generate_ft_tables import _load_all_results
        _make_ft_result_json(tmp_path, [_make_ft_eval()])
        results = _load_all_results(tmp_path)
        assert len(results) == 1

    def test_load_all_results_empty_dir(self, tmp_path):
        from generate_ft_tables import _load_all_results
        results = _load_all_results(tmp_path)
        assert results == []

    def test_load_all_results_skips_invalid_json(self, tmp_path):
        from generate_ft_tables import _load_all_results
        (tmp_path / "bad.json").write_text("NOT JSON {{{")
        results = _load_all_results(tmp_path)
        assert results == []

    def test_load_training_config_reads_file(self, tmp_path):
        from generate_ft_tables import _load_training_config
        _make_training_config(tmp_path, dpo_variant="margin")
        cfg = _load_training_config(str(tmp_path))
        assert cfg["dpo_variant"] == "margin"

    def test_load_training_config_missing_returns_empty(self, tmp_path):
        from generate_ft_tables import _load_training_config
        cfg = _load_training_config(str(tmp_path / "nonexistent"))
        assert cfg == {}


# ---------------------------------------------------------------------------
# analyze_ft_lift.py (Conjecture 1)
# ---------------------------------------------------------------------------

class TestAnalyzeFtLift:
    def test_mcnemar_equal_groups(self):
        from analyze_ft_lift import _mcnemar
        all_ids = {"a", "b", "c", "d"}
        correct_a = {"a", "b"}
        correct_b = {"b", "c"}
        stat = _mcnemar(correct_a, correct_b, all_ids)
        assert "b" in stat and "c" in stat
        assert stat["b"] + stat["c"] > 0

    def test_mcnemar_identical_sets(self):
        from analyze_ft_lift import _mcnemar
        all_ids = {"a", "b"}
        stat = _mcnemar({"a", "b"}, {"a", "b"}, all_ids)
        assert stat["b"] == 0
        assert stat["c"] == 0
        assert stat["p"] == 1.0

    def test_mcnemar_empty_sets(self):
        from analyze_ft_lift import _mcnemar
        stat = _mcnemar(set(), set(), set())
        assert stat["p"] == 1.0

    def test_accuracy_l3(self):
        from analyze_ft_lift import _accuracy
        evals = [
            _make_ft_eval(instance_id="bio-l3-001", correct=True),
            _make_ft_eval(instance_id="bio-l3-002", correct=False),
        ]
        acc, c, n = _accuracy(evals, level=3)
        assert n == 2
        assert c == 1
        assert acc == pytest.approx(0.5)

    def test_main_no_ft_results(self, tmp_path, monkeypatch):
        from analyze_ft_lift import main
        monkeypatch.setattr(
            "sys.argv",
            ["analyze_ft_lift.py",
             "--results-dir", str(tmp_path),
             "--base-results-dir", str(tmp_path)],
        )
        result = main()
        assert result == 1


# ---------------------------------------------------------------------------
# analyze_error_shift.py (Conjecture 2)
# ---------------------------------------------------------------------------

class TestAnalyzeErrorShift:
    def test_error_distribution_collects_types(self):
        from analyze_error_shift import _error_distribution
        evals = [
            _make_ft_eval(instance_id="bio-l3-001", correct=False, error_type="E1"),
            _make_ft_eval(instance_id="bio-l3-002", correct=False, error_type="E2"),
            _make_ft_eval(instance_id="bio-l3-003", correct=True),
        ]
        dist = _error_distribution(evals, level=3)
        assert dist.get("E1", 0) == 1
        assert dist.get("E2", 0) == 1
        assert dist.get("E5", 0) == 1  # correct -> E5

    def test_error_distribution_wrong_level_excluded(self):
        from analyze_error_shift import _error_distribution
        evals = [_make_ft_eval(correct=False, error_type="E1")]  # level 2
        dist = _error_distribution(evals, level=3)
        assert sum(dist.values()) == 0

    def test_chi2_test_zero_table(self):
        from analyze_error_shift import _chi2_test
        result = _chi2_test([0, 0, 0], [0, 0, 0])
        assert result["chi2"] == 0.0

    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_error_shift import main
        monkeypatch.setattr(
            "sys.argv",
            ["analyze_error_shift.py",
             "--results-dir", str(tmp_path),
             "--base-results-dir", str(tmp_path)],
        )
        result = main()
        assert result == 1


# ---------------------------------------------------------------------------
# analyze_level_transfer.py (Conjecture 3)
# ---------------------------------------------------------------------------

class TestAnalyzeLevelTransfer:
    def test_accuracy_l3_nan_when_empty(self):
        from analyze_level_transfer import _accuracy_l3
        acc, c, n = _accuracy_l3([])
        assert math.isnan(acc)
        assert n == 0

    def test_accuracy_l3_correct(self):
        from analyze_level_transfer import _accuracy_l3
        evals = [_make_ft_eval(instance_id="bio-l3-001", correct=True)]
        acc, c, n = _accuracy_l3(evals)
        assert acc == pytest.approx(1.0)

    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_level_transfer import main
        monkeypatch.setattr(
            "sys.argv",
            ["analyze_level_transfer.py",
             "--results-dir", str(tmp_path),
             "--base-results-dir", str(tmp_path)],
        )
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_margin_effect.py (Conjecture 4)
# ---------------------------------------------------------------------------

class TestAnalyzeMarginEffect:
    def test_graded_score_distribution(self):
        from analyze_margin_effect import _graded_score_dist
        evals = [
            _make_ft_eval(instance_id="bio-l3-001", correct=True, graded_score=1.0),
            _make_ft_eval(instance_id="bio-l3-002", correct=False, graded_score=0.5),
        ]
        dist = _graded_score_dist(evals)
        assert dist.get(1.0, 0) == 1
        assert dist.get(0.5, 0) == 1

    def test_graded_score_dist_level2_excluded(self):
        from analyze_margin_effect import _graded_score_dist
        evals = [_make_ft_eval(graded_score=1.0)]  # level 2
        dist = _graded_score_dist(evals)
        assert sum(dist.values()) == 0

    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_margin_effect import main
        monkeypatch.setattr(
            "sys.argv",
            ["analyze_margin_effect.py",
             "--results-dir", str(tmp_path),
             "--base-results-dir", str(tmp_path)],
        )
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_curriculum.py
# ---------------------------------------------------------------------------

class TestAnalyzeCurriculum:
    def test_friedman_test_too_few_columns(self):
        from analyze_curriculum import _friedman_test
        result = _friedman_test([[0.5, 0.6]])  # only 2 columns, need >=3
        assert math.isnan(result["chi2"])

    def test_friedman_test_valid(self):
        from analyze_curriculum import _friedman_test
        data = [[0.5, 0.6, 0.7], [0.4, 0.5, 0.8]]
        result = _friedman_test(data)
        assert "chi2" in result and "p" in result

    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_curriculum import main
        monkeypatch.setattr("sys.argv", ["analyze_curriculum.py",
                                          "--results-dir", str(tmp_path)])
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_scaling_projections.py
# ---------------------------------------------------------------------------

class TestAnalyzeScalingProjections:
    def test_fit_loglinear_basic(self):
        from analyze_scaling_projections import _fit_loglinear
        # acc = 0.1 * log(f) + 0.5
        import math
        fracs = [0.1, 0.25, 0.5, 1.0]
        accs  = [0.1 * math.log(f) + 0.5 for f in fracs]
        a, b, r2 = _fit_loglinear(fracs, accs)
        assert abs(a - 0.1) < 0.01
        assert abs(b - 0.5) < 0.01
        assert r2 > 0.99

    def test_fit_loglinear_single_point(self):
        from analyze_scaling_projections import _fit_loglinear
        a, b, r2 = _fit_loglinear([1.0], [0.8])
        assert math.isnan(a)

    def test_fit_loglinear_constant(self):
        from analyze_scaling_projections import _fit_loglinear
        a, b, r2 = _fit_loglinear([0.5, 1.0], [0.8, 0.8])
        assert abs(a) < 1e-10  # slope should be ~0

    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_scaling_projections import main
        monkeypatch.setattr("sys.argv", ["analyze_scaling_projections.py",
                                          "--results-dir", str(tmp_path)])
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_novel_resolutions.py
# ---------------------------------------------------------------------------

class TestAnalyzeNovelResolutions:
    def test_main_no_results(self, tmp_path, monkeypatch):
        from analyze_novel_resolutions import main
        monkeypatch.setattr("sys.argv", ["analyze_novel_resolutions.py",
                                          "--results-dir", str(tmp_path),
                                          "--instances-dir", str(tmp_path)])
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_reward_fidelity.py
# ---------------------------------------------------------------------------

class TestAnalyzeRewardFidelity:
    def test_spearman_rho_perfect_rank(self):
        from analyze_reward_fidelity import _spearman_rho
        x = [1.0, 2.0, 3.0, 4.0]
        y = [1.0, 2.0, 3.0, 4.0]
        rho, p = _spearman_rho(x, y)
        assert abs(rho - 1.0) < 0.01

    def test_spearman_rho_perfect_inverse(self):
        from analyze_reward_fidelity import _spearman_rho
        x = [1.0, 2.0, 3.0, 4.0]
        y = [4.0, 3.0, 2.0, 1.0]
        rho, p = _spearman_rho(x, y)
        assert abs(rho + 1.0) < 0.01

    def test_spearman_rho_uncorrelated(self):
        from analyze_reward_fidelity import _spearman_rho
        x = [1.0, 3.0, 2.0, 4.0]
        y = [2.0, 4.0, 1.0, 3.0]
        rho, _ = _spearman_rho(x, y)
        assert -1.0 <= rho <= 1.0

    def test_main_missing_reward_model(self, tmp_path, monkeypatch):
        from analyze_reward_fidelity import main
        monkeypatch.setattr("sys.argv", [
            "analyze_reward_fidelity.py",
            "--reward-model", str(tmp_path / "nonexistent"),
            "--preference-data", str(tmp_path / "prefs.jsonl"),
        ])
        assert main() == 1

    def test_main_missing_preference_data(self, tmp_path, monkeypatch):
        from analyze_reward_fidelity import main
        reward_dir = tmp_path / "reward_model"
        reward_dir.mkdir()
        monkeypatch.setattr("sys.argv", [
            "analyze_reward_fidelity.py",
            "--reward-model", str(reward_dir),
            "--preference-data", str(tmp_path / "missing.jsonl"),
        ])
        assert main() == 1


# ---------------------------------------------------------------------------
# analyze_reward_overoptimization.py
# ---------------------------------------------------------------------------

class TestAnalyzeRewardOveroptimization:
    def test_main_missing_rlhf_dir_no_stats(self, tmp_path, monkeypatch):
        from analyze_reward_overoptimization import main
        rlhf_dir = tmp_path / "rlhf_run"
        rlhf_dir.mkdir()
        monkeypatch.setattr("sys.argv", [
            "analyze_reward_overoptimization.py",
            "--rlhf-checkpoint", str(rlhf_dir),
            "--results-dir", str(tmp_path),
        ])
        assert main() == 1

    def test_main_with_reward_stats_file(self, tmp_path, monkeypatch):
        from analyze_reward_overoptimization import main
        rlhf_dir = tmp_path / "rlhf_run"
        rlhf_dir.mkdir()
        stats = [
            {"step": 100, "mean_rm_score": 0.8, "mean_verifier_score": 0.6},
            {"step": 200, "mean_rm_score": 0.85, "mean_verifier_score": 0.62},
        ]
        (rlhf_dir / "reward_stats.json").write_text(json.dumps(stats))
        monkeypatch.setattr("sys.argv", [
            "analyze_reward_overoptimization.py",
            "--rlhf-checkpoint", str(rlhf_dir),
            "--results-dir", str(tmp_path),
        ])
        assert main() == 0
