"""
Tests for NELL extractor.

Uses tempfile CSV files to avoid any network downloads.  Covers
confidence filtering, generalization rules (strict), other relation
rules (defeasible), conflict detection (defeaters with superiority),
taxonomy, and property accessors.

Author: Patrick Cooper
"""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import RuleType
from blanc.ontology.nell_extractor import NellExtractor, _normalize


def _write_csv(rows, header=("entity", "relation", "value", "score")):
    """Write a tab-delimited CSV file and return the path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
    )
    writer = csv.writer(f, delimiter="\t")
    writer.writerow(header)
    for row in rows:
        writer.writerow(row)
    f.close()
    return Path(f.name)


SAMPLE_ROWS = [
    ("bird", "generalizations", "animal", "0.99"),
    ("penguin", "generalizations", "bird", "0.98"),
    ("bird", "can_fly", "true", "0.97"),
    ("penguin", "can_fly", "false", "0.96"),
    ("cat", "has_fur", "true", "0.50"),
    ("dog", "has_fur", "true", "0.99"),
]


class TestNormalize:

    def test_lowercase_and_underscore(self):
        assert _normalize("Bird Species") == "bird_species"
        assert _normalize("Can-Fly") == "can_fly"

    def test_strips_special_chars(self):
        assert _normalize("hello!world") == "helloworld"


class TestNellExtractorInit:

    def test_default_confidence_threshold(self):
        ext = NellExtractor()
        assert ext.confidence_threshold == 0.95

    def test_custom_threshold(self):
        ext = NellExtractor(confidence_threshold=0.5)
        assert ext.confidence_threshold == 0.5

    def test_custom_max_beliefs(self):
        ext = NellExtractor(max_beliefs=10)
        assert ext.max_beliefs == 10


class TestConfidenceFiltering:

    def test_high_threshold_filters_low_confidence(self):
        path = _write_csv(SAMPLE_ROWS)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            scores = [b["score"] for b in ext.beliefs]
            assert all(s >= 0.95 for s in scores)
            entities = {b["entity"] for b in ext.beliefs}
            assert "cat" not in entities
        finally:
            path.unlink()

    def test_low_threshold_includes_more(self):
        path = _write_csv(SAMPLE_ROWS)
        try:
            ext = NellExtractor(confidence_threshold=0.50)
            ext.extract(csv_path=str(path))
            assert len(ext.beliefs) == 6
        finally:
            path.unlink()

    def test_max_beliefs_caps_extraction(self):
        path = _write_csv(SAMPLE_ROWS)
        try:
            ext = NellExtractor(confidence_threshold=0.0, max_beliefs=3)
            ext.extract(csv_path=str(path))
            assert len(ext.beliefs) == 3
        finally:
            path.unlink()

    def test_invalid_score_skipped(self):
        rows = [
            ("bird", "generalizations", "animal", "not_a_number"),
            ("dog", "has_fur", "true", "0.99"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.0)
            ext.extract(csv_path=str(path))
            assert len(ext.beliefs) == 1
            assert ext.beliefs[0]["entity"] == "dog"
        finally:
            path.unlink()

    def test_short_rows_skipped(self):
        rows = [
            ("bird", "generalizations"),
            ("dog", "has_fur", "true", "0.99"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.0)
            ext.extract(csv_path=str(path))
            assert len(ext.beliefs) == 1
        finally:
            path.unlink()

    def test_comment_rows_skipped(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(("entity", "relation", "value", "score"))
        writer.writerow(("# this is a comment",))
        writer.writerow(("dog", "has_fur", "true", "0.99"))
        f.close()
        path = Path(f.name)
        try:
            ext = NellExtractor(confidence_threshold=0.0)
            ext.extract(csv_path=str(path))
            assert len(ext.beliefs) == 1
        finally:
            path.unlink()


class TestGeneralizationRules:

    def test_generalizations_produce_strict_rules(self):
        rows = [
            ("bird", "generalizations", "animal", "0.99"),
            ("penguin", "generalizations", "bird", "0.98"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert len(strict) == 2
            for r in strict:
                assert r.rule_type == RuleType.STRICT
                assert len(r.body) == 1
        finally:
            path.unlink()

    def test_strict_rule_head_is_parent(self):
        rows = [("bird", "generalizations", "animal", "0.99")]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert strict[0].head == "animal(X)"
            assert strict[0].body == ("bird(X)",)
        finally:
            path.unlink()

    def test_strict_rule_label_and_metadata(self):
        rows = [("bird", "generalizations", "animal", "0.99")]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            strict = theory.get_rules_by_type(RuleType.STRICT)
            assert strict[0].label == "nell_isa_bird_animal"
            assert strict[0].metadata["source"] == "NELL"
            assert strict[0].metadata["score"] == 0.99
        finally:
            path.unlink()


class TestDefeasibleRules:

    def test_other_relations_produce_defeasible_rules(self):
        rows = [
            ("bird", "can_fly", "true", "0.97"),
            ("dog", "has_fur", "true", "0.99"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(defeasible) == 2
            for r in defeasible:
                assert r.rule_type == RuleType.DEFEASIBLE
                assert r.body == ()
        finally:
            path.unlink()

    def test_defeasible_rule_format(self):
        rows = [("bird", "can_fly", "true", "0.97")]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert defeasible[0].head == "can_fly(bird, true)"
            assert defeasible[0].label == "nell_can_fly_bird_true"
        finally:
            path.unlink()


class TestConflictDetection:

    def test_conflicting_beliefs_produce_defeaters(self):
        rows = [
            ("bird", "color", "brown", "0.99"),
            ("bird", "color", "black", "0.96"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) == 1
            assert defeaters[0].head.startswith("~")
            assert "black" in defeaters[0].head
        finally:
            path.unlink()

    def test_superiority_favors_higher_confidence(self):
        rows = [
            ("bird", "color", "brown", "0.99"),
            ("bird", "color", "black", "0.96"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            assert len(theory.superiority) > 0
            winner_label = "nell_color_bird_brown"
            assert winner_label in theory.superiority
            defeated = theory.superiority[winner_label]
            assert any("black" in d for d in defeated)
        finally:
            path.unlink()

    def test_no_defeater_for_single_value(self):
        rows = [("bird", "color", "brown", "0.99")]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) == 0
        finally:
            path.unlink()

    def test_no_defeater_for_generalizations(self):
        rows = [
            ("bird", "generalizations", "animal", "0.99"),
            ("bird", "generalizations", "creature", "0.97"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) == 0
        finally:
            path.unlink()

    def test_three_way_conflict_produces_two_defeaters(self):
        rows = [
            ("bird", "color", "brown", "0.99"),
            ("bird", "color", "black", "0.97"),
            ("bird", "color", "white", "0.96"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) == 2
            defeated_values = {d.head for d in defeaters}
            assert "~color(bird, black)" in defeated_values
            assert "~color(bird, white)" in defeated_values
        finally:
            path.unlink()


class TestTaxonomy:

    def test_get_taxonomy_returns_generalization_mapping(self):
        rows = [
            ("bird", "generalizations", "animal", "0.99"),
            ("penguin", "generalizations", "bird", "0.98"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            taxonomy = ext.get_taxonomy()
            assert "bird" in taxonomy
            assert "animal" in taxonomy["bird"]
            assert "penguin" in taxonomy
            assert "bird" in taxonomy["penguin"]
        finally:
            path.unlink()

    def test_taxonomy_excludes_non_generalizations(self):
        rows = [
            ("bird", "generalizations", "animal", "0.99"),
            ("bird", "can_fly", "true", "0.97"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            taxonomy = ext.get_taxonomy()
            assert "bird" in taxonomy
            assert len(taxonomy) == 1
        finally:
            path.unlink()


class TestProperties:

    def test_get_properties_excludes_generalizations(self):
        rows = [
            ("bird", "generalizations", "animal", "0.99"),
            ("bird", "can_fly", "true", "0.97"),
            ("dog", "has_fur", "true", "0.99"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            props = ext.get_properties()
            assert "bird" in props
            bird_rels = {r for r, _ in props["bird"]}
            assert "can_fly" in bird_rels
            assert "generalizations" not in bird_rels
        finally:
            path.unlink()

    def test_get_properties_values(self):
        rows = [("bird", "can_fly", "true", "0.97")]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            props = ext.get_properties()
            bird_vals = dict(props.get("bird", []))
            assert bird_vals.get("can_fly") == "true"
        finally:
            path.unlink()


class TestDeduplication:

    def test_duplicate_beliefs_produce_single_rule(self):
        rows = [
            ("bird", "can_fly", "true", "0.99"),
            ("bird", "can_fly", "true", "0.98"),
        ]
        path = _write_csv(rows)
        try:
            ext = NellExtractor(confidence_threshold=0.95)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            fly_rules = [r for r in defeasible if "can_fly" in r.head]
            assert len(fly_rules) == 1
        finally:
            path.unlink()


class TestEmptyInput:

    def test_empty_csv_produces_empty_theory(self):
        path = _write_csv([])
        try:
            ext = NellExtractor(confidence_threshold=0.0)
            ext.extract(csv_path=str(path))
            theory = ext.to_theory()
            assert len(theory.rules) == 0
            assert len(theory.facts) == 0
        finally:
            path.unlink()
