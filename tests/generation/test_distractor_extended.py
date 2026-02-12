"""
Extended tests for generation/distractor.py to increase coverage.

Targets lines 55-58, 103-106, 121, 144, 162, 177, 206-211, 225-250, 263-274, 280, 283
for 59% -> 90% coverage improvement.

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.generation.distractor import (
    generate_syntactic_distractors,
    generate_random_distractors,
    generate_adversarial_distractors,
)


class TestSyntacticDistractors:
    """Test syntactic distractor generation."""
    
    def test_syntactic_distractors_from_fact(self):
        """Test syntactic distractor generation from fact."""
        theory = Theory()
        theory.add_fact("bird(robin)")
        theory.add_fact("bird(sparrow)")
        theory.add_fact("mammal(dog)")
        theory.add_fact("mammal(cat)")
        
        target_element = "bird(robin)"
        
        distractors = generate_syntactic_distractors(
            target_element,
            theory,
            k=3
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 3
        # Should be similar to target
        assert all('bird' in d or 'robin' in d for d in distractors if d != target_element)
    
    def test_syntactic_distractors_from_rule(self):
        """Test syntactic distractor generation from rule."""
        theory = Theory()
        
        target_rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        theory.add_rule(target_rule)
        
        theory.add_rule(Rule(
            head="swims(X)",
            body=("fish(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r2"
        ))
        
        distractors = generate_syntactic_distractors(
            target_rule,
            theory,
            k=2
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 2
    
    def test_syntactic_distractors_k_parameter(self):
        """Test that k parameter controls number of distractors."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        
        distractors_2 = generate_syntactic_distractors(target, theory, k=2)
        distractors_5 = generate_syntactic_distractors(target, theory, k=5)
        
        assert len(distractors_2) <= 2
        assert len(distractors_5) <= 5
        assert len(distractors_5) >= len(distractors_2)
    
    def test_syntactic_distractors_empty_theory(self):
        """Test syntactic distractors with empty theory."""
        theory = Theory()
        
        distractors = generate_syntactic_distractors(
            "nonexistent(x)",
            theory,
            k=3
        )
        
        # Should return empty or minimal list
        assert isinstance(distractors, list)


class TestRandomDistractors:
    """Test random distractor generation."""
    
    def test_random_distractors_from_facts(self):
        """Test random distractor sampling from facts."""
        theory = Theory()
        for i in range(20):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        
        distractors = generate_random_distractors(
            target,
            theory,
            k=5
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 5
        assert target not in distractors
    
    def test_random_distractors_from_rules(self):
        """Test random distractor sampling from rules."""
        theory = Theory()
        for i in range(10):
            theory.add_rule(Rule(
                head=f"h{i}(X)",
                body=(f"b{i}(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"r{i}"
            ))
        
        target_rule = theory.rules[0]
        
        distractors = generate_random_distractors(
            target_rule,
            theory,
            k=3
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 3
    
    def test_random_distractors_deterministic_seed(self):
        """Test random distractors are deterministic with seed."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        # Same seed should give same results
        import random
        
        random.seed(42)
        distractors1 = generate_random_distractors("fact0(x)", theory, k=5)
        
        random.seed(42)
        distractors2 = generate_random_distractors("fact0(x)", theory, k=5)
        
        assert distractors1 == distractors2


class TestAdversarialDistractors:
    """Test adversarial distractor generation."""
    
    def test_adversarial_distractors_from_rule(self):
        """Test adversarial distractor generation from rule."""
        theory = Theory()
        theory.add_fact("bird(robin)")
        
        target_rule = Rule(
            head="flies(X)",
            body=("bird(X)", "wings(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        # Adversarial distractors should be "almost correct"
        distractors = generate_adversarial_distractors(
            target_rule,
            theory,
            k=2
        )
        
        assert isinstance(distractors, list)
        # May be empty if can't generate adversarial versions
        assert len(distractors) <= 2
    
    def test_adversarial_distractors_single_antecedent(self):
        """Test adversarial generation with single-antecedent rule."""
        theory = Theory()
        
        target_rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        # Can't make adversarial from single antecedent (nothing to remove)
        distractors = generate_adversarial_distractors(
            target_rule,
            theory,
            k=2
        )
        
        assert isinstance(distractors, list)
        # Might be empty for single-antecedent rules
    
    def test_adversarial_distractors_fact(self):
        """Test adversarial distractors from fact."""
        theory = Theory()
        theory.add_fact("bird(robin)")
        
        # Facts don't have antecedents, so adversarial may not apply
        distractors = generate_adversarial_distractors(
            "bird(robin)",
            theory,
            k=2
        )
        
        assert isinstance(distractors, list)


class TestDistractorValidation:
    """Test distractor validation and filtering."""
    
    def test_distractors_exclude_target(self):
        """Test that distractors never include the target element."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        
        # Test all strategies
        syntactic = generate_syntactic_distractors(target, theory, k=5)
        random_dist = generate_random_distractors(target, theory, k=5)
        
        assert target not in syntactic
        assert target not in random_dist
    
    def test_distractors_are_unique(self):
        """Test that distractors don't contain duplicates."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        distractors = generate_random_distractors(target, theory, k=5)
        
        # Should be unique
        assert len(distractors) == len(set(str(d) for d in distractors))
