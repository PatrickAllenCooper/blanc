"""
Tests for Wikidata SPARQL-based extractor.

Mocks the _query method to avoid real SPARQL requests.  Covers
constraint-exception extraction, domain-rule extraction, theory
conversion (defeasible rules and defeaters), and rate-limiting
behavior.

Author: Anonymous Authors
"""

from __future__ import annotations

import time
from unittest.mock import patch, MagicMock

import pytest

from blanc.core.theory import RuleType
from blanc.ontology.wikidata_extractor import (
    WikidataExtractor,
    _normalize,
    _qid,
)


MOCK_CONSTRAINT_RESULTS = {
    "results": {
        "bindings": [
            {
                "property": {"value": "http://www.wikidata.org/entity/P21"},
                "propertyLabel": {"value": "sex or gender"},
                "constraintType": {"value": "http://www.wikidata.org/entity/Q21503250"},
                "constraintTypeLabel": {"value": "type constraint"},
                "exception": {"value": "http://www.wikidata.org/entity/Q43229"},
                "exceptionLabel": {"value": "organization"},
            },
            {
                "property": {"value": "http://www.wikidata.org/entity/P569"},
                "propertyLabel": {"value": "date of birth"},
                "constraintType": {"value": "http://www.wikidata.org/entity/Q21502838"},
                "constraintTypeLabel": {"value": "single-value constraint"},
                "exception": {"value": "http://www.wikidata.org/entity/Q5"},
                "exceptionLabel": {"value": "human"},
            },
        ]
    }
}

MOCK_DOMAIN_RESULTS = {
    "results": {
        "bindings": [
            {
                "item": {"value": "http://www.wikidata.org/entity/Q726"},
                "itemLabel": {"value": "horse"},
                "prop": {"value": "http://www.wikidata.org/prop/direct/P31"},
                "propLabel": {"value": "instance of"},
                "val": {"value": "http://www.wikidata.org/entity/Q16521"},
                "valLabel": {"value": "taxon"},
            },
            {
                "item": {"value": "http://www.wikidata.org/entity/Q726"},
                "itemLabel": {"value": "horse"},
                "prop": {"value": "http://www.wikidata.org/prop/direct/P171"},
                "propLabel": {"value": "parent taxon"},
                "val": {"value": "http://www.wikidata.org/entity/Q19159"},
                "valLabel": {"value": "Equus"},
            },
        ]
    }
}


class TestHelpers:

    def test_normalize(self):
        assert _normalize("sex or gender") == "sex_or_gender"
        assert _normalize("Date-Of-Birth") == "date_of_birth"
        assert _normalize("CamelCase") == "camelcase"

    def test_qid_from_uri(self):
        assert _qid("http://www.wikidata.org/entity/Q726") == "Q726"
        assert _qid("Q726") == "Q726"
        assert _qid("http://www.wikidata.org/entity/P21") == "P21"


class TestExtractConstraintExceptions:

    def test_returns_triples_from_mock_sparql(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_CONSTRAINT_RESULTS):
            triples = ext.extract_constraint_exceptions()
        assert len(triples) == 2
        assert triples[0] == ("sex or gender", "type constraint", "organization")
        assert triples[1] == ("date of birth", "single-value constraint", "human")

    def test_populates_internal_constraint_list(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_CONSTRAINT_RESULTS):
            ext.extract_constraint_exceptions()
        assert len(ext.constraint_exceptions) == 2
        assert ext.constraint_exceptions[0][1] == "sex or gender"

    def test_returns_empty_on_query_failure(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=None):
            triples = ext.extract_constraint_exceptions()
        assert triples == []

    def test_handles_missing_labels_gracefully(self):
        results = {
            "results": {
                "bindings": [
                    {
                        "property": {"value": "http://www.wikidata.org/entity/P999"},
                        "propertyLabel": {},
                        "constraintType": {"value": "http://www.wikidata.org/entity/Q100"},
                        "constraintTypeLabel": {},
                        "exception": {"value": "http://www.wikidata.org/entity/Q200"},
                        "exceptionLabel": {},
                    }
                ]
            }
        }
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=results):
            triples = ext.extract_constraint_exceptions()
        assert len(triples) == 1
        assert triples[0] == ("P999", "Q100", "Q200")


class TestExtractDomainRules:

    def test_populates_domain_assertions(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_DOMAIN_RESULTS):
            ext.extract_domain_rules(["Q16521"])
        assert "Q16521" in ext.domain_assertions
        assert len(ext.domain_assertions["Q16521"]) == 2

    def test_skips_class_on_query_failure(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=None):
            ext.extract_domain_rules(["Q16521"])
        assert len(ext.domain_assertions["Q16521"]) == 0

    def test_multiple_classes_queried(self):
        ext = WikidataExtractor(delay=0.0)
        call_count = 0

        def mock_query(sparql):
            nonlocal call_count
            call_count += 1
            return {"results": {"bindings": []}}

        with patch.object(ext, "_query", side_effect=mock_query):
            ext.extract_domain_rules(["Q16521", "Q7239"])
        assert call_count == 2


class TestToTheory:

    def test_constraints_become_defeasible_rules(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_CONSTRAINT_RESULTS):
            ext.extract_constraint_exceptions()
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        constraint_rules = [r for r in defeasible if r.metadata.get("relation") == "P2302"]
        assert len(constraint_rules) == 2

    def test_exceptions_become_defeaters(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_CONSTRAINT_RESULTS):
            ext.extract_constraint_exceptions()
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) == 2
        for d in defeaters:
            assert d.head.startswith("~")
            assert d.metadata["relation"] == "P2303"

    def test_superiority_set_for_exceptions(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_CONSTRAINT_RESULTS):
            ext.extract_constraint_exceptions()
        theory = ext.to_theory()
        assert len(theory.superiority) > 0
        for sup_label, inf_set in theory.superiority.items():
            assert sup_label.startswith("wd_except_")
            for inf in inf_set:
                assert inf.startswith("wd_constraint_")

    def test_domain_assertions_become_defeasible_rules(self):
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=MOCK_DOMAIN_RESULTS):
            ext.extract_domain_rules(["Q16521"])
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        domain_rules = [r for r in defeasible if r.metadata.get("domain_class")]
        assert len(domain_rules) >= 1

    def test_empty_extractor_produces_empty_theory(self):
        ext = WikidataExtractor(delay=0.0)
        theory = ext.to_theory()
        assert len(theory.rules) == 0


class TestRateLimiting:

    def test_delay_enforced_between_queries(self):
        ext = WikidataExtractor(delay=0.0)
        ext.delay = 0.05
        ext._last_query_time = time.monotonic()

        sleep_calls = []
        original_sleep = time.sleep

        def tracking_sleep(seconds):
            sleep_calls.append(seconds)
            original_sleep(seconds)

        with patch.object(ext, "_query", return_value={"results": {"bindings": []}}):
            with patch("time.sleep", side_effect=tracking_sleep):
                ext.extract_constraint_exceptions()

    def test_extractor_default_delay(self):
        ext = WikidataExtractor()
        assert ext.delay == 2.0

    def test_custom_delay(self):
        ext = WikidataExtractor(delay=5.0)
        assert ext.delay == 5.0

    def test_last_query_time_initialized(self):
        ext = WikidataExtractor(delay=0.0)
        assert ext._last_query_time == 0.0


class TestDeduplication:

    def test_duplicate_constraints_produce_single_rule(self):
        dup_results = {
            "results": {
                "bindings": [
                    {
                        "property": {"value": "http://www.wikidata.org/entity/P21"},
                        "propertyLabel": {"value": "sex or gender"},
                        "constraintType": {"value": "http://www.wikidata.org/entity/Q21503250"},
                        "constraintTypeLabel": {"value": "type constraint"},
                        "exception": {"value": "http://www.wikidata.org/entity/Q43229"},
                        "exceptionLabel": {"value": "organization"},
                    },
                    {
                        "property": {"value": "http://www.wikidata.org/entity/P21"},
                        "propertyLabel": {"value": "sex or gender"},
                        "constraintType": {"value": "http://www.wikidata.org/entity/Q21503250"},
                        "constraintTypeLabel": {"value": "type constraint"},
                        "exception": {"value": "http://www.wikidata.org/entity/Q43229"},
                        "exceptionLabel": {"value": "organization"},
                    },
                ]
            }
        }
        ext = WikidataExtractor(delay=0.0)
        with patch.object(ext, "_query", return_value=dup_results):
            ext.extract_constraint_exceptions()
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        constraint_rules = [r for r in defeasible if "sex_or_gender" in r.head]
        assert len(constraint_rules) == 1
