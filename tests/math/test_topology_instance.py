"""Tests for experiments.math.topology_instance."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.topology_instance import (  # noqa: E402
    TopologyInstance,
    read_jsonl,
    reconstruct_theorem,
    write_jsonl,
)
from blanc.math.types import Hypothesis  # noqa: E402


def make_instance(level: int = 3) -> TopologyInstance:
    return TopologyInstance(
        instance_id=f"L{level}.foo.bar",
        level=level,
        theorem_identifier="foo",
        theorem_statement="C",
        hypotheses=(
            Hypothesis(name="a", lean_expr="A"),
            Hypothesis(name="b", lean_expr="B", critical=True),
        ),
        masked_hypotheses=("b",) if level == 3 else (),
        gold=("B",),
        prompt="propose a defeater",
        metadata={"source_path": "Mathlib/foo.lean", "natural_language": "foo"},
    )


class TestRoundTrip:
    def test_to_dict_from_dict_roundtrip(self) -> None:
        inst = make_instance()
        roundtripped = TopologyInstance.from_dict(inst.to_dict())
        assert roundtripped == inst

    def test_jsonl_roundtrip(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        instances = [make_instance(level=lvl) for lvl in (1, 2, 3)]
        n = write_jsonl(instances, path)
        assert n == 3
        loaded = read_jsonl(path)
        assert loaded == instances

    def test_empty_jsonl_returns_empty_list(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("\n\n")
        assert read_jsonl(path) == []


class TestReconstructTheorem:
    def test_reconstructs_full_theorem(self) -> None:
        inst = make_instance()
        thm = reconstruct_theorem(inst)
        assert thm.identifier == "foo"
        assert thm.statement == "C"
        assert thm.hypotheses == inst.hypotheses
        assert thm.source_path == "Mathlib/foo.lean"
