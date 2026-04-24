"""
Extract the Mathlib topology theorem index for the DeFAb-Math-Topology
novelty filter.

Walks the Lean project's Mathlib checkout (typically at
``lean/.lake/packages/mathlib/``) and extracts all theorem/lemma
declarations from the topology, algebraic topology, and geometry subtrees.
Writes a JSONL index file (one row per theorem) that the
:class:`blanc.math.novelty.NoveltyFilter` can load via ``from_jsonl()``.

Output format (one JSON object per line):
    {
        "identifier": "Mathlib.Topology.Basic.isOpen_univ",
        "statement": "IsOpen (univ : Set X)",
        "source_path": "Mathlib/Topology/Basic.lean"
    }

Plus a single meta-row at the start:
    {"_meta": {"mathlib_commit": "<rev>", "lean_version": "<ver>",
               "theorem_count": N, "timestamp": "..."}}

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blanc.math.topology_extractor import MathlibExtractor  # noqa: E402

# Mathlib sub-trees to include in the novelty index.
_SUBTREES = [
    "Mathlib/Topology",
    "Mathlib/AlgebraicTopology",
    "Mathlib/Geometry",
    "Mathlib/Order/Compact",
]


def _git_rev(mathlib_dir: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(mathlib_dir),
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _lean_version(lean_dir: Path) -> str:
    toolchain = lean_dir / "lean-toolchain"
    if toolchain.exists():
        return toolchain.read_text().strip()
    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--lean-dir", type=Path,
        default=ROOT / "lean",
        help="Path to the lean/ project directory containing .lake/packages/mathlib.",
    )
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "experiments/math_topology/data/mathlib_topology_index.jsonl",
        help="Destination JSONL file.",
    )
    parser.add_argument(
        "--max-per-subtree", type=int, default=None,
        help="Cap per subtree (for quick smoke runs).",
    )
    args = parser.parse_args()

    mathlib_dir = args.lean_dir / ".lake" / "packages" / "mathlib"
    if not mathlib_dir.exists():
        print(
            f"ERROR: Mathlib not found at {mathlib_dir}. "
            "Run `lake exe cache get` inside lean/ first.",
            file=sys.stderr,
        )
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)

    commit = _git_rev(mathlib_dir)
    lean_ver = _lean_version(args.lean_dir)
    timestamp = datetime.now(tz=timezone.utc).isoformat()

    extractor = MathlibExtractor(mathlib_root=mathlib_dir)
    total = 0
    rows: list[dict] = []

    for subtree in _SUBTREES:
        subtree_path = mathlib_dir / subtree
        if not subtree_path.exists():
            print(f"  skipping missing subtree: {subtree}", file=sys.stderr)
            continue
        count = 0
        for theorem in extractor.extract_subtree(subtree):
            rows.append({
                "identifier": theorem.identifier,
                "statement": theorem.statement,
                "source_path": theorem.source_path or "",
            })
            count += 1
            total += 1
            if args.max_per_subtree is not None and count >= args.max_per_subtree:
                break
        print(f"  {subtree}: {count} theorems", file=sys.stderr)

    meta = {
        "_meta": {
            "mathlib_commit": commit,
            "lean_version": lean_ver,
            "theorem_count": total,
            "timestamp": timestamp,
            "subtrees": _SUBTREES,
        }
    }

    with args.output.open("w", encoding="utf-8") as f:
        f.write(json.dumps(meta) + "\n")
        for row in rows:
            f.write(json.dumps(row) + "\n")

    print(
        json.dumps({"output": str(args.output), "theorem_count": total,
                    "mathlib_commit": commit, "lean_version": lean_ver}, indent=2)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
