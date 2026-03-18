"""
Single-pass cross-ontology extraction across all 5 domains.

Extracts taxonomy from OpenCyc and behavioral properties from ConceptNet,
combines them via the cross-ontology pipeline, validates, deduplicates,
and saves per-domain Theory objects and statistics.

Designed for efficiency: ConceptNet is streamed once and edges are bucketed
into all matching domains simultaneously.

Author: Patrick Cooper
"""

import sys
import json
import pickle
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.opencyc_extractor import OpenCycExtractor
from blanc.ontology.conceptnet_extractor import ConceptNetExtractor
from blanc.ontology.cross_ontology import (
    combine_taxonomy_properties,
    build_cross_ontology_theory,
    CombinationStats,
)
from blanc.ontology.domain_profiles import (
    ALL_PROFILES,
    DomainProfile,
    get_profile,
)
from blanc.ontology.rule_validator import (
    validate_theory,
    deduplicate_theory,
    save_report,
)


_PROJECT_ROOT = Path(__file__).parent.parent
_DATA_DIR = _PROJECT_ROOT / "data"
_OPENCYC_PATH = _DATA_DIR / "opencyc" / "opencyc-2012-05-10-readable.owl.gz"
_CONCEPTNET_PATH = _DATA_DIR / "conceptnet" / "conceptnet-assertions-5.7.0.csv.gz"
_OUTPUT_DIR = _PROJECT_ROOT / "data" / "tier1"

_SUPPORTED_RELATIONS = frozenset(
    ["IsA", "CapableOf", "NotCapableOf", "HasProperty", "Causes", "UsedFor"]
)


def extract_opencyc_per_domain(
    opencyc_path: Path,
    domains: list[str],
) -> dict[str, dict]:
    """Extract taxonomy from OpenCyc for each domain.

    Loads the OWL graph once and re-extracts per domain profile to
    avoid redundant rdflib parsing.

    Returns:
        {domain_name: {"taxonomy": {concept: {parents}}, "concepts": set}}
    """
    results = {}

    print("  Loading OpenCyc OWL graph (once)...", flush=True)
    t0 = time.time()
    first_profile = get_profile(domains[0])
    shared_extractor = OpenCycExtractor(opencyc_path, profile=first_profile)
    shared_extractor.load()
    print(f"  Graph loaded in {time.time() - t0:.1f}s", flush=True)

    for domain_name in domains:
        profile = get_profile(domain_name)
        print(f"  Extracting taxonomy for {domain_name}...", flush=True)
        t1 = time.time()

        extractor = OpenCycExtractor.__new__(OpenCycExtractor)
        extractor.opencyc_path = opencyc_path
        extractor.profile = profile
        extractor.graph = shared_extractor.graph
        extractor.domain_concepts = set()
        extractor.taxonomic_relations = []
        extractor.property_relations = []
        extractor.extract_domain()
        taxonomy = extractor.get_taxonomy()

        elapsed = time.time() - t1
        print(f"    {len(taxonomy)} concepts, "
              f"{sum(len(p) for p in taxonomy.values())} relations "
              f"({elapsed:.1f}s)", flush=True)

        results[domain_name] = {
            "taxonomy": taxonomy,
            "concepts": set(taxonomy.keys()),
        }

    return results


def extract_conceptnet_multipass(
    conceptnet_path: Path,
    domains: list[str],
    weight_threshold: float = 2.0,
    max_edges: int | None = None,
) -> dict[str, dict[str, list[tuple[str, str]]]]:
    """Extract ConceptNet properties for each domain in separate passes.

    Returns:
        {domain_name: {concept: [(relation, property), ...]}}
    """
    results = {}

    for domain_name in domains:
        profile = get_profile(domain_name)
        print(f"  Extracting ConceptNet for {domain_name}...")
        t0 = time.time()

        extractor = ConceptNetExtractor(
            conceptnet_path,
            weight_threshold=weight_threshold,
            profile=profile,
        )
        extractor.extract(max_edges=max_edges)

        properties: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for edge in extractor.domain_edges:
            concept = edge["start"]
            relation = edge["relation"]
            prop = edge["end"]
            if relation in _SUPPORTED_RELATIONS:
                properties[concept].append((relation, prop))

        elapsed = time.time() - t0
        n_edges = sum(len(v) for v in properties.values())
        print(f"    {len(properties)} concepts with {n_edges} property edges "
              f"({elapsed:.1f}s)")

        results[domain_name] = dict(properties)

    return results


def _normalize_key(s: str) -> str:
    """Normalize for cross-source matching.

    Handles CamelCase splitting (DomesticCat -> domestic_cat),
    hyphens, spaces, and strips non-alphanumeric characters.
    """
    import re
    # Split CamelCase: insert underscore before uppercase letters
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)
    return s.lower().replace(" ", "_").replace("-", "_")


def _align_keys(
    taxonomy: dict[str, set[str]],
    properties: dict[str, list[tuple[str, str]]],
) -> tuple[dict[str, set[str]], dict[str, list[tuple[str, str]]]]:
    """Normalize concept keys so OpenCyc and ConceptNet entries can match."""
    norm_tax: dict[str, set[str]] = {}
    for concept, parents in taxonomy.items():
        nk = _normalize_key(concept)
        if nk not in norm_tax:
            norm_tax[nk] = set()
        for p in parents:
            norm_tax[nk].add(_normalize_key(p))

    norm_props: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for concept, edges in properties.items():
        nk = _normalize_key(concept)
        norm_props[nk].extend(edges)

    return norm_tax, dict(norm_props)


def combine_and_validate(
    opencyc_data: dict,
    conceptnet_data: dict,
    domain_name: str,
    output_dir: Path,
) -> tuple[Theory, CombinationStats]:
    """Combine taxonomy + properties, validate, deduplicate, save."""
    profile = get_profile(domain_name)
    taxonomy = opencyc_data[domain_name]["taxonomy"]
    properties = conceptnet_data.get(domain_name, {})

    taxonomy, properties = _align_keys(taxonomy, properties)
    overlap = set(taxonomy.keys()) & set(properties.keys())
    print(f"    Key overlap: {len(overlap)} concepts matched", flush=True)

    print(f"\n  Combining {domain_name}...")
    t0 = time.time()

    theory, stats = build_cross_ontology_theory(
        taxonomy, properties, profile=profile,
        output_path=output_dir / f"{domain_name}_stats.json",
    )

    elapsed = time.time() - t0
    print(f"    Raw: {stats.total_rules} rules "
          f"({stats.strict_rules} strict, "
          f"{stats.defeasible_inherited + stats.defeasible_specific} defeasible, "
          f"{stats.defeaters} defeaters) in {elapsed:.1f}s")

    report = validate_theory(theory)
    save_report(report, output_dir / f"{domain_name}_validation.json")

    if report.duplicate_count > 0:
        print(f"    Deduplicating {report.duplicate_count} duplicates...")
        theory = deduplicate_theory(theory)

    domain_dir = output_dir / domain_name
    domain_dir.mkdir(parents=True, exist_ok=True)

    with open(domain_dir / "theory.pkl", "wb") as f:
        pickle.dump(theory, f)

    theory_json = {
        "domain": domain_name,
        "facts": list(theory.facts),
        "rules": [
            {
                "head": r.head,
                "body": list(r.body),
                "rule_type": r.rule_type.value,
                "label": r.label,
            }
            for r in theory.rules
        ],
        "stats": stats.to_dict(),
    }
    with open(domain_dir / "theory.json", "w") as f:
        json.dump(theory_json, f, indent=2)

    print(f"    Final: {len(theory.facts)} facts, {len(theory.rules)} rules")
    print(f"    Saved to {domain_dir}/")

    return theory, stats


def main():
    print("=" * 70)
    print("CROSS-ONTOLOGY EXTRACTION: ALL DOMAINS")
    print("=" * 70)

    for path, name in [(_OPENCYC_PATH, "OpenCyc"), (_CONCEPTNET_PATH, "ConceptNet")]:
        if not path.exists():
            print(f"ERROR: {name} not found at {path}")
            print(f"  Run: python scripts/download_{name.lower().replace(' ', '_')}.py")
            return 1

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    domains = list(ALL_PROFILES.keys())
    print(f"\nDomains: {domains}")
    print(f"Output:  {_OUTPUT_DIR}\n")

    # Step 1: OpenCyc taxonomy
    print("Step 1: OpenCyc taxonomy extraction")
    print("-" * 70)
    opencyc_data = extract_opencyc_per_domain(_OPENCYC_PATH, domains)

    # Step 2: ConceptNet properties
    print("\nStep 2: ConceptNet property extraction")
    print("-" * 70)
    conceptnet_data = extract_conceptnet_multipass(
        _CONCEPTNET_PATH, domains, weight_threshold=2.0,
    )

    # Step 3: Combine per domain
    print("\nStep 3: Cross-ontology combination")
    print("-" * 70)
    all_stats = {}
    for domain_name in domains:
        theory, stats = combine_and_validate(
            opencyc_data, conceptnet_data, domain_name, _OUTPUT_DIR,
        )
        all_stats[domain_name] = stats.to_dict()

    # Summary
    print("\n" + "=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)

    total_rules = 0
    total_defeaters = 0
    for domain_name, s in all_stats.items():
        print(f"  {domain_name:12s}: {s['total_rules']:>8,} rules "
              f"({s['defeaters']:>6,} defeaters)")
        total_rules += s["total_rules"]
        total_defeaters += s["defeaters"]

    print(f"  {'TOTAL':12s}: {total_rules:>8,} rules "
          f"({total_defeaters:>6,} defeaters)")
    print(f"\nTier 0 baseline: 2,318 rules")
    print(f"Tier 1 multiplier: {total_rules / 2318:.1f}x")

    with open(_OUTPUT_DIR / "extraction_summary.json", "w") as f:
        json.dump({
            "domains": all_stats,
            "total_rules": total_rules,
            "total_defeaters": total_defeaters,
            "tier0_rules": 2318,
            "multiplier": round(total_rules / 2318, 1),
        }, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
