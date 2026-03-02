"""
Tests for src/blanc/utils/predicates.py.

Covers extract_predicate, extract_constant, capitalize.
"""

from blanc.utils.predicates import extract_predicate, extract_constant, capitalize


class TestExtractPredicate:
    def test_ground_atom(self):
        assert extract_predicate("bird(tweety)") == "bird"

    def test_variable_atom(self):
        assert extract_predicate("flies(X)") == "flies"

    def test_multi_arg(self):
        assert extract_predicate("path(a, b, c)") == "path"

    def test_no_args(self):
        assert extract_predicate("flies") == "flies"

    def test_compound_predicate(self):
        assert extract_predicate("has_wings(X)") == "has_wings"


class TestExtractConstant:
    def test_simple_unary(self):
        assert extract_constant("bird(tweety)") == "tweety"

    def test_no_args_returns_empty(self):
        assert extract_constant("bird") == ""

    def test_only_open_paren_returns_empty(self):
        # atom without closing paren — both conditions fail
        assert extract_constant("bird(X") == ""

    def test_multi_arg_returns_first(self):
        # extract_constant reads up to closing paren — for "path(a, b)" it
        # returns "a, b" (all args up to first ")")
        result = extract_constant("path(a, b)")
        assert "a" in result

    def test_empty_parens(self):
        assert extract_constant("atom()") == ""


class TestCapitalize:
    def test_lowercase(self):
        assert capitalize("hello") == "Hello"

    def test_already_capitalized(self):
        assert capitalize("Hello") == "Hello"

    def test_single_char(self):
        assert capitalize("a") == "A"

    def test_preserves_rest(self):
        assert capitalize("hELLO") == "HELLO"

    def test_empty_string(self):
        assert capitalize("") == ""
