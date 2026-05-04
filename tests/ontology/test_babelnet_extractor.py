"""
Tests for BabelNet REST API extractor.

Covers synset relation extraction via mocked HTTP responses,
hypernymy -> strict rules, other relations -> defeasible rules,
cross-language inconsistencies -> defeaters, rate limiting
configuration, theory generation, taxonomy output, and the
convenience function -- all without real API calls.

Author: Anonymous Authors
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

from blanc.core.theory import RuleType
from blanc.ontology.babelnet_extractor import (
    BabelNetExtractor,
    _normalize,
    _bn_id,
    STRICT_RELATION_GROUPS,
    DEFEASIBLE_RELATION_GROUPS,
    extract_from_babelnet,
)


# -- Helpers ---------------------------------------------------------------


def _mock_synset_response(synset_id: str, lemma: str = "test") -> dict:
    return {
        "senses": [
            {
                "properties": {
                    "simpleLemma": lemma,
                    "lemma": lemma,
                },
            },
        ],
    }


def _mock_edge(
    target: str,
    rel_group: str = "HYPERNYM",
    short_name: str = "is-a",
    language: str = "EN",
) -> dict:
    return {
        "target": target,
        "pointer": {
            "relationGroup": rel_group,
            "shortName": short_name,
        },
        "language": language,
    }


def _make_extractor(**kwargs) -> BabelNetExtractor:
    return BabelNetExtractor(api_key="test-key-000", **kwargs)


# -- Normalize / BN ID -----------------------------------------------------


class TestNormalize:

    def test_lowercase(self):
        assert _normalize("Animal") == "animal"

    def test_hyphens_and_spaces(self):
        assert _normalize("living-thing entity") == "living_thing_entity"

    def test_leading_digit(self):
        assert _normalize("3DModel") == "c_3dmodel"

    def test_special_chars(self):
        assert _normalize("alpha+beta") == "alphabeta"


class TestBnId:

    def test_colon_replaced(self):
        assert _bn_id("bn:00000001n") == "bn_00000001n"

    def test_no_colon(self):
        assert _bn_id("bn_00000001n") == "bn_00000001n"


# -- Extractor Init --------------------------------------------------------


class TestBabelNetExtractorInit:

    def test_default_delay(self):
        ext = _make_extractor()
        assert ext.delay == 1.0

    def test_custom_delay(self):
        ext = _make_extractor(delay=0.5)
        assert ext.delay == 0.5

    def test_api_key_stored(self):
        ext = _make_extractor()
        assert ext.api_key == "test-key-000"


# -- Synset Relation Extraction (Mocked) -----------------------------------


class TestExtractSynsetRelations:

    @patch.object(BabelNetExtractor, "_request")
    def test_hypernym_edge_stored(self, mock_request):
        mock_request.side_effect = [
            _mock_synset_response("bn:00000001n", "animal"),
            [_mock_edge("bn:00000002n", "HYPERNYM", "is-a", "EN")],
            _mock_synset_response("bn:00000002n", "living_thing"),
        ]
        ext = _make_extractor()
        ext.extract_synset_relations(["bn:00000001n"])
        assert len(ext.edges) == 1
        source, target, rel_group, rel_name, lang = ext.edges[0]
        assert source == "bn:00000001n"
        assert target == "bn:00000002n"
        assert rel_group == "HYPERNYM"
        assert lang == "EN"

    @patch.object(BabelNetExtractor, "_request")
    def test_multiple_edges_stored(self, mock_request):
        mock_request.side_effect = [
            _mock_synset_response("bn:00000001n", "dog"),
            [
                _mock_edge("bn:00000002n", "HYPERNYM", "is-a"),
                _mock_edge("bn:00000003n", "MERONYM", "part-of"),
            ],
            _mock_synset_response("bn:00000002n", "animal"),
            _mock_synset_response("bn:00000003n", "tail"),
        ]
        ext = _make_extractor()
        ext.extract_synset_relations(["bn:00000001n"])
        assert len(ext.edges) == 2

    @patch.object(BabelNetExtractor, "_request")
    def test_synset_metadata_cached(self, mock_request):
        mock_request.side_effect = [
            _mock_synset_response("bn:00000001n", "dog"),
            [],
        ]
        ext = _make_extractor()
        ext.extract_synset_relations(["bn:00000001n"])
        assert "bn:00000001n" in ext.synsets
        assert ext.synsets["bn:00000001n"]["main_sense"] == "dog"

    @patch.object(BabelNetExtractor, "_request")
    def test_empty_edges_response(self, mock_request):
        mock_request.side_effect = [
            _mock_synset_response("bn:00000001n", "concept"),
            [],
        ]
        ext = _make_extractor()
        ext.extract_synset_relations(["bn:00000001n"])
        assert len(ext.edges) == 0

    @patch.object(BabelNetExtractor, "_request")
    def test_none_edges_response(self, mock_request):
        mock_request.side_effect = [
            _mock_synset_response("bn:00000001n", "concept"),
            None,
        ]
        ext = _make_extractor()
        ext.extract_synset_relations(["bn:00000001n"])
        assert len(ext.edges) == 0


# -- Cross-Language Conflict Detection (Defeaters) -------------------------


class TestCrossLanguageConflicts:

    def test_conflict_detected(self):
        ext = _make_extractor()
        ext.synsets["bn:00000001n"] = {"main_sense": "word", "senses": [], "raw": {}}
        ext.synsets["bn:00000002n"] = {"main_sense": "concept", "senses": [], "raw": {}}
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "IT"),
        ]
        ext._detect_cross_language_conflicts()
        assert len(ext._contradictions) >= 1

    def test_no_conflict_single_language(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "EN"),
        ]
        ext._detect_cross_language_conflicts()
        assert len(ext._contradictions) == 0

    def test_no_conflict_same_group(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "IT"),
        ]
        ext._detect_cross_language_conflicts()
        assert len(ext._contradictions) == 0

    def test_conflict_with_multiple_languages(self):
        ext = _make_extractor()
        ext.synsets["bn:00000001n"] = {"main_sense": "a", "senses": [], "raw": {}}
        ext.synsets["bn:00000002n"] = {"main_sense": "b", "senses": [], "raw": {}}
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "HOLONYM", "whole-of", "DE"),
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "FR"),
        ]
        ext._detect_cross_language_conflicts()
        assert len(ext._contradictions) >= 1


# -- Rate Limiting ---------------------------------------------------------


class TestRateLimiting:

    def test_delay_attribute(self):
        ext = _make_extractor(delay=2.5)
        assert ext.delay == 2.5

    def test_last_request_time_initialized(self):
        ext = _make_extractor()
        assert ext._last_request_time == 0.0


# -- Theory Conversion ----------------------------------------------------


class TestBabelNetToTheory:

    def test_hypernym_produces_strict_isa(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "dog", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "animal", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
        ]
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        assert strict[0].head == "isa(bn_00000001n, bn_00000002n)"

    def test_hyponym_produces_reverse_isa(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "animal", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "dog", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPONYM", "has-kind", "EN"),
        ]
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        assert strict[0].head == "isa(bn_00000002n, bn_00000001n)"

    def test_meronym_produces_defeasible(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "car", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "wheel", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "EN"),
        ]
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert "part_of" in defeasible[0].head

    def test_semantically_related_produces_defeasible(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "heat", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "temperature", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "SEMANTICALLY_RELATED", "related", "EN"),
        ]
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1

    def test_conflict_produces_defeater(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "word", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "concept", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "IT"),
        ]
        ext._detect_cross_language_conflicts()
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 1
        assert any("~isa" in d.head for d in defeaters)

    def test_superiority_added_for_conflict(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "word", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "concept", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "IT"),
        ]
        ext._detect_cross_language_conflicts()
        theory = ext.to_theory()
        assert len(theory.superiority) >= 1

    def test_metadata_source_is_babelnet(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "dog", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "animal", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
        ]
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "BabelNet"

    def test_metadata_includes_lemmas(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "dog", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "animal", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
        ]
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert strict[0].metadata["source_lemma"] == "dog"
        assert strict[0].metadata["target_lemma"] == "animal"

    def test_duplicate_edge_not_repeated(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "dog", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "animal", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
        ]
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1

    def test_mixed_relations_theory(self):
        ext = _make_extractor()
        ext.synsets = {
            "bn:00000001n": {"main_sense": "dog", "senses": [], "raw": {}},
            "bn:00000002n": {"main_sense": "animal", "senses": [], "raw": {}},
            "bn:00000003n": {"main_sense": "tail", "senses": [], "raw": {}},
        }
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
            ("bn:00000001n", "bn:00000003n", "MERONYM", "part-of", "EN"),
        ]
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1


# -- Taxonomy --------------------------------------------------------------


class TestBabelNetGetTaxonomy:

    def test_hypernym_in_taxonomy(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPERNYM", "is-a", "EN"),
        ]
        tax = ext.get_taxonomy()
        assert "bn_00000002n" in tax.get("bn_00000001n", set())

    def test_hyponym_reversed_in_taxonomy(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "HYPONYM", "has-kind", "EN"),
        ]
        tax = ext.get_taxonomy()
        assert "bn_00000001n" in tax.get("bn_00000002n", set())

    def test_non_taxonomic_excluded(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "MERONYM", "part-of", "EN"),
        ]
        tax = ext.get_taxonomy()
        assert len(tax) == 0

    def test_any_hypernym_included(self):
        ext = _make_extractor()
        ext.edges = [
            ("bn:00000001n", "bn:00000002n", "ANY_HYPERNYM", "hypernym", "EN"),
        ]
        tax = ext.get_taxonomy()
        assert "bn_00000002n" in tax.get("bn_00000001n", set())


# -- Synset Label Helper ---------------------------------------------------


class TestSynsetLabel:

    def test_known_synset(self):
        ext = _make_extractor()
        ext.synsets["bn:00000001n"] = {"main_sense": "dog", "senses": [], "raw": {}}
        assert ext._synset_label("bn:00000001n") == "dog"

    def test_unknown_synset_returns_id(self):
        ext = _make_extractor()
        assert ext._synset_label("bn:99999999n") == "bn:99999999n"

    def test_empty_lemma_returns_id(self):
        ext = _make_extractor()
        ext.synsets["bn:00000001n"] = {"main_sense": "", "senses": [], "raw": {}}
        assert ext._synset_label("bn:00000001n") == "bn:00000001n"


# -- Convenience Function -------------------------------------------------


class TestExtractFromBabelnet:

    @patch.object(BabelNetExtractor, "_request")
    def test_roundtrip(self, mock_request):
        mock_request.side_effect = [
            [{"id": "bn:00000001n"}],
            _mock_synset_response("bn:00000001n", "biology"),
            [_mock_edge("bn:00000002n", "HYPERNYM", "is-a")],
            _mock_synset_response("bn:00000002n", "science"),
            [],
        ]
        theory = extract_from_babelnet(
            api_key="test-key",
            domain="biology",
            limit=2,
            delay=0.0,
        )
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) >= 1
