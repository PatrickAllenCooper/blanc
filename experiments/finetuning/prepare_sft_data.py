"""
Phase B-SFT: Supervised Fine-Tuning Dataset Construction.

Generates (prompt, completion) pairs from DeFAb instances by rendering gold
hypotheses through the codec.  Unlike preference data, SFT requires no
response sampling -- the gold hypothesis IS the target completion.

For each training instance:
  1. Render the prompt via render_prompt(instance, modality, strategy).
  2. Encode the gold hypothesis h* in the same modality as the prompt.
  3. Write (prompt, completion) to JSONL.

This is the simplest post-training signal: pure supervised imitation of
the formally verified gold standard.

Usage:
  python experiments/finetuning/prepare_sft_data.py \\
      --output-dir experiments/finetuning/data/ \\
      --modalities M4 \\
      --strategies direct

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.author.generation import AbductiveInstance
from blanc.author.loaders import load_instances_from_json
from prompting import render_prompt, _encode_element


# ---------------------------------------------------------------------------
# SFT record
# ---------------------------------------------------------------------------

@dataclass
class SFTRecord:
    prompt:      str
    completion:  str
    level:       int
    domain:      str
    instance_id: str
    modality:    str
    strategy:    str


# ---------------------------------------------------------------------------
# Gold hypothesis encoding
# ---------------------------------------------------------------------------

def encode_gold_hypothesis(
    instance: AbductiveInstance,
    modality: str,
) -> str | None:
    """Encode the first gold hypothesis in *modality*.

    For Level 1-2, the gold is typically a fact or rule string.
    For Level 3, the gold is a defeater rule string.
    Both are encoded through the same modality codec used for prompts.
    """
    if not instance.gold:
        return None
    gold = instance.gold[0]
    if isinstance(gold, str):
        domain = (instance.metadata or {}).get("domain", "biology")
        return _encode_element(gold, modality, domain)
    return str(gold)


# ---------------------------------------------------------------------------
# Stratified split (reuses existing splits if available)
# ---------------------------------------------------------------------------

def _load_or_create_splits(
    instances: list[AbductiveInstance],
    splits_file: Path,
    seed: int,
) -> tuple[list[AbductiveInstance], list[AbductiveInstance], list[AbductiveInstance]]:
    """Load existing train/val/test split or create a new 70/15/15 split."""
    if splits_file.exists():
        with open(splits_file) as f:
            splits_data = json.load(f)
        train_ids = set(splits_data.get("train", []))
        val_ids   = set(splits_data.get("val", []))
        test_ids  = set(splits_data.get("test", []))
        train = [i for i in instances if getattr(i, "id", "") in train_ids]
        val   = [i for i in instances if getattr(i, "id", "") in val_ids]
        test  = [i for i in instances if getattr(i, "id", "") in test_ids]
        return train, val, test

    from finetuning.prepare_preference_data import make_splits
    train, val, test = make_splits(instances, seed=seed)
    splits_data = {
        "train": [getattr(i, "id", "") for i in train],
        "val":   [getattr(i, "id", "") for i in val],
        "test":  [getattr(i, "id", "") for i in test],
    }
    splits_file.parent.mkdir(parents=True, exist_ok=True)
    with open(splits_file, "w") as f:
        json.dump(splits_data, f, indent=2)
    return train, val, test


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def build_sft_dataset(
    instances:  list[AbductiveInstance],
    modalities: list[str],
    strategies: list[str],
    curriculum: str = "joint",
) -> list[SFTRecord]:
    """Build SFT records from *instances* across all modality x strategy combos."""
    records: list[SFTRecord] = []

    for instance in instances:
        level  = getattr(instance, "level", 2)
        domain = (instance.metadata or {}).get("domain", "unknown")
        iid    = getattr(instance, "id", "unknown")

        for modality in modalities:
            gold_text = encode_gold_hypothesis(instance, modality)
            if gold_text is None:
                continue

            for strategy in strategies:
                rendered = render_prompt(instance, modality, strategy)
                records.append(SFTRecord(
                    prompt      = rendered.prompt,
                    completion  = gold_text,
                    level       = level,
                    domain      = domain,
                    instance_id = iid,
                    modality    = modality,
                    strategy    = strategy,
                ))

    if curriculum == "weighted":
        l3    = [r for r in records if r.level == 3]
        other = [r for r in records if r.level != 3]
        records = other + l3 * 5
        random.shuffle(records)
    elif curriculum == "l12_only":
        records = [r for r in records if r.level != 3]

    return records


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build DeFAb SFT dataset from gold hypotheses."
    )
    p.add_argument("--instances-dir", default="instances")
    p.add_argument("--domains", nargs="+",
                   default=["biology", "legal", "materials"])
    p.add_argument("--modalities", nargs="+", default=["M4"])
    p.add_argument("--strategies", nargs="+", default=["direct"])
    p.add_argument("--curriculum", default="joint",
                   choices=["joint", "sequential", "weighted", "l12_only"])
    p.add_argument("--instance-limit", type=int, default=None)
    p.add_argument("--level3-limit", type=int, default=None)
    p.add_argument("--output-dir", default="experiments/finetuning/data")
    p.add_argument("--splits-file", default="instances/splits.json")
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb SFT Data Construction")
    print("=" * 70)
    print(f"  Modalities  : {args.modalities}")
    print(f"  Strategies  : {args.strategies}")
    print(f"  Curriculum  : {args.curriculum}")

    instances_dir = ROOT / args.instances_dir
    output_dir    = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("\nLoading instances...")
    all_instances = load_instances_from_json(
        instances_dir,
        domains=args.domains,
        include_level3=True,
        level2_limit=args.instance_limit,
        level3_limit=args.level3_limit,
    )
    print(f"  Loaded {len(all_instances)} instances")

    splits_file = ROOT / args.splits_file
    train_set, val_set, _ = _load_or_create_splits(
        all_instances, splits_file, args.seed,
    )
    print(f"  Train: {len(train_set)}  Val: {len(val_set)}")

    print("\nBuilding SFT dataset...")
    train_records = build_sft_dataset(
        train_set, args.modalities, args.strategies, args.curriculum,
    )
    val_records = build_sft_dataset(
        val_set, args.modalities, args.strategies, "joint",
    )

    train_file = output_dir / "sft_train.jsonl"
    val_file   = output_dir / "sft_val.jsonl"

    for path, recs in [(train_file, train_records), (val_file, val_records)]:
        with open(path, "w") as f:
            for rec in recs:
                f.write(json.dumps(asdict(rec)) + "\n")

    print(f"\n  Train records: {len(train_records)} -> {train_file}")
    print(f"  Val records:   {len(val_records)}   -> {val_file}")

    level_counts = {}
    for r in train_records:
        level_counts[r.level] = level_counts.get(r.level, 0) + 1
    for lvl in sorted(level_counts):
        print(f"  Level {lvl}: {level_counts[lvl]} records")

    print(f"\n{'='*70}")
    print("SFT data construction complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
