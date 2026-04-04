"""
Theory representation and manipulation.

Provides a unified internal representation for knowledge bases that can be
converted to/from different backend-specific formats (Prolog, ASP, etc.).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class RuleType(Enum):
    """Type of logical rule in defeasible logic."""

    STRICT = "strict"  # Classical deductive rule (->)
    DEFEASIBLE = "defeasible"  # Defeasible rule (=>)
    DEFEATER = "defeater"  # Defeater rule (~>)
    FACT = "fact"  # Ground fact


@dataclass(frozen=True)
class Rule:
    """
    A logical rule in the knowledge base.

    Attributes:
        head: Consequent of the rule
        body: List of antecedents (empty for facts)
        rule_type: Type of rule (strict, defeasible, defeater, fact)
        priority: Optional priority for conflict resolution
        label: Optional label/identifier for the rule
        metadata: Additional metadata for provenance tracking
    """

    head: str
    body: tuple[str, ...] = field(default_factory=tuple)
    rule_type: RuleType = RuleType.STRICT
    priority: Optional[int] = None
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate rule construction."""
        if self.rule_type == RuleType.FACT and self.body:
            raise ValueError("Facts cannot have a body")
        if not self.head:
            raise ValueError("Rule must have a head")

    @property
    def is_fact(self) -> bool:
        """Check if this rule is a ground fact."""
        return self.rule_type == RuleType.FACT and not self.body

    @property
    def is_strict(self) -> bool:
        """Check if this is a strict (classical) rule."""
        return self.rule_type == RuleType.STRICT

    @property
    def is_defeasible(self) -> bool:
        """Check if this is a defeasible rule."""
        return self.rule_type == RuleType.DEFEASIBLE

    @property
    def is_defeater(self) -> bool:
        """Check if this is a defeater rule."""
        return self.rule_type == RuleType.DEFEATER

    def to_prolog(self) -> str:
        """Convert rule to Prolog syntax."""
        if self.is_fact:
            return f"{self.head}."

        body_str = ", ".join(self.body)
        return f"{self.head} :- {body_str}."

    def to_asp(self) -> str:
        """Convert rule to Answer Set Programming syntax."""
        if self.is_fact:
            return f"{self.head}."

        body_str = ", ".join(self.body)
        return f"{self.head} :- {body_str}."

    def to_defeasible(self) -> str:
        """Convert rule to defeasible logic syntax."""
        if self.is_fact:
            return self.head

        body_str = ", ".join(self.body)
        operator = {
            RuleType.STRICT: "->",
            RuleType.DEFEASIBLE: "=>",
            RuleType.DEFEATER: "~>",
        }.get(self.rule_type, "->")

        label_prefix = f"{self.label}: " if self.label else ""
        return f"{label_prefix}{body_str} {operator} {self.head}"

    def __str__(self) -> str:
        """String representation using defeasible logic syntax."""
        return self.to_defeasible()


@dataclass
class Theory:
    """
    A knowledge base theory consisting of rules, facts, and superiority relations.

    Attributes:
        rules: List of rules in the theory
        facts: Set of ground facts
        superiority: Rule superiority relations (label -> set of inferior labels)
        metadata: Additional metadata about the theory
    """

    rules: List[Rule] = field(default_factory=list)
    facts: Set[str] = field(default_factory=set)
    superiority: Dict[str, Set[str]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Coerce types that callers sometimes pass incorrectly."""
        if isinstance(self.facts, list):
            object.__setattr__(self, "facts", set(self.facts))
        if isinstance(self.superiority, (list, tuple)):
            coerced: Dict[str, Set[str]] = {}
            for pair in self.superiority:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    sup, inf = pair
                    coerced.setdefault(sup, set()).add(inf)
            object.__setattr__(self, "superiority", coerced)

    def add_rule(self, rule: Rule) -> None:
        """Add a rule to the theory."""
        if rule.is_fact:
            self.facts.add(rule.head)
        self.rules.append(rule)

    def add_fact(self, fact: str) -> None:
        """Add a ground fact to the theory."""
        self.facts.add(fact)

    def add_superiority(self, superior: str, inferior: str) -> None:
        """Add a superiority relation between rules."""
        if superior not in self.superiority:
            self.superiority[superior] = set()
        self.superiority[superior].add(inferior)

    def copy(self) -> "Theory":
        """
        Return a deep copy of this Theory.

        Handles the case where ``superiority`` has been (incorrectly) stored as
        a list of pairs instead of a dict, normalising the copy to dict form.
        This is the single canonical place for Theory duplication; callers
        should use this instead of rolling their own copy logic.
        """
        dup = Theory()
        for fact in self.facts:
            dup.add_fact(fact)
        for rule in self.rules:
            dup.add_rule(Rule(
                head=rule.head,
                body=tuple(rule.body),
                rule_type=rule.rule_type,
                label=rule.label,
                priority=rule.priority,
                metadata=dict(rule.metadata) if rule.metadata else {},
            ))
        if isinstance(self.superiority, dict):
            for sup, infs in self.superiority.items():
                for inf in infs:
                    dup.add_superiority(sup, inf)
        elif isinstance(self.superiority, (list, tuple)):
            for pair in self.superiority:
                if isinstance(pair, (list, tuple)) and len(pair) == 2:
                    dup.add_superiority(pair[0], pair[1])
        if self.metadata:
            dup.metadata = dict(self.metadata)
        return dup

    def get_rules_by_type(self, rule_type: RuleType) -> List[Rule]:
        """Get all rules of a specific type."""
        return [r for r in self.rules if r.rule_type == rule_type]

    def get_rule_by_label(self, label: str) -> Optional[Rule]:
        """Get a rule by its label."""
        for rule in self.rules:
            if rule.label == label:
                return rule
        return None

    def to_prolog(self) -> str:
        """Convert theory to Prolog syntax."""
        lines = []

        # Facts
        for fact in sorted(self.facts):
            lines.append(f"{fact}.")

        # Rules
        for rule in self.rules:
            if not rule.is_fact:
                lines.append(rule.to_prolog())

        return "\n".join(lines)

    def to_asp(self) -> str:
        """Convert theory to ASP syntax."""
        lines = []

        # Facts
        for fact in sorted(self.facts):
            lines.append(f"{fact}.")

        # Rules
        for rule in self.rules:
            if not rule.is_fact:
                lines.append(rule.to_asp())

        return "\n".join(lines)

    def to_defeasible(self) -> str:
        """Convert theory to defeasible logic syntax."""
        lines = []

        # Facts (no special syntax needed in defeasible logic)
        for fact in sorted(self.facts):
            lines.append(fact)

        # Rules
        for rule in self.rules:
            if not rule.is_fact:
                lines.append(rule.to_defeasible())

        # Superiority relations
        for superior, inferiors in self.superiority.items():
            for inferior in inferiors:
                lines.append(f"{superior} > {inferior}")

        return "\n".join(lines)

    @classmethod
    def from_prolog(cls, source: str) -> "Theory":
        """
        Parse theory from Prolog source.

        Note: This is a placeholder for future implementation.
        Full Prolog parsing requires a proper parser.
        """
        raise NotImplementedError("Prolog parsing not yet implemented")

    @classmethod
    def from_asp(cls, source: str) -> "Theory":
        """
        Parse theory from ASP source.

        Note: This is a placeholder for future implementation.
        """
        raise NotImplementedError("ASP parsing not yet implemented")

    @classmethod
    def from_defeasible(cls, source: str) -> "Theory":
        """
        Parse theory from defeasible logic source.

        Note: This is a placeholder for future implementation.
        """
        raise NotImplementedError("Defeasible logic parsing not yet implemented")

    def __len__(self) -> int:
        """Return total number of rules and facts."""
        return len(self.rules) + len(self.facts)

    def __str__(self) -> str:
        """String representation using defeasible logic syntax."""
        return self.to_defeasible()
