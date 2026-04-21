"""
Tests for situation_report.py: Theory -> LLM commander brief.

Author: Patrick Cooper
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.sc2live.situation_report import (
    build_situation_report,
    build_roe_system_prompt,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_theory():
    t = Theory()
    t.add_fact("infantry_unit(marine)")
    t.add_fact("in_zone(marine, main_base)")
    t.add_fact("military_target(enemy_zergling)")
    t.add_fact("in_zone(enemy_zergling, engagement_zone_alpha)")
    t.add_rule(Rule(
        head="authorized_to_engage(X, Y)",
        body=("military_unit(X)", "military_target(Y)"),
        rule_type=RuleType.DEFEASIBLE,
        label="rts_r3000",
    ))
    return t


@pytest.fixture
def exclusion_theory():
    t = Theory()
    t.add_fact("infantry_unit(marine)")
    t.add_fact("military_target(enemy)")
    t.add_fact("in_zone(marine, restricted_zone_alpha)")
    t.add_fact("in_zone(enemy, restricted_zone_alpha)")
    t.add_rule(Rule(
        head="~authorized_to_engage(X,Y)",
        body=("in_zone(X, restricted_zone_alpha)", "in_zone(Y, restricted_zone_alpha)"),
        rule_type=RuleType.DEFEATER,
        label="rts_r3003",
    ))
    return t


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildSituationReport:
    def test_returns_string(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert isinstance(report, str)
        assert len(report) > 0

    def test_contains_header(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert "SITUATION REPORT" in report

    def test_contains_friendly_unit(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert "marine" in report

    def test_contains_enemy_contact(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert "enemy_zergling" in report

    def test_contains_roe_section(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert "RULES OF ENGAGEMENT" in report.upper()

    def test_contains_defeater_in_exclusion_theory(self, exclusion_theory):
        report = build_situation_report(exclusion_theory)
        assert "EXCEPTION" in report or "rts_r3003" in report

    def test_step_injected_when_provided(self, simple_theory):
        report = build_situation_report(simple_theory, step=88)
        assert "88" in report

    def test_scenario_description_injected(self, simple_theory):
        report = build_situation_report(
            simple_theory, scenario_description="Marine is in danger."
        )
        assert "Marine is in danger" in report

    def test_max_lines_respected(self, simple_theory):
        report = build_situation_report(simple_theory, max_lines=10)
        lines = report.splitlines()
        assert len(lines) <= 10

    def test_contains_orders_prompt(self, simple_theory):
        report = build_situation_report(simple_theory)
        assert "YOUR TASK" in report

    def test_all_in_rush_flag(self):
        t = Theory()
        t.add_fact("all_in_rush_detected")
        report = build_situation_report(t)
        assert "ALL-IN RUSH" in report

    def test_empty_theory_no_crash(self):
        t = Theory()
        report = build_situation_report(t)
        assert isinstance(report, str)


class TestBuildROESystemPrompt:
    def test_returns_non_empty_string(self):
        prompt = build_roe_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 50

    def test_contains_newport_reference(self):
        prompt = build_roe_system_prompt()
        assert "ROE" in prompt or "Rules of Engagement" in prompt

    def test_contains_action_types(self):
        prompt = build_roe_system_prompt()
        assert "attack" in prompt.lower()
        assert "retreat" in prompt.lower()
        assert "hold" in prompt.lower()
