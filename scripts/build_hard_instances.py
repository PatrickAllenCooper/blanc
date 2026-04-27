"""
Generate DeFAb-Hard-ROE instances from the 4 verified hard seeds
and write them to instances/rts_hard_instances.json.

Author: Patrick Cooper
"""
import copy, json, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from generate_hard_roe_seeds import HARD_SEEDS

GOOD_IDS = {
    "H1_chain_defeat_repair_exception",
    "H2_positive_id_chain",
    "H4_stealth_zone_fire_interaction",
    "H6_multi_constraint_conservativity",
}

out = []
for seed in HARD_SEEDS:
    if seed["scenario_id"] not in GOOD_IDS:
        continue
    kb = create_rts_engagement_kb(include_instances=False)
    kb.rules = [r for r in kb.rules if r.label != seed["defeater_label"]]
    for fact in seed["context_facts"]:
        kb.add_fact(fact)

    gold_rule = Rule(
        head=seed["gold_defeater_head"],
        body=tuple(seed["gold_defeater_body"]),
        rule_type=RuleType.DEFEATER,
        label=seed["defeater_label"],
    )
    gold_str = (seed["gold_defeater_head"] + " :~> "
                + ", ".join(seed["gold_defeater_body"]) + ".")
    candidates = [gold_str]

    rec = {
        "scenario_id": seed["scenario_id"],
        "level": 3,
        "description": seed["description"],
        "anomaly": seed["anomaly"],
        "target": seed["anomaly"],
        "gold": gold_str,
        "candidates": candidates,
        "hard_aspects": seed["hard_aspects"],
        "metadata": {
            "domain": "rts_hard",
            "facts": sorted(kb.facts),
            "gold_defeater_label": seed["defeater_label"],
        },
    }
    out.append(rec)
    print(f"  [{seed['scenario_id']}] generated")

out_path = ROOT / "instances" / "rts_hard_instances.json"
with open(out_path, "w") as f:
    json.dump({"instances": out}, f, indent=2)
print(f"\n{len(out)} hard instances -> {out_path}")
