"""Coverage tests for core/knowledge_base.py uncovered paths."""

import pytest

from blanc.core.knowledge_base import KnowledgeBase


class TestCreateBackendErrors:
    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            KnowledgeBase(backend="nonexistent")

    def test_prolog_backend_import_error(self):
        with pytest.raises(ValueError, match="Prolog backend not available"):
            KnowledgeBase(backend="prolog")

    def test_asp_backend_import_error(self):
        with pytest.raises(ValueError, match="ASP backend not available"):
            KnowledgeBase(backend="asp")

    def test_defeasible_backend_import_error(self):
        with pytest.raises(ValueError, match="Defeasible backend not available"):
            KnowledgeBase(backend="defeasible")

    def test_rulelog_backend_import_error(self):
        with pytest.raises(ValueError, match="Rulelog backend not available"):
            KnowledgeBase(backend="rulelog")
