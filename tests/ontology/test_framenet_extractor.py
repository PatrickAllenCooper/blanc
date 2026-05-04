"""
Tests for FrameNet extractor.

Mocks the NLTK framenet corpus so tests run without downloading any
data.  Covers inheritance rules, core FE rules, Using presupposition
rules, taxonomy extraction, and the ImportError fallback.

Author: Anonymous Authors
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from blanc.core.theory import RuleType


def _make_frame(name, fes):
    """Build a mock FrameNet frame object."""
    fe_dict = {}
    for fe_name, core_type in fes:
        fe_obj = SimpleNamespace(coreType=core_type)
        fe_dict[fe_name] = fe_obj
    return SimpleNamespace(name=name, FE=fe_dict)


def _make_relation(rel_type, super_name, sub_name):
    """Build a mock FrameNet relation object."""
    return SimpleNamespace(
        type=SimpleNamespace(name=rel_type),
        superFrameName=super_name,
        subFrameName=sub_name,
    )


MOCK_FRAMES = [
    _make_frame("Motion", [("Theme", "Core"), ("Path", "Peripheral")]),
    _make_frame("Self_motion", [("Self_mover", "Core")]),
    _make_frame("Cooking_creation", [("Cook", "Core"), ("Produced_food", "Core")]),
]

MOCK_RELATIONS = [
    _make_relation("Inheritance", "Motion", "Self_motion"),
    _make_relation("Using", "Motion", "Cooking_creation"),
]


@pytest.fixture()
def mock_fn():
    """Patch NLTK framenet corpus for the entire fixture scope."""
    fn_mock = MagicMock()
    fn_mock.frame_ids_and_names.return_value = {1: "Motion", 2: "Self_motion"}
    fn_mock.frames.return_value = MOCK_FRAMES
    fn_mock.frame_relations.return_value = MOCK_RELATIONS

    with patch.dict("sys.modules", {"nltk": MagicMock(), "nltk.corpus": MagicMock()}):
        with patch("blanc.ontology.framenet_extractor.FrameNetExtractor.__init__", return_value=None) as init_mock:
            from blanc.ontology.framenet_extractor import FrameNetExtractor
            ext = FrameNetExtractor.__new__(FrameNetExtractor)
            ext._fn = fn_mock
            ext.frames = []
            ext.relations = []
            yield ext


class TestFrameNetInit:

    def test_import_error_when_nltk_missing(self):
        with patch.dict("sys.modules", {"nltk": None, "nltk.corpus": None}):
            import importlib
            import blanc.ontology.framenet_extractor as mod
            importlib.reload(mod)
            with pytest.raises(ImportError, match="NLTK"):
                mod.FrameNetExtractor()


class TestFrameNetExtraction:

    def test_extract_populates_frames_and_relations(self, mock_fn):
        mock_fn.extract()
        assert len(mock_fn.frames) == 3
        assert len(mock_fn.relations) == 2

    def test_frame_element_names_captured(self, mock_fn):
        mock_fn.extract()
        motion_frame = next(f for f in mock_fn.frames if f["name"] == "Motion")
        fe_names = {fe["name"] for fe in motion_frame["fes"]}
        assert "Theme" in fe_names
        assert "Path" in fe_names

    def test_relation_types_captured(self, mock_fn):
        mock_fn.extract()
        rel_types = {r["type"] for r in mock_fn.relations}
        assert "Inheritance" in rel_types
        assert "Using" in rel_types


class TestFrameNetInheritanceRules:

    def test_inheritance_produces_strict_rules(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        rule = strict[0]
        assert rule.rule_type == RuleType.STRICT
        assert "motion" in rule.head
        assert "self_motion" in rule.body[0]

    def test_inheritance_label_contains_child_parent(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert strict[0].label.startswith("fn_inherit_")

    def test_inheritance_metadata_source(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert strict[0].metadata["source"] == "FrameNet"
        assert strict[0].metadata["relation"] == "Inheritance"


class TestFrameNetCoreFeRules:

    def test_core_fes_produce_defeasible_priority_1(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        core_rules = [r for r in defeasible if r.priority == 1]
        assert len(core_rules) >= 1
        head_contents = " ".join(r.head for r in core_rules)
        assert "has_role_theme" in head_contents or "has_role_self_mover" in head_contents

    def test_peripheral_fe_has_priority_2(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        peripheral = [r for r in defeasible if r.priority == 2]
        assert len(peripheral) >= 1
        assert any("path" in r.head for r in peripheral)

    def test_fe_metadata_contains_core_type(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        fe_rules = [r for r in defeasible if r.metadata.get("core_type")]
        assert len(fe_rules) > 0
        core_types = {r.metadata["core_type"] for r in fe_rules}
        assert "Core" in core_types


class TestFrameNetUsingRules:

    def test_using_produces_defeasible_presupposition(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        using_rules = [r for r in defeasible if r.metadata.get("relation") == "Using"]
        assert len(using_rules) == 1
        assert "presupposes_" in using_rules[0].head

    def test_using_label_prefix(self, mock_fn):
        mock_fn.extract()
        theory = mock_fn.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        using_rules = [r for r in defeasible if r.metadata.get("relation") == "Using"]
        assert using_rules[0].label.startswith("fn_uses_")


class TestFrameNetTaxonomy:

    def test_get_taxonomy_returns_inheritance_mapping(self, mock_fn):
        mock_fn.extract()
        taxonomy = mock_fn.get_taxonomy()
        assert "self_motion" in taxonomy
        assert "motion" in taxonomy["self_motion"]

    def test_get_taxonomy_excludes_using(self, mock_fn):
        mock_fn.extract()
        taxonomy = mock_fn.get_taxonomy()
        assert "cooking_creation" not in taxonomy


class TestFrameNetDeduplication:

    def test_duplicate_relations_produce_single_rule(self, mock_fn):
        mock_fn._fn.frame_relations.return_value = [
            _make_relation("Inheritance", "Motion", "Self_motion"),
            _make_relation("Inheritance", "Motion", "Self_motion"),
        ]
        mock_fn.extract()
        theory = mock_fn.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
