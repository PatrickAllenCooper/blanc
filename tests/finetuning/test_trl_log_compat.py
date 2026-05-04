"""
Tests for the transformers>=4.43 / TRL ``Trainer.log`` signature-drift shim.

Symptom we are protecting against, observed on Azure 2x A100 with Qwen2.5-72B
running DPO after the QLoRA + grad-checkpointing fix landed:

    File "transformers/trainer.py", line 3043, in _maybe_log_save_evaluate
        self.log(logs, start_time)
    TypeError: DPOTrainer.log() takes 2 positional arguments but 3 were given

The shim lives at ``experiments/finetuning/_trl_compat.py``.  These tests:
  1. Verify the shim's wrapping logic against synthetic classes that mimic
     both the old (logs only) and new (logs + start_time) signatures.
  2. Verify each at-risk training script imports the shim so the patch is
     active before any trainer is instantiated.

Author: Anonymous Authors
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "experiments" / "finetuning"
sys.path.insert(0, str(SCRIPTS))


# ---------------------------------------------------------------------------
# Unit tests for the wrapping logic
# ---------------------------------------------------------------------------

class _OldStyleTrainer:
    """Mimics a TRL trainer whose ``log`` only takes ``(self, logs)``."""
    calls: list = []

    def log(self, logs):
        self.calls.append(("old", logs))


class _NewStyleTrainer:
    """Mimics a transformers Trainer whose ``log`` accepts ``start_time``."""
    calls: list = []

    def log(self, logs, start_time=None):
        self.calls.append(("new", logs, start_time))


class _VarArgsTrainer:
    """Mimics a TRL trainer that already accepts ``*args, **kwargs``."""
    calls: list = []

    def log(self, logs, *args, **kwargs):
        self.calls.append(("varargs", logs, args, kwargs))


def _fresh_compat():
    """Re-import the compat module so each test has a clean patch slate."""
    if "_trl_compat" in sys.modules:
        del sys.modules["_trl_compat"]
    return importlib.import_module("_trl_compat")


def test_wrap_log_drops_extra_positional_for_old_style() -> None:
    compat = _fresh_compat()
    _OldStyleTrainer.calls = []
    if hasattr(_OldStyleTrainer, compat._PATCHED_FLAG):
        delattr(_OldStyleTrainer, compat._PATCHED_FLAG)

    compat._wrap_log(_OldStyleTrainer)

    instance = _OldStyleTrainer()
    instance.log({"loss": 1.0}, "ignored_start_time")

    assert _OldStyleTrainer.calls == [("old", {"loss": 1.0})], (
        "Wrapper should silently drop extra positional args before calling "
        "the original log() that does not accept them."
    )


def test_wrap_log_forwards_extra_positional_for_new_style() -> None:
    compat = _fresh_compat()
    _NewStyleTrainer.calls = []
    if hasattr(_NewStyleTrainer, compat._PATCHED_FLAG):
        delattr(_NewStyleTrainer, compat._PATCHED_FLAG)

    compat._wrap_log(_NewStyleTrainer)

    instance = _NewStyleTrainer()
    instance.log({"loss": 1.0}, 12345)

    assert _NewStyleTrainer.calls == [("new", {"loss": 1.0}, 12345)], (
        "Wrapper should forward extra args when the original log() accepts them."
    )


def test_wrap_log_is_idempotent() -> None:
    compat = _fresh_compat()
    if hasattr(_VarArgsTrainer, compat._PATCHED_FLAG):
        delattr(_VarArgsTrainer, compat._PATCHED_FLAG)

    original = _VarArgsTrainer.log
    compat._wrap_log(_VarArgsTrainer)
    compat._wrap_log(_VarArgsTrainer)
    compat._wrap_log(_VarArgsTrainer)

    assert getattr(_VarArgsTrainer, compat._PATCHED_FLAG) is True
    assert _VarArgsTrainer.log is original, (
        "Class that already accepts *args should not be re-wrapped."
    )


def test_wrap_log_handles_missing_log_method() -> None:
    """Subclasses that do not override log themselves should be a no-op."""
    compat = _fresh_compat()

    class _NoOverride:
        pass

    compat._wrap_log(_NoOverride)
    assert getattr(_NoOverride, compat._PATCHED_FLAG) is True
    assert "log" not in _NoOverride.__dict__


# ---------------------------------------------------------------------------
# Static guards: every training script that uses TRL must import the shim
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("script", [
    "train_sft.py",
    "train_dpo.py",
    "train_grpo.py",
    "train_rlhf_vitl.py",
])
def test_training_script_imports_trl_compat(script: str) -> None:
    src = (SCRIPTS / script).read_text(encoding="utf-8")
    assert "_trl_compat" in src, (
        f"{script}: must import experiments/finetuning/_trl_compat.py before "
        "instantiating any TRL trainer, or transformers>=4.43 will crash on "
        "the first logging_steps interval with: 'TypeError: ...Trainer.log() "
        "takes 2 positional arguments but 3 were given'."
    )
