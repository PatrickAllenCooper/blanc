"""Tests for experiments.math_topology.discovery_harvester."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.at_scale_dropping import run_at_scale  # noqa: E402
from math_topology.discovery_harvester import (  # noqa: E402
    Discovery,
    HarvestSummary,
    harvest,
    write_discoveries,
)
from blanc.math import builtin_corpus  # noqa: E402
from blanc.math.hypothesis_dropper import DropPolicy  # noqa: E402
from blanc.math.topology_extractor import TopologyCorpus  # noqa: E402


CORPUS = builtin_corpus()


def _seed_survivors(tmp_path: Path) -> Path:
    sub = TopologyCorpus()
    sub.add(CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f"))
    run_at_scale(
        corpus=sub, provider_name="mock", samples_per_challenge=8,
        policy=DropPolicy.SINGLE_CRITICAL, output_dir=tmp_path,
    )
    return tmp_path / "survivors.jsonl"


class TestHarvest:
    def test_dedupes_by_normalised_form(self, tmp_path: Path) -> None:
        survivors = _seed_survivors(tmp_path)
        discoveries, summary = harvest(survivors)
        assert summary.n_input_rows >= len(discoveries)
        ids = [(d.theorem_identifier, d.masked, d.normalised) for d in discoveries]
        assert len(set(ids)) == len(ids)

    def test_aggregates_observation_counts(self, tmp_path: Path) -> None:
        survivors = _seed_survivors(tmp_path)
        discoveries, _ = harvest(survivors)
        # The mock sampler cycles deterministically, so every accepted-novel
        # candidate is observed multiple times across the M3 sweep.
        assert any(d.n_observations > 1 for d in discoveries)

    def test_summary_aggregates_by_theorem_and_mask(self, tmp_path: Path) -> None:
        survivors = _seed_survivors(tmp_path)
        _, summary = harvest(survivors)
        assert "EulerCharacteristic.convex_polytope_v_minus_e_plus_f" in summary.by_theorem
        assert sum(summary.by_theorem.values()) == summary.n_unique_discoveries

    def test_missing_file_yields_empty_harvest(self, tmp_path: Path) -> None:
        nonexistent = tmp_path / "nope.jsonl"
        discoveries, summary = harvest(nonexistent)
        assert discoveries == []
        assert summary.n_input_rows == 0
        assert summary.n_unique_discoveries == 0


class TestWriteDiscoveries:
    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        survivors = _seed_survivors(tmp_path)
        discoveries, _ = harvest(survivors)
        out = tmp_path / "discoveries.jsonl"
        n = write_discoveries(discoveries, out)
        assert n == len(discoveries)
        loaded = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        assert all("defeater" in r for r in loaded)
