"""
Tests for the debate agent framework, protocol, and resolution scoring.

Covers proposal generation, defense mechanism, full debate rounds on
a small knowledge base, challenge instance validity, and scoring.

Author: Patrick Cooper
"""

import pytest

from blanc.core.theory import Theory, Rule, RuleType
from blanc.debate.agent import (
    AgentProposal,
    DebateAgent,
    ProponentAgent,
    OpponentAgent,
)
from blanc.debate.protocol import (
    ChallengeInstance,
    DebateConfig,
    DebateProtocol,
    DebateResult,
    DebateRound,
    DefenseResult,
)
from blanc.debate.resolution import (
    DebateScores,
    creativity_score,
    debate_outcome,
    grounding_score,
    robustness_score,
)
from blanc.search.mcts import MCTSConfig
from blanc.reasoning.derivation_tree import (
    DerivationTree,
    DerivationNode,
    NodeType,
    tree_overlap,
    extract_support_path,
    get_critical_subtree,
    enumerate_permutations,
)
from blanc.reasoning.defeasible import DefeasibleEngine, defeasible_provable


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _tweety_theory() -> Theory:
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    ))
    return t


def _richer_theory() -> Theory:
    """Theory with multiple derivation paths and defeaters."""
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_fact("sparrow(tweety)")
    t.add_fact("bird(opus)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule(
        head="bird(X)",
        body=("sparrow(X)",),
        rule_type=RuleType.STRICT,
        label="r_sparrow",
    ))
    t.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r_flies",
    ))
    t.add_rule(Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d_penguin",
    ))
    t.add_superiority("d_penguin", "r_flies")
    return t


# ---------------------------------------------------------------------------
# Agent tests
# ---------------------------------------------------------------------------

class TestDebateAgent:
    def test_propose_statement_basic(self):
        theory = _tweety_theory()
        agent = DebateAgent(
            theory,
            MCTSConfig(max_iterations=100, seed=42),
        )
        proposal = agent.propose_statement(target="flies(tweety)")
        assert proposal.statement == "flies(tweety)"
        assert proposal.confidence > 0

    def test_propose_without_target(self):
        theory = _tweety_theory()
        agent = DebateAgent(
            theory,
            MCTSConfig(max_iterations=100, seed=42),
        )
        proposal = agent.propose_statement()
        assert proposal.statement != ""

    def test_defend_position_succeeds(self):
        theory = _tweety_theory()
        agent = DebateAgent(theory)
        from blanc.author.support import _remove_element
        d_minus = _remove_element(theory, "bird(tweety)")
        candidates = ["bird(tweety)", "fish(tweety)", "rock(tweety)"]
        result = agent.defend_position("flies(tweety)", candidates, d_minus)
        assert result == "bird(tweety)"

    def test_defend_position_fails(self):
        theory = _tweety_theory()
        agent = DebateAgent(theory)
        from blanc.author.support import _remove_element
        d_minus = _remove_element(theory, "bird(tweety)")
        candidates = ["fish(tweety)", "rock(tweety)"]
        result = agent.defend_position("flies(tweety)", candidates, d_minus)
        assert result is None


class TestProponentAgent:
    def test_proponent_has_correct_role(self):
        theory = _tweety_theory()
        agent = ProponentAgent(theory)
        assert agent.role == "proponent"

    def test_proponent_proposal(self):
        theory = _tweety_theory()
        agent = ProponentAgent(
            theory,
            MCTSConfig(max_iterations=100, seed=42),
        )
        proposal = agent.propose_statement(target="flies(tweety)")
        assert proposal.statement == "flies(tweety)"


class TestOpponentAgent:
    def test_opponent_has_correct_role(self):
        theory = _tweety_theory()
        agent = OpponentAgent(theory)
        assert agent.role == "opponent"

    def test_opponent_proposal(self):
        theory = _tweety_theory()
        agent = OpponentAgent(
            theory,
            MCTSConfig(max_iterations=100, seed=42),
        )
        proposal = agent.propose_statement()
        assert isinstance(proposal, AgentProposal)

    def test_opponent_with_opposing_target(self):
        theory = _tweety_theory()
        agent = OpponentAgent(
            theory,
            MCTSConfig(max_iterations=100, seed=42),
            opposing_target="flies(tweety)",
        )
        assert agent.opposing_target == "flies(tweety)"


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------

class TestDebateProtocol:
    def test_single_round(self):
        theory = _tweety_theory()
        config = DebateConfig(
            rounds=1,
            mcts_config=MCTSConfig(max_iterations=50, seed=42),
        )
        protocol = DebateProtocol(theory, config)
        result = protocol.run(target="flies(tweety)")
        assert len(result.rounds) == 1
        rnd = result.rounds[0]
        assert rnd.round_number == 0
        assert rnd.proponent_proposal.statement != ""

    def test_multiple_rounds(self):
        theory = _tweety_theory()
        config = DebateConfig(
            rounds=3,
            mcts_config=MCTSConfig(max_iterations=50, seed=42),
        )
        protocol = DebateProtocol(theory, config)
        result = protocol.run(target="flies(tweety)")
        assert len(result.rounds) == 3

    def test_defense_rate_properties(self):
        theory = _tweety_theory()
        config = DebateConfig(
            rounds=2,
            mcts_config=MCTSConfig(max_iterations=50, seed=42),
        )
        protocol = DebateProtocol(theory, config)
        result = protocol.run(target="flies(tweety)")
        assert 0.0 <= result.proponent_defense_rate <= 1.0
        assert 0.0 <= result.opponent_defense_rate <= 1.0

    def test_theory_size_recorded(self):
        theory = _tweety_theory()
        config = DebateConfig(
            rounds=1,
            mcts_config=MCTSConfig(max_iterations=50, seed=42),
        )
        protocol = DebateProtocol(theory, config)
        result = protocol.run()
        assert result.theory_size == len(theory)

    def test_richer_theory_debate(self):
        theory = _richer_theory()
        config = DebateConfig(
            rounds=2,
            mcts_config=MCTSConfig(max_iterations=80, seed=42),
        )
        protocol = DebateProtocol(theory, config)
        result = protocol.run(target="flies(tweety)")
        assert len(result.rounds) == 2


# ---------------------------------------------------------------------------
# Resolution scoring tests
# ---------------------------------------------------------------------------

class TestResolution:
    def _make_result(self, defenses):
        """Build a minimal DebateResult with supplied defense outcomes."""
        rounds = [
            DebateRound(
                round_number=0,
                proponent_proposal=AgentProposal(
                    statement="s", proof_tree=None,
                    confidence=1.0, derivation_path=[],
                ),
                opponent_proposal=AgentProposal(
                    statement="s", proof_tree=None,
                    confidence=0.5, derivation_path=[],
                ),
                defenses=defenses,
            )
        ]
        return DebateResult(
            rounds=rounds, config=DebateConfig()
        )

    def test_robustness_all_success(self):
        defenses = [
            DefenseResult("proponent", "s", "h", True),
            DefenseResult("proponent", "s", "h", True),
        ]
        result = self._make_result(defenses)
        assert robustness_score(result, "proponent") == 1.0

    def test_robustness_none_success(self):
        defenses = [
            DefenseResult("opponent", "s", None, False),
        ]
        result = self._make_result(defenses)
        assert robustness_score(result, "opponent") == 0.0

    def test_robustness_partial(self):
        defenses = [
            DefenseResult("proponent", "s", "h", True),
            DefenseResult("proponent", "s", None, False),
        ]
        result = self._make_result(defenses)
        assert robustness_score(result, "proponent") == pytest.approx(0.5)

    def test_grounding_all_grounded(self):
        result = self._make_result([])
        assert grounding_score(result, "proponent") == 1.0

    def test_grounding_ungrounded(self):
        rounds = [
            DebateRound(
                round_number=0,
                proponent_proposal=AgentProposal(
                    statement="", proof_tree=None,
                    confidence=0.0, derivation_path=[],
                ),
                opponent_proposal=AgentProposal(
                    statement="", proof_tree=None,
                    confidence=0.0, derivation_path=[],
                ),
                defenses=[],
            )
        ]
        result = DebateResult(rounds=rounds, config=DebateConfig())
        assert grounding_score(result, "proponent") == 0.0

    def test_debate_outcome_winner(self):
        defenses = [
            DefenseResult("proponent", "s", "h", True),
            DefenseResult("opponent", "s", None, False),
        ]
        result = self._make_result(defenses)
        scores = debate_outcome(result)
        assert isinstance(scores, DebateScores)
        assert scores.winner == "proponent"

    def test_debate_outcome_tie(self):
        defenses = []
        result = self._make_result(defenses)
        scores = debate_outcome(result)
        assert scores.winner is None or scores.margin == 0.0

    def test_creativity_no_defenses(self):
        result = self._make_result([])
        assert creativity_score(result, "proponent") == 0.0


# ---------------------------------------------------------------------------
# Derivation tree extension tests
# ---------------------------------------------------------------------------

class TestDerivationTreeExtensions:
    def _build_tree(self):
        leaf = DerivationNode("bird(tweety)", NodeType.FACT, tag="definite")
        root = DerivationNode(
            "flies(tweety)", NodeType.AND,
            rule=Rule(
                head="flies(X)", body=("bird(X)",),
                rule_type=RuleType.DEFEASIBLE, label="r1",
            ),
            children=[leaf],
            tag="defeasible",
        )
        return DerivationTree(root=root)

    def test_get_critical_subtree_found(self):
        tree = self._build_tree()
        sub = get_critical_subtree(tree, "bird(tweety)")
        assert sub is not None
        assert sub.root.literal == "bird(tweety)"

    def test_get_critical_subtree_not_found(self):
        tree = self._build_tree()
        sub = get_critical_subtree(tree, "swims(tweety)")
        assert sub is None

    def test_tree_overlap_identical(self):
        tree = self._build_tree()
        assert tree_overlap(tree, tree) == pytest.approx(1.0)

    def test_tree_overlap_disjoint(self):
        tree_a = self._build_tree()
        leaf_b = DerivationNode("fish(nemo)", NodeType.FACT, tag="definite")
        root_b = DerivationNode(
            "swims(nemo)", NodeType.AND,
            children=[leaf_b], tag="defeasible",
        )
        tree_b = DerivationTree(root=root_b)
        assert tree_overlap(tree_a, tree_b) == 0.0

    def test_extract_support_path(self):
        tree = self._build_tree()
        path = extract_support_path(tree)
        assert "bird(tweety)" in path
        assert "flies(tweety)" in path
        assert path.index("bird(tweety)") < path.index("flies(tweety)")

    def test_enumerate_permutations(self):
        theory = _tweety_theory()
        tree = self._build_tree()
        perms = enumerate_permutations(tree, theory, "flies(tweety)", k=3)
        assert len(perms) >= 1
        for elem, d_minus in perms:
            assert not defeasible_provable(d_minus, "flies(tweety)")
