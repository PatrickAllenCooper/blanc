"""Tests for experiments.math_topology.at_scale_dropping."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.at_scale_dropping import (  # noqa: E402
    GroupRecord,
    SampledScore,
    _MockSampler,
    _populate_mock_harness,
    run_at_scale,
)
from blanc.math import (  # noqa: E402
    builtin_corpus,
    HypothesisDropper,
    MockLeanHarness,
)
from blanc.math.hypothesis_dropper import DropPolicy  # noqa: E402


CORPUS = builtin_corpus()


class TestMockSampler:
    def test_returns_n_responses(self) -> None:
        sampler = _MockSampler()
        thm = CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f")
        challenge = HypothesisDropper(DropPolicy.SINGLE_CRITICAL).drop(thm)[0]
        out = sampler.sample(challenge, 5)
        assert len(out) == 5
        assert all(isinstance(s, str) and s for s in out)


class TestPopulateMockHarness:
    def test_register_critical_pairs(self) -> None:
        harness = MockLeanHarness()
        _populate_mock_harness(CORPUS, harness)
        assert len(harness.responses) > 0


class TestGroupRecord:
    def test_advantages_zero_when_all_rewards_equal(self) -> None:
        samples = [
            SampledScore("t", ("x",), i, "y", "proved", 0.5, False, False, None, 0.5)
            for i in range(4)
        ]
        group = GroupRecord("t", ("x",), "p", samples)
        assert all(abs(a) < 1e-9 for a in group.advantages())

    def test_advantages_have_zero_mean(self) -> None:
        samples = [
            SampledScore("t", ("x",), 0, "a", "proved", 1.0, False, False, None, 1.0),
            SampledScore("t", ("x",), 1, "b", "refuted", 0.0, False, False, None, 0.0),
            SampledScore("t", ("x",), 2, "c", "proved", 0.6, False, False, None, 0.4),
        ]
        group = GroupRecord("t", ("x",), "p", samples)
        adv = group.advantages()
        assert abs(sum(adv)) < 1e-9


class TestRunAtScaleEndToEnd:
    def test_writes_groups_and_survivors(self, tmp_path: Path) -> None:
        # Restrict the corpus for speed.
        from blanc.math.topology_extractor import TopologyCorpus
        sub = TopologyCorpus()
        sub.add(CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f"))
        sub.add(CORPUS.by_id("Topology.heine_borel"))

        summary = run_at_scale(
            corpus=sub,
            provider_name="mock",
            samples_per_challenge=3,
            policy=DropPolicy.SINGLE_CRITICAL,
            output_dir=tmp_path,
        )
        assert summary["n_groups"] > 0
        assert summary["n_samples"] == summary["n_groups"] * 3
        assert (tmp_path / "groups.jsonl").exists()
        assert (tmp_path / "survivors.jsonl").exists()
        assert (tmp_path / "summary.json").exists()
        assert summary["n_survivors"] >= 1
        assert summary["n_lean_accept"] >= summary["n_survivors"]

    def test_groups_jsonl_has_advantages(self, tmp_path: Path) -> None:
        from blanc.math.topology_extractor import TopologyCorpus
        sub = TopologyCorpus()
        sub.add(CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f"))
        run_at_scale(
            corpus=sub,
            provider_name="mock",
            samples_per_challenge=4,
            policy=DropPolicy.SINGLE_CRITICAL,
            output_dir=tmp_path,
        )
        rows = [json.loads(l) for l in (tmp_path / "groups.jsonl").read_text().splitlines() if l.strip()]
        assert rows
        for r in rows:
            assert len(r["advantages"]) == len(r["samples"])
