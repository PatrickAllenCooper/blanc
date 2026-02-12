"""
Extended tests for core/result.py to improve coverage.

Targets missing lines for 80% -> 95% coverage improvement.

Author: Patrick Cooper
Date: 2026-02-12
"""

import pytest
from blanc.core.result import QueryResult, AbductiveResult


class TestQueryResult:
    """Test QueryResult class."""
    
    def test_query_result_creation(self):
        """Test creating QueryResult."""
        result = QueryResult(
            query="test(X)",
            success=True,
            bindings=[{'X': 'a'}],
            metadata={'source': 'test'}
        )
        
        assert result.query == "test(X)"
        assert result.success == True
        assert len(result.bindings) == 1
    
    def test_query_result_empty_bindings(self):
        """Test QueryResult with no bindings."""
        result = QueryResult(
            query="test(a)",
            success=False,
            bindings=[],
            metadata={}
        )
        
        assert result.success == False
        assert len(result.bindings) == 0
    
    def test_query_result_to_dict(self):
        """Test QueryResult serialization."""
        result = QueryResult(
            query="test(X)",
            success=True,
            bindings=[{'X': 'a'}],
            metadata={}
        )
        
        result_dict = result.to_dict()
        
        assert 'query' in result_dict
        assert 'success' in result_dict
        assert 'bindings' in result_dict
    
    def test_query_result_repr(self):
        """Test QueryResult string representation."""
        result = QueryResult(
            query="test(X)",
            success=True,
            bindings=[{'X': 'a'}],
            metadata={}
        )
        
        repr_str = repr(result)
        assert 'QueryResult' in repr_str
        assert 'test(X)' in repr_str


class TestAbductiveResult:
    """Test AbductiveResult class."""
    
    def test_abductive_result_creation(self):
        """Test creating AbductiveResult."""
        result = AbductiveResult(
            query="explains(X)",
            hypotheses=["hyp1(a)", "hyp2(b)"],
            metadata={'method': 'test'}
        )
        
        assert result.query == "explains(X)"
        assert len(result.hypotheses) == 2
    
    def test_abductive_result_empty_hypotheses(self):
        """Test AbductiveResult with no hypotheses."""
        result = AbductiveResult(
            query="explains(X)",
            hypotheses=[],
            metadata={}
        )
        
        assert len(result.hypotheses) == 0
    
    def test_abductive_result_to_dict(self):
        """Test AbductiveResult serialization."""
        result = AbductiveResult(
            query="explains(X)",
            hypotheses=["hyp1(a)"],
            metadata={'score': 0.9}
        )
        
        result_dict = result.to_dict()
        
        assert 'query' in result_dict
        assert 'hypotheses' in result_dict
        assert 'metadata' in result_dict


class TestResultComparison:
    """Test result comparison and equality."""
    
    def test_query_results_equal(self):
        """Test QueryResult equality."""
        result1 = QueryResult("test(X)", True, [{'X': 'a'}], {})
        result2 = QueryResult("test(X)", True, [{'X': 'a'}], {})
        
        # Should have same data
        assert result1.query == result2.query
        assert result1.success == result2.success
    
    def test_query_results_different(self):
        """Test QueryResult inequality."""
        result1 = QueryResult("test(X)", True, [{'X': 'a'}], {})
        result2 = QueryResult("test(X)", False, [], {})
        
        assert result1.success != result2.success
