"""
Tests covering remaining gaps in src/blanc/generation/distractor.py.

Missing lines: 58 (unknown fact strategy), 106 (unknown rule strategy),
177 (no available facts), 274/280/283 (adversarial rule edge cases).
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.generation.distractor import sample_fact_distractors, sample_rule_distractors


def _make_theory_with_facts(*facts: str) -> Theory:
    t = Theory()
    for f in facts:
        t.add_fact(f)
    return t


def _make_theory_with_rules(*rules) -> Theory:
    t = Theory()
    for r in rules:
        t.rules.append(r)
    return t


def _make_rule(head: str, body: tuple, label: str = None) -> Rule:
    return Rule(head=head, body=body, rule_type=RuleType.DEFEASIBLE, label=label)


class TestUnknownStrategy:
    def test_unknown_fact_strategy_raises(self):
        t = _make_theory_with_facts("bird(tweety)")
        with pytest.raises(ValueError, match="Unknown distractor strategy"):
            sample_fact_distractors("bird(tweety)", t, k=1, strategy="bogus")

    def test_unknown_rule_strategy_raises(self):
        rule = _make_rule("flies(X)", ("bird(X)",))
        t = _make_theory_with_rules(rule)
        with pytest.raises(ValueError, match="Unknown distractor strategy"):
            sample_rule_distractors(rule, t, k=1, strategy="bogus")


class TestEmptyTheoryEdgeCases:
    def test_no_available_facts_returns_empty(self):
        # Theory has only the target fact — no other facts to sample
        t = _make_theory_with_facts("bird(tweety)")
        result = sample_fact_distractors("bird(tweety)", t, k=5, strategy="random")
        assert result == []

    def test_no_rules_returns_empty(self):
        t = Theory()
        rule = _make_rule("flies(X)", ("bird(X)",))
        result = sample_rule_distractors(rule, t, k=5, strategy="random")
        assert result == []

    def test_adversarial_rule_single_body_atom(self):
        """Adversarial strategy with a rule that has only one body atom."""
        t = Theory()
        rule  = _make_rule("flies(X)", ("bird(X)",))
        other = _make_rule("swims(X)", ("duck(X)",))
        t.rules.extend([rule, other])
        # Should not raise; may return empty list
        result = sample_rule_distractors(rule, t, k=3, strategy="adversarial")
        assert isinstance(result, list)
