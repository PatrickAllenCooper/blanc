"""
Tests for src/blanc/core/result.py — covering the 80% gap.

Missing lines: 58 (__str__ on DerivationTree), 62-73 (_format_tree),
185-195 (__str__ on ResultSet).
"""

from blanc.core.result import DerivationTree, Result, ResultSet


class TestDerivationTreeStr:
    def test_str_no_children_no_rule(self):
        node = DerivationTree(conclusion="flies(tweety)", premises=[], rule=None)
        result = str(node)
        assert "flies(tweety)" in result
        assert "via" not in result

    def test_str_with_rule(self):
        node = DerivationTree(conclusion="flies(tweety)", premises=[], rule="r1")
        result = str(node)
        assert "flies(tweety)" in result
        assert "r1" in result

    def test_str_with_children(self):
        child = DerivationTree(conclusion="bird(tweety)", premises=[], rule=None)
        parent = DerivationTree(
            conclusion="flies(tweety)", premises=[], rule="r1", children=[child]
        )
        result = str(parent)
        assert "flies(tweety)" in result
        assert "bird(tweety)" in result
        # child indented more
        lines = result.split("\n")
        assert len(lines) >= 2
        assert lines[1].startswith("  ")

    def test_format_tree_indentation_depth(self):
        grandchild = DerivationTree(conclusion="g", premises=[])
        child = DerivationTree(conclusion="c", premises=[], children=[grandchild])
        parent = DerivationTree(conclusion="p", premises=[], children=[child])
        result = str(parent)
        lines = result.split("\n")
        assert len(lines) == 3
        assert lines[0].startswith("p")
        assert lines[1].startswith("  c")
        assert lines[2].startswith("    g")


class TestResultSetStr:
    def test_empty_result_set_str(self):
        rs = ResultSet(results=[])
        result = str(rs)
        assert "empty" in result.lower()

    def test_non_empty_result_set_str(self):
        r1 = Result(bindings={"X": "tweety"})
        r2 = Result(bindings={"X": "opus"})
        rs = ResultSet(results=[r1, r2])
        result = str(rs)
        assert "2 results" in result
        assert "tweety" in result

    def test_more_than_10_results_truncated(self):
        results = [Result(bindings={"X": str(i)}) for i in range(15)]
        rs = ResultSet(results=results)
        result = str(rs)
        assert "5 more" in result

    def test_exactly_10_results_no_truncation(self):
        results = [Result(bindings={"X": str(i)}) for i in range(10)]
        rs = ResultSet(results=results)
        result = str(rs)
        assert "more" not in result
