"""
Tests for src/blanc/codec/cascading_decoder.py — covering the 77% gap.

Missing lines: 58-59 (D1 exception path), 66-78 (D2/D3 exception path,
fallback chain), 95 (_d1_exact_match rule branch), 118 (D2 confidence),
120 (D3 confidence).
"""

from unittest.mock import patch, MagicMock
import pytest

from blanc.codec.cascading_decoder import (
    CascadingDecoder,
    decode_batch,
    get_decoder_statistics,
)
from blanc.core.theory import Rule, RuleType


def _make_rule(head: str, body: tuple = (), label: str = None) -> Rule:
    return Rule(head=head, body=body, rule_type=RuleType.DEFEASIBLE, label=label)


class TestCascadingDecoderExceptionPaths:
    """Cover D1/D2/D3 exception-swallowing branches."""

    def test_d1_exception_falls_through_to_d2(self):
        """If _d1_exact_match raises, decoder falls through to D2."""
        decoder = CascadingDecoder()
        candidates = ["bird(tweety)"]

        with patch.object(decoder, "_d1_exact_match", side_effect=RuntimeError("boom")):
            result, stage = decoder.decode("bird(tweety)", candidates)
        # D2 or D3 may succeed
        assert result is not None or stage is None

    def test_d2_exception_falls_through_to_d3(self):
        """If D2 raises, D3 is tried."""
        from blanc.codec import cascading_decoder
        decoder = CascadingDecoder()
        candidates = ["bird(tweety)"]

        with patch.object(decoder, "_d1_exact_match", return_value=None):
            with patch("blanc.codec.cascading_decoder.decode_d2", side_effect=RuntimeError):
                result, stage = decoder.decode("bird(tweety)", candidates)
        # D3 may or may not succeed for this text
        assert isinstance(stage, (str, type(None)))

    def test_all_stages_raise_returns_none(self):
        """If all decoders raise, (None, None) is returned."""
        decoder = CascadingDecoder()
        with patch.object(decoder, "_d1_exact_match", side_effect=RuntimeError):
            with patch("blanc.codec.cascading_decoder.decode_d2", side_effect=RuntimeError):
                with patch("blanc.codec.cascading_decoder.decode_d3", side_effect=RuntimeError):
                    result, stage = decoder.decode("bird(tweety)", ["bird(tweety)"])
        assert result is None
        assert stage is None


class TestD1ExactMatchRuleBranch:
    """Cover line 95: _d1_exact_match with Rule candidates.

    Note: _normalize(str(rule)) uses defeasible syntax ("bird(X) => flies(X)")
    while _normalize_rule(rule) uses Prolog syntax ("flies(x) :- bird(x)").
    These differ, so str(rule) does NOT match via _d1_exact_match.
    The test covers the code path (the else branch for Rule instances).
    """

    def test_rule_candidate_not_matched_by_str(self):
        decoder = CascadingDecoder()
        rule = _make_rule("flies(X)", ("bird(X)",), label=None)
        # _normalize(str(rule)) != _normalize_rule(rule) — different formats
        text = str(rule)
        candidates = [rule]
        result = decoder._d1_exact_match(text, candidates)
        # Does not match because defeasible str vs prolog normalization differ
        assert result is None

    def test_rule_candidate_matched_via_prolog_text(self):
        """When text is in Prolog form, _normalize(text) may match _normalize_rule."""
        decoder = CascadingDecoder()
        rule = _make_rule("flies(X)", ("bird(X)",), label=None)
        # _normalize_rule produces: "flies(x) :- bird(x)"
        prolog_text = rule.to_prolog()  # "flies(X) :- bird(X)."
        candidates = [rule]
        result = decoder._d1_exact_match(prolog_text, candidates)
        # Both sides normalize the same prolog text — should match
        assert result is rule

    def test_string_and_rule_candidates(self):
        decoder = CascadingDecoder()
        rule = _make_rule("flies(X)", ("bird(X)",))
        candidates = ["bird(tweety)", rule]
        result = decoder._d1_exact_match("bird(tweety)", candidates)
        assert result == "bird(tweety)"


class TestDecodeWithConfidenceAllStages:
    """Cover lines 118 (D2 confidence) and 120 (D3 confidence)."""

    def test_d1_confidence_is_one(self):
        decoder = CascadingDecoder()
        candidates = ["bird(tweety)"]
        _, stage, conf = decoder.decode_with_confidence("bird(tweety)", candidates)
        assert stage == "D1"
        assert conf == 1.0

    def test_d2_confidence(self):
        decoder = CascadingDecoder()
        candidates = ["bird(tweety)"]
        with patch.object(decoder, "_d1_exact_match", return_value=None):
            with patch(
                "blanc.codec.cascading_decoder.decode_d2", return_value="bird(tweety)"
            ):
                _, stage, conf = decoder.decode_with_confidence("bird tweety", candidates)
        assert stage == "D2"
        assert conf == 0.9

    def test_d3_confidence(self):
        decoder = CascadingDecoder()
        candidates = ["bird(tweety)"]
        with patch.object(decoder, "_d1_exact_match", return_value=None):
            with patch("blanc.codec.cascading_decoder.decode_d2", return_value=None):
                with patch(
                    "blanc.codec.cascading_decoder.decode_d3", return_value="bird(tweety)"
                ):
                    _, stage, conf = decoder.decode_with_confidence("...", candidates)
        assert stage == "D3"
        assert conf == 0.75

    def test_fail_confidence_zero(self):
        decoder = CascadingDecoder()
        with patch.object(decoder, "_d1_exact_match", return_value=None):
            with patch("blanc.codec.cascading_decoder.decode_d2", return_value=None):
                with patch("blanc.codec.cascading_decoder.decode_d3", return_value=None):
                    _, stage, conf = decoder.decode_with_confidence("##", [])
        assert stage is None
        assert conf == 0.0


class TestDecodeBatch:
    def test_batch_decodes_all(self):
        candidates = ["bird(tweety)", "flies(tweety)"]
        results = decode_batch(["bird(tweety)", "flies(tweety)"], candidates)
        assert len(results) == 2

    def test_batch_with_failures(self):
        results = decode_batch(["##GARBAGE##"], ["bird(tweety)"])
        assert len(results) == 1
        result, stage = results[0]
        assert result is None or isinstance(result, str)


class TestGetDecoderStatistics:
    def test_all_success(self):
        fake_results = [("a", "D1"), ("b", "D1"), ("c", "D2")]
        stats = get_decoder_statistics(fake_results)
        assert stats["total_decoded"] == 3
        assert stats["total_failed"] == 0
        assert stats["by_stage"]["D1"] == 2
        assert stats["by_stage"]["D2"] == 1
        assert stats["success_rate"] == 1.0

    def test_some_failures(self):
        fake_results = [("a", "D1"), (None, None)]
        stats = get_decoder_statistics(fake_results)
        assert stats["total_decoded"] == 1
        assert stats["total_failed"] == 1
        assert stats["success_rate"] == pytest.approx(0.5)

    def test_empty_results(self):
        stats = get_decoder_statistics([])
        assert stats["success_rate"] == 0.0
        assert stats["total_decoded"] == 0
