"""
Tests for M2 encoder (semi-formal modality).

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.m2_encoder import encode_m2, encode_m2_theory
from blanc.codec.nl_mapping import get_nl_mapping


class TestM2Encoder:
    """Test M2 encoder functionality."""
    
    def test_encode_m2_fact(self):
        """Test M2 encoding of fact with NL predicates."""
        fact = "bird(robin)"
        encoded = encode_m2(fact, domain='biology')
        
        # Should have NL predicate
        assert "is a bird" in encoded
        assert "robin" in encoded
    
    def test_encode_m2_defeasible_rule(self):
        """Test M2 encoding uses defeasible arrow."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m2(rule, domain='biology')
        
        assert "⇒" in encoded  # Defeasible arrow
        assert "∀" in encoded or "forall" in encoded.lower()
    
    def test_encode_m2_strict_rule(self):
        """Test M2 encoding uses strict arrow."""
        rule = Rule(
            head="animal(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT,
            label="r1"
        )
        
        encoded = encode_m2(rule, domain='biology')
        
        assert "→" in encoded  # Strict arrow
    
    def test_encode_m2_nl_predicates(self):
        """Test that M2 uses natural language predicates."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m2(rule, domain='biology')
        
        # Should use NL versions
        assert "bird" in encoded  # Predicate name
        assert "fly" in encoded.lower()  # NL version
    
    def test_encode_m2_all_domains(self):
        """Test M2 encoding for all domains."""
        # Biology
        bio = Rule(head="flies(X)", body=("bird(X)",), 
                  rule_type=RuleType.DEFEASIBLE, label="r1")
        bio_encoded = encode_m2(bio, domain='biology')
        assert "⇒" in bio_encoded
        
        # Legal
        legal = Rule(head="legal_document(X)", body=("statute(X)",),
                    rule_type=RuleType.STRICT, label="r1")
        legal_encoded = encode_m2(legal, domain='legal')
        assert "→" in legal_encoded
        
        # Materials
        mat = Rule(head="material(X)", body=("metal(X)",),
                  rule_type=RuleType.STRICT, label="r1")
        mat_encoded = encode_m2(mat, domain='materials')
        assert "→" in mat_encoded
