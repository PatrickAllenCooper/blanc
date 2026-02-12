"""
Tests for D2 decoder (template extraction).

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.d2_decoder import decode_d2, normalize_text, decode_d2_with_scores


class TestD2Decoder:
    """Test D2 decoder functionality."""
    
    def test_decode_d2_exact_match(self):
        """Test D2 with exact match (should work like D1)."""
        candidates = ["bird(X) => flies(X)", "fish(X) => swims(X)"]
        
        result = decode_d2("bird(X) => flies(X)", candidates)
        
        assert result == "bird(X) => flies(X)"
    
    def test_decode_d2_syntax_variation(self):
        """Test D2 handles syntax variations."""
        candidates = ["bird(X) => flies(X)", "fish(X) => swims(X)"]
        
        # Different arrow syntax
        result = decode_d2("bird(X) -> flies(X)", candidates)
        
        assert result == "bird(X) => flies(X)"
    
    def test_decode_d2_whitespace(self):
        """Test D2 handles whitespace differences."""
        candidates = ["bird(X) => flies(X)"]
        
        # Extra whitespace
        result = decode_d2("bird( X )  =>  flies( X )", candidates)
        
        assert result == "bird(X) => flies(X)"
    
    def test_decode_d2_case_insensitive(self):
        """Test D2 normalizes case."""
        candidates = ["bird(X) => flies(X)"]
        
        # Different case
        result = decode_d2("BIRD(X) => FLIES(X)", candidates)
        
        assert result == "bird(X) => flies(X)"
    
    def test_decode_d2_threshold(self):
        """Test D2 respects distance threshold."""
        candidates = ["bird(X) => flies(X)"]
        
        # Very different text
        result = decode_d2("completely different text", candidates, threshold=5)
        
        # Should return None (too far)
        assert result is None
    
    def test_decode_d2_closest_match(self):
        """Test D2 picks closest match among candidates."""
        candidates = [
            "bird(X) => flies(X)",
            "fish(X) => swims(X)",
            "mammal(X) => walks(X)"
        ]
        
        # Slight variation of first candidate
        result = decode_d2("bird(Y) => flies(Y)", candidates)
        
        assert result == "bird(X) => flies(X)"
    
    def test_decode_d2_with_scores(self):
        """Test D2 scoring function."""
        candidates = [
            "bird(X) => flies(X)",
            "fish(X) => swims(X)"
        ]
        
        scores = decode_d2_with_scores("bird(X) -> flies(X)", candidates)
        
        assert len(scores) == 2
        assert scores[0][0] == "bird(X) => flies(X)"  # Closest should be first
        assert scores[0][1] < scores[1][1]  # Distance to first < distance to second


class TestTextNormalization:
    """Test text normalization for D2."""
    
    def test_normalize_arrows(self):
        """Test arrow normalization."""
        assert "=>" in normalize_text("bird(X) ⇒ flies(X)")
        assert "->" in normalize_text("bird(X) → flies(X)")
    
    def test_normalize_whitespace(self):
        """Test whitespace normalization."""
        normalized = normalize_text("bird(  X  )  =>  flies(  X  )")
        assert "  " not in normalized  # No double spaces
    
    def test_normalize_case(self):
        """Test case normalization."""
        normalized = normalize_text("BIRD(X) => FLIES(X)")
        assert normalized == normalize_text("bird(x) => flies(x)")
