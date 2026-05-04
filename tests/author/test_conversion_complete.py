"""
Complete conversion tests to push coverage to 85%+.

Targets all remaining lines in author/conversion.py for full coverage.

Author: Anonymous Authors
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import convert_theory_to_defeasible, phi_kappa
from blanc.generation.partition import partition_rule, partition_leaf, partition_random, partition_depth, compute_dependency_depths


class TestConversionComplete:
    """Complete coverage of conversion functions."""
    
    def test_convert_all_modes(self):
        """Test convert_theory_to_defeasible with all modes."""
        theory = Theory()
        for i in range(5):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))
        
        # Rule mode
        c1 = convert_theory_to_defeasible(theory, mode='rule')
        assert c1 is not None
        
        # Leaf mode
        c2 = convert_theory_to_defeasible(theory, mode='leaf')
        assert c2 is not None
        
        # Depth mode with different k
        c3 = convert_theory_to_defeasible(theory, mode='depth', k=1)
        c4 = convert_theory_to_defeasible(theory, mode='depth', k=2)
        assert c3 is not None and c4 is not None
        
        # Random mode with different deltas
        c5 = convert_theory_to_defeasible(theory, mode='random', delta=0.1)
        c6 = convert_theory_to_defeasible(theory, mode='random', delta=0.5)
        c7 = convert_theory_to_defeasible(theory, mode='random', delta=0.9)
        assert c5 is not None and c6 is not None and c7 is not None
    
    def test_phi_kappa_with_all_partitions(self):
        """Test phi_kappa with all partition types."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("b(X)",), RuleType.STRICT, label="r2"))
        
        # Test all partition strategies
        depths = compute_dependency_depths(theory)
        
        conversions = [
            phi_kappa(theory, partition_rule),
            phi_kappa(theory, partition_leaf),
            phi_kappa(theory, partition_depth(1, depths)),
            phi_kappa(theory, partition_depth(2, depths)),
            phi_kappa(theory, partition_random(0.3, seed=42)),
            phi_kappa(theory, partition_random(0.7, seed=42)),
        ]
        
        # All should produce valid theories
        assert all(c is not None for c in conversions)
        assert all(len(c.rules) > 0 for c in conversions)
    
    def test_conversion_preserves_structure(self):
        """Test conversion preserves theory structure."""
        theory = Theory()
        theory.add_fact("fact1(a)")
        theory.add_fact("fact2(b)")
        theory.add_rule(Rule("h1(X)", ("fact1(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("h2(X)", ("fact2(X)",), RuleType.DEFEASIBLE, label="r2"))
        
        converted = phi_kappa(theory, partition_rule)
        
        # Should have same number of elements
        assert len(converted.facts) == len(theory.facts)
        assert len(converted.rules) == len(theory.rules)
    
    def test_conversion_rule_types(self):
        """Test conversion handles all rule types correctly."""
        theory = Theory()
        theory.add_rule(Rule("a(X)", ("b(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("d(X)",), RuleType.DEFEASIBLE, label="r2"))
        theory.add_rule(Rule("e(X)", ("f(X)",), RuleType.DEFEATER, label="r3"))
        
        converted = convert_theory_to_defeasible(theory, mode='rule')
        
        # Should handle all types
        assert len(converted.rules) == 3
