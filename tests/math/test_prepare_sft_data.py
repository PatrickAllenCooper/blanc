"""Tests for experiments.math_topology.prepare_sft_data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.lakatos_corpus import HELD_OUT_MASK, training_fixtures  # noqa: E402
from math_topology.prepare_sft_data import (  # noqa: E402
    SFTRecord,
    build_sft_records,
    fixture_to_records,
    write_records,
)


class TestFixtureToRecords:
    def test_one_record_per_gold_defeater(self) -> None:
        f = training_fixtures()[0]
        records = fixture_to_records(f)
        assert len(records) == len(f.gold_defeaters)
        for r, d in zip(records, f.gold_defeaters):
            assert r.completion == d.lean_expr

    def test_record_carries_masked_hypothesis_metadata(self) -> None:
        f = training_fixtures()[0]
        records = fixture_to_records(f)
        for r in records:
            assert r.masked_hypothesis == f.masked
            assert r.theorem_identifier == f.parent.identifier


class TestBuildSFTRecords:
    def test_held_out_excluded_by_default(self) -> None:
        records = build_sft_records()
        for r in records:
            assert r.masked_hypothesis != HELD_OUT_MASK

    def test_include_held_out_flag(self) -> None:
        records_safe = build_sft_records(include_held_out=False)
        records_unsafe = build_sft_records(include_held_out=True)
        assert len(records_unsafe) > len(records_safe)
        held_out_rows = [r for r in records_unsafe if r.masked_hypothesis == HELD_OUT_MASK]
        assert len(held_out_rows) > 0


class TestWriteRecords:
    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        records = build_sft_records()
        out = tmp_path / "sft.jsonl"
        n = write_records(records, out)
        assert n == len(records)
        loaded = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
        assert len(loaded) == len(records)
        assert all("prompt" in r and "completion" in r for r in loaded)
