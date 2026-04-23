"""Tests for experiments.math_topology.grpo_dataset."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.at_scale_dropping import run_at_scale  # noqa: E402
from math_topology.grpo_dataset import (  # noqa: E402
    GRPOUnit,
    _recompute_advantages,
    assemble,
    write_units,
)
from blanc.math import builtin_corpus  # noqa: E402
from blanc.math.hypothesis_dropper import DropPolicy  # noqa: E402
from blanc.math.topology_extractor import TopologyCorpus  # noqa: E402


CORPUS = builtin_corpus()


def _seed_groups(tmp_path: Path) -> Path:
    sub = TopologyCorpus()
    sub.add(CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f"))
    sub.add(CORPUS.by_id("Topology.heine_borel"))
    run_at_scale(
        corpus=sub, provider_name="mock", samples_per_challenge=4,
        policy=DropPolicy.SINGLE_CRITICAL, output_dir=tmp_path,
    )
    return tmp_path / "groups.jsonl"


class TestAssemble:
    def test_one_unit_per_group(self, tmp_path: Path) -> None:
        groups = _seed_groups(tmp_path)
        units = assemble(groups)
        assert len(units) > 0
        for u in units:
            assert len(u.completions) == len(u.rewards) == len(u.advantages)

    def test_unit_carries_theorem_and_mask(self, tmp_path: Path) -> None:
        groups = _seed_groups(tmp_path)
        units = assemble(groups)
        assert all(u.theorem_id for u in units)
        assert all(isinstance(u.masked, tuple) for u in units)


class TestRecomputeAdvantages:
    def test_zero_when_all_equal(self) -> None:
        adv = _recompute_advantages((0.5, 0.5, 0.5, 0.5))
        assert all(abs(a) < 1e-9 for a in adv)

    def test_zero_mean(self) -> None:
        adv = _recompute_advantages((1.0, 0.0, 0.5))
        assert abs(sum(adv)) < 1e-9


class TestWriteUnits:
    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        groups = _seed_groups(tmp_path)
        units = assemble(groups)
        out = tmp_path / "grpo.jsonl"
        n = write_units(units, out)
        assert n == len(units)
        loaded = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        assert all({"prompt", "completions", "rewards", "advantages"} <= set(r.keys()) for r in loaded)
