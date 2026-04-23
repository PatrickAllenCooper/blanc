"""
At-scale hypothesis-dropping driver (M3).

Walks the topology corpus, runs the dropper under a configurable policy,
samples K defeater proposals per challenge from a model interface, scores
every proposal through the Lean harness + novelty filter, and harvests
the Lean-accepted, Mathlib-novel survivors of the trivial-restoration
filter.

The output is the M3 deliverable: a list of candidate defeaters that, in
the language of the project's research thesis, are *Lean-verified
refinements that no existing formalised theorem expresses*.

Usage:

    python experiments/math_topology/at_scale_dropping.py \
        --provider mock \
        --output-dir experiments/math_topology/results/m3_v0/ \
        --samples-per-challenge 8 \
        --policy single_critical

    # Real Foundry runs (M3 production):
    python experiments/math_topology/at_scale_dropping.py \
        --provider foundry-gpt \
        --policy pairs_critical \
        --samples-per-challenge 16 \
        --mathlib-root /path/to/mathlib4 \
        --output-dir experiments/math_topology/results/m3_v1/

The script is GRPO-friendly: per-challenge groups of K samples are
preserved end-to-end, and ``grpo_dataset.py`` consumes the same JSONL.

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

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
    available_harness,
    builtin_corpus,
)
from blanc.math.hypothesis_dropper import ChallengeTheorem, DropPolicy
from blanc.math.lean_harness import LeanHarness
from blanc.math.topology_extractor import MathlibExtractor, TopologyCorpus


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sample provider (mock + ModelInterface)
# ---------------------------------------------------------------------------


class _MockSampler:
    """Deterministic stand-in.  Returns the corpus of plausible defeaters
    for the convex-polytope family plus a noise tail.  Used by tests and
    by ``--dry-run`` style M3 trial runs."""

    name = "mock"

    _CANDIDATES = [
        "P.boundary.genus = 0",
        "EulerCharacteristic P.boundary = 2",
        "IsHomeomorphTo P.boundary (Sphere 2)",
        "IsCompact P.carrier",
        "IsConnected P.carrier",
        "P.dim = 99",
        "P.faces.card \u2265 4",
    ]

    def sample(self, challenge: ChallengeTheorem, n: int) -> list[str]:
        # Cycle deterministically through the candidate pool.
        return [self._CANDIDATES[(i + len(challenge.masked_hypotheses)) % len(self._CANDIDATES)]
                for i in range(n)]


def _build_sampler(name: str) -> Any:
    if name == "mock":
        return _MockSampler()
    import model_interface as mi  # lazy
    table = {
        "foundry-gpt":      mi.FoundryGPT52Interface,
        "foundry-kimi":     mi.FoundryKimiInterface,
        "foundry-claude":   mi.FoundryClaudeInterface,
        "foundry-deepseek": mi.FoundryDeepSeekInterface,
    }
    if name not in table:
        raise ValueError(
            f"unknown sampler {name!r}; pick one of {sorted(table)} or 'mock'."
        )
    return table[name]()


def _sample_responses(provider: Any, challenge: ChallengeTheorem, n: int) -> list[str]:
    if isinstance(provider, _MockSampler):
        return provider.sample(challenge, n)
    out: list[str] = []
    for _ in range(n):
        response = provider.generate(
            challenge.prompt, max_tokens=256, temperature=0.7,
        )
        out.append((response.text if hasattr(response, "text") else str(response)).strip())
    return out


# ---------------------------------------------------------------------------
# Per-row records
# ---------------------------------------------------------------------------


@dataclass
class SampledScore:
    theorem_identifier:    str
    masked:                tuple[str, ...]
    sample_index:          int
    response:              str
    lean_status:           str
    reward:                float
    trivial_restoration:   bool
    matches_mathlib:       bool
    matched_identifier:    str | None
    novelty_distance:      float


@dataclass
class GroupRecord:
    """One challenge's group of K samples (the GRPO unit)."""

    theorem_identifier: str
    masked: tuple[str, ...]
    prompt: str
    samples: list[SampledScore]

    def rewards(self) -> list[float]:
        return [s.reward for s in self.samples]

    def advantages(self) -> list[float]:
        rs = self.rewards()
        if not rs:
            return []
        mean = sum(rs) / len(rs)
        var = sum((r - mean) ** 2 for r in rs) / len(rs)
        std = (var ** 0.5) or 1.0
        return [(r - mean) / std for r in rs]


# ---------------------------------------------------------------------------
# Mock-harness pre-population (deterministic Lean verdicts for the M3 demo)
# ---------------------------------------------------------------------------


def _populate_mock_harness(corpus: TopologyCorpus, harness: MockLeanHarness) -> None:
    """Pre-load the mock harness with verdicts for the M3 candidate pool.

    Real M3 runs use SubprocessLeanHarness against actual Mathlib.  This
    helper exists so the M3 driver runs end-to-end with no Lean install
    and gives the discovery harvester something to harvest.
    """
    accept = LeanStatus.PROVED
    refute = LeanStatus.REFUTED

    accepting_lean_exprs = {
        "P.boundary.genus = 0",
        "EulerCharacteristic P.boundary = 2",
        "IsHomeomorphTo P.boundary (Sphere 2)",
        "IsCompact P.carrier",
        "IsConnected P.carrier",
    }

    for thm in corpus:
        critical = [h for h in thm.hypotheses if h.critical]
        for h in critical:
            masked = (h.name,)
            for expr in accepting_lean_exprs:
                harness.register(thm, Defeater(lean_expr=expr), masked, accept)
            for expr in ("P.dim = 99", "P.faces.card \u2265 4"):
                harness.register(thm, Defeater(lean_expr=expr), masked, refute)
            harness.register(
                thm,
                Defeater(lean_expr=h.lean_expr, provenance="trivial"),
                masked,
                accept,
            )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run_at_scale(
    corpus: TopologyCorpus,
    provider_name: str,
    samples_per_challenge: int,
    policy: DropPolicy,
    output_dir: Path,
    harness: LeanHarness | None = None,
) -> dict[str, Any]:
    if harness is None:
        if provider_name == "mock":
            mock = MockLeanHarness()
            _populate_mock_harness(corpus, mock)
            harness = mock
        else:
            harness = available_harness(prefer_real=True)

    novelty = NoveltyFilter(
        mathlib_statements=[(t.identifier, t.statement) for t in corpus]
    )
    scorer = DefeaterScorer(harness=harness, novelty=novelty)
    sampler = _build_sampler(provider_name)
    dropper = HypothesisDropper(policy=policy)

    output_dir.mkdir(parents=True, exist_ok=True)
    groups_path = output_dir / "groups.jsonl"
    survivors_path = output_dir / "survivors.jsonl"

    n_groups = n_samples = n_lean_accept = n_trivial = n_survivors = 0

    with groups_path.open("w") as gf, survivors_path.open("w") as sf:
        for thm in corpus:
            for challenge in dropper.drop(thm):
                responses = _sample_responses(sampler, challenge, samples_per_challenge)
                samples: list[SampledScore] = []
                for i, resp in enumerate(responses):
                    score = scorer.score(challenge, Defeater(lean_expr=resp, provenance="model"))
                    rec = SampledScore(
                        theorem_identifier=thm.identifier,
                        masked=challenge.masked_hypotheses,
                        sample_index=i,
                        response=resp,
                        lean_status=score.lean.status.value,
                        reward=score.reward,
                        trivial_restoration=score.novelty.is_trivial_restoration,
                        matches_mathlib=score.novelty.matches_mathlib,
                        matched_identifier=score.novelty.matched_identifier,
                        novelty_distance=score.novelty.distance,
                    )
                    samples.append(rec)
                    n_samples += 1
                    if score.lean.accepted:
                        n_lean_accept += 1
                    if score.novelty.is_trivial_restoration:
                        n_trivial += 1
                    if score.lean.accepted and score.novelty.is_novel:
                        n_survivors += 1
                        sf.write(json.dumps({
                            "theorem":          thm.identifier,
                            "masked":           list(challenge.masked_hypotheses),
                            "defeater":         resp,
                            "novelty_distance": score.novelty.distance,
                            "matched_mathlib":  score.novelty.matches_mathlib,
                            "reward":           score.reward,
                        }))
                        sf.write("\n")
                group = GroupRecord(
                    theorem_identifier=thm.identifier,
                    masked=challenge.masked_hypotheses,
                    prompt=challenge.prompt,
                    samples=samples,
                )
                advantages = group.advantages()
                gf.write(json.dumps({
                    "theorem":     thm.identifier,
                    "masked":      list(challenge.masked_hypotheses),
                    "prompt":      challenge.prompt,
                    "samples":     [asdict(s) for s in samples],
                    "advantages":  advantages,
                }))
                gf.write("\n")
                n_groups += 1

    summary = {
        "policy":                policy.value,
        "provider":              provider_name,
        "samples_per_challenge": samples_per_challenge,
        "n_theorems":            len(corpus),
        "n_groups":              n_groups,
        "n_samples":             n_samples,
        "n_lean_accept":         n_lean_accept,
        "n_trivial_restoration": n_trivial,
        "n_survivors":           n_survivors,
        "output_dir":            str(output_dir),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", type=str, default="mock")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--samples-per-challenge", type=int, default=8)
    parser.add_argument("--policy", type=str, default="single_critical",
                        choices=[p.value for p in DropPolicy])
    parser.add_argument("--mathlib-root", type=Path, default=None)
    args = parser.parse_args()

    corpus = builtin_corpus()
    if args.mathlib_root is not None:
        seen = {t.identifier for t in corpus}
        for thm in MathlibExtractor(mathlib_root=args.mathlib_root).extract():
            if thm.identifier not in seen:
                corpus.theorems.append(thm)

    summary = run_at_scale(
        corpus=corpus,
        provider_name=args.provider,
        samples_per_challenge=args.samples_per_challenge,
        policy=DropPolicy(args.policy),
        output_dir=args.output_dir,
    )
    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
