"""
Order data class and tolerant LLM response parser.

Foundation models return unit orders in wildly inconsistent formats:
plain JSON, markdown-fenced JSON, bare bullet lists, or numbered lists.
This module provides a single ``parse_orders`` function that accepts all
of these and returns a list of well-formed ``Order`` objects.

Order schema:
    action : str   -- "attack" | "retreat" | "hold"
    unit   : str   -- atom name, e.g. "marine_00000041"
    target : str | None -- required for "attack"; None for "retreat" / "hold"

Author: Patrick Cooper
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class Order:
    """
    A single high-level battlefield order issued by the LLM commander.

    Attributes
    ----------
    action : str
        One of ``"attack"``, ``"retreat"``, or ``"hold"``.
    unit : str
        Prolog-safe atom name of the acting unit (e.g. ``"marine_00000041"``).
    target : str | None
        Atom name of the target unit for ``attack`` orders.  None for
        ``retreat`` and ``hold``.
    raw : str
        The raw text fragment from the LLM response that produced this order.
        Retained for debugging and re-prompt construction.
    """
    action: str
    unit: str
    target: str | None = None
    raw: str = field(default="", compare=False)

    def __post_init__(self) -> None:
        self.action = self.action.lower().strip()
        self.unit = self.unit.lower().strip()
        if self.target is not None:
            self.target = self.target.lower().strip()
        valid = {"attack", "retreat", "hold"}
        if self.action not in valid:
            raise ValueError(f"Unknown action {self.action!r}; expected one of {valid}")
        if self.action == "attack" and not self.target:
            raise ValueError("attack orders require a target")

    def to_dict(self) -> dict:
        return {
            "action": self.action,
            "unit": self.unit,
            "target": self.target,
        }


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)
_ATOM_RE  = re.compile(r"[a-z][a-z0-9_]*(?:_[0-9a-f]{8})?", re.IGNORECASE)


def _extract_json_candidates(text: str) -> list[str]:
    """
    Return a list of JSON strings to try parsing from ``text``.

    Priority:
      1. Fenced code blocks (```json ... ``` or ``` ... ```)
      2. Top-level JSON array / object found by bracket matching
      3. The whole text as-is
    """
    candidates: list[str] = []

    for m in _FENCE_RE.finditer(text):
        candidates.append(m.group(1).strip())

    # Walk text for top-level [ ... ] or { ... }
    for start_ch, end_ch in (("[", "]"), ("{", "}")):
        i = text.find(start_ch)
        if i == -1:
            continue
        depth = 0
        for j, ch in enumerate(text[i:], start=i):
            if ch == start_ch:
                depth += 1
            elif ch == end_ch:
                depth -= 1
                if depth == 0:
                    candidates.append(text[i : j + 1])
                    break

    candidates.append(text)
    return candidates


def _parse_json_orders(text: str) -> list[Order] | None:
    """
    Attempt to parse ``text`` as JSON containing a list of orders.

    Accepts:
      - Array of objects: ``[{"action":"attack","unit":"m","target":"e"}, ...]``
      - Single object:    ``{"action":"retreat","unit":"m"}``
      - Array at any nesting level if there is a top-level ``"orders"`` key.
    """
    for candidate in _extract_json_candidates(text):
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue

        raw_list: list[dict] = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            if "orders" in data:
                raw_list = data["orders"] if isinstance(data["orders"], list) else [data["orders"]]
            else:
                raw_list = [data]

        orders: list[Order] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            action  = str(item.get("action", "")).lower().strip()
            unit    = str(item.get("unit", "")).lower().strip()
            target  = item.get("target")
            if target is not None:
                target = str(target).lower().strip() or None
            if action and unit:
                try:
                    orders.append(Order(action=action, unit=unit, target=target,
                                        raw=json.dumps(item)))
                except ValueError:
                    continue
        if orders:
            return orders

    return None


# Natural-language action synonyms
_ACTION_SYNONYMS: dict[str, str] = {
    "attack": "attack", "engage": "attack", "fire": "attack", "shoot": "attack",
    "strike": "attack", "assault": "attack",
    "retreat": "retreat", "withdraw": "retreat", "fall back": "retreat",
    "move back": "retreat", "pull back": "retreat", "disengage": "retreat",
    "hold": "hold", "hold position": "hold", "stand by": "hold", "wait": "hold",
    "maintain position": "hold", "defend": "hold",
}


def _parse_prose_orders(text: str) -> list[Order]:
    """
    Extract orders from prose / bullet-list LLM responses.

    Recognises patterns like:
      - "attack marine on enemy_probe_line"
      - "retreat zealot"
      - "hold marine"
      - "1. attack marine enemy_squad"
    """
    orders: list[Order] = []
    # Normalise bullet / numbered prefixes
    cleaned = re.sub(r"^[\s\-*\d.]+", "", text, flags=re.MULTILINE)

    for line in cleaned.splitlines():
        line = line.strip().lower()
        if not line:
            continue

        # Try each action synonym at the start of the line
        matched_action: str | None = None
        rest: str = ""
        # Sort by length descending so multi-word synonyms match first
        for syn, canonical in sorted(_ACTION_SYNONYMS.items(),
                                     key=lambda x: len(x[0]), reverse=True):
            if line.startswith(syn):
                matched_action = canonical
                rest = line[len(syn):].strip().strip(":").strip()
                break

        if not matched_action:
            continue

        # Extract atom names from the rest of the line
        atoms = _ATOM_RE.findall(rest)
        atoms = [a for a in atoms if len(a) >= 2]  # drop single chars
        if not atoms:
            continue

        unit = atoms[0]
        target = atoms[1] if len(atoms) >= 2 else None

        try:
            orders.append(Order(action=matched_action, unit=unit, target=target,
                                raw=line))
        except ValueError:
            continue

    return orders


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_orders(text: str) -> list[Order]:
    """
    Parse an LLM response string into a list of ``Order`` objects.

    Tries (in order):
      1. JSON / fenced-JSON parsing
      2. Prose / bullet-list parsing

    Returns an empty list if no orders can be extracted.

    Parameters
    ----------
    text : str
        Raw LLM response text.

    Returns
    -------
    list[Order]
    """
    text = text.strip()
    if not text:
        return []

    # Try structured JSON first
    json_orders = _parse_json_orders(text)
    if json_orders:
        return json_orders

    # Fall back to prose extraction
    return _parse_prose_orders(text)
