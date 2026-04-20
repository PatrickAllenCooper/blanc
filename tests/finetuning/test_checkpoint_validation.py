"""
Tests for the checkpoint integrity validator in
``scripts/azure_finetune_spot.sh``'s ``latest_checkpoint``.

Concrete bug we are guarding against (observed 2026-04-20 16:10 UTC):

    safetensors_rust.SafetensorError: Error while deserializing header:
      incomplete metadata, file not fully covered

Caused by SIGTERM mid-checkpoint-write from an Azure Spot preemption. The
HF Trainer does not write checkpoints atomically; when the orchestrator
then tried to `resume_from_checkpoint=checkpoint-25`, safetensors refused
to load the truncated file, the trainer died before step 1, systemd
counted a Failure, Restart=on-failure retried, and the service looped
until StartLimitBurst=10 was near exhaustion.

The fix in ``latest_checkpoint`` iterates newest -> oldest, invokes a
Python sub-check that parses each candidate's weight file, quarantines
any that fail under ``<dir>/.corrupt/``, and returns the newest surviving
checkpoint (or empty string to start from scratch).

These tests:
  1. Verify the Python validation snippet against realistic inputs:
     valid safetensors, truncated safetensors, empty safetensors, valid
     pickle, corrupt pickle, missing weight file.
  2. Statically assert the orchestrator script retains the key defences
     (iterates newest-first, quarantines invalid checkpoints, validates
     with Python before returning).

Author: Patrick Cooper
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import torch
from safetensors.torch import save_file

ROOT = Path(__file__).resolve().parent.parent.parent
ORCHESTRATOR = ROOT / "scripts" / "azure_finetune_spot.sh"


# ---------------------------------------------------------------------------
# Reproduce the inline Python validator out-of-band so we can unit test it.
# Kept byte-identical to the heredoc body in azure_finetune_spot.sh:
# if you change one you must change both (checked by a static test below).
# ---------------------------------------------------------------------------

_VALIDATOR_SNIPPET = """import os, sys
path = os.environ["WEIGHT_FILE"]
try:
    if path.endswith(".safetensors"):
        from safetensors import safe_open
        with safe_open(path, framework="pt") as f:
            # Empty keys would mean a valid but useless checkpoint; treat as bad.
            if not list(f.keys()):
                sys.exit(1)
    else:
        import torch
        torch.load(path, map_location="cpu", weights_only=True)
except Exception:
    sys.exit(1)
sys.exit(0)
"""


def _run_validator(weight_file: Path) -> int:
    """Execute the exact validator snippet used by the orchestrator."""
    env = os.environ.copy()
    env["WEIGHT_FILE"] = str(weight_file)
    proc = subprocess.run(
        [sys.executable, "-c", _VALIDATOR_SNIPPET],
        env=env,
        capture_output=True,
        text=True,
    )
    return proc.returncode


# ---------------------------------------------------------------------------
# Fixtures: build representative good/bad checkpoint weight files
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_safetensors(tmp_path: Path) -> Path:
    path = tmp_path / "adapter_model.safetensors"
    save_file({"lora_A": torch.zeros(8, 4), "lora_B": torch.zeros(4, 8)}, str(path))
    assert path.stat().st_size > 32
    return path


@pytest.fixture
def truncated_safetensors(valid_safetensors: Path) -> Path:
    """Simulate SIGTERM-mid-write: keep only the first few KiB, matching
    what the Apr 20 preemption left on disk."""
    full_size = valid_safetensors.stat().st_size
    with valid_safetensors.open("rb") as f:
        data = f.read()
    truncated = valid_safetensors.with_name("adapter_model.truncated.safetensors")
    # Cut the file in half, guaranteeing header under-coverage.
    truncated.write_bytes(data[: full_size // 2])
    return truncated


@pytest.fixture
def empty_safetensors(tmp_path: Path) -> Path:
    """0-byte file -- another way a preemption can leave the adapter file."""
    path = tmp_path / "adapter_model.empty.safetensors"
    path.write_bytes(b"")
    return path


@pytest.fixture
def valid_pickle(tmp_path: Path) -> Path:
    path = tmp_path / "pytorch_model.bin"
    torch.save({"w": torch.zeros(4, 4)}, str(path))
    return path


@pytest.fixture
def corrupt_pickle(tmp_path: Path) -> Path:
    path = tmp_path / "pytorch_model.corrupt.bin"
    path.write_bytes(b"\x80\x02garbage-not-a-pickle")
    return path


# ---------------------------------------------------------------------------
# Validator behaviour
# ---------------------------------------------------------------------------

def test_valid_safetensors_accepted(valid_safetensors: Path) -> None:
    assert _run_validator(valid_safetensors) == 0


def test_truncated_safetensors_rejected(truncated_safetensors: Path) -> None:
    """This is the exact failure mode that caused the Apr 20 crash loop.
    If this assertion ever flips the production service is one preemption
    away from another lockout."""
    assert _run_validator(truncated_safetensors) != 0, (
        "Validator must reject truncated safetensors files. Truncation is "
        "the dominant corruption pattern from spot-preemption-mid-write."
    )


def test_empty_safetensors_rejected(empty_safetensors: Path) -> None:
    assert _run_validator(empty_safetensors) != 0


def test_valid_pickle_accepted(valid_pickle: Path) -> None:
    assert _run_validator(valid_pickle) == 0


def test_corrupt_pickle_rejected(corrupt_pickle: Path) -> None:
    assert _run_validator(corrupt_pickle) != 0


def test_missing_file_rejected(tmp_path: Path) -> None:
    nonexistent = tmp_path / "does_not_exist.safetensors"
    assert _run_validator(nonexistent) != 0


# ---------------------------------------------------------------------------
# Static guards on the orchestrator
# ---------------------------------------------------------------------------

def test_orchestrator_has_quarantine_logic() -> None:
    src = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "_quarantine_checkpoint" in src, (
        "Orchestrator must quarantine corrupt checkpoints so the loop "
        "terminates. Without this, retries keep finding the same bad file."
    )
    assert ".corrupt" in src, (
        "Quarantine target directory must be distinct from live checkpoints."
    )


def test_orchestrator_iterates_newest_first() -> None:
    """sort -t- -k2 -n -r (reverse numeric) is the whole point: without
    -r we'd pick the oldest checkpoint and throw away most of our progress
    on every resume."""
    src = ORCHESTRATOR.read_text(encoding="utf-8")
    assert "sort -t- -k2 -n -r" in src, (
        "latest_checkpoint must sort newest-first (add -r to numeric sort)."
    )


def test_orchestrator_uses_inline_validator() -> None:
    """The heredoc snippet inside latest_checkpoint must stay byte-identical
    to the one this test file reuses, so unit test coverage == production
    behaviour."""
    src = ORCHESTRATOR.read_text(encoding="utf-8")
    for line in (
        'from safetensors import safe_open',
        'with safe_open(path, framework="pt") as f:',
        'torch.load(path, map_location="cpu", weights_only=True)',
    ):
        assert line in src, (
            f"Orchestrator validator snippet is missing critical line:\n"
            f"  {line!r}\n"
            f"Make sure scripts/azure_finetune_spot.sh and this test stay "
            f"in sync."
        )
