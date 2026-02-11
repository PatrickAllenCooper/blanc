"""
Pure Python defeasible reasoning engine.

Implements Definition 7 (tagged proof procedure) from paper.tex lines 548-564.
Complexity: O(|R| · |F|) per Theorem 11 (line 775).

Author: Patrick Cooper
Date: 2026-02-11
"""

from dataclasses import dataclass
from typing import Set, Dict, List, Optional, Tuple
import re

from blanc.core.theory import Theory, Rule, RuleType


@dataclass
class ProofTag:
    """
    Tagged proof step (+Δ, -Δ, +∂, -∂).
    
    Represents a step in the defeasible proof procedure.
    """
    literal: str
    tag: str  # "definite" or "defeasible"
    polarity: bool  # True for +, False for -
    
    def __repr__(self) -> str:
        sign = "+" if self.polarity else "-"
        symbol = "Δ" if self.tag == "definite" else "∂"
        return f"{sign}{symbol}{self.literal}"


class DefeasibleEngine:
    """
    Defeasible reasoning engine.
    
    Implements tagged proof procedure from Definition 7 (paper.tex line 548).
    
    +∂q holds iff:
    (1) +Δq; OR
    (2) All of:
        (a) -Δ¬q (complement not definitely provable)
        (b) ∃r ∈ Rd: C(r) = q and ∀a ∈ A(r): +∂a (applicable rule exists)
        (c) ∀s ∈ Rd ∪ Rdf: C(s) = ¬q ⟹ (team defeat)
              (i) ∃a ∈ A(s): -∂a OR
              (ii) ∃t ∈ Rd: C(t) = q, ∀a ∈ A(t): +∂a, t ≻ s
    
    Complexity: O(|R| · |F|) per Theorem 11.
    """
    
    def __init__(self, theory: Theory):
        """
        Initialize engine with theory.
        
        Args:
            theory: Defeasible theory to reason over
        """
        self.theory = theory
        self._defeasible_cache: Dict[str, bool] = {}
        self._definite_cache: Dict[str, bool] = {}
        self._call_depth = 0  # Prevent infinite recursion
        self._max_depth = 100
    
    def is_defeasibly_provable(self, literal: str) -> bool:
        """
        Check if literal is defeasibly provable (D ⊢∂ q).
        
        Definition 7, lines 548-561.
        
        Args:
            literal: Literal to check (e.g., "flies(tweety)")
        
        Returns:
            True if defeasibly provable, False otherwise
        
        Complexity: O(|R| · |F|)
        """
        # Check cache
        if literal in self._defeasible_cache:
            return self._defeasible_cache[literal]
        
        # Prevent infinite recursion
        self._call_depth += 1
        if self._call_depth > self._max_depth:
            self._call_depth -= 1
            self._defeasible_cache[literal] = False
            return False
        
        try:
            result = self._compute_defeasible_provability(literal)
            self._defeasible_cache[literal] = result
            return result
        finally:
            self._call_depth -= 1
    
    def _compute_defeasible_provability(self, literal: str) -> bool:
        """
        Compute defeasible provability without caching.
        
        Implements Definition 7 conditions.
        """
        # (1) Check if definitely provable
        if self.is_definitely_provable(literal):
            return True
        
        # (2a) Check complement not definitely provable
        complement = self._complement(literal)
        if self.is_definitely_provable(complement):
            return False
        
        # (2b) Find applicable defeasible rule for literal
        applicable_rules = self._find_applicable_defeasible_rules(literal)
        if not applicable_rules:
            return False
        
        # (2c) Team defeat: check all attacking rules
        attacking_rules = self._find_attacking_rules(literal)
        for attack in attacking_rules:
            if not self._is_attack_neutralized(attack, applicable_rules, literal):
                # Attack not neutralized - literal not defeasibly provable
                return False
        
        # All attacks neutralized - literal is defeasibly provable
        return True
    
    def is_definitely_provable(self, literal: str) -> bool:
        """
        Check if literal is definitely provable (D ⊢Δ q).
        
        Uses only facts F and strict rules Rs.
        Definition 7 condition (1).
        
        Args:
            literal: Literal to check
        
        Returns:
            True if definitely provable via facts + strict rules
        """
        # Check cache
        if literal in self._definite_cache:
            return self._definite_cache[literal]
        
        # Base case: literal is a fact
        if literal in self.theory.facts:
            self._definite_cache[literal] = True
            return True
        
        # Recursive case: find strict rule with this head
        for rule in self.theory.get_rules_by_type(RuleType.STRICT):
            # Try to match rule head with literal
            substitution = self._match(rule.head, literal)
            if substitution is not None:
                # Check if all body literals are definitely provable with substitution
                if all(
                    self.is_definitely_provable(self._substitute(body_lit, substitution))
                    for body_lit in rule.body
                ):
                    self._definite_cache[literal] = True
                    return True
        
        self._definite_cache[literal] = False
        return False
    
    def expectation_set(self) -> Set[str]:
        """
        Compute Exp(D) = {q | D ⊢∂ q}.
        
        Definition 11 (line 630).
        
        Returns:
            Set of all defeasibly derivable ground literals
        
        Note: For MVP, we enumerate known literals from facts and rules.
        Full implementation would compute complete Herbrand base.
        """
        expectations = set()
        
        # Enumerate all ground literals we can derive
        # Start with facts
        for fact in self.theory.facts:
            if self.is_defeasibly_provable(fact):
                expectations.add(fact)
        
        # For each rule, try instantiating with known constants
        constants = self._extract_constants()
        
        for rule in self.theory.rules:
            # Try to instantiate rule with constants
            for instance in self._ground_rule(rule, constants):
                if self.is_defeasibly_provable(instance):
                    expectations.add(instance)
        
        return expectations
    
    def _find_applicable_defeasible_rules(self, literal: str) -> List[Rule]:
        """
        Find defeasible rules whose head unifies with literal and body is provable.
        
        Definition 7 condition (2b).
        """
        applicable = []
        
        for rule in self.theory.get_rules_by_type(RuleType.DEFEASIBLE):
            # Try to match rule head with literal
            substitution = self._match(rule.head, literal)
            if substitution is not None:
                # Check if all body literals are defeasibly provable
                all_provable = True
                for body_lit in rule.body:
                    instantiated = self._substitute(body_lit, substitution)
                    if not self.is_defeasibly_provable(instantiated):
                        all_provable = False
                        break
                
                if all_provable:
                    applicable.append(rule)
        
        return applicable
    
    def _find_attacking_rules(self, literal: str) -> List[Rule]:
        """
        Find rules that attack literal (conclude its complement).
        
        Definition 7 condition (2c).
        """
        complement = self._complement(literal)
        attacking = []
        
        # Check defeasible rules
        for rule in self.theory.get_rules_by_type(RuleType.DEFEASIBLE):
            if self._match(rule.head, complement) is not None:
                attacking.append(rule)
        
        # Check defeaters
        for rule in self.theory.get_rules_by_type(RuleType.DEFEATER):
            if self._match(rule.head, complement) is not None:
                attacking.append(rule)
        
        return attacking
    
    def _is_attack_neutralized(self, attack: Rule, defenders: List[Rule], 
                               target_literal: str) -> bool:
        """
        Check if attacking rule is neutralized for the specific target literal.
        
        An attack is neutralized if:
        (i) It's inapplicable for this specific literal (body not provable), OR
        (ii) It's overridden by superior defending rule for this literal
        
        Definition 7 condition (2c).
        
        Args:
            attack: Attacking rule
            defenders: Defending rules
            target_literal: The specific literal we're checking (e.g., "flies(tweety)")
        
        Returns:
            True if attack is neutralized for this specific literal
        """
        # Get the substitution for this specific literal
        complement = self._complement(target_literal)
        substitution = self._match(attack.head, complement)
        
        if substitution is None:
            # Attack head doesn't match - not applicable
            return True
        
        # (i) Check if attack body is provable with this specific substitution
        for body_lit in attack.body:
            instantiated = self._substitute(body_lit, substitution)
            if not self.is_defeasibly_provable(instantiated):
                # Body not provable - attack is inapplicable
                return True
        
        # Attack is applicable - check if overridden by superior defender
        # (ii) Check if any defender overrides this attack
        for defender in defenders:
            if self._is_superior(defender, attack):
                # Check if defender is also applicable with same substitution
                defender_applicable = all(
                    self.is_defeasibly_provable(self._substitute(b, substitution))
                    for b in defender.body
                )
                if defender_applicable:
                    # Defender overrides attack
                    return True
        
        # Attack is applicable and not overridden
        return False
    
    def _is_superior(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if rule1 > rule2 in superiority relation."""
        if rule1.label and rule2.label:
            superiors = self.theory.superiority.get(rule1.label, set())
            return rule2.label in superiors
        return False
    
    def _complement(self, literal: str) -> str:
        """
        Compute complement: p ↦ ~p, ~p ↦ p.
        
        Examples:
            flies(tweety) ↦ ~flies(tweety)
            ~flies(tweety) ↦ flies(tweety)
        """
        if literal.startswith("~"):
            return literal[1:]
        else:
            return f"~{literal}"
    
    def _match(self, pattern: str, literal: str) -> Optional[Dict[str, str]]:
        """
        Match pattern against literal and return substitution.
        
        For MVP: simple predicate matching with variable extraction.
        Pattern has variables (uppercase), literal is ground.
        
        Args:
            pattern: Pattern with variables (e.g., "flies(X)")
            literal: Ground literal (e.g., "flies(tweety)")
        
        Returns:
            Substitution dict {var: value} or None if no match
        
        Examples:
            _match("flies(X)", "flies(tweety)") → {"X": "tweety"}
            _match("bird(X)", "flies(tweety)") → None
        """
        # Parse pattern and literal
        pattern_pred, pattern_args = self._parse_atom(pattern)
        literal_pred, literal_args = self._parse_atom(literal)
        
        # Predicate must match
        if pattern_pred != literal_pred:
            return None
        
        # Arity must match
        if len(pattern_args) != len(literal_args):
            return None
        
        # Build substitution
        substitution = {}
        for pat_arg, lit_arg in zip(pattern_args, literal_args):
            if self._is_variable(pat_arg):
                # Variable - add to substitution
                if pat_arg in substitution:
                    # Variable already bound - must match
                    if substitution[pat_arg] != lit_arg:
                        return None
                else:
                    substitution[pat_arg] = lit_arg
            else:
                # Constant - must match exactly
                if pat_arg != lit_arg:
                    return None
        
        return substitution
    
    def _substitute(self, pattern: str, substitution: Dict[str, str]) -> str:
        """
        Apply substitution to pattern.
        
        Args:
            pattern: Pattern with variables (e.g., "flies(X)")
            substitution: Variable bindings (e.g., {"X": "tweety"})
        
        Returns:
            Instantiated pattern (e.g., "flies(tweety)")
        """
        result = pattern
        for var, value in substitution.items():
            # Replace variable with value
            # Must match whole word to avoid replacing X in eXample
            result = re.sub(r'\b' + re.escape(var) + r'\b', value, result)
        return result
    
    def _parse_atom(self, atom: str) -> Tuple[str, List[str]]:
        """
        Parse atom into predicate and arguments.
        
        Args:
            atom: Atom string (e.g., "flies(tweety)" or "bird(X)")
        
        Returns:
            (predicate, [args])
        
        Examples:
            "flies(tweety)" → ("flies", ["tweety"])
            "bird(X)" → ("bird", ["X"])
            "p" → ("p", [])
        """
        # Handle negation
        if atom.startswith("~"):
            pred, args = self._parse_atom(atom[1:])
            return f"~{pred}", args
        
        if "(" not in atom:
            return (atom, [])
        
        match = re.match(r'([a-z_~][a-z0-9_]*)\((.*)\)', atom)
        if match:
            predicate = match.group(1)
            args_str = match.group(2)
            args = [arg.strip() for arg in args_str.split(",")] if args_str else []
            return (predicate, args)
        
        return (atom, [])
    
    def _is_variable(self, term: str) -> bool:
        """Check if term is a variable (starts with uppercase)."""
        return term and term[0].isupper()
    
    def _extract_constants(self) -> Set[str]:
        """
        Extract all constants from theory.
        
        For MVP: extract from facts.
        """
        constants = set()
        
        for fact in self.theory.facts:
            _, args = self._parse_atom(fact)
            for arg in args:
                if not self._is_variable(arg):
                    constants.add(arg)
        
        return constants
    
    def _generate_substitutions(
        self, rule: Rule, constants: Set[str]
    ) -> List[Dict[str, str]]:
        """
        Generate all possible substitutions for rule variables.
        
        For MVP: simple enumeration over constants.
        """
        # Extract variables from rule head and body
        variables = set()
        
        for atom in [rule.head] + list(rule.body):
            _, args = self._parse_atom(atom)
            for arg in args:
                if self._is_variable(arg):
                    variables.add(arg)
        
        if not variables:
            return [{}]
        
        # Generate all combinations (cartesian product)
        var_list = list(variables)
        const_list = list(constants)
        
        if not const_list:
            return [{}]
        
        substitutions = []
        
        def generate(idx, current):
            if idx == len(var_list):
                substitutions.append(current.copy())
                return
            
            for const in const_list:
                current[var_list[idx]] = const
                generate(idx + 1, current)
        
        generate(0, {})
        return substitutions
    
    def _ground_rule(self, rule: Rule, constants: Set[str]) -> List[str]:
        """
        Ground rule head with all possible substitutions.
        
        Returns list of ground literals.
        """
        if rule.is_fact:
            return [rule.head]
        
        ground_heads = []
        for substitution in self._generate_substitutions(rule, constants):
            ground_heads.append(self._substitute(rule.head, substitution))
        
        return ground_heads
    
    def clear_cache(self):
        """Clear proof caches (useful for testing)."""
        self._defeasible_cache.clear()
        self._definite_cache.clear()


# Convenience functions

def defeasible_provable(theory: Theory, literal: str) -> bool:
    """
    Check if theory defeasibly proves literal.
    
    Convenience function for one-off queries.
    
    Args:
        theory: Defeasible theory
        literal: Literal to check
    
    Returns:
        True if D ⊢∂ literal
    """
    engine = DefeasibleEngine(theory)
    return engine.is_defeasibly_provable(literal)


def strictly_provable(theory: Theory, literal: str) -> bool:
    """
    Check if theory definitely proves literal.
    
    Convenience function for one-off queries.
    
    Args:
        theory: Defeasible theory
        literal: Literal to check
    
    Returns:
        True if D ⊢Δ literal
    """
    engine = DefeasibleEngine(theory)
    return engine.is_definitely_provable(literal)
