"""
Tier 1 instance generation from cross-ontology extracted theories.

Partitions large theories into manageable sub-theories by taxonomy
subtree, then generates Level 1, 2, and 3 instances from each using
all 13 partition strategies. Uses multiprocessing for parallelism.

Author: Anonymous Authors
"""

import sys
import json
import pickle
import time
import random
import multiprocessing as mp
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality, _remove_element
from blanc.author.generation import (
    AbductiveInstance,
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
from blanc.reasoning.defeasible import defeasible_provable


_PROJECT_ROOT = Path(__file__).parent.parent
_TIER1_DIR = _PROJECT_ROOT / "data" / "tier1"
_OUTPUT_DIR = _PROJECT_ROOT / "instances" / "tier1"

MAX_SUBTHEORY_SIZE = 80
MIN_SUBTHEORY_SIZE = 2
MAX_INSTANCES_PER_PARTITION = 8
MAX_TARGETS_PER_SUBTHEORY = 15
MAX_L3_PER_SUBTHEORY = 3
HARD_CAP_RULES = 100
MAX_ABLATION_ATTEMPTS = 30
MAX_FACTS_PER_SUBTHEORY = 200


def partition_into_subtheories(theory: Theory) -> list[Theory]:
    """Split a large theory into sub-theories by taxonomy subtree.

    Groups rules by the primary concept in their body predicate,
    creating sub-theories of manageable size for criticality computation.
    """
    concept_rules: dict[str, list[Rule]] = defaultdict(list)
    concept_facts: dict[str, set[str]] = defaultdict(set)

    for rule in theory.rules:
        if rule.body:
            body_pred = rule.body[0].split("(")[0].lstrip("~")
            concept_rules[body_pred].append(rule)
        else:
            head_pred = rule.head.split("(")[0].lstrip("~")
            concept_rules[head_pred].append(rule)

    for fact in theory.facts:
        pred = fact.split("(")[0]
        concept_facts[pred].add(fact)

    groups: list[tuple[str, list[Rule], set[str]]] = []
    for concept, rules in concept_rules.items():
        facts = concept_facts.get(concept, set())
        all_facts = set(facts)
        for r in rules:
            for b in r.body:
                pred = b.split("(")[0].lstrip("~")
                all_facts |= concept_facts.get(pred, set())
        groups.append((concept, rules, all_facts))

    groups.sort(key=lambda g: len(g[1]), reverse=True)

    subtheories: list[Theory] = []
    current_rules: list[Rule] = []
    current_facts: set[str] = set()
    current_name = ""

    for concept, rules, facts in groups:
        if len(rules) < MIN_SUBTHEORY_SIZE:
            current_rules.extend(rules)
            current_facts |= facts
            if len(current_rules) >= MAX_SUBTHEORY_SIZE:
                st = Theory()
                for f in current_facts:
                    st.add_fact(f)
                for r in current_rules:
                    st.add_rule(r)
                if len(st.rules) >= MIN_SUBTHEORY_SIZE:
                    subtheories.append(st)
                current_rules = []
                current_facts = set()
            continue

        if len(rules) > MAX_SUBTHEORY_SIZE:
            for i in range(0, len(rules), MAX_SUBTHEORY_SIZE):
                chunk = rules[i : i + MAX_SUBTHEORY_SIZE]
                st = Theory()
                for f in facts:
                    st.add_fact(f)
                for r in chunk:
                    st.add_rule(r)
                    for b in r.body:
                        pred = b.split("(")[0].lstrip("~")
                        for cf in concept_facts.get(pred, set()):
                            st.add_fact(cf)
                if len(st.rules) >= MIN_SUBTHEORY_SIZE:
                    subtheories.append(st)
            continue

        if len(current_rules) + len(rules) > MAX_SUBTHEORY_SIZE and current_rules:
            st = Theory()
            for f in current_facts:
                st.add_fact(f)
            for r in current_rules:
                st.add_rule(r)
            if len(st.rules) >= MIN_SUBTHEORY_SIZE:
                subtheories.append(st)
            current_rules = []
            current_facts = set()

        current_rules.extend(rules)
        current_facts |= facts

    if current_rules:
        st = Theory()
        for f in current_facts:
            st.add_fact(f)
        for r in current_rules:
            st.add_rule(r)
        if len(st.rules) >= MIN_SUBTHEORY_SIZE:
            subtheories.append(st)

    # Hard cap: break any oversized sub-theories into manageable chunks
    final = []
    for st in subtheories:
        if len(st.rules) <= HARD_CAP_RULES:
            final.append(st)
        else:
            rules_list = list(st.rules)
            for i in range(0, len(rules_list), HARD_CAP_RULES):
                chunk = rules_list[i : i + HARD_CAP_RULES]
                sub = Theory()
                for r in chunk:
                    sub.add_rule(r)
                # Only include facts referenced by this chunk's rules
                _add_relevant_facts(sub, st.facts)
                if len(sub.rules) >= MIN_SUBTHEORY_SIZE:
                    final.append(sub)

    # For sub-theories containing defeaters, pull in rules that derive
    # the defeated predicate so that anomalies are actually derivable.
    all_rules_by_head: dict[str, list[Rule]] = defaultdict(list)
    for r in theory.rules:
        hp = r.head.split("(")[0].lstrip("~")
        all_rules_by_head[hp].append(r)

    enriched = []
    all_facts = set(theory.facts)
    for st in final:
        defeaters = [r for r in st.rules if r.rule_type == RuleType.DEFEATER]
        if defeaters:
            needed_preds = {d.head.split("(")[0].lstrip("~") for d in defeaters}
            for pred in needed_preds:
                for r in all_rules_by_head.get(pred, []):
                    if r not in st.rules:
                        st.add_rule(r)

        trimmed_st = Theory()
        for r in st.rules:
            trimmed_st.add_rule(r)
        _add_relevant_facts(trimmed_st, all_facts)
        if len(trimmed_st.rules) >= MIN_SUBTHEORY_SIZE:
            enriched.append(trimmed_st)

    return enriched


def _add_relevant_facts(theory: Theory, all_facts: set[str]) -> None:
    """Add only facts whose predicate appears in the theory's rules, with cap."""
    rule_preds = set()
    for r in theory.rules:
        rule_preds.add(r.head.split("(")[0].lstrip("~"))
        for b in r.body:
            rule_preds.add(b.split("(")[0].lstrip("~"))
    added = 0
    for fact in all_facts:
        if added >= MAX_FACTS_PER_SUBTHEORY:
            break
        pred = fact.split("(")[0]
        if pred in rule_preds:
            theory.add_fact(fact)
            added += 1


def get_partition_strategies(theory: Theory) -> list[tuple[str, object]]:
    """Build all 13 partition strategies for a theory."""
    strategies = []
    strategies.append(("leaf", partition_leaf))
    strategies.append(("rule", partition_rule))

    try:
        depths_map = compute_dependency_depths(theory)
        for k in [1, 2, 3]:
            strategies.append((f"depth_{k}", partition_depth(k, depths_map)))
    except Exception:
        pass

    for delta_int in range(1, 10):
        delta = delta_int / 10.0
        strategies.append((f"rand_{delta:.1f}", partition_random(delta, seed=42)))

    return strategies


def _forward_chain(theory: Theory) -> set[str]:
    """Fast forward-chaining derivation (no defeat checking).

    Computes all ground literals derivable by repeatedly applying
    rules whose bodies are satisfied. Much faster than the full
    defeasible proof procedure for target discovery.
    """
    derived = set(theory.facts)
    changed = True
    iterations = 0
    while changed and iterations < 20:
        changed = False
        iterations += 1
        for rule in theory.rules:
            if rule.rule_type == RuleType.DEFEATER:
                continue
            if not rule.body:
                if rule.head not in derived:
                    derived.add(rule.head)
                    changed = True
                continue
            # Try to match body against derived facts
            if len(rule.body) == 1:
                body_pred = rule.body[0].split("(")[0]
                body_var = rule.body[0].split("(")[1].rstrip(")") if "(" in rule.body[0] else ""
                head_pred = rule.head.split("(")[0].lstrip("~")
                if body_var == "X":
                    for d in list(derived):
                        dp = d.split("(")[0]
                        if dp == body_pred:
                            arg = d.split("(")[1].rstrip(")") if "(" in d else ""
                            new = f"{head_pred}({arg})"
                            if new not in derived:
                                derived.add(new)
                                changed = True
    return derived


def _find_derived_targets(theory: Theory) -> list[str]:
    """Find conclusions derivable through rule chains, not bare facts."""
    all_derived = _forward_chain(theory)
    fact_set = set(theory.facts)
    # Targets = derived conclusions that are NOT bare facts
    targets = [t for t in all_derived if t not in fact_set]
    random.shuffle(targets)
    return targets[:MAX_TARGETS_PER_SUBTHEORY]


def _find_critical_by_ablation(
    theory: Theory, target: str, element_type: str,
) -> Optional[object]:
    """Find a critical element by random ablation (fast path).

    Instead of computing full Crit*(D, q), randomly try removing
    elements until we find one that breaks derivability.
    """
    if element_type == "rule":
        candidates = [
            r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE
        ]
    else:
        candidates = list(theory.facts)

    random.shuffle(candidates)
    for elem in candidates[:MAX_ABLATION_ATTEMPTS]:
        try:
            reduced = _remove_element(theory, elem)
            if not defeasible_provable(reduced, target):
                return elem
        except Exception:
            continue
    return None


def generate_from_subtheory(
    subtheory: Theory,
    subtheory_idx: int,
    domain: str,
) -> list[dict]:
    """Generate L1, L2, and L3 instances from a single sub-theory.

    Uses fast ablation instead of full_theory_criticality.
    """
    instances = []
    strategies = get_partition_strategies(subtheory)

    for strat_name, partition_fn in strategies:
        try:
            converted = phi_kappa(subtheory, partition_fn)
        except Exception:
            continue

        # Find DERIVED conclusions (rule heads instantiated with known entities)
        # not bare facts, since facts don't depend on rules.
        derivable_targets = _find_derived_targets(converted)
        if not derivable_targets:
            continue

        l1_count = 0
        l2_count = 0

        for target in derivable_targets:
            if l2_count >= MAX_INSTANCES_PER_PARTITION and l1_count >= MAX_INSTANCES_PER_PARTITION:
                break

            if l2_count < MAX_INSTANCES_PER_PARTITION:
                crit_rule = _find_critical_by_ablation(converted, target, "rule")
                if crit_rule is not None:
                    try:
                        inst = generate_level2_instance(
                            converted, target, crit_rule,
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        d = inst.to_dict()
                        d["domain"] = domain
                        d["partition"] = strat_name
                        d["subtheory_idx"] = subtheory_idx
                        instances.append(d)
                        l2_count += 1
                    except Exception:
                        pass

            if l1_count < MAX_INSTANCES_PER_PARTITION:
                crit_fact = _find_critical_by_ablation(converted, target, "fact")
                if crit_fact is not None:
                    try:
                        inst = generate_level1_instance(
                            converted, target, crit_fact,
                            k_distractors=5, distractor_strategy="syntactic",
                        )
                        d = inst.to_dict()
                        d["domain"] = domain
                        d["partition"] = strat_name
                        d["subtheory_idx"] = subtheory_idx
                        instances.append(d)
                        l1_count += 1
                    except Exception:
                        pass

    # Level 3: from defeaters grounded with concrete entities
    defeaters = [r for r in subtheory.rules if r.rule_type == RuleType.DEFEATER]
    l3_count = 0

    for defeater in defeaters:
        if l3_count >= MAX_L3_PER_SUBTHEORY:
            break
        if not defeater.body:
            continue

        head_pred = defeater.head.lstrip("~").split("(")[0]
        body_pred = defeater.body[0].split("(")[0]

        # Find concrete entities from facts that match the body predicate
        matching_entities = []
        for fact in subtheory.facts:
            fp = fact.split("(")[0]
            if fp == body_pred and "(" in fact:
                ent = fact.split("(", 1)[1].rstrip(")")
                if ent and ent != "X" and "," not in ent:
                    matching_entities.append(ent)

        for entity in matching_entities[:3]:
            if l3_count >= MAX_L3_PER_SUBTHEORY:
                break
            anomaly = f"{head_pred}({entity})"
            try:
                inst = generate_level3_instance(
                    subtheory, anomaly, defeater, k_distractors=5,
                )
                d = inst.to_dict()
                d["domain"] = domain
                d["partition"] = "type_grounded"
                d["subtheory_idx"] = subtheory_idx
                instances.append(d)
                l3_count += 1
            except (ValueError, Exception):
                continue

    return instances


def _worker(args):
    """Multiprocessing worker for sub-theory generation."""
    subtheory, idx, domain = args
    try:
        return generate_from_subtheory(subtheory, idx, domain)
    except Exception as e:
        print(f"  Worker error on subtheory {idx}: {e}")
        return []


def generate_domain(domain: str, theory: Theory) -> list[dict]:
    """Generate all instances for a single domain."""
    print(f"\n{'=' * 70}")
    print(f"GENERATING: {domain.upper()}")
    print(f"{'=' * 70}")
    print(f"  Theory: {len(theory.facts)} facts, {len(theory.rules)} rules")

    subtheories = partition_into_subtheories(theory)
    print(f"  Sub-theories: {len(subtheories)}")
    if subtheories:
        sizes = [len(st.rules) for st in subtheories]
        print(f"  Size range: {min(sizes)}-{max(sizes)} rules "
              f"(median {sorted(sizes)[len(sizes)//2]})")

    all_instances = []
    t0 = time.time()

    n_workers = max(1, mp.cpu_count() - 1)
    work_items = [(st, i, domain) for i, st in enumerate(subtheories)]

    if len(work_items) > 1 and n_workers > 1:
        print(f"  Using {n_workers} workers...")
        with mp.Pool(n_workers) as pool:
            results = pool.map(_worker, work_items)
        for batch in results:
            all_instances.extend(batch)
    else:
        for st, idx, dom in work_items:
            batch = generate_from_subtheory(st, idx, dom)
            all_instances.extend(batch)

    elapsed = time.time() - t0
    l1 = sum(1 for i in all_instances if i["level"] == 1)
    l2 = sum(1 for i in all_instances if i["level"] == 2)
    l3 = sum(1 for i in all_instances if i["level"] == 3)
    print(f"  Generated: {len(all_instances)} instances "
          f"(L1={l1}, L2={l2}, L3={l3}) in {elapsed:.1f}s")

    return all_instances


def main():
    print("=" * 70)
    print("TIER 1 INSTANCE GENERATION")
    print("=" * 70)

    if not _TIER1_DIR.exists():
        print(f"ERROR: Tier 1 data not found at {_TIER1_DIR}")
        print("  Run: python scripts/extract_cross_ontology_all.py")
        return 1

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    domains = [
        d.name for d in _TIER1_DIR.iterdir()
        if d.is_dir() and (d / "theory.pkl").exists()
    ]
    if not domains:
        print("ERROR: No domain theories found in tier1 data")
        return 1

    print(f"Domains found: {domains}")

    all_instances = []
    domain_stats = {}

    for domain in domains:
        theory_path = _TIER1_DIR / domain / "theory.pkl"
        with open(theory_path, "rb") as f:
            theory = pickle.load(f)

        instances = generate_domain(domain, theory)

        domain_dir = _OUTPUT_DIR / domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        with open(domain_dir / "instances.json", "w") as f:
            json.dump(instances, f, indent=2)

        l1 = sum(1 for i in instances if i["level"] == 1)
        l2 = sum(1 for i in instances if i["level"] == 2)
        l3 = sum(1 for i in instances if i["level"] == 3)
        domain_stats[domain] = {"total": len(instances), "L1": l1, "L2": l2, "L3": l3}
        all_instances.extend(instances)

    # Summary
    print(f"\n{'=' * 70}")
    print("GENERATION COMPLETE")
    print(f"{'=' * 70}")

    total = {"L1": 0, "L2": 0, "L3": 0, "total": 0}
    for domain, s in domain_stats.items():
        print(f"  {domain:12s}: {s['total']:>6,} instances "
              f"(L1={s['L1']}, L2={s['L2']}, L3={s['L3']})")
        for k in total:
            total[k] += s[k]

    print(f"  {'TOTAL':12s}: {total['total']:>6,} instances "
          f"(L1={total['L1']}, L2={total['L2']}, L3={total['L3']})")

    with open(_OUTPUT_DIR / "all_instances.json", "w") as f:
        json.dump(all_instances, f)

    summary = {
        "total_instances": total["total"],
        "level_breakdown": total,
        "domain_breakdown": domain_stats,
        "tier0_instances": 409,
        "multiplier": round(total["total"] / 409, 1) if total["total"] else 0,
    }
    with open(_OUTPUT_DIR / "generation_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nTier 0 baseline: 409 instances")
    print(f"Tier 1 total:    {total['total']:,} instances")
    print(f"Multiplier:      {total['total'] / 409:.1f}x" if total['total'] else "")

    return 0


if __name__ == "__main__":
    mp.set_start_method("spawn", force=True)
    sys.exit(main())
