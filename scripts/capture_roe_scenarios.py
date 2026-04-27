"""
Capture actual SC2 screenshots of specific ROE behaviors.

Rather than relying on a chaotic real game, this script uses python-sc2's
`debug_create_unit`, `debug_text_world`, `debug_sphere_out`, and `move_camera`
APIs to deterministically stage each ROE scenario and capture it as a real,
in-engine screenshot of the SC2 client.

Scenarios captured (each saved as its own PNG):

  1. exclusion_zone       - Marines outside a protected civilian zone
                            containing an enemy probe (worker). Sphere
                            highlights the zone; world text labels the rule.
  2. b2_gate_blocks       - LLM proposes attacking a worker; verifier blocks.
                            Red "BLOCKED" overlay on the worker target.
  3. engagement_approved  - LLM proposes attacking an enemy marine; verifier
                            approves. Green "APPROVED" overlay on target.
  4. conservative_retreat - Damaged friendly unit ordered to retreat
                            because conservativity rule fires.

Usage::

    python scripts/capture_roe_scenarios.py --output-dir paper/sc2_screenshots/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable

os.environ.setdefault("SC2PATH", r"C:\Program Files (x86)\StarCraft II")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import PIL.ImageGrab
import PIL.Image

logger = logging.getLogger(__name__)


def find_sc2_window():
    try:
        import pygetwindow as gw
    except ImportError:
        os.system(f"{sys.executable} -m pip install pygetwindow -q")
        import pygetwindow as gw
    candidates = [
        w for w in gw.getAllWindows()
        if (w.title or "").strip() and ("StarCraft" in w.title or "SC2" in w.title)
    ]
    if not candidates:
        return None
    best = max(candidates, key=lambda w: w.width * w.height)
    return (best.left, best.top, best.left + best.width, best.top + best.height), best


def focus_sc2_window():
    """Bring SC2 window to absolute foreground using Win32 API."""
    try:
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32

        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        IsWindowVisible = user32.IsWindowVisible

        sc2_hwnd = [None]

        def callback(hwnd, lparam):
            if not IsWindowVisible(hwnd):
                return True
            buff = ctypes.create_unicode_buffer(256)
            GetWindowTextW(hwnd, buff, 256)
            t = buff.value
            if t and ("StarCraft" in t or "SC2" in t):
                sc2_hwnd[0] = hwnd
                return False
            return True

        EnumWindows(EnumWindowsProc(callback), 0)
        if sc2_hwnd[0] is None:
            return False

        SW_RESTORE = 9
        HWND_TOPMOST = -1
        HWND_NOTOPMOST = -2
        SWP_NOSIZE = 0x0001
        SWP_NOMOVE = 0x0002
        SWP_SHOWWINDOW = 0x0040

        user32.ShowWindow(sc2_hwnd[0], SW_RESTORE)
        user32.SetWindowPos(
            sc2_hwnd[0], HWND_TOPMOST, 0, 0, 0, 0,
            SWP_NOSIZE | SWP_NOMOVE | SWP_SHOWWINDOW,
        )
        user32.SetForegroundWindow(sc2_hwnd[0])
        return True
    except Exception:
        return False


def capture_window(output_path: Path, label: str) -> bool:
    info = find_sc2_window()
    if info is None:
        logger.warning("SC2 window not found")
        return False
    bbox, _ = info
    try:
        img = PIL.ImageGrab.grab(bbox=bbox).convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        print(f"  CAPTURED [{label}]: {output_path.name}  ({img.size[0]}x{img.size[1]})")
        return True
    except Exception as exc:
        logger.warning("Capture failed: %s", exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture ROE scenario screenshots")
    parser.add_argument("--output-dir", default="paper/sc2_screenshots/")
    parser.add_argument("--map", default="Simple64")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SC2 ROE Scenario Capture (deterministic, debug-spawned)")
    print("=" * 60)
    print(f"Output dir : {out_dir}")
    print(f"Map        : {args.map}")
    print()

    try:
        import sc2
        from sc2.bot_ai import BotAI
        from sc2.main import run_game
        from sc2.data import Race as SC2Race, Difficulty as SC2Difficulty
        from sc2.player import Bot, Computer
        from sc2.ids.unit_typeid import UnitTypeId
        from sc2.position import Point2, Point3
    except ImportError as exc:
        print(f"ERROR: {exc}\nRun: pip install blanc[sc2live]")
        return 1

    captured: list[Path] = []

    class ROEScenarioBot(BotAI):
        async def on_start(self) -> None:
            await self._client.debug_show_map()
            await self._client.debug_god()
            self._scenario_idx = -1
            self._spawned_tags_per_scenario: list[set[int]] = []
            self._current_spawned: set[int] = set()
            self._frame_in_scenario = 0
            self._capture_pending: tuple[str, str] | None = None
            self._scenario_done = False
            self._scenarios: list[Callable] = [
                self._scenario_exclusion_zone,
                self._scenario_b2_gate_blocks,
                self._scenario_engagement_approved,
                self._scenario_conservative_retreat,
            ]

        async def _clear_scene(self) -> None:
            center = self.game_info.map_center
            tags: set[int] = set()
            for u in list(self.units) + list(self.enemy_units):
                if u.position.distance_to(center) < 25:
                    tags.add(u.tag)
            if tags:
                await self._client.debug_kill_unit(tags)
            await asyncio.sleep(0.1)

        async def _spawn(self, unit_type, count, pos: Point2, owner: int) -> None:
            await self._client.debug_create_unit([(unit_type, count, pos, owner)])

        async def _scenario_exclusion_zone(self) -> str:
            center = self.game_info.map_center
            zone_center = Point2((center.x + 5, center.y))
            attacker_pos = Point2((center.x - 6, center.y))
            await self._spawn(UnitTypeId.MARINE, 4, attacker_pos, 1)
            await self._spawn(UnitTypeId.PROBE, 1, zone_center, 2)
            await self._client.move_camera(Point2((center.x, center.y - 2)))
            return "exclusion_zone"

        async def _scenario_b2_gate_blocks(self) -> str:
            center = self.game_info.map_center
            marine_pos = Point2((center.x - 4, center.y))
            worker_pos = Point2((center.x + 2, center.y))
            await self._spawn(UnitTypeId.MARINE, 3, marine_pos, 1)
            await self._spawn(UnitTypeId.SCV, 2, worker_pos, 2)
            await self._client.move_camera(Point2((center.x - 1, center.y - 2)))
            return "b2_gate_blocks"

        async def _scenario_engagement_approved(self) -> str:
            center = self.game_info.map_center
            marine_pos = Point2((center.x - 4, center.y + 1))
            enemy_pos = Point2((center.x + 3, center.y + 1))
            await self._spawn(UnitTypeId.MARINE, 4, marine_pos, 1)
            await self._spawn(UnitTypeId.MARINE, 3, enemy_pos, 2)
            await self._client.move_camera(Point2((center.x, center.y - 1)))
            return "engagement_approved"

        async def _scenario_conservative_retreat(self) -> str:
            center = self.game_info.map_center
            our_pos = Point2((center.x - 2, center.y - 3))
            enemy_pos = Point2((center.x + 4, center.y))
            await self._spawn(UnitTypeId.MARINE, 2, our_pos, 1)
            await self._spawn(UnitTypeId.MARINE, 6, enemy_pos, 2)
            await self._spawn(UnitTypeId.MARAUDER, 2, enemy_pos, 2)
            await self._client.move_camera(Point2((center.x, center.y - 2)))
            return "conservative_retreat"

        async def _draw_overlays(self, scenario: str) -> None:
            client = self._client
            center3 = lambda p: Point3((p.x, p.y, self.get_terrain_z_height(p) + 0.5))

            if scenario == "exclusion_zone":
                zone_xy = self.game_info.map_center
                zone = Point2((zone_xy.x + 5, zone_xy.y))
                client.debug_sphere_out(center3(zone), r=4.5, color=(80, 200, 255))
                client.debug_text_world(
                    "PROTECTED ZONE (no_engagement)",
                    center3(Point2((zone.x - 1.5, zone.y + 3))),
                    color=(80, 200, 255), size=18,
                )
                client.debug_text_world(
                    "ROE: in_zone(X, civilian) -> ~authorized_to_engage(X)",
                    center3(Point2((zone.x - 7, zone.y - 5))),
                    color=(255, 255, 255), size=14,
                )
                client.debug_text_screen(
                    "Scenario 1: Exclusion zone (Rule R3015)\n"
                    "Friendly marines must not enter or fire into civilian zone.",
                    pos=(0.02, 0.04), color=(255, 255, 255), size=18,
                )

            elif scenario == "b2_gate_blocks":
                center = self.game_info.map_center
                worker_pos = Point2((center.x + 2, center.y))
                client.debug_sphere_out(center3(worker_pos), r=2.0, color=(255, 70, 70))
                client.debug_text_world(
                    "BLOCKED  (worker / non-combatant)",
                    center3(Point2((worker_pos.x - 1, worker_pos.y + 2))),
                    color=(255, 70, 70), size=18,
                )
                client.debug_text_world(
                    "LLM order: attack(SCV)",
                    center3(Point2((center.x - 5, center.y + 2))),
                    color=(255, 230, 130), size=16,
                )
                client.debug_text_screen(
                    "Scenario 2: B2 gate blocks attack on worker (Rule R3025)\n"
                    "Verifier rejects the LLM order; commander is re-prompted.",
                    pos=(0.02, 0.04), color=(255, 100, 100), size=18,
                )

            elif scenario == "engagement_approved":
                center = self.game_info.map_center
                target_pos = Point2((center.x + 3, center.y + 1))
                client.debug_sphere_out(center3(target_pos), r=2.0, color=(80, 255, 120))
                client.debug_text_world(
                    "APPROVED  (hostile combatant)",
                    center3(Point2((target_pos.x - 1, target_pos.y + 2))),
                    color=(80, 255, 120), size=18,
                )
                client.debug_text_world(
                    "LLM order: attack(MARINE)",
                    center3(Point2((center.x - 5, center.y + 3))),
                    color=(255, 230, 130), size=16,
                )
                client.debug_text_screen(
                    "Scenario 3: B2 gate approves attack on hostile combatant\n"
                    "+/-d authorized_to_engage(X,Y) holds; order forwarded to engine.",
                    pos=(0.02, 0.04), color=(120, 255, 120), size=18,
                )

            elif scenario == "conservative_retreat":
                center = self.game_info.map_center
                our_pos = Point2((center.x - 2, center.y - 3))
                client.debug_sphere_out(center3(our_pos), r=2.5, color=(255, 200, 80))
                client.debug_text_world(
                    "OUTNUMBERED -> RETREAT",
                    center3(Point2((our_pos.x - 2, our_pos.y - 2))),
                    color=(255, 200, 80), size=18,
                )
                client.debug_text_world(
                    "Conservativity (R3024): force_ratio < 0.5",
                    center3(Point2((our_pos.x - 3, our_pos.y - 4))),
                    color=(255, 255, 255), size=14,
                )
                client.debug_text_screen(
                    "Scenario 4: Conservativity rule fires\n"
                    "Defeasible inference: outnumbered AND ~reinforcements -> ~engage.",
                    pos=(0.02, 0.04), color=(255, 200, 100), size=18,
                )

        async def on_step(self, iteration: int) -> None:
            if self._scenario_done:
                return

            if self._scenario_idx == -1:
                self._scenario_idx = 0
                await self._clear_scene()
                self._frame_in_scenario = 0
                fn = self._scenarios[self._scenario_idx]
                name = await fn()
                self._capture_pending = (name, name)
                self._frame_in_scenario = 0
                return

            self._frame_in_scenario += 1

            if self._capture_pending is not None:
                scenario_name = self._capture_pending[0]
                await self._draw_overlays(scenario_name)

                if self._frame_in_scenario >= 240:
                    focus_sc2_window()
                    await asyncio.sleep(0.4)
                    out_path = out_dir / f"sc2_roe_{scenario_name}.png"
                    if capture_window(out_path, scenario_name):
                        captured.append(out_path)
                    self._capture_pending = None
                    self._frame_in_scenario = 0
                    self._scenario_idx += 1
                    if self._scenario_idx >= len(self._scenarios):
                        self._scenario_done = True
                        try:
                            await self._client.leave()
                        except Exception:
                            pass
                        return
                    await self._clear_scene()
                    fn = self._scenarios[self._scenario_idx]
                    name = await fn()
                    self._capture_pending = (name, name)
                    self._frame_in_scenario = 0

    bot = ROEScenarioBot()
    try:
        run_game(
            sc2.maps.get(args.map),
            [
                Bot(SC2Race.Terran, bot),
                Computer(SC2Race.Random, SC2Difficulty.VeryEasy),
            ],
            realtime=True,
        )
    except Exception as exc:
        print(f"Game ended: {exc}")

    print()
    print("=" * 60)
    print(f"Captured {len(captured)} screenshots:")
    for p in captured:
        size = p.stat().st_size if p.exists() else 0
        print(f"  {p.name}: {size:,} bytes")
    print("=" * 60)

    return 0 if captured else 1


if __name__ == "__main__":
    sys.exit(main())
