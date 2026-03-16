"""
Tests for expanded behavioral rules across all three domains.

Verifies that each domain's behavioral rules module produces the
expected types of rules (defeasible defaults and defeaters) and that
the rules integrate correctly with the existing taxonomic KBs.

Author: Patrick Cooper
"""

import pytest

from blanc.core.theory import Theory, Rule, RuleType


class TestBiologyBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.biology_behavioral_rules import (
            add_behavioral_rules,
            count_behavioral_rules,
        )
        theory = Theory()
        theory = add_behavioral_rules(theory)
        return theory, count_behavioral_rules(theory)

    def test_defeasible_count_at_least_80(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 80

    def test_defeater_count_at_least_30(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 30

    def test_total_behavioral_at_least_110(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 110

    def test_all_rules_are_defeasible_or_defeater(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.rule_type in (RuleType.DEFEASIBLE, RuleType.DEFEATER)

    def test_penguin_flies_defeater_exists(self):
        theory, _ = self._build()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        penguin_fly = [
            r for r in defeaters
            if "flies" in r.head and "penguin" in str(r.body)
        ]
        assert len(penguin_fly) == 1

    def test_locomotion_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        for pred in ("flies", "swims", "walks", "runs", "crawls"):
            assert pred in heads

    def test_morphology_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        for pred in ("has_feathers", "has_fur", "has_scales", "has_wings"):
            assert pred in heads

    def test_thermoregulation_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_warm_blooded" in heads
        assert "is_cold_blooded" in heads

    def test_reproduction_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "lays_eggs" in heads
        assert "gives_live_birth" in heads

    def test_labels_are_bio_prefixed(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.label.startswith("bio_r")


class TestLegalBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.legal_behavioral_rules import (
            add_legal_behavioral_rules,
            count_legal_behavioral_rules,
        )
        theory = Theory()
        theory = add_legal_behavioral_rules(theory)
        return theory, count_legal_behavioral_rules(theory)

    def test_defeasible_count_at_least_40(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 40

    def test_defeater_count_at_least_25(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 25

    def test_total_behavioral_at_least_65(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 65

    def test_all_rules_are_defeasible_or_defeater(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.rule_type in (RuleType.DEFEASIBLE, RuleType.DEFEATER)

    def test_minor_capacity_defeater_exists(self):
        theory, _ = self._build()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        minor_cap = [
            r for r in defeaters
            if "has_legal_capacity" in r.head and "minor" in str(r.body)
        ]
        assert len(minor_cap) >= 1

    def test_capacity_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        for pred in ("has_legal_capacity", "can_enter_contract", "can_vote"):
            assert pred in heads

    def test_procedural_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "presumed_innocent" in heads
        assert "bears_burden_of_proof" in heads

    def test_liability_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_liable" in heads
        assert "is_criminally_liable" in heads

    def test_labels_are_legal_prefixed(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.label.startswith("legal_r")


class TestMaterialsBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.materials_behavioral_rules import (
            add_materials_behavioral_rules,
            count_materials_behavioral_rules,
        )
        theory = Theory()
        theory = add_materials_behavioral_rules(theory)
        return theory, count_materials_behavioral_rules(theory)

    def test_defeasible_count_at_least_50(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 50

    def test_defeater_count_at_least_25(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 25

    def test_total_behavioral_at_least_75(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 75

    def test_all_rules_are_defeasible_or_defeater(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.rule_type in (RuleType.DEFEASIBLE, RuleType.DEFEATER)

    def test_metallic_glass_brittle_defeater(self):
        theory, _ = self._build()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        mg = [
            r for r in defeaters
            if "brittle" in r.head and "metallic_glass" in str(r.body)
        ]
        assert len(mg) >= 1

    def test_conductivity_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "conducts_electricity" in heads
        assert "conducts_heat" in heads

    def test_mechanical_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_ductile" in heads
        assert "is_brittle" in heads
        assert "is_elastic" in heads

    def test_processing_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "can_be_welded" in heads
        assert "softens_on_annealing" in heads

    def test_labels_are_mat_beh_prefixed(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.label.startswith("mat_beh_r")


class TestKBComposition:
    """Test that behavioral rules integrate with existing KBs."""

    def test_biology_kb_has_defeasible_rules(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 80

    def test_biology_kb_has_defeaters(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 30

    def test_legal_kb_has_defeasible_rules(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 40

    def test_legal_kb_has_defeaters(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 25

    def test_materials_kb_has_defeasible_rules(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 50

    def test_materials_kb_has_defeaters(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 25

    def test_biology_kb_strict_rules_preserved(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) >= 900  # YAGO (584) + WordNet (334)
