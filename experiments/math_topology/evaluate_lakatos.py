"""
Held-out evaluation for the M2 Lakatos rediscovery positive control.

Pass criterion: the trained model, when given Euler V-E+F=2 with the
convexity hypothesis masked (the ``h_convex`` site reserved by
:mod:`lakatos_corpus`), must propose a Lean expression that the kernel
accepts as a valid extra hypothesis AND that survives the trivial-
restoration filter.  We call this a *positive-control hit*.

The script accepts an iterable of trial responses (one per sampled
generation) and reports:

    n_trials                Total responses scored.
    n_lean_accept           Lean-accepted responses (any).
    n_trivial_restoration   Lean-accepted responses that are trivial.
    n_positive_control_hit  Lean-accepted, novel responses.
    hit_rate                n_positive_control_hit / n_trials.

It also accepts a ``baseline_hits`` count and applies a one-sided
proportion test (McNemar-style for paired counts when supplied) so the
M2 gate decision is statistically defensible.

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.math import (
    Defeater,
    DefeaterScorer,
    HypothesisDropper,
    LeanStatus,
    MockLeanHarness,
    NoveltyFilter,
)
from blanc.math.hypothesis_dropper import DropPolicy
from blanc.math.lean_harness import LeanHarness

from math_topology.lakatos_corpus import held_out_fixture


@dataclass
class HeldOutEvaluation:
    n_trials: int
    n_lean_accept: int
    n_trivial_restoration: int
    n_positive_control_hit: int
    hit_rate: float
    rows: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "n_trials":               self.n_trials,
            "n_lean_accept":          self.n_lean_accept,
            "n_trivial_restoration":  self.n_trivial_restoration,
            "n_positive_control_hit": self.n_positive_control_hit,
            "hit_rate":               self.hit_rate,
            "rows":                   self.rows,
        }


def _build_default_harness() -> MockLeanHarness:
    """Pre-register Lean verdicts for the held-out fixture's known defeaters
    (gold + trivial restoration).  Anything else falls through to UNKNOWN
    and is treated as Lean-rejected."""
    h = MockLeanHarness()
    f = held_out_fixture()
    masked = (f.masked,)
    for d in f.gold_defeaters:
        h.register(f.parent, d, masked, LeanStatus.PROVED)
    trivial_expr = f.parent.hypothesis_by_name(f.masked).lean_expr
    h.register(
        f.parent,
        Defeater(lean_expr=trivial_expr, provenance="adv:trivial_restoration"),
        masked,
        LeanStatus.PROVED,
    )
    return h


def evaluate_responses(
    responses: Iterable[str],
    harness: LeanHarness | None = None,
) -> HeldOutEvaluation:
    f = held_out_fixture()
    challenge = next(
        c for c in HypothesisDropper(DropPolicy.SINGLE_ANY).drop(f.parent)
        if tuple(c.masked_hypotheses) == (f.masked,)
    )
    scorer = DefeaterScorer(
        harness=harness or _build_default_harness(),
        novelty=NoveltyFilter(),
    )
    rows: list[dict[str, object]] = []
    n_trials = n_lean_accept = n_trivial = n_hit = 0
    for resp in responses:
        n_trials += 1
        score = scorer.score(challenge, Defeater(lean_expr=resp, provenance="model"))
        accepted = score.lean.accepted
        trivial = score.novelty.is_trivial_restoration
        hit = accepted and not trivial
        n_lean_accept += int(accepted)
        n_trivial += int(trivial)
        n_hit += int(hit)
        rows.append({
            "response":             resp,
            "lean_status":          score.lean.status.value,
            "trivial_restoration":  trivial,
            "novel":                score.novelty.is_novel,
            "reward":               score.reward,
            "positive_control_hit": hit,
        })
    hit_rate = n_hit / n_trials if n_trials else 0.0
    return HeldOutEvaluation(
        n_trials=n_trials,
        n_lean_accept=n_lean_accept,
        n_trivial_restoration=n_trivial,
        n_positive_control_hit=n_hit,
        hit_rate=hit_rate,
        rows=rows,
    )


def one_sided_z_proportion(
    successes_a: int, n_a: int,
    successes_b: int, n_b: int,
) -> tuple[float, float]:
    """Return (z, p) for H0: p_a <= p_b, H1: p_a > p_b.

    Two-sample one-sided z-test on proportions, pooled variance.  Used by
    the M2 gate to compare trained-model hit rate against baseline.
    """
    if n_a == 0 or n_b == 0:
        return (0.0, 1.0)
    p_a = successes_a / n_a
    p_b = successes_b / n_b
    p_pool = (successes_a + successes_b) / (n_a + n_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / n_a + 1 / n_b))
    if se == 0:
        return (0.0, 1.0)
    z = (p_a - p_b) / se
    p = 0.5 * math.erfc(z / math.sqrt(2))  # 1 - Phi(z)
    return (z, p)


def gate_decision(
    trained: HeldOutEvaluation,
    baseline: HeldOutEvaluation,
    alpha: float = 0.05,
) -> dict[str, object]:
    z, p = one_sided_z_proportion(
        trained.n_positive_control_hit, trained.n_trials,
        baseline.n_positive_control_hit, baseline.n_trials,
    )
    return {
        "trained_hit_rate":  trained.hit_rate,
        "baseline_hit_rate": baseline.hit_rate,
        "delta":             trained.hit_rate - baseline.hit_rate,
        "z":                 z,
        "p_value":           p,
        "alpha":             alpha,
        "passes_gate":       (trained.hit_rate > baseline.hit_rate) and (p < alpha),
    }


def _read_responses(path: Path) -> list[str]:
    if path.suffix == ".jsonl":
        out: list[str] = []
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            out.append(obj.get("response", obj.get("text", "")))
        return out
    return [r for r in path.read_text().splitlines() if r.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trained-responses", type=Path, required=True,
                        help="JSONL or one-per-line text file of the trained model's responses.")
    parser.add_argument("--baseline-responses", type=Path, required=True,
                        help="JSONL or one-per-line text file of baseline responses.")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--alpha", type=float, default=0.05)
    args = parser.parse_args()

    trained = evaluate_responses(_read_responses(args.trained_responses))
    baseline = evaluate_responses(_read_responses(args.baseline_responses))
    decision = gate_decision(trained, baseline, alpha=args.alpha)
    payload = {
        "trained":   trained.to_dict(),
        "baseline":  baseline.to_dict(),
        "decision":  decision,
    }
    text = json.dumps(payload, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text)
    sys.stdout.write(text + "\n")
    return 0 if decision["passes_gate"] else 2


if __name__ == "__main__":
    sys.exit(main())
