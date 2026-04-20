"""
ScriptedPolicy: rule-derivation-only baseline (no LLM).

The scripted policy does not add any defeasible rules beyond the hand-authored
RTS engagement KB.  Every tick it simply returns the unmodified theory.

This is the baseline for E1 (plumbing certification): it verifies that the
lift -> derive -> compile cycle produces correct results before any LLM is
introduced.

Author: Patrick Cooper
"""

from __future__ import annotations

from blanc.core.theory import Theory


class ScriptedPolicy:
    """
    Trivial policy: return the theory as-is, add no defeaters.

    Used in E1 plumbing tests and as the control arm in E3/E4.
    """

    name: str = "scripted"

    def propose_defeaters(self, theory: Theory, step: int) -> list[str]:
        """
        Return a list of additional defeasible rules (Prolog-style strings)
        to add to the current theory for this tick.

        ScriptedPolicy always returns [] -- no LLM, pure rule engine.

        Parameters
        ----------
        theory : Theory
            Current theory (ground facts + KB rules).
        step : int
            Current game step number.

        Returns
        -------
        list[str]
            Zero or more rule strings in the form
            ``"head :- body1, body2."``
        """
        return []
