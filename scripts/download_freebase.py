"""
Download the Freebase RDF dump.

The canonical dump is freebase-rdf-latest.gz (~400 GB uncompressed,
~22 GB gzipped).  The FreebaseExtractor streams the .gz file directly,
so decompression is not required.

Source: https://developers.google.com/freebase

Author: Anonymous Authors
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

FREEBASE_URL = (
    "https://commondatastorage.googleapis.com/"
    "freebase-public/rdf/freebase-rdf-latest.gz"
)


def _download_file(url: str, dest: Path) -> None:
    """Stream-download *url* to *dest* with progress reporting."""
    response = requests.get(url, stream=True, timeout=3600)
    response.raise_for_status()

    total = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(dest, "wb") as fh:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                fh.write(chunk)
                downloaded += len(chunk)
                if total > 0:
                    pct = downloaded / total * 100
                    gb = downloaded / 1024 / 1024 / 1024
                    gb_total = total / 1024 / 1024 / 1024
                    print(
                        f"  Progress: {pct:.1f}% "
                        f"({gb:.2f}/{gb_total:.2f} GB)  ",
                        end="\r",
                    )

    print(
        f"\n  [OK] {dest.name} "
        f"({downloaded / 1024 / 1024 / 1024:.2f} GB)"
    )


def main() -> int:
    print("=" * 70)
    print("Downloading Freebase RDF Dump")
    print("=" * 70)
    print()
    print("WARNING: The Freebase dump is approximately 22 GB compressed.")
    print("The FreebaseExtractor reads the .gz file directly (no decompression).")
    print()

    data_dir = Path("data/freebase")
    data_dir.mkdir(parents=True, exist_ok=True)

    dest = data_dir / "freebase-rdf-latest.gz"

    if dest.exists():
        size_gb = dest.stat().st_size / 1024 / 1024 / 1024
        print(f"[SKIP] Already downloaded: {dest} ({size_gb:.2f} GB)")
        return 0

    print(f"[DOWNLOAD] freebase-rdf-latest.gz")
    print(f"  URL: {FREEBASE_URL}")

    try:
        _download_file(FREEBASE_URL, dest)
    except Exception as exc:
        print(f"\n  [ERROR] {exc}")
        if dest.exists():
            dest.unlink()
        return 1

    print("\n" + "=" * 70)
    print("Download Complete")
    print("=" * 70)

    size_gb = dest.stat().st_size / 1024 / 1024 / 1024
    print(f"\n  {dest}: {size_gb:.2f} GB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
