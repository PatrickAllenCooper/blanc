"""
D3 Decoder: Semantic Parser

Parses natural language and semi-formal text back to formal rules using grammar.
Paper Section 4.4 (D3: Semantic parser).

Author: Patrick Cooper
Date: 2026-02-12
"""

from typing import List, Union, Optional
from blanc.core.theory import Rule, RuleType
from lark import Lark, Transformer, v_args


# Grammar for parsing logical expressions
LOGIC_GRAMMAR = """
    ?start: rule | fact
    
    rule: label? body arrow head
    
    fact: atom
    
    body: atom ("," atom)* | atom ("and" atom)*
    
    arrow: "=>" | "->" | "⇒" | "→" | ":-" | "typically" | "usually"
    
    head: atom
    
    atom: predicate "(" args ")"
    
    predicate: WORD+
    
    args: WORD ("," WORD)*
    
    label: WORD ":"
    
    WORD: /[a-zA-Z_][a-zA-Z0-9_]*/
    
    %import common.WS
    %ignore WS
"""


class LogicTransformer(Transformer):
    """Transform parsed tree to Rule object."""
    
    @v_args(inline=True)
    def rule(self, *args):
        """Transform rule."""
        # Parse: [label?] body arrow head
        if len(args) == 4:
            label, body, arrow, head = args
        else:
            label = None
            body, arrow, head = args
        
        # Determine rule type from arrow
        if arrow in ['=>', '⇒', 'typically', 'usually']:
            rule_type = RuleType.DEFEASIBLE
        else:
            rule_type = RuleType.STRICT
        
        # Build rule
        return Rule(
            head=str(head),
            body=tuple(str(b) for b in body) if isinstance(body, list) else (str(body),),
            rule_type=rule_type,
            label=str(label) if label else None
        )
    
    def body(self, args):
        """Transform body to list of atoms."""
        return list(args)
    
    def atom(self, args):
        """Transform atom."""
        predicate = ''.join(str(a) for a in args[:-1])
        arguments = args[-1]
        return f"{predicate}({arguments})"
    
    def args(self, words):
        """Transform arguments."""
        return ', '.join(str(w) for w in words)
    
    def predicate(self, words):
        """Transform predicate."""
        return ''.join(str(w) for w in words)
    
    def label(self, word):
        """Transform label."""
        return str(word[0])
    
    def arrow(self, arrow):
        """Transform arrow."""
        return str(arrow[0])
    
    def fact(self, atom):
        """Transform fact."""
        return str(atom[0])


# Create parser
logic_parser = Lark(LOGIC_GRAMMAR, start='start', parser='lalr')
transformer = LogicTransformer()


def decode_d3(text: str, candidates: List[Union[str, Rule]]) -> Optional[Union[str, Rule]]:
    """
    Decode text using semantic parsing (D3).
    
    Uses grammar-based parser to extract logical structure from text.
    Handles natural language and semi-formal expressions.
    
    Args:
        text: Text to decode
        candidates: List of candidate elements (for validation)
    
    Returns:
        Decoded element or None if parsing fails
    
    Example:
        >>> text = "Birds typically can fly"
        >>> candidates = [Rule(...)]
        >>> decode_d3(text, candidates)
        Rule(head='flies(X)', body=('bird(X)',), ...)
    """
    
    if not text:
        return None
    
    try:
        # Try to parse text
        tree = logic_parser.parse(text)
        result = transformer.transform(tree)
        
        if candidates:
            result_str = str(result)
            for candidate in candidates:
                if str(candidate) == result_str:
                    return candidate
            return None
        
        return result
    
    except Exception as e:
        # Parsing failed, try fallback to D2-style matching
        if candidates:
            # Use template extraction as fallback
            from .d2_decoder import decode_d2
            return decode_d2(text, candidates, threshold=20)
        return None


def decode_d3_flexible(text: str, candidates: List[Union[str, Rule]]) -> Optional[Union[str, Rule]]:
    """
    Decode with flexible matching.
    
    Tries multiple text normalizations and pattern matching.
    
    Args:
        text: Text to decode
        candidates: Candidate elements
    
    Returns:
        Best matching candidate or None
    """
    
    # Try direct parsing
    result = decode_d3(text, candidates)
    if result:
        return result
    
    # Try normalizing text
    normalized = normalize_for_parsing(text)
    result = decode_d3(normalized, candidates)
    if result:
        return result
    
    # Try extracting key patterns
    result = extract_patterns(text, candidates)
    if result:
        return result
    
    return None


def normalize_for_parsing(text: str) -> str:
    """Normalize text for parsing."""
    import re
    
    # Handle M1 narrative format
    # "Birds typically can fly" -> extract pattern
    
    # Convert natural language markers to symbols
    text = text.replace(' typically ', ' => ')
    text = text.replace(' usually ', ' => ')
    text = text.replace(' generally ', ' => ')
    text = text.replace(' always ', ' -> ')
    
    # Try to extract formal structure from narrative
    # Pattern: "{subjects} {hedging} {predicate}" -> try to map to logic
    
    # Normalize arrows
    text = text.replace('⇒', '=>')
    text = text.replace('→', '->')
    
    # Remove periods
    text = text.rstrip('.')
    
    return text


def extract_patterns(text: str, candidates: List[Union[str, Rule]]) -> Optional[Union[str, Rule]]:
    """Extract patterns from text and match to candidates."""
    import re
    
    # Look for predicate patterns
    predicates = re.findall(r'\b[a-z_]+\([A-Z][a-z]*\)', text)
    
    if not predicates:
        return None
    
    # Try to match based on predicates found
    for candidate in candidates:
        cand_str = str(candidate)
        if all(pred in cand_str for pred in predicates):
            return candidate
    
    return None
