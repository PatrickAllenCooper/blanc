"""
Download SUMO ontology from GitHub.

Author: Anonymous Authors
"""

import subprocess
import sys
from pathlib import Path


def main():
    dest = Path(__file__).parent.parent / "data" / "sumo"
    if dest.exists() and any(dest.glob("*.kif")):
        print(f"[OK] SUMO already present at {dest}")
        kif_count = len(list(dest.glob("*.kif")))
        print(f"  {kif_count} KIF files")
        return 0

    dest.mkdir(parents=True, exist_ok=True)
    print("Cloning SUMO from GitHub...")
    subprocess.run(
        ["git", "clone", "--depth", "1",
         "https://github.com/ontologyportal/sumo.git", str(dest)],
        check=True,
    )
    kif_count = len(list(dest.glob("*.kif")))
    print(f"[OK] SUMO cloned: {kif_count} KIF files")
    return 0

if __name__ == "__main__":
    sys.exit(main())
