"""
Download instructions for UMLS.

UMLS requires a free NLM UMLS Terminology Services (UTS) account.
Automated download is not possible without authentication; this script
prints the manual steps and verifies the local installation if present.

Registration: https://uts.nlm.nih.gov/uts/

Author: Anonymous Authors
"""

import sys
from pathlib import Path


EXPECTED_FILES = [
    "MRCONSO.RRF",
    "MRREL.RRF",
    "MRSTY.RRF",
    "MRDEF.RRF",
]


def main():
    dest = Path(__file__).parent.parent / "data" / "umls"

    if dest.is_dir():
        found = [f.name for f in dest.iterdir() if f.name in EXPECTED_FILES]
        if set(found) >= {"MRCONSO.RRF", "MRREL.RRF", "MRSTY.RRF"}:
            total_mb = sum(
                (dest / f).stat().st_size for f in found
            ) / 1024 / 1024
            print(f"[OK] UMLS RRF files found ({total_mb:.0f} MB total)")
            for f in sorted(found):
                mb = (dest / f).stat().st_size / 1024 / 1024
                print(f"     {f}: {mb:.1f} MB")
            return 0
        else:
            missing = set(EXPECTED_FILES[:3]) - set(found)
            print(f"[INCOMPLETE] Missing: {', '.join(sorted(missing))}")
            print()

    print("UMLS requires manual download (NLM license agreement).")
    print()
    print("Steps:")
    print("  1. Create a free UTS account at https://uts.nlm.nih.gov/uts/")
    print("  2. Accept the UMLS Metathesaurus License Agreement")
    print("  3. Download the UMLS Full Release from:")
    print("     https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html")
    print("  4. Extract the archive and locate the META/ directory")
    print("  5. Copy the RRF files to:", dest)
    print()
    print("Required files:")
    for f in EXPECTED_FILES[:3]:
        print(f"  - {f}")
    print(f"  - {EXPECTED_FILES[3]} (optional, for definitions)")
    print()
    print("Alternative: use the UMLS REST API or MetamorphoSys subset tool")
    print("to extract only the vocabularies you need (reduces size from")
    print("~40 GB to a few GB).")
    print()
    print("MetamorphoSys guide:")
    print("  https://www.nlm.nih.gov/research/umls/implementation_resources/metamorphosys/help.html")
    return 1


if __name__ == "__main__":
    sys.exit(main())
