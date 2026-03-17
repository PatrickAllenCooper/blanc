"""
Package Tier 1 dataset: generate statistics and summary.

Author: Patrick Cooper
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    output_dir = Path("instances/tier1")
    all_instances = []
    domain_stats = {}

    for domain_dir in sorted(output_dir.iterdir()):
        if not domain_dir.is_dir():
            continue
        inst_file = domain_dir / "instances.json"
        if not inst_file.exists():
            continue
        with open(inst_file) as f:
            instances = json.load(f)
        domain = domain_dir.name
        l1 = sum(1 for i in instances if i["level"] == 1)
        l2 = sum(1 for i in instances if i["level"] == 2)
        l3 = sum(1 for i in instances if i["level"] == 3)
        domain_stats[domain] = {"total": len(instances), "L1": l1, "L2": l2, "L3": l3}
        all_instances.extend(instances)
        print(f"  {domain:12s}: {len(instances):>8,} instances "
              f"(L1={l1:,}, L2={l2:,}, L3={l3:,})")

    total = len(all_instances)
    total_l1 = sum(s["L1"] for s in domain_stats.values())
    total_l2 = sum(s["L2"] for s in domain_stats.values())
    total_l3 = sum(s["L3"] for s in domain_stats.values())

    print(f"\n  TOTAL:        {total:>8,} instances "
          f"(L1={total_l1:,}, L2={total_l2:,}, L3={total_l3:,})")
    print(f"\n  Tier 0 baseline: 409 instances")
    print(f"  Tier 1 multiplier: {total / 409:.1f}x")

    summary = {
        "total_instances": total,
        "level_breakdown": {
            "L1": total_l1,
            "L2": total_l2,
            "L3": total_l3,
            "total": total,
        },
        "domain_breakdown": domain_stats,
        "domains_completed": list(domain_stats.keys()),
        "tier0_instances": 409,
        "multiplier": round(total / 409, 1),
        "rules_extracted": 290576,
        "rule_multiplier": 125.4,
    }

    with open(output_dir / "generation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Summary saved to {output_dir / 'generation_summary.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
