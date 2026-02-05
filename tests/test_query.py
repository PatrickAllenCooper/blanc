"""Tests for Query builder."""

import pytest

from blanc.core.knowledge_base import KnowledgeBase
from blanc.core.query import Query, QueryType


class TestQueryBuilder:
    """Test Query builder pattern."""

    def test_deductive_query_construction(self):
        """Test building a deductive query."""
        # Note: KnowledgeBase will fail without backend, so we test Query construction
        # We'll use a mock or skip execution for now
        kb = None  # Placeholder

        # Create query without executing
        query = Query(kb).select("p(X)").where("q(X)", "r(X)")

        assert query.query_type == QueryType.DEDUCTIVE
        assert query.goal == "p(X)"
        assert "q(X)" in query.conditions
        assert "r(X)" in query.conditions

    def test_abductive_query_construction(self):
        """Test building an abductive query."""
        kb = None

        query = (
            Query(kb)
            .abduce("infected(john, covid)")
            .given("symptom(john, fever)", "symptom(john, cough)")
            .minimize("hypothesis_count")
        )

        assert query.query_type == QueryType.ABDUCTIVE
        assert query.goal == "infected(john, covid)"
        assert "symptom(john, fever)" in query.conditions
        assert query.minimize_criterion == "hypothesis_count"

    def test_defeasible_query_construction(self):
        """Test building a defeasible query."""
        kb = None

        query = (
            Query(kb)
            .defeasibly_infer("flies(tweety)")
            .with_defeaters("wounded(tweety)")
            .assuming("bird(tweety)")
        )

        assert query.query_type == QueryType.DEFEASIBLE
        assert query.goal == "flies(tweety)"
        assert "wounded(tweety)" in query.defeasible_context.defeaters
        assert "bird(tweety)" in query.defeasible_context.assumptions

    def test_query_with_limit(self):
        """Test query with result limit."""
        kb = None

        query = Query(kb).select("p(X)").limit(10)

        assert query.result_limit == 10

    def test_query_with_metadata(self):
        """Test query with metadata."""
        kb = None

        query = Query(kb).select("p(X)").with_metadata(source="test", version=1)

        assert query.metadata["source"] == "test"
        assert query.metadata["version"] == 1

    def test_query_requires_type(self):
        """Test that query execution requires type to be set."""
        kb = None
        query = Query(kb)

        with pytest.raises(ValueError, match="Query type not set"):
            # This would try to execute, but we expect error before that
            try:
                query.execute()
            except AttributeError:
                # If kb is None, we might get AttributeError first
                # That's fine for this test, but let's check the validation works
                pass

    def test_query_string_representation(self):
        """Test query string representation."""
        kb = None
        query = Query(kb).select("p(X)").where("q(X)")

        s = str(query)
        assert "deductive" in s
        assert "p(X)" in s


class TestQueryChaining:
    """Test query builder chaining."""

    def test_chaining_returns_query(self):
        """Test that all builder methods return Query for chaining."""
        kb = None

        result = (
            Query(kb)
            .select("p(X)")
            .where("q(X)")
            .limit(5)
            .with_metadata(test=True)
        )

        assert isinstance(result, Query)

    def test_multiple_conditions(self):
        """Test adding multiple conditions."""
        kb = None

        query = Query(kb).select("p(X)").where("q(X)", "r(X)", "s(X)")

        assert len(query.conditions) == 3

    def test_multiple_defeaters(self):
        """Test adding multiple defeaters."""
        kb = None

        query = (
            Query(kb)
            .defeasibly_infer("p(a)")
            .with_defeaters("d1(a)", "d2(a)", "d3(a)")
        )

        assert len(query.defeasible_context.defeaters) == 3

    def test_hypothesis_space_restriction(self):
        """Test restricting hypothesis space for abduction."""
        kb = None

        query = (
            Query(kb)
            .abduce("p(a)")
            .with_hypotheses("h1(a)", "h2(a)", "h3(a)")
        )

        assert len(query.hypotheses) == 3
        assert "h1(a)" in query.hypotheses
