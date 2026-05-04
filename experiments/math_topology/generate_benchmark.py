"""
DeFAb-Math-Topology benchmark generator (M1).

Produces L1 / L2 / L3 instances from a ``TopologyCorpus``.  Targets are
~500 L1, ~300 L2, ~100 L3 once a real Mathlib clone supplies the corpus
(see ``--mathlib-root``).  Against the curated builtin corpus (~13
theorems with ~50 hypotheses) the generator yields a smaller but
schema-valid benchmark that exercises the full loader / scorer round-trip.

Generation policy:

    L1 -- one instance per (theorem, non-critical hypothesis).  The
        non-critical hypothesis is masked from the prompt and becomes
        gold.

    L2 -- one instance per theorem.  The statement is the gold; the
        prompt withholds it and supplies hypotheses + natural-language
        hint.

    L3 -- one instance per (theorem, critical hypothesis).  The critical
        hypothesis is masked; gold is the dropped hypothesis itself
        (always Lean-accepted) plus any registered refinements.

Usage:

    python experiments/math/generate_benchmark.py \
        --output-dir experiments/math/data/v0/ \
        --seed 17

    # Scale to Mathlib once a clone is available:
    python experiments/math/generate_benchmark.py \
        --output-dir experiments/math/data/v1/ \
        --mathlib-root /path/to/mathlib4

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.math import builtin_corpus
from blanc.math.topology_extractor import MathlibExtractor, TopologyCorpus
from blanc.math.types import MathTheorem

from math_topology.topology_instance import TopologyInstance, write_jsonl


@dataclass
class BenchmarkCounts:
    l1: int
    l2: int
    l3: int

    def total(self) -> int:
        return self.l1 + self.l2 + self.l3

    def to_dict(self) -> dict[str, int]:
        return {"l1": self.l1, "l2": self.l2, "l3": self.l3, "total": self.total()}


# ---------------------------------------------------------------------------
# Per-level generators
# ---------------------------------------------------------------------------


def _theorem_metadata(thm: MathTheorem) -> dict[str, str]:
    return {
        "natural_language": thm.natural_language,
        "source_path":      thm.source_path or "",
    }


def generate_l1(theorem: MathTheorem) -> list[TopologyInstance]:
    """One L1 row per non-critical hypothesis."""
    out: list[TopologyInstance] = []
    non_critical = [h for h in theorem.hypotheses if not h.critical]
    for h in non_critical:
        masked = (h.name,)
        retained = [r for r in theorem.hypotheses if r.name != h.name]
        retained_str = "; ".join(f"{r.name} : {r.lean_expr}" for r in retained) or "(none)"
        prompt = (
            "Mathlib theorem: "
            f"{theorem.natural_language or theorem.identifier}\n"
            f"Conclusion: {theorem.statement}\n"
            f"Available hypotheses: {retained_str}\n"
            f"Removed hypothesis name: {h.name}\n"
            "Propose the missing hypothesis (Lean expression).  This must be "
            "exactly the standard Mathlib hypothesis, not a creative refinement."
        )
        out.append(TopologyInstance(
            instance_id=f"L1.{theorem.identifier}.{h.name}",
            level=1,
            theorem_identifier=theorem.identifier,
            theorem_statement=theorem.statement,
            hypotheses=theorem.hypotheses,
            masked_hypotheses=masked,
            gold=(h.lean_expr,),
            prompt=prompt,
            metadata=_theorem_metadata(theorem),
        ))
    return out


def generate_l2(theorem: MathTheorem) -> list[TopologyInstance]:
    """One L2 row per theorem (statement is the gold)."""
    binders = "; ".join(f"{h.name} : {h.lean_expr}" for h in theorem.hypotheses) or "(none)"
    prompt = (
        f"Mathlib context: {theorem.natural_language or theorem.identifier}\n"
        f"Hypotheses: {binders}\n"
        "Propose the conclusion (the Lean expression on the right of `:`).  "
        "Match the Mathlib statement exactly."
    )
    return [TopologyInstance(
        instance_id=f"L2.{theorem.identifier}",
        level=2,
        theorem_identifier=theorem.identifier,
        theorem_statement=theorem.statement,
        hypotheses=theorem.hypotheses,
        masked_hypotheses=(),
        gold=(theorem.statement,),
        prompt=prompt,
        metadata=_theorem_metadata(theorem),
    )]


def generate_l3(theorem: MathTheorem) -> list[TopologyInstance]:
    """One L3 row per critical hypothesis."""
    out: list[TopologyInstance] = []
    critical = [h for h in theorem.hypotheses if h.critical]
    for h in critical:
        masked = (h.name,)
        retained = [r for r in theorem.hypotheses if r.name != h.name]
        retained_str = "; ".join(f"{r.name} : {r.lean_expr}" for r in retained) or "(none)"
        prompt = (
            f"Theorem under consideration: {theorem.natural_language or theorem.identifier}\n"
            f"Conclusion: {theorem.statement}\n"
            f"Available hypotheses: {retained_str}\n"
            f"Removed hypothesis: {h.name}\n"
            "Propose a strictly weaker extra hypothesis (a defeater) that the "
            "Lean kernel will accept as sufficient to re-prove the conclusion.  "
            "Do not simply restate the removed hypothesis."
        )
        out.append(TopologyInstance(
            instance_id=f"L3.{theorem.identifier}.{h.name}",
            level=3,
            theorem_identifier=theorem.identifier,
            theorem_statement=theorem.statement,
            hypotheses=theorem.hypotheses,
            masked_hypotheses=masked,
            gold=(h.lean_expr,),
            prompt=prompt,
            metadata=_theorem_metadata(theorem),
        ))
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def generate_benchmark(
    corpus: TopologyCorpus,
    seed: int = 17,
    cap_l1: Optional[int] = None,
    cap_l2: Optional[int] = None,
    cap_l3: Optional[int] = None,
) -> tuple[list[TopologyInstance], list[TopologyInstance], list[TopologyInstance]]:
    rng = random.Random(seed)
    l1: list[TopologyInstance] = []
    l2: list[TopologyInstance] = []
    l3: list[TopologyInstance] = []
    for thm in corpus:
        l1.extend(generate_l1(thm))
        l2.extend(generate_l2(thm))
        l3.extend(generate_l3(thm))
    rng.shuffle(l1)
    rng.shuffle(l2)
    rng.shuffle(l3)
    if cap_l1 is not None:
        l1 = l1[:cap_l1]
    if cap_l2 is not None:
        l2 = l2[:cap_l2]
    if cap_l3 is not None:
        l3 = l3[:cap_l3]
    return l1, l2, l3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--mathlib-root", type=Path, default=None,
                        help="If set, supplements the builtin corpus with extracted Mathlib theorems.")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--cap-l1", type=int, default=None)
    parser.add_argument("--cap-l2", type=int, default=None)
    parser.add_argument("--cap-l3", type=int, default=None)
    args = parser.parse_args()

    corpus = builtin_corpus()
    if args.mathlib_root is not None:
        extra = MathlibExtractor(mathlib_root=args.mathlib_root).extract()
        existing_ids = {t.identifier for t in corpus}
        for thm in extra:
            if thm.identifier in existing_ids:
                continue
            corpus.theorems.append(thm)

    l1, l2, l3 = generate_benchmark(
        corpus, seed=args.seed,
        cap_l1=args.cap_l1, cap_l2=args.cap_l2, cap_l3=args.cap_l3,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    counts = BenchmarkCounts(
        l1=write_jsonl(l1, args.output_dir / "l1.jsonl"),
        l2=write_jsonl(l2, args.output_dir / "l2.jsonl"),
        l3=write_jsonl(l3, args.output_dir / "l3.jsonl"),
    )
    (args.output_dir / "counts.json").write_text(json.dumps(counts.to_dict(), indent=2))
    sys.stdout.write(f"Wrote {counts.total()} instances to {args.output_dir}: "
                     f"L1={counts.l1}, L2={counts.l2}, L3={counts.l3}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
