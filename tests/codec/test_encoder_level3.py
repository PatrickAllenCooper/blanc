"""
Targeted tests for PureFormalEncoder coverage gaps.

Covers: encode_instance (Level 3), defeater encoding, superiority
encoding, _is_well_formed_atom edge cases, and the module-level
encode_instance convenience function (encoder.py lines 143-262).

Author: Anonymous Authors
Date: 2026-02-18
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.codec.encoder import PureFormalEncoder, encode_instance


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _simple_theory_with_defeater() -> Theory:
    t = Theory()
    t.add_fact("bird(opus)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
    t.add_rule(Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1"))
    t.add_superiority("d1", "r1")
    return t


def _level3_instance() -> AbductiveInstance:
    """Minimal Level 3 abductive instance for testing."""
    D_minus = Theory()
    D_minus.add_fact("bird(opus)")
    D_minus.add_fact("penguin(opus)")
    D_minus.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))

    gold = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
    distractor = Rule("~walks(X)", ("penguin(X)",), RuleType.DEFEATER, label="d_wrong")

    return AbductiveInstance(
        D_minus=D_minus,
        target="~flies(opus)",
        candidates=[gold, distractor],
        gold=[gold],
        level=3,
        metadata={"anomaly": "flies(opus)"},
    )


# ─── Defeater and superiority encoding ───────────────────────────────────────

class TestDefeatersAndSuperiority:
    def test_encode_defeater_rule(self):
        enc = PureFormalEncoder()
        r = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
        result = enc.encode_rule(r)
        assert "~flies(X)" in result
        assert "defeater" in result

    def test_encode_theory_with_defeaters(self):
        enc = PureFormalEncoder()
        t = _simple_theory_with_defeater()
        result = enc.encode_theory(t)
        assert "Defeaters" in result
        assert "~flies(X)" in result

    def test_encode_theory_with_superiority(self):
        enc = PureFormalEncoder()
        t = _simple_theory_with_defeater()
        result = enc.encode_theory(t)
        assert "Superiority" in result
        assert "d1 > r1" in result

    def test_encode_theory_no_defeaters_omits_section(self):
        enc = PureFormalEncoder()
        t = Theory()
        t.add_fact("bird(tweety)")
        t.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        result = enc.encode_theory(t)
        assert "Defeaters" not in result
        assert "Superiority" not in result


# ─── encode_instance (Level 1, 2, 3) ─────────────────────────────────────────

class TestEncodeInstance:
    def test_encode_level1_instance(self):
        D_minus = Theory()
        D_minus.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        inst = AbductiveInstance(
            D_minus=D_minus,
            target="flies(tweety)",
            candidates=["bird(tweety)", "penguin(tweety)"],
            gold=["bird(tweety)"],
            level=1,
        )
        enc = PureFormalEncoder()
        result = enc.encode_instance(inst)
        assert "THEORY:" in result
        assert "TARGET: flies(tweety)" in result
        assert "Which fact" in result
        assert "CANDIDATES:" in result
        assert "bird(tweety)" in result

    def test_encode_level2_instance(self):
        D_minus = Theory()
        D_minus.add_fact("bird(tweety)")
        inst = AbductiveInstance(
            D_minus=D_minus,
            target="flies(tweety)",
            candidates=[Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1")],
            gold=[Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1")],
            level=2,
        )
        enc = PureFormalEncoder()
        result = enc.encode_instance(inst)
        assert "Which rule" in result
        assert "ANSWER" in result

    def test_encode_level3_instance(self):
        inst = _level3_instance()
        enc = PureFormalEncoder()
        result = enc.encode_instance(inst)
        assert "defeater" in result.lower() or "exception" in result.lower() or "anomaly" in result.lower()
        assert "CANDIDATES:" in result

    def test_module_level_encode_instance(self):
        """The module-level convenience function works correctly."""
        inst = _level3_instance()
        result = encode_instance(inst)
        assert isinstance(result, str)
        assert "THEORY:" in result

    def test_encode_instance_with_rule_candidates(self):
        """Candidate Rule objects are encoded via encode_rule."""
        inst = _level3_instance()
        enc = PureFormalEncoder()
        result = enc.encode_instance(inst)
        assert "~flies(X)" in result


# ─── _is_well_formed_atom edge cases ─────────────────────────────────────────

class TestWellFormedAtom:
    def test_empty_string_invalid(self):
        enc = PureFormalEncoder()
        assert not enc._is_well_formed_atom("")

    def test_uppercase_start_invalid(self):
        enc = PureFormalEncoder()
        assert not enc._is_well_formed_atom("Bird(tweety)")

    def test_unbalanced_parens_invalid(self):
        enc = PureFormalEncoder()
        assert not enc._is_well_formed_atom("bird(tweety")

    def test_negation_uppercase_invalid(self):
        enc = PureFormalEncoder()
        assert not enc._is_well_formed_atom("~Bird(tweety)")

    def test_valid_negated_atom(self):
        enc = PureFormalEncoder()
        assert enc._is_well_formed_atom("~flies(X)")

    def test_invalid_characters_rejected(self):
        enc = PureFormalEncoder()
        assert not enc._is_well_formed_atom("bird<tweety>")

    def test_malformed_fact_raises(self):
        enc = PureFormalEncoder()
        with pytest.raises(ValueError, match="Malformed fact"):
            enc.encode_fact("INVALID_ATOM")

    def test_malformed_rule_head_raises(self):
        enc = PureFormalEncoder()
        bad_rule = Rule("BADHEAD(X)", ("bird(X)",), RuleType.STRICT, label="r_bad")
        with pytest.raises(ValueError, match="Malformed rule head"):
            enc.encode_rule(bad_rule)

    def test_malformed_body_literal_raises(self):
        enc = PureFormalEncoder()
        bad_rule = Rule("flies(X)", ("BADLITERAL(X)",), RuleType.STRICT, label="r_bad")
        with pytest.raises(ValueError, match="Malformed body literal"):
            enc.encode_rule(bad_rule)

    def test_unknown_rule_type_raises(self):
        """Unknown rule_type raises ValueError in encode_rule."""
        enc = PureFormalEncoder()
        # Inject an unknown type by bypassing the enum
        r = Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1")
        object.__setattr__(r, "rule_type", "unknown_type")
        with pytest.raises(ValueError):
            enc.encode_rule(r)
