"""
Tests for CommanderPolicy with mocked LLM responses.

One test per enforcement mode demonstrating gating behavior.
All tests are pure Python with no SC2 binary or real API required.

Author: Patrick Cooper
"""

import copy
import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.sc2live.policies.commander import CommanderPolicy, EnforcementMode
from blanc.sc2live.orders_schema import Order


# ---------------------------------------------------------------------------
# Mock LLM model
# ---------------------------------------------------------------------------

class _ModelResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _MockModel:
    """LLM stub that returns a scripted response sequence."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._call_count = 0

    def query(self, prompt: str, **kwargs) -> _ModelResponse:
        text = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return _ModelResponse(text)

    @property
    def call_count(self) -> int:
        return self._call_count


# ---------------------------------------------------------------------------
# Theory fixtures
# ---------------------------------------------------------------------------

def _exclusion_theory() -> Theory:
    """Theory: marine and enemy both in restricted zone -> attack blocked."""
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
    theory = create_rts_engagement_kb(include_instances=False)
    theory.add_fact("military_unit(marine)")
    theory.add_fact("infantry_unit(marine)")
    theory.add_fact("military_target(enemy)")
    theory.add_fact("in_zone(marine, restricted_zone_alpha)")
    theory.add_fact("in_zone(enemy, restricted_zone_alpha)")
    return theory


def _open_theory() -> Theory:
    """Theory: marine authorized to engage enemy (no defeater active)."""
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
    theory = create_rts_engagement_kb(include_instances=False)
    theory.add_fact("military_unit(marine)")
    theory.add_fact("infantry_unit(marine)")
    theory.add_fact("military_target(enemy)")
    return theory


# ---------------------------------------------------------------------------
# Helper to inject mock model into policy
# ---------------------------------------------------------------------------

def _make_policy(
    mode: EnforcementMode,
    responses: list[str],
    max_reprompts: int = 3,
) -> tuple[CommanderPolicy, _MockModel]:
    policy = CommanderPolicy(
        mode=mode,
        provider="mock",
        max_reprompts=max_reprompts,
        macro_step_interval=1,
        scenario_id="test",
    )
    mock_model = _MockModel(responses)
    policy._model = mock_model
    return policy, mock_model


# ---------------------------------------------------------------------------
# B0 trust-LLM tests
# ---------------------------------------------------------------------------

class TestB0Trust:
    def test_non_compliant_order_admitted_verbatim(self):
        """B0 should admit attack in exclusion zone without blocking."""
        policy, model = _make_policy(
            EnforcementMode.B0,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
        )
        theory = _exclusion_theory()
        admitted = policy.propose_orders(theory, step=0)
        assert len(admitted) == 1
        assert admitted[0].action == "attack"

    def test_history_records_violations(self):
        """B0 records compliance verdicts even without enforcement."""
        policy, _ = _make_policy(
            EnforcementMode.B0,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
        )
        theory = _exclusion_theory()
        policy.propose_orders(theory, step=0)
        assert len(policy.history) == 1
        tick = policy.history[0]
        assert tick.mode == "B0"
        assert tick.reprompts == 0

    def test_compliant_order_admitted_in_b0(self):
        policy, _ = _make_policy(
            EnforcementMode.B0,
            ['[{"action":"hold","unit":"marine"}]'],
        )
        admitted = policy.propose_orders(_open_theory(), step=0)
        assert len(admitted) == 1
        assert admitted[0].action == "hold"

    def test_off_interval_returns_empty(self):
        policy, _ = _make_policy(EnforcementMode.B0, ['[{"action":"hold","unit":"m"}]'])
        # interval=1, step=2 should trigger; step=3 also triggers (2%1==0, 3%1==0)
        # interval=44 would not
        policy2 = CommanderPolicy(mode=EnforcementMode.B0, macro_step_interval=44)
        policy2._model = _MockModel(['[{"action":"hold","unit":"m"}]'])
        result = policy2.propose_orders(_open_theory(), step=1)
        assert result == []


# ---------------------------------------------------------------------------
# B1 audit-only tests
# ---------------------------------------------------------------------------

class TestB1Audit:
    def test_non_compliant_order_admitted_in_b1(self):
        """B1 logs violations but does not block."""
        policy, _ = _make_policy(
            EnforcementMode.B1,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
        )
        admitted = policy.propose_orders(_exclusion_theory(), step=0)
        assert len(admitted) == 1

    def test_verdict_logged_in_b1(self):
        policy, _ = _make_policy(
            EnforcementMode.B1,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
        )
        policy.propose_orders(_exclusion_theory(), step=0)
        verdicts = policy.history[0].verdicts
        assert len(verdicts) >= 1

    def test_reprompts_zero_in_b1(self):
        policy, _ = _make_policy(
            EnforcementMode.B1,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
        )
        policy.propose_orders(_exclusion_theory(), step=0)
        assert policy.history[0].reprompts == 0


# ---------------------------------------------------------------------------
# B2 gated tests
# ---------------------------------------------------------------------------

class TestB2Gated:
    def test_non_compliant_order_rejected_in_b2(self):
        """B2 should NOT admit the initial non-compliant attack if re-prompt also fails."""
        # All responses are the same bad attack
        policy, model = _make_policy(
            EnforcementMode.B2,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
            max_reprompts=2,
        )
        admitted = policy.propose_orders(_exclusion_theory(), step=0)
        # All reprompts also return attack, so order should be dropped
        assert all(o.action != "attack" or o.target != "enemy" for o in admitted)

    def test_order_admitted_after_valid_revision(self):
        """B2 should admit a hold order if the LLM revises to a compliant order."""
        responses = [
            # Initial response: attack (non-compliant in exclusion zone)
            '[{"action":"attack","unit":"marine","target":"enemy"}]',
            # Re-prompt response: hold (always compliant)
            '[{"action":"hold","unit":"marine"}]',
        ]
        policy, model = _make_policy(
            EnforcementMode.B2, responses, max_reprompts=3
        )
        admitted = policy.propose_orders(_exclusion_theory(), step=0)
        # Should admit the hold
        assert any(o.action == "hold" for o in admitted)

    def test_reprompts_counted(self):
        """B2 tick should record the number of re-prompts consumed."""
        responses = [
            '[{"action":"attack","unit":"marine","target":"enemy"}]',
            '[{"action":"hold","unit":"marine"}]',
        ]
        policy, _ = _make_policy(EnforcementMode.B2, responses, max_reprompts=3)
        policy.propose_orders(_exclusion_theory(), step=0)
        assert policy.history[0].reprompts >= 1

    def test_hold_order_needs_no_reprompt(self):
        """A compliant hold order should never trigger a re-prompt."""
        policy, model = _make_policy(
            EnforcementMode.B2,
            ['[{"action":"hold","unit":"marine"}]'],
        )
        admitted = policy.propose_orders(_open_theory(), step=0)
        assert len(admitted) == 1
        assert policy.history[0].reprompts == 0
        assert model.call_count == 1  # only one LLM call

    def test_max_reprompts_respected(self):
        """B2 never exceeds max_reprompts even if all responses are non-compliant."""
        policy, model = _make_policy(
            EnforcementMode.B2,
            ['[{"action":"attack","unit":"marine","target":"enemy"}]'],
            max_reprompts=2,
        )
        policy.propose_orders(_exclusion_theory(), step=0)
        # 1 initial + 2 reprompts = 3 total LLM calls maximum
        assert model.call_count <= 3
        assert policy.history[0].reprompts <= 2

    def test_empty_llm_response_handled(self):
        """Empty or unparseable LLM response should not crash."""
        policy, _ = _make_policy(EnforcementMode.B2, [""])
        admitted = policy.propose_orders(_open_theory(), step=0)
        assert admitted == []


# ---------------------------------------------------------------------------
# Record-keeping tests
# ---------------------------------------------------------------------------

class TestHistory:
    def test_history_grows_with_each_tick(self):
        policy, _ = _make_policy(
            EnforcementMode.B0,
            ['[{"action":"hold","unit":"m"}]'],
        )
        theory = _open_theory()
        for step in range(5):
            policy.propose_orders(theory, step)
        assert len(policy.history) == 5

    def test_tick_record_to_dict_has_required_keys(self):
        policy, _ = _make_policy(
            EnforcementMode.B1,
            ['[{"action":"hold","unit":"m"}]'],
        )
        policy.propose_orders(_open_theory(), step=0)
        d = policy.history[0].to_dict()
        for key in ("step", "mode", "scenario_id", "facts_count",
                    "orders_proposed", "orders_admitted", "verdicts",
                    "reprompts", "model_latency_ms"):
            assert key in d
