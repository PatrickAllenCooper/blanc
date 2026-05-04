"""
Novelty filter for the DeFAb-Math-Topology pipeline.

The cardinal failure mode of the experiment is *trivial restoration*: the
model just memorises the dropped hypothesis and Lean accepts it back.
This module supplies the filter that prevents trivial restoration from
counting as a positive result.

Two checks:

    1. Trivial-restoration mask.  A defeater is rejected if it is the dropped
       hypothesis under any of: byte-equality, whitespace-normalised equality,
       or coarse alpha-renaming-tolerant equality.  A real Mathlib-aware
       implementation would extend this with Lean-elaboration-time
       definitional equality; that hook is left explicit at
       :func:`NoveltyFilter._defn_equal`.

    2. Mathlib-membership.  A defeater that matches an existing Mathlib
       theorem statement (string + normalised form) is rejected as non-novel.
       The corpus of "known" Mathlib statements is supplied at construction
       time by the M3 driver, or loaded from a JSONL index file.

The novelty *distance* metric defaults to a bounded edit-distance over the
normalised Lean expressions.  Used by margin-weighted DPO at M2 to reward
strictly-weaker conditions over equivalents.

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

from blanc.math.types import Defeater, MathTheorem, NoveltyVerdict


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[(),]")


def normalised_lean_expr(expr: str) -> str:
    """Return a coarse canonical form of a Lean expression.

    Strips whitespace, normalises Unicode arrows to ASCII surrogates that
    are stable under copy-paste, and collapses runs of spaces.  This is
    intentionally weaker than Lean's definitional equality -- it must not
    over-match, since false positives here turn into false trivial-restoration
    rejections, and the cost of missing one definitionally-equal alias is
    just a slightly weaker filter.
    """
    expr = expr.strip()
    expr = expr.replace("\u2192", "->").replace("\u21d2", "=>")
    expr = expr.replace("\u2200", "forall ").replace("\u2203", "exists ")
    expr = _WS_RE.sub(" ", expr)
    return expr


def _alpha_normalise(expr: str) -> str:
    """Drop the binder names, keep the type structure.

    e.g. ``(x : \u211d) -> x > 0`` and ``(y : \u211d) -> y > 0`` collapse to
    the same string.  Coarse: drops anything inside parentheses that looks
    like a binder.  Used as a secondary trivial-restoration check.
    """
    cleaned = _PUNCT_RE.sub(" ", normalised_lean_expr(expr))
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    tokens: list[str] = []
    for tok in cleaned.split():
        # Identifier tokens of length <= 2 are presumed binder names.
        if tok.isalpha() and len(tok) <= 2:
            continue
        tokens.append(tok)
    return " ".join(tokens)


def _bounded_edit_distance(a: str, b: str, cap: int = 64) -> int:
    """Levenshtein bounded at ``cap`` (constant memory)."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if curr[j] < row_min:
                row_min = curr[j]
        if row_min >= cap:
            return cap
        prev = curr
    return min(prev[-1], cap)


def novelty_distance(a: str, b: str) -> float:
    """Coarse novelty distance in [0, 1] over normalised Lean expressions."""
    na = normalised_lean_expr(a)
    nb = normalised_lean_expr(b)
    if not na and not nb:
        return 0.0
    denom = max(len(na), len(nb), 1)
    return _bounded_edit_distance(na, nb) / denom


# ---------------------------------------------------------------------------
# NoveltyFilter
# ---------------------------------------------------------------------------


@dataclass
class NoveltyFilter:
    """Trivial-restoration mask + Mathlib-membership check.

    Args:
        mathlib_statements: Iterable of (identifier, lean_statement) pairs
            for the Mathlib symbols that count as "already known".  M3 fills
            this from the typed dependency graph; M0/M1 may pass an empty
            mapping and rely on the trivial-restoration check alone.
    """

    mathlib_statements: dict[str, str] = field(default_factory=dict)

    def __init__(
        self,
        mathlib_statements: Optional[Iterable[tuple[str, str]]] = None,
    ) -> None:
        self.mathlib_statements = dict(mathlib_statements or {})
        self._normalised_index: dict[str, str] = {
            normalised_lean_expr(stmt): ident
            for ident, stmt in self.mathlib_statements.items()
        }
        self._alpha_index: dict[str, str] = {
            _alpha_normalise(stmt): ident
            for ident, stmt in self.mathlib_statements.items()
        }
        self.mathlib_commit: Optional[str] = None
        self.loaded_count: int = len(self.mathlib_statements)

    @classmethod
    def from_jsonl(cls, path: Path) -> "NoveltyFilter":
        """Load the Mathlib novelty index from a JSONL file.

        Each line must be a JSON object with at least ``identifier`` and
        ``statement`` fields (produced by
        :func:`scripts.extract_mathlib_topology_index.main`).  The optional
        ``mathlib_commit`` field is recorded for reproducibility logging.

        Args:
            path: Path to the JSONL index file.

        Returns:
            A populated :class:`NoveltyFilter`.
        """
        pairs: list[tuple[str, str]] = []
        commit: Optional[str] = None
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if "_meta" in row:
                commit = row["_meta"].get("mathlib_commit")
                continue
            ident = row.get("identifier", "")
            stmt = row.get("statement", "")
            if ident and stmt:
                pairs.append((ident, stmt))
        instance = cls(mathlib_statements=pairs)
        instance.mathlib_commit = commit
        instance.loaded_count = len(pairs)
        return instance

    def _defn_equal(self, a: str, b: str) -> bool:
        """Hook: return True iff ``a`` and ``b`` are Lean-definitionally equal.

        Default: structural equality after normalisation + alpha-equivalence.
        A future implementation may replace this with a Lean-elaboration call
        through the harness.  Kept as an instance method so subclasses can
        override.
        """
        if normalised_lean_expr(a) == normalised_lean_expr(b):
            return True
        return _alpha_normalise(a) == _alpha_normalise(b)

    def evaluate(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...],
    ) -> NoveltyVerdict:
        """Score a defeater for trivial restoration + Mathlib novelty."""
        for name in masked_hypotheses:
            dropped_expr = theorem.hypothesis_by_name(name).lean_expr
            if self._defn_equal(defeater.lean_expr, dropped_expr):
                return NoveltyVerdict(
                    is_trivial_restoration=True,
                    matches_mathlib=False,
                    distance=0.0,
                )

        normal = normalised_lean_expr(defeater.lean_expr)
        if normal in self._normalised_index:
            return NoveltyVerdict(
                is_trivial_restoration=False,
                matches_mathlib=True,
                matched_identifier=self._normalised_index[normal],
                distance=0.0,
            )
        alpha = _alpha_normalise(defeater.lean_expr)
        if alpha in self._alpha_index:
            return NoveltyVerdict(
                is_trivial_restoration=False,
                matches_mathlib=True,
                matched_identifier=self._alpha_index[alpha],
                distance=0.0,
            )

        if masked_hypotheses:
            distance = min(
                novelty_distance(
                    defeater.lean_expr,
                    theorem.hypothesis_by_name(n).lean_expr,
                )
                for n in masked_hypotheses
            )
        else:
            distance = 1.0
        return NoveltyVerdict(
            is_trivial_restoration=False,
            matches_mathlib=False,
            distance=distance,
        )



# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


_WS_RE = re.compile(r"\s+")
_PUNCT_RE = re.compile(r"[(),]")


def normalised_lean_expr(expr: str) -> str:
    """Return a coarse canonical form of a Lean expression.

    Strips whitespace, normalises Unicode arrows to ASCII surrogates that
    are stable under copy-paste, and collapses runs of spaces.  This is
    intentionally weaker than Lean's definitional equality -- it must not
    over-match, since false positives here turn into false trivial-restoration
    rejections, and the cost of missing one definitionally-equal alias is
    just a slightly weaker filter.
    """
    expr = expr.strip()
    expr = expr.replace("\u2192", "->").replace("\u21d2", "=>")
    expr = expr.replace("\u2200", "forall ").replace("\u2203", "exists ")
    expr = _WS_RE.sub(" ", expr)
    return expr


def _alpha_normalise(expr: str) -> str:
    """Drop the binder names, keep the type structure.

    e.g. ``(x : \u211d) -> x > 0`` and ``(y : \u211d) -> y > 0`` collapse to
    the same string.  Coarse: drops anything inside parentheses that looks
    like a binder.  Used as a secondary trivial-restoration check.
    """
    cleaned = _PUNCT_RE.sub(" ", normalised_lean_expr(expr))
    cleaned = _WS_RE.sub(" ", cleaned).strip()
    tokens: list[str] = []
    for tok in cleaned.split():
        # Identifier tokens of length <= 2 are presumed binder names.
        if tok.isalpha() and len(tok) <= 2:
            continue
        tokens.append(tok)
    return " ".join(tokens)


def _bounded_edit_distance(a: str, b: str, cap: int = 64) -> int:
    """Levenshtein bounded at ``cap`` (constant memory)."""
    if a == b:
        return 0
    if abs(len(a) - len(b)) > cap:
        return cap
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i] + [0] * len(b)
        row_min = i
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            curr[j] = min(curr[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
            if curr[j] < row_min:
                row_min = curr[j]
        if row_min >= cap:
            return cap
        prev = curr
    return min(prev[-1], cap)


def novelty_distance(a: str, b: str) -> float:
    """Coarse novelty distance in [0, 1] over normalised Lean expressions."""
    na = normalised_lean_expr(a)
    nb = normalised_lean_expr(b)
    if not na and not nb:
        return 0.0
    denom = max(len(na), len(nb), 1)
    return _bounded_edit_distance(na, nb) / denom


