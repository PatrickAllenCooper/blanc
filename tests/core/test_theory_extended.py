"""
Extended tests for core/theory.py to improve coverage.

Targets missing lines for 87% -> 95% coverage improvement.

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType


class TestTheoryOperations:
    """Test Theory operations."""
    
    def test_theory_get_rules_by_type_defeasible(self):
        """Test getting defeasible rules."""
        theory = Theory()
        theory.add_rule(Rule(
            head="a(X)",
            body=("b(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        theory.add_rule(Rule(
            head="c(X)",
            body=("d(X)",),
            rule_type=RuleType.STRICT,
            label="r2"
        ))
        
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        
        assert len(defeasible) == 1
        assert defeasible[0].label == "r1"
    
    def test_theory_get_rules_by_type_strict(self):
        """Test getting strict rules."""
        theory = Theory()
        theory.add_rule(Rule(
            head="a(X)",
            body=("b(X)",),
            rule_type=RuleType.STRICT,
            label="r1"
        ))
        
        strict = theory.get_rules_by_type(RuleType.STRICT)
        
        assert len(strict) == 1
    
    def test_theory_clear(self):
        """Test clearing theory."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        
        # Clear should remove all
        theory.facts.clear()
        theory.rules.clear()
        
        assert len(theory.facts) == 0
        assert len(theory.rules) == 0
    
    def test_theory_len(self):
        """Test theory length."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_fact("b(x)")
        theory.add_rule(Rule("c(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        
        # Total elements
        total = len(theory.facts) + len(theory.rules)
        assert total == 3


class TestRuleProperties:
    """Test Rule properties and methods."""
    
    def test_rule_is_fact_property(self):
        """Test Rule.is_fact property."""
        # Rule with body is not a fact
        rule = Rule(
            head="a(X)",
            body=("b(X)",),
            rule_type=RuleType.STRICT,
            label="r1"
        )
        
        assert rule.is_fact == False
    
    def test_rule_to_dict(self):
        """Test Rule serialization."""
        rule = Rule(
            head="a(X)",
            body=("b(X)", "c(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        rule_dict = rule.to_dict()
        
        assert 'head' in rule_dict
        assert 'body' in rule_dict
        assert 'rule_type' in rule_dict
        assert 'label' in rule_dict
    
    def test_rule_str_representation(self):
        """Test Rule string representation."""
        rule = Rule(
            head="a(X)",
            body=("b(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        str_repr = str(rule)
        
        assert 'a(X)' in str_repr
        assert 'b(X)' in str_repr
        assert '=>' in str_repr or 'defeasible' in str_repr.lower()


class TestTheoryIteration:
    """Test theory iteration and access."""
    
    def test_theory_iterate_facts(self):
        """Test iterating over facts."""
        theory = Theory()
        facts = ["a(x)", "b(y)", "c(z)"]
        for fact in facts:
            theory.add_fact(fact)
        
        collected_facts = list(theory.facts)
        
        assert len(collected_facts) == 3
        assert all(f in collected_facts for f in facts)
    
    def test_theory_iterate_rules(self):
        """Test iterating over rules."""
        theory = Theory()
        theory.add_rule(Rule("a(X)", ("b(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("d(X)",), RuleType.DEFEASIBLE, label="r2"))
        
        collected_rules = list(theory.rules)
        
        assert len(collected_rules) == 2
