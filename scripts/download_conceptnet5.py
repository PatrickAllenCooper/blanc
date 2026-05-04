"""
Download ConceptNet5 assertions file.

Downloads the main assertions CSV from ConceptNet 5.7.0 (latest stable).

Author: Anonymous Authors
Date: 2026-02-11
"""

import urllib.request
import sys
from pathlib import Path


def download_conceptnet5(output_dir: Path = None):
    """
    Download ConceptNet 5.7.0 assertions.
    
    Args:
        output_dir: Where to save (default: D:/datasets/conceptnet5/)
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / "data" / "conceptnet"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url = "https://s3.amazonaws.com/conceptnet/downloads/2019/edges/conceptnet-assertions-5.7.0.csv.gz"
    output_file = output_dir / "conceptnet-assertions-5.7.0.csv.gz"
    
    if output_file.exists():
        print(f"[OK] ConceptNet5 already downloaded: {output_file}")
        print(f"Size: {output_file.stat().st_size / (1024*1024):.1f} MB")
        return output_file
    
    print(f"Downloading ConceptNet 5.7.0...")
    print(f"URL: {url}")
    print(f"Destination: {output_file}")
    print("This may take several minutes (~300 MB)...")
    
    def progress(block_num, block_size, total_size):
        downloaded = block_num * block_size
        percent = min(100, downloaded * 100 / total_size)
        mb_downloaded = downloaded / (1024 * 1024)
        mb_total = total_size / (1024 * 1024)
        print(f"\r  Progress: {percent:.1f}% ({mb_downloaded:.1f}/{mb_total:.1f} MB)", end='')
    
    urllib.request.urlretrieve(url, output_file, progress)
    print(f"\n\n[SUCCESS] Downloaded: {output_file}")
    print(f"Size: {output_file.stat().st_size / (1024*1024):.1f} MB")
    
    return output_file


if __name__ == "__main__":
    try:
        file_path = download_conceptnet5()
        print(f"\nConceptNet5 ready at: {file_path}")
        sys.exit(0)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        sys.exit(1)
