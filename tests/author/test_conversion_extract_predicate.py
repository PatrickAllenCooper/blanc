"""
Tests for conversion.py _extract_predicate helper (lines 171-177)
and the continue-path for fact rules in phi_kappa (line 80).

Author: Anonymous Authors
Date: 2026-02-18
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import phi_kappa, _extract_predicate
from blanc.generation.partition import partition_rule, partition_leaf


class TestExtractPredicate:
    def test_simple_atom(self):
        assert _extract_predicate("bird(tweety)") == "bird"

    def test_negated_atom(self):
        assert _extract_predicate("~flies(X)") == "flies"

    def test_no_parens(self):
        assert _extract_predicate("bird") == "bird"

    def test_negated_no_parens(self):
        assert _extract_predicate("~bird") == "bird"

    def test_complex_args(self):
        assert _extract_predicate("parent(tom, jerry)") == "parent"


class TestPhiKappaFactRuleContinue:
    """
    Tests that phi_kappa correctly skips Rule objects with empty body
    (is_fact=True) that are also represented in theory.facts, so they
    are not double-counted (the continue at line 80).
    """

    def test_fact_rules_not_double_added(self):
        """Facts explicitly added to both theory.facts and as Rule objects
        should not be duplicated in the converted theory."""
        t = Theory()
        t.add_fact("bird(tweety)")
        # Also add as a FACT-type rule (simulates the is_fact=True path)
        t.add_rule(Rule("bird(tweety)", (), RuleType.FACT, label="f1"))

        converted = phi_kappa(t, partition_rule)

        # Should only have one representation of bird(tweety), not two
        bird_facts = [f for f in converted.facts if f == "bird(tweety)"]
        bird_rules = [
            r for r in converted.rules if r.head == "bird(tweety)" and not r.body
        ]
        total_bird_representations = len(bird_facts) + len(bird_rules)
        assert total_bird_representations == 1

    def test_phi_kappa_with_mixed_theory(self):
        """Theory with facts, strict rules, and a FACT-type rule converts cleanly."""
        t = Theory()
        t.add_fact("animal(rex)")
        t.add_rule(Rule("mammal(X)", ("animal(X)",), RuleType.STRICT, label="r1"))
        t.add_rule(Rule("animal(rex)", (), RuleType.FACT, label="f_rex"))

        converted = phi_kappa(t, partition_rule)

        # animal(rex) should appear exactly once
        assert "animal(rex)" in converted.facts
        animal_rules = [r for r in converted.rules if r.head == "animal(rex)"]
        assert len(animal_rules) == 0  # Not duplicated as defeasible rule
