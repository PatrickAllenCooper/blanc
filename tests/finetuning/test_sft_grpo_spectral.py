"""
Tests for SFT data preparation, GRPO reward wrapping, spectral LoRA
initialization, and parameter sparsity analysis.

GPU-dependent code (actual training) is not tested.  Tests cover
pure-Python logic: data formatting, reward function interface,
spectral initialization mathematics, and sparsity metrics.

Author: Patrick Cooper
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "finetuning"))

from blanc.author.generation import AbductiveInstance
from blanc.core.theory import Theory, Rule, RuleType


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_instance(
    target: str = "flies(tweety)",
    candidates: list = None,
    gold: list = None,
    level: int = 2,
    domain: str = "biology",
    inst_id: str = "bio-l2-001",
) -> AbductiveInstance:
    theory = Theory()
    theory.add_fact("bird(tweety)")
    inst = AbductiveInstance(
        D_minus=theory,
        target=target,
        candidates=candidates or ["flies(tweety)", "swims(tweety)"],
        gold=gold or ["flies(tweety)"],
        level=level,
        metadata={"domain": domain},
    )
    inst.id = inst_id
    return inst


def _make_instances(n_l2: int = 6, n_l3: int = 2) -> list:
    insts = []
    for i in range(n_l2):
        insts.append(_make_instance(level=2, inst_id=f"bio-l2-{i:03d}"))
    for i in range(n_l3):
        inst = _make_instance(
            level=3,
            inst_id=f"l3-test-{i:03d}",
            gold=["d_penguin: penguin(X) ~> ~flies(X)"],
        )
        insts.append(inst)
    return insts


# ===========================================================================
# SFT Data Preparation Tests
# ===========================================================================

class TestPrepareSFTData:
    """Tests for prepare_sft_data.py."""

    def test_encode_gold_hypothesis_m4(self):
        from prepare_sft_data import encode_gold_hypothesis
        inst = _make_instance(gold=["flies(tweety)"])
        result = encode_gold_hypothesis(inst, "M4")
        assert result is not None
        assert "flies(tweety)" in result

    def test_encode_gold_hypothesis_none_when_empty(self):
        from prepare_sft_data import encode_gold_hypothesis
        theory = Theory()
        theory.add_fact("bird(tweety)")
        inst = AbductiveInstance(
            D_minus=theory,
            target="flies(tweety)",
            candidates=["flies(tweety)"],
            gold=[],
            level=2,
            metadata={"domain": "biology"},
        )
        inst.id = "empty-gold"
        result = encode_gold_hypothesis(inst, "M4")
        assert result is None

    def test_build_sft_dataset_joint(self):
        from prepare_sft_data import build_sft_dataset
        instances = _make_instances(n_l2=4, n_l3=2)
        records = build_sft_dataset(instances, ["M4"], ["direct"], "joint")
        assert len(records) == 6
        for r in records:
            assert r.prompt
            assert r.completion
            assert r.modality == "M4"
            assert r.strategy == "direct"

    def test_build_sft_dataset_weighted(self):
        from prepare_sft_data import build_sft_dataset
        instances = _make_instances(n_l2=4, n_l3=2)
        records = build_sft_dataset(instances, ["M4"], ["direct"], "weighted")
        l3_count = sum(1 for r in records if r.level == 3)
        assert l3_count == 10  # 2 * 5x oversampling

    def test_build_sft_dataset_l12_only(self):
        from prepare_sft_data import build_sft_dataset
        instances = _make_instances(n_l2=4, n_l3=2)
        records = build_sft_dataset(instances, ["M4"], ["direct"], "l12_only")
        assert all(r.level != 3 for r in records)
        assert len(records) == 4

    def test_build_sft_dataset_multiple_modalities(self):
        from prepare_sft_data import build_sft_dataset
        instances = _make_instances(n_l2=2, n_l3=0)
        records = build_sft_dataset(instances, ["M4", "M2"], ["direct"], "joint")
        assert len(records) == 4  # 2 instances x 2 modalities

    def test_sft_record_fields(self):
        from prepare_sft_data import build_sft_dataset, SFTRecord
        instances = _make_instances(n_l2=1, n_l3=0)
        records = build_sft_dataset(instances, ["M4"], ["direct"], "joint")
        r = records[0]
        assert isinstance(r, SFTRecord)
        assert r.instance_id == "bio-l2-000"
        assert r.level == 2
        assert r.domain == "biology"


# ===========================================================================
# GRPO Reward Function Tests
# ===========================================================================

_has_trl = True
try:
    import trl  # noqa: F401
except ImportError:
    _has_trl = False


@pytest.mark.skipif(not _has_trl, reason="trl not installed")
class TestGRPOReward:
    """Tests for the DeFAbRewardFunction in train_grpo.py."""

    def _make_reward_fn(self, instances, mock_decoder):
        from train_grpo import DeFAbRewardFunction
        reward_fn = DeFAbRewardFunction.__new__(DeFAbRewardFunction)
        reward_fn.decoder = mock_decoder
        reward_fn.l3_evaluator = MagicMock()
        reward_fn._instance_map = {
            getattr(i, "id", f"inst-{j}"): i
            for j, i in enumerate(instances)
        }
        return reward_fn

    def test_reward_function_correct_answer(self):
        instances = [_make_instance(inst_id="test-001", gold=["flies(tweety)"])]
        mock_decoder = MagicMock()
        mock_decoder.decode.return_value = ("flies(tweety)", "D1")
        reward_fn = self._make_reward_fn(instances, mock_decoder)

        completions = [[{"role": "assistant", "content": "flies(tweety)"}]]
        scores = reward_fn(completions, ["prompt"], ["test-001"])
        assert scores == [1.0]

    def test_reward_function_wrong_answer(self):
        instances = [_make_instance(inst_id="test-001", gold=["flies(tweety)"])]
        mock_decoder = MagicMock()
        mock_decoder.decode.return_value = ("swims(tweety)", "D1")
        reward_fn = self._make_reward_fn(instances, mock_decoder)

        completions = [[{"role": "assistant", "content": "swims(tweety)"}]]
        scores = reward_fn(completions, ["prompt"], ["test-001"])
        assert scores == [0.0]

    def test_reward_function_decode_failure(self):
        instances = [_make_instance(inst_id="test-001")]
        mock_decoder = MagicMock()
        mock_decoder.decode.side_effect = Exception("decode error")
        reward_fn = self._make_reward_fn(instances, mock_decoder)

        completions = [[{"role": "assistant", "content": "garbage"}]]
        scores = reward_fn(completions, ["prompt"], ["test-001"])
        assert scores == [0.0]

    def test_reward_function_unknown_instance(self):
        mock_decoder = MagicMock()
        reward_fn = self._make_reward_fn([], mock_decoder)

        completions = [[{"role": "assistant", "content": "anything"}]]
        scores = reward_fn(completions, ["prompt"], ["nonexistent"])
        assert scores == [0.0]


# ===========================================================================
# Spectral LoRA Initialization Tests
# ===========================================================================

torch = pytest.importorskip("torch", reason="torch not installed")


class TestSpectralLoRA:
    """Tests for spectral_lora.py."""

    def test_compute_spectral_metrics_identity(self):
        from spectral_lora import compute_spectral_metrics
        W = torch.eye(4)
        metrics = compute_spectral_metrics(W)
        assert abs(metrics["frobenius_norm"] - 2.0) < 1e-5  # sqrt(4) = 2
        assert abs(metrics["spectral_norm"] - 1.0) < 1e-5
        assert len(metrics["singular_values"]) == 4
        assert all(abs(s - 1.0) < 1e-5 for s in metrics["singular_values"])

    def test_compute_spectral_metrics_rank1(self):
        from spectral_lora import compute_spectral_metrics
        W = torch.tensor([[1.0, 0.0], [0.0, 0.0]])
        metrics = compute_spectral_metrics(W)
        assert abs(metrics["effective_rank"] - 1.0) < 1e-3
        assert metrics["spectral_entropy"] < 1e-5  # only one nonzero SV

    def test_compute_spectral_metrics_zero_matrix(self):
        from spectral_lora import compute_spectral_metrics
        W = torch.zeros(3, 3)
        metrics = compute_spectral_metrics(W)
        assert metrics["frobenius_norm"] == 0.0
        assert metrics["effective_rank"] == 0.0

    def test_compute_spectral_metrics_high_rank(self):
        from spectral_lora import compute_spectral_metrics
        torch.manual_seed(42)
        W = torch.randn(10, 10)
        metrics = compute_spectral_metrics(W)
        assert metrics["effective_rank"] > 1.0
        assert metrics["frobenius_norm"] > 0.0

    def test_spectral_entropy_bounds(self):
        from spectral_lora import compute_spectral_metrics
        W = torch.eye(5)
        metrics = compute_spectral_metrics(W)
        assert metrics["spectral_entropy"] >= 0.0
        assert metrics["effective_rank"] <= 5.0

    def test_l0_sparsity_sparse_matrix(self):
        from spectral_lora import compute_spectral_metrics
        W = torch.zeros(10, 10)
        W[0, 0] = 1.0
        metrics = compute_spectral_metrics(W)
        assert metrics["l0_sparsity"] > 0.9  # mostly zeros


# ===========================================================================
# Parameter Sparsity Analysis Tests
# ===========================================================================

class TestParameterSparsityAnalysis:
    """Tests for analyze_parameter_sparsity.py."""

    def test_compare_methods_format(self):
        from analyze_parameter_sparsity import compare_methods
        analyses = {
            "dpo_standard": {
                "num_layers": 7,
                "mean_frobenius_norm": 0.123,
                "mean_effective_rank": 3.5,
                "mean_l0_sparsity": 0.95,
                "mean_spectral_entropy": 1.2,
                "std_effective_rank": 0.5,
            },
            "grpo_joint": {
                "num_layers": 7,
                "mean_frobenius_norm": 0.045,
                "mean_effective_rank": 1.8,
                "mean_l0_sparsity": 0.98,
                "mean_spectral_entropy": 0.6,
                "std_effective_rank": 0.3,
            },
        }
        table = compare_methods(analyses)
        assert "dpo_standard" in table
        assert "grpo_joint" in table

    def test_generate_latex_table(self):
        from analyze_parameter_sparsity import generate_latex_table
        analyses = {
            "sft_joint": {
                "num_layers": 7,
                "mean_frobenius_norm": 0.08,
                "mean_effective_rank": 2.1,
                "mean_l0_sparsity": 0.97,
                "mean_spectral_entropy": 0.8,
            },
        }
        latex = generate_latex_table(analyses)
        assert r"\begin{table}" in latex
        assert "sft" in latex.replace(r"\_", "_")
        assert r"\end{table}" in latex

    def test_find_checkpoints_empty(self, tmp_path):
        from analyze_parameter_sparsity import find_checkpoints
        result = find_checkpoints(tmp_path)
        assert result == {}

    def test_find_checkpoints_discovers(self, tmp_path):
        from analyze_parameter_sparsity import find_checkpoints
        ckpt = tmp_path / "dpo_standard_qwen72b" / "final"
        ckpt.mkdir(parents=True)
        result = find_checkpoints(tmp_path)
        assert "dpo_standard_qwen72b" in result

    def test_analyze_checkpoint_no_weights(self, tmp_path):
        from analyze_parameter_sparsity import analyze_checkpoint
        result = analyze_checkpoint(tmp_path)
        assert "error" in result


# ===========================================================================
# SFT Dataset I/O Tests
# ===========================================================================

class TestSFTDataIO:
    """Tests for SFT JSONL read/write round-trip."""

    def test_sft_jsonl_roundtrip(self, tmp_path):
        from prepare_sft_data import build_sft_dataset, SFTRecord
        from dataclasses import asdict

        instances = _make_instances(n_l2=2, n_l3=1)
        records = build_sft_dataset(instances, ["M4"], ["direct"], "joint")

        out_file = tmp_path / "sft_train.jsonl"
        with open(out_file, "w") as f:
            for r in records:
                f.write(json.dumps(asdict(r)) + "\n")

        loaded = []
        with open(out_file) as f:
            for line in f:
                loaded.append(json.loads(line.strip()))

        assert len(loaded) == len(records)
        for orig, load in zip(records, loaded):
            assert load["prompt"] == orig.prompt
            assert load["completion"] == orig.completion
            assert load["level"] == orig.level
