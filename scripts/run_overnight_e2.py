"""
Overnight E2-E3 pipeline: record games, generate DeFAb instances, mine conflicts.

Designed to run unattended in ~3-4 hours on a local Windows machine.
Produces:
    data/sc2_traces/          .jsonl trace files (one per game)
    instances/sc2live_instances.json   L1/L2 DeFAb instances
    data/sc2_conflicts.jsonl           defeasible conflicts for DPO

Optimisations vs. the standard scripts:
    - MoveToMiddlePolicy: sends units to map center so frames capture
      engagement_zone_alpha scenarios (not just main_base facts)
    - 2 partition strategies instead of 4 (50% faster instance generation)
    - 5 targets per frame instead of 20 (80% faster criticality checks)
    - Processes only the most informative frames (those with military contacts)

Usage::

    python scripts/run_overnight_e2.py
    python scripts/run_overnight_e2.py --games 10 --frames 100 --output-prefix overnight_v1

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path

os.environ.setdefault("SC2PATH", r"C:\Program Files (x86)\StarCraft II")
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 1: record games with MoveToMiddlePolicy
# ---------------------------------------------------------------------------

def record_games(
    n_games: int,
    trace_dir: Path,
    difficulty: str = "VeryEasy",
) -> list[Path]:
    """Record n_games and return list of trace .jsonl files produced."""
    try:
        import sc2
        from sc2.main import run_game
        from sc2.data import Race as SC2Race, Difficulty as SC2Difficulty
        from sc2.player import Bot, Computer
        from blanc.sc2live.bot import DeFAbBot, SNAPSHOT_INTERVAL
        from blanc.sc2live.policies.move_to_middle import MoveToMiddlePolicy
    except ImportError as exc:
        print(f"ERROR: {exc}\nInstall with: pip install blanc[sc2live]")
        return []

    trace_dir.mkdir(parents=True, exist_ok=True)

    # Override on_step to also issue MoveToMiddle orders
    class EnhancedBot(DeFAbBot):
        async def on_step(self, iteration: int) -> None:
            await super().on_step(iteration)
            # Move all units toward center every 88 steps
            if iteration % 88 == 0:
                try:
                    center = self.game_info.map_center  # type: ignore[attr-defined]
                    for unit in self.units:              # type: ignore[attr-defined]
                        unit.move(center)
                except AttributeError:
                    pass

    diff_obj = getattr(SC2Difficulty, difficulty, SC2Difficulty.VeryEasy)
    produced: list[Path] = []

    for i in range(n_games):
        print(f"  Game {i+1}/{n_games} ({difficulty})...")
        t0 = time.time()
        bot = EnhancedBot(trace_dir=trace_dir)
        try:
            run_game(
                sc2.maps.get("Simple64"),
                [
                    Bot(SC2Race.Terran, bot),
                    Computer(SC2Race.Random, diff_obj),
                ],
                realtime=False,
            )
        except Exception as exc:
            logger.debug("Game ended: %s", exc)

        elapsed = time.time() - t0
        n_snap = len(bot.trace)
        print(f"    {n_snap} snapshots in {elapsed:.0f}s")

        if n_snap > 0:
            # Find newest trace file
            files = sorted(trace_dir.glob("trace_*.jsonl"))
            if files:
                produced.append(files[-1])

    return produced


# ---------------------------------------------------------------------------
# Phase 2: instance generation (fast mode)
# ---------------------------------------------------------------------------

def generate_instances_fast(
    trace_dir: Path,
    max_frames: int,
    max_targets: int,
    output_path: Path,
) -> int:
    """
    Generate DeFAb instances using only 2 partition strategies and
    limited targets per frame.  Returns number of instances generated.
    """
    from blanc.sc2live.replay import ReplayTraceExtractor
    from blanc.author.conversion import phi_kappa
    from blanc.author.support import full_theory_criticality
    from blanc.author.generation import generate_level1_instance, generate_level2_instance
    from blanc.generation.partition import (
        partition_leaf, partition_rule, compute_dependency_depths,
    )
    from blanc.core.theory import RuleType
    from blanc.reasoning.defeasible import defeasible_provable
    import importlib.util, re

    # Load _probe_roe_targets from generate_sc2live_instances.py
    spec = importlib.util.spec_from_file_location(
        "gen_sc2", ROOT / "scripts" / "generate_sc2live_instances.py"
    )
    gen_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gen_mod)
    probe_fn = gen_mod._probe_roe_targets

    ext = ReplayTraceExtractor()
    all_instances = []
    frames_processed = 0

    # Prioritise frames with military contacts (more interesting scenarios)
    all_frames = list(ext.stream_directory(trace_dir))
    contact_frames = [f for f in all_frames
                      if any("military_target(" in fact for fact in f.theory.facts)]
    other_frames   = [f for f in all_frames
                      if not any("military_target(" in fact for fact in f.theory.facts)]
    ordered_frames = contact_frames + other_frames
    print(f"  Frames with military contacts: {len(contact_frames)}/{len(all_frames)}")

    for frame in ordered_frames[:max_frames]:
        frames_processed += 1
        theory = frame.theory
        if len(theory.facts) < 3:
            continue

        targets = probe_fn(theory)[:max_targets]
        if not targets:
            continue

        depths_map = compute_dependency_depths(theory)
        # Only two fastest strategies for overnight
        strategies = [("leaf", partition_leaf), ("rule", partition_rule)]

        for strat_name, partition_fn in strategies:
            converted = phi_kappa(theory, partition_fn)
            count = 0
            for target in targets:
                if count >= 5:
                    break
                try:
                    if not defeasible_provable(converted, target):
                        continue
                    critical = full_theory_criticality(converted, target)

                    # L1
                    critical_facts = [e for e in critical if isinstance(e, str)]
                    if critical_facts:
                        inst = generate_level1_instance(
                            converted, target, critical_facts[0],
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        all_instances.append(inst)
                        count += 1

                    # L2
                    critical_rules = [e for e in critical
                                      if hasattr(e, "rule_type")
                                      and e.rule_type == RuleType.DEFEASIBLE]
                    if critical_rules:
                        inst = generate_level2_instance(
                            converted, target, critical_rules[0],
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        all_instances.append(inst)
                        count += 1
                except Exception:
                    continue

        if frames_processed % 10 == 0:
            print(f"  Frame {frames_processed}/{max_frames}: "
                  f"{len(all_instances)} instances so far")

    if not all_instances:
        print("  No instances generated.")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "metadata": {
            "domain": "sc2live",
            "trace_dir": str(trace_dir),
            "frames_processed": frames_processed,
            "frames_with_contacts": len(contact_frames),
            "generation_date": datetime.now().isoformat(),
            "strategies": ["leaf", "rule"],
        },
        "instances": [inst.to_dict() for inst in all_instances],
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    return len(all_instances)


# ---------------------------------------------------------------------------
# Phase 3: conflict mining
# ---------------------------------------------------------------------------

def mine_conflicts(trace_dir: Path, conflicts_path: Path) -> int:
    """Mine defeasible conflicts from traces. Returns conflict count."""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "mine_sc2_conflicts.py"),
         "--trace-dir", str(trace_dir),
         "--output", str(conflicts_path),
         "--max-per-file", "50",
         "--max-frames", "500"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  WARNING: conflict mining failed: {result.stderr[-200:]}")
        return 0
    # Parse count from output
    for line in result.stdout.splitlines():
        if "Conflicts mined:" in line:
            return int(line.split(":")[-1].strip())
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Overnight E2-E3: record games, generate instances, mine conflicts"
    )
    parser.add_argument("--games",   type=int, default=12,
                        help="Number of SC2 games to record (default: 12)")
    parser.add_argument("--frames",  type=int, default=200,
                        help="Max frames to process for instance generation (default: 200)")
    parser.add_argument("--targets", type=int, default=8,
                        help="Max ROE targets per frame (default: 8)")
    parser.add_argument("--difficulty", default="VeryEasy",
                        choices=["VeryEasy", "Easy", "Medium"],
                        help="AI difficulty (default: VeryEasy)")
    parser.add_argument("--trace-dir", default="data/sc2_traces/",
                        help="Trace output directory (default: data/sc2_traces/)")
    parser.add_argument("--instances-out", default="instances/sc2live_instances.json",
                        help="Instance output file")
    parser.add_argument("--conflicts-out", default="data/sc2_conflicts.jsonl",
                        help="Conflict output file")
    parser.add_argument("--skip-games", action="store_true",
                        help="Skip game recording (use existing traces)")
    parser.add_argument("--skip-instances", action="store_true",
                        help="Skip instance generation")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    trace_dir      = ROOT / args.trace_dir
    instances_path = ROOT / args.instances_out
    conflicts_path = ROOT / args.conflicts_out

    print("=" * 70)
    print("OVERNIGHT E2-E3: SC2 GROUNDING + INSTANCE GENERATION + CONFLICT MINING")
    print("=" * 70)
    print(f"Games        : {args.games}  (difficulty={args.difficulty})")
    print(f"Frames       : {args.frames}")
    print(f"Targets/frame: {args.targets}")
    print(f"Trace dir    : {trace_dir}")
    print(f"Instances    : {instances_path}")
    print(f"Conflicts    : {conflicts_path}")
    print(f"Start        : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    t_total = time.time()

    # ── Phase 1: record games ────────────────────────────────────────────────
    if not args.skip_games:
        print(f"PHASE 1: Recording {args.games} games...")
        t1 = time.time()
        produced = record_games(args.games, trace_dir, args.difficulty)
        elapsed1 = time.time() - t1
        print(f"Phase 1 done: {len(produced)} traces in {elapsed1:.0f}s")
        print()
    else:
        print("Phase 1: SKIPPED (using existing traces)")
        print()

    # ── Phase 2: generate instances ───────────────────────────────────────────
    if not args.skip_instances:
        print(f"PHASE 2: Generating instances from up to {args.frames} frames...")
        t2 = time.time()
        n_instances = generate_instances_fast(
            trace_dir, args.frames, args.targets, instances_path,
        )
        elapsed2 = time.time() - t2
        print(f"Phase 2 done: {n_instances} instances in {elapsed2:.0f}s")
        print()
    else:
        print("Phase 2: SKIPPED")
        print()

    # ── Phase 3: mine conflicts ───────────────────────────────────────────────
    print("PHASE 3: Mining defeasible conflicts...")
    t3 = time.time()
    n_conflicts = mine_conflicts(trace_dir, conflicts_path)
    elapsed3 = time.time() - t3
    print(f"Phase 3 done: {n_conflicts} conflicts in {elapsed3:.0f}s")
    print()

    # ── Summary ───────────────────────────────────────────────────────────────
    total_elapsed = time.time() - t_total
    print("=" * 70)
    print("OVERNIGHT RUN COMPLETE")
    print("=" * 70)
    print(f"Total time   : {total_elapsed/3600:.2f} hours ({total_elapsed:.0f}s)")
    print(f"Instances    : {instances_path}")
    print(f"Conflicts    : {conflicts_path}")
    print(f"End          : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Next steps:")
    print("  Evaluate sc2live instances:")
    print(f"    python scripts/run_sc2_evaluation.py --provider foundry-deepseek \\")
    print(f"      --instances-path {instances_path} --include-level3")
    print("  Build DPO preference data:")
    print(f"    python experiments/finetuning/prepare_sc2live_preference_data.py \\")
    print(f"      --conflicts-file {conflicts_path} --provider foundry-deepseek")
    return 0


if __name__ == "__main__":
    sys.exit(main())
