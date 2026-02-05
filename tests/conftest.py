"""Pytest configuration and fixtures."""

import pytest

from blanc.core.theory import Rule, RuleType, Theory


@pytest.fixture
def simple_theory():
    """Create a simple theory for testing."""
    theory = Theory()
    theory.add_fact("bird(tweety)")
    theory.add_fact("penguin(opus)")

    theory.add_rule(
        Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1",
        )
    )

    theory.add_rule(
        Rule(
            head="not_flies(X)",
            body=("penguin(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r2",
        )
    )

    theory.add_superiority("r2", "r1")

    return theory


@pytest.fixture
def medical_theory():
    """Create a medical diagnosis theory for testing."""
    theory = Theory()

    # Patient facts
    theory.add_fact("symptom(patient1, fever)")
    theory.add_fact("symptom(patient1, cough)")
    theory.add_fact("symptom(patient2, fever)")
    theory.add_fact("recent_travel(patient2)")

    # Diagnostic rules
    theory.add_rule(
        Rule(
            head="diagnosis(P, flu)",
            body=("symptom(P, fever)", "symptom(P, cough)"),
            rule_type=RuleType.DEFEASIBLE,
            label="flu",
        )
    )

    theory.add_rule(
        Rule(
            head="diagnosis(P, covid)",
            body=("symptom(P, fever)", "recent_travel(P)"),
            rule_type=RuleType.DEFEASIBLE,
            label="covid",
        )
    )

    theory.add_superiority("covid", "flu")

    return theory
