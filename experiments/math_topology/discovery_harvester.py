"""
Discovery harvester (M3 deliverable).

Reads the per-challenge ``survivors.jsonl`` written by
:mod:`at_scale_dropping`, deduplicates Lean-accepted, Mathlib-novel
defeaters, and ranks them by novelty distance + Lean reward.  The output
is the M3 deliverable: the list of candidate refinements that survive the
trivial-restoration filter and are not already expressible in Mathlib.

A second pass groups discoveries by parent theorem and counts
(per-theorem, per-mask) survivor unique-defeater counts so the discovery
yield can be tracked across runs.

Subsequent (deferred) M4 work runs literature filtering -- ArXiv,
MathOverflow, textbook -- against this same JSONL to identify the
human-mathematics-novel subset.

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

from blanc.math.novelty import normalised_lean_expr


@dataclass(frozen=True)
class Discovery:
    theorem_identifier: str
    masked: tuple[str, ...]
    defeater: str
    normalised: str
    novelty_distance: float
    reward: float
    n_observations: int = 1

    def to_dict(self) -> dict[str, object]:
        out = asdict(self)
        out["masked"] = list(self.masked)
        return out


@dataclass
class HarvestSummary:
    n_input_rows:         int
    n_unique_discoveries: int
    by_theorem:           dict[str, int] = field(default_factory=dict)
    by_mask:              dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _load_survivors(survivors_jsonl: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    if not survivors_jsonl.exists():
        return rows
    for line in survivors_jsonl.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def harvest(survivors_jsonl: Path) -> tuple[list[Discovery], HarvestSummary]:
    rows = _load_survivors(survivors_jsonl)
    by_key: dict[tuple[str, tuple[str, ...], str], Discovery] = {}
    for r in rows:
        masked = tuple(r["masked"])
        defeater = str(r["defeater"]).strip()
        if not defeater:
            continue
        normalised = normalised_lean_expr(defeater)
        key = (str(r["theorem"]), masked, normalised)
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = Discovery(
                theorem_identifier=str(r["theorem"]),
                masked=masked,
                defeater=defeater,
                normalised=normalised,
                novelty_distance=float(r["novelty_distance"]),
                reward=float(r["reward"]),
            )
        else:
            by_key[key] = Discovery(
                theorem_identifier=existing.theorem_identifier,
                masked=existing.masked,
                defeater=existing.defeater,
                normalised=existing.normalised,
                novelty_distance=max(existing.novelty_distance, float(r["novelty_distance"])),
                reward=max(existing.reward, float(r["reward"])),
                n_observations=existing.n_observations + 1,
            )
    discoveries = sorted(
        by_key.values(),
        key=lambda d: (-(d.reward), -d.novelty_distance, d.defeater),
    )
    summary = HarvestSummary(
        n_input_rows=len(rows),
        n_unique_discoveries=len(discoveries),
        by_theorem=dict(Counter(d.theorem_identifier for d in discoveries)),
        by_mask=dict(Counter(",".join(d.masked) for d in discoveries)),
    )
    return discoveries, summary


def write_discoveries(discoveries: Iterable[Discovery], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for d in discoveries:
            f.write(json.dumps(d.to_dict()))
            f.write("\n")
            n += 1
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--survivors", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, default=None)
    args = parser.parse_args()
    discoveries, summary = harvest(args.survivors)
    n = write_discoveries(discoveries, args.output)
    summary_path = args.summary or args.output.with_suffix(".summary.json")
    summary_path.write_text(json.dumps(summary.to_dict(), indent=2))
    sys.stdout.write(
        f"Harvested {n} unique discoveries from {summary.n_input_rows} rows; "
        f"{len(summary.by_theorem)} theorems represented.\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
