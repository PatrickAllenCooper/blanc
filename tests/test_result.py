"""Tests for Result containers."""

import pytest

from blanc.core.result import DerivationTree, Result, ResultSet


class TestDerivationTree:
    """Test DerivationTree class."""

    def test_create_simple_tree(self):
        """Test creating a simple derivation tree."""
        tree = DerivationTree(
            conclusion="mortal(socrates)",
            premises=["human(socrates)"],
            rule="human(X) -> mortal(X)",
        )

        assert tree.conclusion == "mortal(socrates)"
        assert tree.premises == ["human(socrates)"]
        assert tree.rule == "human(X) -> mortal(X)"

    def test_tree_depth(self):
        """Test calculating tree depth."""
        # Simple fact (depth 1)
        leaf = DerivationTree(conclusion="human(socrates)")
        assert leaf.depth() == 1

        # One-level derivation (depth 2)
        tree = DerivationTree(
            conclusion="mortal(socrates)",
            children=[leaf],
        )
        assert tree.depth() == 2

    def test_tree_leaves(self):
        """Test extracting leaf facts."""
        leaf1 = DerivationTree(conclusion="human(socrates)")
        leaf2 = DerivationTree(conclusion="philosopher(socrates)")

        tree = DerivationTree(
            conclusion="mortal_philosopher(socrates)",
            children=[leaf1, leaf2],
        )

        leaves = tree.leaves()
        assert "human(socrates)" in leaves
        assert "philosopher(socrates)" in leaves

    def test_tree_to_dict(self):
        """Test converting tree to dictionary."""
        tree = DerivationTree(
            conclusion="p(a)",
            premises=["q(a)"],
            rule="r1",
            metadata={"test": True},
        )

        d = tree.to_dict()
        assert d["conclusion"] == "p(a)"
        assert d["premises"] == ["q(a)"]
        assert d["rule"] == "r1"
        assert d["metadata"]["test"] is True


class TestResult:
    """Test Result class."""

    def test_create_result(self):
        """Test creating a result."""
        result = Result(bindings={"X": "socrates", "Y": "mortal"})

        assert result["X"] == "socrates"
        assert result["Y"] == "mortal"
        assert result.get("X") == "socrates"
        assert result.get("Z") is None

    def test_result_contains(self):
        """Test checking if variable has binding."""
        result = Result(bindings={"X": "value"})

        assert "X" in result
        assert "Y" not in result

    def test_result_with_derivation(self):
        """Test result with derivation tree."""
        tree = DerivationTree(conclusion="p(a)")
        result = Result(bindings={"X": "a"}, derivation=tree)

        assert result.derivation is not None
        assert result.derivation.conclusion == "p(a)"

    def test_result_with_confidence(self):
        """Test result with confidence score."""
        result = Result(bindings={}, confidence=0.85)

        assert result.confidence == 0.85

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        result = Result(
            bindings={"X": "a"},
            confidence=0.9,
            metadata={"source": "test"},
        )

        d = result.to_dict()
        assert d["bindings"]["X"] == "a"
        assert d["confidence"] == 0.9
        assert d["metadata"]["source"] == "test"


class TestResultSet:
    """Test ResultSet class."""

    def test_create_empty_result_set(self):
        """Test creating an empty result set."""
        rs = ResultSet()

        assert len(rs) == 0
        assert rs.is_empty
        assert not rs
        assert rs.first is None

    def test_create_result_set_with_results(self):
        """Test creating result set with results."""
        results = [
            Result(bindings={"X": "a"}),
            Result(bindings={"X": "b"}),
            Result(bindings={"X": "c"}),
        ]

        rs = ResultSet(results=results)

        assert len(rs) == 3
        assert not rs.is_empty
        assert rs
        assert rs.first is not None
        assert rs.first["X"] == "a"

    def test_result_set_iteration(self):
        """Test iterating over result set."""
        results = [
            Result(bindings={"X": str(i)})
            for i in range(5)
        ]

        rs = ResultSet(results=results)

        count = 0
        for result in rs:
            assert "X" in result
            count += 1

        assert count == 5

    def test_result_set_indexing(self):
        """Test indexing result set."""
        results = [
            Result(bindings={"X": "a"}),
            Result(bindings={"X": "b"}),
        ]

        rs = ResultSet(results=results)

        assert rs[0]["X"] == "a"
        assert rs[1]["X"] == "b"

    def test_result_set_filter(self):
        """Test filtering result set."""
        results = [
            Result(bindings={"X": "a", "Y": "1"}),
            Result(bindings={"X": "b", "Y": "2"}),
            Result(bindings={"X": "c", "Y": "1"}),
        ]

        rs = ResultSet(results=results)

        filtered = rs.filter(lambda r: r["Y"] == "1")

        assert len(filtered) == 2
        assert filtered[0]["X"] == "a"
        assert filtered[1]["X"] == "c"

    def test_result_set_map(self):
        """Test mapping over result set."""
        results = [
            Result(bindings={"X": "a"}),
            Result(bindings={"X": "b"}),
        ]

        rs = ResultSet(results=results)

        values = rs.map(lambda r: r["X"])

        assert values == ["a", "b"]

    def test_get_bindings(self):
        """Test getting all bindings for a variable."""
        results = [
            Result(bindings={"X": "a", "Y": "1"}),
            Result(bindings={"X": "b", "Y": "2"}),
            Result(bindings={"X": "c", "Y": "3"}),
        ]

        rs = ResultSet(results=results)

        x_values = rs.get_bindings("X")
        assert x_values == ["a", "b", "c"]

        y_values = rs.get_bindings("Y")
        assert y_values == ["1", "2", "3"]

    def test_result_set_to_list(self):
        """Test converting result set to list."""
        results = [
            Result(bindings={"X": "a"}),
            Result(bindings={"X": "b"}),
        ]

        rs = ResultSet(results=results)

        lst = rs.to_list()

        assert len(lst) == 2
        assert lst[0]["bindings"]["X"] == "a"
        assert lst[1]["bindings"]["X"] == "b"

    def test_result_set_metadata(self):
        """Test result set metadata."""
        rs = ResultSet(
            query="p(X)",
            backend="prolog",
            execution_time_ms=42.5,
            metadata={"cache_hit": True},
        )

        assert rs.query == "p(X)"
        assert rs.backend == "prolog"
        assert rs.execution_time_ms == 42.5
        assert rs.metadata["cache_hit"] is True
