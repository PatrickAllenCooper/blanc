"""
Download instructions for SNOMED CT.

SNOMED CT requires a license from SNOMED International (IHTSDO) or can be
obtained through the NLM UMLS distribution for US-based users.  This
script prints manual download steps and verifies the local installation
if present.

International Edition: https://www.snomed.org/get-snomed
US Edition (via NLM): https://www.nlm.nih.gov/healthit/snomedct/

Author: Patrick Cooper
"""

import sys
from pathlib import Path


def _find_rf2_file(directory: Path) -> Path | None:
    """Search for sct2_Relationship_Snapshot files in a directory tree."""
    for p in directory.rglob("sct2_Relationship_Snapshot_*.txt"):
        return p
    return None


def _find_owl_file(directory: Path) -> Path | None:
    """Search for SNOMED OWL distribution files."""
    for pattern in ["*.owl", "*.ofn", "snomed*.owl"]:
        for p in directory.rglob(pattern):
            if "snomed" in p.name.lower() or "sct" in p.name.lower():
                return p
    for p in directory.rglob("*.owl"):
        return p
    return None


def main():
    dest = Path(__file__).parent.parent / "data" / "snomed"

    if dest.is_dir():
        rf2 = _find_rf2_file(dest)
        owl = _find_owl_file(dest)

        if rf2:
            mb = rf2.stat().st_size / 1024 / 1024
            print(f"[OK] SNOMED RF2 snapshot found: {rf2.name} ({mb:.1f} MB)")
            return 0
        elif owl:
            mb = owl.stat().st_size / 1024 / 1024
            print(f"[OK] SNOMED OWL file found: {owl.name} ({mb:.1f} MB)")
            return 0
        else:
            print("[INCOMPLETE] SNOMED directory exists but no RF2 or OWL files found")
            print()

    print("SNOMED CT requires a license for download.")
    print()
    print("Option 1 -- NLM UMLS (US users, free NLM account):")
    print("  1. Create a UTS account at https://uts.nlm.nih.gov/uts/")
    print("  2. Download the UMLS release (includes SNOMED CT US Edition)")
    print("  3. Use MetamorphoSys to extract SNOMED CT")
    print("  4. Locate sct2_Relationship_Snapshot_*.txt in the Snapshot/")
    print("     directory and copy to:", dest)
    print()
    print("Option 2 -- SNOMED International (IHTSDO):")
    print("  1. Check if your country is an IHTSDO Member:")
    print("     https://www.snomed.org/our-stakeholders/members")
    print("  2. Register at https://mlds.ihtsdotools.org/")
    print("  3. Download the International Edition (RF2 or OWL format)")
    print("  4. Extract and place files in:", dest)
    print()
    print("Option 3 -- SNOMED CT Browser (read-only, no download):")
    print("  https://browser.ihtsdotools.org/")
    print()
    print("Expected file formats:")
    print("  RF2:  sct2_Relationship_Snapshot_INT_YYYYMMDD.txt")
    print("  OWL:  snomed_ct_international_*.owl")
    print()
    print("The extractor auto-detects RF2 vs OWL format.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
