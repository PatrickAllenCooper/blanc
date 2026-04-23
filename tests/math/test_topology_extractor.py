"""Tests for blanc.math.topology_extractor."""

from __future__ import annotations

from pathlib import Path

import pytest

from blanc.math.topology_extractor import (
    MathlibExtractor,
    TopologyCorpus,
    builtin_corpus,
)
from blanc.math.types import Hypothesis, MathTheorem


class TestBuiltinCorpus:
    def test_corpus_is_non_empty(self) -> None:
        corpus = builtin_corpus()
        assert len(corpus) >= 4

    def test_euler_theorem_present(self) -> None:
        corpus = builtin_corpus()
        thm = corpus.by_id("EulerCharacteristic.convex_polytope_v_minus_e_plus_f")
        assert "= 2" in thm.statement
        critical_names = {h.name for h in thm.hypotheses if h.critical}
        assert "h_convex" in critical_names

    def test_lookup_missing_id_raises(self) -> None:
        corpus = builtin_corpus()
        with pytest.raises(KeyError):
            corpus.by_id("does.not.exist")

    def test_iter_yields_all_theorems(self) -> None:
        corpus = builtin_corpus()
        ids = {t.identifier for t in corpus}
        assert len(ids) == len(corpus)


class TestTopologyCorpus:
    def test_add_rejects_duplicates(self) -> None:
        corpus = TopologyCorpus()
        thm = MathTheorem(identifier="x", statement="C", hypotheses=())
        corpus.add(thm)
        with pytest.raises(ValueError):
            corpus.add(thm)


class TestMathlibExtractor:
    def test_no_root_yields_nothing(self) -> None:
        extractor = MathlibExtractor(mathlib_root=None)
        assert list(extractor.iter_files()) == []
        assert len(extractor.extract()) == 0

    def test_parses_simple_lean_file(self, tmp_path: Path) -> None:
        sub = tmp_path / "Mathlib" / "Topology"
        sub.mkdir(parents=True)
        path = sub / "Foo.lean"
        path.write_text(
            "theorem Topology.foo (X : Type) (h : Continuous f) : True := by trivial\n"
        )
        extractor = MathlibExtractor(mathlib_root=tmp_path)
        theorems = list(extractor.parse_file(path))
        assert any(t.identifier == "Topology.foo" for t in theorems)

    def test_extract_skips_undecorated_decls(self, tmp_path: Path) -> None:
        sub = tmp_path / "Mathlib" / "Topology"
        sub.mkdir(parents=True)
        (sub / "Bar.lean").write_text(
            "-- not a theorem\nstructure Foo where\n  x : Nat\n"
        )
        extractor = MathlibExtractor(mathlib_root=tmp_path)
        corpus = extractor.extract()
        assert len(corpus) == 0

    def test_extract_dedupes_identifiers(self, tmp_path: Path) -> None:
        sub = tmp_path / "Mathlib" / "Topology"
        sub.mkdir(parents=True)
        text = (
            "theorem dup (a : A) : C := by trivial\n"
            "theorem dup (a : A) : C := by trivial\n"
        )
        (sub / "Dup.lean").write_text(text)
        corpus = MathlibExtractor(mathlib_root=tmp_path).extract()
        assert len([t for t in corpus if t.identifier == "dup"]) == 1
