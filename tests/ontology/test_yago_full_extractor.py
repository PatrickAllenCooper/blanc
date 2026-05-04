"""
Tests for YAGO 4.5 full extractor.

Uses tempfile to create small synthetic TTL files for stream parsing.
Covers prefix resolution, triple classification, theory rule types,
taxonomy and property extraction.

Author: Anonymous Authors
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import RuleType
from blanc.ontology.yago_full_extractor import (
    YagoFullExtractor,
    _TtlLineParser,
    _local_name,
    _normalize,
)


SAMPLE_TTL = """\
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix schema: <http://schema.org/> .
@prefix yago: <http://yago-knowledge.org/resource/> .

yago:Cat rdfs:subClassOf yago:Mammal .
yago:Dog rdfs:subClassOf yago:Mammal .
yago:Mammal rdfs:subClassOf yago:Animal .
yago:Felix rdf:type yago:Cat .
yago:Rex rdf:type yago:Dog .
yago:Felix schema:gender "male" .
yago:Rex schema:birthPlace yago:London .
yago:Felix yago:livesIn yago:Paris .
"""


def _write_ttl(content: str) -> Path:
    """Write TTL content to a temporary file and return the path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".ttl", delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return Path(f.name)


class TestNormalize:

    def test_lowercase_and_underscore(self):
        assert _normalize("BirthPlace") == "birth_place"
        assert _normalize("Person") == "person"

    def test_camel_case_split(self):
        assert _normalize("typicalAgeRange") == "typical_age_range"

    def test_leading_digit_prefixed(self):
        assert _normalize("123Thing") == "c_123thing"

    def test_spaces_and_hyphens(self):
        assert _normalize("some thing") == "some_thing"
        assert _normalize("some-thing") == "some_thing"


class TestLocalName:

    def test_hash_uri(self):
        assert _local_name("http://www.w3.org/1999/02/22-rdf-syntax-ns#type") == "type"

    def test_slash_uri(self):
        assert _local_name("http://schema.org/Person") == "Person"

    def test_prefixed_name(self):
        assert _local_name("schema:Person") == "Person"

    def test_plain_name(self):
        assert _local_name("Person") == "Person"


class TestTtlLineParser:

    def test_prefix_registration(self):
        parser = _TtlLineParser()
        parser.feed_line('@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .')
        assert "rdf:" in parser.prefixes
        assert parser.prefixes["rdf:"] == "http://www.w3.org/1999/02/22-rdf-syntax-ns#"

    def test_simple_triple(self):
        parser = _TtlLineParser()
        parser.feed_line('@prefix ex: <http://example.org/> .')
        result = parser.feed_line('ex:Cat ex:subClassOf ex:Animal .')
        assert result is not None
        subj, pred, obj = result
        assert subj == "http://example.org/Cat"
        assert pred == "http://example.org/subClassOf"
        assert obj == "http://example.org/Animal"

    def test_full_uri_triple(self):
        parser = _TtlLineParser()
        result = parser.feed_line(
            '<http://example.org/Cat> <http://example.org/type> <http://example.org/Animal> .'
        )
        assert result is not None
        assert result[0] == "http://example.org/Cat"

    def test_literal_object(self):
        parser = _TtlLineParser()
        parser.feed_line('@prefix schema: <http://schema.org/> .')
        result = parser.feed_line('schema:Felix schema:gender "male" .')
        assert result is not None
        assert result[2] == "male"

    def test_literal_with_datatype(self):
        parser = _TtlLineParser()
        result = parser.feed_line(
            '<http://ex.org/A> <http://ex.org/age> "42"^^<http://www.w3.org/2001/XMLSchema#integer> .'
        )
        assert result is not None
        assert result[2] == "42"

    def test_literal_with_language_tag(self):
        parser = _TtlLineParser()
        result = parser.feed_line(
            '<http://ex.org/A> <http://ex.org/name> "Felix"@en .'
        )
        assert result is not None
        assert result[2] == "Felix"

    def test_comment_line_ignored(self):
        parser = _TtlLineParser()
        assert parser.feed_line("# this is a comment") is None

    def test_blank_line_ignored(self):
        parser = _TtlLineParser()
        assert parser.feed_line("") is None
        assert parser.feed_line("   ") is None

    def test_blank_node_yields_empty(self):
        parser = _TtlLineParser()
        result = parser.feed_line(
            '_:b0 <http://ex.org/pred> <http://ex.org/obj> .'
        )
        assert result is None

    def test_multiline_triple(self):
        parser = _TtlLineParser()
        parser.feed_line('@prefix ex: <http://example.org/> .')
        assert parser.feed_line('ex:Cat ex:subClassOf') is None
        result = parser.feed_line('  ex:Animal .')
        assert result is not None
        assert "Cat" in result[0]
        assert "Animal" in result[2]

    def test_base_line_ignored(self):
        parser = _TtlLineParser()
        assert parser.feed_line("@base <http://example.org/> .") is None


class TestYagoFullExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            YagoFullExtractor(tmp_path / "nonexistent.ttl")

    def test_valid_file_accepted(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            assert ext.ttl_path == path
        finally:
            path.unlink()


class TestYagoFullExtraction:

    def test_subclass_pairs_extracted(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            assert len(ext.subclass_pairs) == 3
            children = {c for c, _ in ext.subclass_pairs}
            assert "Cat" in children
            assert "Dog" in children
            assert "Mammal" in children
        finally:
            path.unlink()

    def test_type_pairs_extracted(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            assert len(ext.type_pairs) == 2
            instances = {i for i, _ in ext.type_pairs}
            assert "Felix" in instances
            assert "Rex" in instances
        finally:
            path.unlink()

    def test_schema_properties_extracted(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            assert len(ext.schema_properties) == 2
            props = {p for _, p, _ in ext.schema_properties}
            assert "gender" in props
            assert "birthPlace" in props
        finally:
            path.unlink()

    def test_yago_properties_extracted(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            assert len(ext.yago_properties) == 1
            assert ext.yago_properties[0] == ("Felix", "livesIn", "Paris")
        finally:
            path.unlink()

    def test_max_triples_cap(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path, max_triples=3)
            ext.extract()
            assert ext._triples_parsed == 3
        finally:
            path.unlink()

    def test_stats_property(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            s = ext.stats
            assert s["triples_parsed"] == 8
            assert s["subclass_pairs"] == 3
            assert s["type_pairs"] == 2
            assert s["schema_properties"] == 2
            assert s["yago_properties"] == 1
        finally:
            path.unlink()


class TestYagoToTheory:

    def test_subclass_produces_strict_rules(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert len(strict) == 3
            for r in strict:
                assert r.metadata["relation"] == "subClassOf"
                assert r.metadata["source"] == "YAGO4.5"
        finally:
            path.unlink()

    def test_type_pairs_produce_facts(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            assert "instance(felix, cat)" in theory.facts
            assert "instance(rex, dog)" in theory.facts
        finally:
            path.unlink()

    def test_schema_properties_produce_defeasible_rules(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            schema_rules = [r for r in defeasible if "schema:" in r.metadata.get("relation", "")]
            assert len(schema_rules) >= 1
        finally:
            path.unlink()

    def test_yago_properties_produce_defeasible_rules(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            yago_rules = [r for r in defeasible if "yago:" in r.metadata.get("relation", "")]
            assert len(yago_rules) >= 1
        finally:
            path.unlink()

    def test_no_self_referencing_subclass_rules(self):
        ttl = """\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix yago: <http://yago-knowledge.org/resource/> .
yago:Thing rdfs:subClassOf yago:Thing .
"""
        path = _write_ttl(ttl)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert len(strict) == 0
        finally:
            path.unlink()


class TestYagoTaxonomy:

    def test_get_taxonomy_returns_parent_mapping(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            taxonomy = ext.get_taxonomy()
            assert "cat" in taxonomy
            assert "mammal" in taxonomy["cat"]
            assert "dog" in taxonomy
            assert "mammal" in taxonomy["dog"]
            assert "mammal" in taxonomy
            assert "animal" in taxonomy["mammal"]
        finally:
            path.unlink()


class TestYagoProperties:

    def test_get_properties_returns_relations(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            props = ext.get_properties()
            assert "felix" in props
            felix_rels = {r for r, _ in props["felix"]}
            assert "schema:gender" in felix_rels
            assert "yago:livesIn" in felix_rels
        finally:
            path.unlink()

    def test_get_properties_values(self):
        path = _write_ttl(SAMPLE_TTL)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            props = ext.get_properties()
            rex_vals = dict(props.get("rex", []))
            assert rex_vals.get("schema:birthPlace") == "london"
        finally:
            path.unlink()


class TestYagoDeduplication:

    def test_duplicate_subclass_produces_single_rule(self):
        ttl = """\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix yago: <http://yago-knowledge.org/resource/> .
yago:Cat rdfs:subClassOf yago:Mammal .
yago:Cat rdfs:subClassOf yago:Mammal .
"""
        path = _write_ttl(ttl)
        try:
            ext = YagoFullExtractor(path)
            ext.extract()
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert len(strict) == 1
        finally:
            path.unlink()
