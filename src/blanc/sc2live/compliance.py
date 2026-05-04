"""
ROE compliance checker for LLM-issued commander orders.

Maps each Order to a defeasible-provability query against the active Theory
and returns a ComplianceVerdict.  This is the runtime guardrail used by
CommanderPolicy enforcement modes B1 (audit) and B2 (gated).

Compliance semantics:
    attack(unit, target)
        COMPLIANT   iff  +∂ authorized_to_engage(unit, target)
                    AND  NOT +∂ ~authorized_to_engage(unit, target)
        The second conjunct is the defeat check: if a defeater is actively
        blocking engagement (self-defense override does NOT fire yet) the
        order is non-compliant.

    retreat(unit)
        COMPLIANT   iff  +∂ ordered_to_retreat(unit)
                    OR   NOT +∂ authorized_to_engage(unit, _any_target)
        Retreating when ordered to retreat is always compliant.
        Retreating when not authorized to engage is also compliant (the unit
        is doing the right thing by standing down).

    hold(unit)
        Always COMPLIANT.  Holding position never violates ROE.

The verdict carries:
    compliant        bool
    violated_rule    Rule | None   -- the specific defeater that blocked the order
    reason           str           -- human-readable for re-prompt injection

Author: Anonymous Authors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable
from blanc.sc2live.orders_schema import Order


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class ComplianceVerdict:
    """
    Result of checking one Order against the active ROE Theory.

    Attributes
    ----------
    order : Order
        The order that was checked.
    compliant : bool
        Whether the order is permitted under the active ROE.
    violated_rule : Rule | None
        The specific defeater (if any) whose firing makes this non-compliant.
        None if compliant or if the violation is a positive-rule absence.
    reason : str
        Human-readable explanation for re-prompt construction.
    check_literal : str
        The defeasible literal that was queried (useful for logging).
    """
    order: Order
    compliant: bool
    violated_rule: Optional[Rule]
    reason: str
    check_literal: str = field(default="")

    def to_dict(self) -> dict:
        return {
            "action": self.order.action,
            "unit": self.order.unit,
            "target": self.order.target,
            "compliant": self.compliant,
            "violated_defeater": self.violated_rule.label if self.violated_rule else None,
            "reason": self.reason,
            "check_literal": self.check_literal,
        }


# ---------------------------------------------------------------------------
# Helpers for pattern-matching ground facts
# ---------------------------------------------------------------------------

def _unit_in_theory(unit: str, theory: Theory) -> bool:
    """Return True if the unit atom appears as a subject in any ground fact."""
    return any(f"({unit}" in fact or f"({unit}," in fact
               for fact in theory.facts)


def _find_blocking_defeater(target_literal: str, theory: Theory) -> Rule | None:
    """
    Return the defeater rule (if any) whose head is ~<target_literal_pred>(...)
    and whose body is satisfied in the current theory.

    We look for defeaters whose head predicate matches the complement of
    target_literal's predicate.  When the theory resolves the conflict via
    superiority, the defeater that *would* block the order in the absence of
    an override is the most informative one to return.
    """
    target_pred = target_literal.split("(")[0]
    neg_pred = f"~{target_pred}"

    for rule in theory.rules:
        if rule.rule_type != RuleType.DEFEATER:
            continue
        rule_head_pred = rule.head.split("(")[0]
        if rule_head_pred != neg_pred:
            continue
        # Check whether the defeater's body is satisfied in the current theory
        body_satisfied = all(
            defeasible_provable(theory, b) or b in theory.facts
            for b in rule.body
        )
        if body_satisfied:
            return rule

    return None


def _find_any_engage_target(unit: str, theory: Theory) -> str | None:
    """
    Return a target atom that ``unit`` is currently authorized to engage,
    or None if the unit has no valid engagement targets.
    """
    for fact in theory.facts:
        if "military_target(" in fact or "worker_target(" in fact:
            m = re.match(r"\w+\((\w+)\)", fact)
            if m:
                target = m.group(1)
                literal = f"authorized_to_engage({unit}, {target})"
                if defeasible_provable(theory, literal):
                    return target
    return None


# ---------------------------------------------------------------------------
# Core checker
# ---------------------------------------------------------------------------

def check_order(order: Order, theory: Theory) -> ComplianceVerdict:
    """
    Check whether ``order`` is compliant with the active ROE in ``theory``.

    Parameters
    ----------
    order : Order
        The order to check.
    theory : Theory
        The current defeasible theory (KB rules + lifted ground facts).

    Returns
    -------
    ComplianceVerdict
    """
    if order.action == "hold":
        return ComplianceVerdict(
            order=order,
            compliant=True,
            violated_rule=None,
            reason="Holding position is always ROE-compliant.",
            check_literal="(none -- hold always compliant)",
        )

    if order.action == "retreat":
        return _check_retreat(order, theory)

    if order.action == "attack":
        return _check_attack(order, theory)

    # Fallback: unknown actions are treated as non-compliant
    return ComplianceVerdict(
        order=order,
        compliant=False,
        violated_rule=None,
        reason=f"Unknown action {order.action!r}.",
        check_literal="",
    )


def _check_attack(order: Order, theory: Theory) -> ComplianceVerdict:
    """Check an attack order."""
    unit   = order.unit
    target = order.target or ""
    pos_literal = f"authorized_to_engage({unit}, {target})"
    neg_literal = f"~authorized_to_engage({unit}, {target})"

    positive_holds = defeasible_provable(theory, pos_literal)
    negative_holds = defeasible_provable(theory, neg_literal)

    if positive_holds and not negative_holds:
        return ComplianceVerdict(
            order=order,
            compliant=True,
            violated_rule=None,
            reason=f"Engagement of {target} by {unit} is authorized (+∂ {pos_literal}).",
            check_literal=pos_literal,
        )

    # Non-compliant: build a helpful reason
    if negative_holds:
        blocking = _find_blocking_defeater(f"authorized_to_engage({unit}, {target})", theory)
        if blocking:
            rule_desc = blocking.label or blocking.head
            reason = (
                f"ROE prohibits engagement of {target} by {unit}: "
                f"defeater '{rule_desc}' is active "
                f"(rule body: {', '.join(blocking.body)})."
            )
        else:
            reason = (
                f"ROE prohibits engagement of {target} by {unit}: "
                f"+∂ {neg_literal} holds but no specific defeater identified."
            )
        return ComplianceVerdict(
            order=order,
            compliant=False,
            violated_rule=blocking,
            reason=reason,
            check_literal=neg_literal,
        )

    # Neither positive nor negative holds: engagement not authorized by any rule
    reason = (
        f"Engagement of {target} by {unit} is not authorized: "
        f"neither +∂ {pos_literal} nor +∂ {neg_literal} holds.  "
        f"No applicable authorization rule found."
    )
    return ComplianceVerdict(
        order=order,
        compliant=False,
        violated_rule=None,
        reason=reason,
        check_literal=pos_literal,
    )


def _check_retreat(order: Order, theory: Theory) -> ComplianceVerdict:
    """Check a retreat order."""
    unit = order.unit
    retreat_literal = f"ordered_to_retreat({unit})"

    if defeasible_provable(theory, retreat_literal):
        return ComplianceVerdict(
            order=order,
            compliant=True,
            violated_rule=None,
            reason=f"Retreat of {unit} is ROE-mandated (+∂ {retreat_literal}).",
            check_literal=retreat_literal,
        )

    # Retreating when not authorized to engage is also fine
    any_target = _find_any_engage_target(unit, theory)
    if any_target is None:
        return ComplianceVerdict(
            order=order,
            compliant=True,
            violated_rule=None,
            reason=(
                f"Retreat of {unit} is compliant: unit has no authorized "
                f"engagement targets (standing down is correct)."
            ),
            check_literal=retreat_literal,
        )

    # Retreating when ordered to hold/engage -- potentially non-compliant if
    # the unit has a mission objective requiring engagement
    mission_literal = f"assigned_to_mission({unit}, op_thunderbolt)"
    mission_active = (mission_literal in theory.facts
                      or defeasible_provable(theory, mission_literal))
    if mission_active and any_target:
        return ComplianceVerdict(
            order=order,
            compliant=False,
            violated_rule=None,
            reason=(
                f"Retreat of {unit} may violate mission objectives: "
                f"unit is assigned to an offensive operation and has "
                f"authorized engagement targets (e.g. {any_target})."
            ),
            check_literal=retreat_literal,
        )

    # Otherwise a precautionary retreat is treated as compliant
    return ComplianceVerdict(
        order=order,
        compliant=True,
        violated_rule=None,
        reason=f"Precautionary retreat of {unit} is ROE-compliant.",
        check_literal=retreat_literal,
    )


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def check_orders(orders: list[Order], theory: Theory) -> list[ComplianceVerdict]:
    """Check a list of orders and return a verdict for each."""
    return [check_order(order, theory) for order in orders]
