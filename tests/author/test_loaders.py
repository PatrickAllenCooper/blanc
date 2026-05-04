"""
Tests for src/blanc/author/loaders.py (currently 0% coverage).

Covers:
  - _build_placeholder_theory
  - _reconstruct_theory_from_level3
  - load_level2_instances
  - load_level3_instances
  - load_instances_from_json

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from blanc.author.loaders import (
    load_level2_instances,
    load_level3_instances,
    load_instances_from_json,
    _build_placeholder_theory,
    _reconstruct_theory_from_level3,
)
from blanc.core.theory import RuleType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def l2_instance_item():
    return {
        "target": "flies(tweety)",
        "candidates": ["flies(tweety)", "swims(tweety)"],
        "gold": ["flies(tweety)"],
        "level": 2,
        "metadata": {
            "instance_id": "bio-l2-0001",
            "domain": "biology",
            "facts": ["bird(tweety)"],
            "rules": [
                {
                    "head": "flies(X)",
                    "body": ["bird(X)"],
                    "rule_type": "defeasible",
                    "label": "r1",
                }
            ],
        },
    }


@pytest.fixture
def l3_instance_item():
    return {
        "name": "bio-l3-001",
        "anomaly": "not_flies(tweety)",
        "candidates": ["penguin(tweety)", "broken_wing(tweety)"],
        "gold": "penguin(tweety)",
        "domain": "biology",
        "nov": 0.5,
        "d_rev": 2,
        "conservative": True,
        "theory_facts": ["bird(tweety)", "normal(tweety)"],
        "theory_rules": [
            "r1: bird(X) => flies(X)",
            "r2: penguin(X) ~> flies(X)",
            "r3: normal(X) :- living(X)",
        ],
    }


@pytest.fixture
def l2_instances_dir(tmp_path, l2_instance_item):
    data = {"instances": [l2_instance_item, l2_instance_item]}
    (tmp_path / "biology_dev_instances.json").write_text(json.dumps(data))
    return tmp_path


@pytest.fixture
def l3_instances_dir(tmp_path, l3_instance_item):
    data = {"instances": [l3_instance_item]}
    (tmp_path / "level3_instances.json").write_text(json.dumps(data))
    return tmp_path


@pytest.fixture
def combined_instances_dir(tmp_path, l2_instance_item, l3_instance_item):
    l2_data = {"instances": [l2_instance_item]}
    (tmp_path / "biology_dev_instances.json").write_text(json.dumps(l2_data))
    (tmp_path / "legal_dev_instances.json").write_text(json.dumps({"instances": []}))
    (tmp_path / "materials_dev_instances.json").write_text(json.dumps({"instances": []}))
    l3_data = {"instances": [l3_instance_item]}
    (tmp_path / "level3_instances.json").write_text(json.dumps(l3_data))
    return tmp_path


# ---------------------------------------------------------------------------
# _build_placeholder_theory
# ---------------------------------------------------------------------------

class TestBuildPlaceholderTheory:
    def test_builds_from_metadata_with_rules(self, l2_instance_item):
        theory = _build_placeholder_theory(l2_instance_item)
        assert theory is not None
        assert len(theory.facts) >= 0  # facts may be present

    def test_includes_facts(self, l2_instance_item):
        theory = _build_placeholder_theory(l2_instance_item)
        # biology KB includes bird(tweety) fact
        assert "bird(tweety)" in theory.facts

    def test_includes_rules(self, l2_instance_item):
        theory = _build_placeholder_theory(l2_instance_item)
        assert len(theory.rules) == 1
        rule = theory.rules[0]
        assert rule.head == "flies(X)"
        assert rule.body == ("bird(X)",)
        assert rule.rule_type == RuleType.DEFEASIBLE
        assert rule.label == "r1"

    def test_empty_metadata(self):
        theory = _build_placeholder_theory({"metadata": {}})
        assert len(theory.facts) == 0
        assert len(theory.rules) == 0

    def test_missing_metadata_key(self):
        theory = _build_placeholder_theory({})
        assert theory is not None

    def test_non_dict_rule_is_skipped(self):
        item = {
            "metadata": {
                "facts": [],
                "rules": ["not_a_dict"],
            }
        }
        theory = _build_placeholder_theory(item)
        assert len(theory.rules) == 0


# ---------------------------------------------------------------------------
# _reconstruct_theory_from_level3
# ---------------------------------------------------------------------------

class TestReconstructTheoryFromLevel3:
    def test_defeasible_rule(self, l3_instance_item):
        theory = _reconstruct_theory_from_level3(l3_instance_item)
        labels = {r.label for r in theory.rules}
        assert "r1" in labels
        r1 = next(r for r in theory.rules if r.label == "r1")
        assert r1.rule_type == RuleType.DEFEASIBLE
        assert r1.head == "flies(X)"

    def test_defeater_rule(self, l3_instance_item):
        theory = _reconstruct_theory_from_level3(l3_instance_item)
        labels = {r.label: r for r in theory.rules}
        assert "r2" in labels
        assert labels["r2"].rule_type == RuleType.DEFEATER

    def test_strict_rule(self, l3_instance_item):
        theory = _reconstruct_theory_from_level3(l3_instance_item)
        labels = {r.label: r for r in theory.rules}
        assert "r3" in labels
        assert labels["r3"].rule_type == RuleType.STRICT

    def test_facts_included(self, l3_instance_item):
        theory = _reconstruct_theory_from_level3(l3_instance_item)
        assert "bird(tweety)" in theory.facts
        assert "normal(tweety)" in theory.facts

    def test_no_label_rule(self):
        item = {
            "theory_facts": [],
            "theory_rules": ["bird(X) => flies(X)"],
        }
        theory = _reconstruct_theory_from_level3(item)
        assert len(theory.rules) == 1
        assert theory.rules[0].label is None
        assert theory.rules[0].rule_type == RuleType.DEFEASIBLE

    def test_bare_atom_rule(self):
        """Rules with no arrow become strict rules with empty body."""
        item = {
            "theory_facts": [],
            "theory_rules": ["lbl: bare_atom"],
        }
        theory = _reconstruct_theory_from_level3(item)
        assert len(theory.rules) == 1
        assert theory.rules[0].head == "bare_atom"
        assert theory.rules[0].body == ()
        assert theory.rules[0].rule_type == RuleType.STRICT

    def test_empty_input(self):
        theory = _reconstruct_theory_from_level3({})
        assert len(theory.facts) == 0
        assert len(theory.rules) == 0

    def test_multi_body_rule(self):
        item = {
            "theory_facts": [],
            "theory_rules": ["r1: bird(X), normal(X) => flies(X)"],
        }
        theory = _reconstruct_theory_from_level3(item)
        assert theory.rules[0].body == ("bird(X)", "normal(X)")


# ---------------------------------------------------------------------------
# load_level2_instances
# ---------------------------------------------------------------------------

class TestLoadLevel2Instances:
    def test_loads_instances(self, l2_instances_dir):
        instances = load_level2_instances("biology", l2_instances_dir)
        assert len(instances) == 2

    def test_instance_fields(self, l2_instances_dir):
        instances = load_level2_instances("biology", l2_instances_dir)
        inst = instances[0]
        assert inst.target == "flies(tweety)"
        assert inst.level == 2
        assert "flies(tweety)" in inst.candidates
        assert "flies(tweety)" in inst.gold

    def test_instance_id_from_metadata(self, l2_instances_dir):
        instances = load_level2_instances("biology", l2_instances_dir)
        assert instances[0].id == "bio-l2-0001"

    def test_instance_id_fallback(self, tmp_path):
        item = {
            "target": "q",
            "candidates": ["q"],
            "gold": ["q"],
            "level": 2,
            "metadata": {},
        }
        (tmp_path / "biology_dev_instances.json").write_text(
            json.dumps({"instances": [item]})
        )
        instances = load_level2_instances("biology", tmp_path)
        assert instances[0].id.startswith("biology-l2-")

    def test_limit_applied(self, l2_instances_dir):
        instances = load_level2_instances("biology", l2_instances_dir, limit=1)
        assert len(instances) == 1

    def test_missing_file_returns_empty(self, tmp_path):
        instances = load_level2_instances("biology", tmp_path)
        assert instances == []

    def test_theory_built(self, l2_instances_dir):
        instances = load_level2_instances("biology", l2_instances_dir)
        assert instances[0].D_minus is not None
        assert "bird(tweety)" in instances[0].D_minus.facts


# ---------------------------------------------------------------------------
# load_level3_instances
# ---------------------------------------------------------------------------

class TestLoadLevel3Instances:
    def test_loads_instances(self, l3_instances_dir):
        instances = load_level3_instances(l3_instances_dir)
        assert len(instances) == 1

    def test_instance_fields(self, l3_instances_dir):
        inst = load_level3_instances(l3_instances_dir)[0]
        assert inst.level == 3
        assert inst.target == "not_flies(tweety)"
        assert inst.gold == ["penguin(tweety)"]

    def test_instance_id(self, l3_instances_dir):
        inst = load_level3_instances(l3_instances_dir)[0]
        assert inst.id == "l3-bio-l3-001"

    def test_metadata_fields(self, l3_instances_dir):
        inst = load_level3_instances(l3_instances_dir)[0]
        assert inst.metadata["domain"] == "biology"
        assert inst.metadata["nov"] == 0.5
        assert inst.metadata["d_rev"] == 2
        assert inst.metadata["conservative"] is True

    def test_limit_applied(self, l3_instances_dir):
        instances = load_level3_instances(l3_instances_dir, limit=0)
        assert len(instances) == 0

    def test_missing_file_returns_empty(self, tmp_path):
        instances = load_level3_instances(tmp_path)
        assert instances == []

    def test_theory_reconstructed(self, l3_instances_dir):
        inst = load_level3_instances(l3_instances_dir)[0]
        assert inst.D_minus is not None
        assert "bird(tweety)" in inst.D_minus.facts


# ---------------------------------------------------------------------------
# load_instances_from_json
# ---------------------------------------------------------------------------

class TestLoadInstancesFromJson:
    def test_loads_both_levels(self, combined_instances_dir):
        instances = load_instances_from_json(combined_instances_dir)
        levels = {i.level for i in instances}
        assert 2 in levels
        assert 3 in levels

    def test_excludes_level3_when_disabled(self, combined_instances_dir):
        instances = load_instances_from_json(
            combined_instances_dir, include_level3=False
        )
        assert all(i.level == 2 for i in instances)

    def test_domain_filter(self, combined_instances_dir):
        instances = load_instances_from_json(
            combined_instances_dir, domains=["biology"]
        )
        l2 = [i for i in instances if i.level == 2]
        assert len(l2) == 1

    def test_level2_limit(self, combined_instances_dir):
        instances = load_instances_from_json(
            combined_instances_dir, level2_limit=0, include_level3=False
        )
        l2 = [i for i in instances if i.level == 2]
        assert len(l2) == 0

    def test_level3_limit(self, combined_instances_dir):
        instances = load_instances_from_json(
            combined_instances_dir, level3_limit=0
        )
        l3 = [i for i in instances if i.level == 3]
        assert len(l3) == 0

    def test_accepts_string_path(self, combined_instances_dir):
        instances = load_instances_from_json(str(combined_instances_dir))
        assert len(instances) > 0

    def test_empty_dir_returns_empty(self, tmp_path):
        instances = load_instances_from_json(tmp_path)
        assert instances == []

    def test_default_domains(self, combined_instances_dir):
        instances = load_instances_from_json(combined_instances_dir, include_level3=False)
        assert isinstance(instances, list)
