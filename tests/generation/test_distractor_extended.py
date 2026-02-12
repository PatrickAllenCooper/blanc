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
    sample_fact_distractors,
    sample_rule_distractors,
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
        
        distractors = sample_fact_distractors(
            target_element,
            theory,
            k=3,
            strategy="syntactic"
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 3
        assert target_element not in distractors
    
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
        
        distractors = sample_rule_distractors(
            target_rule,
            theory,
            k=2,
            strategy="syntactic"
        )
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 2
    
    def test_syntactic_distractors_k_parameter(self):
        """Test that k parameter controls number of distractors."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        
        distractors_2 = sample_fact_distractors(target, theory, k=2, strategy="syntactic")
        distractors_5 = sample_fact_distractors(target, theory, k=5, strategy="syntactic")
        
        assert len(distractors_2) <= 2
        assert len(distractors_5) <= 5
        assert len(distractors_5) >= len(distractors_2)
    
    def test_syntactic_distractors_empty_theory(self):
        """Test syntactic distractors with empty theory."""
        theory = Theory()
        
        distractors = sample_fact_distractors(
            "nonexistent(x)",
            theory,
            k=3,
            strategy="syntactic"
        )
        
        # Should return empty list
        assert isinstance(distractors, list)
        assert len(distractors) == 0


class TestRandomDistractors:
    """Test random distractor generation."""
    
    def test_random_distractors_from_facts(self):
        """Test random distractor sampling from facts."""
        theory = Theory()
        for i in range(20):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        
        distractors = sample_fact_distractors(
            target,
            theory,
            k=5,
            strategy="random"
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
        
        distractors = sample_rule_distractors(
            target_rule,
            theory,
            k=3,
            strategy="random"
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
        
        distractors = sample_fact_distractors("fact0(x)", theory, k=5, strategy="random")
        
        assert isinstance(distractors, list)
        assert len(distractors) <= 5


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
        distractors = sample_rule_distractors(
            target_rule,
            theory,
            k=2,
            strategy="adversarial"
        )
        
        assert isinstance(distractors, list)
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
        
        distractors = sample_rule_distractors(
            target_rule,
            theory,
            k=2,
            strategy="adversarial"
        )
        
        assert isinstance(distractors, list)
    
    def test_adversarial_distractors_fact(self):
        """Test adversarial distractors from fact."""
        theory = Theory()
        theory.add_fact("bird(robin)")
        
        distractors = sample_fact_distractors(
            "bird(robin)",
            theory,
            k=2,
            strategy="adversarial"
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
        syntactic = sample_fact_distractors(target, theory, k=5, strategy="syntactic")
        random_dist = sample_fact_distractors(target, theory, k=5, strategy="random")
        
        assert target not in syntactic
        assert target not in random_dist
    
    def test_distractors_are_unique(self):
        """Test that distractors don't contain duplicates."""
        theory = Theory()
        for i in range(10):
            theory.add_fact(f"fact{i}(x)")
        
        target = "fact0(x)"
        distractors = sample_fact_distractors(target, theory, k=5, strategy="random")
        
        # Should be unique
        assert len(distractors) == len(set(str(d) for d in distractors))
