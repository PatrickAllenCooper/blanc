"""
Pure formal encoder (M4).

Implements M4 encoding modality from paper.tex Appendix B, line 881.

Author: Patrick Cooper
Date: 2026-02-11

CRITICAL COMPONENT: This codec must have perfect round-trip consistency.
Every design decision prioritizes correctness over convenience.
"""

from typing import List, Union
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance


class PureFormalEncoder:
    """
    M4: Pure formal encoder.
    
    Definition 26 (paper.tex line 710-712): Pure formal modality.
    Appendix B (line 881): Raw logical syntax without glosses.
    
    Properties:
    - Faithfulness: Maximum (no information loss)
    - Naturalness: Minimum (raw syntax)
    - Round-trip: Guaranteed with D1 decoder (Proposition, line 903)
    
    For MVP: Uses Prolog-style syntax for universal compatibility.
    """
    
    def __init__(self):
        """Initialize encoder."""
        pass
    
    def encode_fact(self, fact: str) -> str:
        """
        Encode ground fact.
        
        Args:
            fact: Ground atom (e.g., "bird(tweety)")
        
        Returns:
            Encoded fact with period (e.g., "bird(tweety).")
        
        Safety: Validates fact is well-formed before encoding.
        """
        # Validate fact is well-formed
        if not fact or not self._is_well_formed_atom(fact):
            raise ValueError(f"Malformed fact: {fact}")
        
        # Add period if not present
        if not fact.endswith('.'):
            return f"{fact}."
        return fact
    
    def encode_rule(self, rule: Rule) -> str:
        """
        Encode rule to pure formal syntax.
        
        Args:
            rule: Rule object
        
        Returns:
            Encoded rule string
        
        Format:
            - Facts: "p(a)."
            - Strict: "h(X) :- b1(X), b2(X)."
            - Defeasible: "h(X) :- b1(X), b2(X). % defeasible"
            - Defeater: "~h(X) :- b1(X). % defeater"
        
        Safety: Validates rule structure before encoding.
        """
        # Validate rule
        if not rule.head or not self._is_well_formed_atom(rule.head):
            raise ValueError(f"Malformed rule head: {rule.head}")
        
        for body_lit in rule.body:
            if not self._is_well_formed_atom(body_lit):
                raise ValueError(f"Malformed body literal: {body_lit}")
        
        # Encode based on type
        if rule.is_fact:
            return f"{rule.head}."
        
        # Build body string
        body_str = ", ".join(rule.body)
        
        # Build rule with annotation
        if rule.rule_type == RuleType.STRICT:
            return f"{rule.head} :- {body_str}."
        elif rule.rule_type == RuleType.DEFEASIBLE:
            return f"{rule.head} :- {body_str}. % defeasible"
        elif rule.rule_type == RuleType.DEFEATER:
            return f"{rule.head} :- {body_str}. % defeater"
        else:
            raise ValueError(f"Unknown rule type: {rule.rule_type}")
    
    def encode_theory(self, theory: Theory) -> str:
        """
        Encode complete theory.
        
        Args:
            theory: Theory object
        
        Returns:
            Multi-line string with all facts and rules
        
        Format:
            Facts first (sorted), then rules (by type).
            Clear separation for readability.
        """
        lines = []
        
        # Encode facts
        if theory.facts:
            lines.append("% Facts")
            for fact in sorted(theory.facts):
                lines.append(self.encode_fact(fact))
            lines.append("")  # Blank line
        
        # Encode strict rules
        strict_rules = theory.get_rules_by_type(RuleType.STRICT)
        if strict_rules:
            lines.append("% Strict Rules")
            for rule in strict_rules:
                lines.append(self.encode_rule(rule))
            lines.append("")
        
        # Encode defeasible rules
        defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        if defeasible_rules:
            lines.append("% Defeasible Rules")
            for rule in defeasible_rules:
                lines.append(self.encode_rule(rule))
            lines.append("")
        
        # Encode defeaters
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        if defeaters:
            lines.append("% Defeaters")
            for rule in defeaters:
                lines.append(self.encode_rule(rule))
            lines.append("")
        
        # Encode superiority relations
        if theory.superiority:
            lines.append("% Superiority")
            for superior, inferiors in sorted(theory.superiority.items()):
                for inferior in sorted(inferiors):
                    lines.append(f"{superior} > {inferior}.")
        
        return "\n".join(lines)
    
    def encode_instance(self, instance: AbductiveInstance) -> str:
        """
        Encode complete abductive instance as prompt.
        
        Args:
            instance: AbductiveInstance object
        
        Returns:
            Formatted prompt string
        
        Format:
            1. Theory (incomplete)
            2. Target query
            3. Candidate list
            4. Task instruction
        
        Safety: Validates all components before encoding.
        """
        lines = []
        
        # Encode incomplete theory
        lines.append("THEORY:")
        lines.append("-" * 60)
        theory_str = self.encode_theory(instance.D_minus)
        lines.append(theory_str)
        lines.append("-" * 60)
        lines.append("")
        
        # Encode target
        lines.append(f"TARGET: {instance.target}")
        lines.append("")
        
        # Task description based on level
        if instance.level == 1:
            lines.append("TASK: Which fact, when added to the theory, allows deriving the target?")
        elif instance.level == 2:
            lines.append("TASK: Which rule, when added to the theory, allows deriving the target?")
        elif instance.level == 3:
            lines.append("TASK: Which defeater or exception, when added, resolves the anomaly?")
        lines.append("")
        
        # Encode candidates
        lines.append("CANDIDATES:")
        for i, candidate in enumerate(instance.candidates, 1):
            if isinstance(candidate, str):
                lines.append(f"  {i}. {candidate}")
            else:  # Rule
                lines.append(f"  {i}. {self.encode_rule(candidate)}")
        lines.append("")
        
        lines.append("ANSWER (select number or provide element):")
        
        return "\n".join(lines)
    
    def _is_well_formed_atom(self, atom: str) -> bool:
        """
        Check if atom is well-formed.
        
        Well-formed atoms:
        - Start with lowercase or ~
        - Contain only alphanumeric, underscore, parentheses, comma
        - Balanced parentheses
        - No trailing/leading whitespace
        
        Safety: Strict validation prevents malformed output.
        """
        if not atom:
            return False
        
        # Strip whitespace for validation
        atom = atom.strip()
        
        # Handle negation
        if atom.startswith("~"):
            atom = atom[1:]
        
        # Must start with lowercase
        if not atom or not atom[0].islower():
            return False
        
        # Check balanced parentheses
        if atom.count("(") != atom.count(")"):
            return False
        
        # Check allowed characters
        allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_(),~")
        if not all(c.lower() in allowed for c in atom):
            return False
        
        return True


def encode_instance(instance: AbductiveInstance) -> str:
    """
    Convenience function to encode instance.
    
    Args:
        instance: AbductiveInstance to encode
    
    Returns:
        Encoded prompt string
    """
    encoder = PureFormalEncoder()
    return encoder.encode_instance(instance)
