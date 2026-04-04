"""Coverage tests for reasoning/defeasible.py uncovered paths.

Targets: complement definite provability, attack neutralization with
inapplicable bodies and superior defenders, _match variable conflicts
and constant mismatches, substitution edge cases, clear_cache.
"""

import pytest

from blanc.core.theory import Rule, RuleType, Theory
from blanc.reasoning.defeasible import DefeasibleEngine, defeasible_provable


def _make_theory(facts=(), rules=(), superiority=None):
    t = Theory()
    for f in facts:
        t.add_fact(f)
    for r in rules:
        t.add_rule(r)
    if superiority:
        for sup, inf in superiority:
            t.add_superiority(sup, inf)
    return t


class TestComplementDefiniteProvability:
    """Line 111: complement is strictly provable -> return False."""

    def test_complement_strictly_provable_blocks(self):
        theory = _make_theory(
            facts=["~flies(tweety)"],
            rules=[
                Rule(head="flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r1"),
            ],
        )
        theory.add_fact("bird(tweety)")
        assert not defeasible_provable(theory, "flies(tweety)")


class TestAttackNeutralization:
    """Lines 268-288: inapplicable attacks and superior defenders."""

    def test_attack_with_inapplicable_body(self):
        theory = _make_theory(
            facts=["bird(tweety)"],
            rules=[
                Rule(head="flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r1"),
                Rule(head="~flies(X)", body=("penguin(X)",),
                     rule_type=RuleType.DEFEATER, label="d1"),
            ],
        )
        assert defeasible_provable(theory, "flies(tweety)")

    def test_attack_neutralized_by_superior_defender(self):
        theory = _make_theory(
            facts=["bird(tweety)", "healthy(tweety)"],
            rules=[
                Rule(head="flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r1"),
                Rule(head="flies(X)", body=("healthy(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r2"),
                Rule(head="~flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="a1"),
            ],
            superiority=[("r2", "a1")],
        )
        assert defeasible_provable(theory, "flies(tweety)")

    def test_attack_not_neutralized(self):
        theory = _make_theory(
            facts=["bird(tweety)", "penguin(tweety)"],
            rules=[
                Rule(head="flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r1"),
                Rule(head="~flies(X)", body=("penguin(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="a1"),
            ],
        )
        assert not defeasible_provable(theory, "flies(tweety)")

    def test_defeater_blocks_without_superiority(self):
        theory = _make_theory(
            facts=["bird(tweety)", "penguin(tweety)"],
            rules=[
                Rule(head="flies(X)", body=("bird(X)",),
                     rule_type=RuleType.DEFEASIBLE, label="r1"),
                Rule(head="~flies(X)", body=("penguin(X)",),
                     rule_type=RuleType.DEFEATER, label="d1"),
            ],
        )
        assert not defeasible_provable(theory, "flies(tweety)")


class TestMatchConflicts:
    """Lines 341, 350-351, 356-357: arity, variable conflicts, constant mismatch."""

    def test_arity_mismatch_returns_none(self):
        engine = DefeasibleEngine(Theory())
        assert engine._match("p(X, Y)", "p(a)") is None

    def test_variable_conflict_returns_none(self):
        engine = DefeasibleEngine(Theory())
        assert engine._match("p(X, X)", "p(a, b)") is None

    def test_variable_consistent_binding(self):
        engine = DefeasibleEngine(Theory())
        result = engine._match("p(X, X)", "p(a, a)")
        assert result == {"X": "a"}

    def test_constant_mismatch_returns_none(self):
        engine = DefeasibleEngine(Theory())
        assert engine._match("p(a)", "p(b)") is None

    def test_constant_match_succeeds(self):
        engine = DefeasibleEngine(Theory())
        assert engine._match("p(a)", "p(a)") == {}

    def test_predicate_mismatch_returns_none(self):
        engine = DefeasibleEngine(Theory())
        assert engine._match("p(X)", "q(a)") is None


class TestParseAtom:
    """Lines 399-409: _parse_atom fallback paths."""

    def test_no_parens(self):
        engine = DefeasibleEngine(Theory())
        pred, args = engine._parse_atom("simple")
        assert pred == "simple"
        assert args == []

    def test_negated_atom(self):
        engine = DefeasibleEngine(Theory())
        pred, args = engine._parse_atom("~flies(tweety)")
        assert pred == "~flies"
        assert args == ["tweety"]

    def test_malformed_atom_fallback(self):
        engine = DefeasibleEngine(Theory())
        pred, args = engine._parse_atom("123bad")
        assert pred == "123bad"
        assert args == []


class TestSubstitutionEdgeCases:
    """Lines 448-456, 479-490."""

    def test_no_variables_returns_empty_substitution(self):
        engine = DefeasibleEngine(Theory())
        rule = Rule(head="p(a)", body=("q(b)",), rule_type=RuleType.STRICT)
        subs = engine._generate_substitutions(rule, {"a", "b"})
        assert subs == [{}]

    def test_empty_constants_returns_empty_substitution(self):
        engine = DefeasibleEngine(Theory())
        rule = Rule(head="p(X)", body=("q(X)",), rule_type=RuleType.DEFEASIBLE)
        subs = engine._generate_substitutions(rule, set())
        assert subs == [{}]

    def test_ground_rule_with_variables(self):
        theory = _make_theory(facts=["a(c1)", "a(c2)"])
        engine = DefeasibleEngine(theory)
        rule = Rule(head="p(X)", body=("a(X)",), rule_type=RuleType.DEFEASIBLE)
        constants = engine._extract_constants()
        grounds = engine._ground_rule(rule, constants)
        assert "p(c1)" in grounds
        assert "p(c2)" in grounds

    def test_ground_rule_fact(self):
        engine = DefeasibleEngine(Theory())
        rule = Rule(head="p(a)", body=(), rule_type=RuleType.FACT)
        assert engine._ground_rule(rule, set()) == ["p(a)"]

    def test_clear_cache(self):
        theory = _make_theory(facts=["bird(tweety)"], rules=[
            Rule(head="flies(X)", body=("bird(X)",),
                 rule_type=RuleType.DEFEASIBLE, label="r1"),
        ])
        engine = DefeasibleEngine(theory)
        assert engine.is_defeasibly_provable("flies(tweety)")
        engine.clear_cache()
        assert engine.is_defeasibly_provable("flies(tweety)")
