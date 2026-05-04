"""
Debate protocol orchestrating competitive MCTS agents.

Four phases per round:
  1. Proposal  -- both agents independently run MCTS on the shared KB.
  2. Challenge -- the author algorithm permutes each agent's proof tree
                  by ablating critical elements, creating AbductiveInstances.
  3. Defense   -- each agent selects a hypothesis from the ablated instance
                  to restore their derivation.
  4. Resolution-- compare defense quality to score the round.

Author: Anonymous Authors
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from blanc.core.theory import Theory, Rule, RuleType
from blanc.debate.agent import (
    AgentProposal,
    DebateAgent,
    OpponentAgent,
    ProponentAgent,
)
from blanc.author.generation import AbductiveInstance
from blanc.search.mcts import MCTSConfig


@dataclass
class DebateConfig:
    """Parameters governing a debate."""

    rounds: int = 3
    mcts_config: Optional[MCTSConfig] = None
    permutation_depth: int = 1
    distractor_count: int = 5
    distractor_strategy: str = "syntactic"


@dataclass
class ChallengeInstance:
    """An ablated challenge derived from an agent's proof tree."""

    agent_role: str
    statement: str
    instance: Optional[AbductiveInstance]
    ablated_element: Optional[Any] = None


@dataclass
class DefenseResult:
    """Outcome of an agent defending against a challenge."""

    agent_role: str
    statement: str
    selected_hypothesis: Optional[str]
    success: bool
    challenge: Optional[ChallengeInstance] = None


@dataclass
class DebateRound:
    """Complete record of a single debate round."""

    round_number: int
    proponent_proposal: AgentProposal
    opponent_proposal: AgentProposal
    challenges: List[ChallengeInstance] = field(default_factory=list)
    defenses: List[DefenseResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DebateResult:
    """Full debate record across all rounds."""

    rounds: List[DebateRound]
    config: DebateConfig
    theory_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def proponent_defense_rate(self) -> float:
        total = sum(
            1 for r in self.rounds for d in r.defenses
            if d.agent_role == "proponent"
        )
        wins = sum(
            1 for r in self.rounds for d in r.defenses
            if d.agent_role == "proponent" and d.success
        )
        return wins / max(1, total)

    @property
    def opponent_defense_rate(self) -> float:
        total = sum(
            1 for r in self.rounds for d in r.defenses
            if d.agent_role == "opponent"
        )
        wins = sum(
            1 for r in self.rounds for d in r.defenses
            if d.agent_role == "opponent" and d.success
        )
        return wins / max(1, total)


class DebateProtocol:
    """
    Orchestrates a multi-round debate between a proponent and an opponent.

    Each round:
      1. Both agents propose a statement via MCTS.
      2. The author algorithm creates challenges by ablating critical
         elements from each agent's proof tree.
      3. Each agent defends against the challenges to the other's claim.
      4. Defenses are scored.
    """

    def __init__(
        self,
        theory: Theory,
        config: Optional[DebateConfig] = None,
    ):
        self.theory = theory
        self.config = config or DebateConfig()
        mcts_cfg = self.config.mcts_config or MCTSConfig()
        self.proponent = ProponentAgent(theory, mcts_cfg)
        self.opponent = OpponentAgent(theory, mcts_cfg)

    def run(
        self,
        target: Optional[str] = None,
    ) -> DebateResult:
        rounds: List[DebateRound] = []

        for i in range(self.config.rounds):
            rnd = self._run_round(i, target)
            rounds.append(rnd)

            if target and rnd.proponent_proposal.statement == target:
                opposing = self.opponent.opposing_target
                if opposing is None:
                    self.opponent.opposing_target = target

        return DebateResult(
            rounds=rounds,
            config=self.config,
            theory_size=len(self.theory),
        )

    def _run_round(
        self,
        round_idx: int,
        target: Optional[str],
    ) -> DebateRound:
        prop_proposal = self.proponent.propose_statement(target)
        opp_proposal = self.opponent.propose_statement(target)

        challenges = self._generate_challenges(
            prop_proposal, opp_proposal
        )

        defenses = self._run_defenses(
            challenges, prop_proposal, opp_proposal
        )

        return DebateRound(
            round_number=round_idx,
            proponent_proposal=prop_proposal,
            opponent_proposal=opp_proposal,
            challenges=challenges,
            defenses=defenses,
        )

    def _generate_challenges(
        self,
        prop_proposal: AgentProposal,
        opp_proposal: AgentProposal,
    ) -> List[ChallengeInstance]:
        challenges: List[ChallengeInstance] = []

        for role, proposal in [
            ("proponent", prop_proposal),
            ("opponent", opp_proposal),
        ]:
            if not proposal.statement:
                continue
            inst = self._ablate_proof(proposal)
            if inst is not None:
                challenges.append(inst)

        return challenges

    def _ablate_proof(
        self, proposal: AgentProposal
    ) -> Optional[ChallengeInstance]:
        """
        Use the author algorithm to ablate a critical element from
        the proposal's proof tree, producing a Level-2 challenge.
        """
        from blanc.author.support import full_theory_criticality
        from blanc.author.generation import _add_element
        from blanc.reasoning.defeasible import defeasible_provable

        statement = proposal.statement
        if not statement:
            return None

        if not defeasible_provable(self.theory, statement):
            return None

        try:
            critical = full_theory_criticality(self.theory, statement)
        except ValueError:
            return None

        if not critical:
            return None

        ablated_element = critical[0]

        from blanc.author.support import _remove_element
        from blanc.generation.distractor import (
            sample_fact_distractors,
            sample_rule_distractors,
        )

        d_minus = _remove_element(self.theory, ablated_element)

        if isinstance(ablated_element, str):
            try:
                distractors = sample_fact_distractors(
                    target_fact=ablated_element,
                    theory=self.theory,
                    k=self.config.distractor_count,
                    strategy=self.config.distractor_strategy,
                )
            except Exception:
                distractors = []
            gold = [ablated_element]
        elif isinstance(ablated_element, Rule):
            try:
                distractors = sample_rule_distractors(
                    target_rule=ablated_element,
                    theory=self.theory,
                    k=self.config.distractor_count,
                    strategy=self.config.distractor_strategy,
                )
            except Exception:
                distractors = []
            gold = [ablated_element]
        else:
            return None

        candidates = gold + distractors
        instance = AbductiveInstance(
            D_minus=d_minus,
            target=statement,
            candidates=candidates,
            gold=gold,
            level=2,
            metadata={
                "ablated_element": (
                    ablated_element
                    if isinstance(ablated_element, str)
                    else ablated_element.label or str(ablated_element)
                ),
                "source": "debate_challenge",
            },
        )

        return ChallengeInstance(
            agent_role=proposal.proof_tree.root.tag
            if proposal.proof_tree
            else "unknown",
            statement=statement,
            instance=instance,
            ablated_element=ablated_element,
        )

    def _run_defenses(
        self,
        challenges: List[ChallengeInstance],
        prop_proposal: AgentProposal,
        opp_proposal: AgentProposal,
    ) -> List[DefenseResult]:
        defenses: List[DefenseResult] = []

        for challenge in challenges:
            if challenge.instance is None:
                continue

            if challenge.statement == prop_proposal.statement:
                defender = self.opponent
                defender_role = "opponent"
            else:
                defender = self.proponent
                defender_role = "proponent"

            selected = defender.defend_position(
                challenge.statement,
                challenge.instance.candidates,
                challenge.instance.D_minus,
            )

            gold_strs = {
                g if isinstance(g, str) else str(g)
                for g in challenge.instance.gold
            }
            success = selected is not None and selected in gold_strs

            defenses.append(
                DefenseResult(
                    agent_role=defender_role,
                    statement=challenge.statement,
                    selected_hypothesis=selected,
                    success=success,
                    challenge=challenge,
                )
            )

        return defenses
