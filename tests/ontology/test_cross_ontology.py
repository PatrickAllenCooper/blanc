"""
Tests for cross-ontology combiner module.

Author: Patrick Cooper
"""

import json
import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import RuleType
from blanc.ontology.cross_ontology import (
    CombinationStats,
    combine_taxonomy_properties,
    build_cross_ontology_theory,
)
from blanc.ontology.domain_profiles import BIOLOGY


class TestCombineTaxonomyProperties:

    def _simple_taxonomy(self):
        return {
            "penguin": {"bird"},
            "sparrow": {"bird"},
            "bird": {"animal"},
            "animal": set(),
        }

    def _simple_properties(self):
        return {
            "bird": [("CapableOf", "fly"), ("HasProperty", "feathers")],
            "penguin": [("NotCapableOf", "fly"), ("CapableOf", "swim")],
            "sparrow": [("CapableOf", "sing")],
            "animal": [("CapableOf", "move")],
        }

    def test_produces_theory_and_stats(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        assert len(theory.rules) > 0
        assert isinstance(stats, CombinationStats)

    def test_strict_taxonomic_rules(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert stats.strict_rules == len(strict)
        assert stats.strict_rules > 0
        heads = {r.head for r in strict}
        assert "bird(X)" in heads
        assert "animal(X)" in heads

    def test_defeasible_inherited_rules(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) > 0
        inherited_labels = [
            r.label for r in defeasible
            if r.label and "inh" in r.label
        ]
        assert len(inherited_labels) > 0

    def test_defeasible_specific_rules(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        specific_labels = [
            r.label for r in defeasible
            if r.label and "spec" in r.label
        ]
        assert len(specific_labels) > 0

    def test_defeaters_from_notcapableof(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert stats.defeaters > 0
        assert len(defeaters) == stats.defeaters
        heads = {r.head for r in defeaters}
        assert "~fly(X)" in heads

    def test_stats_total(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        assert stats.total_rules == len(theory.rules)

    def test_facts_for_concepts(self):
        theory, _ = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        assert "concept(penguin)" in theory.facts
        assert "concept(bird)" in theory.facts

    def test_property_rules_from_hasproperty(self):
        theory, stats = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        assert stats.property_rules > 0

    def test_no_duplicates(self):
        theory, _ = combine_taxonomy_properties(
            self._simple_taxonomy(), self._simple_properties()
        )
        sigs = set()
        for rule in theory.rules:
            sig = (rule.head, rule.body, rule.rule_type)
            assert sig not in sigs, f"Duplicate rule: {rule}"
            sigs.add(sig)

    def test_causes_relation(self):
        props = {"bird": [("Causes", "noise")]}
        taxonomy = {"sparrow": {"bird"}}
        theory, stats = combine_taxonomy_properties(taxonomy, props)
        assert stats.causal_rules > 0

    def test_usedfor_relation(self):
        props = {"bird": [("UsedFor", "companionship")]}
        taxonomy = {"sparrow": {"bird"}}
        theory, stats = combine_taxonomy_properties(taxonomy, props)
        assert stats.functional_rules > 0

    def test_empty_inputs(self):
        theory, stats = combine_taxonomy_properties({}, {})
        assert stats.total_rules == 0
        assert len(theory.rules) == 0

    def test_profile_metadata(self):
        theory, _ = combine_taxonomy_properties(
            self._simple_taxonomy(),
            self._simple_properties(),
            profile=BIOLOGY,
        )
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata.get("domain") == "biology"


class TestBuildCrossOntologyTheory:

    def test_saves_stats_json(self):
        taxonomy = {"penguin": {"bird"}, "bird": set()}
        props = {"bird": [("CapableOf", "fly")]}

        with tempfile.TemporaryDirectory() as tmpdir:
            out = Path(tmpdir) / "stats.json"
            theory, stats = build_cross_ontology_theory(
                taxonomy, props, output_path=out
            )
            assert out.exists()
            with open(out) as f:
                data = json.load(f)
            assert data["total_rules"] == stats.total_rules


class TestCombinationStats:

    def test_to_dict(self):
        stats = CombinationStats(strict_rules=5, defeaters=3)
        d = stats.to_dict()
        assert d["strict_rules"] == 5
        assert d["defeaters"] == 3
        assert d["total_rules"] == 8

    def test_total_rules_sum(self):
        stats = CombinationStats(
            strict_rules=10,
            defeasible_inherited=20,
            defeasible_specific=5,
            property_rules=3,
            causal_rules=2,
            functional_rules=1,
            defeaters=4,
        )
        assert stats.total_rules == 45
