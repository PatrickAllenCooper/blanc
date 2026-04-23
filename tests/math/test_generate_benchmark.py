"""Tests for experiments.math.generate_benchmark."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.generate_benchmark import (  # noqa: E402
    generate_benchmark,
    generate_l1,
    generate_l2,
    generate_l3,
)
from blanc.math import builtin_corpus  # noqa: E402


CORPUS = builtin_corpus()


class TestPerLevelGenerators:
    def test_l1_one_per_non_critical(self) -> None:
        thm = CORPUS.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f")
        rows = generate_l1(thm)
        non_critical = [h for h in thm.hypotheses if not h.critical]
        assert len(rows) == len(non_critical)
        for r in rows:
            assert r.level == 1
            assert len(r.masked_hypotheses) == 1
            assert r.gold

    def test_l2_one_per_theorem(self) -> None:
        thm = CORPUS.by_id("Topology.heine_borel")
        rows = generate_l2(thm)
        assert len(rows) == 1
        row = rows[0]
        assert row.level == 2
        assert row.gold == (thm.statement,)
        assert thm.statement not in row.prompt  # statement is masked

    def test_l3_one_per_critical(self) -> None:
        thm = CORPUS.by_id("Topology.urysohn_lemma")
        rows = generate_l3(thm)
        critical = [h for h in thm.hypotheses if h.critical]
        assert len(rows) == len(critical)
        for r in rows:
            assert r.level == 3
            assert len(r.masked_hypotheses) == 1
            assert "Do not simply restate" in r.prompt


class TestDriver:
    def test_generate_benchmark_returns_three_lists(self) -> None:
        l1, l2, l3 = generate_benchmark(CORPUS, seed=17)
        assert len(l1) > 0
        assert len(l2) == len(CORPUS)
        assert len(l3) > 0

    def test_caps_are_respected(self) -> None:
        l1, l2, l3 = generate_benchmark(
            CORPUS, seed=17, cap_l1=2, cap_l2=1, cap_l3=3,
        )
        assert len(l1) == 2
        assert len(l2) == 1
        assert len(l3) == 3

    def test_seed_is_deterministic(self) -> None:
        first = generate_benchmark(CORPUS, seed=99)
        second = generate_benchmark(CORPUS, seed=99)
        assert [r.instance_id for r in first[0]] == [r.instance_id for r in second[0]]
        assert [r.instance_id for r in first[2]] == [r.instance_id for r in second[2]]

    def test_instance_ids_are_unique_per_level(self) -> None:
        l1, l2, l3 = generate_benchmark(CORPUS, seed=17)
        for level_rows in (l1, l2, l3):
            ids = [r.instance_id for r in level_rows]
            assert len(set(ids)) == len(ids)


class TestCLIIntegration:
    def test_writes_three_jsonl_plus_counts(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from math_topology.generate_benchmark import main
        monkeypatch.setattr(
            "sys.argv",
            ["generate_benchmark.py", "--output-dir", str(tmp_path), "--seed", "7"],
        )
        rc = main()
        assert rc == 0
        for fname in ("l1.jsonl", "l2.jsonl", "l3.jsonl", "counts.json"):
            assert (tmp_path / fname).exists()
        counts = json.loads((tmp_path / "counts.json").read_text())
        assert counts["total"] > 0
