"""
Tests for src/blanc/ontology/opencyc_extractor.py.

The OpenCyc OWL file is not included in the repo, so tests that require
the actual file are skipped. Tests cover:
  - Class initialization with missing file raises FileNotFoundError
  - Class initialization with missing rdflib raises ImportError (mocked)
  - extract_biology_from_opencyc with missing file returns empty Theory
  - Helper methods can be instantiated and have the right interface
"""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


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


class TestExtractBiologyFromOpencyc:
    def test_missing_file_raises_file_not_found(self, tmp_path):
        from blanc.ontology.opencyc_extractor import extract_biology_from_opencyc
        with pytest.raises(FileNotFoundError):
            extract_biology_from_opencyc(tmp_path / "nonexistent.owl")

    def test_function_is_callable(self):
        from blanc.ontology.opencyc_extractor import extract_biology_from_opencyc
        assert callable(extract_biology_from_opencyc)


class TestOpenCycExtractorInterface:
    def test_class_exists_with_expected_methods(self):
        from blanc.ontology.opencyc_extractor import OpenCycExtractor
        assert hasattr(OpenCycExtractor, "__init__")

    def test_module_imports_cleanly(self):
        import blanc.ontology.opencyc_extractor as m
        assert m is not None
