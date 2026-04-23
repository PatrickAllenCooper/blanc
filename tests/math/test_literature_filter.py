"""Tests for experiments.math_topology.literature_filter."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.literature_filter import (  # noqa: E402
    DeferredLiteratureFilter,
    HumanNoveltyLabel,
    LiteratureVerdict,
    StubLiteratureFilter,
)


class TestStubLiteratureFilter:
    def test_unknown_is_human_novel(self) -> None:
        f = StubLiteratureFilter()
        v = f.classify("some unknown lean expr")
        assert v.label is HumanNoveltyLabel.HUMAN_NOVEL

    def test_known_is_human_known_with_source(self) -> None:
        f = StubLiteratureFilter(
            known_index={"P.boundary.genus = 0": ("ArXiv", "Lakatos 1976")}
        )
        v = f.classify("P.boundary.genus = 0")
        assert v.label is HumanNoveltyLabel.HUMAN_KNOWN
        assert v.matched_source == "ArXiv"
        assert v.matched_title == "Lakatos 1976"

    def test_classify_jsonl_round_trip(self, tmp_path: Path) -> None:
        in_path = tmp_path / "discoveries.jsonl"
        in_path.write_text(json.dumps({"defeater": "P.boundary.genus = 0"}) + "\n"
                           + json.dumps({"defeater": "Foo.unknown"}) + "\n")
        out_path = tmp_path / "labelled.jsonl"
        f = StubLiteratureFilter(known_index={"P.boundary.genus = 0": ("ArXiv", "Lakatos")})
        counts = f.classify_jsonl(in_path, out_path)
        assert counts[HumanNoveltyLabel.HUMAN_KNOWN.value] == 1
        assert counts[HumanNoveltyLabel.HUMAN_NOVEL.value] == 1
        rows = [json.loads(l) for l in out_path.read_text().splitlines() if l.strip()]
        assert len(rows) == 2
        assert all("human_novelty_label" in r for r in rows)


class TestDeferredLiteratureFilter:
    def test_classify_raises_not_implemented(self) -> None:
        f = DeferredLiteratureFilter()
        with pytest.raises(NotImplementedError, match="M4"):
            f.classify("anything")
