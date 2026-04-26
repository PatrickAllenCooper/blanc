"""
Record SC2 game traces via two DeFAbBot instances playing the built-in AI.

Each game produces a .jsonl trace file (one JSON line per SNAPSHOT_INTERVAL
steps) that feeds scripts/generate_sc2live_instances.py.

Usage::

    # Default: 1 game, Easy AI, Simple64, Terran
    python scripts/sc2live_extract_traces.py

    # 20 games across difficulties and races
    python scripts/sc2live_extract_traces.py --games 20 --difficulty Random

    # Custom output directory
    python scripts/sc2live_extract_traces.py --output data/sc2_traces/

Requirements:
    - StarCraft II installed (Windows/macOS local, or headless Linux on CURC)
    - pip install blanc[sc2live]
    - SC2PATH environment variable set on Linux

Author: Patrick Cooper
"""

import argparse
import asyncio
import logging
import random
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent
import sys as _sys
_sys.path.insert(0, str(ROOT / "src"))
_sys.path.insert(0, str(ROOT))   # for examples/ package

# ── Difficulty mapping ────────────────────────────────────────────────────────

DIFFICULTY_MAP = {
    "VeryEasy": "VeryEasy",
    "Easy": "Easy",
    "Medium": "Medium",
    "Hard": "Hard",
    "VeryHard": "VeryHard",
    "Random": None,  # chosen randomly each game
}

RACE_NAMES = ["Terran", "Protoss", "Zerg", "Random"]

MAPS = [
    "Simple64",
    "AcropolisLE",
    "BerlingradLE",
    "NightshadeLE",
]


def _check_sc2_import() -> bool:
    """Return True if burnysc2 is importable."""
    try:
        import sc2  # noqa: F401  type: ignore[import]
        return True
    except ImportError:
        print(
            "ERROR: burnysc2 is not installed.\n"
            "Install with: pip install blanc[sc2live]\n"
            "On Linux headless: run scripts/install_sc2_linux_headless.sh first."
        )
        return False


def run_single_game(
    map_name: str,
    race: str,
    difficulty: str,
    trace_dir: Path,
    realtime: bool = False,
) -> Path | None:
    """
    Run a single SC2 game and return the trace file path on success.

    Returns None if sc2 is unavailable or the game fails.
    """
    try:
        import sc2  # type: ignore[import]
        from sc2.main import run_game  # type: ignore[import]
        from sc2.data import Difficulty as SC2Difficulty, Race as SC2Race  # type: ignore[import]
        from sc2.player import Bot, Computer  # type: ignore[import]
        from blanc.sc2live.bot import DeFAbBot
        from blanc.sc2live.policies.scripted import ScriptedPolicy

        bot = DeFAbBot(policy=ScriptedPolicy(), trace_dir=trace_dir)
        race_obj = getattr(SC2Race, race, SC2Race.Terran)
        diff_obj = getattr(SC2Difficulty, difficulty, SC2Difficulty.Easy)

        run_game(
            sc2.maps.get(map_name),
            [
                Bot(race_obj, bot),
                Computer(SC2Race.Random, diff_obj),
            ],
            realtime=realtime,
        )

        # Find newest .jsonl in trace_dir
        files = sorted(trace_dir.glob("trace_*.jsonl"))
        return files[-1] if files else None

    except Exception as exc:
        logger.error("Game failed: %s", exc)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Record DeFAbBot game traces for DeFAb instance generation"
    )
    parser.add_argument(
        "--games", type=int, default=1,
        help="Number of games to record (default: 1)"
    )
    parser.add_argument(
        "--map", default="Simple64",
        choices=MAPS + ["random"],
        help="Map name or 'random' (default: Simple64)"
    )
    parser.add_argument(
        "--race", default="Terran",
        choices=RACE_NAMES,
        help="Bot race (default: Terran)"
    )
    parser.add_argument(
        "--difficulty", default="Easy",
        choices=list(DIFFICULTY_MAP.keys()),
        help="Built-in AI difficulty (default: Easy)"
    )
    parser.add_argument(
        "--output", default="data/sc2_traces/",
        help="Directory to write .jsonl trace files (default: data/sc2_traces/)"
    )
    parser.add_argument(
        "--realtime", action="store_true",
        help="Run at real-time speed (slower but more natural)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Enable debug logging"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    if not _check_sc2_import():
        return 1

    trace_dir = Path(args.output)
    trace_dir.mkdir(parents=True, exist_ok=True)

    difficulties = list(DIFFICULTY_MAP.keys())[:-1] if args.difficulty == "Random" else [DIFFICULTY_MAP[args.difficulty]]
    maps = MAPS if args.map == "random" else [args.map]

    print(f"Recording {args.games} game(s) -> {trace_dir}")
    print("=" * 60)

    success = 0
    for i in range(args.games):
        map_name = random.choice(maps)
        diff = random.choice(difficulties)
        print(f"\nGame {i+1}/{args.games}: {map_name}, difficulty={diff}, race={args.race}")

        trace_file = run_single_game(
            map_name=map_name,
            race=args.race,
            difficulty=diff,
            trace_dir=trace_dir,
            realtime=args.realtime,
        )
        if trace_file:
            print(f"  -> Trace: {trace_file}")
            success += 1
        else:
            print("  -> FAILED (no trace produced)")

    print(f"\nComplete: {success}/{args.games} games succeeded")
    print(f"Traces in: {trace_dir}")
    return 0 if success > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
