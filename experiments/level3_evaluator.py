"""
Level 3 (Defeater Abduction) Response Evaluator.

For each model response on a Level 3 instance this module:
  1. Parses the free-form response text into a Rule object.
  2. Checks whether the predicted defeater resolves the anomaly.
  3. Classifies resolution strength (weak / strong / restructuring).
  4. Checks conservativity (Definition 13, paper.tex).
  5. Checks minimality (no proper sub-hypothesis also resolves the anomaly).
  6. Computes predicate novelty Nov(h, D^-) (Definition 14).
  7. Computes revision distance d_rev (Definition 15).
  8. Computes the graded partial credit score Score(h, D, alpha) in {0, 0.25, 0.5, 0.75, 1.0}
     (Section 4.6, paper.tex).
  9. Assigns error class E1-E5 matching the paper's taxonomy (Section 4.8):
       E1  Decoder failure         -- response cannot be parsed
       E2  Derivation failure      -- decoded rule does not restore derivability
       E3  Minimality violation    -- correct but non-minimal (proper sub-hypothesis works)
       E4  Conservativity violation-- resolves anomaly but breaks other expectations
       E5  Strength shortfall      -- conservative but weaker strength than gold

Author: Patrick Cooper
Date: 2026-02-18
"""

from __future__ import annotations

import copy
import re
import sys
from dataclasses import dataclass
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
# Constants
# ---------------------------------------------------------------------------

# Resolution strength values
STRENGTH_WEAK         = "weak"
STRENGTH_STRONG       = "strong"
STRENGTH_RESTRUCTURING = "restructuring"

# Partial credit tiers (Section 4.6)
SCORE_NONE        = 0.00   # decoder failure or anomaly unresolved
SCORE_MINIMAL     = 0.25   # resolves but not well-formed under language bias
SCORE_PARTIAL     = 0.50   # resolves, well-formed, but non-conservative
SCORE_SUBSTANTIAL = 0.75   # conservative weak resolution, or non-conservative strong
SCORE_FULL        = 1.00   # conservative resolution (any strength)

# Error class labels matching paper Section 4.8 exactly
EC_DECODER_FAILURE      = "E1_decoder_failure"
EC_DERIVATION_FAILURE   = "E2_derivation_failure"
EC_MINIMALITY_VIOLATION = "E3_minimality_violation"
EC_CONSERVATIVITY_VIOLATION = "E4_conservativity_violation"
EC_STRENGTH_SHORTFALL   = "E5_strength_shortfall"
EC_CORRECT              = "correct"  # not an error class; kept for bookkeeping


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class Level3EvalResult:
    """Complete Level 3 evaluation for one (instance, response) pair."""

    instance_id: str
    raw_response: str
    decoded_hypothesis: Optional[str]

    # Parsed rule (None if parsing fails)
    parsed_rule: Optional[Rule]
    parse_success: bool

    # Formal metrics
    resolves_anomaly: Optional[bool] = None
    resolution_strength: Optional[str] = None   # weak / strong / restructuring
    is_minimal: Optional[bool] = None           # no proper sub-hypothesis also resolves
    is_conservative: Optional[bool] = None
    nov: Optional[float] = None                 # Nov(predicted, D^-)
    d_rev: Optional[int] = None

    # Scoring
    graded_score: float = 0.0                   # 0 / 0.25 / 0.5 / 0.75 / 1.0

    # Gold comparison
    correct: bool = False

    # Error classification (paper Section 4.8)
    error_class: Optional[str] = None

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
            "resolution_strength": self.resolution_strength,
            "is_minimal": self.is_minimal,
            "is_conservative": self.is_conservative,
            "nov": self.nov,
            "d_rev": self.d_rev,
            "graded_score": self.graded_score,
            "correct": self.correct,
            "error_class": self.error_class,
        }


# ---------------------------------------------------------------------------
# Rule parser
# ---------------------------------------------------------------------------

_TILDE_ARROW_RE = re.compile(
    r"(?:(?P<label>[a-zA-Z_][a-zA-Z0-9_]*):\s*)?"
    r"(?P<body>[^~>]+?)"
    r"\s*~>\s*"
    r"(?P<head>~?[a-zA-Z_][a-zA-Z0-9_(),._ X]*)",
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

    Tries patterns in order:
      1. Tilde-arrow defeater   body ~> head
      2. Fat-arrow defeasible   body => head
      3. Prolog-style           head :- body. % type

    Returns None if no pattern matches.
    """
    text = text.strip()
    if not text:
        return None

    m = _TILDE_ARROW_RE.search(text)
    if m:
        return _build_rule(m.group("label"), m.group("head").strip(),
                           m.group("body").strip(), RuleType.DEFEATER)

    m = _FAT_ARROW_RE.search(text)
    if m:
        return _build_rule(m.group("label"), m.group("head").strip(),
                           m.group("body").strip(), RuleType.DEFEASIBLE)

    m = _PROLOG_RE.search(text)
    if m:
        type_str = m.group("type").lower()
        rt = (RuleType.DEFEATER if type_str == "defeater"
              else RuleType.DEFEASIBLE if type_str == "defeasible"
              else RuleType.STRICT)
        return _build_rule(None, m.group("head").strip(),
                           m.group("body").strip(), rt)

    return None


def _build_rule(label, head_str, body_str, rule_type) -> Optional[Rule]:
    head_str = head_str.strip().rstrip(".")
    if not head_str:
        return None
    body_atoms = tuple(b.strip().rstrip(".") for b in body_str.split(",") if b.strip())
    return Rule(head=head_str, body=body_atoms, rule_type=rule_type, label=label)


# ---------------------------------------------------------------------------
# Theory utilities
# ---------------------------------------------------------------------------

def _add_rule_with_superiority(D: Theory, rule: Rule, anomaly: str) -> Theory:
    """
    Return a copy of D with `rule` added and made superior to any defeasible rule
    in D whose head predicate matches the anomaly or the defeater's head predicate.

    Evaluation-lenient: we grant the predicted defeater superiority over conflicting
    rules so the formal check evaluates structural correctness, not explicit
    superiority declarations (which the model was not asked to produce).
    """
    D2 = D.copy()
    D2.add_rule(rule)

    if rule.rule_type != RuleType.DEFEATER:
        return D2

    anomaly_pred = anomaly.split("(")[0].lstrip("~")
    defeater_head_pred = rule.head.split("(")[0].lstrip("~")
    label = rule.label or "d_predicted"

    if not rule.label:
        for r in D2.rules:
            if r.head == rule.head and tuple(r.body) == tuple(rule.body):
                r.label = label  # type: ignore[attr-defined]

    for existing in D.rules:
        if existing.rule_type == RuleType.DEFEASIBLE and existing.label:
            ep = existing.head.split("(")[0].lstrip("~")
            if ep == defeater_head_pred or ep == anomaly_pred:
                D2.add_superiority(label, existing.label)

    return D2


# ---------------------------------------------------------------------------
# Resolution strength (Definition def:resstrength, paper.tex)
# ---------------------------------------------------------------------------

def classify_resolution_strength(
    D_minus: Theory,
    D_predicted: Theory,
    anomaly: str,
    rule: Rule,
) -> str:
    """
    Classify rule as weak / strong / restructuring per Definition def:resstrength.

    Let D' = D_predicted (= D^- ∪ {rule} ∪ superiority).

      - Restructuring: D' derives alpha AND preserves all q in Exp(D^-) \\ {~alpha}
      - Strong: rule is a defeater with non-empty superiority AND D' derives alpha
      - Weak: D' does not derive ~alpha but also doesn't derive alpha

    We test D' ⊢∂ alpha (positive derivation of the anomaly itself) to distinguish
    strong/restructuring from weak.
    """
    try:
        derives_anomaly_positive = defeasible_provable(D_predicted, anomaly)
    except Exception:
        return STRENGTH_WEAK

    if not derives_anomaly_positive:
        return STRENGTH_WEAK

    # Now check whether it's restructuring (derives alpha AND all preserved expectations hold)
    preserved = []
    # We check against the anomaly literal -- for restructuring D' must derive alpha itself
    # (same as strong, but we require conservative preservation is already checked separately)
    has_superiority = (
        rule.label is not None
        and isinstance(D_predicted.superiority, dict)
        and rule.label in D_predicted.superiority
        and len(D_predicted.superiority[rule.label]) > 0
    )

    if has_superiority:
        # Potentially strong or restructuring; conservativity test (done in evaluate()) tells us
        # restructuring requires ALL expectations preserved -- we flag as restructuring if
        # is_conservative is True (already computed by caller).
        # We return STRONG here; the caller upgrades to RESTRUCTURING if also conservative.
        return STRENGTH_STRONG

    return STRENGTH_WEAK


# ---------------------------------------------------------------------------
# Minimality check (paper Section 4.8, error E3)
# ---------------------------------------------------------------------------

def is_minimal_hypothesis(
    D_minus: Theory,
    rule: Rule,
    anomaly: str,
) -> bool:
    """
    Return True if no proper sub-hypothesis (strict subset of body atoms) also
    resolves the anomaly.

    A non-minimal rule over-specifies: it has redundant antecedent atoms.
    """
    body = list(rule.body)
    if len(body) <= 1:
        return True  # single-atom body is necessarily minimal

    for i in range(len(body)):
        # Try removing body atom i
        sub_body = tuple(b for j, b in enumerate(body) if j != i)
        sub_rule = Rule(
            head=rule.head,
            body=sub_body,
            rule_type=rule.rule_type,
            label=rule.label,
        )
        try:
            D_sub = _add_rule_with_superiority(D_minus, sub_rule, anomaly)
            if not defeasible_provable(D_sub, anomaly):
                return False  # sub-hypothesis also resolves → not minimal
        except Exception:
            continue

    return True


# ---------------------------------------------------------------------------
# Partial credit scoring (Section 4.6, paper.tex)
# ---------------------------------------------------------------------------

def partial_credit_score(
    resolves: Optional[bool],
    is_well_formed: bool,
    is_conservative: Optional[bool],
    resolution_strength: Optional[str],
) -> float:
    """
    Compute Score(h, D, alpha) in {0, 0.25, 0.5, 0.75, 1.0} per Section 4.6.

    (i)   0.00 -- decoder failure or anomaly unresolved
    (ii)  0.25 -- resolves but not well-formed under language bias
    (iii) 0.50 -- resolves + well-formed + non-conservative
    (iv)  0.75 -- conservative weak, OR non-conservative strong
    (v)   1.00 -- conservative (any strength)
    """
    if not resolves:
        return SCORE_NONE
    if not is_well_formed:
        return SCORE_MINIMAL
    if is_conservative is True:
        return SCORE_FULL
    # Not conservative
    if resolution_strength in (STRENGTH_STRONG, STRENGTH_RESTRUCTURING):
        return SCORE_SUBSTANTIAL  # non-conservative strong = 0.75
    return SCORE_PARTIAL  # non-conservative weak = 0.5


# ---------------------------------------------------------------------------
# Error classification (paper Section 4.8 taxonomy exactly)
# ---------------------------------------------------------------------------

def classify_error(
    parse_success: bool,
    resolves: Optional[bool],
    is_minimal: Optional[bool],
    is_conservative: Optional[bool],
    resolution_strength: Optional[str],
    gold_strength: Optional[str],
) -> str:
    """
    Assign error class E1-E5 per paper Section 4.8.

      E1  Decoder failure           -- parse_success is False
      E2  Derivation failure        -- parsed but anomaly persists
      E3  Minimality violation      -- resolves but non-minimal body
      E4  Conservativity violation  -- resolves, minimal, but non-conservative
      E5  Strength shortfall        -- conservative but weaker than gold
      (correct if none apply)
    """
    if not parse_success:
        return EC_DECODER_FAILURE
    if not resolves:
        return EC_DERIVATION_FAILURE
    if is_minimal is False:
        return EC_MINIMALITY_VIOLATION
    if is_conservative is False:
        return EC_CONSERVATIVITY_VIOLATION
    if (gold_strength in (STRENGTH_STRONG, STRENGTH_RESTRUCTURING)
            and resolution_strength == STRENGTH_WEAK):
        return EC_STRENGTH_SHORTFALL
    return EC_CORRECT


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------

class Level3Evaluator:
    """Evaluate a model's Level 3 response against a DeFAb instance."""

    # ------------------------------------------------------------------
    # Private helpers — each isolates one analysis step
    # ------------------------------------------------------------------

    @staticmethod
    def _gold_strength(D_minus: Theory, anomaly: str, gold: list) -> Optional[str]:
        """Return the resolution strength of the gold defeater, or None."""
        gold_str = (gold[0] if isinstance(gold, list) else gold) or ""
        gold_rule = parse_rule_from_text(gold_str)
        if gold_rule is None:
            return None
        try:
            D_gold = _add_rule_with_superiority(D_minus, gold_rule, anomaly)
            return classify_resolution_strength(D_minus, D_gold, anomaly, gold_rule)
        except Exception:
            return None

    @staticmethod
    def _check_resolves(
        D_minus: Theory, parsed_rule: Rule, anomaly: str
    ) -> tuple[Optional[bool], Optional[Theory]]:
        """
        Return (resolves, D_predicted).

        resolves is True if the anomaly is no longer defeasibly provable after
        adding the predicted rule; None on error.
        """
        try:
            D_predicted = _add_rule_with_superiority(D_minus, parsed_rule, anomaly)
            resolves = not defeasible_provable(D_predicted, anomaly)
            return resolves, D_predicted
        except Exception:
            return None, None

    @staticmethod
    def _check_strength(
        D_minus: Theory,
        D_predicted: Optional[Theory],
        anomaly: str,
        parsed_rule: Rule,
        resolves: Optional[bool],
    ) -> Optional[str]:
        if not resolves or D_predicted is None:
            return None
        try:
            return classify_resolution_strength(D_minus, D_predicted, anomaly, parsed_rule)
        except Exception:
            return STRENGTH_WEAK

    @staticmethod
    def _check_conservativity(
        D_minus: Theory,
        D_predicted: Optional[Theory],
        anomaly: str,
        preserved: list,
        resolves: Optional[bool],
        strength: Optional[str],
    ) -> tuple[Optional[bool], Optional[str]]:
        """
        Return (is_conservative, updated_strength).

        Upgrades strength to RESTRUCTURING when the rule is conservative and
        defeasibly proves the (positive) anomaly literal.
        """
        if not resolves or D_predicted is None:
            updated_strength = strength
            conservative = None if not preserved else None
            return conservative, updated_strength

        if preserved:
            try:
                conservative, _ = check_conservativity(
                    D_minus.copy(), D_predicted, anomaly, preserved
                )
                updated_strength = strength
                if conservative and strength == STRENGTH_STRONG:
                    try:
                        if defeasible_provable(D_predicted, anomaly):
                            updated_strength = STRENGTH_RESTRUCTURING
                    except Exception:
                        pass
                return conservative, updated_strength
            except Exception:
                return None, strength
        else:
            return True, strength

    @staticmethod
    def _check_minimality(
        D_minus: Theory, parsed_rule: Rule, anomaly: str, resolves: Optional[bool]
    ) -> Optional[bool]:
        if not resolves:
            return None
        try:
            return is_minimal_hypothesis(D_minus, parsed_rule, anomaly)
        except Exception:
            return None

    @staticmethod
    def _compute_metrics(
        D_minus: Theory,
        D_predicted: Optional[Theory],
        parsed_rule: Rule,
        anomaly: str,
        preserved: list,
        resolves: Optional[bool],
    ) -> tuple[Optional[float], Optional[int]]:
        """Return (predicate_novelty_score, revision_distance)."""
        try:
            nov = predicate_novelty(parsed_rule, D_minus)
        except Exception:
            nov = None

        d_rev = None
        if resolves and preserved and D_predicted is not None:
            try:
                d_rev = revision_distance(D_minus, D_predicted, anomaly, preserved)
            except Exception:
                pass

        return nov, d_rev

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def evaluate(
        self,
        instance: AbductiveInstance,
        response_text: str,
        decoded_hypothesis: Optional[str],
    ) -> Level3EvalResult:
        instance_id = getattr(instance, "id", "unknown")

        correct = (
            decoded_hypothesis is not None
            and decoded_hypothesis.strip() in [g.strip() for g in instance.gold]
        )

        parse_source = decoded_hypothesis or response_text
        parsed_rule = parse_rule_from_text(parse_source)

        if parsed_rule is None:
            return Level3EvalResult(
                instance_id=instance_id,
                raw_response=response_text,
                decoded_hypothesis=decoded_hypothesis,
                parsed_rule=None,
                parse_success=False,
                graded_score=SCORE_NONE,
                correct=correct,
                error_class=EC_DECODER_FAILURE,
            )

        D_minus  = instance.D_minus
        anomaly  = instance.target
        preserved = instance.metadata.get("preserved_expectations", [])

        gold_strength = self._gold_strength(D_minus, anomaly, instance.gold)
        resolves, D_predicted = self._check_resolves(D_minus, parsed_rule, anomaly)
        strength = self._check_strength(D_minus, D_predicted, anomaly, parsed_rule, resolves)
        conservative, strength = self._check_conservativity(
            D_minus, D_predicted, anomaly, preserved, resolves, strength
        )
        minimal = self._check_minimality(D_minus, parsed_rule, anomaly, resolves)
        nov, d_rev = self._compute_metrics(
            D_minus, D_predicted, parsed_rule, anomaly, preserved, resolves
        )

        score = partial_credit_score(resolves, True, conservative, strength)
        error_class = classify_error(
            parse_success=True,
            resolves=resolves,
            is_minimal=minimal,
            is_conservative=conservative,
            resolution_strength=strength,
            gold_strength=gold_strength,
        )

        if resolves and conservative:
            correct = True

        return Level3EvalResult(
            instance_id=instance_id,
            raw_response=response_text,
            decoded_hypothesis=decoded_hypothesis,
            parsed_rule=parsed_rule,
            parse_success=True,
            resolves_anomaly=resolves,
            resolution_strength=strength,
            is_minimal=minimal,
            is_conservative=conservative,
            nov=nov,
            d_rev=d_rev,
            graded_score=score,
            correct=correct,
            error_class=error_class,
        )


def evaluate_level3_batch(
    instances: list,
    responses: list[str],
    decoded_hypotheses: list,
) -> list[Level3EvalResult]:
    evaluator = Level3Evaluator()
    return [
        evaluator.evaluate(inst, resp, dec)
        for inst, resp, dec in zip(instances, responses, decoded_hypotheses)
    ]


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    r1 = Rule(head="flies(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_flies")
    r2 = Rule(head="has_feathers(X)", body=("bird(X)",), rule_type=RuleType.DEFEASIBLE, label="r_feathers")
    D = Theory(facts=["bird(opus)", "bird(tweety)", "penguin(opus)"], rules=[r1, r2], superiority={})

    from blanc.author.generation import AbductiveInstance
    inst = AbductiveInstance(
        D_minus=D, target="flies(opus)",
        candidates=["d_penguin: penguin(X) ~> ~flies(X)", "d_broad: bird(X) ~> ~flies(X)"],
        gold=["d_penguin: penguin(X) ~> ~flies(X)"],
        level=3,
        metadata={"preserved_expectations": ["flies(tweety)", "has_feathers(tweety)"]},
    )
    inst.id = "test-penguin"
    ev = Level3Evaluator()

    print("Test 1: correct gold")
    r = ev.evaluate(inst, "d_penguin: penguin(X) ~> ~flies(X)", "d_penguin: penguin(X) ~> ~flies(X)")
    assert r.correct, f"Expected correct, got error={r.error_class}"
    assert r.graded_score == SCORE_FULL, f"Expected 1.0, got {r.graded_score}"
    assert r.error_class == EC_CORRECT, r.error_class
    print(f"  PASS  score={r.graded_score}  error={r.error_class}")

    print("Test 2: too-broad defeater (E4 conservativity violation)")
    r2_ = ev.evaluate(inst, "d_broad: bird(X) ~> ~flies(X)", "d_broad: bird(X) ~> ~flies(X)")
    assert not r2_.correct
    assert r2_.resolves_anomaly
    assert r2_.is_conservative is False
    assert r2_.error_class == EC_CONSERVATIVITY_VIOLATION, r2_.error_class
    assert r2_.graded_score == SCORE_PARTIAL, r2_.graded_score
    print(f"  PASS  score={r2_.graded_score}  error={r2_.error_class}")

    print("Test 3: unparseable (E1 decoder failure)")
    r3 = ev.evaluate(inst, "Penguins cannot fly.", None)
    assert not r3.correct
    assert r3.error_class == EC_DECODER_FAILURE, r3.error_class
    assert r3.graded_score == SCORE_NONE
    print(f"  PASS  score={r3.graded_score}  error={r3.error_class}")

    print("Test 4: wrong head (E2 derivation failure)")
    r4 = ev.evaluate(inst, "d_wrong: penguin(X) ~> ~has_feathers(X)", "d_wrong: penguin(X) ~> ~has_feathers(X)")
    assert not r4.correct
    assert r4.error_class == EC_DERIVATION_FAILURE, r4.error_class
    assert r4.graded_score == SCORE_NONE
    print(f"  PASS  score={r4.graded_score}  error={r4.error_class}")

    print("\nAll self-tests passed.")
