"""
Remove cache entries that were truncated by an insufficient max_tokens budget.

A truncated entry has finish_reason='length' AND text==''.  These will never
produce a useful result on retry unless max_tokens is increased first.

Usage:
    python experiments/clear_truncated_cache.py [--cache-dir experiments/cache] [--dry-run]

After running, re-run the evaluation; the pipeline will re-query all cleared entries.
"""
import argparse
import json
import os
import sys


def scan(cache_dir: str, dry_run: bool) -> None:
    if not os.path.isdir(cache_dir):
        print(f"Cache directory not found: {cache_dir}")
        sys.exit(1)

    total   = 0
    removed = 0
    skipped = 0

    for root, _, files in os.walk(cache_dir):
        for fname in files:
            path = os.path.join(root, fname)
            total += 1
            try:
                with open(path) as f:
                    entry = json.load(f)
                resp = entry.get("response", {})
                text          = resp.get("text", "NOKEY")
                finish_reason = (resp.get("metadata") or {}).get("finish_reason", "")
                if text == "" and finish_reason == "length":
                    if dry_run:
                        print(f"  would delete: {path}")
                    else:
                        os.remove(path)
                    removed += 1
                else:
                    skipped += 1
            except Exception as e:
                print(f"  warning: could not process {path}: {e}")
                skipped += 1

    label = "would remove" if dry_run else "removed"
    print(f"\nCache dir : {cache_dir}")
    print(f"Total     : {total}")
    print(f"{label:10}: {removed}  (finish_reason=length, text='')")
    print(f"Kept      : {skipped}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-dir", default="experiments/cache",
                   help="Root cache directory (default: experiments/cache)")
    p.add_argument("--provider", default=None,
                   help="Limit to one provider sub-directory, e.g. foundry_deepseek")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be deleted without deleting")
    args = p.parse_args()

    target = os.path.join(args.cache_dir, args.provider) if args.provider else args.cache_dir
    mode   = "DRY RUN" if args.dry_run else "LIVE"
    print(f"Clearing truncated cache entries ({mode})")
    print(f"Target: {target}\n")
    scan(target, args.dry_run)


if __name__ == "__main__":
    main()
