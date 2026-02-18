"""
Targeted tests for codec/nl_mapping.py coverage gaps.

Covers: _verify_injectivity, from_nl, has_mapping, add_mapping,
get_nl_mapping error path (lines 122-125, 150-151, 155, 168-170, 196).

Author: Patrick Cooper
Date: 2026-02-18
"""

import pytest
from blanc.codec.nl_mapping import (
    NLMapping,
    get_nl_mapping,
    biology_nl,
    legal_nl,
    materials_nl,
)


class TestNLMappingInjectivity:
    def test_duplicate_nl_phrases_raises(self):
        """Duplicate NL phrases violate injectivity and raise ValueError."""
        bad_mapping = {
            "pred_a": "is able to fly",
            "pred_b": "is able to fly",  # duplicate
        }
        with pytest.raises(ValueError, match="not injective"):
            NLMapping(bad_mapping)

    def test_unique_phrases_accepted(self):
        """Unique NL phrases pass injectivity check."""
        good = {"pred_a": "can fly", "pred_b": "can swim"}
        m = NLMapping(good)
        assert m.to_nl("pred_a") == "can fly"


class TestFromNl:
    def test_from_nl_returns_predicate(self):
        m = NLMapping({"flies": "can fly", "swims": "can swim"})
        assert m.from_nl("can fly") == "flies"
        assert m.from_nl("can swim") == "swims"

    def test_from_nl_unknown_returns_none(self):
        m = NLMapping({"flies": "can fly"})
        assert m.from_nl("unknown phrase") is None


class TestHasMapping:
    def test_known_predicate_returns_true(self):
        m = NLMapping({"flies": "can fly"})
        assert m.has_mapping("flies") is True

    def test_unknown_predicate_returns_false(self):
        m = NLMapping({"flies": "can fly"})
        assert m.has_mapping("walks") is False


class TestAddMapping:
    def test_add_new_mapping(self):
        m = NLMapping({"flies": "can fly"})
        m.add_mapping("walks", "can walk")
        assert m.has_mapping("walks")
        assert m.to_nl("walks") == "can walk"

    def test_add_duplicate_nl_phrase_raises(self):
        m = NLMapping({"flies": "can fly"})
        with pytest.raises(ValueError, match="already mapped"):
            m.add_mapping("soars", "can fly")


class TestGetNlMapping:
    def test_biology_mapping_returned(self):
        mapping = get_nl_mapping("biology")
        assert mapping is biology_nl

    def test_legal_mapping_returned(self):
        mapping = get_nl_mapping("legal")
        assert mapping is legal_nl

    def test_materials_mapping_returned(self):
        mapping = get_nl_mapping("materials")
        assert mapping is materials_nl

    def test_unknown_domain_raises(self):
        with pytest.raises(ValueError, match="Unknown domain"):
            get_nl_mapping("physics")
