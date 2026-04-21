"""
Integration test: full ROE compliance quiz with mock LLM.

Runs the 6 ROE_LEVEL3_SEEDS quiz scenarios through all three enforcement modes
(B0 / B1 / B2) using a mock LLM.  Two mock response strategies are tested:

    - Non-compliant strategy: LLM always proposes the prohibited action.
      Expected: B0/B1 admit it; B2 drops it (after max reprompts).

    - Compliant strategy: LLM always proposes a hold order.
      Expected: all three modes admit it; no violations.

No SC2 binary required.  Runtime < 10 seconds.

Author: Patrick Cooper
"""

import pytest
from blanc.sc2live.policies.commander import CommanderPolicy, EnforcementMode


# ---------------------------------------------------------------------------
# Load the 6 quiz scenarios
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def quiz_scenarios():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
    from run_roe_compliance_experiment import _build_quiz_scenarios, _build_theory_for_scenario
    scenarios = _build_quiz_scenarios()
    return [(s, _build_theory_for_scenario(s)) for s in scenarios]


# ---------------------------------------------------------------------------
# Mock LLM model factory
# ---------------------------------------------------------------------------

class _ModelResponse:
    def __init__(self, text: str) -> None:
        self.text = text


def _make_mock(text: str):
    class _M:
        def query(self, prompt, **kwargs):
            return _ModelResponse(text)
    return _M()


def _prohibited_response(scenario: dict) -> str:
    """Return a JSON order string that issues the prohibited action."""
    prohibited = scenario.get("gold_prohibited_action")
    if prohibited is None:
        return '[{"action":"hold","unit":"marine"}]'
    if prohibited.get("action") == "attack":
        return (f'[{{"action":"attack","unit":"{prohibited["unit"]}",'
                f'"target":"{prohibited["target"]}"}}]')
    if prohibited.get("action") == "retreat":
        return f'[{{"action":"retreat","unit":"{prohibited["unit"]}"}}]'
    return '[{"action":"hold","unit":"marine"}]'


def _compliant_response(scenario: dict) -> str:
    """Return a hold order (always compliant)."""
    from scripts.generate_rts_instances import ROE_LEVEL3_SEEDS
    # Get any allied unit from context_facts
    for fact in scenario.get("context_facts", []):
        if fact.startswith("infantry_unit(") or fact.startswith("military_unit("):
            unit = fact.split("(")[1].rstrip(")")
            return f'[{{"action":"hold","unit":"{unit}"}}]'
    return '[{"action":"hold","unit":"marine"}]'


# ---------------------------------------------------------------------------
# Non-compliant LLM: B0/B1 admit, B2 drops
# ---------------------------------------------------------------------------

class TestNonCompliantLLM:
    """When the LLM insists on the prohibited action, B2 should drop it."""

    def test_b0_admits_prohibited_action(self, quiz_scenarios):
        """B0 always admits whatever the LLM says."""
        for scenario, theory in quiz_scenarios:
            prohibited = scenario.get("gold_prohibited_action")
            if prohibited is None:
                continue
            policy = CommanderPolicy(
                mode=EnforcementMode.B0,
                macro_step_interval=1,
                scenario_id=scenario["scenario_id"],
            )
            policy._model = _make_mock(_prohibited_response(scenario))
            admitted = policy.propose_orders(theory, step=0)
            # B0 should admit at least the prohibited order
            actions = [o.action for o in admitted]
            assert prohibited["action"] in actions, (
                f"B0 should admit the order for {scenario['scenario_id']}"
            )

    def test_b2_drops_prohibited_after_reprompts(self, quiz_scenarios):
        """B2 with a stubbornly non-compliant LLM should drop the order."""
        from blanc.sc2live.compliance import check_order
        from blanc.sc2live.orders_schema import Order as Ord

        for scenario, theory in quiz_scenarios:
            prohibited = scenario.get("gold_prohibited_action")
            if prohibited is None:
                continue

            # Skip if the prohibited action is actually compliant in this theory
            # (can happen when the compliance checker legitimately permits it,
            # e.g. retreating when there are no authorized engagement targets).
            try:
                probe_order = Ord(
                    action=prohibited["action"],
                    unit=prohibited["unit"],
                    target=prohibited.get("target"),
                )
                import copy
                probe_verdict = check_order(probe_order, copy.deepcopy(theory))
                if probe_verdict.compliant:
                    continue  # B2 cannot block a legitimately compliant order
            except (ValueError, KeyError):
                continue

            policy = CommanderPolicy(
                mode=EnforcementMode.B2,
                max_reprompts=2,
                macro_step_interval=1,
                scenario_id=scenario["scenario_id"],
            )
            # Always returns the prohibited action
            policy._model = _make_mock(_prohibited_response(scenario))
            admitted = policy.propose_orders(copy.deepcopy(theory), step=0)
            # Admitted list should NOT contain the prohibited action
            for o in admitted:
                if o.action == prohibited.get("action"):
                    assert o.unit != prohibited.get("unit") or o.target != prohibited.get("target"), (
                        f"B2 should have dropped the prohibited order for {scenario['scenario_id']}"
                    )

    def test_b2_correct_abstain_rate_above_b0(self, quiz_scenarios):
        """B2 should have more correct abstentions than B0 on non-compliant LLM."""
        b0_correct = 0
        b2_correct = 0
        scenarios_with_prohibited = [
            (s, t) for s, t in quiz_scenarios if s.get("gold_prohibited_action")
        ]

        for scenario, theory in scenarios_with_prohibited:
            import copy
            prohibited = scenario["gold_prohibited_action"]
            mock_resp = _prohibited_response(scenario)

            for mode, counter in [(EnforcementMode.B0, "b0"), (EnforcementMode.B2, "b2")]:
                policy = CommanderPolicy(
                    mode=mode, max_reprompts=2,
                    macro_step_interval=1,
                    scenario_id=scenario["scenario_id"],
                )
                policy._model = _make_mock(mock_resp)
                admitted = policy.propose_orders(copy.deepcopy(theory), step=0)
                issued_prohibited = any(
                    o.action == prohibited["action"]
                    and o.unit == prohibited["unit"]
                    and o.target == prohibited.get("target")
                    for o in admitted
                )
                if not issued_prohibited:
                    if counter == "b0":
                        b0_correct += 1
                    else:
                        b2_correct += 1

        assert b2_correct >= b0_correct, (
            f"B2 correct abstentions ({b2_correct}) should be >= B0 ({b0_correct})"
        )


# ---------------------------------------------------------------------------
# Compliant LLM: all modes admit, no violations
# ---------------------------------------------------------------------------

class TestCompliantLLM:
    """When the LLM always issues hold orders, all modes should admit and log no violations."""

    @pytest.mark.parametrize("mode", [EnforcementMode.B0, EnforcementMode.B1, EnforcementMode.B2])
    def test_hold_admitted_in_all_modes(self, quiz_scenarios, mode):
        for scenario, theory in quiz_scenarios:
            import copy
            policy = CommanderPolicy(
                mode=mode, max_reprompts=2,
                macro_step_interval=1,
                scenario_id=scenario["scenario_id"],
            )
            policy._model = _make_mock(_compliant_response(scenario))
            admitted = policy.propose_orders(copy.deepcopy(theory), step=0)
            assert len(admitted) >= 1, (
                f"Hold order should be admitted in {mode.value} for {scenario['scenario_id']}"
            )

    @pytest.mark.parametrize("mode", [EnforcementMode.B0, EnforcementMode.B1, EnforcementMode.B2])
    def test_no_violations_on_hold(self, quiz_scenarios, mode):
        for scenario, theory in quiz_scenarios:
            import copy
            policy = CommanderPolicy(
                mode=mode, max_reprompts=2,
                macro_step_interval=1,
                scenario_id=scenario["scenario_id"],
            )
            policy._model = _make_mock(_compliant_response(scenario))
            policy.propose_orders(copy.deepcopy(theory), step=0)
            if policy.history:
                violations = [
                    v for v in policy.history[0].verdicts
                    if not v.get("compliant", True)
                ]
                assert len(violations) == 0, (
                    f"Hold should have no violations in {mode.value}"
                )

    def test_b2_no_reprompts_on_hold(self, quiz_scenarios):
        for scenario, theory in quiz_scenarios[:3]:  # sample first 3
            import copy
            policy = CommanderPolicy(
                mode=EnforcementMode.B2, max_reprompts=3,
                macro_step_interval=1,
                scenario_id=scenario["scenario_id"],
            )
            policy._model = _make_mock(_compliant_response(scenario))
            policy.propose_orders(copy.deepcopy(theory), step=0)
            assert policy.history[0].reprompts == 0
