"""
blanc.sc2live -- Live StarCraft II bridge for DeFAb.

Provides three external surfaces:

    ObservationLifter   BotAI.state  ->  Theory (ground facts)
    ActionCompiler      derived literals  ->  async BotAI unit orders
    ReplayTraceExtractor  SC2Replay  ->  [(theory_state, observed_action)]

The polynomial-time DefeasibleEngine (blanc.reasoning.defeasible) is the
fixed point: every bit of live game state that enters DeFAb is expressed as
a Theory so that the existing verifier scores it without modification.

Requires: pip install blanc[sc2live]  (adds burnysc2>=7.0)

Author: Patrick Cooper
"""

from blanc.sc2live.observation import ObservationLifter
from blanc.sc2live.orders import ActionCompiler
from blanc.sc2live.replay import ReplayTraceExtractor
from blanc.sc2live.bot import DeFAbBot

__all__ = [
    "ObservationLifter",
    "ActionCompiler",
    "ReplayTraceExtractor",
    "DeFAbBot",
]
