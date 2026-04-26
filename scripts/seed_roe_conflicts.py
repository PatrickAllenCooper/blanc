"""
Convert ROE_LEVEL3_SEEDS into conflict records for DPO preference data.

The organic conflict miner (mine_sc2_conflicts.py) requires game traces where
units are in restricted zones, which don't arise naturally from the current
ScriptedPolicy bot.  This script takes the direct route: the 6 ROE_LEVEL3_SEEDS
already define perfect defeasible conflicts with known gold defeaters.  It
converts each seed into the conflict record format expected by
experiments/finetuning/prepare_sc2live_preference_data.py.

Output format (one JSON object per line, same schema as mine_sc2_conflicts.py):
{
    "conflict_id": "roe_seed_c00001",
    "source_file": "ROE_LEVEL3_SEEDS",
    "step": 0,
    "facts": [...context_facts],
    "rule_a_label": "rts_r3000",
    "rule_a_head": "authorized_to_engage(X,Y)",
    "rule_a_body": ["military_unit(X)", "military_target(Y)"],
    "rule_b_label": "rts_r3003",
    "rule_b_head": "~authorized_to_engage(X,Y)",
    "rule_b_body": ["in_zone(X, restricted_zone_alpha)", ...],
    "target": "authorized_to_engage(marine, enemy_marine_squad)"
}

Usage::

    python scripts/seed_roe_conflicts.py
    python scripts/seed_roe_conflicts.py --output data/sc2_conflicts.jsonl

Author: Patrick Cooper
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from blanc.core.theory import RuleType
from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb


def _get_matching_default_rule(kb, gold_defeater_head: str):
    """
    Find the defeasible rule whose head predicate matches the positive form
    of the defeater's head (i.e., the default that the defeater overrides).

    e.g., gold_defeater_head = "~authorized_to_engage(X,Y)"
          -> looks for authorized_to_engage rule in KB
    """
    if not gold_defeater_head.startswith("~"):
        return None
    positive_pred = gold_defeater_head[1:].split("(")[0]
    for rule in kb.rules:
        if rule.rule_type == RuleType.DEFEASIBLE:
            if rule.head.split("(")[0] == positive_pred:
                return rule
    return None


def _get_gold_defeater_rule(kb, defeater_label: str):
    """Return the defeater rule with the given label from the KB."""
    for rule in kb.rules:
        if rule.label == defeater_label:
            return rule
    return None


def build_conflict_records(kb, seeds: list) -> list[dict]:
    """
    Convert ROE_LEVEL3_SEEDS into conflict record dicts.

    Each seed provides:
        scenario_id, context_facts, defeater_label, gold_defeater_head,
        gold_defeater_body, anomaly
    """
    records = []
    for i, seed in enumerate(seeds):
        defeater_label = seed["defeater_label"]
        gold_head      = seed["gold_defeater_head"]
        gold_body      = seed["gold_defeater_body"]
        anomaly        = seed["anomaly"]
        context_facts  = seed["context_facts"]

        # Find the default rule (rule_a) that the defeater (rule_b) overrides
        default_rule = _get_matching_default_rule(kb, gold_head)
        # Find the actual defeater rule (rule_b) in the KB
        defeater_rule = _get_gold_defeater_rule(kb, defeater_label)

        if default_rule is None:
            print(f"  WARNING: no default rule found for {gold_head}, skipping")
            continue

        record = {
            "conflict_id": f"roe_seed_c{i+1:05d}",
            "source_file": "ROE_LEVEL3_SEEDS",
            "step": 0,
            "scenario_id": seed["scenario_id"],
            "description": seed.get("description", ""),
            "facts": context_facts,
            # rule_a = the default rule being overridden
            "rule_a_label": default_rule.label or "",
            "rule_a_head":  default_rule.head,
            "rule_a_body":  list(default_rule.body),
            # rule_b = the defeater (gold answer for DPO)
            "rule_b_label": defeater_label,
            "rule_b_head":  gold_head,
            "rule_b_body":  gold_body,
            "target": anomaly,
        }
        records.append(record)

    return records


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Convert ROE_LEVEL3_SEEDS into DPO conflict records"
    )
    parser.add_argument(
        "--output", default="data/sc2_conflicts.jsonl",
        help="Output .jsonl path (default: data/sc2_conflicts.jsonl)"
    )
    parser.add_argument(
        "--append", action="store_true",
        help="Append to existing file instead of overwriting"
    )
    args = parser.parse_args()

    output_path = ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Loading RTS engagement KB...")
    kb = create_rts_engagement_kb(include_instances=False)

    print("Loading ROE_LEVEL3_SEEDS...")
    sys.path.insert(0, str(ROOT / "scripts"))
    from generate_rts_instances import ROE_LEVEL3_SEEDS

    print(f"Converting {len(ROE_LEVEL3_SEEDS)} seeds to conflict records...")
    records = build_conflict_records(kb, ROE_LEVEL3_SEEDS)

    mode = "a" if args.append else "w"
    with open(output_path, mode) as f:
        for rec in records:
            f.write(json.dumps(rec) + "\n")

    print(f"\nWrote {len(records)} conflict records to: {output_path}")
    for rec in records:
        print(f"  {rec['conflict_id']}  {rec['scenario_id']}")
        print(f"    default: [{rec['rule_a_label']}] {rec['rule_a_head']}")
        print(f"    defeater: [{rec['rule_b_label']}] {rec['rule_b_head']}")
        print(f"    target anomaly: {rec['target']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
