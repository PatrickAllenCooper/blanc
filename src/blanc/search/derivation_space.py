"""
Defeasible derivation space as an MCTS search domain.

Maps the tagged proof procedure (Definition 7) into the SearchSpace
protocol expected by mcts.py.  A *state* is a frozen snapshot of
which conclusions have been derived so far; an *action* is a ground
rule instantiation that extends the derivation.

Author: Patrick Cooper
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from blanc.core.theory import Rule, RuleType, Theory
from blanc.reasoning.defeasible import DefeasibleEngine
from blanc.search.mcts import SearchSpace


@dataclass(frozen=True)
class DerivationAction:
    """A single rule application that extends a derivation."""

    rule: Rule
    substitution: Dict[str, str]
    derived_literal: str

    def __str__(self) -> str:
        label = self.rule.label or self.rule.to_defeasible()
        return f"{label} -> {self.derived_literal}"


@dataclass(frozen=True)
class DerivationState:
    """
    Frozen snapshot of a partial derivation.

    Tracks which conclusions have been established and which rules
    have already been applied, so the search never revisits the
    same derivation step.
    """

    derived: FrozenSet[str]
    applied_rules: FrozenSet[str]  # stringified (rule_label, substitution)
    theory_hash: int = 0

    @staticmethod
    def initial(theory: Theory) -> "DerivationState":
        return DerivationState(
            derived=frozenset(theory.facts),
            applied_rules=frozenset(),
            theory_hash=id(theory),
        )


def _action_key(rule: Rule, sub: Dict[str, str]) -> str:
    label = rule.label or rule.to_defeasible()
    sub_str = ",".join(f"{k}={v}" for k, v in sorted(sub.items()))
    return f"{label}[{sub_str}]"


class DerivationSpace(SearchSpace[DerivationState, DerivationAction]):
    """
    Adapter that presents a defeasible theory as an MCTS search space.

    Nodes   = sets of derived conclusions (DerivationState).
    Actions = ground rule instantiations (DerivationAction).
    Terminal= no new rule fires, or an optional target literal is reached.
    """

    def __init__(
        self,
        theory: Theory,
        target: Optional[str] = None,
        max_depth: int = 50,
    ):
        self.theory = theory
        self.target = target
        self.max_depth = max_depth
        self._engine = DefeasibleEngine(theory)
        self._constants = self._engine._extract_constants()

    def get_legal_actions(
        self, state: DerivationState
    ) -> List[DerivationAction]:
        actions: List[DerivationAction] = []
        rule_types = [RuleType.STRICT, RuleType.DEFEASIBLE]

        for rt in rule_types:
            for rule in self.theory.get_rules_by_type(rt):
                for sub in self._engine._generate_substitutions(
                    rule, self._constants
                ):
                    derived_lit = self._engine._substitute(rule.head, sub)
                    key = _action_key(rule, sub)

                    if key in state.applied_rules:
                        continue
                    if derived_lit in state.derived:
                        continue

                    body_satisfied = all(
                        self._engine._substitute(b, sub) in state.derived
                        for b in rule.body
                    )
                    if not body_satisfied:
                        continue

                    actions.append(
                        DerivationAction(
                            rule=rule,
                            substitution=dict(sub),
                            derived_literal=derived_lit,
                        )
                    )
        return actions

    def apply_action(
        self, state: DerivationState, action: DerivationAction
    ) -> DerivationState:
        key = _action_key(action.rule, action.substitution)
        return DerivationState(
            derived=state.derived | {action.derived_literal},
            applied_rules=state.applied_rules | {key},
            theory_hash=state.theory_hash,
        )

    def is_terminal(self, state: DerivationState) -> bool:
        if self.target and self.target in state.derived:
            return True
        return len(self.get_legal_actions(state)) == 0

    def evaluate(self, state: DerivationState) -> float:
        if self.target:
            return 1.0 if self.target in state.derived else 0.0
        n_facts = len(self.theory.facts)
        n_derived = len(state.derived)
        bonus = max(0, n_derived - n_facts)
        return bonus / max(1, len(self.theory.rules))

    def get_derived_beyond_facts(
        self, state: DerivationState
    ) -> FrozenSet[str]:
        return state.derived - frozenset(self.theory.facts)
