"""Tests for Prolog (PySwip/SWI-Prolog) backend."""

import pytest

from blanc.backends.prolog import PrologBackend, PYSWIP_AVAILABLE
from blanc.core.theory import Rule, RuleType, Theory


@pytest.mark.skipif(not PYSWIP_AVAILABLE, reason="PySwip/SWI-Prolog not installed")
class TestPrologBackend:
    """Test Prolog backend functionality."""

    def test_backend_initialization(self):
        """Test Prolog backend can be initialized."""
        backend = PrologBackend()
        assert backend is not None
        assert backend._prolog is not None

    def test_load_theory_from_object(self):
        """Test loading Theory object."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_fact("bird(woody)")
        
        backend = PrologBackend()
        backend.load_theory(theory)
        
        assert backend._theory == theory

    def test_load_theory_from_string(self):
        """Test loading Prolog program from string."""
        program = """
        bird(tweety).
        bird(woody).
        flies(X) :- bird(X), \\+ penguin(X).
        """
        
        backend = PrologBackend()
        backend.load_theory(program)
        
        # Verify facts are loaded by querying
        solutions = list(backend._prolog.query("bird(X)"))
        assert len(solutions) >= 2

    def test_simple_deductive_query(self):
        """Test simple deductive query."""
        theory = Theory()
        theory.add_fact("human(socrates)")
        theory.add_rule(
            Rule(head="mortal(X)", body=("human(X)",))
        )
        
        backend = PrologBackend()
        backend.load_theory(theory)
        
        # Query should return socrates
        solutions = list(backend._prolog.query("mortal(X)"))
        assert len(solutions) > 0
        assert any(s.get('X') == 'socrates' for s in solutions)

    def test_backtracking(self):
        """Test Prolog backtracking with multiple solutions."""
        theory = Theory()
        theory.add_fact("parent(tom, bob)")
        theory.add_fact("parent(tom, liz)")
        theory.add_fact("parent(bob, ann)")
        theory.add_fact("parent(bob, pat)")
        theory.add_rule(
            Rule(head="grandparent(X, Z)", body=("parent(X, Y)", "parent(Y, Z)"))
        )
        
        backend = PrologBackend()
        backend.load_theory(theory)
        
        # Tom should be grandparent of ann and pat
        solutions = list(backend._prolog.query("grandparent(tom, X)"))
        assert len(solutions) == 2
        grandchildren = [s['X'] for s in solutions]
        assert 'ann' in grandchildren
        assert 'pat' in grandchildren

    def test_theory_to_prolog_conversion(self):
        """Test converting Theory to Prolog format."""
        theory = Theory()
        theory.add_fact("human(socrates)")
        theory.add_rule(
            Rule(head="mortal(X)", body=("human(X)",))
        )
        
        prolog_code = theory.to_prolog()
        
        assert "human(socrates)." in prolog_code
        assert "mortal(X) :- human(X)." in prolog_code

    def test_defeasible_query_basic(self):
        """Test basic defeasible query."""
        theory = Theory()
        theory.add_fact("human(socrates)")
        theory.add_rule(
            Rule(head="mortal(X)", body=("human(X)",))
        )
        
        backend = PrologBackend()
        backend.load_theory(theory)
        
        # Verify socrates is mortal
        solutions = list(backend._prolog.query("mortal(socrates)"))
        assert len(solutions) > 0

    def test_close_cleanup(self):
        """Test backend cleanup."""
        backend = PrologBackend()
        theory = Theory()
        theory.add_fact("test(value)")
        backend.load_theory(theory)
        
        backend.close()
        # After close, prolog should be None
        assert backend._prolog is None


@pytest.mark.skipif(not PYSWIP_AVAILABLE, reason="PySwip/SWI-Prolog not installed")
class TestPrologBackendIntegration:
    """Integration tests with actual Prolog solving."""

    def test_family_relations(self):
        """Test family relationship inference."""
        program = """
        male(tom).
        male(bob).
        female(liz).
        female(ann).
        
        parent(tom, bob).
        parent(tom, liz).
        parent(bob, ann).
        
        father(X, Y) :- parent(X, Y), male(X).
        mother(X, Y) :- parent(X, Y), female(X).
        """
        
        backend = PrologBackend()
        backend.load_theory(program)
        
        # Test father inference
        fathers = list(backend._prolog.query("father(X, Y)"))
        assert len(fathers) >= 2
        
    def test_list_operations(self):
        """Test Prolog list operations."""
        program = """
        member(X, [X|_]).
        member(X, [_|T]) :- member(X, T).
        
        append([], L, L).
        append([H|T1], L2, [H|T3]) :- append(T1, L2, T3).
        """
        
        backend = PrologBackend()
        backend.load_theory(program)
        
        # Test member predicate
        solutions = list(backend._prolog.query("member(2, [1, 2, 3])"))
        assert len(solutions) > 0

    def test_arithmetic(self):
        """Test arithmetic operations."""
        backend = PrologBackend()
        
        # Basic arithmetic
        solutions = list(backend._prolog.query("X is 2 + 3"))
        assert len(solutions) > 0
        assert solutions[0]['X'] == 5


def test_pyswip_not_available():
    """Test graceful handling when PySwip not available."""
    if PYSWIP_AVAILABLE:
        pytest.skip("PySwip is available, can't test unavailable case")
    
    with pytest.raises(ImportError, match="PySwip not installed"):
        PrologBackend()


def test_installation_instructions():
    """Test that installation instructions are provided."""
    if PYSWIP_AVAILABLE:
        pytest.skip("PySwip is available")
    
    try:
        PrologBackend()
    except ImportError as e:
        error_msg = str(e)
        assert "pip install pyswip" in error_msg
        assert "SWI-Prolog" in error_msg
