"""Coverage tests for author/generation.py validation and distractor branches.

Targets: is_valid() branches where gold doesn't restore target,
non-gold candidate restores target, Level 3 conservativity violation,
and distractor generation strategies (wrong-body, reversed).
"""

import pytest

from blanc.author.generation import (
    AbductiveInstance,
    _generate_defeater_distractors,
    generate_level3_instance,
)
from blanc.core.theory import Rule, RuleType, Theory


def _simple_theory():
    """Theory: bird(tweety) + flies(X) :- bird(X) [defeasible]."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r1",
    ))
    return t


class TestIsValidLevel1:
    def test_gold_does_not_restore_target(self):
        """Line 84: gold element added but target still not derivable."""
        t = Theory()
        t.add_fact("fish(nemo)")
        inst = AbductiveInstance(
            D_minus=t,
            target="flies(tweety)",
            candidates=["bird(tweety)", "fish(nemo)"],
            gold=["fish(nemo)"],
            level=1,
        )
        assert not inst.is_valid()

    def test_empty_gold_invalid(self):
        inst = AbductiveInstance(
            D_minus=Theory(),
            target="flies(tweety)",
            candidates=["a"],
            gold=[],
            level=1,
        )
        assert not inst.is_valid()

    def test_target_already_derivable_invalid(self):
        """Line 82: D^- already proves target -> invalid instance."""
        t = _simple_theory()
        inst = AbductiveInstance(
            D_minus=t,
            target="flies(tweety)",
            candidates=["bird(tweety)"],
            gold=["bird(tweety)"],
            level=1,
        )
        assert not inst.is_valid()


class TestIsValidLevel2:
    def test_non_gold_candidate_restores_target(self):
        """Lines 90-97: a non-gold distractor also restores derivability."""
        t = Theory()
        t.add_fact("bird(tweety)")
        r1 = Rule(head="flies(X)", body=("bird(X)",),
                  rule_type=RuleType.DEFEASIBLE, label="r1")
        r2 = Rule(head="flies(X)", body=("bird(X)",),
                  rule_type=RuleType.DEFEASIBLE, label="r2_dup")
        inst = AbductiveInstance(
            D_minus=t,
            target="flies(tweety)",
            candidates=[r1, r2],
            gold=[r1],
            level=2,
        )
        assert not inst.is_valid()


class TestIsValidLevel3:
    def test_level3_with_rule_gold(self):
        t = Theory()
        t.add_fact("bird(opus)")
        gold = Rule(head="~flies(X)", body=("penguin(X)",),
                    rule_type=RuleType.DEFEATER, label="d1")
        inst = AbductiveInstance(
            D_minus=t, target="flies(opus)",
            candidates=[gold], gold=[gold], level=3,
        )
        assert inst.is_valid()

    def test_level3_empty_gold_head_invalid(self):
        with pytest.raises(ValueError):
            Rule(head="", body=("x(X)",),
                 rule_type=RuleType.DEFEATER, label="bad")

    def test_level3_whitespace_string_gold_invalid(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="anomaly",
            candidates=["  "], gold=["  "], level=3,
        )
        assert not inst.is_valid()

    def test_unknown_level_raises(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="x",
            candidates=["a"], gold=["a"], level=99,
        )
        with pytest.raises(ValueError, match="Unknown level"):
            inst.is_valid()


class TestGenerateDefeaterDistractors:
    def test_wrong_head_distractors(self):
        theory = Theory()
        theory.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r1"))
        theory.add_rule(Rule(head="swims(X)", body=("fish(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r2"))
        gold = Rule(head="~flies(X)", body=("penguin(X)",),
                    rule_type=RuleType.DEFEATER, label="d1")
        distractors = _generate_defeater_distractors(theory, gold, "flies(opus)", k=3)
        assert len(distractors) >= 1
        for d in distractors:
            assert d.rule_type == RuleType.DEFEATER

    def test_wrong_body_distractors(self):
        theory = Theory()
        theory.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r1"))
        theory.add_rule(Rule(head="swims(X)", body=("fish(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r2"))
        gold = Rule(head="~flies(X)", body=("penguin(X)",),
                    rule_type=RuleType.DEFEATER, label="d1")
        distractors = _generate_defeater_distractors(theory, gold, "flies(opus)", k=5)
        wrong_body = [d for d in distractors if d.label and "wrongbody" in d.label]
        assert len(wrong_body) >= 1

    def test_reversed_distractor(self):
        theory = Theory()
        theory.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                             rule_type=RuleType.DEFEASIBLE, label="r1"))
        gold = Rule(head="~flies(X)", body=("penguin(X)",),
                    rule_type=RuleType.DEFEATER, label="d1")
        distractors = _generate_defeater_distractors(theory, gold, "flies(opus)", k=10)
        reversed_d = [d for d in distractors if d.label and "reversed" in d.label]
        assert len(reversed_d) >= 1

    def test_k_limits_output(self):
        theory = Theory()
        for i in range(20):
            theory.add_rule(Rule(head=f"p{i}(X)", body=(f"q{i}(X)",),
                                 rule_type=RuleType.DEFEASIBLE, label=f"r{i}"))
        gold = Rule(head="~p0(X)", body=("special(X)",),
                    rule_type=RuleType.DEFEATER, label="d0")
        distractors = _generate_defeater_distractors(theory, gold, "p0(a)", k=3)
        assert len(distractors) <= 3
