"""
Unit tests for ReplayTraceExtractor.

Uses in-memory .jsonl content written to tmp files; no SC2 binary needed.

Author: Patrick Cooper
"""

import json
import tempfile
from pathlib import Path

import pytest

from blanc.sc2live.replay import ReplayTraceExtractor, TraceFrame
from blanc.core.theory import Theory


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_snapshot(step: int, facts: list[str], derived: list[str] | None = None) -> dict:
    return {
        "step": step,
        "facts": facts,
        "derived": derived or [],
        "orders_issued": [],
        "timestamp": 1714000000.0 + step,
    }


def _write_jsonl(path: Path, snapshots: list[dict]) -> None:
    with open(path, "w") as f:
        for snap in snapshots:
            f.write(json.dumps(snap) + "\n")


@pytest.fixture
def extractor():
    return ReplayTraceExtractor()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStreamFile:
    def test_stream_returns_correct_step_numbers(self, extractor, tmp_path):
        trace = tmp_path / "trace_001.jsonl"
        snaps = [
            _make_snapshot(0, ["infantry_unit(marine_00000041)"]),
            _make_snapshot(22, ["infantry_unit(marine_00000041)", "in_zone(marine_00000041, main_base)"]),
        ]
        _write_jsonl(trace, snaps)

        frames = list(extractor.stream_file(trace))
        assert len(frames) == 2
        assert frames[0].step == 0
        assert frames[1].step == 22

    def test_frame_theory_contains_facts(self, extractor, tmp_path):
        trace = tmp_path / "trace_002.jsonl"
        _write_jsonl(trace, [
            _make_snapshot(0, [
                "infantry_unit(marine_00000041)",
                "in_zone(marine_00000041, main_base)",
            ])
        ])
        frames = list(extractor.stream_file(trace))
        assert len(frames) == 1
        theory = frames[0].theory
        assert isinstance(theory, Theory)
        assert "infantry_unit(marine_00000041)" in theory.facts
        assert "in_zone(marine_00000041, main_base)" in theory.facts

    def test_frame_source_file_is_set(self, extractor, tmp_path):
        trace = tmp_path / "trace_003.jsonl"
        _write_jsonl(trace, [_make_snapshot(0, [])])
        frames = list(extractor.stream_file(trace))
        assert frames[0].source_file == str(trace)

    def test_frame_derived_list_preserved(self, extractor, tmp_path):
        trace = tmp_path / "trace_004.jsonl"
        _write_jsonl(trace, [
            _make_snapshot(0, [], derived=["authorized_to_engage(marine_00000041, enemy_00000001)"])
        ])
        frames = list(extractor.stream_file(trace))
        assert "authorized_to_engage(marine_00000041, enemy_00000001)" in frames[0].derived

    def test_empty_file_yields_nothing(self, extractor, tmp_path):
        trace = tmp_path / "trace_empty.jsonl"
        trace.write_text("")
        frames = list(extractor.stream_file(trace))
        assert frames == []

    def test_theory_has_kb_rules(self, extractor, tmp_path):
        """Theory from replay should include the hand-authored KB rules, not just facts."""
        trace = tmp_path / "trace_005.jsonl"
        _write_jsonl(trace, [_make_snapshot(0, ["infantry_unit(marine_1)"])])
        frames = list(extractor.stream_file(trace))
        theory = frames[0].theory
        # KB rules should be present (not just facts)
        assert len(theory.rules) > 0


class TestStreamDirectory:
    def test_streams_multiple_files(self, extractor, tmp_path):
        for i in range(3):
            trace = tmp_path / f"trace_{i:03d}.jsonl"
            _write_jsonl(trace, [_make_snapshot(i * 22, [])])

        frames = list(extractor.stream_directory(tmp_path))
        assert len(frames) == 3

    def test_files_processed_in_sorted_order(self, extractor, tmp_path):
        for step, name in [(22, "trace_b.jsonl"), (0, "trace_a.jsonl"), (44, "trace_c.jsonl")]:
            _write_jsonl(tmp_path / name, [_make_snapshot(step, [])])

        steps = [f.step for f in extractor.stream_directory(tmp_path)]
        assert steps == [0, 22, 44]

    def test_empty_directory_yields_nothing(self, extractor, tmp_path):
        frames = list(extractor.stream_directory(tmp_path))
        assert frames == []


class TestCountConflicts:
    def test_no_conflict_in_clean_trace(self, extractor, tmp_path):
        trace = tmp_path / "trace_clean.jsonl"
        _write_jsonl(trace, [
            _make_snapshot(0, [], derived=["authorized_to_engage(m,e)"])
        ])
        count = extractor.count_conflicts(tmp_path)
        assert count == 0

    def test_conflict_detected_when_both_literal_and_complement(self, extractor, tmp_path):
        trace = tmp_path / "trace_conflict.jsonl"
        _write_jsonl(trace, [
            _make_snapshot(0, [], derived=[
                "authorized_to_engage(m,e)",
                "~authorized_to_engage(m,e)",
            ])
        ])
        count = extractor.count_conflicts(tmp_path)
        assert count == 1


class TestReconstructTheory:
    def test_facts_injected_into_kb_skeleton(self, extractor):
        facts = ["infantry_unit(marine_1)", "in_zone(marine_1, main_base)"]
        theory = extractor._reconstruct_theory(facts)
        assert "infantry_unit(marine_1)" in theory.facts
        assert "in_zone(marine_1, main_base)" in theory.facts

    def test_empty_facts_still_has_kb_rules(self, extractor):
        theory = extractor._reconstruct_theory([])
        assert len(theory.rules) > 0

    def test_does_not_mutate_kb_skeleton(self, extractor):
        original_rule_count = len(extractor._kb_skeleton.rules)
        extractor._reconstruct_theory(["foo(bar)"])
        assert len(extractor._kb_skeleton.rules) == original_rule_count
