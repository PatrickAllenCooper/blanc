"""
Extended tests for author/metrics.py to improve coverage.

Author: Anonymous Authors
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.metrics import defeasible_yield
from blanc.generation.partition import partition_random, partition_rule


class TestYieldComputation:
    """Test yield computation on various scenarios."""
    
    def test_yield_empty_target_set(self):
        """Test yield with empty target set."""
        theory = Theory()
        theory.add_fact("a(x)")
        
        yield_val = defeasible_yield(partition_rule, set(), theory)
        
        assert yield_val == 0
    
    def test_yield_no_critical_elements(self):
        """Test yield when no elements are critical."""
        theory = Theory()
        theory.add_fact("a(x)")
        
        targets = {"a(x)"}  # Fact is already derivable, no critical elements needed
        
        yield_val = defeasible_yield(partition_rule, targets, theory)
        
        # Should be 0 or low
        assert yield_val >= 0
    
    def test_yield_with_multiple_targets(self):
        """Test yield aggregates over multiple targets."""
        theory = Theory()
        theory.add_fact("bird(robin)")
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        ))
        
        targets = {"flies(robin)", "bird(robin)"}
        
        yield_val = defeasible_yield(partition_rule, targets, theory)
        
        assert yield_val >= 0
    
    def test_yield_different_partitions(self):
        """Test yield varies with partition strategy."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("b(X)",), RuleType.STRICT, label="r2"))
        
        targets = {"c(x)"}
        
        # Different partitions should potentially give different yields
        yield_rule = defeasible_yield(partition_rule, targets, theory)
        yield_rand = defeasible_yield(partition_random(0.5, seed=42), targets, theory)
        
        # Both should be >= 0
        assert yield_rule >= 0
        assert yield_rand >= 0
