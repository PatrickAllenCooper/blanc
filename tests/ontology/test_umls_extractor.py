"""
Tests for UMLS RRF extractor.

Covers pipe-delimited RRF parsing for MRCONSO, MRREL, MRSTY, and MRDEF,
semantic type -> defeasible rules, inter-vocabulary contradictions ->
defeaters, taxonomy from broader/narrower, theory generation, and
the convenience function -- all using synthetic RRF files.

Author: Patrick Cooper
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.umls_extractor import (
    UmlsExtractor,
    _normalize,
    _cui_id,
    RELATION_MAP,
    CLINICAL_RELA,
    extract_from_umls,
)


# -- Helpers ---------------------------------------------------------------


def _make_rrf_dir(
    tmp_path: Path,
    mrconso_lines: list[str] | None = None,
    mrsty_lines: list[str] | None = None,
    mrrel_lines: list[str] | None = None,
    mrdef_lines: list[str] | None = None,
) -> Path:
    """Create a synthetic UMLS RRF directory with the required files."""
    rrf_dir = tmp_path / "META"
    rrf_dir.mkdir()

    (rrf_dir / "MRCONSO.RRF").write_text(
        "\n".join(mrconso_lines or []) + "\n", encoding="utf-8"
    )
    (rrf_dir / "MRSTY.RRF").write_text(
        "\n".join(mrsty_lines or []) + "\n", encoding="utf-8"
    )
    (rrf_dir / "MRREL.RRF").write_text(
        "\n".join(mrrel_lines or []) + "\n", encoding="utf-8"
    )
    if mrdef_lines is not None:
        (rrf_dir / "MRDEF.RRF").write_text(
            "\n".join(mrdef_lines) + "\n", encoding="utf-8"
        )

    return rrf_dir


def _make_mrconso_line(
    cui: str,
    lat: str = "ENG",
    sab: str = "MSH",
    tty: str = "PT",
    name: str = "Aspirin",
    suppress: str = "N",
) -> str:
    """Build a synthetic MRCONSO.RRF line.

    Column order: CUI|LAT|TS|LUI|STT|SUI|ISPREF|AUI|SAUI|SCUI|SDUI|SAB|TTY|CODE|STR|SRL|SUPPRESS|CVF
    """
    return f"{cui}|{lat}|P|L0000001|PF|S0000001|Y|A0000001||{cui}||{sab}|{tty}|{cui}|{name}|0|{suppress}|"


def _make_mrsty_line(cui: str, tui: str, sty: str) -> str:
    """Build a synthetic MRSTY.RRF line.

    Column order: CUI|TUI|STN|STY|ATUI|CVF
    """
    return f"{cui}|{tui}|A1.1|{sty}|AT000001|"


def _make_mrrel_line(
    cui1: str,
    rel: str,
    cui2: str,
    rela: str = "",
    sab: str = "MSH",
    suppress: str = "N",
) -> str:
    """Build a synthetic MRREL.RRF line.

    Column order: CUI1|AUI1|STYPE1|REL|CUI2|AUI2|STYPE2|RELA|RUI|SRUI|SAB|SL|RG|DIR|SUPPRESS|CVF
    """
    return f"{cui1}|A0001|AUI|{rel}|{cui2}|A0002|AUI|{rela}|R0001||{sab}|{sab}||Y|{suppress}|"


def _make_mrdef_line(cui: str, definition: str, suppress: str = "N") -> str:
    """Build a synthetic MRDEF.RRF line.

    Column order: CUI|AUI|ATUI|SATUI|SAB|DEF|SUPPRESS|CVF
    """
    return f"{cui}|A0001|AT0001||MSH|{definition}|{suppress}|"


# -- Normalize / CUI -------------------------------------------------------


class TestNormalize:

    def test_lowercase(self):
        assert _normalize("Pharmacologic Substance") == "pharmacologic_substance"

    def test_hyphens(self):
        assert _normalize("Anti-Inflammatory") == "anti_inflammatory"

    def test_leading_digit(self):
        assert _normalize("5-HT Receptor") == "c_5_ht_receptor"


class TestCuiId:

    def test_uppercase_cui(self):
        assert _cui_id("C0000001") == "cui_c0000001"

    def test_lowercase_cui(self):
        assert _cui_id("c0000001") == "cui_c0000001"


# -- Extractor Init --------------------------------------------------------


class TestUmlsExtractorInit:

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            UmlsExtractor(tmp_path / "nonexistent")

    def test_missing_required_files_raises(self, tmp_path):
        rrf_dir = tmp_path / "META"
        rrf_dir.mkdir()
        (rrf_dir / "MRCONSO.RRF").write_text("")
        with pytest.raises(FileNotFoundError, match="MRREL"):
            UmlsExtractor(rrf_dir)

    def test_extract_before_load_raises(self, tmp_path):
        rrf_dir = _make_rrf_dir(tmp_path)
        ext = UmlsExtractor(rrf_dir)
        with pytest.raises(ValueError, match="load"):
            ext.extract()


# -- MRCONSO Loading -------------------------------------------------------


class TestMrconsoLoading:

    def test_concepts_loaded(self, tmp_path):
        lines = [
            _make_mrconso_line("C0000001", name="Aspirin"),
            _make_mrconso_line("C0000002", name="Ibuprofen"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrconso_lines=lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert ext.concepts["C0000001"] == "Aspirin"
        assert ext.concepts["C0000002"] == "Ibuprofen"

    def test_non_english_skipped(self, tmp_path):
        lines = [
            _make_mrconso_line("C0000001", lat="ENG", name="Aspirin"),
            _make_mrconso_line("C0000002", lat="FRE", name="Aspirine"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrconso_lines=lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert "C0000001" in ext.concepts
        assert "C0000002" not in ext.concepts

    def test_suppressed_skipped(self, tmp_path):
        lines = [
            _make_mrconso_line("C0000001", suppress="N", name="Active"),
            _make_mrconso_line("C0000002", suppress="O", name="Obsolete"),
            _make_mrconso_line("C0000003", suppress="Y", name="Suppressed"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrconso_lines=lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert "C0000001" in ext.concepts
        assert "C0000002" not in ext.concepts
        assert "C0000003" not in ext.concepts

    def test_source_vocab_tracked(self, tmp_path):
        lines = [
            _make_mrconso_line("C0000001", sab="MSH", name="Aspirin"),
            _make_mrconso_line("C0000001", sab="SNOMEDCT_US", name="Aspirin"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrconso_lines=lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert "MSH" in ext.concept_sources["C0000001"]
        assert "SNOMEDCT_US" in ext.concept_sources["C0000001"]


# -- MRSTY Loading ---------------------------------------------------------


class TestMrstyLoading:

    def test_semantic_types_loaded(self, tmp_path):
        sty_lines = [
            _make_mrsty_line("C0000001", "T109", "Organic Chemical"),
            _make_mrsty_line("C0000001", "T121", "Pharmacologic Substance"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrsty_lines=sty_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert len(ext.semantic_types) == 2
        cuis = [s[0] for s in ext.semantic_types]
        assert cuis.count("C0000001") == 2


# -- MRREL Loading ---------------------------------------------------------


class TestMrrelLoading:

    def test_relations_loaded(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RB", "C0000002", rela="", sab="MSH"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert len(ext.relations) == 1
        assert ext.relations[0][0] == "C0000001"
        assert ext.relations[0][1] == "RB"
        assert ext.relations[0][2] == "C0000002"

    def test_self_relation_skipped(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RB", "C0000001"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert len(ext.relations) == 0

    def test_suppressed_relation_skipped(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RB", "C0000002", suppress="O"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert len(ext.relations) == 0


# -- MRDEF Loading ---------------------------------------------------------


class TestMrdefLoading:

    def test_definitions_loaded(self, tmp_path):
        def_lines = [
            _make_mrdef_line("C0000001", "A pain reliever"),
        ]
        rrf_dir = _make_rrf_dir(
            tmp_path,
            mrconso_lines=[_make_mrconso_line("C0000001")],
            mrdef_lines=def_lines,
        )
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert ext.definitions["C0000001"] == "A pain reliever"

    def test_missing_mrdef_skipped(self, tmp_path):
        rrf_dir = _make_rrf_dir(tmp_path)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        assert len(ext.definitions) == 0


# -- Contradiction Detection -----------------------------------------------


class TestContradictionDetection:

    def test_treats_vs_contraindicated(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats", sab="MSH"),
            _make_mrrel_line(
                "C0000001", "RO", "C0000002",
                rela="contraindicated_with", sab="SNOMEDCT_US",
            ),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        assert len(ext._contradictions) >= 1

    def test_causes_vs_prevents(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="causes", sab="MSH"),
            _make_mrrel_line(
                "C0000001", "RO", "C0000002",
                rela="prevents", sab="RXNORM",
            ),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        assert len(ext._contradictions) >= 1

    def test_no_contradiction_for_consistent_rels(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats", sab="MSH"),
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats", sab="RXNORM"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        assert len(ext._contradictions) == 0


# -- Theory Conversion ----------------------------------------------------


class TestUmlsToTheory:

    def test_semantic_type_produces_defeasible(self, tmp_path):
        sty_lines = [
            _make_mrsty_line("C0000001", "T121", "Pharmacologic Substance"),
        ]
        conso_lines = [
            _make_mrconso_line("C0000001", name="Aspirin"),
        ]
        rrf_dir = _make_rrf_dir(
            tmp_path,
            mrconso_lines=conso_lines,
            mrsty_lines=sty_lines,
        )
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 1
        heads = {r.head for r in defeasible}
        assert any("has_semantic_type" in h for h in heads)

    def test_hierarchical_rel_produces_strict(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "PAR", "C0000002"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) >= 1
        assert any("parent" in r.head for r in strict)

    def test_clinical_rel_produces_defeasible(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        heads = {r.head for r in defeasible}
        assert any("treats" in h for h in heads)

    def test_contradiction_produces_defeater(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats", sab="MSH"),
            _make_mrrel_line(
                "C0000001", "RO", "C0000002",
                rela="contraindicated_with", sab="SNOMEDCT_US",
            ),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 1
        assert any("~treats" in d.head for d in defeaters)

    def test_metadata_source_is_umls(self, tmp_path):
        sty_lines = [
            _make_mrsty_line("C0000001", "T121", "Pharmacologic Substance"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrsty_lines=sty_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "UMLS"

    def test_superiority_added_for_contradiction(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats", sab="MSH"),
            _make_mrrel_line(
                "C0000001", "RO", "C0000002",
                rela="contraindicated_with", sab="SNOMEDCT_US",
            ),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        assert len(theory.superiority) >= 1


# -- Taxonomy --------------------------------------------------------------


class TestUmlsGetTaxonomy:

    def test_par_relation_in_taxonomy(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "PAR", "C0000002"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        tax = ext.get_taxonomy()
        assert "cui_c0000002" in tax.get("cui_c0000001", set())

    def test_chd_relation_reversed(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "CHD", "C0000002"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        tax = ext.get_taxonomy()
        assert "cui_c0000001" in tax.get("cui_c0000002", set())

    def test_non_taxonomic_excluded(self, tmp_path):
        rel_lines = [
            _make_mrrel_line("C0000001", "RO", "C0000002", rela="treats"),
        ]
        rrf_dir = _make_rrf_dir(tmp_path, mrrel_lines=rel_lines)
        ext = UmlsExtractor(rrf_dir)
        ext.load()
        ext.extract()
        tax = ext.get_taxonomy()
        assert len(tax) == 0


# -- Convenience Function -------------------------------------------------


class TestExtractFromUmls:

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_umls(tmp_path / "nonexistent")

    def test_roundtrip(self, tmp_path):
        conso_lines = [_make_mrconso_line("C0000001", name="Aspirin")]
        sty_lines = [_make_mrsty_line("C0000001", "T121", "Pharmacologic Substance")]
        rel_lines = [_make_mrrel_line("C0000001", "PAR", "C0000002")]
        rrf_dir = _make_rrf_dir(
            tmp_path,
            mrconso_lines=conso_lines,
            mrsty_lines=sty_lines,
            mrrel_lines=rel_lines,
        )
        theory = extract_from_umls(rrf_dir)
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) >= 1
        assert len(theory.get_rules_by_type(RuleType.STRICT)) >= 1
