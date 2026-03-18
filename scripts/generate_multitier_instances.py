"""
Generate instances from all extracted multi-tier theories.

Loads theories from data/extracted/*/theory.pkl and generates
L1, L2, and L3 instances using the same pipeline as Tier 1.

Author: Patrick Cooper
"""

import sys
import json
import pickle
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.generate_tier1_instances import (
    generate_domain,
    partition_into_subtheories,
    generate_from_subtheory,
)

_PROJECT_ROOT = Path(__file__).parent.parent
_EXTRACTED_DIR = _PROJECT_ROOT / "data" / "extracted"
_OUTPUT_DIR = _PROJECT_ROOT / "instances" / "multitier"


def main():
    print("=" * 70, flush=True)
    print("MULTI-TIER INSTANCE GENERATION", flush=True)
    print("=" * 70, flush=True)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    sources = []
    for d in sorted(_EXTRACTED_DIR.iterdir()):
        if d.is_dir() and (d / "theory.pkl").exists():
            stats_file = d / "stats.json"
            if stats_file.exists():
                with open(stats_file) as f:
                    stats = json.load(f)
                rules = stats.get("total_rules", 0)
                if rules > 0 and rules < 500000:
                    sources.append((d.name, rules))

    if not sources:
        print("No extracted theories found.", flush=True)
        return 1

    print(f"Sources with materialized theories:", flush=True)
    for name, rules in sources:
        print(f"  {name}: {rules:,} rules", flush=True)

    all_stats = {}
    for name, rules in sources:
        theory_path = _EXTRACTED_DIR / name / "theory.pkl"
        with open(theory_path, "rb") as f:
            theory = pickle.load(f)

        instances = generate_domain(name, theory)

        out_dir = _OUTPUT_DIR / name
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "instances.json", "w") as f:
            json.dump(instances, f)

        l1 = sum(1 for i in instances if i["level"] == 1)
        l2 = sum(1 for i in instances if i["level"] == 2)
        l3 = sum(1 for i in instances if i["level"] == 3)
        all_stats[name] = {"total": len(instances), "L1": l1, "L2": l2, "L3": l3}

    print(f"\n{'=' * 70}", flush=True)
    print("GENERATION COMPLETE", flush=True)
    print(f"{'=' * 70}", flush=True)

    total = {"L1": 0, "L2": 0, "L3": 0, "total": 0}
    for name, s in all_stats.items():
        print(f"  {name:20s}: {s['total']:>6,} (L1={s['L1']}, L2={s['L2']}, L3={s['L3']})",
              flush=True)
        for k in total:
            total[k] += s[k]

    print(f"  {'TOTAL':20s}: {total['total']:>6,} (L1={total['L1']}, L2={total['L2']}, L3={total['L3']})",
          flush=True)

    with open(_OUTPUT_DIR / "generation_summary.json", "w") as f:
        json.dump({"sources": all_stats, "totals": total}, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
