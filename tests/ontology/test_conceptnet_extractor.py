"""
Comprehensive tests for ConceptNet5 extractor.

Tests extraction logic across multiple domains with all supported
relation types.

Author: Patrick Cooper
"""

import gzip
import json
import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import RuleType
from blanc.ontology.conceptnet_extractor import (
    ConceptNetExtractor,
    extract_biology_from_conceptnet,
    extract_from_conceptnet,
)
from blanc.ontology.domain_profiles import BIOLOGY, LEGAL, MATERIALS


def _make_edge(relation, start, end, weight=5.0):
    meta = json.dumps({"weight": weight})
    return (
        f"/a/[/r/{relation}]/[/c/en/{start}]/[/c/en/{end}]/\t"
        f"/r/{relation}\t/c/en/{start}\t/c/en/{end}\t{meta}"
    )


def _write_sample(lines):
    f = tempfile.NamedTemporaryFile(
        mode="wb", suffix=".csv.gz", delete=False
    )
    with gzip.open(f.name, "wt", encoding="utf-8") as gz:
        for line in lines:
            gz.write(line + "\n")
    return Path(f.name)


class TestConceptNetExtractorInit:

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            ConceptNetExtractor(tmp_path / "nope.csv.gz")

    def test_default_profile_is_biology(self):
        path = _write_sample([_make_edge("IsA", "bird", "animal")])
        try:
            ext = ConceptNetExtractor(path)
            assert ext.profile.name == "biology"
        finally:
            path.unlink()


class TestHelpers:

    def test_extract_concept(self):
        path = _write_sample([_make_edge("IsA", "bird", "animal")])
        try:
            ext = ConceptNetExtractor(path)
            assert ext._extract_concept("/c/en/bird") == "bird"
            assert ext._extract_concept("/c/en/bird/n") == "bird"
        finally:
            path.unlink()

    def test_extract_relation(self):
        path = _write_sample([_make_edge("IsA", "bird", "animal")])
        try:
            ext = ConceptNetExtractor(path)
            assert ext._extract_relation("/r/CapableOf") == "CapableOf"
            assert ext._extract_relation("/r/IsA") == "IsA"
            assert ext._extract_relation("/r/NotCapableOf") == "NotCapableOf"
            assert ext._extract_relation("/r/Causes") == "Causes"
            assert ext._extract_relation("/r/UsedFor") == "UsedFor"
        finally:
            path.unlink()

    def test_normalize(self):
        path = _write_sample([_make_edge("IsA", "bird", "animal")])
        try:
            ext = ConceptNetExtractor(path)
            assert ext._normalize("Bird Species") == "bird_species"
            assert ext._normalize("Can-Fly") == "can_fly"
        finally:
            path.unlink()


class TestBiologyExtraction:

    def test_biology_edges(self):
        lines = [
            _make_edge("CapableOf", "bird", "fly", 8.0),
            _make_edge("IsA", "penguin", "bird", 9.0),
            _make_edge("NotCapableOf", "penguin", "fly", 7.0),
            _make_edge("CapableOf", "rock", "fly", 0.5),  # low weight
            _make_edge("CapableOf", "car", "drive", 9.0),  # not bio
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path, weight_threshold=2.0)
            ext.extract_biology()
            assert len(ext.domain_edges) == 3
        finally:
            path.unlink()

    def test_to_theory_isa_facts(self):
        path = _write_sample([_make_edge("IsA", "sparrow", "bird", 9.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            theory = ext.to_theory()
            assert "isa(sparrow, bird)" in theory.facts
        finally:
            path.unlink()

    def test_to_theory_defeasible(self):
        path = _write_sample([_make_edge("CapableOf", "bird", "fly", 8.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            theory = ext.to_theory()
            d = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(d) > 0
            assert "fly" in d[0].head
        finally:
            path.unlink()

    def test_to_theory_defeater(self):
        path = _write_sample([_make_edge("NotCapableOf", "penguin", "fly", 7.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            theory = ext.to_theory()
            df = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(df) > 0
            assert "~" in df[0].head
        finally:
            path.unlink()

    def test_to_theory_hasproperty(self):
        path = _write_sample([_make_edge("HasProperty", "bird", "feathers", 6.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            theory = ext.to_theory()
            d = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert any("has_" in r.head for r in d)
        finally:
            path.unlink()


class TestNewRelationTypes:

    def test_causes_produces_defeasible_rule(self):
        path = _write_sample([_make_edge("Causes", "bird", "noise", 5.0)])
        try:
            ext = ConceptNetExtractor(path, profile=BIOLOGY)
            ext.extract()
            theory = ext.to_theory()
            d = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            causes = [r for r in d if "causes_" in r.head]
            assert len(causes) > 0
        finally:
            path.unlink()

    def test_usedfor_produces_defeasible_rule(self):
        path = _write_sample([_make_edge("UsedFor", "bird", "companionship", 5.0)])
        try:
            ext = ConceptNetExtractor(path, profile=BIOLOGY)
            ext.extract()
            theory = ext.to_theory()
            d = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            uses = [r for r in d if "used_for_" in r.head]
            assert len(uses) > 0
        finally:
            path.unlink()


class TestMultiDomainExtraction:

    def test_legal_profile_filters_legal_concepts(self):
        lines = [
            _make_edge("CapableOf", "contract", "bind", 8.0),
            _make_edge("CapableOf", "bird", "fly", 8.0),  # not legal
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path, profile=LEGAL)
            ext.extract()
            assert len(ext.domain_edges) == 1
            assert ext.domain_edges[0]["start"] == "contract"
        finally:
            path.unlink()

    def test_materials_profile_filters_materials_concepts(self):
        lines = [
            _make_edge("HasProperty", "metal", "conductive", 8.0),
            _make_edge("HasProperty", "bird", "feathers", 8.0),  # not materials
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path, profile=MATERIALS)
            ext.extract()
            assert len(ext.domain_edges) == 1
            assert ext.domain_edges[0]["start"] == "metal"
        finally:
            path.unlink()

    def test_domain_metadata_in_rules(self):
        path = _write_sample([_make_edge("CapableOf", "contract", "bind", 8.0)])
        try:
            ext = ConceptNetExtractor(path, profile=LEGAL)
            ext.extract()
            theory = ext.to_theory()
            for rule in theory.rules:
                if rule.metadata:
                    assert rule.metadata.get("domain") == "legal"
        finally:
            path.unlink()


class TestWeightFiltering:

    def test_below_threshold_filtered(self):
        lines = [
            _make_edge("CapableOf", "bird", "fly", 8.0),
            _make_edge("CapableOf", "bird", "teleport", 0.1),
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path, weight_threshold=2.0)
            ext.extract_biology()
            assert len(ext.domain_edges) == 1
            assert ext.domain_edges[0]["weight"] >= 2.0
        finally:
            path.unlink()


class TestMalformedData:

    def test_malformed_lines_skipped(self):
        lines = [
            _make_edge("IsA", "bird", "animal", 5.0),
            "malformed line without tabs",
            "/a/test\t/r/IsA\t/c/en/bird\t/c/en/animal\t{invalid json}",
            _make_edge("CapableOf", "bird", "fly", 3.0),
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path, weight_threshold=2.0)
            ext.extract_biology()
            assert len(ext.domain_edges) == 2
        finally:
            path.unlink()

    def test_non_english_filtered(self):
        meta = json.dumps({"weight": 5.0})
        line = f"/a/test\t/r/CapableOf\t/c/fr/oiseau\t/c/fr/voler\t{meta}"
        path = _write_sample([line, _make_edge("IsA", "bird", "animal", 5.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            assert len(ext.domain_edges) == 1
        finally:
            path.unlink()


class TestBackwardCompatibility:

    def test_biological_edges_alias(self):
        path = _write_sample([_make_edge("IsA", "bird", "animal", 5.0)])
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            assert ext.biological_edges is ext.domain_edges
        finally:
            path.unlink()

    def test_extract_biology_from_conceptnet_function(self):
        path = _write_sample([_make_edge("CapableOf", "bird", "fly", 8.0)])
        try:
            theory = extract_biology_from_conceptnet(
                path, weight_threshold=2.0, max_edges=10
            )
            assert len(theory.rules) > 0
        finally:
            path.unlink()

    def test_extract_from_conceptnet_function(self):
        path = _write_sample([_make_edge("CapableOf", "bird", "fly", 8.0)])
        try:
            theory = extract_from_conceptnet(
                path, weight_threshold=2.0, max_edges=10, profile=BIOLOGY
            )
            assert len(theory.rules) > 0
        finally:
            path.unlink()


class TestNoDuplicates:

    def test_duplicate_edges_produce_single_rule(self):
        lines = [
            _make_edge("CapableOf", "bird", "fly", 8.0),
            _make_edge("CapableOf", "bird", "fly", 7.0),
        ]
        path = _write_sample(lines)
        try:
            ext = ConceptNetExtractor(path)
            ext.extract_biology()
            theory = ext.to_theory()
            d = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            fly_rules = [r for r in d if "fly" in r.head]
            assert len(fly_rules) == 1
        finally:
            path.unlink()
