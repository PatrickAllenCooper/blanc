"""Coverage tests for reasoning/derivation_tree.py uncovered paths.

Targets: tree_overlap, extract_support_path, enumerate_permutations edge cases.
"""

import pytest

from blanc.core.theory import Rule, RuleType, Theory
from blanc.reasoning.defeasible import DefeasibleEngine
from blanc.reasoning.derivation_tree import (
    DerivationNode,
    DerivationTree,
    build_derivation_tree,
    enumerate_permutations,
    extract_support_path,
    tree_overlap,
)


def _make_theory():
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r1",
    ))
    return t


def _build_tree(theory, literal):
    engine = DefeasibleEngine(theory)
    return build_derivation_tree(engine, literal)


class TestTreeOverlap:
    def test_identical_trees(self):
        theory = _make_theory()
        tree = _build_tree(theory, "flies(tweety)")
        assert tree is not None
        assert tree_overlap(tree, tree) == 1.0

    def test_disjoint_trees(self):
        t1 = Theory()
        t1.add_fact("bird(tweety)")
        t1.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                         rule_type=RuleType.DEFEASIBLE, label="r1"))
        tree1 = _build_tree(t1, "flies(tweety)")

        t2 = Theory()
        t2.add_fact("fish(nemo)")
        t2.add_rule(Rule(head="swims(X)", body=("fish(X)",),
                         rule_type=RuleType.DEFEASIBLE, label="r2"))
        tree2 = _build_tree(t2, "swims(nemo)")

        assert tree1 is not None and tree2 is not None
        overlap = tree_overlap(tree1, tree2)
        assert overlap == 0.0

    def test_both_empty(self):
        from blanc.reasoning.derivation_tree import NodeType
        empty1 = DerivationTree(
            root=DerivationNode(literal="", node_type=NodeType.FACT),
        )
        empty2 = DerivationTree(
            root=DerivationNode(literal="", node_type=NodeType.FACT),
        )
        assert tree_overlap(empty1, empty2) == 1.0


class TestExtractSupportPath:
    def test_extracts_path(self):
        theory = _make_theory()
        tree = _build_tree(theory, "flies(tweety)")
        assert tree is not None
        path = extract_support_path(tree)
        assert isinstance(path, list)
        assert len(path) >= 1

    def test_with_target_node(self):
        theory = _make_theory()
        tree = _build_tree(theory, "flies(tweety)")
        assert tree is not None
        path = extract_support_path(tree, target="bird(tweety)")
        assert isinstance(path, list)

    def test_with_missing_target(self):
        theory = _make_theory()
        tree = _build_tree(theory, "flies(tweety)")
        assert tree is not None
        path = extract_support_path(tree, target="nonexistent(x)")
        assert isinstance(path, list)


class TestEnumeratePermutations:
    def test_produces_permutations(self):
        theory = _make_theory()
        tree = _build_tree(theory, "flies(tweety)")
        assert tree is not None
        perms = enumerate_permutations(tree, theory, "flies(tweety)", k=5)
        assert isinstance(perms, list)
        for elem, d_minus in perms:
            assert isinstance(d_minus, Theory)

    def test_unprovable_target_returns_empty(self):
        from blanc.reasoning.derivation_tree import NodeType
        theory = Theory()
        theory.add_fact("bird(tweety)")
        tree = DerivationTree(
            root=DerivationNode(literal="swims(nemo)", node_type=NodeType.FACT),
        )
        perms = enumerate_permutations(tree, theory, "swims(nemo)", k=5)
        assert perms == []
