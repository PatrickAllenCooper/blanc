"""
Capture actual SC2 game screenshots during a live game.

Uses pygetwindow to find the SC2 window and PIL.ImageGrab to capture it
specifically (rather than the whole desktop). Saves screenshots at key
moments: game start, when units appear, and when the bot makes engagement decisions.

Usage::

    python scripts/capture_live_sc2_screenshots.py --output paper/

Author: Anonymous Authors
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

os.environ.setdefault("SC2PATH", r"C:\Program Files (x86)\StarCraft II")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

import argparse
import logging
import PIL.ImageGrab
import PIL.Image

logger = logging.getLogger(__name__)


def find_sc2_window():
    """Return the SC2 window's bounding box (left, top, right, bottom) or None."""
    try:
        import pygetwindow as gw
    except ImportError:
        os.system(f"{sys.executable} -m pip install pygetwindow -q")
        import pygetwindow as gw

    candidates = []
    for w in gw.getAllWindows():
        title = (w.title or "").strip()
        if title and ("StarCraft" in title or "SC2" in title):
            candidates.append(w)

    if not candidates:
        return None

    # Pick the largest window matching
    best = max(candidates, key=lambda w: w.width * w.height)
    return (best.left, best.top, best.left + best.width, best.top + best.height)


def capture_sc2_window(output_path: Path, label: str = "") -> bool:
    """Capture only the SC2 window region. Returns True if successful."""
    bbox = find_sc2_window()
    if bbox is None:
        logger.warning("SC2 window not found")
        return False

    try:
        img = PIL.ImageGrab.grab(bbox=bbox)
        img = img.convert("RGB")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path)
        print(f"  Captured {label}: {output_path}  ({img.size[0]}x{img.size[1]})")
        return True
    except Exception as exc:
        logger.warning("Capture failed: %s", exc)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture live SC2 game screenshots for paper figures"
    )
    parser.add_argument("--output-dir", default="paper/sc2_screenshots/",
                        help="Output directory")
    parser.add_argument("--game-duration", type=float, default=120.0,
                        help="Game duration in seconds (default: 120)")
    parser.add_argument("--difficulty", default="VeryEasy",
                        choices=["VeryEasy", "Easy", "Medium"])
    parser.add_argument("--map", default="Simple64")
    parser.add_argument("--realtime", action="store_true",
                        help="Run at real-time speed for cleaner screenshots")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    out_dir = ROOT / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SC2 Live Screenshot Capture")
    print("=" * 60)
    print(f"Output dir : {out_dir}")
    print(f"Map        : {args.map}")
    print(f"Difficulty : {args.difficulty}")
    print(f"Duration   : {args.game_duration}s ({'realtime' if args.realtime else 'fastest'})")
    print()

    try:
        import sc2
        from sc2.main import run_game
        from sc2.data import Race as SC2Race, Difficulty as SC2Difficulty
        from sc2.player import Bot, Computer
        from blanc.sc2live.bot import DeFAbBot
        from blanc.sc2live.policies.scripted import ScriptedPolicy
    except ImportError as exc:
        print(f"ERROR: {exc}\nRun: pip install blanc[sc2live]")
        return 1

    # Capture moments: at fixed intervals via a custom bot
    capture_steps = [50, 200, 500, 800, 1100, 1500]
    captured = []

    class CapturingBot(DeFAbBot):
        async def on_step(self, iteration: int) -> None:
            await super().on_step(iteration)
            # Move units to map center to make screenshots more interesting
            if iteration % 88 == 0:
                try:
                    center = self.game_info.map_center  # type: ignore[attr-defined]
                    for unit in self.units:              # type: ignore[attr-defined]
                        unit.move(center)
                except AttributeError:
                    pass
            # Capture at key moments
            if iteration in capture_steps:
                label = f"step{iteration:04d}"
                path = out_dir / f"sc2_live_{label}.png"
                ok = capture_sc2_window(path, label)
                if ok:
                    captured.append(path)
            # End game after duration
            if iteration > 1600:
                try:
                    await self._client.leave()  # type: ignore[attr-defined]
                except Exception:
                    pass

    bot = CapturingBot(policy=ScriptedPolicy())
    diff_obj = getattr(SC2Difficulty, args.difficulty, SC2Difficulty.VeryEasy)

    try:
        run_game(
            sc2.maps.get(args.map),
            [
                Bot(SC2Race.Terran, bot),
                Computer(SC2Race.Random, diff_obj),
            ],
            realtime=args.realtime,
        )
    except Exception as exc:
        print(f"Game error (likely concede): {exc}")

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
