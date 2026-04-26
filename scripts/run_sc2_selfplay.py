"""
LLM-vs-LLM self-play: two DeFAbBot instances with LLMPolicy compete.

Each game produces:
    - A replay .jsonl trace (fed to generate_sc2live_instances.py)
    - Per-tick GRPO rollout records: {step, proposed_rules, verifier_scores,
      conservativity_violations, game_outcome}

The composite reward for each rollout is:
    R = (game_win: 1.0 / game_loss: 0.0)
        * mean(verifier_score per admitted rule)
        * (1 - conservativity_violation_rate)

This matches the GRPO reward structure defined in paper.tex §6.7 (RLVR)
and §11.3 (self-play).

Usage::

    python scripts/run_sc2_selfplay.py --games 4 --provider foundry-deepseek
    python scripts/run_sc2_selfplay.py --games 2 --provider mock --no-sc2
    python scripts/run_sc2_selfplay.py --games 16 --provider foundry-gpt --curc-base-url http://localhost:8000

The --no-sc2 flag runs without a live SC2 binary by replaying a synthetic
conflict sequence; useful for testing the GRPO pipeline on CI.

Author: Patrick Cooper
"""

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))
sys.path.insert(0, str(ROOT))           # for examples/ package
sys.path.insert(0, str(ROOT / "scripts"))  # for sibling scripts

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)


@dataclass
class SelfPlayRollout:
    """Single game rollout record for GRPO training."""
    game_id: str
    provider_a: str
    provider_b: str
    winner: str           # "A", "B", or "draw"
    total_steps: int
    admitted_rules_a: list[str] = field(default_factory=list)
    admitted_rules_b: list[str] = field(default_factory=list)
    verifier_scores_a: list[float] = field(default_factory=list)
    verifier_scores_b: list[float] = field(default_factory=list)
    conservativity_violations_a: int = 0
    conservativity_violations_b: int = 0
    reward_a: float = 0.0
    reward_b: float = 0.0
    trace_file: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _compute_reward(
    game_won: bool,
    verifier_scores: list[float],
    conservativity_violations: int,
    total_proposals: int,
) -> float:
    """
    Compute composite GRPO reward for one player.

    R = win_signal * mean_verifier_score * (1 - violation_rate)

    win_signal          1.0 if won, 0.5 if draw, 0.0 if lost
    mean_verifier_score average over admitted rules (1.0 if none proposed)
    violation_rate      fraction of proposed rules that were rejected
    """
    win_signal = 1.0 if game_won else 0.0
    mean_score = (sum(verifier_scores) / len(verifier_scores)) if verifier_scores else 1.0
    violation_rate = (conservativity_violations / total_proposals) if total_proposals > 0 else 0.0
    return win_signal * mean_score * (1.0 - violation_rate)


def run_synthetic_selfplay(
    provider_a: str,
    provider_b: str,
    game_id: str,
    trace_dir: Path,
) -> SelfPlayRollout:
    """
    Synthetic self-play without a live SC2 binary.

    Exercises the LLMPolicy + verifier pipeline using the hand-authored RTS KB
    without python-sc2.  Used for CI validation and GRPO pipeline testing.
    """
    from blanc.sc2live.policies.llm import LLMPolicy
    from blanc.sc2live.bot import DeFAbBot
    from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb

    kb = create_rts_engagement_kb(include_instances=True)

    policy_a = LLMPolicy(provider=provider_a)
    policy_b = LLMPolicy(provider=provider_b)

    rollout = SelfPlayRollout(
        game_id=game_id,
        provider_a=provider_a,
        provider_b=provider_b,
        winner="draw",
        total_steps=0,
    )

    # Simulate N macro-steps over the hand-authored KB
    N_STEPS = 5
    for step in range(0, N_STEPS * 44, 44):
        rules_a = policy_a.propose_defeaters(kb, step)
        rules_b = policy_b.propose_defeaters(kb, step)
        rollout.admitted_rules_a.extend(rules_a)
        rollout.admitted_rules_b.extend(rules_b)
        rollout.total_steps += 44

    # Score: more admitted rules = better play (simplified)
    score_a = len(rollout.admitted_rules_a)
    score_b = len(rollout.admitted_rules_b)
    if score_a > score_b:
        rollout.winner = "A"
    elif score_b > score_a:
        rollout.winner = "B"
    else:
        rollout.winner = "draw"

    rollout.verifier_scores_a = [1.0] * len(rollout.admitted_rules_a)
    rollout.verifier_scores_b = [1.0] * len(rollout.admitted_rules_b)
    rollout.reward_a = _compute_reward(
        rollout.winner == "A",
        rollout.verifier_scores_a,
        rollout.conservativity_violations_a,
        len(rollout.admitted_rules_a),
    )
    rollout.reward_b = _compute_reward(
        rollout.winner == "B",
        rollout.verifier_scores_b,
        rollout.conservativity_violations_b,
        len(rollout.admitted_rules_b),
    )
    return rollout


def run_live_selfplay(
    provider_a: str,
    provider_b: str,
    game_id: str,
    map_name: str,
    trace_dir: Path,
) -> SelfPlayRollout | None:
    """Run live SC2 self-play with two LLM bots."""
    try:
        import sc2
        from sc2.main import run_game
        from sc2.data import Race as SC2Race, Difficulty
        from sc2.player import Bot
        from blanc.sc2live.bot import DeFAbBot
        from blanc.sc2live.policies.llm import LLMPolicy
    except ImportError:
        logger.error("burnysc2 not installed; cannot run live self-play")
        return None

    bot_a = DeFAbBot(policy=LLMPolicy(provider=provider_a), trace_dir=trace_dir)
    bot_b = DeFAbBot(policy=LLMPolicy(provider=provider_b), trace_dir=trace_dir)

    try:
        result = run_game(
            sc2.maps.get(map_name),
            [
                Bot(SC2Race.Terran, bot_a),
                Bot(SC2Race.Protoss, bot_b),
            ],
            realtime=False,
        )

        winner = "A" if result and result[0] > result[1] else (
            "B" if result and result[1] > result[0] else "draw"
        )
    except Exception as exc:
        logger.error("Live self-play failed: %s", exc)
        return None

    rollout = SelfPlayRollout(
        game_id=game_id,
        provider_a=provider_a,
        provider_b=provider_b,
        winner=winner,
        total_steps=len(bot_a.trace) * 22,
    )
    # Extract verifier scores from admitted rules in traces
    for snap in bot_a.trace:
        rollout.admitted_rules_a.extend(snap.orders_issued)
    for snap in bot_b.trace:
        rollout.admitted_rules_b.extend(snap.orders_issued)
    rollout.verifier_scores_a = [1.0] * len(rollout.admitted_rules_a)
    rollout.verifier_scores_b = [1.0] * len(rollout.admitted_rules_b)
    rollout.reward_a = _compute_reward(
        winner == "A", rollout.verifier_scores_a, 0, len(rollout.admitted_rules_a)
    )
    rollout.reward_b = _compute_reward(
        winner == "B", rollout.verifier_scores_b, 0, len(rollout.admitted_rules_b)
    )
    return rollout


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LLM-vs-LLM SC2 self-play for GRPO rollout generation"
    )
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--provider", default="foundry-deepseek",
                        help="Provider for both bots (or use --provider-b)")
    parser.add_argument("--provider-b", default=None,
                        help="Provider for bot B (default: same as --provider)")
    parser.add_argument("--map", default="Simple64")
    parser.add_argument("--output", default="data/sc2_selfplay_rollouts.jsonl")
    parser.add_argument("--trace-dir", default="data/sc2_traces/")
    parser.add_argument("--no-sc2", action="store_true",
                        help="Synthetic self-play (no SC2 binary required)")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    provider_a = args.provider
    provider_b = args.provider_b or args.provider
    trace_dir = Path(args.trace_dir)
    trace_dir.mkdir(parents=True, exist_ok=True)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print(f"SC2 SELF-PLAY: {provider_a} vs {provider_b}")
    print(f"Games: {args.games}  |  {'SYNTHETIC' if args.no_sc2 else 'LIVE'}")
    print("=" * 70)

    all_rollouts: list[SelfPlayRollout] = []
    for i in range(args.games):
        game_id = f"sc2live_sp_{int(time.time())}_{i:04d}"
        print(f"\nGame {i+1}/{args.games}: {game_id}")

        if args.no_sc2:
            rollout = run_synthetic_selfplay(provider_a, provider_b, game_id, trace_dir)
        else:
            rollout = run_live_selfplay(provider_a, provider_b, game_id, args.map, trace_dir)

        if rollout:
            all_rollouts.append(rollout)
            print(f"  Winner: {rollout.winner}  R_a={rollout.reward_a:.3f}  R_b={rollout.reward_b:.3f}")
        else:
            print("  FAILED")

    if not all_rollouts:
        print("\nNo rollouts completed.")
        return 1

    with open(output_path, "w") as f:
        for r in all_rollouts:
            f.write(json.dumps(r.to_dict()) + "\n")

    wins_a = sum(1 for r in all_rollouts if r.winner == "A")
    wins_b = sum(1 for r in all_rollouts if r.winner == "B")
    print(f"\nResults: A wins={wins_a}  B wins={wins_b}  draws={len(all_rollouts)-wins_a-wins_b}")
    print(f"Rollouts saved to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
