"""
Shared utilities for atom and predicate manipulation.

Previously duplicated verbatim across m1_encoder, m2_encoder, m3_encoder,
and d2_decoder. Centralised here so changes propagate everywhere.
"""

from __future__ import annotations


def extract_predicate(atom: str) -> str:
    """Return the predicate symbol from a (possibly ground) atom.

    Examples::

        extract_predicate("bird(tweety)")  -> "bird"
        extract_predicate("flies")         -> "flies"
    """
    return atom.split("(")[0] if "(" in atom else atom


def extract_constant(atom: str) -> str:
    """Return the first argument of a unary ground atom.

    Examples::

        extract_constant("bird(tweety)")  -> "tweety"
        extract_constant("bird")          -> ""
    """
    if "(" in atom and ")" in atom:
        return atom[atom.index("(") + 1 : atom.index(")")]
    return ""


def capitalize(text: str) -> str:
    """Capitalise the first character without lowercasing the rest."""
    return text[0].upper() + text[1:] if text else text
