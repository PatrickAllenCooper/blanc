"""
blanc.sc2live -- Live StarCraft II bridge for DeFAb.

Provides three external surfaces:

    ObservationLifter   BotAI.state  ->  Theory (ground facts)
    ActionCompiler      derived literals  ->  async BotAI unit orders
    ReplayTraceExtractor  SC2Replay  ->  [(theory_state, observed_action)]

ROE compliance experiment surfaces:

    CommanderPolicy     LLM-as-commander with B0/B1/B2 enforcement modes
    Order               High-level battlefield order data class
    parse_orders        Tolerant LLM response -> list[Order] parser
    check_order         ROE compliance check for one Order -> ComplianceVerdict
    check_orders        Batch compliance check
    ComplianceVerdict   Verdict data class
    build_situation_report  Theory -> LLM commander brief string
    build_roe_system_prompt Fixed ROE system prompt string

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
from blanc.sc2live.orders_schema import Order, parse_orders
from blanc.sc2live.compliance import ComplianceVerdict, check_order, check_orders
from blanc.sc2live.situation_report import build_situation_report, build_roe_system_prompt
from blanc.sc2live.policies.commander import CommanderPolicy, EnforcementMode

__all__ = [
    # Original surfaces
    "ObservationLifter",
    "ActionCompiler",
    "ReplayTraceExtractor",
    "DeFAbBot",
    # ROE compliance experiment
    "CommanderPolicy",
    "EnforcementMode",
    "Order",
    "parse_orders",
    "ComplianceVerdict",
    "check_order",
    "check_orders",
    "build_situation_report",
    "build_roe_system_prompt",
]
