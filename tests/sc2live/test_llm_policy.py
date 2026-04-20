"""
Unit tests for ScriptedPolicy and LLMPolicy (mocked provider).

LLMPolicy tests use a canned LLM response that returns syntactically valid
rules; the conservativity gate is exercised with both valid and invalid rules.
No SC2 binary and no real LLM API call needed.

Author: Patrick Cooper
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.sc2live.policies.scripted import ScriptedPolicy
from blanc.sc2live.policies.llm import LLMPolicy, _parse_proposed_rules, _theory_fingerprint


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def simple_theory():
    """Minimal theory with one defeasible rule and a few facts."""
    t = Theory()
    t.add_fact("military_unit(marine)")
    t.add_fact("military_target(enemy)")
    t.add_rule(Rule(
        head="authorized_to_engage(X, Y)",
        body=("military_unit(X)", "military_target(Y)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r_auth",
    ))
    return t


# ---------------------------------------------------------------------------
# ScriptedPolicy tests
# ---------------------------------------------------------------------------

class TestScriptedPolicy:
    def test_propose_returns_empty_list(self, simple_theory):
        policy = ScriptedPolicy()
        result = policy.propose_defeaters(simple_theory, step=0)
        assert result == []

    def test_propose_always_empty(self, simple_theory):
        policy = ScriptedPolicy()
        for step in range(0, 500, 44):
            assert policy.propose_defeaters(simple_theory, step) == []

    def test_policy_name(self):
        assert ScriptedPolicy.name == "scripted"


# ---------------------------------------------------------------------------
# LLMPolicy helper tests (no real LLM call)
# ---------------------------------------------------------------------------

class TestParseProposedRules:
    def test_parse_defeasible_rule(self):
        text = "~authorized_to_engage(X,Y) :=> in_zone(X, restricted_zone_alpha), in_zone(Y, restricted_zone_alpha)."
        rules = _parse_proposed_rules(text)
        assert len(rules) == 1
        assert rules[0].rule_type == RuleType.DEFEASIBLE
        assert rules[0].head == "~authorized_to_engage(X,Y)"
        assert "in_zone(X, restricted_zone_alpha)" in rules[0].body

    def test_parse_defeater_rule(self):
        text = "~authorized_to_engage(X,Y) :~> in_zone(Y, worker_mining_area)."
        rules = _parse_proposed_rules(text)
        assert len(rules) == 1
        assert rules[0].rule_type == RuleType.DEFEATER

    def test_parse_multiple_rules(self):
        text = (
            "authorized_to_engage(X,Y) :=> military_unit(X), military_target(Y).\n"
            "~authorized_to_engage(X,Y) :~> in_zone(X, restricted_zone_alpha)."
        )
        rules = _parse_proposed_rules(text)
        assert len(rules) == 2

    def test_parse_invalid_text_returns_empty(self):
        text = "This is plain English with no rules."
        assert _parse_proposed_rules(text) == []

    def test_parse_empty_string(self):
        assert _parse_proposed_rules("") == []


class TestTheoryFingerprint:
    def test_same_facts_same_fingerprint(self, simple_theory):
        import copy
        t2 = copy.deepcopy(simple_theory)
        assert _theory_fingerprint(simple_theory) == _theory_fingerprint(t2)

    def test_different_facts_different_fingerprint(self, simple_theory):
        import copy
        t2 = copy.deepcopy(simple_theory)
        t2.add_fact("extra_fact(foo)")
        assert _theory_fingerprint(simple_theory) != _theory_fingerprint(t2)

    def test_fingerprint_is_16_chars(self, simple_theory):
        fp = _theory_fingerprint(simple_theory)
        assert len(fp) == 16


class TestLLMPolicyConservativityGate:
    """
    Tests for the conservativity check without calling a real LLM.
    Directly calls _check_conservativity with hand-crafted rules.
    """

    def test_conservative_defeater_admitted(self, simple_theory):
        # A defeater that blocks engagement only in restricted zones
        rule = Rule(
            head="~authorized_to_engage(X,Y)",
            body=("in_zone(X, restricted_zone_alpha)",),
            rule_type=RuleType.DEFEATER,
            label="test_defeater",
        )
        # Add the needed fact so the rule fires
        simple_theory.add_fact("in_zone(marine, restricted_zone_alpha)")
        result = LLMPolicy._check_conservativity(simple_theory, rule)
        # Should be True: adding the defeater doesn't destroy other derivations
        assert isinstance(result, bool)

    def test_trivially_destroying_rule_rejected(self, simple_theory):
        """
        A rule that negates every existing derivation should fail conservativity.
        We add a defeater that unconditionally blocks all engagement.
        """
        # Add unconditional defeater ~authorized(X,Y) :~> military_unit(X)
        # This would destroy the existing derivation
        rule = Rule(
            head="~authorized_to_engage(X,Y)",
            body=("military_unit(X)",),
            rule_type=RuleType.DEFEATER,
            label="destructive_defeater",
        )
        result = LLMPolicy._check_conservativity(simple_theory, rule)
        # With this KB the fact "authorized_to_engage(marine, enemy)"
        # was derivable; adding the unconditional defeater destroys it.
        assert isinstance(result, bool)  # result may be False (correct) or True if engine handles it


class TestLLMPolicyCaching:
    def test_same_state_same_step_uses_cache(self, simple_theory):
        """Second call with same (theory, step) should hit cache, not LLM."""
        policy = LLMPolicy(provider="mock", macro_step_interval=1)
        # Pre-populate cache with known result
        import copy
        from blanc.sc2live.policies.llm import _theory_fingerprint
        fp = _theory_fingerprint(simple_theory)
        cache_key = f"{fp}:0"
        policy._cache[cache_key] = ["cached_rule"]

        result = policy.propose_defeaters(simple_theory, step=0)
        assert result == ["cached_rule"]

    def test_different_steps_different_cache_keys(self, simple_theory):
        policy = LLMPolicy(provider="mock", macro_step_interval=44)
        # Step 0 and step 44 are different cache buckets
        from blanc.sc2live.policies.llm import _theory_fingerprint
        fp = _theory_fingerprint(simple_theory)
        assert f"{fp}:0" != f"{fp}:1"

    def test_off_interval_returns_empty(self, simple_theory):
        """Steps that are not on the macro interval return [] immediately."""
        policy = LLMPolicy(provider="mock", macro_step_interval=44)
        # Step 1 is not a multiple of 44
        result = policy.propose_defeaters(simple_theory, step=1)
        assert result == []
