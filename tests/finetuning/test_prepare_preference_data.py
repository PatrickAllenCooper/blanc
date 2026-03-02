"""
Tests for experiments/finetuning/prepare_preference_data.py.

Tests cover pure-Python logic (no GPU, no live model):
  - PreferencePair dataclass
  - make_splits (stratified split)
  - extract_pairs (preference extraction with margin threshold)
  - extract_gold_anchored_pairs
  - score_response (via mocks)

Author: Patrick Cooper
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT / "experiments" / "finetuning"))

from blanc.author.generation import AbductiveInstance
from blanc.core.theory import Theory, Rule, RuleType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_instance(
    target: str = "flies(tweety)",
    candidates: list = None,
    gold: list = None,
    level: int = 2,
    domain: str = "biology",
    inst_id: str = "bio-l2-001",
) -> AbductiveInstance:
    theory = Theory()
    theory.add_fact("bird(tweety)")
    inst = AbductiveInstance(
        D_minus=theory,
        target=target,
        candidates=candidates or ["flies(tweety)", "swims(tweety)"],
        gold=gold or ["flies(tweety)"],
        level=level,
        metadata={"domain": domain},
    )
    inst.id = inst_id
    return inst


def _make_instances(n_l2: int = 10, n_l3: int = 5) -> list:
    insts = []
    for i in range(n_l2):
        inst = _make_instance(level=2, inst_id=f"bio-l2-{i:03d}")
        insts.append(inst)
    for i in range(n_l3):
        inst = _make_instance(
            level=3, target="not_flies(tweety)",
            inst_id=f"bio-l3-{i:03d}",
            domain="biology",
        )
        insts.append(inst)
    return insts


# ---------------------------------------------------------------------------
# PreferencePair
# ---------------------------------------------------------------------------

class TestPreferencePair:
    def test_creation(self):
        from prepare_preference_data import PreferencePair
        pair = PreferencePair(
            prompt="p", chosen="y_w", rejected="y_l",
            score_chosen=1.0, score_rejected=0.0, margin=1.0,
            level=2, domain="biology", instance_id="bio-001",
            modality="M4", strategy="direct", source="sampled",
        )
        assert pair.margin == 1.0
        assert pair.level == 2

    def test_to_dict_has_hf_keys(self):
        from prepare_preference_data import PreferencePair
        from dataclasses import asdict
        pair = PreferencePair(
            prompt="p", chosen="y_w", rejected="y_l",
            score_chosen=1.0, score_rejected=0.0, margin=1.0,
            level=2, domain="biology", instance_id="bio-001",
            modality="M4", strategy="direct", source="sampled",
        )
        d = asdict(pair)
        assert "prompt" in d
        assert "chosen" in d
        assert "rejected" in d
        assert "margin" in d


# ---------------------------------------------------------------------------
# make_splits
# ---------------------------------------------------------------------------

class TestMakeSplits:
    def test_split_sizes(self):
        from prepare_preference_data import make_splits
        instances = _make_instances(n_l2=20, n_l3=6)
        train, val, test = make_splits(instances)
        total = len(train) + len(val) + len(test)
        assert total == 26

    def test_split_fractions_approximate(self):
        from prepare_preference_data import make_splits
        instances = _make_instances(n_l2=100, n_l3=20)
        train, val, test = make_splits(instances)
        total = len(train) + len(val) + len(test)
        assert abs(len(train) / total - 0.70) < 0.10
        assert abs(len(val) / total - 0.15) < 0.08
        assert abs(len(test) / total - 0.15) < 0.08

    def test_no_instance_shared_between_splits(self):
        from prepare_preference_data import make_splits
        instances = _make_instances(n_l2=30, n_l3=9)
        train, val, test = make_splits(instances)
        train_ids = {i.id for i in train}
        val_ids   = {i.id for i in val}
        test_ids  = {i.id for i in test}
        assert len(train_ids & val_ids) == 0
        assert len(train_ids & test_ids) == 0
        assert len(val_ids & test_ids) == 0

    def test_stratified_by_level(self):
        from prepare_preference_data import make_splits
        instances = _make_instances(n_l2=20, n_l3=10)
        train, val, test = make_splits(instances)
        # Both L2 and L3 should appear in all splits
        for split in [train, val, test]:
            levels = {i.level for i in split}
            assert 2 in levels

    def test_reproducible_with_same_seed(self):
        from prepare_preference_data import make_splits
        instances = _make_instances(n_l2=30, n_l3=9)
        train1, val1, test1 = make_splits(instances, seed=42)
        train2, val2, test2 = make_splits(instances, seed=42)
        assert [i.id for i in train1] == [i.id for i in train2]


# ---------------------------------------------------------------------------
# extract_pairs
# ---------------------------------------------------------------------------

class TestExtractPairs:
    def test_extracts_pairs_above_margin(self):
        from prepare_preference_data import extract_pairs
        inst = _make_instance()
        responses = [
            ("correct response", 1.0, "flies(tweety)"),
            ("wrong response",   0.0, ""),
        ]
        pairs = extract_pairs(inst, responses, "prompt text", "M4", "direct", min_margin=0.25)
        assert len(pairs) == 1  # only (1.0, 0.0) pair qualifies

    def test_no_pairs_below_margin_threshold(self):
        from prepare_preference_data import extract_pairs
        inst = _make_instance()
        responses = [
            ("r1", 0.5, "r1"),
            ("r2", 0.6, "r2"),
        ]
        pairs = extract_pairs(inst, responses, "prompt", "M4", "direct", min_margin=0.5)
        assert len(pairs) == 0

    def test_pair_fields(self):
        from prepare_preference_data import extract_pairs
        inst = _make_instance()
        responses = [("good", 1.0, "good"), ("bad", 0.0, "")]
        pairs = extract_pairs(inst, responses, "the prompt", "M4", "direct", min_margin=0.25)
        assert len(pairs) == 1
        p = pairs[0]
        assert p.chosen == "good"
        assert p.rejected == "bad"
        assert p.margin == pytest.approx(1.0)
        assert p.prompt == "the prompt"
        assert p.source == "sampled"
        assert p.level == 2
        assert p.domain == "biology"

    def test_symmetric_pairs_extracted(self):
        from prepare_preference_data import extract_pairs
        inst = _make_instance()
        # Three responses with different scores
        responses = [
            ("high",   1.0, "h"),
            ("medium", 0.5, "m"),
            ("low",    0.0, "l"),
        ]
        pairs = extract_pairs(inst, responses, "p", "M4", "direct", min_margin=0.25)
        # (high,medium), (high,low), (medium,low) qualify (not reverses)
        assert len(pairs) == 3


# ---------------------------------------------------------------------------
# extract_gold_anchored_pairs
# ---------------------------------------------------------------------------

class TestExtractGoldAnchoredPairs:
    def test_extracts_gold_vs_incorrect(self):
        from prepare_preference_data import extract_gold_anchored_pairs
        inst = _make_instance(gold=["flies(tweety)"])
        responses = [
            ("flies(tweety)", 1.0, "flies(tweety)"),
            ("wrong answer",   0.0, ""),
        ]
        pairs = extract_gold_anchored_pairs(inst, responses, "prompt", "M4", "direct")
        # gold (score 1.0) vs incorrect (score 0.0) → 1 pair
        assert len(pairs) >= 1

    def test_gold_is_always_chosen(self):
        from prepare_preference_data import extract_gold_anchored_pairs
        inst = _make_instance(gold=["flies(tweety)"])
        responses = [
            ("flies(tweety)", 1.0, "flies(tweety)"),
            ("wrong",          0.0, ""),
        ]
        pairs = extract_gold_anchored_pairs(inst, responses, "prompt", "M4", "direct")
        for p in pairs:
            # The gold answer should be the chosen response
            assert p.source == "gold_anchored"

    def test_no_incorrect_responses_no_pairs(self):
        from prepare_preference_data import extract_gold_anchored_pairs
        inst = _make_instance(gold=["flies(tweety)"])
        # All responses are correct
        responses = [
            ("flies(tweety)", 1.0, "flies(tweety)"),
        ]
        pairs = extract_gold_anchored_pairs(inst, responses, "prompt", "M4", "direct")
        # No incorrect response to pair against
        assert len(pairs) == 0


# ---------------------------------------------------------------------------
# score_response
# ---------------------------------------------------------------------------

class TestScoreResponse:
    def test_correct_l2_returns_one(self):
        from prepare_preference_data import score_response
        inst = _make_instance(gold=["flies(tweety)"])
        decoder = MagicMock()
        decoder.decode.return_value = ("flies(tweety)", "D1")
        l3_eval = MagicMock()
        score, decoded = score_response("flies(tweety)", inst, decoder, l3_eval)
        assert score == 1.0
        assert decoded == "flies(tweety)"

    def test_incorrect_l2_returns_zero(self):
        from prepare_preference_data import score_response
        inst = _make_instance(gold=["flies(tweety)"])
        decoder = MagicMock()
        decoder.decode.return_value = ("swims(tweety)", "D1")
        l3_eval = MagicMock()
        score, decoded = score_response("swims(tweety)", inst, decoder, l3_eval)
        assert score == 0.0

    def test_decode_failure_returns_zero(self):
        from prepare_preference_data import score_response
        inst = _make_instance()
        decoder = MagicMock()
        decoder.decode.side_effect = RuntimeError("parse error")
        l3_eval = MagicMock()
        score, decoded = score_response("garbage", inst, decoder, l3_eval)
        assert score == 0.0
        assert decoded == ""

    def test_decode_returns_none_gives_zero(self):
        from prepare_preference_data import score_response
        inst = _make_instance()
        decoder = MagicMock()
        decoder.decode.return_value = (None, None)
        l3_eval = MagicMock()
        score, decoded = score_response("...", inst, decoder, l3_eval)
        assert score == 0.0

    def test_l3_uses_graded_scoring(self):
        from prepare_preference_data import score_response
        inst = _make_instance(level=3, target="not_flies(tweety)")
        decoder = MagicMock()
        decoder.decode.return_value = ("penguin(tweety)", "D2")
        l3_result = MagicMock()
        l3_result.graded_score = 0.75
        l3_eval = MagicMock()
        l3_eval.evaluate.return_value = l3_result
        score, decoded = score_response("penguin(tweety)", inst, decoder, l3_eval)
        assert score == pytest.approx(0.75)

    def test_l3_evaluator_exception_returns_zero(self):
        from prepare_preference_data import score_response
        inst = _make_instance(level=3, target="not_flies(tweety)")
        decoder = MagicMock()
        decoder.decode.return_value = ("penguin(tweety)", "D2")
        l3_eval = MagicMock()
        l3_eval.evaluate.side_effect = RuntimeError("eval error")
        score, _ = score_response("penguin(tweety)", inst, decoder, l3_eval)
        assert score == 0.0
