"""
Situation report builder: Theory -> LLM commander brief.

Renders the ground facts of the current Theory into a structured,
human-readable situation report that serves as the LLM prompt body.

The report is capped at ~30 lines to fit comfortably within a system-prompt
context window.  Units are grouped by allegiance and type; zones and status
conditions (under fire, numerical disadvantage) are highlighted.

Author: Patrick Cooper
"""

from __future__ import annotations

import re
from collections import defaultdict

from blanc.core.theory import Theory, RuleType
from blanc.reasoning.defeasible import defeasible_provable


# ---------------------------------------------------------------------------
# Fact-classification helpers
# ---------------------------------------------------------------------------

# Ordered predicate families for grouping
_UNIT_TYPE_PREDS = {
    "infantry_unit", "armored_unit", "fighter_unit", "bomber_unit",
    "worker_unit", "medic_unit", "transport_unit", "sensor_unit", "support_unit",
    "military_unit",
}
_ZONE_PRED      = "in_zone"
_FIRE_PRED      = "under_direct_fire"
_DISADV_PRED    = "has_numerical_disadvantage"
_TARGET_PREDS   = {"military_target", "worker_target"}
_MISSION_PRED   = "assigned_to_mission"
_ALLIN_PRED     = "all_in_rush_detected"
_HVT_PRED       = "high_value_target_in_range"
_ESCAPE_PRED    = "target_attempting_escape"

_UNARY_RE  = re.compile(r"^(\w+)\((\w+)\)$")
_BINARY_RE = re.compile(r"^(\w+)\((\w+),\s*(\w+)\)$")


def _parse_fact(fact: str) -> tuple[str, list[str]]:
    m = _BINARY_RE.match(fact)
    if m:
        return m.group(1), [m.group(2), m.group(3)]
    m = _UNARY_RE.match(fact)
    if m:
        return m.group(1), [m.group(2)]
    return fact, []


def _group_facts(facts: set[str]) -> dict:
    """
    Group ground facts into semantic categories for the situation report.

    Returns a dict with keys:
        allied_units    : dict[unit_atom -> {"type": str, "zone": str, "status": list[str]}]
        enemy_units     : dict[unit_atom -> {"zone": str, "status": list[str]}]
        army_flags      : list[str]   (all_in_rush, target_attempting_escape, etc.)
        missions        : list[(unit, mission)]
    """
    allied_units: dict[str, dict] = {}
    enemy_units: dict[str, dict]  = {}
    army_flags: list[str]  = []
    missions: list[tuple]  = []

    target_atoms: set[str] = set()

    for fact in facts:
        pred, args = _parse_fact(fact)

        if pred in _TARGET_PREDS and args:
            target_atoms.add(args[0])

        elif pred in _UNIT_TYPE_PREDS and args:
            unit = args[0]
            if unit not in allied_units:
                allied_units[unit] = {"type": pred, "zone": None, "status": []}
            else:
                allied_units[unit]["type"] = pred  # more specific wins

        elif pred == _ZONE_PRED and len(args) == 2:
            unit, zone = args
            if unit in allied_units:
                allied_units[unit]["zone"] = zone
            else:
                enemy_units.setdefault(unit, {"zone": None, "status": []})
                enemy_units[unit]["zone"] = zone

        elif pred == _FIRE_PRED and args:
            unit = args[0]
            for registry in (allied_units, enemy_units):
                if unit in registry:
                    registry[unit]["status"].append("UNDER FIRE")

        elif pred == _DISADV_PRED and args:
            unit = args[0]
            if unit in allied_units:
                allied_units[unit]["status"].append("OUTNUMBERED")

        elif pred == _HVT_PRED and args:
            unit = args[0]
            if unit in allied_units:
                allied_units[unit]["status"].append("HVT IN RANGE")

        elif pred == _MISSION_PRED and len(args) == 2:
            missions.append((args[0], args[1]))

        elif pred == _ALLIN_PRED:
            army_flags.append("ALL-IN RUSH DETECTED")

        elif pred == _ESCAPE_PRED:
            army_flags.append("HIGH-VALUE TARGET ATTEMPTING ESCAPE")

    # Mark target atoms that did not appear in unit-type facts as enemy units
    for atom in target_atoms:
        if atom not in allied_units:
            enemy_units.setdefault(atom, {"zone": None, "status": []})

    return {
        "allied_units": allied_units,
        "enemy_units":  enemy_units,
        "army_flags":   army_flags,
        "missions":     missions,
    }


def _render_roe_rules(theory: Theory, max_rules: int = 12) -> list[str]:
    """
    Return a short list of active ROE rule descriptions for the system prompt.

    Renders the most-specific defeasible rules and defeaters in plain English.
    """
    lines: list[str] = []
    roe_predicates = {
        "authorized_to_engage":    "may engage",
        "~authorized_to_engage":   "may NOT engage",
        "ordered_to_retreat":      "must retreat",
        "must_use_minimum_force":  "must use minimum force only",
        "stealth_posture_active":  "must maintain stealth (no engagement)",
        "priority_target":         "is a priority target",
        "cleared_to_engage":       "is cleared to engage",
        "protected_from_attack":   "is protected from attack",
    }

    for rule in theory.rules:
        if rule.rule_type not in (RuleType.DEFEASIBLE, RuleType.DEFEATER):
            continue
        head_pred = rule.head.split("(")[0]
        if head_pred not in roe_predicates:
            continue
        desc = roe_predicates[head_pred]
        body_str = ", ".join(rule.body) if rule.body else "(unconditional)"
        label = rule.label or head_pred
        prefix = "DEFAULT" if rule.rule_type == RuleType.DEFEASIBLE else "EXCEPTION"
        lines.append(f"  [{prefix} {label}] When {body_str} -> unit {desc}")
        if len(lines) >= max_rules:
            break

    return lines


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_situation_report(
    theory: Theory,
    scenario_description: str | None = None,
    step: int | None = None,
    max_lines: int = 30,
) -> str:
    """
    Render the active Theory into a structured commander situation report.

    Parameters
    ----------
    theory : Theory
        The current game-state Theory (KB rules + lifted ground facts).
    scenario_description : str | None
        Optional scenario narrative (from ROE_LEVEL3_SEEDS description).
    step : int | None
        Current game step number for the header.
    max_lines : int
        Approximate cap on the number of lines in the report.

    Returns
    -------
    str
        A multi-line situation report suitable for direct injection into an
        LLM system prompt or user message.
    """
    grouped = _group_facts(theory.facts)
    allied  = grouped["allied_units"]
    enemy   = grouped["enemy_units"]
    flags   = grouped["army_flags"]
    missions = grouped["missions"]

    lines: list[str] = []

    # ── Header ───────────────────────────────────────────────────────────────
    step_str = f" (game step {step})" if step is not None else ""
    lines.append(f"=== BATTLEFIELD SITUATION REPORT{step_str} ===")

    if scenario_description:
        lines.append(f"SCENARIO: {scenario_description[:120]}")

    lines.append("")

    # ── Army-wide flags ──────────────────────────────────────────────────────
    if flags:
        lines.append("ALERTS:")
        for flag in flags:
            lines.append(f"  ! {flag}")
        lines.append("")

    # ── Missions ─────────────────────────────────────────────────────────────
    if missions:
        lines.append("ACTIVE MISSIONS:")
        for unit, mission in missions[:4]:
            lines.append(f"  {unit} -> {mission}")
        lines.append("")

    # ── Allied units ─────────────────────────────────────────────────────────
    if allied:
        lines.append(f"FRIENDLY UNITS ({len(allied)}):")
        for unit, info in list(allied.items())[:10]:
            zone   = info["zone"] or "unknown zone"
            utype  = info["type"].replace("_unit", "").replace("_", " ")
            status = " [" + ", ".join(info["status"]) + "]" if info["status"] else ""
            lines.append(f"  {unit}  ({utype})  zone={zone}{status}")
        lines.append("")

    # ── Enemy units ──────────────────────────────────────────────────────────
    if enemy:
        lines.append(f"ENEMY CONTACTS ({len(enemy)}):")
        for unit, info in list(enemy.items())[:10]:
            zone   = info["zone"] or "unknown zone"
            status = " [" + ", ".join(info["status"]) + "]" if info["status"] else ""
            lines.append(f"  {unit}  zone={zone}{status}")
        lines.append("")

    # ── Active ROE rules ─────────────────────────────────────────────────────
    roe_lines = _render_roe_rules(theory)
    if roe_lines:
        lines.append("ACTIVE RULES OF ENGAGEMENT:")
        lines.extend(roe_lines)
        lines.append("")

    # ── Orders prompt ────────────────────────────────────────────────────────
    unit_list = ", ".join(list(allied.keys())[:6])
    enemy_list = ", ".join(list(enemy.keys())[:6])
    lines += [
        "YOUR TASK:",
        "Issue orders for the friendly units listed above.",
        "Valid actions: attack(unit, target) | retreat(unit) | hold(unit)",
        "You MUST respect the Rules of Engagement listed above.",
        "",
        f"Friendly units: {unit_list or '(none visible)'}",
        f"Enemy contacts: {enemy_list or '(none visible)'}",
        "",
        "Return your orders as a JSON array, e.g.:",
        '  [{"action":"attack","unit":"marine_1","target":"enemy_1"},',
        '   {"action":"retreat","unit":"zealot_1"}]',
    ]

    return "\n".join(lines[:max_lines])


# ---------------------------------------------------------------------------
# ROE system prompt builder
# ---------------------------------------------------------------------------

_ROE_SYSTEM_PROMPT_TEMPLATE = """\
You are a battlefield commander operating under formal Rules of Engagement (ROE).
Your decisions are constrained by the Newport ROE Handbook framework:
  1. Self-defense overrides mission constraints.
  2. Mission constraints override general engagement authority.
  3. You must use minimum necessary force.
  4. Workers and non-combatants are protected from attack.
  5. Exclusion and restricted zones prohibit engagement.

You will receive a situation report each turn.  You must respond with a
JSON array of orders.  Each order has keys: "action", "unit", and optionally
"target".  Valid actions: "attack", "retreat", "hold".

Non-compliant orders will be flagged and you will be asked to revise them.
"""


def build_roe_system_prompt() -> str:
    """Return the fixed ROE commander system prompt."""
    return _ROE_SYSTEM_PROMPT_TEMPLATE.strip()
