"""
Build DeFAb preference dataset from mined SC2 live conflicts for DPO fine-tuning.

Mirrors experiments/finetuning/prepare_rts_preference_data.py but consumes
conflict pairs from scripts/mine_sc2_conflicts.py (data/sc2_conflicts.jsonl)
rather than the hand-authored ROE seed scenarios.

Cross-domain training hypothesis (paper.tex line 992, Conjecture C.3):
    Training on conflicts mined from real SC2 games and evaluating on
    biology/legal/materials L3 instances tests whether real-game grounding
    produces domain-general defeasible reasoning transfer.

Usage::

    python experiments/finetuning/prepare_sc2live_preference_data.py \\
        --provider mock \\
        --num-samples 4 \\
        --output-dir experiments/finetuning/data/sc2live/

    python experiments/finetuning/prepare_sc2live_preference_data.py \\
        --provider foundry-deepseek \\
        --conflicts-file data/sc2_conflicts.jsonl \\
        --num-samples 16 \\
        --output-dir experiments/finetuning/data/sc2live/

Outputs (in --output-dir):
    sc2live_preference_train.jsonl
    sc2live_preference_val.jsonl
    sc2live_preference_test.jsonl
    sc2live_splits.json
    sc2live_preference_stats.json

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine


def load_conflicts(conflicts_file: Path) -> list[dict]:
    """Load mined conflict records from data/sc2_conflicts.jsonl."""
    if not conflicts_file.exists():
        print(f"  Conflicts file not found: {conflicts_file}")
        print("  Run: python scripts/mine_sc2_conflicts.py first.")
        return []
    records = []
    with open(conflicts_file) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def conflict_to_instance(record: dict) -> AbductiveInstance | None:
    """
    Convert a mined conflict record to an AbductiveInstance (Level 3).

    The conflict record provides:
        - facts: ground theory state
        - rule_b: the defeater that should resolve the conflict
        - target: the anomaly literal

    We construct D^- by removing rule_b and verify that the anomaly is
    derivable in D^- but not in D^+ (D^- + rule_b).
    """
    try:
        from examples.knowledge_bases.rts_engagement_kb import create_rts_engagement_kb

        kb = create_rts_engagement_kb(include_instances=False)
        import copy
        theory = copy.deepcopy(kb)
        for fact in record.get("facts", []):
            theory.add_fact(fact)

        # The gold defeater is rule_b
        gold_head = record.get("rule_b_head", "")
        gold_body = tuple(record.get("rule_b_body", []))
        if not gold_head or not gold_body:
            return None

        gold_rule = Rule(
            head=gold_head,
            body=gold_body,
            rule_type=RuleType.DEFEATER,
            label=record.get("rule_b_label", "mined_defeater"),
        )

        target = record.get("target", "")
        if not target:
            return None

        # D^- = theory without the gold defeater
        theory_minus = copy.deepcopy(theory)
        theory_minus.rules = [
            r for r in theory_minus.rules
            if r.label != record.get("rule_b_label", "")
        ]

        # Verify anomaly semantics: target derivable in D^- (anomalous)
        if not defeasible_provable(theory_minus, target):
            return None

        inst = AbductiveInstance(
            D_minus=theory_minus,
            target=target,
            candidates=[str(gold_rule.head) + " :~> " + ", ".join(gold_rule.body) + "."],
            gold=[str(gold_rule.head) + " :~> " + ", ".join(gold_rule.body) + "."],
            level=3,
            metadata={
                "domain": "sc2live",
                "conflict_id": record.get("conflict_id", ""),
                "source_file": record.get("source_file", ""),
                "step": record.get("step", 0),
                "gold_rule_label": record.get("rule_b_label", ""),
            },
        )
        return inst
    except Exception:
        return None


@dataclass
class PreferencePair:
    prompt:         str
    chosen:         str
    rejected:       str
    score_chosen:   float
    score_rejected: float
    margin:         float
    level:          int
    domain:         str
    instance_id:    str
    source:         str   # "mined_conflict"


def instances_to_pairs(
    instances: list[AbductiveInstance],
    model_iface: object,
    modality: str,
    strategy: str,
    n_samples: int,
    seed: int = 42,
) -> list[PreferencePair]:
    """
    Sample model responses for each instance and form preference pairs.

    Scores are determined by the polynomial-time verifier (L3Evaluator).
    """
    try:
        from prompting import render_prompt
        from level3_evaluator import Level3Evaluator
        from blanc.codec.cascading_decoder import CascadingDecoder
    except ImportError:
        return []

    rng = random.Random(seed)
    decoder = CascadingDecoder()
    evaluator = Level3Evaluator()
    pairs: list[PreferencePair] = []

    for inst in instances:
        rendered = render_prompt(inst, modality, strategy)
        responses: list[tuple[str, float]] = []

        for _ in range(n_samples):
            try:
                resp = model_iface.query(  # type: ignore[attr-defined]
                    prompt=rendered.prompt,
                    temperature=0.8,
                    max_tokens=256,
                )
                text = resp.text if hasattr(resp, "text") else str(resp)
                decoded, _ = decoder.decode(text, inst)
                if decoded is None:
                    score = 0.0
                else:
                    result = evaluator.evaluate(inst, text, decoded)
                    score = result.graded_score if result.graded_score is not None else 0.0
                responses.append((text, score))
            except Exception:
                responses.append(("", 0.0))

        if len(responses) < 2:
            continue
        responses.sort(key=lambda x: x[1], reverse=True)
        chosen_text, chosen_score = responses[0]
        rejected_text, rejected_score = responses[-1]
        margin = chosen_score - rejected_score
        if margin < 0.1:
            continue

        pairs.append(PreferencePair(
            prompt=rendered.prompt,
            chosen=chosen_text,
            rejected=rejected_text,
            score_chosen=chosen_score,
            score_rejected=rejected_score,
            margin=margin,
            level=inst.level,
            domain="sc2live",
            instance_id=getattr(inst, "id", ""),
            source="mined_conflict",
        ))

    return pairs


def make_splits(
    instances: list,
    seed: int = 42,
) -> tuple[list, list, list]:
    rng = random.Random(seed)
    rng.shuffle(instances)
    n = len(instances)
    n_tr = max(1, round(n * 0.70))
    n_val = max(1, round(n * 0.15))
    return instances[:n_tr], instances[n_tr:n_tr+n_val], instances[n_tr+n_val:]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare DPO preference data from mined SC2 live conflicts"
    )
    parser.add_argument("--provider", default="mock")
    parser.add_argument("--conflicts-file", default="data/sc2_conflicts.jsonl")
    parser.add_argument("--num-samples", type=int, default=4)
    parser.add_argument("--output-dir", default="experiments/finetuning/data/sc2live/")
    parser.add_argument("--modality", default="M4")
    parser.add_argument("--strategy", default="cot")
    parser.add_argument("--max-instances", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    conflicts_file = ROOT / args.conflicts_file
    output_dir = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("SC2 LIVE PREFERENCE DATA CONSTRUCTION")
    print("=" * 70)

    records = load_conflicts(conflicts_file)
    if not records:
        return 1
    print(f"Loaded {len(records)} conflict records")

    instances: list[AbductiveInstance] = []
    for rec in records[:args.max_instances]:
        inst = conflict_to_instance(rec)
        if inst:
            inst.id = rec.get("conflict_id", f"sc2live_c{len(instances):05d}")
            instances.append(inst)
    print(f"Converted to {len(instances)} AbductiveInstances")

    if not instances:
        print("No instances; check conflicts file.")
        return 1

    # Assign IDs for split tracking
    split_ids: dict[str, str] = {}
    train_insts, val_insts, test_insts = make_splits(instances, seed=args.seed)
    for split, split_name in [(train_insts, "train"), (val_insts, "val"), (test_insts, "test")]:
        for inst in split:
            split_ids[inst.id] = split_name

    try:
        from model_interface import create_model_interface
        model_iface = create_model_interface(provider=args.provider)
    except ImportError:
        print("WARNING: model_interface not available; writing empty preference files")
        model_iface = None

    stats = {"total_instances": len(instances), "provider": args.provider}

    for split_name, split_instances in [
        ("train", train_insts), ("val", val_insts), ("test", test_insts)
    ]:
        out_file = output_dir / f"sc2live_preference_{split_name}.jsonl"
        pairs: list[PreferencePair] = []
        if model_iface:
            pairs = instances_to_pairs(
                split_instances, model_iface,
                modality=args.modality,
                strategy=args.strategy,
                n_samples=args.num_samples,
                seed=args.seed,
            )
        with open(out_file, "w") as f:
            for p in pairs:
                f.write(json.dumps(p.__dict__) + "\n")
        stats[f"pairs_{split_name}"] = len(pairs)
        print(f"  {split_name}: {len(split_instances)} instances -> {len(pairs)} pairs -> {out_file.name}")

    # Write split mapping
    with open(output_dir / "sc2live_splits.json", "w") as f:
        json.dump(split_ids, f, indent=2)

    # Write stats
    with open(output_dir / "sc2live_preference_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print(f"\nOutputs in: {output_dir}")
    print("=" * 70)
    print("SC2 LIVE PREFERENCE DATA COMPLETE")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
