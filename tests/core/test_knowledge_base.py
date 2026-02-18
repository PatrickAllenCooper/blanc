"""
Tests for core/knowledge_base.py coverage gaps.

Covers: KnowledgeBase initialization, _create_backend error paths,
load FileNotFoundError, repr (lines 44-48, 64-107, 123-128, 204-206).

Author: Patrick Cooper
Date: 2026-02-18
"""

import pytest
from blanc.core.knowledge_base import KnowledgeBase


class TestKnowledgeBaseInit:
    def test_repr(self):
        """KnowledgeBase repr includes backend name."""
        # We can't instantiate a real backend easily, but we can test
        # the repr by testing _create_backend raises on unknown backend
        # and by checking that repr is defined correctly.
        # Use the class directly without calling __init__ fully.
        kb = object.__new__(KnowledgeBase)
        kb._backend_name = "defeasible"
        assert "defeasible" in repr(kb)

    def test_unknown_backend_raises(self):
        """An unrecognised backend name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown backend"):
            KnowledgeBase(backend="unknown_backend_xyz")

    def test_prolog_backend_unavailable_raises_value_error(self):
        """If prolog dependencies are missing, ValueError is raised (not ImportError)."""
        # This tests the ImportError -> ValueError wrapping (lines 71-74).
        # On systems without SWI-Prolog the PrologBackend will raise ImportError.
        try:
            kb = KnowledgeBase(backend="prolog")
            # If Prolog is available, repr should include it
            assert "prolog" in repr(kb)
        except ValueError as e:
            assert "not available" in str(e)

    def test_load_missing_file_raises(self):
        """load() raises FileNotFoundError for non-existent paths."""
        # First create a KB without a real backend (the defeasible backend
        # may or may not be available); skip if neither backend is available.
        try:
            kb = KnowledgeBase(backend="defeasible")
        except (ValueError, Exception):
            pytest.skip("No available backend for load test")

        with pytest.raises(FileNotFoundError):
            kb.load("/nonexistent/path/that/does/not/exist.pl")


class TestKnowledgeBaseProperties:
    def test_backend_name_property(self):
        kb = object.__new__(KnowledgeBase)
        kb._backend_name = "test_backend"
        assert kb.backend_name == "test_backend"

    def test_repr_format(self):
        kb = object.__new__(KnowledgeBase)
        kb._backend_name = "prolog"
        assert repr(kb) == "KnowledgeBase(backend='prolog')"
