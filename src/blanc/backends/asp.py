"""
Answer Set Programming backend using Clingo.

Adapter for Clingo ASP solver with Clorm ORM.
"""

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Set, Union

try:
    import clingo
    from clorm import FactBase, Predicate, StringField, IntegerField, ConstantField
    CLINGO_AVAILABLE = True
except ImportError:
    CLINGO_AVAILABLE = False

from blanc.backends.base import KnowledgeBaseBackend
from blanc.core.query import Query, QueryType
from blanc.core.result import DerivationTree, Result, ResultSet
from blanc.core.theory import Rule, RuleType, Theory


class ASPBackend(KnowledgeBaseBackend):
    """
    ASP backend using Clingo and Clorm.
    
    Provides Answer Set Programming capabilities for logic-based reasoning.
    Supports deductive queries, abductive hypothesis generation, and
    optimization-based reasoning.
    """

    def __init__(self, arguments: List[str] = None, **kwargs):
        """
        Initialize ASP backend.
        
        Args:
            arguments: Command-line arguments for Clingo
            **kwargs: Additional backend configuration
            
        Raises:
            ImportError: If Clingo/Clorm not installed
        """
        if not CLINGO_AVAILABLE:
            raise ImportError(
                "Clingo/Clorm not installed. Install with: pip install clingo clorm"
            )
        
        self._arguments = arguments or []
        self._control = clingo.Control(self._arguments)
        self._theory: Union[Theory, None] = None
        self._program_text = ""
        
    def load_theory(self, source: Union[str, Path, Theory]) -> None:
        """
        Load knowledge base from source.
        
        Args:
            source: File path, ASP program text, or Theory object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If theory format is invalid
        """
        if isinstance(source, Theory):
            self._theory = source
            self._program_text = self._theory_to_asp(source)
            self._control.add("base", [], self._program_text)
            
        elif isinstance(source, (str, Path)):
            source_path = Path(source)
            if source_path.exists():
                # Load from file
                self._program_text = source_path.read_text()
                self._control.load(str(source_path))
            else:
                # Treat as ASP program text
                self._program_text = str(source)
                self._control.add("base", [], self._program_text)
        else:
            raise ValueError(f"Invalid source type: {type(source)}")
            
        # Ground the program
        self._control.ground([("base", [])])
    
    def _theory_to_asp(self, theory: Theory) -> str:
        """
        Convert Theory object to ASP program.
        
        Args:
            theory: Theory to convert
            
        Returns:
            ASP program as string
        """
        lines = []
        
        # Add facts
        for fact in sorted(theory.facts):
            lines.append(f"{fact}.")
            
        # Add rules
        for rule in theory.rules:
            if rule.is_fact:
                continue  # Already added in facts section
                
            if rule.body:
                body_str = ", ".join(rule.body)
                lines.append(f"{rule.head} :- {body_str}.")
            else:
                lines.append(f"{rule.head}.")
                
        # Handle defeasible rules and superiority (encoding for ASP)
        # For defeasible rules, we use weak constraints or preferences
        defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        if defeasible_rules:
            lines.append("\n% Defeasible rules (encoded with preferences)")
            for rule in defeasible_rules:
                label = rule.label or f"r_{hash(rule) % 10000}"
                if rule.body:
                    body_str = ", ".join(rule.body)
                    # Create defeasible version with label
                    lines.append(f"{rule.head} :- {body_str}, not defeated_{label}.")
                    lines.append(f"applicable_{label} :- {body_str}.")
                    
            # Add superiority relations
            for superior, inferiors in theory.superiority.items():
                for inferior in inferiors:
                    lines.append(f"defeats({superior}, {inferior}).")
                    lines.append(f"defeated_{inferior} :- applicable_{superior}, defeats({superior}, {inferior}).")
        
        return "\n".join(lines)
    
    def query_deductive(self, query: Query) -> ResultSet:
        """
        Execute deductive query.
        
        Args:
            query: Query object
            
        Returns:
            Result set with answer sets
        """
        start_time = time.time()
        
        # Parse query goal to extract predicate and variables
        goal = query.goal or ""
        results = []
        
        # Add query goal as a constraint to find models where it holds
        query_program = self._program_text
        if query.conditions:
            for cond in query.conditions:
                query_program += f"\n:- not {cond}."
                
        # Create temporary control for query
        control = clingo.Control(self._arguments)
        control.add("base", [], query_program)
        control.ground([("base", [])])
        
        # Solve and collect answer sets
        with control.solve(yield_=True) as handle:
            for model in handle:
                # Extract atoms from model
                atoms = [str(atom) for atom in model.symbols(shown=True)]
                
                # Try to match query goal pattern
                bindings = self._extract_bindings(goal, atoms)
                if bindings:
                    for binding in bindings:
                        results.append(Result(bindings=binding))
                        
                # Limit results if specified
                if query.result_limit and len(results) >= query.result_limit:
                    break
                    
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=str(query),
            backend="asp",
            execution_time_ms=elapsed,
        )
    
    def _extract_bindings(self, pattern: str, atoms: List[str]) -> List[Dict[str, str]]:
        """
        Extract variable bindings from atoms matching pattern.
        
        Args:
            pattern: Query pattern (e.g., "p(X, Y)")
            atoms: List of ground atoms from answer set
            
        Returns:
            List of variable binding dictionaries
        """
        # Simple pattern matching for common cases
        # Extract predicate name and variables
        match = re.match(r'(\w+)\((.*?)\)', pattern)
        if not match:
            return []
            
        pred_name = match.group(1)
        params = [p.strip() for p in match.group(2).split(',')]
        
        # Find which parameters are variables (uppercase)
        var_positions = []
        var_names = []
        for i, param in enumerate(params):
            if param and param[0].isupper():
                var_positions.append(i)
                var_names.append(param)
                
        if not var_positions:
            # No variables, just check if pattern exists
            return [{}] if pattern in atoms else []
            
        # Extract bindings from matching atoms
        bindings = []
        for atom in atoms:
            if atom.startswith(pred_name + "("):
                # Extract arguments
                atom_match = re.match(r'\w+\((.*?)\)', atom)
                if atom_match:
                    args = [a.strip() for a in atom_match.group(1).split(',')]
                    if len(args) == len(params):
                        # Extract variable values
                        binding = {}
                        for i, var_name in zip(var_positions, var_names):
                            if i < len(args):
                                binding[var_name] = args[i]
                        bindings.append(binding)
                        
        return bindings
    
    def query_abductive(self, query: Query) -> ResultSet:
        """
        Execute abductive query using choice rules.
        
        Args:
            query: Query with observation and evidence
            
        Returns:
            Result set with hypotheses
        """
        start_time = time.time()
        
        # Create abductive program
        observation = query.goal or ""
        evidence = query.conditions
        hypotheses = query.hypotheses
        
        # Build program with choice rules for hypotheses
        abd_program = self._program_text + "\n\n% Abductive reasoning\n"
        
        # Add choice rules for candidate hypotheses
        if hypotheses:
            for hyp in hypotheses:
                # Choice rule: hypothesis may or may not hold
                abd_program += f"{{ {hyp} }}.\n"
        
        # Add evidence as constraints
        for ev in evidence:
            abd_program += f":- not {ev}.\n"
            
        # Observation must hold
        abd_program += f":- not {observation}.\n"
        
        # Minimize number of hypotheses (preference for smaller explanations)
        if query.minimize_criterion == "hypothesis_count" and hypotheses:
            for hyp in hypotheses:
                abd_program += f"#minimize {{ 1 : {hyp} }}.\n"
        
        # Solve
        control = clingo.Control(self._arguments + ["--opt-mode=optN"])
        control.add("base", [], abd_program)
        control.ground([("base", [])])
        
        results = []
        with control.solve(yield_=True) as handle:
            for model in handle:
                atoms = [str(atom) for atom in model.symbols(shown=True)]
                
                # Extract which hypotheses are in this model
                active_hypotheses = {}
                for hyp in hypotheses:
                    if hyp in atoms:
                        active_hypotheses[hyp] = "true"
                        
                if active_hypotheses:
                    results.append(Result(
                        bindings=active_hypotheses,
                        metadata={"observation": observation, "evidence": evidence}
                    ))
                    
                if query.result_limit and len(results) >= query.result_limit:
                    break
                    
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=str(query),
            backend="asp",
            execution_time_ms=elapsed,
            metadata={"type": "abductive"}
        )
    
    def query_defeasible(self, query: Query) -> ResultSet:
        """
        Execute defeasible query using weak constraints.
        
        Args:
            query: Query with goal and defeasible context
            
        Returns:
            Result set indicating what is defeasibly derivable
        """
        start_time = time.time()
        
        goal = query.goal or ""
        context = query.defeasible_context
        
        # Add defeaters to program
        def_program = self._program_text + "\n\n% Defeasible query\n"
        
        for defeater in context.defeaters:
            def_program += f"{defeater}.\n"
            
        for assumption in context.assumptions:
            def_program += f"{assumption}.\n"
            
        # Check if goal is derivable
        def_program += f"goal_holds :- {goal}.\n"
        def_program += f":- not goal_holds.\n"
        
        # Solve
        control = clingo.Control(self._arguments)
        control.add("base", [], def_program)
        control.ground([("base", [])])
        
        results = []
        with control.solve(yield_=True) as handle:
            for model in handle:
                # If we get a model, goal is defeasibly derivable
                results.append(Result(
                    bindings={"goal": goal, "derivable": "yes"},
                    metadata={"defeaters": list(context.defeaters)}
                ))
                break
        
        if not results:
            # No model found, goal is not derivable
            results.append(Result(
                bindings={"goal": goal, "derivable": "no"},
                metadata={"defeaters": list(context.defeaters)}
            ))
            
        elapsed = (time.time() - start_time) * 1000
        
        return ResultSet(
            results=results,
            query=str(query),
            backend="asp",
            execution_time_ms=elapsed,
        )
    
    def get_derivation_trace(self, fact: str) -> DerivationTree:
        """
        Extract derivation tree (basic implementation).
        
        Note: ASP doesn't provide direct proof trees like Prolog.
        This is a simplified version.
        
        Args:
            fact: Fact to trace
            
        Returns:
            Derivation tree
        """
        # Basic implementation: create simple tree
        return DerivationTree(
            conclusion=fact,
            metadata={"backend": "asp", "note": "ASP derivation traces are limited"}
        )
    
    def get_minimal_support(self, conclusion: str) -> Set[str]:
        """
        Compute minimal support set.
        
        Args:
            conclusion: Conclusion to find support for
            
        Returns:
            Set of minimal supporting facts
        """
        # This requires analyzing the program structure
        # For now, return empty set with note
        # TODO: Implement by analyzing grounding and rules used
        return set()
    
    def close(self) -> None:
        """Clean up Clingo control."""
        self._control = None
