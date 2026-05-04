"""
UMLS subsampled instance generation for CURC HPC.

The full UMLS theory has 29.5M rules -- far too large to partition as a
single theory. This script samples connected subgraphs of manageable size
(100--500 rules) by traversing the CUI relation graph, then generates
instances from each subgraph using the standard pipeline.

Designed for CURC Alpine amilan partition (128GB RAM, 32--48 CPUs).

Author: Anonymous Authors
"""

import json
import multiprocessing as mp
import pickle
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType

_PROJECT_ROOT = Path(__file__).parent.parent
_THEORY_PATH = _PROJECT_ROOT / "data" / "extracted" / "umls" / "theory.pkl"
_OUTPUT_DIR = _PROJECT_ROOT / "instances" / "multitier" / "umls"

MAX_SUBGRAPH_RULES = 300
MIN_SUBGRAPH_RULES = 10
NUM_SUBGRAPHS = 500
MAX_INSTANCES_TOTAL = 200000
SEED = 42


def build_cui_adjacency(theory):
    """Build a CUI-to-CUI adjacency list from rule heads.

    Each rule head like ``treats(cui_c0000001, cui_c0000002)`` creates
    an edge between the two CUIs. This lets us sample connected subgraphs.
    """
    adj = defaultdict(set)
    cui_rules = defaultdict(list)

    for r in theory.rules:
        head = r.head.lstrip("~")
        if "(" not in head:
            continue
        args = head.split("(", 1)[1].rstrip(")")
        parts = [a.strip() for a in args.split(",")]
        cuis = [p for p in parts if p.startswith("cui_")]

        if cuis:
            primary = cuis[0]
            cui_rules[primary].append(r)
            for c in cuis[1:]:
                adj[primary].add(c)
                adj[c].add(primary)
                cui_rules[c].append(r)

    return dict(adj), dict(cui_rules)


def sample_subgraph(start_cui, adj, cui_rules, max_rules):
    """BFS from a seed CUI, collecting rules until we hit the size cap."""
    visited = set()
    queue = [start_cui]
    collected_rules = []
    collected_facts = set()

    while queue and len(collected_rules) < max_rules:
        cui = queue.pop(0)
        if cui in visited:
            continue
        visited.add(cui)

        for r in cui_rules.get(cui, []):
            if len(collected_rules) >= max_rules:
                break
            collected_rules.append(r)
            for b in r.body:
                collected_facts.add(b)

        collected_facts.add(f"umls_concept({cui})")

        for neighbor in adj.get(cui, set()):
            if neighbor not in visited:
                queue.append(neighbor)

    return collected_rules, collected_facts


def generate_from_subgraph(args):
    """Worker function for multiprocessing."""
    idx, rules, facts = args

    from scripts.generate_tier1_instances import generate_from_subtheory

    sub = Theory()
    for r in rules:
        sub.add_rule(r)
    for f in facts:
        sub.add_fact(f)

    try:
        instances = generate_from_subtheory(sub, idx, "umls")
        return instances
    except Exception as e:
        return []


def main():
    print("=" * 70, flush=True)
    print("UMLS SUBSAMPLED INSTANCE GENERATION", flush=True)
    print("=" * 70, flush=True)

    print(f"Loading UMLS theory from {_THEORY_PATH}...", flush=True)
    t0 = time.time()
    with open(_THEORY_PATH, "rb") as f:
        theory = pickle.load(f)
    print(f"  Loaded in {time.time() - t0:.0f}s: {len(theory.rules)} rules, {len(theory.facts)} facts", flush=True)

    print("Building CUI adjacency graph...", flush=True)
    t0 = time.time()
    adj, cui_rules = build_cui_adjacency(theory)
    print(f"  {len(cui_rules)} CUIs with rules, {sum(len(v) for v in adj.values())} edges in {time.time() - t0:.0f}s", flush=True)

    defeasible_cuis = []
    for cui, rules in cui_rules.items():
        n_def = sum(1 for r in rules if r.rule_type == RuleType.DEFEASIBLE and r.body)
        if n_def >= 3:
            defeasible_cuis.append(cui)

    print(f"  CUIs with 3+ defeasible body-bearing rules: {len(defeasible_cuis)}", flush=True)

    rng = random.Random(SEED)
    rng.shuffle(defeasible_cuis)
    seed_cuis = defeasible_cuis[:NUM_SUBGRAPHS]

    print(f"\nSampling {len(seed_cuis)} subgraphs (max {MAX_SUBGRAPH_RULES} rules each)...", flush=True)
    subgraphs = []
    used_rules = set()
    t0 = time.time()

    for i, cui in enumerate(seed_cuis):
        rules, facts = sample_subgraph(cui, adj, cui_rules, MAX_SUBGRAPH_RULES)
        new_rules = [r for r in rules if id(r) not in used_rules]
        if len(new_rules) < MIN_SUBGRAPH_RULES:
            continue
        for r in new_rules:
            used_rules.add(id(r))
        subgraphs.append((i, new_rules, facts))

        if (i + 1) % 100 == 0:
            print(f"  Sampled {i + 1}/{len(seed_cuis)} seeds, {len(subgraphs)} valid subgraphs, {len(used_rules)} unique rules", flush=True)

    print(f"  Final: {len(subgraphs)} subgraphs, {len(used_rules)} unique rules in {time.time() - t0:.0f}s", flush=True)

    sizes = [len(sg[1]) for sg in subgraphs]
    if sizes:
        print(f"  Subgraph sizes: min={min(sizes)}, max={max(sizes)}, median={sorted(sizes)[len(sizes)//2]}", flush=True)

    n_workers = min(mp.cpu_count(), 32)
    print(f"\nGenerating instances with {n_workers} workers...", flush=True)
    t0 = time.time()

    all_instances = []
    batch_size = 50

    for batch_start in range(0, len(subgraphs), batch_size):
        batch = subgraphs[batch_start:batch_start + batch_size]

        with mp.Pool(n_workers) as pool:
            results = pool.map(generate_from_subgraph, batch)

        for inst_list in results:
            all_instances.extend(inst_list)

        elapsed = time.time() - t0
        print(f"  Batch {batch_start // batch_size + 1}: {len(all_instances)} total instances ({elapsed:.0f}s)", flush=True)

        if len(all_instances) >= MAX_INSTANCES_TOTAL:
            print(f"  Reached instance cap ({MAX_INSTANCES_TOTAL}), stopping.", flush=True)
            all_instances = all_instances[:MAX_INSTANCES_TOTAL]
            break

    elapsed = time.time() - t0
    print(f"\nGeneration complete: {len(all_instances)} instances in {elapsed:.0f}s", flush=True)

    l1 = sum(1 for x in all_instances if x.get("level") == 1)
    l2 = sum(1 for x in all_instances if x.get("level") == 2)
    l3 = sum(1 for x in all_instances if x.get("level") == 3)
    print(f"  L1={l1}, L2={l2}, L3={l3}", flush=True)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _OUTPUT_DIR / "instances.json"
    with open(out_path, "w") as f:
        json.dump(all_instances, f)
    print(f"  Saved to {out_path} ({out_path.stat().st_size / 1024 / 1024:.1f} MB)", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
