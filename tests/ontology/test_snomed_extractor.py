"""
Tests for SNOMED CT extractor.

Covers RF2 format detection and parsing (tab-delimited relationship
snapshots), Is-a (typeId 116680003) -> strict taxonomic rules, other
relationship types -> defeasible rules, property overrides in child
concepts -> defeaters, theory generation, taxonomy output, and the
convenience function -- all using synthetic RF2 data.

Author: Patrick Cooper
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.snomed_extractor import (
    SnomedExtractor,
    ISA_TYPE_ID,
    SNOMED_DEFINING_RELATIONS,
    _normalize,
    _sct_id,
    extract_from_snomed,
)


# -- Helpers ---------------------------------------------------------------

RF2_HEADER = "id\teffectiveTime\tactive\tmoduleId\tsourceId\tdestinationId\trelationshipGroup\ttypeId\tcharacteristicTypeId\tmodifierId"


def _rf2_line(
    rel_id: str = "100",
    effective_time: str = "20250131",
    active: str = "1",
    module_id: str = "900000000000207008",
    source_id: str = "123456789",
    dest_id: str = "987654321",
    rel_group: str = "0",
    type_id: str = "116680003",
    char_type: str = "900000000000011006",
    modifier: str = "900000000000451002",
) -> str:
    return "\t".join([
        rel_id, effective_time, active, module_id,
        source_id, dest_id, rel_group, type_id,
        char_type, modifier,
    ])


def _write_rf2(tmp_path: Path, data_lines: list[str], name: str = "snapshot.txt") -> Path:
    rf2_path = tmp_path / name
    content = RF2_HEADER + "\n" + "\n".join(data_lines) + "\n"
    rf2_path.write_text(content, encoding="utf-8")
    return rf2_path


def _make_extractor(tmp_path: Path, data_lines: list[str]) -> SnomedExtractor:
    rf2_path = _write_rf2(tmp_path, data_lines)
    ext = SnomedExtractor(rf2_path)
    ext.load()
    ext.extract()
    return ext


# -- Normalize / SCT ID ----------------------------------------------------


class TestNormalize:

    def test_lowercase(self):
        assert _normalize("Finding Site") == "finding_site"

    def test_hyphens(self):
        assert _normalize("Anti-Inflammatory") == "anti_inflammatory"

    def test_leading_digit(self):
        assert _normalize("3rd Trimester") == "c_3rd_trimester"


class TestSctId:

    def test_concept_id(self):
        assert _sct_id("123456789") == "sct_123456789"


# -- Extractor Init --------------------------------------------------------


class TestSnomedExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SnomedExtractor(tmp_path / "nonexistent.txt")

    def test_extract_before_load_raises(self, tmp_path):
        rf2_path = _write_rf2(tmp_path, [])
        ext = SnomedExtractor(rf2_path)
        with pytest.raises(ValueError, match="load"):
            ext.extract()


# -- Format Detection ------------------------------------------------------


class TestFormatDetection:

    def test_rf2_detected(self, tmp_path):
        rf2_path = _write_rf2(tmp_path, [])
        ext = SnomedExtractor(rf2_path)
        fmt = ext._detect_format()
        assert fmt == "rf2"

    def test_owl_by_suffix(self, tmp_path):
        owl_path = tmp_path / "snomed.owl"
        owl_path.write_text("<Ontology>SubClassOf</Ontology>", encoding="utf-8")
        ext = SnomedExtractor(owl_path)
        fmt = ext._detect_format()
        assert fmt == "owl"


# -- RF2 Is-a Extraction (Strict) -----------------------------------------


class TestIsaExtraction:

    def test_isa_edge_extracted(self, tmp_path):
        lines = [
            _rf2_line(source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.isa_edges) == 1
        assert ext.isa_edges[0] == ("100001", "200001")

    def test_multiple_isa_edges(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100001", dest_id="200002", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="3", source_id="100002", dest_id="200001", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.isa_edges) == 3

    def test_inactive_row_skipped(self, tmp_path):
        lines = [
            _rf2_line(source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID, active="0"),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.isa_edges) == 0


# -- RF2 Defining Relationship Extraction (Defeasible) ---------------------


class TestDefiningRelExtraction:

    def test_finding_site_extracted(self, tmp_path):
        lines = [
            _rf2_line(
                source_id="100001", dest_id="300001",
                type_id="363698007", rel_group="1",
            ),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.defining_rels) == 1
        source, rel, dest, group = ext.defining_rels[0]
        assert source == "100001"
        assert rel == "finding_site"
        assert dest == "300001"
        assert group == "1"

    def test_unknown_type_id_stored_raw(self, tmp_path):
        lines = [
            _rf2_line(
                source_id="100001", dest_id="300001",
                type_id="999999999", rel_group="0",
            ),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.defining_rels) == 1
        _, rel, _, _ = ext.defining_rels[0]
        assert rel == "999999999"

    def test_mixed_isa_and_defining(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100001", dest_id="300001", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.isa_edges) == 1
        assert len(ext.defining_rels) == 1


# -- Property Override Detection (Defeaters) --------------------------------


class TestPropertyOverrideDetection:

    def test_override_detected(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="200001", dest_id="300001", type_id="363698007"),
            _rf2_line(rel_id="3", source_id="100001", dest_id="300002", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext._property_overrides) >= 1
        child, parent, rel_type, old_target, new_target = ext._property_overrides[0]
        assert child == "100001"
        assert parent == "200001"
        assert old_target == "300001"
        assert new_target == "300002"

    def test_no_override_when_same_target(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="200001", dest_id="300001", type_id="363698007"),
            _rf2_line(rel_id="3", source_id="100001", dest_id="300001", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext._property_overrides) == 0

    def test_no_override_without_isa(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="200001", dest_id="300001", type_id="363698007"),
            _rf2_line(rel_id="2", source_id="100001", dest_id="300002", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext._property_overrides) == 0


# -- Theory Conversion ----------------------------------------------------


class TestSnomedToTheory:

    def test_isa_produces_strict_rule(self, tmp_path):
        lines = [
            _rf2_line(source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        assert strict[0].head == "isa(sct_100001, sct_200001)"

    def test_defining_rel_produces_defeasible_rule(self, tmp_path):
        lines = [
            _rf2_line(
                source_id="100001", dest_id="300001",
                type_id="363698007", rel_group="1",
            ),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert defeasible[0].head == "finding_site(sct_100001, sct_300001)"

    def test_override_produces_defeater(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="200001", dest_id="300001", type_id="363698007"),
            _rf2_line(rel_id="3", source_id="100001", dest_id="300002", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 1
        assert any("~finding_site" in d.head for d in defeaters)

    def test_superiority_added_for_override(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="200001", dest_id="300001", type_id="363698007"),
            _rf2_line(rel_id="3", source_id="100001", dest_id="300002", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert len(theory.superiority) >= 1

    def test_metadata_source_is_snomed(self, tmp_path):
        lines = [
            _rf2_line(source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "SNOMED_CT"

    def test_duplicate_isa_not_repeated(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1

    def test_mixed_relations_theory(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100001", dest_id="300001", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1


# -- Taxonomy --------------------------------------------------------------


class TestSnomedGetTaxonomy:

    def test_taxonomy_structure(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100002", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="3", source_id="100001", dest_id="200002", type_id=ISA_TYPE_ID),
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert tax["sct_100001"] == {"sct_200001", "sct_200002"}
        assert tax["sct_100002"] == {"sct_200001"}
        assert "sct_200001" not in tax

    def test_defining_rels_excluded_from_taxonomy(self, tmp_path):
        lines = [
            _rf2_line(source_id="100001", dest_id="300001", type_id="363698007"),
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert len(tax) == 0


# -- Convenience Function -------------------------------------------------


class TestExtractFromSnomed:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_snomed(tmp_path / "nonexistent.txt")

    def test_roundtrip(self, tmp_path):
        lines = [
            _rf2_line(rel_id="1", source_id="100001", dest_id="200001", type_id=ISA_TYPE_ID),
            _rf2_line(rel_id="2", source_id="100001", dest_id="300001", type_id="363698007"),
        ]
        rf2_path = _write_rf2(tmp_path, lines)
        theory = extract_from_snomed(rf2_path)
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1
