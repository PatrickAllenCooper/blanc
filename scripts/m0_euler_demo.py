"""
M0 single-example end-to-end demo for DeFAb-Math-Topology.

Runs the full pipeline -- topology corpus, hypothesis dropping, defeater
scoring against a (mock) Lean kernel, novelty filter -- on the Euler
V - E + F = 2 / genus example.  Validates that all M0 surfaces compose
without a real Lean install.

Usage:
    python scripts/m0_euler_demo.py

When a real ``lean`` binary is on PATH and ``--real-lean`` is supplied,
the demo swaps in :class:`SubprocessLeanHarness`.  The remainder of the
pipeline is identical.

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blanc.math import (
    Defeater,
    DefeaterScorer,
    HypothesisDropper,
    LeanStatus,
    MockLeanHarness,
    NoveltyFilter,
    SubprocessLeanHarness,
    builtin_corpus,
)
from blanc.math.hypothesis_dropper import DropPolicy


def build_mock_harness(corpus_theorem_id: str) -> MockLeanHarness:
    """Pre-load the mock harness with verdicts for the Euler / genus example.

    Three defeaters per ablation:
        1. ``trivial_restoration`` -- the dropped hypothesis verbatim
           (Lean accepts but the novelty filter must reject this).
        2. ``genus_zero``          -- the canonical Lakatos refinement
           (Lean accepts, novel).
        3. ``garbage``             -- a syntactically valid but unrelated
           proposal (Lean rejects).
    """
    harness = MockLeanHarness()
    corpus = builtin_corpus()
    parent = corpus.by_id(corpus_theorem_id)

    for masked_name in ("h_convex", "h_bounded", "h_simply_connected"):
        masked = (masked_name,)

        trivial = Defeater(
            lean_expr=parent.hypothesis_by_name(masked_name).lean_expr,
            natural_language="(restating the dropped hypothesis verbatim)",
            provenance="adversarial:trivial_restoration",
        )
        harness.register(parent, trivial, masked, LeanStatus.PROVED,
                         message="re-introducing the dropped hypothesis closes the goal")

        genus_zero = Defeater(
            lean_expr="P.boundary.genus = 0",
            natural_language="The polytope's surface has genus zero.",
            provenance="harvest:lakatos",
        )
        harness.register(parent, genus_zero, masked, LeanStatus.PROVED,
                         message="genus-zero suffices for V - E + F = 2")

        garbage = Defeater(
            lean_expr="P.vertices.card = 17",
            natural_language="The polytope has exactly 17 vertices.",
            provenance="adversarial:noise",
        )
        harness.register(parent, garbage, masked, LeanStatus.REFUTED,
                         message="not enough information to discharge the goal")

    return harness


def run(real_lean: bool, output: Path | None) -> dict[str, object]:
    corpus = builtin_corpus()
    target = "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"

    if real_lean:
        harness = SubprocessLeanHarness()
    else:
        harness = build_mock_harness(target)

    dropper = HypothesisDropper(policy=DropPolicy.SINGLE_CRITICAL)
    novelty = NoveltyFilter(
        mathlib_statements=[
            (t.identifier, t.statement)
            for t in corpus
            if t.identifier != target
        ]
    )
    scorer = DefeaterScorer(harness=harness, novelty=novelty)

    parent = corpus.by_id(target)
    challenges = dropper.drop(parent)

    candidate_defeaters = [
        Defeater(lean_expr="P.boundary.genus = 0",
                 natural_language="genus-zero surface",
                 provenance="harvest:lakatos"),
        Defeater(lean_expr=parent.hypothesis_by_name("h_convex").lean_expr,
                 natural_language="(restating dropped hypothesis)",
                 provenance="adversarial:trivial_restoration"),
        Defeater(lean_expr="P.vertices.card = 17",
                 natural_language="polytope has 17 vertices",
                 provenance="adversarial:noise"),
    ]

    rows: list[dict[str, object]] = []
    for challenge in challenges:
        for defeater in candidate_defeaters:
            score = scorer.score(challenge, defeater)
            rows.append({
                "theorem":              parent.identifier,
                "masked":               list(challenge.masked_hypotheses),
                "defeater_lean":        defeater.lean_expr,
                "defeater_provenance":  defeater.provenance,
                "lean_status":          score.lean.status.value,
                "trivial_restoration":  score.novelty.is_trivial_restoration,
                "matches_mathlib":      score.novelty.matches_mathlib,
                "novelty_distance":     round(score.novelty.distance, 3),
                "reward":               round(score.reward, 3),
            })

    summary = {
        "theorem":           target,
        "n_challenges":      len(challenges),
        "n_defeaters":       len(candidate_defeaters),
        "n_rows":            len(rows),
        "rows":              rows,
        "passed_acceptance": all(
            (r["lean_status"] == "proved" and not r["trivial_restoration"])
            == (r["reward"] > 0)
            for r in rows
        ),
    }
    if output is not None:
        output.write_text(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--real-lean", action="store_true",
                        help="Use SubprocessLeanHarness (requires `lean` on PATH).")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write the summary JSON here.")
    args = parser.parse_args()

    summary = run(real_lean=args.real_lean, output=args.output)

    sys.stdout.write(
        f"M0 demo: theorem={summary['theorem']}, "
        f"challenges={summary['n_challenges']}, "
        f"defeaters={summary['n_defeaters']}, "
        f"rows={summary['n_rows']}, "
        f"acceptance_invariant_holds={summary['passed_acceptance']}\n"
    )
    accepted_novel = [
        r for r in summary["rows"]
        if r["reward"] > 0 and not r["trivial_restoration"]
    ]
    sys.stdout.write(
        f"  Lean-accepted, novel defeaters: {len(accepted_novel)} / {summary['n_rows']}\n"
    )
    if not summary["passed_acceptance"]:
        sys.stderr.write("ERROR: acceptance invariant violated.\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
