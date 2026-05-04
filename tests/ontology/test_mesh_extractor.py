"""
Tests for MeSH ontology extractor.

Covers XML parsing of DescriptorRecord elements, tree number parent
derivation, category assignment, theory generation with strict rules,
and taxonomy output -- all using small synthetic XML fragments.

Author: Anonymous Authors
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.mesh_extractor import (
    MeshExtractor,
    MESH_CATEGORIES,
    extract_from_mesh,
)


# ── Synthetic XML Helpers ─────────────────────────────────────────

MINIMAL_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI>D000001</DescriptorUI>
    <DescriptorName><String>Body Regions</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>A01</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D000002</DescriptorUI>
    <DescriptorName><String>Abdomen</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>A01.456</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D000003</DescriptorUI>
    <DescriptorName><String>Abdominal Muscles</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>A01.456.505</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D000004</DescriptorUI>
    <DescriptorName><String>Neoplasms</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>C04</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
</DescriptorRecordSet>
"""

POLYHIERARCHY_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI>D100</DescriptorUI>
    <DescriptorName><String>Parent A</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>A01</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D200</DescriptorUI>
    <DescriptorName><String>Parent B</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>C01</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
  <DescriptorRecord>
    <DescriptorUI>D300</DescriptorUI>
    <DescriptorName><String>Multi Parent Child</String></DescriptorName>
    <TreeNumberList>
      <TreeNumber>A01.100</TreeNumber>
      <TreeNumber>C01.200</TreeNumber>
    </TreeNumberList>
  </DescriptorRecord>
</DescriptorRecordSet>
"""


def _write_xml(tmp_path: Path, content: str, name: str = "test.xml") -> Path:
    xml_path = tmp_path / name
    xml_path.write_text(content, encoding="utf-8")
    return xml_path


# ── Init ──────────────────────────────────────────────────────────


class TestMeshExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            MeshExtractor(tmp_path / "nonexistent.xml")

    def test_extract_before_load_raises(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        with pytest.raises(ValueError, match="load"):
            ext.extract()


# ── XML Loading ───────────────────────────────────────────────────


class TestMeshLoad:

    def test_descriptors_loaded(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        assert len(ext.descriptors) == 4
        assert ext.descriptors["D000001"] == "Body Regions"
        assert ext.descriptors["D000003"] == "Abdominal Muscles"

    def test_tree_to_descriptor_mapping(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        assert ext.tree_to_descriptor["A01"] == "D000001"
        assert ext.tree_to_descriptor["A01.456"] == "D000002"
        assert ext.tree_to_descriptor["A01.456.505"] == "D000003"
        assert ext.tree_to_descriptor["C04"] == "D000004"

    def test_empty_descriptor_skipped(self, tmp_path):
        xml = """\
<?xml version="1.0" encoding="UTF-8"?>
<DescriptorRecordSet>
  <DescriptorRecord>
    <DescriptorUI></DescriptorUI>
    <DescriptorName><String>Blank</String></DescriptorName>
  </DescriptorRecord>
</DescriptorRecordSet>
"""
        xml_path = _write_xml(tmp_path, xml)
        ext = MeshExtractor(xml_path)
        ext.load()
        assert len(ext.descriptors) == 0


# ── Tree Number Parent Derivation ─────────────────────────────────


class TestTreeNumberParents:

    def test_dotted_parent(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        child_parent_ids = [(c, p) for c, p in ext.parent_child
                            if not p.startswith("category_")]
        assert ("D000003", "D000002") in child_parent_ids
        assert ("D000002", "D000001") in child_parent_ids

    def test_top_level_gets_category(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        category_pairs = [(c, p) for c, p in ext.parent_child
                          if p.startswith("category_")]
        child_ids_with_anatomy = [c for c, p in category_pairs
                                  if p == "category_anatomy"]
        assert "D000001" in child_ids_with_anatomy
        assert "D000002" in child_ids_with_anatomy
        assert "D000003" in child_ids_with_anatomy

    def test_c_category_assigned(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        category_pairs = [(c, p) for c, p in ext.parent_child
                          if p == "category_diseases"]
        assert any(c == "D000004" for c, _ in category_pairs)

    def test_polyhierarchy_multiple_parents(self, tmp_path):
        xml_path = _write_xml(tmp_path, POLYHIERARCHY_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        parents_of_d300 = [p for c, p in ext.parent_child
                           if c == "D300" and not p.startswith("category_")]
        assert "D100" in parents_of_d300
        assert "D200" in parents_of_d300


# ── Theory Conversion ────────────────────────────────────────────


class TestMeshToTheory:

    def test_strict_rules_only(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 0
        assert len(theory.get_rules_by_type(RuleType.DEFEATER)) == 0
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) > 0

    def test_isa_rule_content(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        heads = {r.head for r in strict}
        assert "isa(abdominal_muscles, abdomen)" in heads

    def test_category_isa_rules(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        heads = {r.head for r in strict}
        assert any("category_anatomy" in h for h in heads)

    def test_descriptor_facts(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        assert "mesh_descriptor(body_regions)" in theory.facts
        assert "mesh_descriptor(abdomen)" in theory.facts

    def test_category_facts(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        assert "mesh_category(category_anatomy)" in theory.facts
        assert "mesh_category(category_diseases)" in theory.facts

    def test_metadata_source_is_mesh(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        for rule in theory.get_rules_by_type(RuleType.STRICT):
            assert rule.metadata.get("source") == "MeSH"

    def test_no_duplicate_rules(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        heads = [r.head for r in strict]
        assert len(heads) == len(set(heads))


# ── Taxonomy ──────────────────────────────────────────────────────


class TestMeshGetTaxonomy:

    def test_taxonomy_structure(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        tax = ext.get_taxonomy()
        assert "category_anatomy" in tax.get("abdominal_muscles", set())
        assert "abdomen" in tax.get("abdominal_muscles", set())

    def test_polyhierarchy_taxonomy(self, tmp_path):
        xml_path = _write_xml(tmp_path, POLYHIERARCHY_XML)
        ext = MeshExtractor(xml_path)
        ext.load()
        ext.extract()
        tax = ext.get_taxonomy()
        parents = tax.get("multi_parent_child", set())
        assert "parent_a" in parents
        assert "parent_b" in parents


# ── Convenience Function ─────────────────────────────────────────


class TestExtractFromMesh:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_mesh(tmp_path / "nonexistent.xml")

    def test_roundtrip(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        theory = extract_from_mesh(xml_path)
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) > 0
        assert len(theory.facts) > 0


# ── Normalize Helper ──────────────────────────────────────────────


class TestMeshNormalize:

    def test_lowercase_and_underscores(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        assert ext._normalize("Body Regions") == "body_regions"
        assert ext._normalize("Abdominal-Muscles") == "abdominal_muscles"

    def test_leading_digit(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        assert ext._normalize("3-Hydroxybutyrate") == "c_3_hydroxybutyrate"

    def test_special_chars_stripped(self, tmp_path):
        xml_path = _write_xml(tmp_path, MINIMAL_XML)
        ext = MeshExtractor(xml_path)
        assert ext._normalize("alpha,beta-test") == "alphabeta_test"
