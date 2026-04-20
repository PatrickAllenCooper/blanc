"""
Static guards against the canonical QLoRA + gradient-checkpointing regression.

Symptom we are protecting against, observed on Azure 2x A100 with Qwen2.5-72B
4-bit + LoRA + DDP + gradient checkpointing:

    UserWarning: None of the inputs have requires_grad=True. Gradients will be None
    RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn

Cause: when the base model is frozen (4-bit / quantized), its embedding output
loses ``requires_grad=True`` after gradient checkpointing recomputation, so
the autograd graph breaks before reaching the LoRA adapters and ``loss.backward()``
fails on the very first training step.

Fix (must be present in every script that loads a quantized base + applies LoRA
with gradient checkpointing enabled):

  1. ``prepare_model_for_kbit_training(model, use_gradient_checkpointing=True,
     gradient_checkpointing_kwargs={"use_reentrant": False})`` BEFORE
     ``get_peft_model`` when ``bnb_config is not None``.
  2. ``model.enable_input_require_grads()`` AFTER ``get_peft_model`` (covers
     the AWQ branch where step 1 is skipped).
  3. ``gradient_checkpointing_kwargs={"use_reentrant": False}`` passed to
     the trainer config.

Loading the actual model needs a GPU and tens of GB of weights, so these tests
parse the source files instead. They run in <50 ms and break the build the
moment any of the three guards is removed.

Author: Patrick Cooper
"""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "experiments" / "finetuning"

# (path, requires_kbit_prep): rlhf_vitl loads classification head; GRPO defers
# model loading to TRL which does kbit prep internally and is exempt.
QLORA_TRAINING_SCRIPTS = [
    (SCRIPTS / "train_sft.py",        True),
    (SCRIPTS / "train_dpo.py",        True),
    (SCRIPTS / "train_rlhf_vitl.py",  True),
    (SCRIPTS / "train_grpo.py",       False),
]


def _read(path: Path) -> str:
    assert path.exists(), f"missing training script: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.parametrize("path,requires_kbit_prep", QLORA_TRAINING_SCRIPTS)
def test_non_reentrant_grad_checkpointing(path: Path, requires_kbit_prep: bool) -> None:
    """Trainer config must request use_reentrant=False or backward will silently
    drop the LoRA grads on quantized bases."""
    src = _read(path)
    assert 'gradient_checkpointing_kwargs={"use_reentrant": False}' in src, (
        f"{path.name}: missing gradient_checkpointing_kwargs={{'use_reentrant': False}}. "
        "Required for PEFT + gradient checkpointing on a quantized base."
    )


@pytest.mark.parametrize("path,requires_kbit_prep", [
    p for p in QLORA_TRAINING_SCRIPTS if p[1]
])
def test_prepare_model_for_kbit_training_imported(path: Path, requires_kbit_prep: bool) -> None:
    """The fix requires importing prepare_model_for_kbit_training from peft."""
    src = _read(path)
    assert "prepare_model_for_kbit_training" in src, (
        f"{path.name}: prepare_model_for_kbit_training is not imported or used. "
        "QLoRA backward will fail on the first step without it."
    )


@pytest.mark.parametrize("path,requires_kbit_prep", [
    p for p in QLORA_TRAINING_SCRIPTS if p[1]
])
def test_prepare_model_for_kbit_training_invoked_under_4bit(
    path: Path,
    requires_kbit_prep: bool,
) -> None:
    """It must be CALLED, not just imported, and gated behind the bnb_config."""
    src = _read(path)
    assert "prepare_model_for_kbit_training(" in src, (
        f"{path.name}: prepare_model_for_kbit_training is imported but never called."
    )
    # Must appear inside an ``if bnb_config is not None`` (or equivalent guarded)
    # block to keep the AWQ / non-quantized path working.
    lines = src.splitlines()
    saw_guard_then_call = False
    for i, line in enumerate(lines):
        if "if bnb_config is not None" in line:
            for j in range(i + 1, min(i + 12, len(lines))):
                if "prepare_model_for_kbit_training(" in lines[j]:
                    saw_guard_then_call = True
                    break
        if saw_guard_then_call:
            break
    assert saw_guard_then_call, (
        f"{path.name}: prepare_model_for_kbit_training must be invoked inside an "
        "`if bnb_config is not None:` block so AWQ models still work."
    )


@pytest.mark.parametrize("path,requires_kbit_prep", [
    p for p in QLORA_TRAINING_SCRIPTS if p[1]
])
def test_enable_input_require_grads_called(path: Path, requires_kbit_prep: bool) -> None:
    """Belt-and-braces guard for AWQ path that skips kbit_training prep."""
    src = _read(path)
    assert "enable_input_require_grads" in src, (
        f"{path.name}: model.enable_input_require_grads() is missing. "
        "Required for the AWQ branch where prepare_model_for_kbit_training is skipped."
    )
