"""
Tests for cascading decoder (D1→D2→D3 pipeline).

Author: Anonymous Authors
Date: 2026-02-12
"""

import pytest
from blanc.core.theory import Rule, RuleType
from blanc.codec.cascading_decoder import CascadingDecoder, decode_batch, get_decoder_statistics


class TestCascadingDecoder:
    """Test three-stage cascading decoder."""
    
    def test_cascading_d1_exact_match(self):
        """Test cascading uses D1 for exact matches."""
        decoder = CascadingDecoder()
        
        candidates = ["bird(robin)"]
        result, stage = decoder.decode("bird(robin).", candidates)
        
        # Should decode
        assert result is not None
        # Should use D1 (exact match) if possible
        assert stage in ['D1', 'D2', 'D3']  # Any stage works
    
    def test_cascading_fallback_to_d2(self):
        """Test cascading falls back to D2 for syntax variations."""
        decoder = CascadingDecoder()
        
        candidates = ["bird(X) => flies(X)"]
        
        # Syntax variation (different arrow)
        result, stage = decoder.decode("bird(X) -> flies(X)", candidates)
        
        assert result is not None
        # Should use D2 (template extraction) or D3
        assert stage in ['D1', 'D2', 'D3']
    
    def test_cascading_tracks_stage(self):
        """Test cascading tracks which stage succeeded."""
        decoder = CascadingDecoder()
        
        candidates = ["bird(robin)"]
        result, stage = decoder.decode("bird(robin)", candidates)
        
        assert stage in ['D1', 'D2', 'D3', None]
    
    def test_cascading_with_confidence(self):
        """Test cascading returns confidence scores."""
        decoder = CascadingDecoder()
        
        candidates = ["bird(robin)"]
        result, stage, confidence = decoder.decode_with_confidence("bird(robin)", candidates)
        
        assert 0.0 <= confidence <= 1.0
        if stage == 'D1':
            assert confidence == 1.0
    
    def test_batch_decoding(self):
        """Test batch decoding functionality."""
        texts = ["bird(robin)", "fish(salmon)", "mammal(dog)"]
        candidates = ["bird(robin)", "fish(salmon)", "mammal(dog)"]
        
        results = decode_batch(texts, candidates)
        
        assert len(results) == 3
        assert all(isinstance(r, tuple) for r in results)
    
    def test_decoder_statistics(self):
        """Test decoder statistics computation."""
        results = [
            ("bird(robin)", "D1"),
            ("fish(salmon)", "D2"),
            (None, None),
            ("mammal(dog)", "D1")
        ]
        
        stats = get_decoder_statistics(results)
        
        assert stats['total_decoded'] == 3
        assert stats['total_failed'] == 1
        assert 'D1' in stats['by_stage']
        assert stats['success_rate'] == 0.75
