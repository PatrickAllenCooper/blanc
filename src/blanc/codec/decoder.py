"""
Exact match decoder (D1).

Implements D1 decoding strategy from paper.tex Definition 29, line 723.

Author: Patrick Cooper
Date: 2026-02-11

CRITICAL COMPONENT: Round-trip consistency must be perfect.
Proposition (line 903): D1 satisfies round-trip by construction.
"""

from typing import List, Optional, Union
from blanc.core.theory import Rule, RuleType
from blanc.author.generation import AbductiveInstance

# Element can be fact (str) or Rule
Element = Union[str, Rule]


class ExactMatchDecoder:
    """
    D1: Exact match decoder.
    
    Definition 29 (paper.tex line 723): Exact match strategy.
    
    Properties (Proposition, line 893):
    - Sound: checkmark (always returns valid candidate or None)
    - Complete: X (fails on paraphrases)
    - Faithful: checkmark (no hallucinations)
    
    Round-trip (Proposition, line 903):
    - Satisfies round-trip consistency by construction
    - For encoded candidate c: decode(encode(c)) = c
    
    Strategy:
        1. Normalize response (whitespace, punctuation)
        2. Normalize each candidate
        3. Find exact string match
        4. Return matched candidate or None
    
    Safety:
        - Never returns element not in candidates
        - Deterministic (same input → same output)
        - No parsing errors (pure string matching)
    """
    
    def __init__(self):
        """Initialize decoder."""
        pass
    
    def decode(
        self,
        response: str,
        instance: AbductiveInstance
    ) -> Optional[Element]:
        """
        Decode response to candidate element.
        
        Args:
            response: Model response (string)
            instance: Instance containing candidates
        
        Returns:
            Matched candidate or None if no match
        
        Algorithm:
            1. Normalize response
            2. Try matching each candidate
            3. Return first exact match or None
        
        Safety: Only returns elements from instance.candidates.
        """
        # Normalize response
        response_norm = self._normalize(response)
        
        # Try matching each candidate
        for candidate in instance.candidates:
            # Normalize candidate
            if isinstance(candidate, str):
                candidate_norm = self._normalize(candidate)
            else:  # Rule
                candidate_norm = self._normalize_rule(candidate)
            
            # Check exact match
            if response_norm == candidate_norm:
                return candidate
        
        # No match found
        return None
    
    def _normalize(self, text: str) -> str:
        """
        Normalize text for matching.
        
        Normalization ORDER (critical):
            1. Strip leading/trailing whitespace
            2. Remove % comments FIRST
            3. Remove periods at end
            4. Collapse multiple spaces to single space
            5. Lowercase for comparison
        
        Safety: Preserves semantic content while removing formatting variance.
        """
        if not text:
            return ""
        
        # 1. Strip whitespace
        text = text.strip()
        
        # 2. Remove comments (% ...) BEFORE removing periods
        if '%' in text:
            text = text.split('%')[0].strip()
        
        # 3. Remove trailing period(s)
        while text.endswith('.'):
            text = text[:-1].strip()
        
        # 4. Collapse whitespace
        text = ' '.join(text.split())
        
        # 5. Lowercase for case-insensitive matching
        text = text.lower()
        
        return text
    
    def _normalize_rule(self, rule: Rule) -> str:
        """
        Normalize rule to canonical form for matching.
        
        Args:
            rule: Rule object
        
        Returns:
            Normalized string representation
        
        Format:
            - Facts: "p(a)"
            - Rules: "h(x) :- b1(x), b2(x)"
        
        Safety: Deterministic canonical form ensures consistent matching.
        """
        if rule.is_fact:
            return self._normalize(rule.head)
        
        # Build rule string
        body_str = ", ".join(rule.body)
        rule_str = f"{rule.head} :- {body_str}"
        
        return self._normalize(rule_str)


def decode_response(response: str, instance: AbductiveInstance) -> Optional[Element]:
    """
    Convenience function to decode response.
    
    Args:
        response: Model response string
        instance: Instance with candidates
    
    Returns:
        Matched candidate or None
    
    Example:
        >>> response = "bird(tweety)"
        >>> candidate = decode_response(response, instance)
    """
    decoder = ExactMatchDecoder()
    return decoder.decode(response, instance)
