"""Tests for experiments.math_topology.train_lakatos (the M2 driver)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.train_lakatos import maybe_run_training, prepare_artifacts  # noqa: E402


class TestPrepareArtifacts:
    def test_artifacts_created(self, tmp_path: Path) -> None:
        artifacts = prepare_artifacts(tmp_path)
        assert artifacts.sft_path.exists()
        assert artifacts.dpo_path.exists()
        assert artifacts.n_sft > 0
        assert artifacts.n_dpo > 0

    def test_artifacts_are_jsonl(self, tmp_path: Path) -> None:
        artifacts = prepare_artifacts(tmp_path)
        for path in (artifacts.sft_path, artifacts.dpo_path):
            content = path.read_text()
            assert content.strip()
            for line in content.splitlines():
                if line.strip():
                    assert line.startswith("{") and line.endswith("}")


class TestMaybeRunTraining:
    def test_dry_run_returns_zero_without_subprocess(self, tmp_path: Path) -> None:
        artifacts = prepare_artifacts(tmp_path)
        rc = maybe_run_training(
            artifacts,
            base_model=None,
            output_dir=None,
            dry_run=True,
        )
        assert rc == 0

    def test_no_base_model_skips_training(self, tmp_path: Path) -> None:
        artifacts = prepare_artifacts(tmp_path)
        rc = maybe_run_training(
            artifacts,
            base_model=None,
            output_dir=tmp_path / "out",
            dry_run=False,
        )
        assert rc == 0
