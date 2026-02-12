"""
Tests for M1 encoder (narrative modality).

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.m1_encoder import encode_m1, pluralize_predicate


class TestM1Encoder:
    """Test M1 encoder functionality."""
    
    def test_encode_m1_fact(self):
        """Test M1 encoding of fact."""
        fact = "bird(robin)"
        encoded = encode_m1(fact, domain='biology')
        
        assert "Robin" in encoded  # Capitalized
        assert "bird" in encoded.lower()
        assert encoded.endswith('.')
    
    def test_encode_m1_defeasible_rule(self):
        """Test M1 uses hedging for defeasible rules."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m1(rule, domain='biology')
        
        # Should have hedging word
        assert any(word in encoded.lower() for word in ['typically', 'usually', 'generally'])
        assert "bird" in encoded.lower()
        assert "fly" in encoded.lower()
    
    def test_encode_m1_strict_rule(self):
        """Test M1 has no hedging for strict rules."""
        rule = Rule(
            head="animal(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT,
            label="r1"
        )
        
        encoded = encode_m1(rule, domain='biology')
        
        # Should NOT have hedging
        assert not any(word in encoded.lower() for word in ['typically', 'usually', 'generally'])
    
    def test_encode_m1_multi_antecedent(self):
        """Test M1 with multiple antecedents."""
        rule = Rule(
            head="hunts(X)",
            body=("mammal(X)", "carnivore(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m1(rule, domain='biology')
        
        assert "mammal" in encoded.lower()
        assert "carnivore" in encoded.lower() or "carnivorous" in encoded.lower()
    
    def test_encode_m1_all_domains(self):
        """Test M1 works for all domains."""
        # Biology
        bio = Rule(head="flies(X)", body=("bird(X)",), 
                  rule_type=RuleType.DEFEASIBLE, label="r1")
        bio_encoded = encode_m1(bio, domain='biology')
        assert len(bio_encoded) > 0
        
        # Legal
        legal = Rule(head="legal_document(X)", body=("statute(X)",),
                    rule_type=RuleType.STRICT, label="r1")
        legal_encoded = encode_m1(legal, domain='legal')
        assert len(legal_encoded) > 0
        
        # Materials
        mat = Rule(head="material(X)", body=("metal(X)",),
                  rule_type=RuleType.STRICT, label="r1")
        mat_encoded = encode_m1(mat, domain='materials')
        assert len(mat_encoded) > 0


class TestPluralizer:
    """Test predicate pluralization."""
    
    def test_pluralize_is_a(self):
        """Test pluralizing 'is a X'."""
        result = pluralize_predicate("is a bird")
        assert "are" in result
        assert "bird" in result
    
    def test_pluralize_can(self):
        """Test 'can X' stays same."""
        result = pluralize_predicate("can fly")
        assert result == "can fly"
    
    def test_pluralize_has(self):
        """Test 'has X' becomes 'have X'."""
        result = pluralize_predicate("has obligation")
        assert "have" in result
