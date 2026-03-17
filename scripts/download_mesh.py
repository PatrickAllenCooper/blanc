"""
Download MeSH descriptor XML.

Author: Patrick Cooper
"""

import sys
import urllib.request
from pathlib import Path


def main():
    dest = Path(__file__).parent.parent / "data" / "mesh"
    dest.mkdir(parents=True, exist_ok=True)

    url = "https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/desc2026.xml"
    out = dest / "desc2026.xml"

    if out.exists():
        mb = out.stat().st_size / 1024 / 1024
        print(f"[SKIP] MeSH XML already exists ({mb:.1f} MB)")
        return 0

    print("Downloading MeSH descriptor XML (~300 MB)...")
    urllib.request.urlretrieve(url, out)
    mb = out.stat().st_size / 1024 / 1024
    print(f"[OK] MeSH XML ({mb:.1f} MB)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
