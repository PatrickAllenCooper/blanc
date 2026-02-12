"""
Download MatOnto materials science ontology.

MatOnto is an expert-curated materials science ontology based on BFO upper ontology.
Available through MatPortal - the ontology repository for materials science.

Source: https://matportal.org/ontologies/MATONTO
Classes: 1,307
Properties: 95
Depth: 129 levels

Author: Patrick Cooper
Date: 2026-02-12
"""

import requests
from pathlib import Path
import sys

def download_matonto():
    """Download MatOnto materials science ontology."""
    
    print("=" * 70)
    print("Downloading MatOnto Materials Science Ontology")
    print("=" * 70)
    
    # MatOnto OWL file from MatPortal
    # Note: MatPortal may require API key or web scraping
    # Trying direct OWL download
    
    output_dir = Path("data/matonto")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {output_dir}")
    print("\nNote: MatOnto may require manual download from MatPortal")
    print("URL: https://matportal.org/ontologies/MATONTO")
    print("Format: OWL")
    
    # MatPortal REST API (from website)
    matportal_api = "http://rest.matportal.org/ontologies/MATONTO/submissions/1/download?apikey=66c82e77-ce0d-4385-8056-a95898e47ebb"
    
    output_file = output_dir / "MatOnto-ontology.owl"
    
    if output_file.exists():
        print(f"\n[SKIP] MatOnto already exists")
        size_kb = output_file.stat().st_size / 1024
        print(f"  File: {output_file.name} ({size_kb:.1f} KB)")
        return output_dir
    
    print(f"\n[DOWNLOAD] Attempting MatOnto download...")
    
    try:
        response = requests.get(matportal_api, timeout=60)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        size_kb = len(response.content) / 1024
        print(f"  [OK] Downloaded: {size_kb:.1f} KB")
        
    except Exception as e:
        print(f"  [ERROR] Failed: {e}")
        print("\n  MANUAL DOWNLOAD REQUIRED:")
        print("  1. Visit: https://matportal.org/ontologies/MATONTO")
        print("  2. Click 'Download' and select OWL format")
        print(f"  3. Save to: {output_file}")
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    
    return output_dir


if __name__ == "__main__":
    download_matonto()
