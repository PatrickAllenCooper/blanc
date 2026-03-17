"""
Download YAGO knowledge base.

YAGO is a large-scale expert-curated knowledge base with rich taxonomy.
We'll use it to extract inference rules and build derivation chains.

Author: Patrick Cooper
Date: 2026-02-12
"""

import requests
import gzip
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def download_yago():
    """Download YAGO knowledge base from official sources."""
    
    # YAGO 4.5 is the latest with rich taxonomy and logical consistency
    # Available from yago-knowledge.org and Zenodo
    
    print("=" * 70)
    print("Downloading YAGO Knowledge Base")
    print("=" * 70)
    
    # Create data directory
    data_dir = Path("data/yago")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # YAGO 4.5 download links (from official sources)
    # Using tiny version for development (200MB vs 12GB full)
    urls = {
        "yago-tiny": "https://yago-knowledge.org/data/yago4.5/yago-4.5.0.2-tiny.zip",
        "yago-full": "https://yago-knowledge.org/data/yago4.5/yago-4.5.0.2.zip",
        "yago-entities": "https://yago-knowledge.org/data/yago4.5/yago-entities.jsonl.zip",
    }
    
    print(f"\nDownload directory: {data_dir}")
    print(f"Files to download: {len(urls)}\n")
    
    for name, url in urls.items():
        filename = url.split('/')[-1]
        output_file = data_dir / filename
        
        if output_file.exists():
            print(f"[SKIP] {name} - already exists")
            continue
        
        print(f"[DOWNLOAD] {name}")
        print(f"  URL: {url}")
        print(f"  File: {filename}")
        
        try:
            response = requests.get(url, stream=True, timeout=300)
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
                            print(f"  Progress: {percent:.1f}% ({mb_down:.1f}/{mb_total:.1f} MB)  ", end='\r')
            
            print(f"\n  [OK] Downloaded: {output_file.name} ({downloaded / 1024 / 1024:.1f} MB)")
            
        except Exception as e:
            print(f"\n  [ERROR] Failed to download {name}: {e}")
            if output_file.exists():
                output_file.unlink()
    
    print("\n" + "=" * 70)
    print("Download Complete")
    print("=" * 70)
    
    # List downloaded files
    print("\nDownloaded files:")
    for f in data_dir.glob("*.zip"):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {size_mb:.1f} MB")
    
    # Extract zip files
    print("\nExtracting files...")
    import zipfile
    for zip_file in data_dir.glob("*.zip"):
        extract_dir = data_dir / zip_file.stem
        if extract_dir.exists():
            print(f"  [SKIP] {zip_file.stem} - already extracted")
            continue
        
        print(f"  [EXTRACT] {zip_file.name}")
        with zipfile.ZipFile(zip_file, 'r') as zf:
            zf.extractall(extract_dir)
        print(f"    -> {extract_dir}")
    
    print("\nExtracted directories:")
    for d in data_dir.iterdir():
        if d.is_dir():
            num_files = len(list(d.glob("*")))
            print(f"  {d.name}: {num_files} files")
    
    return data_dir


if __name__ == "__main__":
    download_yago()
