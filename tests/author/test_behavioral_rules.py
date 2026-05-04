"""
Tests for expanded behavioral rules across all three domains.

Verifies that each domain's behavioral rules module produces the
expected types of rules (defeasible defaults and defeaters), includes
multi-body compound rules and superiority relations, and integrates
correctly with the existing taxonomic KBs.

Author: Anonymous Authors
"""

import pytest

from blanc.core.theory import Theory, Rule, RuleType


class TestBiologyBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.biology_behavioral_rules import (
            add_behavioral_rules,
            add_bio_superiority_relations,
            count_behavioral_rules,
        )
        theory = Theory()
        theory = add_behavioral_rules(theory)
        add_bio_superiority_relations(theory)
        return theory, count_behavioral_rules(theory)

    def test_defeasible_count_at_least_150(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 150

    def test_defeater_count_at_least_70(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 70

    def test_total_behavioral_at_least_250(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 250

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

    def test_sensory_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "has_color_vision" in heads
        assert "has_electroreception" in heads

    def test_social_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_social" in heads
        assert "is_solitary" in heads

    def test_defense_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "has_armor" in heads
        assert "uses_mimicry" in heads

    def test_ecological_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_producer" in heads
        assert "is_decomposer" in heads

    def test_multi_body_rules_exist(self):
        theory, _ = self._build()
        multi = [r for r in theory.rules if len(r.body) >= 2]
        assert len(multi) >= 25

    def test_superiority_relations_exist(self):
        theory, _ = self._build()
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 20

    def test_labels_are_bio_prefixed(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.label.startswith("bio_r")


class TestLegalBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.legal_behavioral_rules import (
            add_legal_behavioral_rules,
            add_legal_superiority_relations,
            count_legal_behavioral_rules,
        )
        theory = Theory()
        theory = add_legal_behavioral_rules(theory)
        add_legal_superiority_relations(theory)
        return theory, count_legal_behavioral_rules(theory)

    def test_defeasible_count_at_least_90(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 90

    def test_defeater_count_at_least_55(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 55

    def test_total_behavioral_at_least_160(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 160

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

    def test_constitutional_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "has_free_speech" in heads
        assert "has_privacy_right" in heads

    def test_criminal_law_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "requires_mens_rea" in heads
        assert "eligible_for_bail" in heads

    def test_corporate_law_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "has_limited_liability" in heads

    def test_employment_law_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "entitled_to_minimum_wage" in heads

    def test_multi_body_rules_exist(self):
        theory, _ = self._build()
        multi = [r for r in theory.rules if len(r.body) >= 2]
        assert len(multi) >= 15

    def test_superiority_relations_exist(self):
        theory, _ = self._build()
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 10

    def test_labels_are_legal_prefixed(self):
        theory, _ = self._build()
        for rule in theory.rules:
            assert rule.label.startswith("legal_r")


class TestMaterialsBehavioralRules:

    def _build(self):
        from examples.knowledge_bases.materials_behavioral_rules import (
            add_materials_behavioral_rules,
            add_materials_superiority_relations,
            count_materials_behavioral_rules,
        )
        theory = Theory()
        theory = add_materials_behavioral_rules(theory)
        add_materials_superiority_relations(theory)
        return theory, count_materials_behavioral_rules(theory)

    def test_defeasible_count_at_least_90(self):
        _, counts = self._build()
        assert counts["defeasible"] >= 90

    def test_defeater_count_at_least_55(self):
        _, counts = self._build()
        assert counts["defeaters"] >= 55

    def test_total_behavioral_at_least_160(self):
        _, counts = self._build()
        assert counts["total_behavioral"] >= 160

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

    def test_phase_transition_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_solid_at_room_temp" in heads
        assert "undergoes_glass_transition" in heads

    def test_failure_mode_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "fails_by_fatigue" in heads
        assert "fails_by_creep" in heads

    def test_semiconductor_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "has_band_gap" in heads

    def test_recyclability_rules_present(self):
        theory, _ = self._build()
        heads = {r.head.split("(")[0].lstrip("~") for r in theory.rules}
        assert "is_recyclable" in heads
        assert "is_biodegradable" in heads

    def test_multi_body_rules_exist(self):
        theory, _ = self._build()
        multi = [r for r in theory.rules if len(r.body) >= 2]
        assert len(multi) >= 15

    def test_superiority_relations_exist(self):
        theory, _ = self._build()
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 10

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
        assert len(defeasible) >= 150

    def test_biology_kb_has_defeaters(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 70

    def test_biology_kb_has_superiority(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 20

    def test_legal_kb_has_defeasible_rules(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 90

    def test_legal_kb_has_defeaters(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 55

    def test_legal_kb_has_superiority(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 10

    def test_materials_kb_has_defeasible_rules(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) >= 90

    def test_materials_kb_has_defeaters(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) >= 55

    def test_materials_kb_has_superiority(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        total_sup = sum(len(v) for v in theory.superiority.values())
        assert total_sup >= 10

    def test_biology_kb_strict_rules_preserved(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) >= 900

    def test_combined_multi_body_rules(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        from examples.knowledge_bases.legal_kb import create_legal_kb
        from examples.knowledge_bases.materials_kb import create_materials_kb
        total_mb = 0
        for fn in [create_biology_kb, create_legal_kb, create_materials_kb]:
            t = fn(include_instances=False)
            total_mb += sum(1 for r in t.rules if len(r.body) >= 2)
        assert total_mb >= 60
