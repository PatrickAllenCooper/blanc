"""
Download DAPRECO GDPR Legal Knowledge Base.

DAPRECO is the largest freely available LegalRuleML knowledge base.
Represents GDPR provisions as deontic rules (obligations, permissions, prohibitions).

Source: GitHub dapreco/daprecokb
Citation: Robaldo, Bartolini, Lenzini (2020), LREC
License: Open source

Author: Patrick Cooper
Date: 2026-02-12
"""

import requests
from pathlib import Path
import sys

def download_dapreco():
    """Download DAPRECO GDPR legal KB from GitHub."""
    
    print("=" * 70)
    print("Downloading DAPRECO GDPR Legal Knowledge Base")
    print("=" * 70)
    
    base_url = "https://raw.githubusercontent.com/dapreco/daprecokb/master/"
    
    files = {
        "gdpr/rioKB_GDPR.xml": "GDPR rules (main KB)",
        "gdpr/prefLabel.xml": "GDPR labels",
        "gdpr/hasSub.xml": "GDPR subsumption",
        "iso27018/iso27018.xml": "ISO 27018 rules",
    }
    
    output_dir = Path("data/dapreco")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {output_dir}")
    print(f"Files to download: {len(files)}\n")
    
    for filepath, description in files.items():
        url = base_url + filepath
        output_file = output_dir / Path(filepath).name
        
        if output_file.exists():
            print(f"[SKIP] {output_file.name} - already exists")
            continue
        
        print(f"[DOWNLOAD] {output_file.name}")
        print(f"  {description}")
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            with open(output_file, 'wb') as f:
                f.write(response.content)
            
            size_kb = len(response.content) / 1024
            print(f"  [OK] Downloaded: {size_kb:.1f} KB\n")
            
        except Exception as e:
            print(f"  [ERROR] Failed: {e}\n")
    
    print("=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    
    # List downloaded files
    print("\nDownloaded files:")
    for f in sorted(output_dir.glob("*.xml")):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name}: {size_kb:.1f} KB")
    
    return output_dir


if __name__ == "__main__":
    download_dapreco()
