"""
Download DBpedia N-Triples dumps from the DBpedia Databus.

Downloads English instance-types and mappingbased-objects files
for use with the DbpediaExtractor.

Author: Patrick Cooper
"""

import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).parent.parent))

URLS = {
    "instance-types": (
        "https://databus.dbpedia.org/dbpedia/mappings/"
        "instance-types/2022.12.01/"
        "instance-types_lang=en.ttl.bz2"
    ),
    "mappingbased-objects": (
        "https://databus.dbpedia.org/dbpedia/mappings/"
        "mappingbased-objects/2022.12.01/"
        "mappingbased-objects_lang=en.ttl.bz2"
    ),
}


def _download_file(url: str, dest: Path) -> None:
    """Stream-download *url* to *dest* with progress reporting."""
    response = requests.get(url, stream=True, timeout=600)
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
                    mb = downloaded / 1024 / 1024
                    mb_total = total / 1024 / 1024
                    print(
                        f"  Progress: {pct:.1f}% "
                        f"({mb:.1f}/{mb_total:.1f} MB)  ",
                        end="\r",
                    )

    print(f"\n  [OK] {dest.name} ({downloaded / 1024 / 1024:.1f} MB)")


def _decompress_bz2(src: Path, dest: Path) -> None:
    """Decompress a .bz2 file to *dest*."""
    import bz2

    print(f"  [DECOMPRESS] {src.name} -> {dest.name}")
    with bz2.open(src, "rb") as fin, open(dest, "wb") as fout:
        while True:
            block = fin.read(1024 * 1024)
            if not block:
                break
            fout.write(block)
    print(f"  [OK] {dest.name}")


def main() -> int:
    print("=" * 70)
    print("Downloading DBpedia N-Triples (English)")
    print("=" * 70)

    data_dir = Path("data/dbpedia")
    data_dir.mkdir(parents=True, exist_ok=True)

    for name, url in URLS.items():
        filename = url.rsplit("/", 1)[-1]
        bz2_path = data_dir / filename
        nt_path = data_dir / filename.replace(".bz2", "")

        if nt_path.exists():
            print(f"[SKIP] {name} -- already decompressed")
            continue

        if not bz2_path.exists():
            print(f"[DOWNLOAD] {name}")
            print(f"  URL: {url}")
            try:
                _download_file(url, bz2_path)
            except Exception as exc:
                print(f"\n  [ERROR] {exc}")
                if bz2_path.exists():
                    bz2_path.unlink()
                continue

        _decompress_bz2(bz2_path, nt_path)

    print("\n" + "=" * 70)
    print("Download Complete")
    print("=" * 70)

    print("\nFiles:")
    for f in sorted(data_dir.iterdir()):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name}: {size_mb:.1f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
