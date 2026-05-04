"""
Tests for Level 3 metrics: predicate_novelty, check_conservativity,
revision_distance (blanc.author.metrics).

Author: Anonymous Authors
Date: 2026-02-18
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable
from blanc.author.metrics import (
    predicate_novelty,
    check_conservativity,
    revision_distance,
    _theory_predicates,
)


# ─── Fixtures ────────────────────────────────────────────────────────────────

def _bird_theory() -> Theory:
    """Base: bird(tweety), sparrow(tweety), r1: bird(X)=>flies(X)."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_fact("sparrow(tweety)")
    t.add_fact("bird(opus)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r_flies"))
    t.add_rule(Rule("has_feathers(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r_feat"))
    return t


def _full_theory(base: Theory, defeater: Rule, beaten: str) -> Theory:
    """Copy base, add defeater with superiority over beaten rule."""
    from blanc.core.theory import Theory as T
    full = T()
    for f in base.facts:
        full.add_fact(f)
    for r in base.rules:
        full.add_rule(Rule(r.head, r.body, r.rule_type, label=r.label))
    full.add_rule(defeater)
    full.add_superiority(defeater.label, beaten)
    return full


# ─── _theory_predicates ──────────────────────────────────────────────────────

class TestTheoryPredicates:
    def test_collects_fact_predicates(self):
        t = Theory()
        t.add_fact("bird(tweety)")
        t.add_fact("penguin(opus)")
        preds = _theory_predicates(t)
        assert "bird" in preds
        assert "penguin" in preds

    def test_collects_rule_head_and_body_predicates(self):
        t = Theory()
        t.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        preds = _theory_predicates(t)
        assert "flies" in preds
        assert "bird" in preds

    def test_strips_negation(self):
        t = Theory()
        t.add_rule(Rule("~walks(X)", ("whale(X)",), RuleType.DEFEATER, label="d1"))
        preds = _theory_predicates(t)
        assert "walks" in preds
        assert "~walks" not in preds

    def test_empty_theory(self):
        assert _theory_predicates(Theory()) == set()


# ─── predicate_novelty ───────────────────────────────────────────────────────

class TestPredicateNovelty:
    def test_zero_novelty_all_known_predicates(self):
        """Gold rule uses only predicates already in D^-."""
        base = _bird_theory()
        gold = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d_peng")
        assert predicate_novelty(gold, base) == 0.0

    def test_full_novelty_entirely_new_predicate(self):
        """Gold rule body uses a predicate not in D^- at all."""
        base = Theory()
        base.add_fact("fish(lenny)")
        base.add_rule(Rule("swims(X)", ("fish(X)",), RuleType.DEFEASIBLE, label="r1"))
        # 'has_accessory_lung' is not in base
        gold = Rule("~swims(X)", ("has_accessory_lung(X)",), RuleType.DEFEATER, label="d1")
        # rule_preds = {swims, has_accessory_lung}; novel = {has_accessory_lung}
        nov = predicate_novelty(gold, base)
        assert nov == 0.5  # 1 novel out of 2

    def test_full_novelty_both_predicates_new(self):
        """Both head and body predicates are novel."""
        base = Theory()
        base.add_fact("x(a)")
        gold = Rule("~novel_head(X)", ("novel_body(X)",), RuleType.DEFEATER, label="d1")
        nov = predicate_novelty(gold, base)
        assert nov == 1.0

    def test_partial_novelty(self):
        """Head known, body novel: Nov = 0.5."""
        base = Theory()
        base.add_fact("known(a)")
        base.add_rule(Rule("known(X)", ("a(X)",), RuleType.DEFEASIBLE, label="r1"))
        gold = Rule("~known(X)", ("brand_new_pred(X)",), RuleType.DEFEATER, label="d1")
        # rule_preds = {known, brand_new_pred}; novel = {brand_new_pred}
        nov = predicate_novelty(gold, base)
        assert nov == 0.5

    def test_negation_does_not_create_false_novelty(self):
        """~flies is NOT a new predicate; it maps to 'flies' which is known."""
        base = Theory()
        base.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        gold = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d1")
        assert predicate_novelty(gold, base) == 0.0


# ─── check_conservativity ────────────────────────────────────────────────────

class TestCheckConservativity:
    def test_conservative_defeater(self):
        """Adding penguin defeater preserves tweety's flight."""
        base = _bird_theory()
        defeater = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
        full = _full_theory(base, defeater, "r_flies")

        preserved = ["flies(tweety)", "has_feathers(tweety)", "has_feathers(opus)"]
        is_cons, lost = check_conservativity(base, full, "flies(opus)", preserved)

        assert is_cons
        assert lost == []

    def test_non_conservative_too_broad_defeater(self):
        """Defeater blocking ALL birds is non-conservative (loses tweety)."""
        base = _bird_theory()
        broad = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d_broad")
        full = _full_theory(base, broad, "r_flies")

        preserved = ["flies(tweety)"]
        is_cons, lost = check_conservativity(base, full, "flies(opus)", preserved)

        assert not is_cons
        assert "flies(tweety)" in lost

    def test_anomaly_excluded_from_loss_check(self):
        """The anomaly itself is not counted as a lost expectation."""
        base = _bird_theory()
        defeater = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
        full = _full_theory(base, defeater, "r_flies")

        # Include the anomaly itself in preserved list - should be skipped
        preserved = ["flies(opus)", "flies(tweety)"]
        is_cons, lost = check_conservativity(base, full, "flies(opus)", preserved)

        assert is_cons
        assert "flies(opus)" not in lost

    def test_empty_preserved_is_always_conservative(self):
        """If there are no preserved expectations to check, result is trivially conservative."""
        base = _bird_theory()
        defeater = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d_broad")
        full = _full_theory(base, defeater, "r_flies")

        is_cons, lost = check_conservativity(base, full, "flies(opus)", [])
        assert is_cons
        assert lost == []

    def test_returns_all_lost_expectations(self):
        """Multiple lost expectations are all reported."""
        base = Theory()
        base.add_fact("bird(a)")
        base.add_fact("bird(b)")
        base.add_fact("bird(c)")
        base.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))

        # Broad defeater kills all
        full = Theory()
        for f in base.facts:
            full.add_fact(f)
        for r in base.rules:
            full.add_rule(Rule(r.head, r.body, r.rule_type, label=r.label))
        broad = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d_broad")
        full.add_rule(broad)
        full.add_superiority("d_broad", "r1")

        preserved = ["flies(a)", "flies(b)", "flies(c)"]
        is_cons, lost = check_conservativity(base, full, "flies(x)", preserved)

        assert not is_cons
        assert set(lost) == {"flies(a)", "flies(b)", "flies(c)"}


# ─── revision_distance ───────────────────────────────────────────────────────

class TestRevisionDistance:
    def test_conservative_defeater_distance_one(self):
        """A conservative defeater adds 1 element and loses 0: d_rev = 1."""
        base = _bird_theory()
        defeater = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
        full = _full_theory(base, defeater, "r_flies")

        preserved = ["flies(tweety)", "has_feathers(tweety)"]
        d = revision_distance(base, full, "flies(opus)", preserved)
        assert d == 1

    def test_non_conservative_defeater_higher_distance(self):
        """Broad defeater adds 1 element but loses expectations: d_rev > 1."""
        base = _bird_theory()
        broad = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d_broad")
        full = _full_theory(base, broad, "r_flies")

        preserved = ["flies(tweety)", "has_feathers(tweety)"]
        d = revision_distance(base, full, "flies(opus)", preserved)
        # Added 1 element + lost flies(tweety)
        assert d == 2

    def test_same_theory_zero_distance(self):
        """Identical theories have d_rev = 0."""
        base = _bird_theory()
        import copy
        same = Theory()
        for f in base.facts:
            same.add_fact(f)
        for r in base.rules:
            same.add_rule(Rule(r.head, r.body, r.rule_type, label=r.label))

        preserved = ["flies(tweety)"]
        d = revision_distance(base, same, "dummy_anomaly", preserved)
        assert d == 0


# ─── Integration: penguin instance ───────────────────────────────────────────

class TestLevel3MetricsIntegration:
    """End-to-end validation of a penguin Level 3 instance."""

    def setup_method(self):
        self.base = Theory()
        self.base.add_fact("bird(tweety)")
        self.base.add_fact("sparrow(tweety)")
        self.base.add_fact("bird(opus)")
        self.base.add_fact("penguin(opus)")
        self.base.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r1"))
        self.base.add_rule(Rule("has_feathers(X)", ("bird(X)",), RuleType.DEFEASIBLE, label="r2"))

        self.gold = Rule("~flies(X)", ("penguin(X)",), RuleType.DEFEATER, label="d1")
        self.full = _full_theory(self.base, self.gold, "r1")
        self.preserved = ["flies(tweety)", "has_feathers(tweety)", "has_feathers(opus)"]

    def test_anomaly_provable_in_base(self):
        assert defeasible_provable(self.base, "flies(opus)")

    def test_gold_blocks_anomaly(self):
        assert not defeasible_provable(self.full, "flies(opus)")

    def test_gold_is_conservative(self):
        is_cons, lost = check_conservativity(
            self.base, self.full, "flies(opus)", self.preserved
        )
        assert is_cons
        assert lost == []

    def test_gold_novelty_is_zero(self):
        # penguin and flies are both in base
        assert predicate_novelty(self.gold, self.base) == 0.0

    def test_revision_distance_is_one(self):
        d = revision_distance(self.base, self.full, "flies(opus)", self.preserved)
        assert d == 1

    def test_broad_distractor_is_non_conservative(self):
        broad = Rule("~flies(X)", ("bird(X)",), RuleType.DEFEATER, label="d_broad")
        full_broad = _full_theory(self.base, broad, "r1")
        is_cons, lost = check_conservativity(
            self.base, full_broad, "flies(opus)", self.preserved
        )
        assert not is_cons
        assert "flies(tweety)" in lost

    def test_novel_defeater_novelty(self):
        """A defeater using an absent predicate has Nov > 0."""
        novel_gold = Rule(
            "~flies(X)", ("has_vestigial_wings(X)",), RuleType.DEFEATER, label="d_novel"
        )
        nov = predicate_novelty(novel_gold, self.base)
        assert nov > 0.0
