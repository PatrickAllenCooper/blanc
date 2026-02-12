"""
Comprehensive tests for codec/encoder.py (M4) to improve coverage.

Targets M4 encoder for 38% -> 70%+ coverage improvement.

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.encoder import PureFormalEncoder


class TestM4EncoderComprehensive:
    """Comprehensive tests for M4 (pure formal) encoder."""
    
    def setup_method(self):
        """Setup encoder for each test."""
        self.encoder = PureFormalEncoder()
    
    def test_encode_fact_with_period(self):
        """Test encoding fact that already has period."""
        fact = "bird(robin)."
        encoded = self.encoder.encode_fact(fact)
        
        assert encoded.endswith('.')
        assert encoded.count('.') == 1  # Only one period
    
    def test_encode_fact_without_period(self):
        """Test encoding fact without period."""
        fact = "bird(robin)"
        encoded = self.encoder.encode_fact(fact)
        
        assert encoded.endswith('.')
    
    def test_encode_rule_defeasible_annotation(self):
        """Test defeasible rule has correct annotation."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = self.encoder.encode_rule(rule)
        
        assert "% defeasible" in encoded or ":- " in encoded
    
    def test_encode_rule_defeater_annotation(self):
        """Test defeater has correct annotation."""
        rule = Rule(
            head="flies(X)",
            body=("penguin(X)",),
            rule_type=RuleType.DEFEATER,
            label="r1"
        )
        
        encoded = self.encoder.encode_rule(rule)
        
        assert "% defeater" in encoded or "defeater" in encoded
    
    def test_encode_rule_multi_body(self):
        """Test rule with multiple body literals."""
        rule = Rule(
            head="hunts(X)",
            body=("mammal(X)", "carnivore(X)", "predator(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = self.encoder.encode_rule(rule)
        
        assert "mammal" in encoded
        assert "carnivore" in encoded
        assert "predator" in encoded
        assert "," in encoded  # Body literals separated by commas
    
    def test_encode_rule_no_label(self):
        """Test encoding rule without label."""
        rule = Rule(
            head="a(X)",
            body=("b(X)",),
            rule_type=RuleType.STRICT,
            label=None
        )
        
        encoded = self.encoder.encode_rule(rule)
        
        assert ":-" in encoded
    
    def test_encode_theory_mixed(self):
        """Test encoding theory with facts and rules."""
        from blanc.core.theory import Theory
        
        theory = Theory()
        theory.add_fact("bird(robin)")
        theory.add_fact("fish(salmon)")
        theory.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        theory.add_rule(Rule("swims(X)", ("fish(X)",), RuleType.STRICT, label="r2"))
        
        encoded = self.encoder.encode_theory(theory)
        
        assert "bird(robin)" in encoded
        assert "fish(salmon)" in encoded
        assert "flies" in encoded
        assert "swims" in encoded
    
    def test_encoder_validation_well_formed(self):
        """Test encoder validates well-formed atoms."""
        # Valid fact
        fact = "predicate(constant)"
        encoded = self.encoder.encode_fact(fact)
        assert encoded.endswith('.')
    
    def test_encoder_handles_complex_terms(self):
        """Test encoder with complex predicate names."""
        fact = "complex_predicate_name(term123)"
        encoded = self.encoder.encode_fact(fact)
        
        assert "complex_predicate_name" in encoded
        assert "term123" in encoded
