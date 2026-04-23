"""
Four-model baseline runner for DeFAb-Math-Topology (M1).

Drives the existing ``model_interface`` panel against a generated benchmark
and grades responses:

    L1 / L2 -- exact match (after normalisation) of the model response
        against the gold Lean expression / statement.

    L3      -- the parsed Lean expression is fed to the project's
        :class:`DefeaterScorer` and graded by the Lean harness + novelty
        filter.  Reward in [0, 1] is reported alongside per-row Lean status.

The runner is provider-agnostic by design: it accepts ``--provider mock``
(deterministic stub) for tests and CI, ``--provider foundry-{gpt,kimi,
claude,deepseek}`` for the four-model panel, and ``--provider curc`` for
the local vLLM tunnel.  See ``model_interface.py`` for the full set.

Usage:

    python experiments/math/run_baseline.py \
        --benchmark experiments/math/data/v0/ \
        --provider mock \
        --output-dir experiments/math/results/v0/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.math import (
    Defeater,
    DefeaterScorer,
    HypothesisDropper,
    MockLeanHarness,
    NoveltyFilter,
    available_harness,
)
from blanc.math.hypothesis_dropper import DropPolicy
from blanc.math.lean_harness import LeanHarness
from blanc.math.novelty import normalised_lean_expr

from math_topology.topology_instance import (
    TopologyInstance,
    read_jsonl,
    reconstruct_theorem,
)


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Mock model (used by tests and dry runs)
# ---------------------------------------------------------------------------


class _MockModel:
    """Deterministic stand-in for ModelInterface.  Returns the gold for half
    the rows and a noise string for the other half, so baseline accuracy
    on a freshly generated benchmark is around 0.5 -- enough to validate
    the grading pipeline without spending on real API calls.

    Order of returned values follows Python's hash() to be deterministic
    within a process; swap to a real ModelInterface for honest baselines.
    """

    name = "mock"

    def __init__(self) -> None:
        self.calls = 0

    def query(self, instance: TopologyInstance) -> str:
        self.calls += 1
        if self.calls % 2 == 0 and instance.gold:
            return instance.gold[0]
        return "P.dim = 99"


# ---------------------------------------------------------------------------
# Provider plumbing
# ---------------------------------------------------------------------------


def _build_provider(name: str) -> Any:
    """Return either the mock model or a ModelInterface from model_interface.

    We only import model_interface lazily so the mock path stays free of
    Foundry / Anthropic / Azure dependencies.
    """
    if name == "mock":
        return _MockModel()
    import model_interface as mi  # noqa: WPS433  (lazy on purpose)
    table = {
        "foundry-gpt":      mi.FoundryGPT52Interface,
        "foundry-kimi":     mi.FoundryKimiInterface,
        "foundry-claude":   mi.FoundryClaudeInterface,
        "foundry-deepseek": mi.FoundryDeepSeekInterface,
    }
    if name not in table:
        raise ValueError(f"unknown provider {name!r}; pick one of {sorted(table)} or 'mock'.")
    return table[name]()


def _query(provider: Any, instance: TopologyInstance) -> str:
    if isinstance(provider, _MockModel):
        return provider.query(instance)
    response = provider.generate(instance.prompt, max_tokens=256, temperature=0.0)
    return response.text if hasattr(response, "text") else str(response)


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------


@dataclass
class RowResult:
    instance_id: str
    level: int
    theorem_identifier: str
    response: str
    correct: bool
    reward: float
    lean_status: str = ""
    trivial_restoration: bool = False
    matches_mathlib: bool = False
    novelty_distance: float = 0.0


def _grade_l1_l2(inst: TopologyInstance, response: str) -> RowResult:
    norm_resp = normalised_lean_expr(response)
    gold_norms = {normalised_lean_expr(g) for g in inst.gold}
    correct = norm_resp in gold_norms
    return RowResult(
        instance_id=inst.instance_id,
        level=inst.level,
        theorem_identifier=inst.theorem_identifier,
        response=response,
        correct=correct,
        reward=1.0 if correct else 0.0,
    )


def _grade_l3(
    inst: TopologyInstance,
    response: str,
    scorer: DefeaterScorer,
) -> RowResult:
    parent = reconstruct_theorem(inst)
    challenge = next(
        (c for c in HypothesisDropper(DropPolicy.SINGLE_ANY).drop(parent)
         if tuple(c.masked_hypotheses) == tuple(inst.masked_hypotheses)),
        None,
    )
    if challenge is None:
        # Parent had no matching ablation (shouldn't happen for instances
        # generated by generate_benchmark); fall through with zero reward.
        return RowResult(
            instance_id=inst.instance_id,
            level=inst.level,
            theorem_identifier=inst.theorem_identifier,
            response=response,
            correct=False,
            reward=0.0,
            lean_status="error",
        )
    score = scorer.score(challenge, Defeater(lean_expr=response, provenance="model"))
    return RowResult(
        instance_id=inst.instance_id,
        level=inst.level,
        theorem_identifier=inst.theorem_identifier,
        response=response,
        correct=score.reward > 0,
        reward=score.reward,
        lean_status=score.lean.status.value,
        trivial_restoration=score.novelty.is_trivial_restoration,
        matches_mathlib=score.novelty.matches_mathlib,
        novelty_distance=score.novelty.distance,
    )


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


@dataclass
class LevelSummary:
    level:       int
    n_rows:      int
    accuracy:    float
    mean_reward: float
    extras:      dict[str, float] = field(default_factory=dict)


def summarise(rows: list[RowResult]) -> dict[int, LevelSummary]:
    out: dict[int, LevelSummary] = {}
    for level in (1, 2, 3):
        sub = [r for r in rows if r.level == level]
        n = len(sub)
        if n == 0:
            continue
        accuracy = sum(1 for r in sub if r.correct) / n
        mean_reward = sum(r.reward for r in sub) / n
        extras: dict[str, float] = {}
        if level == 3:
            extras["pct_trivial_restoration"] = sum(1 for r in sub if r.trivial_restoration) / n
            extras["pct_matches_mathlib"] = sum(1 for r in sub if r.matches_mathlib) / n
            extras["mean_novelty_distance"] = sum(r.novelty_distance for r in sub) / n
        out[level] = LevelSummary(
            level=level, n_rows=n, accuracy=accuracy,
            mean_reward=mean_reward, extras=extras,
        )
    return out


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------


def run_baseline(
    benchmark_dir: Path,
    provider_name: str,
    output_dir: Path,
    harness: LeanHarness | None = None,
) -> dict[str, Any]:
    instances: list[TopologyInstance] = []
    for fname in ("l1.jsonl", "l2.jsonl", "l3.jsonl"):
        path = benchmark_dir / fname
        if path.exists():
            instances.extend(read_jsonl(path))
    if not instances:
        raise FileNotFoundError(f"no L1/L2/L3 JSONL files under {benchmark_dir}")

    provider = _build_provider(provider_name)
    scorer = DefeaterScorer(
        harness=harness or available_harness(prefer_real=False),
        novelty=NoveltyFilter(),
    )

    rows: list[RowResult] = []
    for inst in instances:
        response = _query(provider, inst).strip()
        if inst.level in (1, 2):
            rows.append(_grade_l1_l2(inst, response))
        else:
            rows.append(_grade_l3(inst, response, scorer))

    summaries = summarise(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows_path = output_dir / f"{provider_name}.rows.jsonl"
    with rows_path.open("w") as f:
        for r in rows:
            f.write(json.dumps(asdict(r)))
            f.write("\n")
    summary_payload = {
        "provider": provider_name,
        "benchmark": str(benchmark_dir),
        "summary": {str(k): asdict(v) for k, v in summaries.items()},
    }
    (output_dir / f"{provider_name}.summary.json").write_text(
        json.dumps(summary_payload, indent=2)
    )
    return summary_payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--provider", type=str, default="mock")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    payload = run_baseline(
        benchmark_dir=args.benchmark,
        provider_name=args.provider,
        output_dir=args.output_dir,
    )
    sys.stdout.write(json.dumps(payload, indent=2))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
