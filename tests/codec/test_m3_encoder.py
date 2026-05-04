"""
Tests for M3 encoder (annotated formal modality).

Author: Anonymous Authors
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.m3_encoder import encode_m3, encode_m3_theory
from blanc.codec.nl_mapping import get_nl_mapping


class TestM3Encoder:
    """Test M3 encoder functionality."""
    
    def test_encode_m3_fact(self):
        """Test M3 encoding of fact."""
        fact = "bird(robin)"
        encoded = encode_m3(fact, domain='biology')
        
        assert "bird(robin)" in encoded
        assert "#" in encoded  # Has comment
        assert "robin" in encoded.lower()
    
    def test_encode_m3_defeasible_rule(self):
        """Test M3 encoding of defeasible rule."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m3(rule, domain='biology')
        
        assert "=>" in encoded  # Defeasible arrow
        assert "#" in encoded  # Has comment
        assert "bird" in encoded.lower()
        assert "fl" in encoded.lower()  # flies
    
    def test_encode_m3_strict_rule(self):
        """Test M3 encoding of strict rule."""
        rule = Rule(
            head="animal(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT,
            label="r1"
        )
        
        encoded = encode_m3(rule, domain='biology')
        
        assert "->" in encoded  # Strict arrow
        assert "#" in encoded
    
    def test_encode_m3_multi_antecedent(self):
        """Test M3 encoding of rule with multiple antecedents."""
        rule = Rule(
            head="hunts(X)",
            body=("mammal(X)", "carnivore(X)"),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m3(rule, domain='biology')
        
        assert "mammal" in encoded.lower()
        assert "carnivore" in encoded.lower()
        assert "#" in encoded
    
    def test_encode_m3_all_domains(self):
        """Test M3 encoding works for all 3 domains."""
        # Biology
        bio_fact = "bird(robin)"
        bio_encoded = encode_m3(bio_fact, domain='biology')
        assert "#" in bio_encoded
        
        # Legal
        legal_fact = "statute(gdpr)"
        legal_encoded = encode_m3(legal_fact, domain='legal')
        assert "#" in legal_encoded
        
        # Materials
        mat_fact = "metal(iron)"
        mat_encoded = encode_m3(mat_fact, domain='materials')
        assert "#" in mat_encoded


class TestM3RoundTrip:
    """Test M3 round-trip encoding/decoding."""
    
    def test_m3_roundtrip_with_d1(self):
        """Test M3 encoding can be decoded (stripping comments)."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1"
        )
        
        encoded = encode_m3(rule, domain='biology')
        
        # M3 should have formal part before '#'
        assert '#' in encoded
        formal_part = encoded.split('#')[0].strip()
        
        # Should contain key elements
        assert '=>' in formal_part  # Defeasible arrow
        assert 'bird' in formal_part
        assert 'flies' in formal_part
        assert 'r1' in formal_part  # Label
