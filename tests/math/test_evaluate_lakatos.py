"""Tests for experiments.math_topology.evaluate_lakatos."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.evaluate_lakatos import (  # noqa: E402
    evaluate_responses,
    gate_decision,
    one_sided_z_proportion,
)
from math_topology.lakatos_corpus import held_out_fixture  # noqa: E402


def _gold_response() -> str:
    return held_out_fixture().gold_defeaters[0].lean_expr


def _trivial_response() -> str:
    f = held_out_fixture()
    return f.parent.hypothesis_by_name(f.masked).lean_expr


def _noise_response() -> str:
    return "P.dim = 99"


class TestEvaluateResponses:
    def test_gold_response_is_positive_control_hit(self) -> None:
        result = evaluate_responses([_gold_response()])
        assert result.n_positive_control_hit == 1
        assert result.hit_rate == 1.0

    def test_trivial_response_is_not_a_hit(self) -> None:
        result = evaluate_responses([_trivial_response()])
        assert result.n_lean_accept == 1
        assert result.n_trivial_restoration == 1
        assert result.n_positive_control_hit == 0

    def test_noise_response_is_not_a_hit(self) -> None:
        result = evaluate_responses([_noise_response()])
        assert result.n_lean_accept == 0
        assert result.n_positive_control_hit == 0

    def test_mixed_run(self) -> None:
        responses = (
            [_gold_response()] * 5
            + [_trivial_response()] * 3
            + [_noise_response()] * 2
        )
        result = evaluate_responses(responses)
        assert result.n_trials == 10
        assert result.n_positive_control_hit == 5
        assert result.hit_rate == 0.5
        assert result.n_trivial_restoration == 3


class TestZProportion:
    def test_equal_rates_give_p_around_half(self) -> None:
        z, p = one_sided_z_proportion(5, 10, 5, 10)
        assert z == pytest.approx(0.0)
        assert p == pytest.approx(0.5)

    def test_higher_a_lower_p(self) -> None:
        z, p = one_sided_z_proportion(20, 30, 5, 30)
        assert z > 0
        assert p < 0.001

    def test_zero_n_returns_safe_default(self) -> None:
        assert one_sided_z_proportion(0, 0, 0, 0) == (0.0, 1.0)


class TestGateDecision:
    def test_pass_when_trained_significantly_higher(self) -> None:
        trained = evaluate_responses([_gold_response()] * 30)
        baseline = evaluate_responses([_noise_response()] * 30)
        decision = gate_decision(trained, baseline, alpha=0.05)
        assert decision["passes_gate"] is True
        assert decision["delta"] > 0

    def test_fail_when_no_difference(self) -> None:
        trained = evaluate_responses([_noise_response()] * 30)
        baseline = evaluate_responses([_noise_response()] * 30)
        decision = gate_decision(trained, baseline, alpha=0.05)
        assert decision["passes_gate"] is False

    def test_fail_when_trained_is_lower(self) -> None:
        trained = evaluate_responses([_noise_response()] * 30)
        baseline = evaluate_responses([_gold_response()] * 30)
        decision = gate_decision(trained, baseline)
        assert decision["passes_gate"] is False
        assert decision["delta"] < 0
