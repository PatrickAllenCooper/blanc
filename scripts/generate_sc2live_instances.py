"""
Generate DeFAb instances from live SC2 game traces.

Reads .jsonl trace files produced by scripts/sc2live_extract_traces.py and
applies the full DeFAb instance generation pipeline to each frame snapshot:

    - Level 1: missing ground fact (observation completion)
    - Level 2: missing defeasible ROE rule (rule abduction)
    - Level 3: missing defeater (exception construction)

Output: instances/sc2live_instances.json  (same format as rts_engagement_instances.json)

The generated instances are certified by the same DefeasibleEngine verifier as
all other DeFAb instances.  Cross-environment evaluation (E5) uses them
directly via scripts/run_sc2_evaluation.py.

Usage::

    python scripts/generate_sc2live_instances.py
    python scripts/generate_sc2live_instances.py --trace-dir data/sc2_traces/
    python scripts/generate_sc2live_instances.py --level 3 --max-instances 50

Author: Patrick Cooper
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from blanc.sc2live.replay import ReplayTraceExtractor
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import (
    generate_level1_instance,
    generate_level2_instance,
    generate_level3_instance,
)
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    partition_depth,
    partition_random,
    compute_dependency_depths,
)
from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


ROE_PREDICATES = [
    "authorized_to_engage",
    "cleared_to_engage",
    "ordered_to_retreat",
    "stealth_posture_active",
    "priority_target",
    "mission_accomplished",
]


def generate_instances_from_frame(
    frame,
    level: int,
    max_instances: int,
) -> list:
    """Generate Level 1 or Level 2 instances from a single trace frame."""
    theory = frame.theory
    if len(theory.facts) < 3:
        return []

    depths_map = compute_dependency_depths(theory)
    strategies = [
        ("leaf", partition_leaf),
        ("rule", partition_rule),
        ("depth_1", partition_depth(1, depths_map)),
        ("rand_0.3", partition_random(0.3, seed=42)),
    ]

    # Collect derivable ROE targets from this frame's facts
    roe_targets = []
    for fact in theory.facts:
        for pred in ROE_PREDICATES:
            if pred in fact and defeasible_provable(theory, fact):
                roe_targets.append(fact)
    roe_targets = list(dict.fromkeys(roe_targets))

    if not roe_targets:
        return []

    all_instances = []
    for strat_name, partition_fn in strategies:
        converted = phi_kappa(theory, partition_fn)
        count = 0
        for target in roe_targets:
            if count >= max_instances:
                break
            try:
                if not defeasible_provable(converted, target):
                    continue
                critical = full_theory_criticality(converted, target)
                if level == 1:
                    critical_facts = [e for e in critical if isinstance(e, str)]
                    if critical_facts:
                        inst = generate_level1_instance(
                            converted, target, critical_facts[0],
                            k_distractors=5,
                            distractor_strategy="syntactic",
                        )
                        all_instances.append(inst)
                        count += 1
                elif level == 2:
                    critical_rules = [
                        e for e in critical
                        if hasattr(e, "rule_type")
                        and e.rule_type == RuleType.DEFEASIBLE
                    ]
                    if critical_rules:
                        inst = generate_level2_instance(
                            converted, target, critical_rules[0],
                            k_distractors=5,
                            distractor_strategy="syntactic",
                        )
                        all_instances.append(inst)
                        count += 1
            except Exception:
                continue

    return all_instances


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate DeFAb instances from SC2 live game traces"
    )
    parser.add_argument(
        "--trace-dir", default="data/sc2_traces/",
        help="Directory containing .jsonl trace files (default: data/sc2_traces/)"
    )
    parser.add_argument(
        "--level", type=int, choices=[0, 1, 2], default=0,
        help="Level to generate (0 = L1+L2, default)"
    )
    parser.add_argument(
        "--max-instances", type=int, default=10,
        help="Max instances per frame per strategy (default: 10)"
    )
    parser.add_argument(
        "--output", default=None,
        help="Output JSON path (default: instances/sc2live_instances.json)"
    )
    parser.add_argument(
        "--max-frames", type=int, default=500,
        help="Maximum trace frames to process (default: 500)"
    )
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    if not trace_dir.exists():
        print(f"ERROR: trace directory not found: {trace_dir}")
        print("Run scripts/sc2live_extract_traces.py first.")
        return 1

    output_path = Path(args.output) if args.output else ROOT / "instances" / "sc2live_instances.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SC2 LIVE TRACE -- DeFAb INSTANCE GENERATION")
    print("=" * 70)
    print(f"Trace dir : {trace_dir}")
    print(f"Output    : {output_path}")
    print(f"Date      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    extractor = ReplayTraceExtractor()
    all_instances = []
    frames_processed = 0

    generation_log = {
        "domain": "sc2live",
        "trace_dir": str(trace_dir),
        "generation_date": datetime.now().isoformat(),
        "levels": {},
    }

    l1_count = 0
    l2_count = 0

    for frame in extractor.stream_directory(trace_dir):
        if frames_processed >= args.max_frames:
            break
        frames_processed += 1

        if frames_processed % 50 == 0:
            print(f"  Processing frame {frames_processed} (step={frame.step}, "
                  f"source={Path(frame.source_file).name})")

        if args.level in (0, 1):
            instances = generate_instances_from_frame(frame, level=1,
                                                       max_instances=args.max_instances)
            all_instances.extend(instances)
            l1_count += len(instances)

        if args.level in (0, 2):
            instances = generate_instances_from_frame(frame, level=2,
                                                       max_instances=args.max_instances)
            all_instances.extend(instances)
            l2_count += len(instances)

    generation_log["frames_processed"] = frames_processed
    generation_log["levels"]["level1"] = {"count": l1_count}
    generation_log["levels"]["level2"] = {"count": l2_count}

    print(f"\nFrames processed : {frames_processed}")
    print(f"Level 1 instances: {l1_count}")
    print(f"Level 2 instances: {l2_count}")
    print(f"Total instances  : {len(all_instances)}")

    if not all_instances:
        print("\nNo instances generated.  Record more traces or lower --max-instances.")
        return 1

    output = {
        "metadata": generation_log,
        "instances": [inst.to_dict() for inst in all_instances],
    }
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved {len(all_instances)} instances to: {output_path}")

    print("\n" + "=" * 70)
    print("SC2 LIVE INSTANCE GENERATION COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
