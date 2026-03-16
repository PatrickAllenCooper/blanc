"""
Tests for OpenCyc extractor (domain-generic).

The OpenCyc OWL file is not included in the repo, so tests that require
the actual file are skipped.  Tests cover initialization, interface,
domain-profile acceptance, and helper methods.

Author: Patrick Cooper
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch

from blanc.ontology.domain_profiles import BIOLOGY, LEGAL, MATERIALS


class TestOpenCycExtractorInit:

    def test_missing_file_raises_file_not_found(self, tmp_path):
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        with pytest.raises(FileNotFoundError):
            OpenCycExtractor(tmp_path / "nonexistent.owl")

    def test_rdflib_unavailable_raises_import_error(self, tmp_path):
        with patch("blanc.ontology.opencyc_extractor.RDFLIB_AVAILABLE", False):
            from blanc.ontology.opencyc_extractor import OpenCycExtractor
            with pytest.raises(ImportError, match="rdflib"):
                OpenCycExtractor(tmp_path / "anything.owl")


class TestOpenCycExtractorInterface:

    def test_class_has_expected_methods(self):
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        assert hasattr(OpenCycExtractor, "load")
        assert hasattr(OpenCycExtractor, "extract_domain")
        assert hasattr(OpenCycExtractor, "extract_biology")
        assert hasattr(OpenCycExtractor, "to_definite_lp")
        assert hasattr(OpenCycExtractor, "get_taxonomy")

    def test_module_imports(self):
        import blanc.ontology.opencyc_extractor as m
        assert m is not None


class TestDomainProfileAcceptance:

    def test_default_profile_is_biology(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file)
        assert ext.profile.name == "biology"

    def test_accepts_legal_profile(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file, profile=LEGAL)
        assert ext.profile.name == "legal"

    def test_accepts_materials_profile(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file, profile=MATERIALS)
        assert ext.profile.name == "materials"


class TestHelperMethods:

    def test_normalize_for_prolog(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file)
        assert ext._normalize_for_prolog("Bird Species") == "bird_species"
        assert ext._normalize_for_prolog("Can-Fly") == "can_fly"
        assert ext._normalize_for_prolog("123start") == "c_123start"

    def test_extract_concept_name(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file)
        assert ext._extract_concept_name("http://sw.opencyc.org/concept/Bird") == "Bird"
        assert ext._extract_concept_name("http://example.org#Animal") == "Animal"


class TestExtractBiologyFromOpencyc:

    def test_missing_file_raises(self, tmp_path):
        from blanc.ontology.opencyc_extractor import extract_biology_from_opencyc
        with pytest.raises(FileNotFoundError):
            extract_biology_from_opencyc(tmp_path / "nonexistent.owl")

    def test_function_is_callable(self):
        from blanc.ontology.opencyc_extractor import extract_biology_from_opencyc
        assert callable(extract_biology_from_opencyc)


class TestExtractFromOpencyc:

    def test_function_exists(self):
        from blanc.ontology.opencyc_extractor import extract_from_opencyc
        assert callable(extract_from_opencyc)

    def test_missing_file_raises(self, tmp_path):
        from blanc.ontology.opencyc_extractor import extract_from_opencyc
        with pytest.raises(FileNotFoundError):
            extract_from_opencyc(tmp_path / "nope.owl", profile=LEGAL)


class TestBackwardCompatibility:

    def test_biological_concepts_alias(self, tmp_path):
        owl_file = tmp_path / "test.owl"
        owl_file.write_text("<rdf:RDF/>")
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        ext = OpenCycExtractor(owl_file)
        assert ext.biological_concepts is ext.domain_concepts
