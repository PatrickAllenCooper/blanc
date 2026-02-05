"""
Main KnowledgeBase interface with backend abstraction.

Provides the primary user-facing API for loading and querying knowledge bases
across different backend systems.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Optional, Union

from blanc.core.result import ResultSet
from blanc.core.theory import Theory

if TYPE_CHECKING:
    from blanc.backends.base import KnowledgeBaseBackend
    from blanc.core.query import Query


class KnowledgeBase:
    """
    Main interface for knowledge base operations.

    Abstracts over different backend implementations (Prolog, ASP, etc.)
    and provides unified query interface.
    """

    def __init__(
        self,
        backend: str = "prolog",
        source: Optional[Union[str, Path, Theory]] = None,
        **backend_kwargs,
    ):
        """
        Initialize knowledge base with specified backend.

        Args:
            backend: Backend type ('prolog', 'asp', 'defeasible', 'rulelog')
            source: Source of knowledge base (file path, Theory object, or None)
            **backend_kwargs: Additional backend-specific configuration

        Raises:
            ValueError: If backend is not recognized
        """
        self._backend_name = backend
        self._backend = self._create_backend(backend, **backend_kwargs)

        if source is not None:
            self.load(source)

    def _create_backend(self, backend: str, **kwargs) -> "KnowledgeBaseBackend":
        """
        Create backend instance.

        Args:
            backend: Backend type
            **kwargs: Backend-specific configuration

        Returns:
            Backend instance

        Raises:
            ValueError: If backend is not recognized or not available
        """
        backend = backend.lower()

        if backend == "prolog":
            try:
                from blanc.backends.prolog import PrologBackend

                return PrologBackend(**kwargs)
            except ImportError as e:
                raise ValueError(
                    f"Prolog backend not available (missing dependencies): {e}"
                ) from e

        elif backend == "asp":
            try:
                from blanc.backends.asp import ASPBackend

                return ASPBackend(**kwargs)
            except ImportError as e:
                raise ValueError(
                    f"ASP backend not available (missing dependencies): {e}"
                ) from e

        elif backend == "defeasible":
            try:
                from blanc.backends.defeasible import DefeasibleBackend

                return DefeasibleBackend(**kwargs)
            except ImportError as e:
                raise ValueError(
                    f"Defeasible backend not available (missing dependencies): {e}"
                ) from e

        elif backend == "rulelog":
            try:
                from blanc.backends.rulelog import RulelogBackend

                return RulelogBackend(**kwargs)
            except ImportError as e:
                raise ValueError(
                    f"Rulelog backend not available (missing dependencies): {e}"
                ) from e

        else:
            raise ValueError(
                f"Unknown backend: {backend}. "
                f"Available: prolog, asp, defeasible, rulelog"
            )

    def load(self, source: Union[str, Path, Theory]) -> None:
        """
        Load knowledge base from source.

        Args:
            source: File path (str/Path) or Theory object

        Raises:
            FileNotFoundError: If file path doesn't exist
            ValueError: If source format is invalid
        """
        if isinstance(source, (str, Path)):
            source_path = Path(source)
            if not source_path.exists():
                raise FileNotFoundError(f"Knowledge base file not found: {source}")

        self._backend.load_theory(source)

    def query(self, goal: str) -> "ResultSet":
        """
        Execute a simple deductive query.

        Convenience method for basic queries. For complex queries,
        use Query builder.

        Args:
            goal: Goal to query (e.g., 'p(X)')

        Returns:
            Result set

        Example:
            >>> kb = KnowledgeBase(backend='prolog', source='medical.pl')
            >>> results = kb.query('diagnosis(Patient, Disease)')
        """
        from blanc.core.query import Query

        return Query(self).select(goal).execute()

    def _execute_deductive(self, query: "Query") -> ResultSet:
        """Execute deductive query via backend."""
        return self._backend.query_deductive(query)

    def _execute_abductive(self, query: "Query") -> ResultSet:
        """Execute abductive query via backend."""
        return self._backend.query_abductive(query)

    def _execute_defeasible(self, query: "Query") -> ResultSet:
        """Execute defeasible query via backend."""
        return self._backend.query_defeasible(query)

    def get_derivation(self, fact: str):
        """
        Get derivation tree for a fact.

        Args:
            fact: Fact to get derivation for

        Returns:
            DerivationTree showing how fact was derived

        Raises:
            ValueError: If fact is not derivable
        """
        return self._backend.get_derivation_trace(fact)

    def get_minimal_support(self, conclusion: str) -> set[str]:
        """
        Compute minimal support set for conclusion.

        Args:
            conclusion: Conclusion to find support for

        Returns:
            Set of minimal facts/rules needed to derive conclusion

        Example:
            >>> kb.get_minimal_support('flies(tweety)')
            {'bird(tweety)', 'bird(X) => flies(X)'}
        """
        return self._backend.get_minimal_support(conclusion)

    @property
    def backend_name(self) -> str:
        """Get name of current backend."""
        return self._backend_name

    @property
    def backend(self) -> "KnowledgeBaseBackend":
        """Get backend instance (for advanced usage)."""
        return self._backend

    def __repr__(self) -> str:
        """String representation."""
        return f"KnowledgeBase(backend='{self._backend_name}')"
