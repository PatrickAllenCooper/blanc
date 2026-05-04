"""
Targeted tests for codec/cascading_decoder.py coverage gaps.

Covers: empty input paths, decode_with_confidence, decode_batch,
get_decoder_statistics (lines 48, 53-54, 63-75, 93, 96-99, 104-147).

Author: Anonymous Authors
Date: 2026-02-18
"""

import pytest
from blanc.codec.cascading_decoder import (
    CascadingDecoder,
    decode_batch,
    get_decoder_statistics,
)


CANDIDATES = ["bird(tweety)", "penguin(tweety)", "sparrow(tweety)"]


class TestCascadingDecoderEdgeCases:
    def test_empty_text_returns_none(self):
        dec = CascadingDecoder()
        result, stage = dec.decode("", CANDIDATES)
        assert result is None
        assert stage is None

    def test_none_candidates_returns_none(self):
        dec = CascadingDecoder()
        result, stage = dec.decode("bird(tweety)", [])
        assert result is None
        assert stage is None

    def test_exact_match_returns_d1(self):
        dec = CascadingDecoder()
        result, stage = dec.decode("bird(tweety)", CANDIDATES)
        assert result == "bird(tweety)"
        assert stage == "D1"

    def test_empty_candidates_returns_none_none(self):
        """Empty candidate list always returns (None, None) regardless of text."""
        dec = CascadingDecoder()
        result, stage = dec.decode("bird(tweety)", [])
        assert result is None
        assert stage is None


class TestDecodeWithConfidence:
    def test_d1_match_confidence_one(self):
        dec = CascadingDecoder()
        result, stage, conf = dec.decode_with_confidence("bird(tweety)", CANDIDATES)
        assert result == "bird(tweety)"
        assert stage == "D1"
        assert conf == 1.0

    def test_no_candidates_confidence_zero(self):
        """Empty candidate list always gives confidence 0."""
        dec = CascadingDecoder()
        result, stage, conf = dec.decode_with_confidence("bird(tweety)", [])
        assert result is None
        assert conf == 0.0

    def test_confidence_is_float(self):
        dec = CascadingDecoder()
        _, _, conf = dec.decode_with_confidence("bird(tweety)", CANDIDATES)
        assert isinstance(conf, float)


class TestDecodeBatch:
    def test_batch_decodes_all_texts(self):
        texts = ["bird(tweety)", "penguin(tweety)", "unknown_xyz"]
        results = decode_batch(texts, CANDIDATES)
        assert len(results) == 3

    def test_batch_returns_tuples(self):
        results = decode_batch(["bird(tweety)"], CANDIDATES)
        assert isinstance(results[0], tuple)
        assert len(results[0]) == 2

    def test_batch_exact_matches_resolved(self):
        texts = ["bird(tweety)", "sparrow(tweety)"]
        results = decode_batch(texts, CANDIDATES)
        decoded, stages = zip(*results)
        assert "bird(tweety)" in decoded
        assert "sparrow(tweety)" in decoded

    def test_empty_batch_returns_empty(self):
        results = decode_batch([], CANDIDATES)
        assert results == []


class TestGetDecoderStatistics:
    def test_all_successful(self):
        results = [("bird(tweety)", "D1"), ("penguin(tweety)", "D1")]
        stats = get_decoder_statistics(results)
        assert stats["total_decoded"] == 2
        assert stats["total_failed"] == 0
        assert stats["success_rate"] == 1.0

    def test_some_failed(self):
        results = [("bird(tweety)", "D1"), (None, None)]
        stats = get_decoder_statistics(results)
        assert stats["total_decoded"] == 1
        assert stats["total_failed"] == 1
        assert stats["success_rate"] == 0.5

    def test_by_stage_counts(self):
        results = [
            ("a", "D1"), ("b", "D1"), ("c", "D2"), (None, None)
        ]
        stats = get_decoder_statistics(results)
        assert stats["by_stage"]["D1"] == 2
        assert stats["by_stage"]["D2"] == 1

    def test_empty_results(self):
        stats = get_decoder_statistics([])
        assert stats["total_decoded"] == 0
        assert stats["success_rate"] == 0.0

    def test_all_failed(self):
        results = [(None, None), (None, None)]
        stats = get_decoder_statistics(results)
        assert stats["total_failed"] == 2
        assert stats["success_rate"] == 0.0
