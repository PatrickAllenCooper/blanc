"""Coverage tests for debate/resolution.py.

Targets: grounding_score with empty proposals, creativity_score
with mixed success, debate_outcome tie.
"""

import pytest

from blanc.author.generation import AbductiveInstance
from blanc.core.theory import Rule, RuleType, Theory
from blanc.debate.agent import AgentProposal
from blanc.debate.protocol import (
    ChallengeInstance,
    DebateConfig,
    DebateResult,
    DebateRound,
    DefenseResult,
)
from blanc.debate.resolution import (
    creativity_score,
    debate_outcome,
    grounding_score,
    robustness_score,
)


def _make_proposal(statement="p(a)", confidence=0.9):
    return AgentProposal(
        statement=statement, proof_tree=None,
        confidence=confidence, derivation_path=[],
    )


def _make_defense(role, success, challenge=None, selected=None):
    return DefenseResult(
        agent_role=role, statement="p(a)",
        selected_hypothesis=selected, success=success,
        challenge=challenge,
    )


def _make_round(p_conf=0.9, o_conf=0.9, defenses=None):
    return DebateRound(
        round_number=1,
        proponent_proposal=_make_proposal(confidence=p_conf),
        opponent_proposal=_make_proposal(confidence=o_conf),
        defenses=defenses or [],
    )


class TestGroundingScore:
    def test_empty_proposals(self):
        result = DebateResult(
            rounds=[_make_round()],
            config=DebateConfig(),
        )
        # No proposals collected for a non-existent role
        score = grounding_score(result, "nonexistent_role")
        assert score == 0.0

    def test_all_grounded(self):
        result = DebateResult(
            rounds=[_make_round(p_conf=0.8)],
            config=DebateConfig(),
        )
        score = grounding_score(result, "proponent")
        assert score == 1.0

    def test_mixed_grounding(self):
        result = DebateResult(
            rounds=[
                _make_round(p_conf=0.9),
                _make_round(p_conf=0.0),
            ],
            config=DebateConfig(),
        )
        score = grounding_score(result, "proponent")
        assert 0.0 < score < 1.0


class TestCreativityScore:
    def test_no_successful_defenses(self):
        result = DebateResult(
            rounds=[_make_round(defenses=[
                _make_defense("proponent", success=False),
            ])],
            config=DebateConfig(),
        )
        assert creativity_score(result, "proponent") == 0.0

    def test_successful_defense_without_novelty(self):
        challenge = ChallengeInstance(
            agent_role="opponent", statement="p(a)",
            instance=AbductiveInstance(
                D_minus=Theory(), target="p(a)",
                candidates=["a"], gold=["a"], level=2,
            ),
        )
        result = DebateResult(
            rounds=[_make_round(defenses=[
                _make_defense("proponent", success=True,
                              challenge=challenge, selected="a"),
            ])],
            config=DebateConfig(),
        )
        score = creativity_score(result, "proponent")
        assert score == 0.0

    def test_successful_defense_with_novel_rule_gold(self):
        theory = Theory()
        theory.add_fact("bird(tweety)")
        gold_rule = Rule(
            head="novel_pred(X)", body=("bird(X)",),
            rule_type=RuleType.DEFEATER, label="novel",
        )
        challenge = ChallengeInstance(
            agent_role="opponent", statement="p(a)",
            instance=AbductiveInstance(
                D_minus=theory, target="p(a)",
                candidates=[gold_rule], gold=[gold_rule], level=3,
            ),
        )
        result = DebateResult(
            rounds=[_make_round(defenses=[
                _make_defense("proponent", success=True,
                              challenge=challenge, selected="novel_pred(X)"),
            ])],
            config=DebateConfig(),
        )
        score = creativity_score(result, "proponent")
        assert score > 0.0


class TestDebateOutcome:
    def test_proponent_wins(self):
        result = DebateResult(
            rounds=[_make_round(
                p_conf=1.0, o_conf=0.0,
                defenses=[
                    _make_defense("proponent", success=True),
                    _make_defense("opponent", success=False),
                ],
            )],
            config=DebateConfig(),
        )
        scores = debate_outcome(result)
        assert scores.winner == "proponent"

    def test_opponent_wins(self):
        result = DebateResult(
            rounds=[_make_round(
                p_conf=0.0, o_conf=1.0,
                defenses=[
                    _make_defense("proponent", success=False),
                    _make_defense("opponent", success=True),
                ],
            )],
            config=DebateConfig(),
        )
        scores = debate_outcome(result)
        assert scores.winner == "opponent"

    def test_tie(self):
        result = DebateResult(
            rounds=[_make_round(
                p_conf=0.5, o_conf=0.5,
                defenses=[
                    _make_defense("proponent", success=True),
                    _make_defense("opponent", success=True),
                ],
            )],
            config=DebateConfig(),
        )
        scores = debate_outcome(result)
        assert scores.winner is None
        assert scores.margin == 0.0
