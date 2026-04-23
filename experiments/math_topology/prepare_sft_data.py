"""
SFT data preparation for the M2 Lakatos rediscovery positive control.

Emits ``{prompt, completion}`` JSONL pairs suitable for the existing
``experiments/finetuning/train_sft.py`` script.  The prompts are exactly
the L3 prompts from :func:`generate_l3`; the completions are the
gold-defeater Lean expressions from :mod:`lakatos_corpus`.

Held-out hypothesis (default ``h_convex``) is never represented in the
training set; its instances are reserved for
:mod:`evaluate_lakatos`.

Usage:

    python experiments/math_topology/prepare_sft_data.py \
        --output experiments/math_topology/data/lakatos_sft.jsonl

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.math.hypothesis_dropper import DropPolicy, HypothesisDropper

from math_topology.lakatos_corpus import (
    LakatosFixture,
    held_out_fixture,
    training_fixtures,
)


@dataclass(frozen=True)
class SFTRecord:
    prompt: str
    completion: str
    instance_id: str
    theorem_identifier: str
    masked_hypothesis: str
    provenance: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def fixture_to_records(fixture: LakatosFixture) -> list[SFTRecord]:
    dropper = HypothesisDropper(policy=DropPolicy.SINGLE_ANY)
    challenges = dropper.drop(fixture.parent)
    matching = next(
        (c for c in challenges
         if tuple(c.masked_hypotheses) == (fixture.masked,)),
        None,
    )
    if matching is None:
        raise RuntimeError(
            f"no challenge matches masked hypothesis {fixture.masked!r}"
        )
    out: list[SFTRecord] = []
    for d in fixture.gold_defeaters:
        out.append(SFTRecord(
            prompt=matching.prompt,
            completion=d.lean_expr,
            instance_id=f"L3.{fixture.parent.identifier}.{fixture.masked}.{d.provenance}",
            theorem_identifier=fixture.parent.identifier,
            masked_hypothesis=fixture.masked,
            provenance=d.provenance,
        ))
    return out


def build_sft_records(include_held_out: bool = False) -> list[SFTRecord]:
    records: list[SFTRecord] = []
    fixtures = list(training_fixtures())
    if include_held_out:
        fixtures.append(held_out_fixture())
    for f in fixtures:
        records.extend(fixture_to_records(f))
    return records


def write_records(records: list[SFTRecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()))
            f.write("\n")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--include-held-out", action="store_true",
                        help="(unsafe) include the held-out site in training data; "
                        "for negative-control / data-leak experiments only.")
    args = parser.parse_args()
    records = build_sft_records(include_held_out=args.include_held_out)
    n = write_records(records, args.output)
    sys.stdout.write(f"Wrote {n} SFT records to {args.output} "
                     f"(held_out_in_training={args.include_held_out})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
