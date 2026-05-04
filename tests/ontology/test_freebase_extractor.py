"""
Tests for Freebase N-Triples extractor.

Covers N-Triples parsing with Freebase MID format (/m/012abc),
type.object.type -> strict type facts, type.type.instance -> instance
facts, other predicates -> defeasible rules, cross-domain type conflict
detection -> defeaters, theory generation, and taxonomy output.

Author: Anonymous Authors
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.freebase_extractor import (
    FreebaseExtractor,
    _parse_nt_line,
    _freebase_local,
    _mid_to_id,
    _type_path_to_name,
    _is_mid,
    _normalize,
    extract_from_freebase,
)


# -- Helpers ---------------------------------------------------------------


def _write_nt(tmp_path: Path, lines: list[str], name: str = "test.nt") -> Path:
    nt_path = tmp_path / name
    nt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return nt_path


def _make_extractor(tmp_path: Path, lines: list[str], **kwargs) -> FreebaseExtractor:
    nt_path = _write_nt(tmp_path, lines)
    ext = FreebaseExtractor(nt_path, **kwargs)
    ext.extract()
    return ext


# -- Freebase Local / MID Helpers ------------------------------------------


class TestFreebaseLocal:

    def test_freebase_ns_prefix(self):
        uri = "http://rdf.freebase.com/ns/m.012abc"
        assert _freebase_local(uri) == "m.012abc"

    def test_freebase_key_prefix(self):
        uri = "http://rdf.freebase.com/key/en.berlin"
        assert _freebase_local(uri) == "en.berlin"

    def test_type_path(self):
        uri = "http://rdf.freebase.com/ns/type.object.type"
        assert _freebase_local(uri) == "type.object.type"

    def test_hash_uri(self):
        uri = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
        assert _freebase_local(uri) == "type"

    def test_plain_uri(self):
        uri = "http://example.org/foo/bar"
        assert _freebase_local(uri) == "bar"


class TestMidToId:

    def test_dot_format(self):
        assert _mid_to_id("m.012abc") == "m_012abc"

    def test_slash_format(self):
        assert _mid_to_id("/m/012abc") == "m_012abc"

    def test_g_prefix(self):
        assert _mid_to_id("g.11abc") == "g_11abc"


class TestTypePathToName:

    def test_dotted_path(self):
        assert _type_path_to_name("biology.organism") == "biology_organism"

    def test_slash_path(self):
        assert _type_path_to_name("/type/typename") == "type_typename"


class TestIsMid:

    def test_m_prefix(self):
        assert _is_mid("m.012abc") is True

    def test_g_prefix(self):
        assert _is_mid("g.11abc") is True

    def test_type_path_not_mid(self):
        assert _is_mid("type.object.type") is False

    def test_plain_not_mid(self):
        assert _is_mid("biology.organism") is False


class TestNormalize:

    def test_dots_to_underscores(self):
        assert _normalize("type.object.type") == "type_object_type"

    def test_lowercase(self):
        assert _normalize("Person") == "person"

    def test_leading_digit(self):
        assert _normalize("3dmodel") == "c_3dmodel"


# -- Extractor Init --------------------------------------------------------


class TestFreebaseExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            FreebaseExtractor(tmp_path / "nonexistent.nt")


# -- type.object.type Extraction -------------------------------------------


class TestTypeObjectTypeExtraction:

    def test_type_assignment_extracted(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.type_assignments) == 1
        entity, type_name = ext.type_assignments[0]
        assert entity == "m_012abc"
        assert type_name == "people_person"

    def test_rdf_type_also_captured(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.type_assignments) == 1

    def test_entity_types_tracked(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/music.artist> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext._entity_types["m_012abc"]) == 2


# -- type.type.instance Extraction ----------------------------------------


class TestTypeTypeInstanceExtraction:

    def test_instance_pair_extracted(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/people.person> '
            '<http://rdf.freebase.com/ns/type.type.instance> '
            '<http://rdf.freebase.com/ns/m.099def> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.instance_pairs) == 1
        entity, type_name = ext.instance_pairs[0]
        assert entity == "m_099def"
        assert type_name == "people_person"


# -- Other Relations (Defeasible) ------------------------------------------


class TestTypedRelationExtraction:

    def test_typed_relation_extracted(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/people.person.nationality> '
            '<http://rdf.freebase.com/ns/m.0d060g> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.typed_relations) == 1
        subj, rel, obj = ext.typed_relations[0]
        assert subj == "m_012abc"
        assert "people_person_nationality" == rel
        assert obj == "m_0d060g"

    def test_skip_predicates_ignored(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.name> '
            '"Some Name"@en .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.typed_relations) == 0
        assert len(ext.type_assignments) == 0


# -- Conflict Detection (Defeaters) ---------------------------------------


class TestFreebaseConflictDetection:

    def test_cross_domain_conflict(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.deceased_person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        conflicts = ext._find_type_conflicts()
        assert len(conflicts) >= 1
        entities = [c[0] for c in conflicts]
        assert "m_012abc" in entities

    def test_no_conflict_different_domains(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/music.artist> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        conflicts = ext._find_type_conflicts()
        assert len(conflicts) == 0

    def test_single_type_no_conflict(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        conflicts = ext._find_type_conflicts()
        assert len(conflicts) == 0


# -- Max Triples -----------------------------------------------------------


class TestFreebaseMaxTriples:

    def test_max_triples_caps_output(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.01> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.02> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.03> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines, max_triples=2)
        assert ext._triples_parsed == 2


# -- Theory Conversion ----------------------------------------------------


class TestFreebaseToTheory:

    def test_type_assignment_produces_fact(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert "instance(m_012abc, people_person)" in theory.facts

    def test_instance_pair_produces_fact(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/people.person> '
            '<http://rdf.freebase.com/ns/type.type.instance> '
            '<http://rdf.freebase.com/ns/m.099def> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert "instance(m_099def, people_person)" in theory.facts

    def test_typed_relation_produces_defeasible(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/people.person.nationality> '
            '<http://rdf.freebase.com/ns/m.0d060g> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert defeasible[0].head == "people_person_nationality(m_012abc, m_0d060g)"

    def test_conflict_produces_defeater(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.deceased_person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 1
        assert any("~instance" in d.head for d in defeaters)

    def test_metadata_source_is_freebase(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/people.person.nationality> '
            '<http://rdf.freebase.com/ns/m.0d060g> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "Freebase"

    def test_mixed_relations_theory(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/people.person> '
            '<http://rdf.freebase.com/ns/type.type.instance> '
            '<http://rdf.freebase.com/ns/m.099def> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/people.person.nationality> '
            '<http://rdf.freebase.com/ns/m.0d060g> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert len(theory.facts) >= 2
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) >= 1


# -- Taxonomy --------------------------------------------------------------


class TestFreebaseGetTaxonomy:

    def test_taxonomy_from_type_assignments(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert "people_person" in tax.get("m_012abc", set())

    def test_taxonomy_from_instance_pairs(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/people.person> '
            '<http://rdf.freebase.com/ns/type.type.instance> '
            '<http://rdf.freebase.com/ns/m.099def> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert "people_person" in tax.get("m_099def", set())


# -- Stats -----------------------------------------------------------------


class TestFreebaseStats:

    def test_stats_keys(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        stats = ext.stats
        expected_keys = {
            "triples_parsed", "triples_skipped",
            "type_assignments", "instance_pairs",
            "typed_relations", "type_conflicts",
        }
        assert set(stats.keys()) == expected_keys


# -- Convenience Function -------------------------------------------------


class TestExtractFromFreebase:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_freebase(tmp_path / "nonexistent.nt")

    def test_roundtrip(self, tmp_path):
        lines = [
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/type.object.type> '
            '<http://rdf.freebase.com/ns/people.person> .',
            '<http://rdf.freebase.com/ns/m.012abc> '
            '<http://rdf.freebase.com/ns/people.person.nationality> '
            '<http://rdf.freebase.com/ns/m.0d060g> .',
        ]
        nt_path = _write_nt(tmp_path, lines)
        theory = extract_from_freebase(nt_path)
        assert "instance(m_012abc, people_person)" in theory.facts
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) >= 1
