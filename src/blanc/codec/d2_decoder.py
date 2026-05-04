"""
D2 Decoder: Template Extraction via Edit Distance

Decodes text by finding closest match via Levenshtein distance.
Paper Section 4.4 (D2: Template extraction).

Author: Anonymous Authors
Date: 2026-02-12
"""

from typing import List, Optional, Union
from Levenshtein import distance as levenshtein_distance
from blanc.core.theory import Rule
from blanc.utils.predicates import extract_predicate  # noqa: F401 (re-exported for callers)


def decode_d2(text: str, candidates: List[Union[str, Rule]], threshold: int = 10) -> Optional[Union[str, Rule]]:
    """
    Decode text using template extraction (D2).
    
    Finds closest candidate via Levenshtein edit distance.
    Fallback decoder when D1 (exact match) fails.
    
    Args:
        text: Text to decode
        candidates: List of candidate elements
        threshold: Maximum edit distance to accept
    
    Returns:
        Best matching candidate or None if no match within threshold
    
    Example:
        >>> candidates = ["bird(X) => flies(X)", "fish(X) => swims(X)"]
        >>> decode_d2("bird(X) -> flies(X)", candidates)
        'bird(X) => flies(X)'  # Closest match despite syntax difference
    """
    
    if not candidates:
        return None
    
    # Convert candidates to strings for comparison
    candidate_strs = [str(c) for c in candidates]
    
    # Normalize text for comparison
    text_normalized = normalize_text(text)
    
    # Find closest match
    min_distance = float('inf')
    best_candidate = None
    best_index = -1
    
    for i, cand_str in enumerate(candidate_strs):
        cand_normalized = normalize_text(cand_str)
        dist = levenshtein_distance(text_normalized, cand_normalized)
        
        if dist < min_distance:
            min_distance = dist
            best_candidate = candidates[i]
            best_index = i
    
    # Return best match if within threshold
    if min_distance <= threshold:
        return best_candidate
    else:
        return None


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.
    
    Removes extra whitespace, converts to lowercase, removes punctuation variations.
    
    Args:
        text: Text to normalize
    
    Returns:
        Normalized text
    """
    import re
    
    # Remove comments (for M3 format)
    if '#' in text:
        text = text.split('#')[0]
    
    # Convert to lowercase
    text = text.lower()
    
    # Normalize arrows
    text = text.replace('⇒', '=>')
    text = text.replace('→', '->')
    text = text.replace('∧', ',')
    text = text.replace('∀', 'forall')
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Remove trailing periods
    text = text.rstrip('.')
    
    return text


def decode_d2_with_scores(text: str, candidates: List[Union[str, Rule]]) -> List[tuple]:
    """
    Decode with distance scores for all candidates.
    
    Useful for debugging and analysis.
    
    Args:
        text: Text to decode
        candidates: Candidate elements
    
    Returns:
        List of (candidate, distance) tuples sorted by distance
    """
    
    text_normalized = normalize_text(text)
    
    scores = []
    for candidate in candidates:
        cand_normalized = normalize_text(str(candidate))
        dist = levenshtein_distance(text_normalized, cand_normalized)
        scores.append((candidate, dist))
    
    # Sort by distance (ascending)
    scores.sort(key=lambda x: x[1])
    
    return scores


