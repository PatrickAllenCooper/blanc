"""
Query abstraction and builder pattern.

Provides a fluent interface for constructing queries across different
reasoning modes (deductive, abductive, defeasible).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from blanc.core.knowledge_base import KnowledgeBase
    from blanc.core.result import ResultSet


class QueryType(Enum):
    """Type of logical query."""

    DEDUCTIVE = "deductive"  # Standard logical query
    ABDUCTIVE = "abductive"  # Generate hypotheses
    DEFEASIBLE = "defeasible"  # Defeasible inference


@dataclass
class DefeasibleContext:
    """Context for defeasible reasoning queries."""

    defeaters: Set[str] = field(default_factory=set)
    assumptions: Set[str] = field(default_factory=set)
    excluded_rules: Set[str] = field(default_factory=set)


class Query:
    """
    Query builder for knowledge base queries.

    Provides fluent interface for constructing queries:
        Query(kb).select('p(X)').where('q(X)', 'r(X)').execute()
        Query(kb).abduce('p(a)').given('q(a)').minimize('hypothesis_count').execute()
        Query(kb).defeasibly_infer('p(a)').with_defeaters('d(a)').execute()
    """

    def __init__(self, kb: "KnowledgeBase"):
        """
        Initialize query builder.

        Args:
            kb: Knowledge base to query
        """
        self._kb = kb
        self._query_type: Optional[QueryType] = None
        self._goal: Optional[str] = None
        self._conditions: List[str] = []
        self._defeaters: Set[str] = set()
        self._assumptions: Set[str] = set()
        self._hypotheses: Set[str] = set()
        self._minimize: Optional[str] = None
        self._limit: Optional[int] = None
        self._metadata: Dict[str, Any] = {}

    def select(self, goal: str) -> "Query":
        """
        Start a deductive query.

        Args:
            goal: Goal to query (e.g., 'p(X, Y)')

        Returns:
            Query builder for chaining
        """
        self._query_type = QueryType.DEDUCTIVE
        self._goal = goal
        return self

    def where(self, *conditions: str) -> "Query":
        """
        Add conditions to deductive query.

        Args:
            conditions: Additional conditions/constraints

        Returns:
            Query builder for chaining
        """
        self._conditions.extend(conditions)
        return self

    def abduce(self, observation: str) -> "Query":
        """
        Start an abductive query.

        Args:
            observation: Observed fact to explain

        Returns:
            Query builder for chaining
        """
        self._query_type = QueryType.ABDUCTIVE
        self._goal = observation
        return self

    def given(self, *evidence: str) -> "Query":
        """
        Add evidence for abductive query.

        Args:
            evidence: Known facts as evidence

        Returns:
            Query builder for chaining
        """
        self._conditions.extend(evidence)
        return self

    def with_hypotheses(self, *hypotheses: str) -> "Query":
        """
        Restrict hypothesis space for abductive query.

        Args:
            hypotheses: Candidate hypotheses to consider

        Returns:
            Query builder for chaining
        """
        self._hypotheses.update(hypotheses)
        return self

    def minimize(self, criterion: str) -> "Query":
        """
        Set minimization criterion for abductive query.

        Args:
            criterion: What to minimize (e.g., 'hypothesis_count', 'complexity')

        Returns:
            Query builder for chaining
        """
        self._minimize = criterion
        return self

    def defeasibly_infer(self, goal: str) -> "Query":
        """
        Start a defeasible reasoning query.

        Args:
            goal: Goal to defeasibly infer

        Returns:
            Query builder for chaining
        """
        self._query_type = QueryType.DEFEASIBLE
        self._goal = goal
        return self

    def with_defeaters(self, *defeaters: str) -> "Query":
        """
        Add defeaters for defeasible reasoning.

        Args:
            defeaters: Defeater facts

        Returns:
            Query builder for chaining
        """
        self._defeaters.update(defeaters)
        return self

    def assuming(self, *assumptions: str) -> "Query":
        """
        Add assumptions for defeasible reasoning.

        Args:
            assumptions: Assumed facts

        Returns:
            Query builder for chaining
        """
        self._assumptions.update(assumptions)
        return self

    def limit(self, n: int) -> "Query":
        """
        Limit number of results.

        Args:
            n: Maximum number of results

        Returns:
            Query builder for chaining
        """
        self._limit = n
        return self

    def with_metadata(self, **kwargs: Any) -> "Query":
        """
        Add metadata to query.

        Args:
            kwargs: Metadata key-value pairs

        Returns:
            Query builder for chaining
        """
        self._metadata.update(kwargs)
        return self

    def execute(self) -> "ResultSet":
        """
        Execute the query.

        Returns:
            Result set containing query results

        Raises:
            ValueError: If query is not properly configured
        """
        if self._query_type is None:
            raise ValueError("Query type not set (use select/abduce/defeasibly_infer)")
        if self._goal is None:
            raise ValueError("Query goal not set")

        if self._query_type == QueryType.DEDUCTIVE:
            return self._kb._execute_deductive(self)
        elif self._query_type == QueryType.ABDUCTIVE:
            return self._kb._execute_abductive(self)
        elif self._query_type == QueryType.DEFEASIBLE:
            return self._kb._execute_defeasible(self)
        else:
            raise ValueError(f"Unknown query type: {self._query_type}")

    @property
    def query_type(self) -> Optional[QueryType]:
        """Get query type."""
        return self._query_type

    @property
    def goal(self) -> Optional[str]:
        """Get query goal."""
        return self._goal

    @property
    def conditions(self) -> List[str]:
        """Get query conditions."""
        return self._conditions.copy()

    @property
    def defeasible_context(self) -> DefeasibleContext:
        """Get defeasible reasoning context."""
        return DefeasibleContext(
            defeaters=self._defeaters.copy(),
            assumptions=self._assumptions.copy(),
        )

    @property
    def hypotheses(self) -> Set[str]:
        """Get hypothesis space for abductive query."""
        return self._hypotheses.copy()

    @property
    def minimize_criterion(self) -> Optional[str]:
        """Get minimization criterion."""
        return self._minimize

    @property
    def result_limit(self) -> Optional[int]:
        """Get result limit."""
        return self._limit

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get query metadata."""
        return self._metadata.copy()

    def __str__(self) -> str:
        """String representation of query."""
        parts = [f"Query({self._query_type.value if self._query_type else 'unset'})"]
        if self._goal:
            parts.append(f"goal={self._goal}")
        if self._conditions:
            parts.append(f"conditions={self._conditions}")
        if self._defeaters:
            parts.append(f"defeaters={self._defeaters}")
        if self._hypotheses:
            parts.append(f"hypotheses={self._hypotheses}")
        return " ".join(parts)
