"""
Tests for experiments/level3_evaluator.py.

Author: Anonymous Authors
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from level3_evaluator import (
    Level3Evaluator,
    parse_rule_from_text,
    _add_rule_with_superiority,
    EC_CORRECT,
    EC_DECODER_FAILURE,
    EC_DERIVATION_FAILURE,
    EC_MINIMALITY_VIOLATION,
    EC_CONSERVATIVITY_VIOLATION,
    EC_STRENGTH_SHORTFALL,
    SCORE_FULL,
    SCORE_PARTIAL,
    SCORE_NONE,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def penguin_instance():
    """Minimal penguin-style Level 3 AbductiveInstance."""
    r_flies = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_flies")
    r_feathers = Rule(head="has_feathers(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_feathers")
    D = Theory(
        facts=["bird(opus)", "bird(tweety)", "penguin(opus)"],
        rules=[r_flies, r_feathers],
        superiority={},
    )
    inst = AbductiveInstance(
        D_minus=D,
        target="flies(opus)",
        candidates=[
            "d_penguin: penguin(X) ~> ~flies(X)",
            "d_broad: bird(X) ~> ~flies(X)",
            "d_wrong: penguin(X) ~> ~has_feathers(X)",
        ],
        gold=["d_penguin: penguin(X) ~> ~flies(X)"],
        level=3,
        metadata={"preserved_expectations": ["flies(tweety)", "has_feathers(tweety)"]},
    )
    inst.id = "test-penguin"
    return inst


@pytest.fixture
def evaluator():
    return Level3Evaluator()


# ---------------------------------------------------------------------------
# parse_rule_from_text
# ---------------------------------------------------------------------------

class TestParseRuleFromText:
    def test_defeater_with_label(self):
        r = parse_rule_from_text("d_penguin: penguin(X) ~> ~flies(X)")
        assert r is not None
        assert r.rule_type == RuleType.DEFEATER
        assert r.head == "~flies(X)"
        assert "penguin(X)" in r.body
        assert r.label == "d_penguin"

    def test_defeater_without_label(self):
        r = parse_rule_from_text("penguin(X) ~> ~flies(X)")
        assert r is not None
        assert r.rule_type == RuleType.DEFEATER
        assert r.head == "~flies(X)"

    def test_defeasible_fat_arrow(self):
        r = parse_rule_from_text("r1: bird(X) => flies(X)")
        assert r is not None
        assert r.rule_type == RuleType.DEFEASIBLE
        assert r.head == "flies(X)"

    def test_prolog_defeater_style(self):
        r = parse_rule_from_text("~flies(X) :- penguin(X). % defeater")
        assert r is not None
        assert r.rule_type == RuleType.DEFEATER

    def test_unparseable_returns_none(self):
        r = parse_rule_from_text("Penguins cannot fly because they are flightless birds.")
        assert r is None

    def test_empty_string_returns_none(self):
        r = parse_rule_from_text("")
        assert r is None

    def test_multi_body(self):
        r = parse_rule_from_text("tardigrade(X), in_cryptobiosis(X) ~> ~requires_water(X)")
        assert r is not None
        assert len(r.body) == 2


# ---------------------------------------------------------------------------
# Level3Evaluator
# ---------------------------------------------------------------------------

class TestLevel3Evaluator:
    def test_correct_gold(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        assert result.correct is True
        assert result.parse_success is True
        assert result.resolves_anomaly is True
        assert result.is_conservative is True
        assert result.error_class == EC_CORRECT
        assert result.graded_score == SCORE_FULL

    def test_non_conservative_too_broad(self, evaluator, penguin_instance):
        broad = "d_broad: bird(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, broad, broad)
        assert result.correct is False
        assert result.resolves_anomaly is True
        assert result.is_conservative is False
        assert result.error_class == EC_CONSERVATIVITY_VIOLATION  # E4 in paper taxonomy
        assert result.graded_score == SCORE_PARTIAL               # 0.5

    def test_wrong_head_no_resolve(self, evaluator, penguin_instance):
        wrong = "d_wrong: penguin(X) ~> ~has_feathers(X)"
        result = evaluator.evaluate(penguin_instance, wrong, wrong)
        assert result.correct is False
        assert result.resolves_anomaly is False
        assert result.error_class == EC_DERIVATION_FAILURE         # E2 in paper taxonomy
        assert result.graded_score == SCORE_NONE

    def test_parse_failure(self, evaluator, penguin_instance):
        prose = "Penguins are flightless birds so they cannot fly."
        result = evaluator.evaluate(penguin_instance, prose, None)
        assert result.correct is False
        assert result.parse_success is False
        assert result.error_class == EC_DECODER_FAILURE            # E1 in paper taxonomy
        assert result.graded_score == SCORE_NONE

    def test_novelty_zero_for_existing_predicate(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        # penguin(X) already exists in D_minus (as a fact)
        assert result.nov is not None
        assert result.nov == 0.0

    def test_to_dict_has_required_keys(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        d = result.to_dict()
        for key in ("instance_id", "correct", "parse_success", "resolves_anomaly",
                    "is_conservative", "nov", "d_rev", "error_class",
                    "graded_score", "resolution_strength", "is_minimal"):
            assert key in d

    def test_graded_score_correct_is_full(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        assert result.graded_score == SCORE_FULL

    def test_graded_score_parse_failure_is_zero(self, evaluator, penguin_instance):
        result = evaluator.evaluate(penguin_instance, "nonsense text here", None)
        assert result.graded_score == SCORE_NONE

    def test_resolution_strength_present_for_valid_response(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        assert result.resolution_strength is not None

    def test_is_minimal_present_for_valid_response(self, evaluator, penguin_instance):
        gold = "d_penguin: penguin(X) ~> ~flies(X)"
        result = evaluator.evaluate(penguin_instance, gold, gold)
        assert result.is_minimal is not None


# ---------------------------------------------------------------------------
# Theory.copy  (canonical deep-copy now lives on the dataclass)
# ---------------------------------------------------------------------------

class TestTheoryCopy:
    def test_preserves_facts(self):
        D = Theory(facts=["bird(opus)"], rules=[], superiority={})
        D2 = D.copy()
        assert "bird(opus)" in D2.facts

    def test_normalizes_list_superiority(self):
        D = Theory(facts=[], rules=[], superiority=[["r1", "r2"]])
        D2 = D.copy()
        assert isinstance(D2.superiority, dict)
        assert "r2" in D2.superiority.get("r1", set())

    def test_preserves_dict_superiority(self):
        D = Theory(facts=[], rules=[], superiority={"r1": {"r2"}})
        D2 = D.copy()
        assert isinstance(D2.superiority, dict)
        assert "r2" in D2.superiority.get("r1", set())

    def test_independence(self):
        D = Theory(facts=["bird(X)"], rules=[], superiority={})
        D2 = D.copy()
        D2.add_fact("penguin(X)")
        assert "penguin(X)" not in D.facts
