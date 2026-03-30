"""
Generate synthetic contamination-control instances matched to Tier 0.

For each Tier 0 evaluation instance, generates a structurally matched
synthetic counterpart with invented predicate and entity names. The
synthetic instances use the same difficulty structure but novel vocabulary
that cannot appear in any training corpus.

Author: Patrick Cooper
"""

import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.generation.synthetic import (
    generate_synthetic_theory,
    SyntheticTheoryParams,
    generate_vocabulary,
)
from blanc.author.conversion import phi_kappa
from blanc.author.generation import (
    generate_level1_instance,
    generate_level2_instance,
)
from blanc.generation.partition import partition_rule
from blanc.reasoning.defeasible import defeasible_provable

_PROJECT_ROOT = Path(__file__).parent.parent
_INSTANCES_DIR = _PROJECT_ROOT / "instances"
_OUTPUT_DIR = _PROJECT_ROOT / "instances" / "synthetic"


def load_tier0_instances():
    """Load all Tier 0 instances from the dev instance files."""
    instances = []
    for domain in ["biology", "legal", "materials"]:
        fpath = _INSTANCES_DIR / f"{domain}_dev_instances.json"
        if fpath.exists():
            with open(fpath) as f:
                data = json.load(f)
            if isinstance(data, dict) and "instances" in data:
                for inst in data["instances"]:
                    inst["domain"] = domain
                    instances.append(inst)
            elif isinstance(data, list):
                for inst in data:
                    inst["domain"] = domain
                    instances.append(inst)

    l3_path = _INSTANCES_DIR / "level3_instances.json"
    if l3_path.exists():
        with open(l3_path) as f:
            data = json.load(f)
        if isinstance(data, dict) and "instances" in data:
            instances.extend(data["instances"])
        elif isinstance(data, list):
            instances.extend(data)

    return instances


def generate_synthetic_for_instance(inst: dict, idx: int) -> dict:
    """Generate a single synthetic instance matched to a naturalistic one."""
    level = inst.get("level", 2)
    n_candidates = len(inst.get("candidates", []))
    n_gold = len(inst.get("gold", inst.get("gold_hypotheses", [])))

    theory_rules = inst.get("theory", {}).get("rules", [])
    theory_facts = inst.get("theory", {}).get("facts", [])

    types = Counter()
    for r in theory_rules:
        rt = r.get("rule_type", "DEFEASIBLE")
        types[rt] += 1

    params = SyntheticTheoryParams(
        n_facts=max(len(theory_facts), 10),
        n_strict=max(types.get("STRICT", types.get("strict", 0)), 2),
        n_defeasible=max(types.get("DEFEASIBLE", types.get("defeasible", 0)), 5),
        n_defeaters=max(types.get("DEFEATER", types.get("defeater", 0)), 1),
    )

    syn_theory = generate_synthetic_theory(params, seed=idx * 1000 + 42)

    syn_instance = {
        "id": f"synthetic_{idx}",
        "matched_to": inst.get("id", f"nat_{idx}"),
        "level": level,
        "synthetic": True,
        "theory": {
            "facts": list(syn_theory.facts),
            "rules": [
                {
                    "head": r.head,
                    "body": list(r.body),
                    "rule_type": r.rule_type.name,
                    "label": r.label,
                }
                for r in syn_theory.rules
            ],
        },
        "n_rules": len(syn_theory.rules),
        "n_facts": len(syn_theory.facts),
        "n_candidates_matched": n_candidates,
        "n_gold_matched": n_gold,
        "structural_match": {
            "nat_rules": len(theory_rules),
            "nat_facts": len(theory_facts),
            "nat_level": level,
        },
    }

    return syn_instance


def main():
    print("=" * 60)
    print("SYNTHETIC INSTANCE GENERATION")
    print("=" * 60)

    instances = load_tier0_instances()
    print(f"Tier 0 instances loaded: {len(instances)}")

    levels = Counter()
    for inst in instances:
        levels[inst.get("level", "?")] += 1
    print(f"  By level: {dict(levels)}")

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    synthetic_instances = []
    for idx, inst in enumerate(instances):
        try:
            syn = generate_synthetic_for_instance(inst, idx)
            synthetic_instances.append(syn)
        except Exception as e:
            print(f"  Warning: failed on instance {idx}: {e}")

    with open(_OUTPUT_DIR / "synthetic_instances.json", "w") as f:
        json.dump({
            "metadata": {
                "name": "DeFAb Synthetic Contamination Control Instances",
                "total": len(synthetic_instances),
                "matched_to": "Tier 0 evaluation instances",
            },
            "instances": synthetic_instances,
        }, f, indent=2)

    syn_levels = Counter()
    for s in synthetic_instances:
        syn_levels[s["level"]] += 1

    print(f"\nGenerated {len(synthetic_instances)} synthetic instances")
    print(f"  By level: {dict(syn_levels)}")
    print(f"  Saved to {_OUTPUT_DIR / 'synthetic_instances.json'}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
