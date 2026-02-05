"""
BLANC: Unified API for querying heterogeneous knowledge bases.

Supports Prolog, Answer Set Programming, Rulelog, and defeasible logic systems
for research on abductive and defeasible reasoning in foundation models.
"""

from blanc.core.knowledge_base import KnowledgeBase
from blanc.core.query import Query
from blanc.core.result import Result, ResultSet
from blanc.core.theory import Rule, RuleType, Theory

__version__ = "0.1.0"

__all__ = [
    "KnowledgeBase",
    "Query",
    "Result",
    "ResultSet",
    "Rule",
    "RuleType",
    "Theory",
]
