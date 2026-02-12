"""
Complete M4 encoder tests to push coverage from 38% to 70%+.

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.codec.encoder import PureFormalEncoder


class TestM4Complete:
    """Complete M4 encoder coverage."""
    
    def setup_method(self):
        self.encoder = PureFormalEncoder()
    
    def test_encode_theory_empty(self):
        """Test encoding empty theory."""
        theory = Theory()
        encoded = self.encoder.encode_theory(theory)
        assert encoded is not None
    
    def test_encode_theory_facts_only(self):
        """Test encoding theory with only facts."""
        theory = Theory()
        theory.add_fact("a(x)")
        theory.add_fact("b(y)")
        
        encoded = self.encoder.encode_theory(theory)
        assert "a(x)" in encoded
        assert "b(y)" in encoded
    
    def test_encode_theory_rules_only(self):
        """Test encoding theory with only rules."""
        theory = Theory()
        theory.add_rule(Rule("a(X)", ("b(X)",), RuleType.STRICT, label="r1"))
        theory.add_rule(Rule("c(X)", ("d(X)",), RuleType.DEFEASIBLE, label="r2"))
        
        encoded = self.encoder.encode_theory(theory)
        assert "a(X)" in encoded
        assert "c(X)" in encoded
    
    def test_encode_rule_all_types(self):
        """Test encoding all rule types."""
        # Strict
        strict = Rule("a(X)", ("b(X)",), RuleType.STRICT, label="r1")
        strict_enc = self.encoder.encode_rule(strict)
        assert ":-" in strict_enc
        
        # Defeasible
        defeasible = Rule("c(X)", ("d(X)",), RuleType.DEFEASIBLE, label="r2")
        defeasible_enc = self.encoder.encode_rule(defeasible)
        assert "defeasible" in defeasible_enc or ":- " in defeasible_enc
        
        # Defeater
        defeater = Rule("e(X)", ("f(X)",), RuleType.DEFEATER, label="r3")
        defeater_enc = self.encoder.encode_rule(defeater)
        assert "defeater" in defeater_enc
    
    def test_encode_rule_complex_body(self):
        """Test encoding rule with many body literals."""
        rule = Rule(
            "conclusion(X)",
            ("premise1(X)", "premise2(X)", "premise3(X)", "premise4(X)"),
            RuleType.DEFEASIBLE,
            label="complex"
        )
        
        encoded = self.encoder.encode_rule(rule)
        assert all(f"premise{i}" in encoded for i in range(1, 5))
    
    def test_encode_fact_special_characters(self):
        """Test encoding facts with underscores and numbers."""
        facts = [
            "predicate_with_underscore(term)",
            "pred123(term456)",
            "complex_pred_123(term_456)"
        ]
        
        for fact in facts:
            encoded = self.encoder.encode_fact(fact)
            assert fact.rstrip('.') in encoded
    
    def test_encoder_consistency(self):
        """Test encoder produces consistent output."""
        rule = Rule("a(X)", ("b(X)",), RuleType.STRICT, label="r1")
        
        enc1 = self.encoder.encode_rule(rule)
        enc2 = self.encoder.encode_rule(rule)
        
        assert enc1 == enc2  # Should be deterministic
