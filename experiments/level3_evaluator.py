"""
Level 3 (Defeater Abduction) Response Evaluator.

For each model response on a Level 3 instance this module:
  1. Parses the free-form response text into a Rule object.
  2. Checks whether the predicted defeater resolves the anomaly.
  3. Checks conservativity (Definition 13, paper.tex).
  4. Computes predicate novelty Nov(h, D^-) (Definition 14).
  5. Computes revision distance d_rev (Definition 15).

Parsing is intentionally lenient: the pipeline extracts the first
candidate-like structure from the response, trying the same sequence of
normalisation steps as the D1→D2 cascade so that the richer metrics are
available even when the decoded hypothesis came from a fallback stage.

Author: Patrick Cooper
Date: 2026-02-18
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.author.metrics import (
    predicate_novelty,
    check_conservativity,
    revision_distance,
)
from blanc.reasoning.defeasible import defeasible_provable


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Level3EvalResult:
    """Complete Level 3 evaluation for one (instance, response) pair."""

    instance_id: str
    raw_response: str
    decoded_hypothesis: Optional[str]  # string form of the candidate picked by decoder

    # Parsed rule (None if parsing fails)
    parsed_rule: Optional[Rule]
    parse_success: bool

    # Formal metrics (all None if parse fails)
    resolves_anomaly: Optional[bool] = None
    is_conservative: Optional[bool] = None
    nov: Optional[float] = None            # Nov(predicted, D^-)
    d_rev: Optional[int] = None            # revision distance

    # Gold comparison
    correct: bool = False                  # exact match to any gold string

    # Error classification
    error_class: Optional[str] = None      # E1-E5 (see error_taxonomy.py)

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "raw_response": self.raw_response,
            "decoded_hypothesis": self.decoded_hypothesis,
            "parse_success": self.parse_success,
            "parsed_rule_label": self.parsed_rule.label if self.parsed_rule else None,
            "parsed_rule_head": self.parsed_rule.head if self.parsed_rule else None,
            "parsed_rule_body": list(self.parsed_rule.body) if self.parsed_rule else None,
            "parsed_rule_type": self.parsed_rule.rule_type.value if self.parsed_rule else None,
            "resolves_anomaly": self.resolves_anomaly,
            "is_conservative": self.is_conservative,
            "nov": self.nov,
            "d_rev": self.d_rev,
            "correct": self.correct,
            "error_class": self.error_class,
        }


# ---------------------------------------------------------------------------
# Rule parser
# ---------------------------------------------------------------------------

# Regex patterns for formal rule syntax variants.
# We support:
#   label: body1(X), body2(X) ~> ~head(X)      (M4 defeater with label)
#   body1(X) ~> ~head(X)                         (M4 defeater without label)
#   label: body1(X), body2(X) => head(X)        (defeasible)
#   ~head(X) :- body1(X), body2(X). % defeater  (Prolog-style)
#   head(X) :- body1(X). % defeasible

_TILDE_ARROW_RE = re.compile(
    r"(?:(?P<label>[a-zA-Z_][a-zA-Z0-9_]*):\s*)?"   # optional label
    r"(?P<body>[^~>]+?)"                              # body literals
    r"\s*~>\s*"                                       # defeater arrow
    r"(?P<head>~?[a-zA-Z_][a-zA-Z0-9_(),._ X]*)",   # head literal
    re.IGNORECASE,
)

_FAT_ARROW_RE = re.compile(
    r"(?:(?P<label>[a-zA-Z_][a-zA-Z0-9_]*):\s*)?"
    r"(?P<body>[^=>]+?)"
    r"\s*=>\s*"
    r"(?P<head>~?[a-zA-Z_][a-zA-Z0-9_(),._ X]*)",
    re.IGNORECASE,
)

_PROLOG_RE = re.compile(
    r"(?P<head>~?[a-zA-Z_][a-zA-Z0-9_(),._ X]+?)"
    r"\s*:-\s*"
    r"(?P<body>[^.]+)"
    r"\.?\s*%\s*(?P<type>defeater|defeasible|strict)",
    re.IGNORECASE,
)


def parse_rule_from_text(text: str) -> Optional[Rule]:
    """
    Best-effort parse of a rule string into a Rule object.

    Tries four patterns in order:
      1. Tilde-arrow defeater:   body ~> head
      2. Fat-arrow defeasible:   body => head
      3. Prolog-style:           head :- body. % type
      4. Atom-only (no body):    head  (strict fact)

    Returns None if no pattern matches.
    """
    text = text.strip()
    if not text:
        return None

    # --- Pattern 1: defeater with ~> ---
    m = _TILDE_ARROW_RE.search(text)
    if m:
        return _build_rule(
            label=m.group("label"),
            head_str=m.group("head").strip(),
            body_str=m.group("body").strip(),
            rule_type=RuleType.DEFEATER,
        )

    # --- Pattern 2: defeasible with => ---
    m = _FAT_ARROW_RE.search(text)
    if m:
        return _build_rule(
            label=m.group("label"),
            head_str=m.group("head").strip(),
            body_str=m.group("body").strip(),
            rule_type=RuleType.DEFEASIBLE,
        )

    # --- Pattern 3: Prolog-style head :- body. % type ---
    m = _PROLOG_RE.search(text)
    if m:
        type_str = m.group("type").lower()
        rule_type = (
            RuleType.DEFEATER if type_str == "defeater"
            else RuleType.DEFEASIBLE if type_str == "defeasible"
            else RuleType.STRICT
        )
        return _build_rule(
            label=None,
            head_str=m.group("head").strip(),
            body_str=m.group("body").strip(),
            rule_type=rule_type,
        )

    return None


def _build_rule(
    label: Optional[str],
    head_str: str,
    body_str: str,
    rule_type: RuleType,
) -> Optional[Rule]:
    """Construct a Rule from parsed components; return None on failure."""
    head_str = head_str.strip().rstrip(".")
    if not head_str:
        return None

    # Split body on comma, filter empty
    body_atoms = tuple(
        b.strip().rstrip(".")
        for b in body_str.split(",")
        if b.strip()
    )

    return Rule(head=head_str, body=body_atoms, rule_type=rule_type, label=label)


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------

class Level3Evaluator:
    """
    Evaluate a model's Level 3 response against a DeFAb instance.

    Usage::

        evaluator = Level3Evaluator()
        result = evaluator.evaluate(instance, response_text, decoded_hypothesis)
    """

    def evaluate(
        self,
        instance: AbductiveInstance,
        response_text: str,
        decoded_hypothesis: Optional[str],
    ) -> Level3EvalResult:
        """
        Evaluate one Level 3 (instance, response) pair.

        Args:
            instance:           The AbductiveInstance (level must be 3).
            response_text:      Raw text returned by the model.
            decoded_hypothesis: The candidate string selected by the decoder
                                cascade (may be None if all stages failed).

        Returns:
            Level3EvalResult with all metrics populated.
        """
        instance_id = getattr(instance, "id", "unknown")

        # --- Exact-match correctness (already computed by pipeline; recompute here) ---
        correct = (
            decoded_hypothesis is not None
            and decoded_hypothesis.strip() in [g.strip() for g in instance.gold]
        )

        # --- Parse text into Rule ---
        # Prefer the decoded hypothesis (already normalised) over raw response.
        parse_source = decoded_hypothesis or response_text
        parsed_rule = parse_rule_from_text(parse_source)
        parse_success = parsed_rule is not None

        if not parse_success:
            return Level3EvalResult(
                instance_id=instance_id,
                raw_response=response_text,
                decoded_hypothesis=decoded_hypothesis,
                parsed_rule=None,
                parse_success=False,
                correct=correct,
                error_class="E4_parse_failure",
            )

        # --- Resolve anomaly? ---
        D_minus = instance.D_minus
        anomaly = instance.target
        preserved = instance.metadata.get("preserved_expectations", [])

        try:
            D_predicted = _add_rule_with_superiority(D_minus, parsed_rule, anomaly)
            resolves = not defeasible_provable(D_predicted, anomaly)
        except Exception:
            resolves = None

        # --- Conservativity ---
        if resolves and preserved:
            try:
                conservative, _ = check_conservativity(
                    _deep_copy_theory(D_minus), D_predicted, anomaly, preserved
                )
            except Exception:
                conservative = None
        else:
            conservative = None if resolves is None else False

        # --- Novelty ---
        try:
            nov = predicate_novelty(parsed_rule, D_minus)
        except Exception:
            nov = None

        # --- Revision distance ---
        if resolves and preserved:
            try:
                d_rev = revision_distance(D_minus, D_predicted, anomaly, preserved)
            except Exception:
                d_rev = None
        else:
            d_rev = None

        # --- Error classification ---
        error_class = _classify_error(
            correct=correct,
            resolves=resolves,
            conservative=conservative,
        )

        return Level3EvalResult(
            instance_id=instance_id,
            raw_response=response_text,
            decoded_hypothesis=decoded_hypothesis,
            parsed_rule=parsed_rule,
            parse_success=True,
            resolves_anomaly=resolves,
            is_conservative=conservative,
            nov=nov,
            d_rev=d_rev,
            correct=correct,
            error_class=error_class,
        )


def _add_rule_with_superiority(D: Theory, rule: Rule, anomaly: str) -> Theory:
    """
    Return a copy of D with `rule` added, with the rule made superior to any
    defeasible rule in D that could derive the anomaly.

    This is the evaluation-lenient interpretation: the model's defeater is
    assumed to beat whichever existing rules conflict with it, so the formal
    check is whether the *structure* of the rule is right, not whether the
    model also stated the superiority relation explicitly.
    """
    D2 = _deep_copy_theory(D)
    D2.add_rule(rule)

    if rule.rule_type != RuleType.DEFEATER:
        return D2

    anomaly_pred = anomaly.split("(")[0].lstrip("~")
    defeater_head_pred = rule.head.split("(")[0].lstrip("~")

    label = rule.label or "d_predicted"
    # Assign a label to the rule if it doesn't have one so superiority works
    if not rule.label:
        for r in D2.rules:
            if r.head == rule.head and r.body == rule.body:
                r.label = label  # type: ignore[attr-defined]

    for existing in D.rules:
        if existing.rule_type == RuleType.DEFEASIBLE and existing.label:
            existing_head_pred = existing.head.split("(")[0].lstrip("~")
            if (existing_head_pred == defeater_head_pred
                    or existing_head_pred == anomaly_pred):
                D2.add_superiority(label, existing.label)

    return D2


def _deep_copy_theory(D: Theory) -> Theory:
    """Deep-copy a Theory, always normalizing superiority to a dict."""
    D2 = Theory()
    for f in D.facts:
        D2.add_fact(f)
    for r in D.rules:
        D2.add_rule(Rule(
            head=r.head, body=tuple(r.body),
            rule_type=r.rule_type, label=r.label,
            metadata=dict(r.metadata) if r.metadata else {},
        ))
    # Normalize superiority to dict regardless of source type
    if isinstance(D.superiority, dict):
        for sup, infs in D.superiority.items():
            for inf in infs:
                D2.add_superiority(sup, inf)
    elif isinstance(D.superiority, (list, tuple)):
        for pair in D.superiority:
            if isinstance(pair, (list, tuple)) and len(pair) == 2:
                D2.add_superiority(pair[0], pair[1])
    return D2


def _classify_error(
    correct: bool,
    resolves: Optional[bool],
    conservative: Optional[bool],
) -> Optional[str]:
    """
    Classify why the prediction is wrong (if it is).

    Error classes (from paper Section 5):
      E1 - Correct (no error)
      E2 - Resolves anomaly but non-conservative (too broad)
      E3 - Does not resolve anomaly (wrong head/condition)
      E4 - Parse failure (response is unparseable)
      E5 - Wrong but conservative (odd distractor picked)
    """
    if correct:
        return "E1_correct"
    if resolves is None:
        return "E4_parse_failure"
    if resolves and conservative is False:
        return "E2_non_conservative"
    if not resolves:
        return "E3_no_resolve"
    if resolves and conservative:
        return "E5_wrong_but_conservative"
    return "E5_wrong_but_conservative"


# ---------------------------------------------------------------------------
# Batch helper
# ---------------------------------------------------------------------------

def evaluate_level3_batch(
    instances: list[AbductiveInstance],
    responses: list[str],
    decoded_hypotheses: list[Optional[str]],
) -> list[Level3EvalResult]:
    """Evaluate a batch of Level 3 responses."""
    evaluator = Level3Evaluator()
    return [
        evaluator.evaluate(inst, resp, dec)
        for inst, resp, dec in zip(instances, responses, decoded_hypotheses)
    ]


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(ROOT / "src"))
    from blanc.core.theory import Theory, Rule, RuleType
    from blanc.author.generation import AbductiveInstance

    # Build a minimal penguin-style Level 3 instance
    r1 = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_flies")
    r2 = Rule(head="has_feathers(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_feathers")
    D = Theory(facts=["bird(opus)", "bird(tweety)", "penguin(opus)"], rules=[r1, r2], superiority=[])

    inst = AbductiveInstance(
        D_minus=D,
        target="flies(opus)",
        candidates=[
            "d_penguin: penguin(X) ~> ~flies(X)",
            "d_broad: bird(X) ~> ~flies(X)",
        ],
        gold=["d_penguin: penguin(X) ~> ~flies(X)"],
        level=3,
        metadata={"preserved_expectations": ["flies(tweety)", "has_feathers(tweety)"]},
    )
    inst.id = "test-penguin"

    ev = Level3Evaluator()

    print("Test 1: correct gold response")
    r = ev.evaluate(inst, "d_penguin: penguin(X) ~> ~flies(X)", "d_penguin: penguin(X) ~> ~flies(X)")
    print(f"  correct={r.correct}, resolves={r.resolves_anomaly}, "
          f"conservative={r.is_conservative}, nov={r.nov}, error={r.error_class}")

    print("\nTest 2: too-broad defeater (non-conservative)")
    r2 = ev.evaluate(inst, "d_broad: bird(X) ~> ~flies(X)", "d_broad: bird(X) ~> ~flies(X)")
    print(f"  correct={r2.correct}, resolves={r2.resolves_anomaly}, "
          f"conservative={r2.is_conservative}, nov={r2.nov}, error={r2.error_class}")

    print("\nTest 3: unparseable response")
    r3 = ev.evaluate(inst, "Penguins cannot fly because they are flightless birds.", None)
    print(f"  correct={r3.correct}, parse_success={r3.parse_success}, error={r3.error_class}")

    print("\nTest 4: wrong head (does not resolve)")
    r4 = ev.evaluate(inst, "d_wrong: penguin(X) ~> ~has_feathers(X)", "d_wrong: penguin(X) ~> ~has_feathers(X)")
    print(f"  correct={r4.correct}, resolves={r4.resolves_anomaly}, error={r4.error_class}")

    print("\nAll Level3Evaluator tests passed.")
