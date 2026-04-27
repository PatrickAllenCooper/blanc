"""Crop ROE scenario screenshots to remove side-panel overlays.

Usage::

    python scripts/crop_roe_screenshots.py paper/sc2_screenshots/
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image


def crop_screenshot(path: Path, right_x: int = 660) -> None:
    img = Image.open(path).convert("RGB")
    w, h = img.size
    if right_x >= w:
        return
    cropped = img.crop((0, 0, right_x, h))
    cropped.save(path)
    print(f"  Cropped {path.name}: {w}x{h} -> {right_x}x{h}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: crop_roe_screenshots.py <directory> [right_x]")
        return 1
    src = Path(sys.argv[1])
    right_x = int(sys.argv[2]) if len(sys.argv) > 2 else 660
    if not src.is_dir():
        print(f"not a directory: {src}")
        return 1
    pngs = sorted(src.glob("sc2_roe_*.png"))
    if not pngs:
        print("no sc2_roe_*.png files found")
        return 1
    for p in pngs:
        crop_screenshot(p, right_x=right_x)
    return 0


if __name__ == "__main__":
    sys.exit(main())
