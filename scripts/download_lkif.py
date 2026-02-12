"""
Download LKIF (Legal Knowledge Interchange Format) Core ontology.

LKIF is an expert-curated legal ontology developed by University of Amsterdam
researchers for the European ESTRELLA project.

Source: https://github.com/RinkeHoekstra/lkif-core
Citation: Hoekstra, Boer, van den Berg - University of Amsterdam
License: Open source

Author: Patrick Cooper
Date: 2026-02-12
"""

import requests
from pathlib import Path
import sys

def download_lkif():
    """Download LKIF Core ontology files from GitHub."""
    
    print("=" * 70)
    print("Downloading LKIF Core Legal Ontology")
    print("=" * 70)
    
    # LKIF Core ontology files from GitHub
    base_url = "https://raw.githubusercontent.com/RinkeHoekstra/lkif-core/master/"
    
    files = [
        "lkif-core.owl",
        "action.owl",
        "expression.owl",
        "legal-action.owl",
        "legal-role.owl",
        "mereology.owl",
        "norm.owl",
        "place.owl",
        "process.owl",
        "role.owl",
        "time.owl",
        "top.owl",
    ]
    
    # Create directory
    output_dir = Path("data/lkif-core")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {output_dir}")
    print(f"Files to download: {len(files)}\n")
    
    for filename in files:
        url = base_url + filename
        output_file = output_dir / filename
        
        if output_file.exists():
            print(f"[SKIP] {filename} - already exists")
            continue
        
        print(f"[DOWNLOAD] {filename}")
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            print(f"  [OK] Downloaded: {size_kb:.1f} KB")
            
        except Exception as e:
            print(f"  [ERROR] Failed to download {filename}: {e}")
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    
    # List downloaded files
    print("\nDownloaded files:")
    for f in sorted(output_dir.glob("*.owl")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name}: {size_kb:.1f} KB")
    
    return output_dir


if __name__ == "__main__":
    download_lkif()
