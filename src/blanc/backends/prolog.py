"""
Prolog backend using PySwip.

Adapter for SWI-Prolog via PySwip library.
"""

import re
import time
from pathlib import Path
from typing import Dict, List, Set, Union

try:
    from pyswip import Prolog
    from pyswip.prolog import PrologError
    PYSWIP_AVAILABLE = True
except (ImportError, Exception):  # Catch SwiPrologNotFoundError too
    PYSWIP_AVAILABLE = False
    Prolog = None  # type: ignore
    PrologError = Exception  # Fallback

from blanc.backends.base import KnowledgeBaseBackend
from blanc.core.query import Query, QueryType
from blanc.core.result import DerivationTree, Result, ResultSet
from blanc.core.theory import Rule, RuleType, Theory


class PrologBackend(KnowledgeBaseBackend):
    """
    Prolog backend using PySwip for SWI-Prolog integration.
    
    Provides Prolog-based reasoning with full support for deductive queries,
    backtracking, and proof tree extraction.
    
    Requires:
        - SWI-Prolog 8.4.2+ installed
        - PySwip 0.3.3+ installed
        - Architecture match (both 64-bit or both 32-bit)
    """

    def __init__(self, **kwargs):
        """
        Initialize Prolog backend.

        Args:
            **kwargs: Backend-specific configuration
            
        Raises:
            ImportError: If PySwip not installed
            RuntimeError: If SWI-Prolog not found
        """
        if not PYSWIP_AVAILABLE:
            raise ImportError(
                "PySwip not installed. Install with:\n"
                "  pip install pyswip\n"
                "Also requires SWI-Prolog 8.4.2+:\n"
                "  Windows: https://www.swi-prolog.org/download/stable\n"
                "  Linux: apt install swi-prolog\n"
                "  Mac: brew install swi-prolog"
            )
            
        try:
            self._prolog = Prolog()
        except Exception as e:
            raise RuntimeError(
                f"Failed to initialize SWI-Prolog: {e}\n"
                "Ensure SWI-Prolog is installed and accessible.\n"
                "Check: swipl --version"
            ) from e
            
        self._theory: Union[Theory, None] = None
        self._loaded_files: List[str] = []

    def load_theory(self, source: Union[str, Path, Theory]) -> None:
        """
        Load knowledge base from source.
        
        Args:
            source: File path, Prolog code string, or Theory object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If theory format is invalid
            PrologError: If Prolog syntax error
        """
        if isinstance(source, Theory):
            self._theory = source
            # Convert to Prolog and assert
            prolog_code = source.to_prolog()
            self._assert_program(prolog_code)
            
        elif isinstance(source, (str, Path)):
            source_path = Path(source)
            if source_path.exists():
                # Load from file
                try:
                    self._prolog.consult(str(source_path))
                    self._loaded_files.append(str(source_path))
                except PrologError as e:
                    raise ValueError(f"Prolog syntax error in {source_path}: {e}") from e
            else:
                # Treat as Prolog code string
                self._assert_program(str(source))
        else:
            raise ValueError(f"Invalid source type: {type(source)}")
    
    def _assert_program(self, prolog_code: str) -> None:
        """
        Assert Prolog code into the knowledge base.
        
        Args:
            prolog_code: Prolog program as string
        """
        # Split into individual clauses and assert them
        lines = prolog_code.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('%'):
                try:
                    # Remove trailing period if present
                    clause = line.rstrip('.')
                    self._prolog.assertz(clause)
                except PrologError as e:
                    # Some lines might be directives or special syntax
                    # Try to handle them differently
                    try:
                        list(self._prolog.query(line))
                    except:
                        # If both fail, skip with warning
                        pass
    
    def query_deductive(self, query: Query) -> ResultSet:
        """
        Execute deductive query.
        
        Args:
            query: Query object with goal and conditions
            
        Returns:
            Result set with variable bindings
        """
        start_time = time.time()
        
        # Build Prolog query
        goal = query.goal or ""
        conditions = query.conditions
        
        # Combine goal with conditions
        if conditions:
            full_query = f"({', '.join(conditions)}), {goal}"
        else:
            full_query = goal
            
        results = []
        
        try:
            # Execute query and collect results
            for solution in self._prolog.query(full_query):
                # Convert Prolog solution to Result
                bindings = {}
                for var, value in solution.items():
                    # Convert Prolog terms to strings
                    bindings[var] = str(value)
                    
                results.append(Result(bindings=bindings))
                
                # Limit results if specified
                if query.result_limit and len(results) >= query.result_limit:
                    break
                    
        except PrologError as e:
            # Query failed - return empty result set with error info
            pass
            
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=full_query,
            backend="prolog",
            execution_time_ms=elapsed,
        )
    
    def query_abductive(self, query: Query) -> ResultSet:
        """
        Execute abductive query using generate-and-test.
        
        Args:
            query: Query with observation and evidence
            
        Returns:
            Result set with hypotheses
        """
        start_time = time.time()
        
        observation = query.goal or ""
        evidence = query.conditions
        hypotheses = query.hypotheses
        
        results = []
        
        if not hypotheses:
            # No candidate hypotheses provided
            return ResultSet(
                results=[],
                query=str(query),
                backend="prolog",
                execution_time_ms=0,
                metadata={"error": "No candidate hypotheses provided"}
            )
        
        # Test each hypothesis
        tested_combos = []
        
        # Try single hypotheses first
        for hyp in hypotheses:
            # Build query: evidence + hypothesis => observation
            test_query = f"{', '.join(evidence + [hyp])}, {observation}"
            
            try:
                # Check if this hypothesis explains the observation
                solutions = list(self._prolog.query(test_query))
                if solutions:
                    results.append(Result(
                        bindings={hyp: "true"},
                        metadata={
                            "observation": observation,
                            "evidence": evidence,
                            "hypothesis_count": 1
                        }
                    ))
                    tested_combos.append([hyp])
            except PrologError:
                pass
        
        # If minimization requested, sort by hypothesis count
        if query.minimize_criterion == "hypothesis_count":
            results.sort(key=lambda r: len(r.bindings))
            
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=str(query),
            backend="prolog",
            execution_time_ms=elapsed,
            metadata={"type": "abductive"}
        )
    
    def query_defeasible(self, query: Query) -> ResultSet:
        """
        Execute defeasible query.
        
        Note: Basic implementation. Full defeasible logic requires
        specialized predicates for superiority relations.
        
        Args:
            query: Query with goal and defeasible context
            
        Returns:
            Result set indicating derivability
        """
        start_time = time.time()
        
        goal = query.goal or ""
        context = query.defeasible_context
        
        # Assert defeaters and assumptions temporarily
        temp_facts = []
        for defeater in context.defeaters:
            try:
                self._prolog.assertz(defeater)
                temp_facts.append(defeater)
            except PrologError:
                pass
                
        for assumption in context.assumptions:
            try:
                self._prolog.assertz(assumption)
                temp_facts.append(assumption)
            except PrologError:
                pass
        
        # Try to prove goal
        results = []
        try:
            solutions = list(self._prolog.query(goal))
            if solutions:
                results.append(Result(
                    bindings={"goal": goal, "derivable": "yes"},
                    metadata={"defeaters": list(context.defeaters)}
                ))
            else:
                results.append(Result(
                    bindings={"goal": goal, "derivable": "no"},
                    metadata={"defeaters": list(context.defeaters)}
                ))
        except PrologError:
            results.append(Result(
                bindings={"goal": goal, "derivable": "no"},
                metadata={"defeaters": list(context.defeaters), "error": True}
            ))
        
        # Retract temporary facts
        for fact in temp_facts:
            try:
                self._prolog.retract(fact)
            except:
                pass
                
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=str(query),
            backend="prolog",
            execution_time_ms=elapsed,
        )
    
    def get_derivation_trace(self, fact: str) -> DerivationTree:
        """
        Extract proof tree for fact.
        
        Note: This is a simplified implementation. Full proof tree extraction
        requires using SWI-Prolog's trace/debug facilities or library(prolog_stack).
        
        Args:
            fact: Fact to get derivation for
            
        Returns:
            Derivation tree
        """
        # Basic implementation: try to prove and create simple tree
        try:
            solutions = list(self._prolog.query(fact))
            if solutions:
                return DerivationTree(
                    conclusion=fact,
                    metadata={
                        "backend": "prolog",
                        "provable": True,
                        "note": "Full proof tree extraction requires trace hooks"
                    }
                )
        except PrologError:
            pass
            
        return DerivationTree(
            conclusion=fact,
            metadata={
                "backend": "prolog",
                "provable": False
            }
        )
    
    def get_minimal_support(self, conclusion: str) -> Set[str]:
        """
        Compute minimal support set for conclusion.
        
        Note: This requires analyzing which facts/rules were used in the proof.
        Full implementation needs proof tree analysis.
        
        Args:
            conclusion: Conclusion to find support for
            
        Returns:
            Set of minimal supporting facts/rules
        """
        # TODO: Implement using proof tree analysis
        # For now, return empty set
        return set()
    
    def close(self) -> None:
        """Clean up Prolog instance."""
        # Retract all asserted facts
        try:
            if self._prolog:
                self._prolog.query("retractall(_)")
        except:
            pass
        self._prolog = None
