"""Coverage tests for author/generation.py.

Targets generate_level1/2/3_instance functions and helpers
that were previously uncovered.
"""

import pytest

from blanc.author.generation import (
    AbductiveInstance,
    _add_element,
    _element_to_str,
    generate_level1_instance,
    generate_level2_instance,
    generate_level3_instance,
)
from blanc.core.theory import Rule, RuleType, Theory


@pytest.fixture
def bird_theory():
    """A simple theory where flies(tweety) is derivable only via bird(tweety) + r1."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r1",
    ))
    return t


@pytest.fixture
def defeater_theory():
    """Theory with a defeater for Level 3 testing."""
    t = Theory()
    t.add_fact("bird(opus)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r1",
    ))
    t.add_rule(Rule(
        head="~flies(X)", body=("penguin(X)",),
        rule_type=RuleType.DEFEATER, label="d1",
    ))
    t.add_superiority("d1", "r1")
    return t


class TestGenerateLevel1:
    def test_creates_instance(self, bird_theory):
        inst = generate_level1_instance(
            bird_theory, "flies(tweety)", "bird(tweety)", k_distractors=2,
        )
        assert isinstance(inst, AbductiveInstance)
        assert inst.level == 1
        assert "bird(tweety)" in inst.gold

    def test_non_critical_fact_raises(self, bird_theory):
        with pytest.raises(ValueError, match="not critical"):
            generate_level1_instance(
                bird_theory, "flies(tweety)", "some_unrelated_fact", k_distractors=1,
            )

    def test_d_minus_lacks_ablated_fact(self, bird_theory):
        inst = generate_level1_instance(
            bird_theory, "flies(tweety)", "bird(tweety)", k_distractors=1,
        )
        assert "bird(tweety)" not in inst.D_minus.facts

    def test_metadata_populated(self, bird_theory):
        inst = generate_level1_instance(
            bird_theory, "flies(tweety)", "bird(tweety)", k_distractors=2,
        )
        assert inst.metadata["ablated_element"] == "bird(tweety)"
        assert inst.metadata["ablated_type"] == "fact"
        assert inst.metadata["k_distractors"] == 2


class TestGenerateLevel2:
    def test_creates_instance(self, bird_theory):
        r1 = bird_theory.get_rule_by_label("r1")
        inst = generate_level2_instance(
            bird_theory, "flies(tweety)", r1, k_distractors=2,
        )
        assert isinstance(inst, AbductiveInstance)
        assert inst.level == 2
        assert r1 in inst.gold

    def test_strict_rule_raises(self, bird_theory):
        strict_rule = Rule(
            head="animal(X)", body=("living(X)",),
            rule_type=RuleType.STRICT, label="s_test",
        )
        with pytest.raises(ValueError, match="defeasible"):
            generate_level2_instance(
                bird_theory, "flies(tweety)", strict_rule, k_distractors=1,
            )

    def test_non_critical_rule_raises(self, bird_theory):
        fake_rule = Rule(
            head="swims(X)", body=("fish(X)",),
            rule_type=RuleType.DEFEASIBLE, label="fake",
        )
        with pytest.raises(ValueError, match="not critical"):
            generate_level2_instance(
                bird_theory, "flies(tweety)", fake_rule, k_distractors=1,
            )

    def test_metadata_includes_rule_type(self, bird_theory):
        r1 = bird_theory.get_rule_by_label("r1")
        inst = generate_level2_instance(
            bird_theory, "flies(tweety)", r1, k_distractors=1,
        )
        assert inst.metadata["ablated_rule_type"] == "defeasible"


class TestGenerateLevel3:
    def test_creates_instance(self, defeater_theory):
        d1 = defeater_theory.get_rule_by_label("d1")
        inst = generate_level3_instance(
            defeater_theory, "flies(opus)", d1, k_distractors=2,
        )
        assert isinstance(inst, AbductiveInstance)
        assert inst.level == 3
        assert d1 in inst.gold
        assert inst.metadata["conservative"] is True

    def test_non_defeater_raises(self, defeater_theory):
        r1 = defeater_theory.get_rule_by_label("r1")
        with pytest.raises(ValueError, match="DEFEATER"):
            generate_level3_instance(
                defeater_theory, "flies(opus)", r1, k_distractors=1,
            )

    def test_has_distractors(self, defeater_theory):
        d1 = defeater_theory.get_rule_by_label("d1")
        inst = generate_level3_instance(
            defeater_theory, "flies(opus)", d1, k_distractors=3,
        )
        assert len(inst.candidates) >= 2


class TestAddElement:
    def test_add_fact(self, bird_theory):
        new = _add_element(bird_theory, "penguin(opus)")
        assert "penguin(opus)" in new.facts
        assert "bird(tweety)" in new.facts

    def test_add_rule(self, bird_theory):
        rule = Rule(
            head="swims(X)", body=("fish(X)",),
            rule_type=RuleType.DEFEASIBLE, label="new_rule",
        )
        new = _add_element(bird_theory, rule)
        labels = [r.label for r in new.rules]
        assert "new_rule" in labels

    def test_preserves_superiority(self, defeater_theory):
        new = _add_element(defeater_theory, "extra_fact(x)")
        assert "d1" in new.superiority
        assert "r1" in new.superiority["d1"]


class TestElementToStr:
    def test_string_passthrough(self):
        assert _element_to_str("bird(tweety)") == "bird(tweety)"

    def test_rule_converts(self):
        r = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE)
        result = _element_to_str(r)
        assert "flies" in result


class TestAbductiveInstanceId:
    def test_default_id(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="x",
            candidates=["a"], gold=["a"], level=1,
        )
        assert inst.id == ""

    def test_id_in_to_dict(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="x",
            candidates=["a"], gold=["a"], level=1, id="test-001",
        )
        d = inst.to_dict()
        assert d["id"] == "test-001"

    def test_l3_validation_requires_target(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="",
            candidates=["a"], gold=["a"], level=3,
        )
        assert not inst.is_valid()

    def test_l3_validation_requires_gold(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="anomaly",
            candidates=["a"], gold=[], level=3,
        )
        assert not inst.is_valid()

    def test_l3_validation_passes_with_good_data(self):
        inst = AbductiveInstance(
            D_minus=Theory(), target="anomaly",
            candidates=["a"], gold=["~flies(X) :- penguin(X)"], level=3,
        )
        assert inst.is_valid()
