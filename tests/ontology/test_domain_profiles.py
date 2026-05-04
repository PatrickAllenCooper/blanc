"""
Tests for domain profile system.

Author: Anonymous Authors
"""

import pytest

from blanc.ontology.domain_profiles import (
    BIOLOGY,
    LEGAL,
    MATERIALS,
    CHEMISTRY,
    EVERYDAY,
    ALL_PROFILES,
    DomainProfile,
    RelationMapping,
    get_profile,
    combined_keywords,
)


class TestDomainProfileDataclass:

    def test_biology_profile_exists(self):
        assert BIOLOGY.name == "biology"
        assert len(BIOLOGY.keywords) > 0

    def test_legal_profile_exists(self):
        assert LEGAL.name == "legal"
        assert len(LEGAL.keywords) > 0

    def test_materials_profile_exists(self):
        assert MATERIALS.name == "materials"
        assert len(MATERIALS.keywords) > 0

    def test_chemistry_profile_exists(self):
        assert CHEMISTRY.name == "chemistry"
        assert len(CHEMISTRY.keywords) > 0

    def test_everyday_profile_exists(self):
        assert EVERYDAY.name == "everyday"
        assert len(EVERYDAY.keywords) > 0

    def test_profiles_are_frozen(self):
        with pytest.raises(AttributeError):
            BIOLOGY.name = "other"

    def test_all_profiles_registry(self):
        assert len(ALL_PROFILES) == 5
        assert set(ALL_PROFILES.keys()) == {
            "biology", "legal", "materials", "chemistry", "everyday"
        }


class TestDomainProfileMatches:

    def test_biology_matches_bird(self):
        assert BIOLOGY.matches("bird")
        assert BIOLOGY.matches("A bird flies")

    def test_biology_does_not_match_contract(self):
        assert not BIOLOGY.matches("contract")
        assert not BIOLOGY.matches("A valid contract")

    def test_legal_matches_contract(self):
        assert LEGAL.matches("contract")
        assert LEGAL.matches("The court ruled")

    def test_legal_does_not_match_bird(self):
        assert not LEGAL.matches("bird")

    def test_materials_matches_metal(self):
        assert MATERIALS.matches("metal")
        assert MATERIALS.matches("Stainless steel alloy")

    def test_chemistry_matches_acid(self):
        assert CHEMISTRY.matches("acid")
        assert CHEMISTRY.matches("Molecular compound")

    def test_everyday_matches_chair(self):
        assert EVERYDAY.matches("chair")
        assert EVERYDAY.matches("A wooden table")

    def test_case_insensitive(self):
        assert BIOLOGY.matches("BIRD")
        assert BIOLOGY.matches("Bird")


class TestGetProfile:

    def test_valid_names(self):
        for name in ("biology", "legal", "materials", "chemistry", "everyday"):
            profile = get_profile(name)
            assert profile.name == name

    def test_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown domain"):
            get_profile("astronomy")


class TestCombinedKeywords:

    def test_single_domain(self):
        kw = combined_keywords("biology")
        assert kw == BIOLOGY.keywords

    def test_multiple_domains(self):
        kw = combined_keywords("biology", "legal")
        assert BIOLOGY.keywords.issubset(kw)
        assert LEGAL.keywords.issubset(kw)

    def test_returns_frozenset(self):
        kw = combined_keywords("biology")
        assert isinstance(kw, frozenset)


class TestRelationMapping:

    def test_common_relations_include_causes_usedfor(self):
        rel_names = {rm.relation for rm in BIOLOGY.relation_mappings}
        assert "Causes" in rel_names
        assert "UsedFor" in rel_names
        assert "CapableOf" in rel_names
        assert "NotCapableOf" in rel_names
        assert "HasProperty" in rel_names
        assert "IsA" in rel_names

    def test_all_profiles_share_relations(self):
        for profile in ALL_PROFILES.values():
            rel_names = {rm.relation for rm in profile.relation_mappings}
            assert "CapableOf" in rel_names
            assert "NotCapableOf" in rel_names


class TestProfileContent:

    def test_biology_has_opencyc_roots(self):
        assert len(BIOLOGY.opencyc_roots) > 0
        assert "Animal" in BIOLOGY.opencyc_roots

    def test_biology_has_behavioral_predicates(self):
        assert "flies" in BIOLOGY.behavioral_predicates
        assert "swims" in BIOLOGY.behavioral_predicates

    def test_biology_has_known_exceptions(self):
        assert ("flies", "penguin") in BIOLOGY.known_exceptions

    def test_legal_has_known_exceptions(self):
        assert ("can_contract", "minor") in LEGAL.known_exceptions

    def test_materials_has_known_exceptions(self):
        assert ("is_brittle", "metallic_glass") in MATERIALS.known_exceptions
