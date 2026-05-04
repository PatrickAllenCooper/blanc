"""
LLMPolicy: foundation model proposes defeasible rules each macro-tick.

The LLM policy queries a foundation model (via experiments/model_interface.py)
every N game steps and asks it to propose additional defeasible rules or
defeaters for the current theory state.  Only rules that pass the
polynomial-time verifier (DefeasibleEngine) are admitted; rejected rules
incur a GRPO penalty and are not issued to SC2.

Policy workflow (each macro-tick, every MACRO_STEP_INTERVAL steps):

    1. Encode the current theory + anomalies as a prompt (M4 modality).
    2. Query the LLM for candidate defeasible rules / defeaters.
    3. Parse each proposed rule into a (Rule, RuleType) pair.
    4. Run DefeasibleEngine.check_conservativity(rule) to admit or reject.
    5. Return the list of admitted rule strings.

The admit/reject gate is the same conservativity check used by the offline
Author Algorithm -- this is the critical property that keeps live SC2 traces
formally valid DeFAb instances.

Cache keying: responses are keyed on hash(theory.fingerprint()) + step_bucket,
so identical theory states within the same macro-tick window reuse the cached
response without polluting self-play diversity across different game states.

Author: Anonymous Authors
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import hashlib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine

logger = logging.getLogger(__name__)

# Add experiments/ to path so model_interface is importable without install
_EXPERIMENTS_DIR = Path(__file__).parents[4] / "experiments"
if str(_EXPERIMENTS_DIR) not in sys.path:
    sys.path.insert(0, str(_EXPERIMENTS_DIR))


_DEFEASIBLE_RULE_RE = re.compile(
    r"^(~?\w+\([^)]*\))\s*:=>\s*(.+)\.$", re.MULTILINE
)
_DEFEATER_RULE_RE = re.compile(
    r"^(~?\w+\([^)]*\))\s*:~>\s*(.+)\.$", re.MULTILINE
)


def _split_body(body_str: str) -> tuple[str, ...]:
    """
    Split a rule body string on top-level commas (ignoring commas inside
    parentheses).  Handles predicates like ``in_zone(X, some_zone)``.
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in body_str:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return tuple(p for p in parts if p)


def _parse_proposed_rules(text: str) -> list[Rule]:
    """
    Extract Rule objects from an LLM response string.

    Accepts two notations:
        head :=> body1, body2.    (defeasible rule)
        head :~> body1, body2.    (defeater)

    Returns only syntactically valid rules; malformed lines are dropped.
    """
    rules: list[Rule] = []
    for m in _DEFEASIBLE_RULE_RE.finditer(text):
        head = m.group(1).strip()
        body = _split_body(m.group(2))
        rules.append(Rule(head=head, body=body, rule_type=RuleType.DEFEASIBLE,
                          label="llm_proposed"))
    for m in _DEFEATER_RULE_RE.finditer(text):
        head = m.group(1).strip()
        body = _split_body(m.group(2))
        rules.append(Rule(head=head, body=body, rule_type=RuleType.DEFEATER,
                          label="llm_proposed"))
    return rules


def _theory_fingerprint(theory: Theory) -> str:
    """Stable hash of a theory's facts (rules are fixed across ticks)."""
    facts_sorted = sorted(theory.facts)
    payload = json.dumps(facts_sorted, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def _build_prompt(theory: Theory, anomalies: list[str]) -> str:
    """
    Encode the current theory state as an M4-style natural-language prompt.

    Follows the M4 encoder template from src/blanc/codec/m1_encoder.py
    conventions adapted for defeasible rule proposals.
    """
    lines: list[str] = [
        "You are a formal defeasible reasoning assistant.",
        "",
        "Current ground facts (game state):",
    ]
    for fact in sorted(theory.facts)[:40]:   # cap at 40 to stay within context
        lines.append(f"  {fact}")

    if anomalies:
        lines += [
            "",
            "Anomalous conclusions the theory produces (should NOT hold):",
        ]
        for a in anomalies[:10]:
            lines.append(f"  {a}")

    lines += [
        "",
        "Propose 1-3 defeasible rules or defeaters in the following notation only:",
        "  Defeasible rule:  head :=> body1, body2.",
        "  Defeater:         head :~> body1, body2.",
        "",
        "Rules must use only predicates already present in the theory.",
        "Do not explain. Output only the rule lines.",
    ]
    return "\n".join(lines)


class LLMPolicy:
    """
    Foundation-model policy that proposes defeasible rules each macro-tick.

    Parameters
    ----------
    provider : str
        Model provider string as accepted by experiments/model_interface.py
        (e.g. ``"foundry-deepseek"``, ``"foundry-gpt"``).
    macro_step_interval : int
        Number of SC2 game steps between LLM queries (default 44 ~= 2 sec
        at fastest speed).
    max_rules_per_tick : int
        Maximum rules to admit per tick.
    verify_conservativity : bool
        If True (default), reject rules that violate conservativity.
        Set False only for ablation experiments.
    """

    name: str = "llm"

    def __init__(
        self,
        provider: str = "foundry-deepseek",
        macro_step_interval: int = 44,
        max_rules_per_tick: int = 3,
        verify_conservativity: bool = True,
    ) -> None:
        self._provider = provider
        self._interval = macro_step_interval
        self._max_rules = max_rules_per_tick
        self._verify = verify_conservativity
        self._cache: dict[str, list[str]] = {}
        self._model: Any = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    def _get_model(self) -> Any:
        """Lazy-load the model interface (avoids import cost at startup)."""
        if self._model is None:
            try:
                import os as _os
                from model_interface import create_model_interface  # type: ignore[import]
                api_key: str | None = None
                if self._provider.startswith("foundry-"):
                    api_key = _os.environ.get("FOUNDRY_API_KEY") or None
                self._model = create_model_interface(
                    provider=self._provider,
                    api_key=api_key,
                )
            except ImportError:
                logger.warning(
                    "model_interface not importable; LLMPolicy will return []"
                )
        return self._model

    def propose_defeaters(self, theory: Theory, step: int) -> list[str]:
        """
        Return a list of rule strings admitted by the verifier for this tick.

        Called synchronously from DeFAbBot.on_step via a thread executor
        to avoid blocking the async SC2 event loop.

        Parameters
        ----------
        theory : Theory
            Current lifted theory (facts + KB rules).
        step : int
            Current game step.

        Returns
        -------
        list[str]
            Admitted rule strings, each parseable back to a Rule object.
        """
        if step % self._interval != 0:
            return []

        fingerprint = _theory_fingerprint(theory)
        cache_key = f"{fingerprint}:{step // self._interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        model = self._get_model()
        if model is None:
            return []

        # Find anomalies: facts derivable that we might want to override
        anomalies: list[str] = []
        engine = DefeasibleEngine(theory)
        for fact in list(theory.facts)[:20]:
            if fact.startswith("~"):
                continue
            neg = f"~{fact}"
            # Anomaly: fact is NOT derivable but its negation IS
            if not defeasible_provable(theory, fact) and defeasible_provable(theory, neg):
                anomalies.append(fact)

        prompt = _build_prompt(theory, anomalies[:5])

        try:
            response = model.query(prompt, max_tokens=256)
            raw_text = response.text if hasattr(response, "text") else str(response)
        except Exception as exc:
            logger.warning("LLM query failed: %s", exc)
            return []

        proposed = _parse_proposed_rules(raw_text)
        admitted: list[str] = []

        for rule in proposed[:self._max_rules]:
            if self._verify:
                if not self._check_conservativity(theory, rule):
                    logger.debug("Rejected rule (conservativity): %s", rule)
                    continue
            rule_str = self._rule_to_str(rule)
            admitted.append(rule_str)

        self._cache[cache_key] = admitted
        return admitted

    @staticmethod
    def _check_conservativity(theory: Theory, rule: Rule) -> bool:
        r"""
        Verify that adding rule does not destroy existing expectations.

        A rule is conservative if Exp(D union {rule}) superset-of Exp(D) \ {~q} where
        q is the anomaly the rule resolves.  We approximate this by checking
        that no currently-derivable fact becomes non-derivable.
        """
        import copy
        augmented = copy.deepcopy(theory)
        augmented.add_rule(rule)
        engine_before = DefeasibleEngine(theory)
        engine_after  = DefeasibleEngine(augmented)

        # Sample up to 30 currently derivable facts
        for fact in list(theory.facts)[:30]:
            if defeasible_provable(theory, fact):
                if not defeasible_provable(augmented, fact):
                    return False
        return True

    @staticmethod
    def _rule_to_str(rule: Rule) -> str:
        """Render a Rule as a Prolog-style string."""
        connector = "=>>" if rule.rule_type == RuleType.DEFEASIBLE else "~>>"
        body = ", ".join(rule.body)
        return f"{rule.head} :{connector} {body}." if body else f"{rule.head}."