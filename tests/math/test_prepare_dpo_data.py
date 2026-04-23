"""Tests for experiments.math_topology.prepare_dpo_data."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.lakatos_corpus import HELD_OUT_MASK  # noqa: E402
from math_topology.prepare_dpo_data import (  # noqa: E402
    DPORecord,
    build_dpo_records,
    write_records,
)


class TestBuildDPORecords:
    def test_records_have_positive_margin(self) -> None:
        records = build_dpo_records()
        assert len(records) > 0
        for r in records:
            assert r.margin > 0

    def test_records_exclude_held_out(self) -> None:
        records = build_dpo_records()
        for r in records:
            assert r.masked_hypothesis != HELD_OUT_MASK

    def test_includes_trivial_restoration_as_rejected(self) -> None:
        records = build_dpo_records()
        trivial_pairs = [
            r for r in records if "trivial" in r.rejected_provenance
        ]
        assert len(trivial_pairs) > 0
        for r in trivial_pairs:
            assert r.margin > 0

    def test_chosen_is_lean_expr_not_natural_language(self) -> None:
        records = build_dpo_records()
        for r in records:
            assert "." in r.chosen or "=" in r.chosen or "(" in r.chosen


class TestWriteRecords:
    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        records = build_dpo_records()
        out = tmp_path / "dpo.jsonl"
        n = write_records(records, out)
        loaded = [json.loads(line) for line in out.read_text().splitlines() if line.strip()]
        assert len(loaded) == n
        assert all({"prompt", "chosen", "rejected", "margin"} <= set(r.keys()) for r in loaded)
