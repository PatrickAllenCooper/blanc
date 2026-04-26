"""
MoveToMiddlePolicy: scripted policy that moves all units toward map center.

Unlike ScriptedPolicy (which idles), this policy sends every combat unit
to the map midpoint so that frames capture engagement_zone_alpha scenarios
where authorized_to_engage can actually fire (enemy units in transit
rather than inside the main base).

Author: Patrick Cooper
"""

from __future__ import annotations

from blanc.core.theory import Theory


class MoveToMiddlePolicy:
    """
    Scripted policy: walk every unit to the map center.

    No LLM required. Used in overnight E2 grounding runs to generate
    frames where allied and enemy units meet in the engagement zone
    (not just in main_base), enabling authorized_to_engage to fire.
    """

    name: str = "move_to_middle"

    def __init__(self, move_every_n_steps: int = 88) -> None:
        """
        Parameters
        ----------
        move_every_n_steps : int
            Re-issue move commands every N steps to ensure units keep moving.
        """
        self._move_every = move_every_n_steps
        self._center: object = None

    def propose_defeaters(self, theory: Theory, step: int) -> list[str]:
        """ScriptedPolicy-compatible interface: propose no defeater rules."""
        return []

    async def issue_orders(self, bot: object, step: int) -> None:
        """
        Issue move-to-center orders via python-sc2 BotAI.

        Called from an overriding DeFAbBot subclass (see run_overnight_e2.py).
        """
        if step % self._move_every != 0:
            return
        try:
            if self._center is None:
                gi = bot.game_info  # type: ignore[attr-defined]
                self._center = gi.map_center
            for unit in bot.units:  # type: ignore[attr-defined]
                unit.move(self._center)
        except AttributeError:
            pass
