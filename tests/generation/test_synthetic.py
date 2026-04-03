"""Tests for synthetic defeasible theory generation."""

import pytest

from blanc.core.theory import Rule, RuleType, Theory
from blanc.generation.synthetic import (
    SyntheticTheoryParams,
    generate_nonsense_word,
    generate_synthetic_theory,
    generate_vocabulary,
)


class TestGenerateNonsenseWord:
    def test_returns_string(self):
        import random
        rng = random.Random(0)
        word = generate_nonsense_word(rng)
        assert isinstance(word, str)
        assert len(word) >= 2

    def test_deterministic_with_seed(self):
        import random
        w1 = generate_nonsense_word(random.Random(42))
        w2 = generate_nonsense_word(random.Random(42))
        assert w1 == w2

    def test_different_seeds_differ(self):
        import random
        w1 = generate_nonsense_word(random.Random(1))
        w2 = generate_nonsense_word(random.Random(999))
        assert w1 != w2


class TestGenerateVocabulary:
    def test_returns_correct_counts(self):
        preds, consts = generate_vocabulary(10, 5)
        assert len(preds) == 10
        assert len(consts) == 5

    def test_no_duplicates(self):
        preds, consts = generate_vocabulary(50, 30)
        assert len(set(preds)) == len(preds)
        assert len(set(consts)) == len(consts)
        assert not set(preds) & set(consts)

    def test_avoids_existing_vocab(self):
        avoid = {"hello", "world"}
        preds, consts = generate_vocabulary(20, 10, existing_vocab=avoid)
        for w in preds + consts:
            assert w not in avoid

    def test_minimum_word_length(self):
        preds, consts = generate_vocabulary(20, 10)
        for w in preds + consts:
            assert len(w) >= 4


class TestGenerateSyntheticTheory:
    def test_produces_theory(self):
        params = SyntheticTheoryParams(
            n_facts=5, n_strict=3, n_defeasible=5, n_defeaters=2,
        )
        theory = generate_synthetic_theory(params)
        assert len(theory.facts) > 0
        assert len(theory.rules) > 0

    def test_deterministic(self):
        params = SyntheticTheoryParams(n_facts=10, n_defeasible=8)
        t1 = generate_synthetic_theory(params, seed=42)
        t2 = generate_synthetic_theory(params, seed=42)
        assert str(t1) == str(t2)

    def test_different_seeds_differ(self):
        params = SyntheticTheoryParams(n_facts=10, n_defeasible=8)
        t1 = generate_synthetic_theory(params, seed=1)
        t2 = generate_synthetic_theory(params, seed=999)
        assert str(t1) != str(t2)

    def test_contains_expected_rule_types(self):
        params = SyntheticTheoryParams(
            n_facts=5, n_strict=3, n_defeasible=5, n_defeaters=2,
        )
        theory = generate_synthetic_theory(params)
        rule_types = {r.rule_type for r in theory.rules}
        assert RuleType.DEFEASIBLE in rule_types

    def test_facts_are_ground(self):
        params = SyntheticTheoryParams(n_facts=10, n_defeasible=5)
        theory = generate_synthetic_theory(params)
        for fact in theory.facts:
            assert "(" in fact
            assert "X" not in fact


class TestGenerateMatchedSynthetic:
    def test_matches_naturalistic_structure(self):
        from blanc.generation.synthetic import generate_matched_synthetic
        nat = Theory()
        nat.add_fact("bird(tweety)")
        nat.add_fact("penguin(opus)")
        nat.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                          rule_type=RuleType.DEFEASIBLE, label="r1"))
        nat.add_rule(Rule(head="swims(X)", body=("fish(X)",),
                          rule_type=RuleType.STRICT, label="s1"))
        nat.add_rule(Rule(head="~flies(X)", body=("penguin(X)",),
                          rule_type=RuleType.DEFEATER, label="d1"))
        syn = generate_matched_synthetic(nat, seed=123)
        assert len(syn.facts) > 0
        assert len(syn.rules) > 0

    def test_different_seeds_differ(self):
        from blanc.generation.synthetic import generate_matched_synthetic
        nat = Theory()
        nat.add_fact("a(x)")
        nat.add_rule(Rule(head="b(X)", body=("a(X)",),
                          rule_type=RuleType.DEFEASIBLE, label="r1"))
        s1 = generate_matched_synthetic(nat, seed=1)
        s2 = generate_matched_synthetic(nat, seed=999)
        assert str(s1) != str(s2)


class TestSyntheticTheoryParams:
    def test_defaults(self):
        p = SyntheticTheoryParams()
        assert p.n_facts == 20
        assert p.n_strict == 5
        assert p.n_defeasible == 15
        assert p.n_defeaters == 3
        assert p.max_depth == 3
