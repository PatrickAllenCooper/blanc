"""
Mine defeasible conflicts from SC2 game traces for DPO preference data.

A defeasible conflict (Definition 9.1 in paper.tex line 1009) is a pair of
defeasible rules (r_A, r_B) such that:
    D ⊢∂ q  via a chain including r_A
    D ⊢∂ ~q via a chain including r_B

with no existing superiority relation resolving the conflict.

This script scans all .jsonl trace files in a directory, reconstructs the
Theory for each frame, and identifies frames where a conflict is present by
querying the DefeasibleEngine.  Each conflict is serialized as a JSON record
for consumption by experiments/finetuning/prepare_sc2live_preference_data.py.

Output format (one JSON object per line in --output file):
{
    "conflict_id": "sc2live_c0001",
    "source_file": "trace_1234567890.jsonl",
    "step": 440,
    "rule_a_label": "rts_r3000",
    "rule_a_head": "authorized_to_engage(X,Y)",
    "rule_a_body": ["military_unit(X)", "military_target(Y)"],
    "rule_b_label": "rts_r3003",
    "rule_b_head": "~authorized_to_engage(X,Y)",
    "rule_b_body": ["in_zone(X, restricted_zone_alpha)", "in_zone(Y, restricted_zone_alpha)"],
    "target": "authorized_to_engage(marine_0x00000041, enemy_marine_0x00000042)",
    "facts": ["military_unit(marine_0x00000041)", ...]
}

Usage::

    python scripts/mine_sc2_conflicts.py
    python scripts/mine_sc2_conflicts.py --trace-dir data/sc2_traces/ --output data/sc2_conflicts.jsonl
    python scripts/mine_sc2_conflicts.py --max-per-file 50

Author: Anonymous Authors
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from blanc.core.theory import Theory, RuleType
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from blanc.sc2live.replay import ReplayTraceExtractor


ROE_PREDICATES = [
    "authorized_to_engage",
    "cleared_to_engage",
    "ordered_to_retreat",
    "stealth_posture_active",
    "priority_target",
]


def _find_conflicts_in_theory(theory: Theory) -> list[dict]:
    """
    Return a list of conflict records for all detected defeasible conflicts.

    A conflict is detected when:
        (a) q is +∂ derivable via at least one defeasible rule
        (b) ~q is +∂ derivable via at least one defeater
    with no superiority relation resolving the conflict (i.e., both hold).

    In standard defeasible logic this cannot happen simultaneously (the
    engine picks the winning side).  We detect *potential* conflicts by
    checking whether removing each defeater would expose a conflict.
    """
    conflicts = []

    defeasible_rules = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in theory.rules if r.rule_type == RuleType.DEFEATER]

    for defeater in defeaters:
        if not defeater.head.startswith("~"):
            continue
        # The defeated literal (strip leading ~)
        positive_head = defeater.head[1:]
        pred_name = positive_head.split("(")[0]
        if pred_name not in ROE_PREDICATES:
            continue

        # Find a matching defeasible rule that concludes positive_head pattern
        matching_defeasible = [
            r for r in defeasible_rules
            if r.head.split("(")[0] == pred_name
        ]
        if not matching_defeasible:
            continue

        # Build theory without the defeater (D^-)
        import copy
        theory_minus = copy.deepcopy(theory)
        theory_minus.rules = [r for r in theory_minus.rules
                               if r.label != defeater.label]

        # Find ground instances where the conflict would fire
        for fact in theory.facts:
            if pred_name not in fact:
                continue
            # Check: in D^- is the fact derivable (no defeater -> default fires)?
            if not defeasible_provable(theory_minus, fact):
                continue
            # Check: in D is the defeater rule actually blocking it?
            if defeasible_provable(theory, fact):
                # Not a conflict -- defeater didn't block it
                continue

            for rule_a in matching_defeasible:
                conflicts.append({
                    "rule_a_label": rule_a.label or "",
                    "rule_a_head": rule_a.head,
                    "rule_a_body": list(rule_a.body),
                    "rule_b_label": defeater.label or "",
                    "rule_b_head": defeater.head,
                    "rule_b_body": list(defeater.body),
                    "target": fact,
                })
            break  # one conflict record per defeater per theory

    return conflicts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Mine defeasible conflicts from SC2 live game traces"
    )
    parser.add_argument(
        "--trace-dir", default="data/sc2_traces/",
        help="Directory of .jsonl trace files (default: data/sc2_traces/)"
    )
    parser.add_argument(
        "--output", default="data/sc2_conflicts.jsonl",
        help="Output .jsonl file path (default: data/sc2_conflicts.jsonl)"
    )
    parser.add_argument(
        "--max-per-file", type=int, default=100,
        help="Max conflicts extracted per trace file (default: 100)"
    )
    parser.add_argument(
        "--max-frames", type=int, default=1000,
        help="Max frames to scan (default: 1000)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
    )
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    if not trace_dir.exists():
        print(f"ERROR: trace directory not found: {trace_dir}")
        return 1

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SC2 LIVE CONFLICT MINING")
    print("=" * 70)
    print(f"Trace dir : {trace_dir}")
    print(f"Output    : {output_path}")

    extractor = ReplayTraceExtractor()
    conflict_id = 0
    frames_scanned = 0

    with open(output_path, "w") as out:
        for frame in extractor.stream_directory(trace_dir):
            if frames_scanned >= args.max_frames:
                break
            frames_scanned += 1

            conflicts = _find_conflicts_in_theory(frame.theory)
            for rec in conflicts[:args.max_per_file]:
                conflict_id += 1
                record = {
                    "conflict_id": f"sc2live_c{conflict_id:05d}",
                    "source_file": str(Path(frame.source_file).name),
                    "step": frame.step,
                    "facts": sorted(frame.theory.facts),
                    **rec,
                }
                out.write(json.dumps(record) + "\n")

            if args.verbose and conflicts:
                print(f"  frame step={frame.step}: {len(conflicts)} conflicts")

    print(f"\nFrames scanned : {frames_scanned}")
    print(f"Conflicts mined: {conflict_id}")
    print(f"Output         : {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
