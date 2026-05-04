"""
Scoring and resolution for defeasible debate.

Provides robustness, grounding, and creativity metrics that evaluate
how well agents defend their positions across debate rounds, plus
an aggregate ``debate_outcome`` that determines the winner.

Author: Anonymous Authors
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from blanc.debate.protocol import DebateResult, DebateRound


@dataclass
class DebateScores:
    """Per-agent aggregate scores for a completed debate."""

    proponent_robustness: float
    opponent_robustness: float
    proponent_grounding: float
    opponent_grounding: float
    proponent_creativity: float
    opponent_creativity: float
    winner: Optional[str]  # "proponent", "opponent", or None (tie)
    margin: float = 0.0


def robustness_score(result: DebateResult, role: str) -> float:
    """
    Fraction of challenges the agent successfully defended.

    Higher is better -- an agent that can always reconstruct its
    derivation after ablation is maximally robust.
    """
    total = 0
    wins = 0
    for rnd in result.rounds:
        for d in rnd.defenses:
            if d.agent_role == role:
                total += 1
                if d.success:
                    wins += 1
    return wins / max(1, total)


def grounding_score(result: DebateResult, role: str) -> float:
    """
    Proportion of an agent's proposals that trace to KB-derivable
    statements (confidence > 0).

    Measures how well the agent stays within the explicit knowledge
    of the theory rather than hallucinating unsupported claims.
    """
    proposals = _collect_proposals(result, role)
    if not proposals:
        return 0.0
    grounded = sum(1 for p in proposals if p.confidence > 0)
    return grounded / len(proposals)


def creativity_score(result: DebateResult, role: str) -> float:
    """
    Fraction of successful defenses that produced a novel hypothesis.

    A defense is *creative* when the selected hypothesis introduces
    predicates not present in the ablated theory (Nov > 0).  This
    mirrors Definition 14 from the paper.
    """
    from blanc.author.metrics import predicate_novelty
    from blanc.core.theory import Rule

    total_defenses = 0
    novel_defenses = 0

    for rnd in result.rounds:
        for d in rnd.defenses:
            if d.agent_role != role or not d.success:
                continue
            total_defenses += 1
            if d.challenge and d.challenge.instance:
                hyp = d.selected_hypothesis
                if hyp and d.challenge.instance.D_minus:
                    for g in d.challenge.instance.gold:
                        if isinstance(g, Rule):
                            nov = predicate_novelty(
                                g, d.challenge.instance.D_minus
                            )
                            if nov > 0:
                                novel_defenses += 1
                                break

    return novel_defenses / max(1, total_defenses)


def debate_outcome(result: DebateResult) -> DebateScores:
    """
    Compute aggregate scores for both agents and declare a winner.

    The winner is the agent with the higher weighted combination of
    robustness (0.5), grounding (0.3), and creativity (0.2).
    """
    p_rob = robustness_score(result, "proponent")
    o_rob = robustness_score(result, "opponent")
    p_gnd = grounding_score(result, "proponent")
    o_gnd = grounding_score(result, "opponent")
    p_cre = creativity_score(result, "proponent")
    o_cre = creativity_score(result, "opponent")

    p_total = 0.5 * p_rob + 0.3 * p_gnd + 0.2 * p_cre
    o_total = 0.5 * o_rob + 0.3 * o_gnd + 0.2 * o_cre

    margin = abs(p_total - o_total)
    if p_total > o_total:
        winner = "proponent"
    elif o_total > p_total:
        winner = "opponent"
    else:
        winner = None

    return DebateScores(
        proponent_robustness=round(p_rob, 4),
        opponent_robustness=round(o_rob, 4),
        proponent_grounding=round(p_gnd, 4),
        opponent_grounding=round(o_gnd, 4),
        proponent_creativity=round(p_cre, 4),
        opponent_creativity=round(o_cre, 4),
        winner=winner,
        margin=round(margin, 4),
    )


def _collect_proposals(result: DebateResult, role: str):
    proposals = []
    for rnd in result.rounds:
        if role == "proponent":
            proposals.append(rnd.proponent_proposal)
        elif role == "opponent":
            proposals.append(rnd.opponent_proposal)
    return proposals
