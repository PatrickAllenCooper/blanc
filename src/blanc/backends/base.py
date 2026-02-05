"""
Abstract backend interface for knowledge base systems.

Defines the contract that all backend adapters must implement.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Set, Union

from blanc.core.query import Query
from blanc.core.result import DerivationTree, ResultSet
from blanc.core.theory import Theory


class KnowledgeBaseBackend(ABC):
    """
    Abstract base class for knowledge base backend implementations.

    All backend adapters (Prolog, ASP, defeasible logic, etc.) must
    implement this interface to ensure consistent behavior.
    """

    @abstractmethod
    def load_theory(self, source: Union[str, Path, Theory]) -> None:
        """
        Load knowledge base from source.

        Args:
            source: File path (str/Path) or Theory object

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If theory format is invalid
        """
        pass

    @abstractmethod
    def query_deductive(self, query: Query) -> ResultSet:
        """
        Execute deductive query.

        Standard logical query: find all bindings that satisfy goal.

        Args:
            query: Query object with goal and conditions

        Returns:
            Result set with variable bindings

        Example:
            Query: select('p(X)').where('q(X)')
            Returns: All X where both p(X) and q(X) hold
        """
        pass

    @abstractmethod
    def query_abductive(self, query: Query) -> ResultSet:
        """
        Execute abductive query.

        Find hypotheses that explain observation.

        Args:
            query: Query object with observation and evidence

        Returns:
            Result set with candidate hypotheses

        Example:
            Query: abduce('infected(john, covid)').given('symptom(john, fever)')
            Returns: Minimal hypotheses that explain observation
        """
        pass

    @abstractmethod
    def query_defeasible(self, query: Query) -> ResultSet:
        """
        Execute defeasible reasoning query.

        Determine what can be defeasibly inferred given defeaters.

        Args:
            query: Query object with goal and defeasible context

        Returns:
            Result set indicating what is defeasibly derivable

        Example:
            Query: defeasibly_infer('flies(tweety)').with_defeaters('wounded(tweety)')
            Returns: Whether flies(tweety) is defeasibly derivable
        """
        pass

    @abstractmethod
    def get_derivation_trace(self, fact: str) -> DerivationTree:
        """
        Extract proof/derivation tree for a fact.

        Args:
            fact: Fact to get derivation for

        Returns:
            Derivation tree showing proof structure

        Raises:
            ValueError: If fact is not derivable
        """
        pass

    @abstractmethod
    def get_minimal_support(self, conclusion: str) -> Set[str]:
        """
        Compute minimal support set for conclusion.

        Find the minimal set of facts/rules needed to derive conclusion.

        Args:
            conclusion: Conclusion to find support for

        Returns:
            Set of minimal supporting facts/rules

        Raises:
            ValueError: If conclusion is not derivable
        """
        pass

    def close(self) -> None:
        """
        Clean up backend resources.

        Optional method for backends that need cleanup.
        Default implementation does nothing.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
