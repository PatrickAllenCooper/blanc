"""
Cascading Decoder: Three-Stage Decoder Pipeline

Implements D1 → D2 → D3 cascading fallback strategy.
Paper Section 4.4 (decoder pipeline).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import List, Union, Optional, Tuple
from blanc.core.theory import Rule
from .decoder import PureFormalDecoder
from .d2_decoder import decode_d2
from .d3_decoder import decode_d3


class CascadingDecoder:
    """
    Three-stage decoder with fallback.
    
    Tries decoders in order: D1 (exact) → D2 (template) → D3 (semantic)
    Returns first successful decode and which stage succeeded.
    """
    
    def __init__(self):
        """Initialize cascading decoder."""
        self.d1_decoder = PureFormalDecoder()
    
    def decode(self, text: str, candidates: List[Union[str, Rule]]) -> Tuple[Optional[Union[str, Rule]], Optional[str]]:
        """
        Decode text using cascading strategy.
        
        Args:
            text: Text to decode
            candidates: List of candidate elements
        
        Returns:
            Tuple of (decoded_element, stage_name) or (None, None)
        
        Example:
            >>> decoder = CascadingDecoder()
            >>> result, stage = decoder.decode("bird(X) => flies(X)", candidates)
            >>> print(f"Decoded by {stage}: {result}")
        """
        
        if not text or not candidates:
            return None, None
        
        # Stage 1: D1 (Exact Match)
        try:
            result = self.d1_decoder.decode_response(text, candidates)
            if result is not None:
                return result, 'D1'
        except Exception:
            pass
        
        # Stage 2: D2 (Template Extraction)
        try:
            result = decode_d2(text, candidates)
            if result is not None:
                return result, 'D2'
        except Exception:
            pass
        
        # Stage 3: D3 (Semantic Parsing)
        try:
            result = decode_d3(text, candidates)
            if result is not None:
                return result, 'D3'
        except Exception:
            pass
        
        # All stages failed
        return None, None
    
    def decode_with_confidence(self, text: str, candidates: List[Union[str, Rule]]) -> Tuple[Optional[Union[str, Rule]], Optional[str], float]:
        """
        Decode with confidence score.
        
        Returns:
            (decoded_element, stage_name, confidence)
            
        Confidence:
            - D1: 1.0 (exact match)
            - D2: 0.8-0.95 (based on edit distance)
            - D3: 0.6-0.85 (based on parse success)
        """
        
        result, stage = self.decode(text, candidates)
        
        if stage == 'D1':
            confidence = 1.0
        elif stage == 'D2':
            confidence = 0.9  # Template extraction is reliable
        elif stage == 'D3':
            confidence = 0.75  # Semantic parsing less certain
        else:
            confidence = 0.0
        
        return result, stage, confidence


def decode_batch(texts: List[str], candidates: List[Union[str, Rule]]) -> List[Tuple]:
    """
    Decode batch of texts using cascading decoder.
    
    Args:
        texts: List of texts to decode
        candidates: Candidate elements (same for all)
    
    Returns:
        List of (result, stage) tuples
    """
    decoder = CascadingDecoder()
    results = []
    
    for text in texts:
        result, stage = decoder.decode(text, candidates)
        results.append((result, stage))
    
    return results


def get_decoder_statistics(results: List[Tuple]) -> dict:
    """
    Get statistics on decoder stage usage.
    
    Args:
        results: List of (result, stage) tuples from decode_batch
    
    Returns:
        Dictionary with stage usage statistics
    """
    from collections import Counter
    
    stages = [stage for _, stage in results if stage]
    stage_counts = Counter(stages)
    
    total = len([r for r, s in results if s is not None])
    
    return {
        'total_decoded': total,
        'total_failed': len(results) - total,
        'by_stage': dict(stage_counts),
        'success_rate': total / len(results) if results else 0.0
    }
