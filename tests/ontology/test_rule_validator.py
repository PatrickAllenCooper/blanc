"""
Tests for rule validation framework.

Author: Anonymous Authors
"""

import json
import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.rule_validator import (
    ValidationReport,
    validate_theory,
    deduplicate_theory,
    save_report,
)


def _simple_theory():
    """A small theory with strict + defeasible + defeater rules."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule(
        head="animal(X)", body=("bird(X)",),
        rule_type=RuleType.STRICT, label="r_tax",
    ))
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r_flies",
    ))
    t.add_rule(Rule(
        head="~flies(X)", body=("penguin(X)",),
        rule_type=RuleType.DEFEATER, label="d_flies_penguin",
    ))
    return t


class TestValidateTheory:

    def test_counts_rule_types(self):
        report = validate_theory(_simple_theory())
        assert report.strict_rules == 1
        assert report.defeasible_rules == 1
        assert report.defeaters == 1
        assert report.total_rules == 3

    def test_counts_facts(self):
        report = validate_theory(_simple_theory())
        assert report.total_facts == 2

    def test_no_duplicates_in_simple(self):
        report = validate_theory(_simple_theory())
        assert report.duplicate_count == 0
        assert report.duplicates == []

    def test_detects_duplicates(self):
        t = _simple_theory()
        t.add_rule(Rule(
            head="flies(X)", body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE, label="r_flies_dup",
        ))
        report = validate_theory(t)
        assert report.duplicate_count == 1

    def test_predicate_coverage(self):
        report = validate_theory(_simple_theory())
        assert "animal" in report.predicates
        assert "flies" in report.predicates
        assert report.predicate_count >= 2

    def test_contradiction_detection(self):
        report = validate_theory(_simple_theory())
        assert report.contradiction_count >= 1
        assert report.anomaly_pairs >= 1

    def test_depth_estimation(self):
        t = Theory()
        t.add_fact("a(x)")
        t.add_rule(Rule(head="b(x)", body=("a(x)",),
                        rule_type=RuleType.STRICT, label="r1"))
        t.add_rule(Rule(head="c(x)", body=("b(x)",),
                        rule_type=RuleType.STRICT, label="r2"))
        report = validate_theory(t)
        assert report.max_depth >= 2

    def test_healthy_theory(self):
        report = validate_theory(_simple_theory())
        assert report.is_healthy

    def test_unhealthy_no_defeasible(self):
        t = Theory()
        t.add_rule(Rule(head="a(X)", body=("b(X)",),
                        rule_type=RuleType.STRICT, label="r1"))
        report = validate_theory(t)
        assert not report.is_healthy

    def test_empty_theory(self):
        report = validate_theory(Theory())
        assert report.total_rules == 0
        assert report.total_facts == 0
        assert not report.is_healthy


class TestValidationReportOutput:

    def test_to_dict(self):
        report = validate_theory(_simple_theory())
        d = report.to_dict()
        assert isinstance(d, dict)
        assert "total_rules" in d
        assert "is_healthy" in d

    def test_summary_string(self):
        report = validate_theory(_simple_theory())
        s = report.summary()
        assert "Validation Report" in s
        assert "Healthy" in s


class TestDeduplicate:

    def test_removes_duplicates(self):
        t = _simple_theory()
        t.add_rule(Rule(
            head="flies(X)", body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE, label="r_flies_dup",
        ))
        assert len(t.rules) == 4
        clean = deduplicate_theory(t)
        assert len(clean.rules) == 3

    def test_preserves_facts(self):
        t = _simple_theory()
        clean = deduplicate_theory(t)
        assert clean.facts == t.facts

    def test_no_change_when_no_duplicates(self):
        t = _simple_theory()
        clean = deduplicate_theory(t)
        assert len(clean.rules) == len(t.rules)


class TestSaveReport:

    def test_saves_json(self):
        report = validate_theory(_simple_theory())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            save_report(report, path)
            assert path.exists()
            with open(path) as f:
                data = json.load(f)
            assert data["total_rules"] == 3

    def test_creates_parent_dirs(self):
        report = validate_theory(_simple_theory())
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sub" / "dir" / "report.json"
            save_report(report, path)
            assert path.exists()


class TestDepthHistogram:

    def test_histogram_sums_to_facts_plus_derived(self):
        t = Theory()
        t.add_fact("a(x)")
        t.add_rule(Rule(head="b(x)", body=("a(x)",),
                        rule_type=RuleType.STRICT, label="r1"))
        t.add_rule(Rule(head="c(x)", body=("b(x)",),
                        rule_type=RuleType.STRICT, label="r2"))
        report = validate_theory(t)
        assert 0 in report.depth_histogram
        assert sum(report.depth_histogram.values()) >= 3


class TestDomainCoverage:

    def test_biology_label_detection(self):
        t = Theory()
        t.add_rule(Rule(head="flies(X)", body=("bird(X)",),
                        rule_type=RuleType.DEFEASIBLE, label="bio_r1000"))
        t.add_rule(Rule(head="~flies(X)", body=("penguin(X)",),
                        rule_type=RuleType.DEFEATER, label="bio_r1001"))
        report = validate_theory(t)
        assert report.domain_coverage.get("biology", 0) == 2

    def test_legal_label_detection(self):
        t = Theory()
        t.add_rule(Rule(head="can_vote(X)", body=("adult(X)",),
                        rule_type=RuleType.DEFEASIBLE, label="legal_r2000"))
        report = validate_theory(t)
        assert report.domain_coverage.get("legal", 0) == 1

    def test_materials_label_detection(self):
        t = Theory()
        t.add_rule(Rule(head="conducts(X)", body=("metal(X)",),
                        rule_type=RuleType.DEFEASIBLE, label="mat_beh_r3000"))
        report = validate_theory(t)
        assert report.domain_coverage.get("materials", 0) == 1
