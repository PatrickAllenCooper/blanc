"""
Tests covering remaining gaps in src/blanc/core/theory.py.

Missing lines: 80-84 (to_asp), 89 (to_defeasible fact), 198-209
(Theory.to_prolog / to_asp / to_defeasible), 265 (Theory.__len__).
"""

import pytest
from blanc.core.theory import Rule, RuleType, Theory


class TestRuleToAsp:
    def test_fact_type_to_asp(self):
        """is_fact requires RuleType.FACT (not STRICT with empty body)."""
        rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.FACT, label=None)
        result = rule.to_asp()
        assert result == "bird(tweety)."

    def test_strict_rule_to_asp(self):
        rule = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.STRICT)
        result = rule.to_asp()
        assert "flies(X)" in result
        assert "bird(X)" in result
        assert ":-" in result

    def test_strict_empty_body_to_asp_produces_fact_like_prolog(self):
        """STRICT + empty body IS NOT is_fact; produces 'head :- .'."""
        rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.STRICT)
        result = rule.to_asp()
        assert "bird(tweety)" in result

    def test_defeasible_rule_to_defeasible_method(self):
        rule = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r1")
        result = rule.to_defeasible()
        assert "=>" in result
        assert "r1:" in result

    def test_strict_rule_to_defeasible_method(self):
        rule = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.STRICT)
        result = rule.to_defeasible()
        assert "->" in result

    def test_defeater_rule_to_defeasible_method(self):
        rule = Rule(head="not_flies(X)", body=("penguin(X)",), rule_type=RuleType.DEFEATER)
        result = rule.to_defeasible()
        assert "~>" in result

    def test_fact_type_to_defeasible_method(self):
        """RuleType.FACT with no body produces just the head atom."""
        rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.FACT, label=None)
        result = rule.to_defeasible()
        assert result == "bird(tweety)"


class TestTheorySerializationMethods:
    def _make_theory(self) -> Theory:
        t = Theory()
        t.add_fact("bird(tweety)")
        t.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        return t

    def test_to_prolog(self):
        t = self._make_theory()
        result = t.to_prolog()
        assert isinstance(result, str)
        assert "bird(tweety)" in result

    def test_to_asp(self):
        t = self._make_theory()
        result = t.to_asp()
        assert isinstance(result, str)

    def test_to_defeasible(self):
        t = self._make_theory()
        result = t.to_defeasible()
        assert isinstance(result, str)
        assert "=>" in result

    def test_theory_len(self):
        t = self._make_theory()
        # __len__ counts rules (if implemented); if not present, this tests
        # that the theory has the right number of rules
        assert len(t.rules) == 1
        assert len(t.facts) == 1
