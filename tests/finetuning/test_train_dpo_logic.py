"""
Tests for data loading, curriculum logic, and MarginDPOTrainer in train_dpo.py.

GPU-dependent code (actual training, model loading) is not tested here.
Tests cover pure-Python logic: JSONL loading, curriculum filtering,
data fraction subsampling, and the MarginDPOTrainer class structure.

Author: Patrick Cooper
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "finetuning"))

# TRL and torch must both be present for the training module to import
trl   = pytest.importorskip("trl",   reason="trl not installed — training tests skipped")
torch = pytest.importorskip("torch", reason="torch not installed — training tests skipped")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_pair(
    prompt: str = "p",
    chosen: str = "y_w",
    rejected: str = "y_l",
    margin: float = 1.0,
    level: int = 2,
    instance_id: str = "inst-001",
) -> dict:
    return {
        "prompt":       prompt,
        "chosen":       chosen,
        "rejected":     rejected,
        "margin":       margin,
        "level":        level,
        "instance_id":  instance_id,
    }


@pytest.fixture
def pref_jsonl(tmp_path):
    pairs = [
        _make_pair(level=2, instance_id=f"l2-{i:03d}") for i in range(10)
    ] + [
        _make_pair(level=3, instance_id=f"l3-{i:03d}") for i in range(4)
    ]
    path = tmp_path / "preferences_Qwen_Qwen2.5-72B-Instruct-AWQ.jsonl"
    path.write_text("\n".join(json.dumps(p) for p in pairs))
    return tmp_path


# ---------------------------------------------------------------------------
# _load_jsonl
# ---------------------------------------------------------------------------

class TestLoadJsonl:
    def test_loads_valid_jsonl(self, tmp_path):
        from train_dpo import _load_jsonl
        path = tmp_path / "data.jsonl"
        path.write_text('{"a": 1}\n{"a": 2}\n')
        records = _load_jsonl(path)
        assert len(records) == 2
        assert records[0]["a"] == 1

    def test_skips_blank_lines(self, tmp_path):
        from train_dpo import _load_jsonl
        path = tmp_path / "data.jsonl"
        path.write_text('{"a": 1}\n\n{"a": 2}\n\n')
        records = _load_jsonl(path)
        assert len(records) == 2


# ---------------------------------------------------------------------------
# _load_preference_data — curriculum modes
# ---------------------------------------------------------------------------

class TestLoadPreferenceDataCurricula:
    def test_joint_curriculum_keeps_all(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        total = len(train) + len(val)
        assert total == 14  # 10 L2 + 4 L3

    def test_weighted_curriculum_repeats_l3(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(pref_jsonl, "weighted", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        total = len(train) + len(val)
        # 10 other + 4*5 L3 = 30 pairs
        assert total == 30

    def test_l12_only_curriculum_excludes_l3(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(pref_jsonl, "l12_only", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        total = len(train) + len(val)
        assert total == 10  # only L2

    def test_sequential_curriculum_keeps_all(self, pref_jsonl):
        from train_dpo import _load_preference_data
        # "sequential" is not a weighting strategy — it's handled externally (via warmup),
        # so the data count should be the same as joint
        train, val = _load_preference_data(pref_jsonl, "sequential", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        total = len(train) + len(val)
        assert total == 14

    def test_data_fraction_reduces_count(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(
            pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ",
            data_fraction=0.5,
        )
        total = len(train) + len(val)
        assert total < 14

    def test_data_fraction_1_keeps_all(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train_full, val_full = _load_preference_data(
            pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ"
        )
        train_frac, val_frac = _load_preference_data(
            pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ",
            data_fraction=1.0,
        )
        assert len(train_full) + len(val_full) == len(train_frac) + len(val_frac)

    def test_no_matching_file_raises(self, tmp_path):
        from train_dpo import _load_preference_data
        with pytest.raises(FileNotFoundError):
            _load_preference_data(tmp_path, "joint", "SomeModel")

    def test_val_split_is_nonempty(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        assert len(val) > 0

    def test_dataset_has_required_columns(self, pref_jsonl):
        from train_dpo import _load_preference_data
        train, val = _load_preference_data(pref_jsonl, "joint", "Qwen/Qwen2.5-72B-Instruct-AWQ")
        for col in ("prompt", "chosen", "rejected", "margins"):
            assert col in train.column_names

    def test_fallback_to_any_preferences_file(self, tmp_path):
        from train_dpo import _load_preference_data
        pairs = [_make_pair() for _ in range(5)]
        (tmp_path / "preferences_OtherModel.jsonl").write_text(
            "\n".join(json.dumps(p) for p in pairs)
        )
        # Should find the only preferences_*.jsonl
        train, val = _load_preference_data(tmp_path, "joint", "TargetModel")
        assert len(train) + len(val) == 5


# ---------------------------------------------------------------------------
# MarginDPOTrainer class structure (no GPU required)
# ---------------------------------------------------------------------------

class TestMarginDPOTrainer:
    def test_trainer_class_exists(self):
        from train_dpo import MarginDPOTrainer
        assert MarginDPOTrainer is not None

    def test_trainer_inherits_from_dpo_trainer(self):
        from train_dpo import MarginDPOTrainer
        from trl import DPOTrainer
        assert issubclass(MarginDPOTrainer, DPOTrainer)

    def test_trainer_has_gamma_attribute(self):
        from train_dpo import MarginDPOTrainer
        # We can't instantiate without a model, but we can inspect the signature
        import inspect
        sig = inspect.signature(MarginDPOTrainer.__init__)
        assert "gamma" in sig.parameters

    def test_dpo_loss_override_exists(self):
        from train_dpo import MarginDPOTrainer
        assert hasattr(MarginDPOTrainer, "dpo_loss")
        assert callable(MarginDPOTrainer.dpo_loss)

    def test_get_batch_loss_metrics_override_exists(self):
        from train_dpo import MarginDPOTrainer
        assert hasattr(MarginDPOTrainer, "get_batch_loss_metrics")

    def test_dpo_loss_applies_margin_shift(self):
        """Test dpo_loss formula without actual training: additive margin shift."""
        import torch
        from train_dpo import MarginDPOTrainer

        # Instantiate a minimal mock trainer
        trainer = object.__new__(MarginDPOTrainer)
        trainer.gamma = 2.0
        trainer.beta  = 0.1
        trainer._margins_buffer = None

        policy_chosen_logps   = torch.tensor([0.8])
        policy_rejected_logps = torch.tensor([0.3])
        ref_chosen_logps      = torch.tensor([0.5])
        ref_rejected_logps    = torch.tensor([0.2])

        losses, chosen_r, rejected_r = trainer.dpo_loss(
            policy_chosen_logps, policy_rejected_logps,
            ref_chosen_logps, ref_rejected_logps,
        )
        assert losses.shape == (1,)
        assert chosen_r.shape == (1,)
        assert rejected_r.shape == (1,)
        # Without margin, loss should be positive (model prefers chosen)
        assert losses.item() > 0

    def test_dpo_loss_with_margin_applied(self):
        """With gamma>0 and a margin, logit should be shifted."""
        import torch
        from train_dpo import MarginDPOTrainer

        trainer = object.__new__(MarginDPOTrainer)
        trainer.gamma = 2.0
        trainer.beta  = 0.1
        # Set a margin buffer (delta_r = 0.5)
        trainer._margins_buffer = torch.tensor([0.5])

        policy_chosen_logps   = torch.tensor([0.8])
        policy_rejected_logps = torch.tensor([0.3])
        ref_chosen_logps      = torch.tensor([0.5])
        ref_rejected_logps    = torch.tensor([0.2])

        losses_with_margin, _, _ = trainer.dpo_loss(
            policy_chosen_logps, policy_rejected_logps,
            ref_chosen_logps, ref_rejected_logps,
        )
        # After consuming the margin buffer, it should be None
        assert trainer._margins_buffer is None

        # Recompute without margin for comparison
        trainer._margins_buffer = None
        losses_without, _, _ = trainer.dpo_loss(
            policy_chosen_logps, policy_rejected_logps,
            ref_chosen_logps, ref_rejected_logps,
        )

        # With positive margin and gamma=2.0, logit decreases, so loss increases
        assert losses_with_margin.item() > losses_without.item()
