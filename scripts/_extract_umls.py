"""Extract UMLS 2025AB into a defeasible theory."""
import pickle
import json
import time
from pathlib import Path
from blanc.ontology.umls_extractor import extract_from_umls

UMLS_META = Path(r"D:\datasets\umls-2025AB-metathesaurus-full\2025AB\META")
OUT_DIR = Path("data/extracted/umls")

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70, flush=True)
    print("UMLS 2025AB EXTRACTION", flush=True)
    print(f"Source: {UMLS_META}", flush=True)
    print("=" * 70, flush=True)

    t0 = time.time()
    theory = extract_from_umls(UMLS_META)
    elapsed = time.time() - t0
    print(f"\nExtraction complete in {elapsed:.1f}s", flush=True)

    from collections import Counter
    types = Counter()
    body_sizes = Counter()
    for r in theory.rules:
        types[r.rule_type.name] += 1
        body_sizes[len(r.body)] += 1

    stats = {
        "facts": len(theory.facts),
        "total_rules": len(theory.rules),
        "strict": types.get("STRICT", 0),
        "defeasible": types.get("DEFEASIBLE", 0),
        "defeaters": types.get("DEFEATER", 0),
    }
    print(f"Stats: {json.dumps(stats, indent=2)}", flush=True)
    print(f"Body sizes: {dict(body_sizes)}", flush=True)

    print(f"\nSaving theory to {OUT_DIR}...", flush=True)
    with open(OUT_DIR / "theory.pkl", "wb") as f:
        pickle.dump(theory, f)

    with open(OUT_DIR / "stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("Done.", flush=True)

if __name__ == "__main__":
    main()
