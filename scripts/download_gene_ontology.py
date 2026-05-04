"""
Download Gene Ontology OBO file and human GAF annotations.

Author: Anonymous Authors
"""

import sys
import requests
from pathlib import Path


_FILES = {
    "go-basic.obo": "https://purl.obolibrary.org/obo/go/go-basic.obo",
    "goa_human.gaf.gz": "https://release.geneontology.org/2024-06-17/annotations/goa_human.gaf.gz",
}

_HEADERS = {"User-Agent": "DeFAb/1.0 (anonymous@anonymous.org)"}


def main():
    dest = Path(__file__).parent.parent / "data" / "gene_ontology"
    dest.mkdir(parents=True, exist_ok=True)

    for name, url in _FILES.items():
        out = dest / name
        if out.exists():
            mb = out.stat().st_size / 1024 / 1024
            print(f"[SKIP] {name} already exists ({mb:.1f} MB)")
            continue
        print(f"Downloading {name}...")
        r = requests.get(url, headers=_HEADERS, stream=True, timeout=120)
        r.raise_for_status()
        with open(out, "wb") as f:
            for chunk in r.iter_content(1024 * 1024):
                f.write(chunk)
        mb = out.stat().st_size / 1024 / 1024
        print(f"[OK] {name} ({mb:.1f} MB)")

    return 0

if __name__ == "__main__":
    sys.exit(main())
