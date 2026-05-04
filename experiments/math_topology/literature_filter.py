"""
Literature filter for the M4 (deferred) phase.

Takes the discovery JSONL produced by :mod:`discovery_harvester` and
classifies each candidate as one of:

    HUMAN_NOVEL    -- no hit in ArXiv / MathOverflow / textbook indices.
    HUMAN_KNOWN    -- a hit was found; the candidate names a known
                      mathematical refinement.
    UNCERTAIN      -- the filter could not produce a confident verdict.

The contract is provider-agnostic.  M4 production work will subclass
:class:`LiteratureFilter` with a real index integration (Semantic
Scholar API, MathOverflow scraper, an embedded textbook catalog).

This module ships with two concrete filters:

    StubLiteratureFilter        -- deterministic in-memory backend used
                                   by tests; carries an explicit known-set
                                   so the contract can be exercised.

    DeferredLiteratureFilter    -- the M4-deferred placeholder; raises
                                   NotImplementedError on calls so
                                   downstream code cannot silently treat
                                   it as a real filter.

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterable

from blanc.math.novelty import normalised_lean_expr


class HumanNoveltyLabel(str, Enum):
    HUMAN_NOVEL = "human_novel"
    HUMAN_KNOWN = "human_known"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True)
class LiteratureVerdict:
    label: HumanNoveltyLabel
    confidence: float = 0.0
    matched_source: str | None = None
    matched_title: str | None = None


class LiteratureFilter(ABC):
    """Abstract M4 literature filter."""

    @abstractmethod
    def classify(self, defeater_lean: str, defeater_natural_language: str = "") -> LiteratureVerdict:
        """Return a verdict for one candidate defeater."""

    def classify_jsonl(
        self,
        discoveries_jsonl: Path,
        output: Path,
    ) -> dict[str, int]:
        counts = {label.value: 0 for label in HumanNoveltyLabel}
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w") as out_f:
            for line in discoveries_jsonl.read_text().splitlines():
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                verdict = self.classify(
                    row.get("defeater", ""),
                    row.get("natural_language", ""),
                )
                counts[verdict.label.value] += 1
                row.update({
                    "human_novelty_label":   verdict.label.value,
                    "human_novelty_confidence": verdict.confidence,
                    "matched_source":        verdict.matched_source,
                    "matched_title":         verdict.matched_title,
                })
                out_f.write(json.dumps(row))
                out_f.write("\n")
        return counts


# ---------------------------------------------------------------------------
# Stub backend (tests + contract validation)
# ---------------------------------------------------------------------------


@dataclass
class StubLiteratureFilter(LiteratureFilter):
    """In-memory filter with an explicit known-set.

    Anything in ``known_index`` (keyed by normalised Lean expression) is
    HUMAN_KNOWN; everything else is HUMAN_NOVEL.  The stub never returns
    UNCERTAIN -- subclasses with real indices should.
    """

    known_index: dict[str, tuple[str, str]] = field(default_factory=dict)

    def classify(
        self,
        defeater_lean: str,
        defeater_natural_language: str = "",
    ) -> LiteratureVerdict:
        normal = normalised_lean_expr(defeater_lean)
        hit = self.known_index.get(normal)
        if hit is None:
            return LiteratureVerdict(label=HumanNoveltyLabel.HUMAN_NOVEL, confidence=1.0)
        source, title = hit
        return LiteratureVerdict(
            label=HumanNoveltyLabel.HUMAN_KNOWN,
            confidence=1.0,
            matched_source=source,
            matched_title=title,
        )


# ---------------------------------------------------------------------------
# Deferred placeholder (the actual M4 plug-in lives here later)
# ---------------------------------------------------------------------------


class DeferredLiteratureFilter(LiteratureFilter):
    """The real M4 filter is intentionally not implemented in this session.

    The M4 plan calls for ArXiv / MathOverflow / textbook integration; that
    is follow-on work and would silently mislead downstream code if stubbed
    in.  This class exists so the import works and the contract is visible;
    calling :meth:`classify` raises ``NotImplementedError`` immediately.
    """

    def classify(
        self,
        defeater_lean: str,
        defeater_natural_language: str = "",
    ) -> LiteratureVerdict:
        raise NotImplementedError(
            "M4 literature filter is deferred per the research agenda; "
            "use StubLiteratureFilter for contract tests, or implement an "
            "ArXiv / MathOverflow / textbook backend."
        )


# ---------------------------------------------------------------------------
# CLI (kept thin; production use will swap StubLiteratureFilter)
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--discoveries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--stub-known", type=Path, default=None,
                        help="Optional JSON file mapping normalised expr -> [source, title].")
    args = parser.parse_args()

    known: dict[str, tuple[str, str]] = {}
    if args.stub_known is not None:
        raw = json.loads(args.stub_known.read_text())
        known = {k: (v[0], v[1]) for k, v in raw.items()}
    counts = StubLiteratureFilter(known_index=known).classify_jsonl(
        args.discoveries, args.output,
    )
    sys.stdout.write(json.dumps(counts, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
