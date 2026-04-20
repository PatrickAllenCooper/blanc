"""
ReplayTraceExtractor: streams replay .jsonl files into theory-state pairs.

Reads trace files written by DeFAbBot.on_end() and yields
(theory_state, observed_orders) pairs suitable for the Author Algorithm.

The extractor reconstructs the Theory for each snapshot by:
    1. Loading the hand-authored RTS engagement KB (strict + defeasible rules)
    2. Re-injecting the snapshot's facts
    3. Returning the reconstituted Theory alongside the observed orders

This allows scripts/generate_sc2live_instances.py to apply the full DeFAb
instance generation pipeline (phi_kappa, generate_level{1,2,3}_instance)
to real game data.

Author: Patrick Cooper
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from blanc.core.theory import Theory


@dataclass
class TraceFrame:
    """
    A single deserialized snapshot from a replay .jsonl file.

    Attributes
    ----------
    step : int
        Game step number.
    theory : Theory
        Reconstituted theory (KB rules + snapshot facts).
    derived : list[str]
        ROE conclusions derived at this step by the live bot.
    orders_issued : list[str]
        SC2 unit orders actually executed.
    source_file : str
        Originating trace file path (for provenance).
    """
    step: int
    theory: Theory
    derived: list[str]
    orders_issued: list[str]
    source_file: str


class ReplayTraceExtractor:
    """
    Streams (theory_state, observed_action) pairs from .jsonl trace files.

    Parameters
    ----------
    kb_theory : Theory | None
        Rule skeleton to inject facts into.  If None, the standard RTS
        engagement KB is loaded (include_instances=False).
    """

    def __init__(self, kb_theory: Theory | None = None) -> None:
        if kb_theory is None:
            from examples.knowledge_bases.rts_engagement_kb import (
                create_rts_engagement_kb,
            )
            kb_theory = create_rts_engagement_kb(include_instances=False)
        self._kb_skeleton = kb_theory

    def stream_file(self, path: Path | str) -> Iterator[TraceFrame]:
        """
        Yield TraceFrame objects from a single .jsonl trace file.

        Parameters
        ----------
        path : Path | str
            Path to a .jsonl trace produced by DeFAbBot.on_end().
        """
        path = Path(path)
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                record = json.loads(line)
                theory = self._reconstruct_theory(record.get("facts", []))
                yield TraceFrame(
                    step=record.get("step", 0),
                    theory=theory,
                    derived=record.get("derived", []),
                    orders_issued=record.get("orders_issued", []),
                    source_file=str(path),
                )

    def stream_directory(self, directory: Path | str) -> Iterator[TraceFrame]:
        """
        Yield TraceFrame objects from all .jsonl files in a directory.

        Files are processed in sorted order for reproducibility.
        """
        directory = Path(directory)
        for path in sorted(directory.glob("*.jsonl")):
            yield from self.stream_file(path)

    def count_conflicts(self, directory: Path | str) -> int:
        """
        Count the number of defeasible conflicts across all traces.

        A conflict is a step where the derived set contains both a literal
        and its complement (indicating an unresolved conflict before the
        DefeasibleEngine resolves it via superiority).  Useful for estimating
        DPO dataset size before running mine_sc2_conflicts.py.
        """
        count = 0
        for frame in self.stream_directory(directory):
            derived_set = set(frame.derived)
            for lit in frame.derived:
                if lit.startswith("~") and lit[1:] in derived_set:
                    count += 1
                    break  # one conflict per frame
        return count

    def _reconstruct_theory(self, facts: list[str]) -> Theory:
        """Inject a snapshot's facts into the KB skeleton."""
        import copy
        theory = copy.deepcopy(self._kb_skeleton)
        for fact in facts:
            theory.add_fact(fact)
        return theory
