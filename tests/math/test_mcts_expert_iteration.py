"""Tests for experiments.math_topology.mcts_expert_iteration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.math.defeater_scorer import DefeaterScorer  # noqa: E402
from blanc.math.lean_harness import MockLeanHarness  # noqa: E402
from blanc.math.novelty import NoveltyFilter  # noqa: E402
from blanc.math.topology_extractor import builtin_corpus  # noqa: E402
from blanc.math.types import Defeater, LeanStatus  # noqa: E402

from math_topology.mcts_expert_iteration import (  # noqa: E402
    DeferredMCTS,
    ExpertIterationRecord,
    UniformRolloutMCTS,
    _ListPolicy,
    search_to_record,
    write_records,
)


def _euler_theorem():
    return next(
        t for t in builtin_corpus().theorems
        if t.identifier == "EulerCharacteristic.convex_polytope_v_minus_e_plus_f"
    )


def _scorer_with_known_accepts(accept_exprs: list[str]) -> DefeaterScorer:
    theorem = _euler_theorem()
    harness = MockLeanHarness(default_status=LeanStatus.UNKNOWN)
    for expr in accept_exprs:
        harness.register(
            theorem,
            Defeater(lean_expr=expr),
            masked_hypotheses=("h_convex",),
            status=LeanStatus.PROVED,
        )
    return DefeaterScorer(harness=harness, novelty=NoveltyFilter())


class TestUniformRolloutMCTS:
    def test_search_concentrates_on_lean_accepted(self) -> None:
        theorem = _euler_theorem()
        good = Defeater(lean_expr="P.boundary.genus = 0")
        bad = Defeater(lean_expr="False")
        scorer = _scorer_with_known_accepts([good.lean_expr])
        policy = _ListPolicy(proposals=[(good, 0.5), (bad, 0.5)])
        expert = UniformRolloutMCTS(
            policy=policy, scorer=scorer,
            n_simulations=16, n_candidates=2, seed=42,
        )
        result = expert.search(theorem, masked=("h_convex",))
        assert result.best_defeater.lean_expr == good.lean_expr
        assert result.best_reward > 0.0
        good_node = next(n for n in result.nodes if n.defeater.lean_expr == good.lean_expr)
        bad_node = next(n for n in result.nodes if n.defeater.lean_expr == bad.lean_expr)
        assert good_node.visit_count >= bad_node.visit_count
        assert sum(n.visit_count for n in result.nodes) == 16

    def test_search_raises_on_empty_proposals(self) -> None:
        theorem = _euler_theorem()
        scorer = _scorer_with_known_accepts([])
        expert = UniformRolloutMCTS(
            policy=_ListPolicy(proposals=[]), scorer=scorer,
            n_simulations=4, n_candidates=2,
        )
        with pytest.raises(ValueError, match="no proposals"):
            expert.search(theorem, masked=("h_convex",))


class TestExpertIterationExport:
    def test_search_to_record_is_normalised_distribution(self) -> None:
        theorem = _euler_theorem()
        good = Defeater(lean_expr="P.boundary.genus = 0")
        bad = Defeater(lean_expr="False")
        scorer = _scorer_with_known_accepts([good.lean_expr])
        result = UniformRolloutMCTS(
            policy=_ListPolicy([(good, 0.5), (bad, 0.5)]), scorer=scorer,
            n_simulations=10, n_candidates=2, seed=1,
        ).search(theorem, masked=("h_convex",))
        record = search_to_record(result)
        assert isinstance(record, ExpertIterationRecord)
        assert abs(sum(record.visit_distribution) - 1.0) < 1e-9
        assert record.best_defeater == good.lean_expr

    def test_write_records_writes_jsonl(self, tmp_path: Path) -> None:
        records = [
            ExpertIterationRecord(
                theorem_identifier="X",
                masked=("h",),
                visit_distribution=(1.0,),
                candidate_defeaters=("True",),
                best_defeater="True",
                best_reward=1.0,
            )
        ]
        out = tmp_path / "ei.jsonl"
        write_records(records, out)
        rows = [json.loads(l) for l in out.read_text().splitlines() if l.strip()]
        assert len(rows) == 1
        assert rows[0]["best_defeater"] == "True"


class TestDeferredMCTS:
    def test_search_raises_not_implemented(self) -> None:
        with pytest.raises(NotImplementedError, match="M5"):
            DeferredMCTS().search(_euler_theorem(), masked=("h_convex",))
