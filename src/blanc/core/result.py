"""
Result containers with provenance tracking.

Provides structured results from knowledge base queries with full derivation
information for research and debugging purposes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set


@dataclass
class DerivationTree:
    """
    A proof tree showing how a conclusion was derived.

    Attributes:
        conclusion: The derived conclusion
        premises: Premises used in this derivation step
        rule: Rule applied (if any)
        children: Sub-derivations for premises
        metadata: Additional provenance information
    """

    conclusion: str
    premises: List[str] = field(default_factory=list)
    rule: Optional[str] = None
    children: List["DerivationTree"] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def depth(self) -> int:
        """Calculate the depth of the derivation tree."""
        if not self.children:
            return 1
        return 1 + max(child.depth() for child in self.children)

    def leaves(self) -> Set[str]:
        """Get all leaf facts (facts without derivation)."""
        if not self.children:
            return {self.conclusion}
        result = set()
        for child in self.children:
            result.update(child.leaves())
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "conclusion": self.conclusion,
            "premises": self.premises,
            "rule": self.rule,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata,
        }

    def __str__(self) -> str:
        """String representation of derivation tree."""
        return self._format_tree(0)

    def _format_tree(self, indent: int) -> str:
        """Format tree with indentation."""
        lines = []
        prefix = "  " * indent

        if self.rule:
            lines.append(f"{prefix}{self.conclusion} (via {self.rule})")
        else:
            lines.append(f"{prefix}{self.conclusion}")

        for child in self.children:
            lines.append(child._format_tree(indent + 1))

        return "\n".join(lines)


@dataclass
class Result:
    """
    A single query result with provenance.

    Attributes:
        bindings: Variable bindings for this result
        derivation: Optional derivation tree showing how result was derived
        confidence: Optional confidence score for defeasible/abductive results
        metadata: Additional result metadata
    """

    bindings: Dict[str, str] = field(default_factory=dict)
    derivation: Optional[DerivationTree] = None
    confidence: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get(self, var: str) -> Optional[str]:
        """Get binding for a variable."""
        return self.bindings.get(var)

    def __getitem__(self, var: str) -> str:
        """Get binding for a variable (raises KeyError if not found)."""
        return self.bindings[var]

    def __contains__(self, var: str) -> bool:
        """Check if variable has a binding."""
        return var in self.bindings

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "bindings": self.bindings,
            "derivation": self.derivation.to_dict() if self.derivation else None,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class ResultSet:
    """
    A collection of query results.

    Attributes:
        results: List of individual results
        query: The query that produced these results
        backend: Backend used to execute query
        execution_time_ms: Time taken to execute query
        metadata: Additional metadata about the result set
    """

    results: List[Result] = field(default_factory=list)
    query: Optional[str] = None
    backend: Optional[str] = None
    execution_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        """Return number of results."""
        return len(self.results)

    def __iter__(self):
        """Iterate over results."""
        return iter(self.results)

    def __getitem__(self, index: int) -> Result:
        """Get result by index."""
        return self.results[index]

    def __bool__(self) -> bool:
        """Check if any results exist."""
        return len(self.results) > 0

    @property
    def is_empty(self) -> bool:
        """Check if result set is empty."""
        return len(self.results) == 0

    @property
    def first(self) -> Optional[Result]:
        """Get first result, or None if empty."""
        return self.results[0] if self.results else None

    def filter(self, predicate) -> "ResultSet":
        """Filter results by predicate function."""
        filtered_results = [r for r in self.results if predicate(r)]
        return ResultSet(
            results=filtered_results,
            query=self.query,
            backend=self.backend,
            execution_time_ms=self.execution_time_ms,
            metadata=self.metadata,
        )

    def map(self, func) -> List[Any]:
        """Map function over results."""
        return [func(r) for r in self.results]

    def get_bindings(self, var: str) -> List[str]:
        """Get all bindings for a specific variable."""
        return [r[var] for r in self.results if var in r]

    def to_list(self) -> List[Dict[str, Any]]:
        """Convert to list of dictionaries."""
        return [r.to_dict() for r in self.results]

    def __str__(self) -> str:
        """String representation of result set."""
        if self.is_empty:
            return "ResultSet(empty)"

        lines = [f"ResultSet({len(self.results)} results):"]
        for i, result in enumerate(self.results[:10]):  # Show first 10
            lines.append(f"  [{i}] {result.bindings}")

        if len(self.results) > 10:
            lines.append(f"  ... and {len(self.results) - 10} more")

        return "\n".join(lines)
