"""
Rulelog backend.

Adapter for Rulelog knowledge representation system.
"""

from pathlib import Path
from typing import Set, Union

from blanc.backends.base import KnowledgeBaseBackend
from blanc.core.query import Query
from blanc.core.result import DerivationTree, ResultSet
from blanc.core.theory import Theory


class RulelogBackend(KnowledgeBaseBackend):
    """
    Rulelog backend.

    Note: Placeholder implementation. Rulelog integration strategy TBD.
    """

    def __init__(self, **kwargs):
        """Initialize Rulelog backend."""
        self._theory: Union[Theory, None] = None

    def load_theory(self, source: Union[str, Path, Theory]) -> None:
        """Load knowledge base from source."""
        raise NotImplementedError(
            "Rulelog backend not yet implemented. "
            "Rulelog integration strategy needs determination."
        )

    def query_deductive(self, query: Query) -> ResultSet:
        """Execute deductive query."""
        raise NotImplementedError("Rulelog backend not yet implemented")

    def query_abductive(self, query: Query) -> ResultSet:
        """Execute abductive query."""
        raise NotImplementedError("Rulelog backend not yet implemented")

    def query_defeasible(self, query: Query) -> ResultSet:
        """Execute defeasible query."""
        raise NotImplementedError("Rulelog backend not yet implemented")

    def get_derivation_trace(self, fact: str) -> DerivationTree:
        """Extract proof tree for fact."""
        raise NotImplementedError("Rulelog backend not yet implemented")

    def get_minimal_support(self, conclusion: str) -> Set[str]:
        """Compute minimal support set."""
        raise NotImplementedError("Rulelog backend not yet implemented")
