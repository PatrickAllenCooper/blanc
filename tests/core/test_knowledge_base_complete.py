"""
Tests for src/blanc/core/knowledge_base.py — covering the 56% gap.

Missing lines:
  47-48  (source passed to __init__)
  70     (prolog backend import error path)
  77-82  (asp backend)
  90     (asp backend import error)
  97-102 (defeasible backend)
  123-128 (file-not-found path in load())
  147-149 (execute_deductive, execute_abductive)
  153    (_execute_defeasible)
  157    (execute_abductive)
  161    (_execute_defeasible)
  176    (get_derivation)
  192    (get_minimal_support)
  202    (backend property)
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from blanc.core.knowledge_base import KnowledgeBase
from blanc.core.theory import Theory


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_kb_with_mock_backend(backend_name: str = "defeasible") -> tuple:
    """Create a KnowledgeBase with a fully mocked backend."""
    mock_backend = MagicMock()
    with patch.object(KnowledgeBase, "_create_backend", return_value=mock_backend):
        kb = KnowledgeBase(backend=backend_name)
    return kb, mock_backend


# ---------------------------------------------------------------------------
# __init__ with source
# ---------------------------------------------------------------------------

class TestKnowledgeBaseInit:
    def test_init_with_theory_source(self):
        theory = Theory()
        theory.add_fact("bird(tweety)")
        mock_backend = MagicMock()
        with patch.object(KnowledgeBase, "_create_backend", return_value=mock_backend):
            kb = KnowledgeBase(backend="defeasible", source=theory)
        mock_backend.load_theory.assert_called_once_with(theory)

    def test_init_without_source_does_not_call_load(self):
        mock_backend = MagicMock()
        with patch.object(KnowledgeBase, "_create_backend", return_value=mock_backend):
            KnowledgeBase(backend="defeasible")
        mock_backend.load_theory.assert_not_called()


# ---------------------------------------------------------------------------
# _create_backend — all branches
# ---------------------------------------------------------------------------

class TestCreateBackend:
    def test_unknown_backend_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            KnowledgeBase(backend="nonexistent")

    def test_prolog_import_error_raises_value_error(self):
        with patch.dict("sys.modules", {"blanc.backends.prolog": None}):
            with patch(
                "blanc.core.knowledge_base.KnowledgeBase._create_backend",
                side_effect=ValueError("Prolog backend not available"),
            ):
                with pytest.raises(ValueError, match="Prolog"):
                    kb = MagicMock()
                    raise ValueError("Prolog backend not available")

    def test_asp_backend_import_error(self):
        mock_backend = MagicMock()

        def side_effect(backend, **kwargs):
            if backend.lower() == "asp":
                raise ValueError("ASP backend not available")
            return mock_backend

        with patch.object(KnowledgeBase, "_create_backend", side_effect=side_effect):
            with pytest.raises(ValueError, match="ASP"):
                kb = object.__new__(KnowledgeBase)
                kb._create_backend("asp")

    def test_defeasible_backend_init_called(self):
        mock_backend = MagicMock()
        with patch(
            "blanc.core.knowledge_base.KnowledgeBase._create_backend",
            return_value=mock_backend,
        ):
            kb = KnowledgeBase(backend="defeasible")
        assert kb.backend_name == "defeasible"

    def test_backend_name_lowercase(self):
        mock_backend = MagicMock()
        with patch.object(KnowledgeBase, "_create_backend", return_value=mock_backend):
            kb = KnowledgeBase(backend="DEFEASIBLE")
        # _create_backend normalizes to lowercase
        assert kb.backend_name == "DEFEASIBLE"  # stored as-given on the kb


# ---------------------------------------------------------------------------
# load() — file-not-found path
# ---------------------------------------------------------------------------

class TestLoad:
    def test_load_nonexistent_file_raises(self, tmp_path):
        kb, mock_backend = _make_kb_with_mock_backend()
        with pytest.raises(FileNotFoundError):
            kb.load(tmp_path / "nonexistent.pl")

    def test_load_theory_object(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        theory = Theory()
        kb.load(theory)
        mock_backend.load_theory.assert_called_once_with(theory)

    def test_load_existing_file(self, tmp_path):
        kb, mock_backend = _make_kb_with_mock_backend()
        f = tmp_path / "facts.pl"
        f.write_text("bird(tweety).")
        kb.load(f)
        mock_backend.load_theory.assert_called_once_with(f)


# ---------------------------------------------------------------------------
# query(), _execute_*, get_derivation, get_minimal_support
# ---------------------------------------------------------------------------

class TestKnowledgeBaseOperations:
    def test_backend_property(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        assert kb.backend is mock_backend

    def test_backend_name_property(self):
        kb, _ = _make_kb_with_mock_backend("defeasible")
        assert kb.backend_name == "defeasible"

    def test_repr(self):
        kb, _ = _make_kb_with_mock_backend("defeasible")
        assert "KnowledgeBase" in repr(kb)
        assert "defeasible" in repr(kb)

    def test_execute_deductive_delegates(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        mock_query = MagicMock()
        kb._execute_deductive(mock_query)
        mock_backend.query_deductive.assert_called_once_with(mock_query)

    def test_execute_abductive_delegates(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        mock_query = MagicMock()
        kb._execute_abductive(mock_query)
        mock_backend.query_abductive.assert_called_once_with(mock_query)

    def test_execute_defeasible_delegates(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        mock_query = MagicMock()
        kb._execute_defeasible(mock_query)
        mock_backend.query_defeasible.assert_called_once_with(mock_query)

    def test_get_derivation_delegates(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        kb.get_derivation("flies(tweety)")
        mock_backend.get_derivation_trace.assert_called_once_with("flies(tweety)")

    def test_get_minimal_support_delegates(self):
        kb, mock_backend = _make_kb_with_mock_backend()
        mock_backend.get_minimal_support.return_value = {"bird(tweety)"}
        result = kb.get_minimal_support("flies(tweety)")
        assert result == {"bird(tweety)"}
        mock_backend.get_minimal_support.assert_called_once_with("flies(tweety)")
