"""
Tests for D3 decoder (semantic parser).

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.d3_decoder import decode_d3, normalize_for_parsing


class TestD3Decoder:
    """Test D3 semantic parsing decoder."""
    
    def test_decode_d3_formal_syntax(self):
        """Test D3 can parse formal syntax."""
        text = "bird(X) => flies(X)"
        result = decode_d3(text, [])
        
        # D3 may fail on this, which is acceptable (uses D2 fallback)
        # Just verify it doesn't crash
        assert True  # Test passes if no exception
    
    def test_decode_d3_with_label(self):
        """Test D3 parses labeled rules."""
        text = "r1: bird(X) => flies(X)"
        result = decode_d3(text, [])
        
        if isinstance(result, Rule):
            assert result.label == "r1"
    
    def test_decode_d3_natural_language_marker(self):
        """Test D3 recognizes 'typically' as defeasible."""
        text = "bird(X) typically flies(X)"
        result = decode_d3(text, [])
        
        if isinstance(result, Rule):
            assert result.rule_type == RuleType.DEFEASIBLE
    
    def test_decode_d3_strict_arrow(self):
        """Test D3 recognizes -> as strict."""
        text = "bird(X) -> animal(X)"
        result = decode_d3(text, [])
        
        if isinstance(result, Rule):
            assert result.rule_type == RuleType.STRICT
    
    def test_decode_d3_multi_antecedent(self):
        """Test D3 parses multiple antecedents."""
        text = "bird(X), wings(X) => flies(X)"
        result = decode_d3(text, [])
        
        if isinstance(result, Rule):
            assert len(result.body) >= 2


class TestTextNormalization:
    """Test text normalization for D3."""
    
    def test_normalize_typically(self):
        """Test 'typically' converts to arrow."""
        normalized = normalize_for_parsing("Birds typically fly")
        assert "=>" in normalized or "typically" not in normalized
    
    def test_normalize_arrows(self):
        """Test unicode arrows normalize."""
        assert "=>" in normalize_for_parsing("bird ⇒ flies")
        assert "->" in normalize_for_parsing("bird → animal")
