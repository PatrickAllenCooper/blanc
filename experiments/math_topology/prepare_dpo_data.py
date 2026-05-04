"""
DPO preference-data preparation for the M2 Lakatos rediscovery loop.

Implements margin-weighted DPO at the math level: each (prompt, chosen,
rejected) pair carries a ``margin`` equal to the conservativity / novelty
gap between chosen and rejected, scored by :class:`DefeaterScorer`.

Pair construction policy (rich enough for a small corpus):

    -- For each non-held-out Lakatos fixture, every gold defeater pairs
       against every distractor (gold = chosen, distractor = rejected).
    -- For each gold defeater, the dropped hypothesis itself (trivial
       restoration) is constructed and added as a *rejected* example,
       teaching the model not to memorise the masked hypothesis.

Margins are derived from :class:`DefeaterScorer.compute_reward`, so the
weights are exactly the verifier-aligned ones the loss should put gradient
on (see paper Section 6.2 -- margin-weighted DPO).

Author: Anonymous Authors
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

from blanc.math import (
    Defeater,
    DefeaterScorer,
    LeanStatus,
    MockLeanHarness,
    NoveltyFilter,
)
from blanc.math.hypothesis_dropper import DropPolicy, HypothesisDropper
from blanc.math.lean_harness import LeanHarness

from math_topology.lakatos_corpus import (
    LakatosFixture,
    training_fixtures,
)


@dataclass(frozen=True)
class DPORecord:
    prompt: str
    chosen: str
    rejected: str
    margin: float
    instance_id: str
    theorem_identifier: str
    masked_hypothesis: str
    chosen_provenance: str
    rejected_provenance: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _populate_default_lean_verdicts(
    fixtures: list[LakatosFixture],
    harness: MockLeanHarness,
) -> None:
    """Pre-load mock harness with verdicts for every gold/distractor/trivial.

    Real-Lean runs swap in :class:`SubprocessLeanHarness`; this helper exists
    so the prep step is meaningful in CI without a Lean install.
    """
    for f in fixtures:
        masked = (f.masked,)
        for d in f.gold_defeaters:
            harness.register(f.parent, d, masked, LeanStatus.PROVED)
        for d in f.distractors:
            harness.register(f.parent, d, masked, LeanStatus.REFUTED)
        trivial_expr = f.parent.hypothesis_by_name(f.masked).lean_expr
        harness.register(
            f.parent,
            Defeater(lean_expr=trivial_expr, provenance="adv:trivial_restoration"),
            masked,
            LeanStatus.PROVED,
        )


def build_dpo_records(harness: LeanHarness | None = None) -> list[DPORecord]:
    fixtures = list(training_fixtures())
    if harness is None:
        mock = MockLeanHarness()
        _populate_default_lean_verdicts(fixtures, mock)
        harness = mock
    scorer = DefeaterScorer(harness=harness, novelty=NoveltyFilter())
    dropper = HypothesisDropper(policy=DropPolicy.SINGLE_ANY)

    records: list[DPORecord] = []
    for f in fixtures:
        challenge = next(
            (c for c in dropper.drop(f.parent)
             if tuple(c.masked_hypotheses) == (f.masked,)),
            None,
        )
        if challenge is None:
            continue

        gold_scores = [(g, scorer.score(challenge, g)) for g in f.gold_defeaters]
        distractor_scores = [(d, scorer.score(challenge, d)) for d in f.distractors]

        trivial_def = Defeater(
            lean_expr=f.parent.hypothesis_by_name(f.masked).lean_expr,
            provenance="adv:trivial_restoration",
        )
        trivial_score = scorer.score(challenge, trivial_def)

        for gold, gs in gold_scores:
            for distractor, ds in distractor_scores:
                margin = gs.reward - ds.reward
                if margin <= 0:
                    continue
                records.append(DPORecord(
                    prompt=challenge.prompt,
                    chosen=gold.lean_expr,
                    rejected=distractor.lean_expr,
                    margin=float(margin),
                    instance_id=f"L3.{f.parent.identifier}.{f.masked}.{gold.provenance}.vs.{distractor.provenance}",
                    theorem_identifier=f.parent.identifier,
                    masked_hypothesis=f.masked,
                    chosen_provenance=gold.provenance,
                    rejected_provenance=distractor.provenance,
                ))
            margin_trivial = gs.reward - trivial_score.reward
            if margin_trivial > 0:
                records.append(DPORecord(
                    prompt=challenge.prompt,
                    chosen=gold.lean_expr,
                    rejected=trivial_def.lean_expr,
                    margin=float(margin_trivial),
                    instance_id=f"L3.{f.parent.identifier}.{f.masked}.{gold.provenance}.vs.trivial",
                    theorem_identifier=f.parent.identifier,
                    masked_hypothesis=f.masked,
                    chosen_provenance=gold.provenance,
                    rejected_provenance=trivial_def.provenance,
                ))
    return records


def write_records(records: list[DPORecord], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r.to_dict()))
            f.write("\n")
    return len(records)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--harness", choices=["mock", "lean_interact"], default="mock",
        help="Which Lean harness to use for scoring gold/distractor defeaters. "
             "'mock' uses pre-registered verdicts (default, no Lean required). "
             "'lean_interact' calls a real Lean 4 REPL via lean-interact.",
    )
    args = parser.parse_args()

    if args.harness == "lean_interact":
        from blanc.math.lean_harness import LeanInteractHarness  # noqa: WPS433
        lean_dir = ROOT / "lean"
        h: LeanHarness = LeanInteractHarness(
            lean_version="v4.25.0",
            project_dir=lean_dir if lean_dir.exists() else None,
        )
    else:
        h = None  # build_dpo_records uses MockLeanHarness by default

    records = build_dpo_records(harness=h)
    n = write_records(records, args.output)
    sys.stdout.write(f"Wrote {n} DPO records to {args.output} (harness={args.harness})\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
