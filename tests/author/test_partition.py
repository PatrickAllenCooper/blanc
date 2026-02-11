"""
Tests for partition functions.

Tests Definition 10 (structured partition classes).
Author: Patrick Cooper
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    partition_depth,
    partition_random,
    defeasibility_ratio,
    compute_dependency_depths,
)
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
)


class TestPartitionLeaf:
    """Test κ_leaf partition function."""
    
    def test_facts_defeasible(self):
        """Facts should be classified as defeasible."""
        fact_rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.FACT)
        assert partition_leaf(fact_rule) == 'd'
    
    def test_rules_strict(self):
        """Rules should be classified as strict."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE
        )
        assert partition_leaf(rule) == 's'


class TestPartitionRule:
    """Test κ_rule partition function."""
    
    def test_facts_strict(self):
        """Facts should be classified as strict."""
        fact_rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.FACT)
        assert partition_rule(fact_rule) == 's'
    
    def test_rules_defeasible(self):
        """Rules should be classified as defeasible."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT
        )
        assert partition_rule(rule) == 'd'


class TestPartitionDepth:
    """Test κ_depth(k) partition function."""
    
    def test_shallow_predicates_strict(self):
        """Predicates at depth ≤ k should be strict."""
        depths = {"bird": 0, "flies": 2}
        partition_fn = partition_depth(k=1, dependency_depths=depths)
        
        rule = Rule(head="bird(tweety)", body=(), rule_type=RuleType.FACT)
        assert partition_fn(rule) == 's'  # depth 0 ≤ 1
    
    def test_deep_predicates_defeasible(self):
        """Predicates at depth > k should be defeasible."""
        depths = {"bird": 0, "flies": 2}
        partition_fn = partition_depth(k=1, dependency_depths=depths)
        
        rule = Rule(head="flies(X)", body=("bird(X)",))
        assert partition_fn(rule) == 'd'  # depth 2 > 1
    
    def test_compute_dependency_depths_avian(self):
        """Test dependency depth computation on Avian Biology."""
        theory = create_avian_biology_base()
        depths = compute_dependency_depths(theory)
        
        # Source predicates (only facts, no rules deriving them) should be depth 0
        assert depths.get("sparrow", -1) == 0
        assert depths.get("penguin", -1) == 0
        assert depths.get("wing_injury", -1) == 0
        
        # bird can be derived from sparrow, so depth >= 1
        assert depths.get("bird", -1) >= 1
        
        # Behavioral predicates derived from bird should be deeper
        assert depths.get("flies", -1) >= 2
        assert depths.get("migrates", -1) >= 2


class TestPartitionRandom:
    """Test κ_rand(δ) partition function."""
    
    def test_deterministic_with_seed(self):
        """Same seed should give same classifications."""
        rule = Rule(head="flies(X)", body=("bird(X)",))
        
        partition1 = partition_random(delta=0.5, seed=42)
        partition2 = partition_random(delta=0.5, seed=42)
        
        assert partition1(rule) == partition2(rule)
    
    def test_different_seeds_differ(self):
        """Different seeds may give different classifications."""
        rule = Rule(head="flies(X)", body=("bird(X)",))
        
        partition1 = partition_random(delta=0.5, seed=42)
        partition2 = partition_random(delta=0.5, seed=43)
        
        # Might be different (not guaranteed, but likely with 0.5 probability)
        # Just verify it doesn't crash
        result1 = partition1(rule)
        result2 = partition2(rule)
        assert result1 in ['s', 'd']
        assert result2 in ['s', 'd']
    
    def test_delta_zero_all_strict(self):
        """δ=0 should classify all as strict."""
        partition_fn = partition_random(delta=0.0, seed=42)
        
        for i in range(10):
            rule = Rule(head=f"p{i}", body=())
            assert partition_fn(rule) == 's'
    
    def test_delta_one_all_defeasible(self):
        """δ=1 should classify all as defeasible."""
        partition_fn = partition_random(delta=1.0, seed=42)
        
        for i in range(10):
            rule = Rule(head=f"p{i}", body=())
            assert partition_fn(rule) == 'd'
    
    def test_delta_half_approximately_balanced(self):
        """δ=0.5 should give roughly 50/50 split."""
        partition_fn = partition_random(delta=0.5, seed=42)
        
        rules = [Rule(head=f"p{i}", body=()) for i in range(100)]
        defeasible_count = sum(1 for r in rules if partition_fn(r) == 'd')
        
        # Should be roughly 50% (allow 30-70% range for randomness)
        assert 30 <= defeasible_count <= 70


class TestDefeasibilityRatio:
    """Test defeasibility ratio computation."""
    
    def test_all_strict(self):
        """All strict should give δ=0."""
        rules = [
            Rule(head="p1", body=()),
            Rule(head="p2", body=()),
        ]
        partition_fn = partition_random(delta=0.0, seed=42)
        
        ratio = defeasibility_ratio(partition_fn, rules)
        assert ratio == 0.0
    
    def test_all_defeasible(self):
        """All defeasible should give δ=1."""
        rules = [
            Rule(head="p1", body=()),
            Rule(head="p2", body=()),
        ]
        partition_fn = partition_random(delta=1.0, seed=42)
        
        ratio = defeasibility_ratio(partition_fn, rules)
        assert ratio == 1.0
    
    def test_mixed(self):
        """Mixed should give intermediate ratio."""
        fact = Rule(head="p1", body=(), rule_type=RuleType.FACT)
        rule = Rule(head="p2", body=("p1",), rule_type=RuleType.STRICT)
        
        rules = [fact, rule]
        partition_fn = partition_leaf  # Facts defeasible, rules strict
        
        # fact.is_fact = True → 'd'
        # rule.is_fact = False → 's'
        ratio = defeasibility_ratio(partition_fn, rules)
        assert ratio == 0.5  # 1/2 defeasible


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
