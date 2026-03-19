"""
Tests for DBpedia N-Triples extractor.

Covers N-Triples line parsing, rdf:type -> facts, rdfs:subClassOf -> strict
rules, dbo:* -> defeasible rules, infobox/ontology type clash -> defeaters,
theory generation, and taxonomy output -- all using synthetic NT data.

Author: Patrick Cooper
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.dbpedia_extractor import (
    DbpediaExtractor,
    _parse_nt_line,
    _local_name,
    _normalize,
    extract_from_dbpedia,
)


# -- Helpers ---------------------------------------------------------------


def _write_nt(tmp_path: Path, lines: list[str], name: str = "test.nt") -> Path:
    nt_path = tmp_path / name
    nt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return nt_path


def _make_extractor(tmp_path: Path, lines: list[str], **kwargs) -> DbpediaExtractor:
    nt_path = _write_nt(tmp_path, lines)
    ext = DbpediaExtractor(nt_path, **kwargs)
    ext.extract()
    return ext


# -- NT Line Parser --------------------------------------------------------


class TestParseNtLine:

    def test_uri_triple(self):
        line = (
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .'
        )
        result = _parse_nt_line(line)
        assert result is not None
        subj, pred, obj = result
        assert "Berlin" in subj
        assert "type" in pred
        assert "City" in obj

    def test_literal_triple(self):
        line = (
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/populationTotal> '
            '"3748148"^^<http://www.w3.org/2001/XMLSchema#integer> .'
        )
        result = _parse_nt_line(line)
        assert result is not None
        _, _, obj = result
        assert obj == "3748148"

    def test_lang_tagged_literal(self):
        line = (
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/abstract> '
            '"Berlin is a city"@en .'
        )
        result = _parse_nt_line(line)
        assert result is not None
        _, _, obj = result
        assert obj == "Berlin is a city"

    def test_comment_returns_none(self):
        assert _parse_nt_line("# This is a comment") is None

    def test_blank_returns_none(self):
        assert _parse_nt_line("") is None
        assert _parse_nt_line("   \t  ") is None

    def test_malformed_returns_none(self):
        assert _parse_nt_line("not a triple at all") is None


# -- Local Name Extraction -------------------------------------------------


class TestLocalName:

    def test_slash_uri(self):
        assert _local_name("http://dbpedia.org/ontology/Person") == "Person"

    def test_hash_uri(self):
        assert _local_name("http://www.w3.org/1999/02/22-rdf-syntax-ns#type") == "type"

    def test_plain_string(self):
        assert _local_name("Person") == "Person"


# -- Normalize -------------------------------------------------------------


class TestNormalize:

    def test_camel_case_split(self):
        assert _normalize("PersonName") == "person_name"

    def test_lowercase(self):
        assert _normalize("City") == "city"

    def test_space_and_hyphen(self):
        assert _normalize("New-York City") == "new_york_city"

    def test_leading_digit(self):
        assert _normalize("3DModel") == "c_3dmodel"

    def test_special_chars_stripped(self):
        assert _normalize("alpha+beta") == "alphabeta"


# -- Extractor Init --------------------------------------------------------


class TestDbpediaExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            DbpediaExtractor(tmp_path / "nonexistent.nt")


# -- RDF Type Extraction (Facts) ------------------------------------------


class TestRdfTypeExtraction:

    def test_type_pair_extracted(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.type_pairs) == 1
        assert ext.type_pairs[0] == ("Berlin", "City")

    def test_type_added_to_dbo_type_map(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert "City" in ext.dbo_type_map["Berlin"]

    def test_dbp_property_type_added_to_dbp_map(self, tmp_path):
        lines = [
            '<http://dbpedia.org/property/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/property/Settlement> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert "Settlement" in ext.dbp_type_map["Berlin"]

    def test_multiple_types_for_same_entity(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/Place> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.type_pairs) == 2


# -- SubClassOf Extraction (Strict) ---------------------------------------


class TestSubClassOfExtraction:

    def test_subclass_pair_extracted(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.subclass_pairs) == 1
        assert ext.subclass_pairs[0] == ("City", "Settlement")

    def test_multiple_subclass(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
            '<http://dbpedia.org/ontology/Settlement> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Place> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.subclass_pairs) == 2


# -- DBO Property Extraction (Defeasible) ----------------------------------


class TestDboPropertyExtraction:

    def test_dbo_property_extracted(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/country> '
            '<http://dbpedia.org/resource/Germany> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.dbo_properties) == 1
        assert ext.dbo_properties[0] == ("Berlin", "country", "Germany")

    def test_multiple_dbo_properties(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/country> '
            '<http://dbpedia.org/resource/Germany> .',
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/leader> '
            '<http://dbpedia.org/resource/Franziska_Giffey> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        assert len(ext.dbo_properties) == 2


# -- Type Clash Detection (Defeaters) -------------------------------------


class TestTypeClashDetection:

    def test_infobox_ontology_clash(self, tmp_path):
        lines = [
            '<http://dbpedia.org/property/Mars> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/property/Planet> .',
            '<http://dbpedia.org/ontology/Mars> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/CelestialBody> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        conflicts = ext._find_type_conflicts()
        assert len(conflicts) >= 1
        entities = [c[0] for c in conflicts]
        assert "Mars" in entities

    def test_no_clash_when_types_agree(self, tmp_path):
        lines = [
            '<http://dbpedia.org/property/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/property/City> .',
            '<http://dbpedia.org/ontology/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        conflicts = ext._find_type_conflicts()
        assert len(conflicts) == 0


# -- Max Triples -----------------------------------------------------------


class TestMaxTriples:

    def test_max_triples_caps_output(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/A> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/X> .',
            '<http://dbpedia.org/resource/B> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/Y> .',
            '<http://dbpedia.org/resource/C> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/Z> .',
        ]
        ext = _make_extractor(tmp_path, lines, max_triples=2)
        assert ext._triples_parsed == 2


# -- Theory Conversion ----------------------------------------------------


class TestDbpediaToTheory:

    def test_subclass_produces_strict_rule(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        assert strict[0].head == "isa(city, settlement)"

    def test_rdf_type_produces_fact(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert "instance(berlin, city)" in theory.facts

    def test_dbo_property_produces_defeasible_rule(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/country> '
            '<http://dbpedia.org/resource/Germany> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert defeasible[0].head == "country(berlin, germany)"

    def test_type_clash_produces_defeater(self, tmp_path):
        lines = [
            '<http://dbpedia.org/property/Mars> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/property/Planet> .',
            '<http://dbpedia.org/ontology/Mars> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/CelestialBody> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 1
        assert any("~instance" in d.head for d in defeaters)

    def test_metadata_source_is_dbpedia(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "DBpedia"

    def test_duplicate_subclass_not_repeated(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1

    def test_mixed_relations_theory(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
            '<http://dbpedia.org/resource/Berlin> '
            '<http://dbpedia.org/ontology/country> '
            '<http://dbpedia.org/resource/Germany> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1
        assert "instance(berlin, city)" in theory.facts


# -- Taxonomy --------------------------------------------------------------


class TestDbpediaGetTaxonomy:

    def test_taxonomy_structure(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
            '<http://dbpedia.org/ontology/Settlement> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Place> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert tax["city"] == {"settlement"}
        assert tax["settlement"] == {"place"}
        assert "place" not in tax

    def test_self_reference_excluded(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/Thing> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Thing> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        tax = ext.get_taxonomy()
        assert len(tax) == 0


# -- Stats -----------------------------------------------------------------


class TestDbpediaStats:

    def test_stats_keys(self, tmp_path):
        lines = [
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        ext = _make_extractor(tmp_path, lines)
        stats = ext.stats
        expected_keys = {
            "triples_parsed", "triples_skipped",
            "type_pairs", "subclass_pairs",
            "dbo_properties", "type_conflicts",
        }
        assert set(stats.keys()) == expected_keys
        assert stats["triples_parsed"] == 1


# -- Convenience Function -------------------------------------------------


class TestExtractFromDbpedia:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_dbpedia(tmp_path / "nonexistent.nt")

    def test_roundtrip(self, tmp_path):
        lines = [
            '<http://dbpedia.org/ontology/City> '
            '<http://www.w3.org/2000/01/rdf-schema#subClassOf> '
            '<http://dbpedia.org/ontology/Settlement> .',
            '<http://dbpedia.org/resource/Berlin> '
            '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type> '
            '<http://dbpedia.org/ontology/City> .',
        ]
        nt_path = _write_nt(tmp_path, lines)
        theory = extract_from_dbpedia(nt_path)
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert "instance(berlin, city)" in theory.facts
