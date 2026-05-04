"""
Master extraction script for all knowledge source tiers.

Runs each extractor, validates, saves per-source Theory objects,
and produces a cumulative summary.

Usage:
    python scripts/extract_all_tiers.py [--sources nell,sumo,go,mesh,framenet,yago,wikidata]

Author: Anonymous Authors
"""

import sys
import json
import pickle
import time
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, RuleType
from blanc.ontology.rule_validator import validate_theory, deduplicate_theory, save_report

_PROJECT_ROOT = Path(__file__).parent.parent
_OUTPUT_DIR = _PROJECT_ROOT / "data" / "extracted"

ALL_SOURCES = ["nell", "sumo", "go", "mesh", "framenet", "yago", "wikidata"]


def _save_theory(theory: Theory, name: str, output_dir: Path) -> dict:
    """Validate, deduplicate, and save a theory. Returns stats dict."""
    source_dir = output_dir / name
    source_dir.mkdir(parents=True, exist_ok=True)

    report = validate_theory(theory)
    save_report(report, source_dir / "validation.json")

    if report.duplicate_count > 0:
        print(f"    Deduplicating {report.duplicate_count} duplicates...", flush=True)
        theory = deduplicate_theory(theory)

    with open(source_dir / "theory.pkl", "wb") as f:
        pickle.dump(theory, f)

    strict = sum(1 for r in theory.rules if r.rule_type == RuleType.STRICT)
    defeasible = sum(1 for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE)
    defeaters = sum(1 for r in theory.rules if r.rule_type == RuleType.DEFEATER)

    stats = {
        "facts": len(theory.facts),
        "total_rules": len(theory.rules),
        "strict": strict,
        "defeasible": defeasible,
        "defeaters": defeaters,
    }

    with open(source_dir / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    return stats


def extract_nell(output_dir: Path) -> dict:
    print("\n  NELL (HuggingFace rtw-cmu/nell)...", flush=True)
    t0 = time.time()
    from blanc.ontology.nell_extractor import NellExtractor
    ext = NellExtractor(confidence_threshold=0.95)
    ext.extract()
    theory = ext.to_theory()
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "nell", output_dir)


def extract_sumo(output_dir: Path) -> dict:
    print("\n  SUMO (GitHub ontologyportal/sumo)...", flush=True)
    sumo_dir = _PROJECT_ROOT / "data" / "sumo"
    if not sumo_dir.exists() or not list(sumo_dir.glob("*.kif")):
        print("    [SKIP] SUMO not downloaded. Run: python scripts/download_sumo.py", flush=True)
        return {}
    t0 = time.time()
    from blanc.ontology.sumo_extractor import SumoExtractor
    ext = SumoExtractor(sumo_dir)
    ext.load()
    ext.extract()
    theory = ext.to_theory()
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "sumo", output_dir)


def extract_gene_ontology(output_dir: Path) -> dict:
    print("\n  Gene Ontology (OBO + GAF)...", flush=True)
    go_dir = _PROJECT_ROOT / "data" / "gene_ontology"
    obo = go_dir / "go-basic.obo"
    if not obo.exists():
        print("    [SKIP] GO not downloaded. Run: python scripts/download_gene_ontology.py", flush=True)
        return {}
    gafs = list(go_dir.glob("*.gaf.gz")) + list(go_dir.glob("*.gaf"))
    t0 = time.time()
    from blanc.ontology.gene_ontology_extractor import GeneOntologyExtractor
    ext = GeneOntologyExtractor(obo, gafs if gafs else None)
    ext.extract()
    theory = ext.to_theory()
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "gene_ontology", output_dir)


def extract_mesh(output_dir: Path) -> dict:
    print("\n  MeSH (NLM XML)...", flush=True)
    mesh_dir = _PROJECT_ROOT / "data" / "mesh"
    xmls = list(mesh_dir.glob("desc*.xml")) if mesh_dir.exists() else []
    if not xmls:
        print("    [SKIP] MeSH not downloaded. Run: python scripts/download_mesh.py", flush=True)
        return {}
    t0 = time.time()
    from blanc.ontology.mesh_extractor import MeshExtractor
    ext = MeshExtractor(xmls[0])
    ext.load()
    ext.extract()
    theory = ext.to_theory()
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "mesh", output_dir)


def extract_framenet(output_dir: Path) -> dict:
    print("\n  FrameNet (NLTK)...", flush=True)
    t0 = time.time()
    try:
        from blanc.ontology.framenet_extractor import FrameNetExtractor
        ext = FrameNetExtractor()
        ext.extract()
        theory = ext.to_theory()
    except ImportError as e:
        print(f"    [SKIP] {e}", flush=True)
        return {}
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "framenet", output_dir)


def extract_yago(output_dir: Path) -> dict:
    print("\n  YAGO 4.5 (full TTL)...", flush=True)
    yago_dir = _PROJECT_ROOT / "data" / "yago"
    ttl_candidates = (
        list(yago_dir.glob("yago-4.5*/yago-*.ttl"))
        + list(yago_dir.glob("*.ttl"))
    ) if yago_dir.exists() else []
    if not ttl_candidates:
        print("    [SKIP] YAGO TTL not found.", flush=True)
        return {}
    ttl = ttl_candidates[0]
    print(f"    Using: {ttl.name} ({ttl.stat().st_size / 1024 / 1024:.0f} MB)", flush=True)
    t0 = time.time()
    from blanc.ontology.yago_full_extractor import YagoFullExtractor
    ext = YagoFullExtractor(ttl)
    ext.extract()
    theory = ext.to_theory()
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "yago_full", output_dir)


def extract_wikidata(output_dir: Path) -> dict:
    print("\n  Wikidata (SPARQL endpoint)...", flush=True)
    t0 = time.time()
    try:
        from blanc.ontology.wikidata_extractor import WikidataExtractor, DOMAIN_CLASSES
        ext = WikidataExtractor()
        ext.extract_constraint_exceptions()
        all_qids = []
        for domain_qids in DOMAIN_CLASSES.values():
            all_qids.extend(domain_qids.keys())
        ext.extract_domain_rules(all_qids[:10], limit=5000)
        theory = ext.to_theory()
    except Exception as e:
        print(f"    [WARN] Wikidata extraction failed: {e}", flush=True)
        return {}
    elapsed = time.time() - t0
    print(f"    Extracted in {elapsed:.1f}s", flush=True)
    return _save_theory(theory, "wikidata", output_dir)


_EXTRACTORS = {
    "nell": extract_nell,
    "sumo": extract_sumo,
    "go": extract_gene_ontology,
    "mesh": extract_mesh,
    "framenet": extract_framenet,
    "yago": extract_yago,
    "wikidata": extract_wikidata,
}


def main():
    parser = argparse.ArgumentParser(description="Extract rules from all knowledge sources")
    parser.add_argument(
        "--sources", type=str, default=",".join(ALL_SOURCES),
        help=f"Comma-separated sources to extract (default: all). Options: {ALL_SOURCES}",
    )
    args = parser.parse_args()
    sources = [s.strip() for s in args.sources.split(",")]

    print("=" * 70, flush=True)
    print("MULTI-TIER KNOWLEDGE EXTRACTION", flush=True)
    print("=" * 70, flush=True)
    print(f"Sources: {sources}", flush=True)

    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_stats = {}

    for source in sources:
        if source not in _EXTRACTORS:
            print(f"\n  [SKIP] Unknown source: {source}", flush=True)
            continue
        try:
            stats = _EXTRACTORS[source](_OUTPUT_DIR)
            if stats:
                all_stats[source] = stats
                print(f"    -> {stats['total_rules']:,} rules "
                      f"({stats['strict']:,} strict, {stats['defeasible']:,} defeasible, "
                      f"{stats['defeaters']:,} defeaters)", flush=True)
        except Exception as e:
            print(f"    [ERROR] {source}: {e}", flush=True)

    print(f"\n{'=' * 70}", flush=True)
    print("EXTRACTION COMPLETE", flush=True)
    print(f"{'=' * 70}", flush=True)

    total_rules = sum(s.get("total_rules", 0) for s in all_stats.values())
    total_defeaters = sum(s.get("defeaters", 0) for s in all_stats.values())

    for name, s in all_stats.items():
        print(f"  {name:15s}: {s['total_rules']:>10,} rules "
              f"({s['defeaters']:>6,} defeaters)", flush=True)
    print(f"  {'NEW TOTAL':15s}: {total_rules:>10,} rules "
          f"({total_defeaters:>6,} defeaters)", flush=True)
    print(f"\n  Tier 0+1 baseline: 292,894 rules", flush=True)
    print(f"  Grand total:       {total_rules + 292894:,} rules", flush=True)

    with open(_OUTPUT_DIR / "extraction_summary.json", "w") as f:
        json.dump({
            "sources": all_stats,
            "new_total_rules": total_rules,
            "new_total_defeaters": total_defeaters,
            "tier01_baseline": 292894,
            "grand_total": total_rules + 292894,
        }, f, indent=2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
