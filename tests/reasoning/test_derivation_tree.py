"""
Tests for derivation tree construction.

Tests Definition 13 (AND-OR derivation trees).
Author: Patrick Cooper
"""

import pytest

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import DefeasibleEngine
from blanc.reasoning.derivation_tree import (
    build_derivation_tree,
    DerivationNode,
    NodeType,
)
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
    create_avian_biology_full,
)


class TestDerivationTreeBasic:
    """Test basic derivation tree construction."""
    
    def test_fact_derivation(self):
        """Derivation of a fact should be single node."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "bird(tweety)")
        
        assert tree is not None
        assert tree.root.literal == "bird(tweety)"
        assert tree.root.node_type == NodeType.FACT
        assert tree.depth() == 0
        assert tree.size() == 1
    
    def test_simple_rule_derivation(self):
        """Derivation via one rule."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "flies(tweety)")
        
        assert tree is not None
        assert tree.root.literal == "flies(tweety)"
        assert tree.root.rule.label == "r1"
        assert len(tree.root.children) == 1
        assert tree.root.children[0].literal == "bird(tweety)"
        assert tree.depth() == 1
        assert tree.size() == 2
    
    def test_chain_derivation(self):
        """Derivation via rule chain."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        theory.add_rule(Rule(
            head="migrates(X)",
            body=("bird(X)", "flies(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r2"
        ))
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "migrates(tweety)")
        
        assert tree is not None
        assert tree.root.literal == "migrates(tweety)"
        assert tree.root.rule.label == "r2"
        assert len(tree.root.children) == 2  # bird(tweety) and flies(tweety)
        assert tree.depth() == 2
        assert tree.size() >= 3
    
    def test_unprovable_returns_none(self):
        """Derivation tree for unprovable literal should be None."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "flies(tweety)")  # No rule!
        
        assert tree is None


class TestDerivationTreeRules:
    """Test rule extraction from derivation trees."""
    
    def test_get_rules_used(self):
        """Test getting all rules used in derivation."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        theory.add_rule(Rule(
            head="migrates(X)",
            body=("bird(X)", "flies(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r2"
        ))
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "migrates(tweety)")
        
        rules_used = tree.get_rules_used()
        labels = {r.label for r in rules_used}
        
        assert "r1" in labels
        assert "r2" in labels
    
    def test_get_defeasible_rules_used(self):
        """Test getting only defeasible rules (for anomaly support)."""
        theory = Theory()
        theory.add_fact("sparrow(tweety)")
        
        # Strict rule
        theory.add_rule(Rule(
            head="bird(X)",
            body=("sparrow(X)",),
            rule_type=RuleType.STRICT,
            label="s1"
        ))
        
        # Defeasible rule
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "flies(tweety)")
        
        defeasible_rules = tree.get_defeasible_rules_used()
        labels = {r.label for r in defeasible_rules}
        
        assert "r1" in labels
        assert "s1" not in labels  # Strict rule excluded


class TestDerivationTreeAvianBiology:
    """Test derivation trees on Avian Biology KB."""
    
    def test_avian_flight_derivation(self):
        """Test flight derivation tree."""
        theory = create_avian_biology_base()
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "flies(tweety)")
        
        assert tree is not None
        assert tree.root.literal == "flies(tweety)"
        
        # Should use r1: flies(X) :- bird(X)
        rules_used = tree.get_rules_used()
        assert any(r.label == "r1" for r in rules_used)
    
    def test_avian_migration_derivation(self):
        """Test migration derivation tree (2-step)."""
        theory = create_avian_biology_base()
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "migrates(tweety)")
        
        assert tree is not None
        assert tree.root.literal == "migrates(tweety)"
        
        # Should use both r1 and r2
        rules_used = tree.get_rules_used()
        labels = {r.label for r in rules_used}
        assert "r1" in labels  # flies(X) :- bird(X)
        assert "r2" in labels  # migrates(X) :- bird(X), flies(X)


class TestSerialization:
    """Test serialization of derivation trees."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        
        engine = DefeasibleEngine(theory)
        tree = build_derivation_tree(engine, "flies(tweety)")
        
        tree_dict = tree.to_dict()
        
        assert "root" in tree_dict
        assert "depth" in tree_dict
        assert "size" in tree_dict
        assert "rules_used" in tree_dict
        assert tree_dict["depth"] == 1
        assert tree_dict["size"] == 2
        assert "r1" in tree_dict["rules_used"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
