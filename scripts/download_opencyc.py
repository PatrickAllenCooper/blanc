"""
Download OpenCyc ontology.

OpenCyc is an expert-curated ontology from Cycorp (million-axiom knowledge base).
Last public version: May 2012 (OWL format).

Source: GitHub therohk/opencyc-kb
Citation: Cycorp ontology engineers
License: Apache 2.0

Author: Patrick Cooper
Date: 2026-02-12
"""

import requests
from pathlib import Path
import sys

def download_opencyc():
    """Download OpenCyc OWL files from GitHub."""
    
    print("=" * 70)
    print("Downloading OpenCyc Ontology")
    print("=" * 70)
    
    # OpenCyc OWL files from GitHub (2012 version - last public release)
    base_url = "https://github.com/therohk/opencyc-kb/raw/main/"
    
    files = {
        "opencyc-2012-05-10-readable.owl.gz": "OpenCyc 2012 (human-readable IDs)",
    }
    
    output_dir = Path("data/opencyc")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\nDownload directory: {output_dir}")
    print(f"Source: Last public OpenCyc release (May 2012)")
    print(f"Size: ~120 MB compressed\n")
    
    for filename, description in files.items():
        url = base_url + filename
        output_file = output_dir / filename
        
        if output_file.exists():
            print(f"[SKIP] {filename} - already exists")
            size_mb = output_file.stat().st_size / 1024 / 1024
            print(f"  Size: {size_mb:.1f} MB")
            continue
        
        print(f"[DOWNLOAD] {filename}")
        print(f"  {description}")
        print(f"  URL: {url}")
        
        try:
            response = requests.get(url, stream=True, timeout=120)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            mb_down = downloaded / 1024 / 1024
                            mb_total = total_size / 1024 / 1024
                            print(f"  Progress: {percent:.1f}% ({mb_down:.1f}/{mb_total:.1f} MB)", end='\r')
            
            print(f"\n  [OK] Downloaded: {downloaded / 1024 / 1024:.1f} MB")
            
        except Exception as e:
            print(f"\n  [ERROR] Failed: {e}")
    
    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print("=" * 70)
    
    # List downloaded files
    print("\nDownloaded files:")
    for f in sorted(output_dir.glob("*.gz")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {size_mb:.1f} MB")
    
    return output_dir


if __name__ == "__main__":
    download_opencyc()
