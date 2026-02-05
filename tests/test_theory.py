"""Tests for Theory representation and manipulation."""

import pytest

from blanc.core.theory import Rule, RuleType, Theory


class TestRule:
    """Test Rule class."""

    def test_create_fact(self):
        """Test creating a fact."""
        rule = Rule(head="bird(tweety)", rule_type=RuleType.FACT)
        assert rule.is_fact
        assert not rule.is_strict
        assert not rule.is_defeasible
        assert not rule.is_defeater

    def test_create_strict_rule(self):
        """Test creating a strict rule."""
        rule = Rule(
            head="mortal(X)",
            body=("human(X)",),
            rule_type=RuleType.STRICT,
        )
        assert not rule.is_fact
        assert rule.is_strict
        assert rule.head == "mortal(X)"
        assert rule.body == ("human(X)",)

    def test_create_defeasible_rule(self):
        """Test creating a defeasible rule."""
        rule = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1",
        )
        assert rule.is_defeasible
        assert rule.label == "r1"

    def test_create_defeater(self):
        """Test creating a defeater."""
        rule = Rule(
            head="not_flies(X)",
            body=("bird(X)", "wounded(X)"),
            rule_type=RuleType.DEFEATER,
        )
        assert rule.is_defeater

    def test_fact_cannot_have_body(self):
        """Test that facts cannot have a body."""
        with pytest.raises(ValueError, match="Facts cannot have a body"):
            Rule(head="bird(tweety)", body=("something",), rule_type=RuleType.FACT)

    def test_rule_must_have_head(self):
        """Test that rules must have a head."""
        with pytest.raises(ValueError, match="Rule must have a head"):
            Rule(head="", body=("something",))

    def test_to_prolog(self):
        """Test conversion to Prolog syntax."""
        fact = Rule(head="bird(tweety)", rule_type=RuleType.FACT)
        assert fact.to_prolog() == "bird(tweety)."

        rule = Rule(head="mortal(X)", body=("human(X)",))
        assert rule.to_prolog() == "mortal(X) :- human(X)."

    def test_to_defeasible(self):
        """Test conversion to defeasible logic syntax."""
        strict = Rule(
            head="mortal(X)",
            body=("human(X)",),
            rule_type=RuleType.STRICT,
        )
        assert strict.to_defeasible() == "human(X) -> mortal(X)"

        defeasible = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1",
        )
        assert defeasible.to_defeasible() == "r1: bird(X) => flies(X)"

        defeater = Rule(
            head="not_flies(X)",
            body=("wounded(X)",),
            rule_type=RuleType.DEFEATER,
        )
        assert defeater.to_defeasible() == "wounded(X) ~> not_flies(X)"


class TestTheory:
    """Test Theory class."""

    def test_create_empty_theory(self):
        """Test creating an empty theory."""
        theory = Theory()
        assert len(theory) == 0
        assert len(theory.rules) == 0
        assert len(theory.facts) == 0

    def test_add_fact(self):
        """Test adding a fact to theory."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        assert "bird(tweety)" in theory.facts
        assert len(theory) == 1

    def test_add_rule(self):
        """Test adding a rule to theory."""
        theory = Theory()
        rule = Rule(head="mortal(X)", body=("human(X)",))
        theory.add_rule(rule)
        assert rule in theory.rules
        assert len(theory.rules) == 1

    def test_add_superiority(self):
        """Test adding superiority relation."""
        theory = Theory()
        theory.add_superiority("r1", "r2")
        assert "r2" in theory.superiority["r1"]

    def test_get_rules_by_type(self):
        """Test filtering rules by type."""
        theory = Theory()
        strict = Rule(head="p(X)", body=("q(X)",), rule_type=RuleType.STRICT)
        defeasible = Rule(head="r(X)", body=("s(X)",), rule_type=RuleType.DEFEASIBLE)

        theory.add_rule(strict)
        theory.add_rule(defeasible)

        strict_rules = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict_rules) == 1
        assert strict_rules[0] == strict

        defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible_rules) == 1
        assert defeasible_rules[0] == defeasible

    def test_get_rule_by_label(self):
        """Test finding rule by label."""
        theory = Theory()
        rule = Rule(head="p(X)", body=("q(X)",), label="r1")
        theory.add_rule(rule)

        found = theory.get_rule_by_label("r1")
        assert found == rule

        not_found = theory.get_rule_by_label("r2")
        assert not_found is None

    def test_to_prolog(self):
        """Test conversion to Prolog format."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(Rule(head="mortal(X)", body=("human(X)",)))

        prolog = theory.to_prolog()
        assert "bird(tweety)." in prolog
        assert "mortal(X) :- human(X)." in prolog

    def test_to_defeasible(self):
        """Test conversion to defeasible logic format."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(
            Rule(
                head="flies(X)",
                body=("bird(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label="r1",
            )
        )
        theory.add_superiority("r1", "r2")

        defeasible = theory.to_defeasible()
        assert "bird(tweety)" in defeasible
        assert "r1: bird(X) => flies(X)" in defeasible
        assert "r1 > r2" in defeasible

    def test_theory_immutability(self):
        """Test that Rule objects are immutable."""
        rule = Rule(head="p(a)")
        with pytest.raises(Exception):  # dataclass frozen
            rule.head = "q(a)"  # type: ignore


class TestTheoryExamples:
    """Test realistic theory examples."""

    def test_tweety_example(self):
        """Test classic Tweety the penguin example."""
        theory = Theory()

        # Facts
        theory.add_fact("bird(tweety)")
        theory.add_fact("penguin(tweety)")

        # Rules
        r1 = Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1",
        )
        r2 = Rule(
            head="not_flies(X)",
            body=("penguin(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r2",
        )

        theory.add_rule(r1)
        theory.add_rule(r2)

        # Penguin rule defeats bird rule
        theory.add_superiority("r2", "r1")

        assert len(theory.facts) == 2
        assert len(theory.rules) == 2
        assert "r1" in theory.superiority["r2"]

    def test_medical_diagnosis_example(self):
        """Test medical diagnosis example."""
        theory = Theory()

        # Patient symptoms (facts)
        theory.add_fact("symptom(patient1, fever)")
        theory.add_fact("symptom(patient1, cough)")

        # Diagnostic rules
        flu_rule = Rule(
            head="diagnosis(P, flu)",
            body=("symptom(P, fever)", "symptom(P, cough)"),
            rule_type=RuleType.DEFEASIBLE,
            label="flu_diagnosis",
        )

        covid_rule = Rule(
            head="diagnosis(P, covid)",
            body=("symptom(P, fever)", "symptom(P, cough)", "recent_travel(P)"),
            rule_type=RuleType.DEFEASIBLE,
            label="covid_diagnosis",
        )

        theory.add_rule(flu_rule)
        theory.add_rule(covid_rule)

        # COVID diagnosis takes precedence if travel history exists
        theory.add_superiority("covid_diagnosis", "flu_diagnosis")

        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 2
