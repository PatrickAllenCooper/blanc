"""
Defeasible logic backend.

Adapter for defeasible logic implementations (DePYsible, etc.).
"""

from pathlib import Path
from typing import Set, Union

from blanc.backends.base import KnowledgeBaseBackend
from blanc.core.query import Query
from blanc.core.result import DerivationTree, ResultSet
from blanc.core.theory import Theory


class DefeasibleBackend(KnowledgeBaseBackend):
    """
    Defeasible logic backend.

    Note: Placeholder implementation for Phase 2.
    """

    def __init__(self, **kwargs):
        """Initialize defeasible logic backend."""
        self._theory: Union[Theory, None] = None

    def load_theory(self, source: Union[str, Path, Theory]) -> None:
        """Load knowledge base from source."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")

    def query_deductive(self, query: Query) -> ResultSet:
        """Execute deductive query."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")

    def query_abductive(self, query: Query) -> ResultSet:
        """Execute abductive query."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")

    def query_defeasible(self, query: Query) -> ResultSet:
        """Execute defeasible query."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")

    def get_derivation_trace(self, fact: str) -> DerivationTree:
        """Extract proof tree for fact."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")

    def get_minimal_support(self, conclusion: str) -> Set[str]:
        """Compute minimal support set."""
        raise NotImplementedError("Defeasible backend not yet implemented (Phase 2)")
