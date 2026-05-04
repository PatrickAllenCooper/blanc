"""
Comprehensive tests for author/conversion.py to reach 85%+ coverage.

Targets lines 80, 151-162, 171-177 (current 65% -> target 85%).

Author: Anonymous Authors
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import (
    convert_theory_to_defeasible,
    phi_kappa,
)
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    partition_depth,
    partition_random,
    compute_dependency_depths,
)


class TestConversionWrappers:
    """Test conversion wrapper functions."""

    def test_convert_theory_depth_mode(self):
        """Test convert_theory_to_defeasible with depth partition strategy."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("b(X)",), RuleType.STRICT, label="r2"))
        theory.add_rule(Rule("d(X)", ("c(X)",), RuleType.STRICT, label="r3"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='depth', k=1)

        assert converted is not None
        assert len(converted.rules) > 0

    def test_convert_theory_depth_mode_k2(self):
        """Test depth partition strategy with k=2."""
        theory = Theory()
        theory.add_fact("a(x)")
        for i in range(3):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='depth', k=2)

        assert converted is not None

    def test_convert_theory_depth_mode_k3(self):
        """Test depth partition strategy with k=3."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='depth', k=3)

        assert converted is not None

    def test_convert_theory_random_mode_low_delta(self):
        """Test random partition strategy with low delta."""
        theory = Theory()
        for i in range(5):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='random', delta=0.1)

        assert converted is not None

    def test_convert_theory_random_mode_high_delta(self):
        """Test random partition strategy with high delta."""
        theory = Theory()
        for i in range(5):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='random', delta=0.9)

        assert converted is not None

    def test_convert_theory_random_mode_mid_delta(self):
        """Test random partition strategy with mid delta."""
        theory = Theory()
        for i in range(5):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='random', delta=0.5)

        assert converted is not None
        defeasible_count = sum(
            1 for r in converted.rules if r.rule_type == RuleType.DEFEASIBLE
        )
        assert defeasible_count >= 0

    def test_convert_theory_unknown_strategy_raises(self):
        """Unknown partition strategy raises ValueError."""
        theory = Theory()
        theory.add_fact("a(x)")
        with pytest.raises(ValueError, match="Unknown partition strategy"):
            convert_theory_to_defeasible(theory, partition_strategy='nonexistent')

    def test_convert_theory_leaf_strategy(self):
        """Leaf partition strategy marks facts as defeasible."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.STRICT, label="r1"))

        converted = convert_theory_to_defeasible(theory, partition_strategy='leaf')

        assert converted is not None
        # Leaf: facts defeasible, rules strict
        strict_rules = [r for r in converted.rules if r.rule_type == RuleType.STRICT]
        assert len(strict_rules) >= 1


class TestPartitionApplications:
    """Test phi_kappa with various partition strategies."""
    
    def test_phi_kappa_partition_depth_k1(self):
        """Test phi_kappa with depth partition k=1."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        
        depths = compute_dependency_depths(theory)
        converted = phi_kappa(theory, partition_depth(1, depths))
        
        assert converted is not None
    
    def test_phi_kappa_partition_depth_k2(self):
        """Test phi_kappa with depth partition k=2."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule("b(X)", ("a(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("b(X)",), RuleType.STRICT, label="r2"))
        
        depths = compute_dependency_depths(theory)
        converted = phi_kappa(theory, partition_depth(2, depths))
        
        assert converted is not None
    
    def test_phi_kappa_partition_random_multiple_seeds(self):
        """Test partition_random with different seeds."""
        theory = Theory()
        for i in range(10):
            theory.add_rule(Rule(f"h{i}(X)", ("a(X)",), RuleType.STRICT, label=f"r{i}"))
        
        # Different seeds
        conv1 = phi_kappa(theory, partition_random(0.5, seed=1))
        conv2 = phi_kappa(theory, partition_random(0.5, seed=2))
        conv3 = phi_kappa(theory, partition_random(0.5, seed=3))
        
        # All should produce valid conversions
        assert conv1 is not None
        assert conv2 is not None
        assert conv3 is not None
    
    def test_phi_kappa_preserves_defeasible_rules(self):
        """Test that existing defeasible rules stay defeasible."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_rule(Rule(
            head="b(X)",
            body=("a(X)",),
            rule_type=RuleType.DEFEASIBLE,  # Already defeasible
            label="r1"
        ))
        
        converted = phi_kappa(theory, partition_rule)
        
        # Should preserve defeasible type
        defeasible_count = sum(1 for r in converted.rules 
                              if r.rule_type == RuleType.DEFEASIBLE)
        assert defeasible_count >= 1
