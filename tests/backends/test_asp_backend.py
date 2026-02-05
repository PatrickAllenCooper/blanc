"""Tests for ASP (Clingo) backend."""

import pytest

from blanc.backends.asp import ASPBackend, CLINGO_AVAILABLE
from blanc.core.query import Query
from blanc.core.theory import Rule, RuleType, Theory


@pytest.mark.skipif(not CLINGO_AVAILABLE, reason="Clingo not installed")
class TestASPBackend:
    """Test ASP backend functionality."""

    def test_backend_initialization(self):
        """Test ASP backend can be initialized."""
        backend = ASPBackend()
        assert backend is not None

    def test_load_theory_from_object(self):
        """Test loading Theory object."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_fact("bird(woody)")
        
        backend = ASPBackend()
        backend.load_theory(theory)
        
        assert backend._theory == theory

    def test_load_theory_from_string(self):
        """Test loading ASP program from string."""
        program = """
        bird(tweety).
        bird(woody).
        flies(X) :- bird(X), not penguin(X).
        """
        
        backend = ASPBackend()
        backend.load_theory(program)
        
        assert "bird(tweety)" in backend._program_text

    def test_simple_deductive_query(self):
        """Test simple deductive query."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_fact("bird(woody)")
        theory.add_rule(
            Rule(head="flies(X)", body=("bird(X)",))
        )
        
        backend = ASPBackend()
        backend.load_theory(theory)
        
        # Query for flying things
        query = Query(backend).select("flies(X)")
        # Note: Need to implement query execution through backend directly
        # For now, test the theory loading worked
        assert backend._theory is not None

    def test_theory_to_asp_conversion(self):
        """Test converting Theory to ASP format."""
        theory = Theory()
        theory.add_fact("human(socrates)")
        theory.add_rule(
            Rule(head="mortal(X)", body=("human(X)",))
        )
        
        backend = ASPBackend()
        asp_program = backend._theory_to_asp(theory)
        
        assert "human(socrates)." in asp_program
        assert "mortal(X) :- human(X)." in asp_program

    def test_defeasible_rules_encoding(self):
        """Test encoding defeasible rules in ASP."""
        theory = Theory()
        theory.add_fact("bird(tweety)")
        theory.add_rule(
            Rule(
                head="flies(X)",
                body=("bird(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label="r1"
            )
        )
        
        backend = ASPBackend()
        asp_program = backend._theory_to_asp(theory)
        
        # Should include defeasible encoding
        assert "defeated_r1" in asp_program or "applicable_r1" in asp_program

    def test_extract_bindings(self):
        """Test extracting variable bindings from atoms."""
        backend = ASPBackend()
        
        pattern = "parent(X, Y)"
        atoms = ["parent(john, mary)", "parent(john, bob)", "person(alice)"]
        
        bindings = backend._extract_bindings(pattern, atoms)
        
        assert len(bindings) == 2
        assert {"X": "john", "Y": "mary"} in bindings
        assert {"X": "john", "Y": "bob"} in bindings

    def test_extract_bindings_no_variables(self):
        """Test pattern with no variables."""
        backend = ASPBackend()
        
        pattern = "bird(tweety)"
        atoms = ["bird(tweety)", "bird(woody)"]
        
        bindings = backend._extract_bindings(pattern, atoms)
        
        assert len(bindings) == 1
        assert bindings[0] == {}


@pytest.mark.skipif(not CLINGO_AVAILABLE, reason="Clingo not installed")
class TestASPBackendIntegration:
    """Integration tests with actual Clingo solving."""

    def test_basic_facts_query(self):
        """Test querying basic facts."""
        program = """
        person(alice).
        person(bob).
        person(charlie).
        """
        
        backend = ASPBackend()
        backend.load_theory(program)
        
        # The backend is loaded, solve to verify
        with backend._control.solve(yield_=True) as handle:
            models = list(handle)
            assert len(models) > 0

    def test_rule_inference(self):
        """Test inference with rules."""
        program = """
        human(socrates).
        mortal(X) :- human(X).
        """
        
        backend = ASPBackend()
        backend.load_theory(program)
        
        # Verify program loaded and can solve
        with backend._control.solve(yield_=True) as handle:
            for model in handle:
                atoms = [str(atom) for atom in model.symbols(shown=True)]
                # Should derive mortal(socrates)
                assert any("mortal" in atom for atom in atoms)
                break

    def test_tweety_example(self):
        """Test classic Tweety example."""
        program = """
        bird(tweety).
        flies(X) :- bird(X), not penguin(X).
        """
        
        backend = ASPBackend()
        backend.load_theory(program)
        
        with backend._control.solve(yield_=True) as handle:
            for model in handle:
                atoms = [str(atom) for atom in model.symbols(shown=True)]
                # Tweety should fly (not a penguin)
                assert any("flies" in atom for atom in atoms)
                break


def test_clingo_not_available():
    """Test graceful handling when Clingo not available."""
    if CLINGO_AVAILABLE:
        pytest.skip("Clingo is available, can't test unavailable case")
    
    with pytest.raises(ImportError, match="Clingo/Clorm not installed"):
        ASPBackend()
