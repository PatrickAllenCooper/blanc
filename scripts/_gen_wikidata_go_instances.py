"""Generate instances from fixed Wikidata and Gene Ontology theories.

Handles these sources separately from the full multitier script
to avoid the 409K-rule GO partitioning bottleneck. Uses smaller
sub-samples for GO.

Author: Patrick Cooper
"""

import sys
import json
import pickle
import time
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType
from scripts.generate_tier1_instances import generate_from_subtheory

_PROJECT_ROOT = Path(__file__).parent.parent
_EXTRACTED_DIR = _PROJECT_ROOT / "data" / "extracted"
_OUTPUT_DIR = _PROJECT_ROOT / "instances" / "multitier"

MAX_RULES_PER_BATCH = 200


def generate_from_source(source_name: str, max_batches: int = 50):
    theory_path = _EXTRACTED_DIR / source_name / "theory.pkl"
    if not theory_path.exists():
        print(f"  [SKIP] {source_name}: no theory.pkl")
        return []

    with open(theory_path, "rb") as f:
        theory = pickle.load(f)

    print(f"  {source_name}: {len(theory.rules)} rules, {len(theory.facts)} facts")

    defeasible = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE and r.body]
    defeaters = [r for r in theory.rules if r.rule_type == RuleType.DEFEATER and r.body]
    strict = [r for r in theory.rules if r.rule_type == RuleType.STRICT]

    print(f"    Defeasible with body: {len(defeasible)}")
    print(f"    Defeaters with body: {len(defeaters)}")
    print(f"    Strict: {len(strict)}")

    if not defeasible:
        print(f"    [SKIP] No defeasible rules with bodies")
        return []

    random.seed(42)
    random.shuffle(defeasible)

    all_instances = []
    batch_count = 0

    for i in range(0, len(defeasible), MAX_RULES_PER_BATCH):
        if batch_count >= max_batches:
            break

        batch_rules = defeasible[i:i + MAX_RULES_PER_BATCH]

        sub = Theory()
        for r in batch_rules:
            sub.add_rule(r)
            for b in r.body:
                sub.add_fact(b)

        for r in defeaters:
            body_arg = r.body[0].split("(")[1].rstrip(")") if "(" in r.body[0] else ""
            for fact in sub.facts:
                if body_arg and body_arg in fact:
                    sub.add_rule(r)
                    for b in r.body:
                        sub.add_fact(b)
                    break

        if len(sub.rules) < 2:
            continue

        try:
            instances = generate_from_subtheory(sub, batch_count, source_name)
            all_instances.extend(instances)
            batch_count += 1
            if batch_count % 10 == 0:
                print(f"    Batch {batch_count}: {len(all_instances)} instances so far", flush=True)
        except Exception as e:
            print(f"    Batch {batch_count} error: {e}")
            batch_count += 1

    return all_instances


def main():
    print("=" * 60, flush=True)
    print("WIKIDATA + GO INSTANCE GENERATION", flush=True)
    print("=" * 60, flush=True)

    for source in ["wikidata", "gene_ontology"]:
        print(f"\n--- {source} ---", flush=True)
        t0 = time.time()

        if source == "gene_ontology":
            instances = generate_from_source(source, max_batches=100)
        else:
            instances = generate_from_source(source, max_batches=50)

        elapsed = time.time() - t0

        out_dir = _OUTPUT_DIR / source
        out_dir.mkdir(parents=True, exist_ok=True)
        with open(out_dir / "instances.json", "w") as f:
            json.dump(instances, f)

        l1 = sum(1 for i in instances if i.get("level") == 1)
        l2 = sum(1 for i in instances if i.get("level") == 2)
        l3 = sum(1 for i in instances if i.get("level") == 3)
        print(f"  Generated {len(instances)} instances in {elapsed:.1f}s")
        print(f"  L1={l1}, L2={l2}, L3={l3}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
