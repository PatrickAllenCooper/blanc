"""
Build DeFAb-ROE preference dataset for DPO fine-tuning.

This script mirrors the main preference data pipeline
(experiments/finetuning/prepare_preference_data.py) but operates specifically
on the RTS engagement knowledge base, generating preference pairs for the
ROE exception reasoning domain.

The verifier used for scoring is identical to the one used for the existing
biology/legal/materials domains: the polynomial-time DefeasibleEngine checks
resolution, conservativity, minimality, and novelty for each sampled response.
This is the key property that makes DPO fine-tuning on ROE instances directly
analogous to fine-tuning on the existing domains.

Cross-domain training hypothesis:
    Training on ROE instances and evaluating on biology/legal/materials
    tests whether defeasible exception reasoning is domain-general.
    This is the central empirical claim of the paper: DeFAb isolates a
    formal reasoning capability that transfers across subject domains.

Usage:
    # Mock dry-run
    python experiments/finetuning/prepare_rts_preference_data.py \\
        --provider mock \\
        --num-samples 4 \\
        --output-dir experiments/finetuning/data/rts/

    # Foundry production run
    python experiments/finetuning/prepare_rts_preference_data.py \\
        --provider foundry-deepseek \\
        --num-samples 16 \\
        --output-dir experiments/finetuning/data/rts/

    # CURC vLLM
    python experiments/finetuning/prepare_rts_preference_data.py \\
        --provider curc \\
        --base-url http://localhost:8000 \\
        --model-name Qwen/Qwen2.5-72B-Instruct-AWQ \\
        --num-samples 16 \\
        --output-dir experiments/finetuning/data/rts/

Outputs (in --output-dir):
    rts_preference_train.jsonl   -- training preference pairs (JSONL, HF DPO format)
    rts_preference_val.jsonl     -- validation set
    rts_preference_test.jsonl    -- held-out test set
    rts_splits.json              -- instance ID -> split mapping
    rts_preference_stats.json    -- counts, margins, error breakdown

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from blanc.author.generation import AbductiveInstance
from blanc.core.theory import Theory, Rule, RuleType
from model_interface import create_model_interface, ModelInterface
from prompting import render_prompt
from blanc.codec.cascading_decoder import CascadingDecoder
from level3_evaluator import Level3Evaluator


# ── Shared helpers (duplicated here to avoid circular imports) ────────────────

def score_response(
    response_text: str,
    instance: AbductiveInstance,
    decoder: CascadingDecoder,
    l3_evaluator: Level3Evaluator,
) -> tuple[float, str]:
    """Score response_text against instance using the DeFAb verifier."""
    try:
        decoded, stage = decoder.decode(response_text, instance)
    except Exception:
        return 0.0, ""
    if decoded is None:
        return 0.0, ""
    level = getattr(instance, "level", 2)
    if level < 3:
        gold = instance.gold or []
        correct = any(decoded.strip().lower() == g.strip().lower() for g in gold)
        return 1.0 if correct else 0.0, decoded
    try:
        result = l3_evaluator.evaluate(instance, response_text, decoded)
        return result.graded_score if result.graded_score is not None else 0.0, decoded
    except Exception:
        return 0.0, decoded


def make_splits(
    instances: list[AbductiveInstance],
    train_frac: float = 0.70,
    val_frac: float = 0.15,
    seed: int = 42,
) -> tuple[list[AbductiveInstance], list[AbductiveInstance], list[AbductiveInstance]]:
    """Stratified 70/15/15 split by (level, domain). Returns (train, val, test)."""
    from collections import defaultdict
    rng = random.Random(seed)
    strata: dict = defaultdict(list)
    for inst in instances:
        level = getattr(inst, "level", 2)
        domain = (inst.metadata or {}).get("domain", "rts_engagement")
        strata[(level, domain)].append(inst)
    train, val, test = [], [], []
    for key, group in strata.items():
        rng.shuffle(group)
        n = len(group)
        n_tr = max(1, round(n * train_frac))
        n_val = max(1, round(n * val_frac))
        train.extend(group[:n_tr])
        val.extend(group[n_tr:n_tr + n_val])
        test.extend(group[n_tr + n_val:])
    return train, val, test


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
    modality:       str
    strategy:       str
    source:         str   # "sampled" | "gold_anchored"


def sample_responses(
    instance: AbductiveInstance,
    model: ModelInterface,
    modality: str,
    strategy: str,
    n: int,
    temperature: float,
    decoder: CascadingDecoder,
    l3_evaluator: Level3Evaluator,
) -> list[tuple[str, float, str]]:
    rendered = render_prompt(instance, modality, strategy)
    results = []
    for _ in range(n):
        try:
            resp = model.query(
                prompt=rendered.prompt,
                temperature=temperature,
                max_tokens=512,
            )
            sc, decoded = score_response(resp.text, instance, decoder, l3_evaluator)
            results.append((resp.text, sc, decoded))
        except Exception as exc:
            print(f"    Warning: query failed: {exc}")
            time.sleep(2)
    return results


def extract_pairs(
    instance: AbductiveInstance,
    responses: list[tuple[str, float, str]],
    rendered_prompt: str,
    modality: str,
    strategy: str,
    min_margin: float,
) -> list[PreferencePair]:
    level = getattr(instance, "level", 2)
    domain = (instance.metadata or {}).get("domain", "rts_engagement")
    iid = getattr(instance, "id", "unknown")
    pairs = []
    for i in range(len(responses)):
        for j in range(len(responses)):
            if i == j:
                continue
            text_i, score_i, _ = responses[i]
            text_j, score_j, _ = responses[j]
            margin = score_i - score_j
            if margin >= min_margin:
                pairs.append(PreferencePair(
                    prompt=rendered_prompt, chosen=text_i, rejected=text_j,
                    score_chosen=score_i, score_rejected=score_j, margin=margin,
                    level=level, domain=domain, instance_id=iid,
                    modality=modality, strategy=strategy, source="sampled",
                ))
    return pairs


def extract_gold_anchored_pairs(
    instance: AbductiveInstance,
    responses: list[tuple[str, float, str]],
    rendered_prompt: str,
    modality: str,
    strategy: str,
) -> list[PreferencePair]:
    level = getattr(instance, "level", 2)
    domain = (instance.metadata or {}).get("domain", "rts_engagement")
    iid = getattr(instance, "id", "unknown")
    gold = instance.gold[0] if instance.gold else ""
    if not gold:
        return []
    pairs = []
    for text, score, _ in responses:
        if score < 1.0:
            pairs.append(PreferencePair(
                prompt=rendered_prompt, chosen=gold, rejected=text,
                score_chosen=1.0, score_rejected=score, margin=1.0 - score,
                level=level, domain=domain, instance_id=iid,
                modality=modality, strategy=strategy, source="gold_anchored",
            ))
    return pairs


# ── RTS instance loading ──────────────────────────────────────────────────────

def load_rts_instances_for_finetuning(
    instances_dir: Path,
    limit: Optional[int] = None,
) -> list[AbductiveInstance]:
    """Load all RTS engagement instances for fine-tuning."""
    rts_file = instances_dir / "rts_engagement_instances.json"
    if not rts_file.exists():
        print(f"  Warning: {rts_file} not found.")
        print("  Run: python scripts/generate_rts_instances.py")
        return []

    with open(rts_file) as f:
        data = json.load(f)

    all_records = data.get("instances", [])
    if limit:
        all_records = all_records[:limit]

    instances = []
    for i, item in enumerate(all_records):
        level = item.get("level", 2)
        facts = list(item.get("theory_facts", item.get("metadata", {}).get("facts", [])))
        rules_raw = item.get("theory_rules", [])

        rules = []
        for rule_item in rules_raw:
            if isinstance(rule_item, dict):
                try:
                    rules.append(Rule(
                        head=rule_item.get("head", ""),
                        body=tuple(rule_item.get("body", [])),
                        rule_type=RuleType(rule_item.get("rule_type", "defeasible")),
                        label=rule_item.get("label"),
                    ))
                except (ValueError, TypeError):
                    continue
            elif isinstance(rule_item, str) and ("=>" in rule_item or ":-" in rule_item):
                # Parse string-format rule
                if "~>" in rule_item:
                    body_part, head_part = rule_item.split("~>", 1)
                    rtype = RuleType.DEFEATER
                elif "=>" in rule_item:
                    body_part, head_part = rule_item.split("=>", 1)
                    rtype = RuleType.DEFEASIBLE
                else:
                    body_part, head_part = rule_item.split(":-", 1)
                    rtype = RuleType.STRICT
                body_atoms = tuple(b.strip() for b in body_part.split(",") if b.strip())
                rules.append(Rule(head=head_part.strip(), body=body_atoms, rule_type=rtype))

        d_minus = Theory(facts=set(facts), rules=rules, superiority={})

        inst = AbductiveInstance(
            D_minus=d_minus,
            target=item.get("anomaly", item.get("target", "")),
            candidates=item.get("candidates", []),
            gold=(
                [item["gold"]] if isinstance(item.get("gold"), str)
                else item.get("gold", [])
            ),
            level=level,
            metadata={
                "domain": "rts_engagement",
                "scenario_id": item.get("scenario_id", f"rts-{i:04d}"),
                **item.get("metadata", {}),
            },
        )
        inst.id = f"rts-l{level}-{item.get('scenario_id', i)}"
        instances.append(inst)

    return instances


# ── Main ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build DeFAb-ROE preference dataset for DPO fine-tuning."
    )
    p.add_argument("--provider", default="foundry-gpt",
                   choices=["curc", "foundry-gpt", "foundry-kimi",
                            "foundry-claude", "foundry-deepseek",
                            "openai", "anthropic", "mock"])
    p.add_argument("--model-name", default=None)
    p.add_argument("--base-url", default=None)
    p.add_argument("--api-key", default=None)
    p.add_argument("--num-samples", type=int, default=16)
    p.add_argument("--temperature", type=float, default=0.7)
    p.add_argument("--min-margin", type=float, default=0.25)
    p.add_argument("--modalities", nargs="+", default=["M4"])
    p.add_argument("--strategies", nargs="+", default=["direct"])
    p.add_argument("--instances-dir", default=str(ROOT / "instances"))
    p.add_argument("--instance-limit", type=int, default=None)
    p.add_argument("--output-dir", default=str(ROOT / "experiments" / "finetuning" / "data" / "rts"))
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def main() -> int:
    args = parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    instances_dir = Path(args.instances_dir)

    print("=" * 70)
    print("DeFAb-ROE Preference Data Construction")
    print("=" * 70)
    print(f"Provider    : {args.provider}")
    print(f"Samples/inst: {args.num_samples}")
    print(f"Min margin  : {args.min_margin}")
    print(f"Modalities  : {args.modalities}")
    print(f"Strategies  : {args.strategies}")
    print(f"Output dir  : {output_dir}")
    print()

    # ── Load instances ────────────────────────────────────────────────────────
    print("Loading RTS engagement instances...")
    instances = load_rts_instances_for_finetuning(instances_dir, limit=args.instance_limit)
    if not instances:
        return 1
    print(f"  Loaded {len(instances)} instances")

    # ── Stratified split ──────────────────────────────────────────────────────
    train_set, val_set, test_set = make_splits(instances, seed=args.seed)
    print(f"  Split: {len(train_set)} train / {len(val_set)} val / {len(test_set)} test")

    splits_map = {}
    for inst in train_set:
        splits_map[getattr(inst, "id", "")] = "train"
    for inst in val_set:
        splits_map[getattr(inst, "id", "")] = "val"
    for inst in test_set:
        splits_map[getattr(inst, "id", "")] = "test"
    with open(output_dir / "rts_splits.json", "w") as f:
        json.dump(splits_map, f, indent=2)
    print(f"  Split map saved.")

    # ── Build model interface ─────────────────────────────────────────────────
    api_key = args.api_key
    kwargs: dict = {}
    if args.provider == "curc":
        kwargs["base_url"] = args.base_url or "http://localhost:8000"
        if args.model_name:
            kwargs["model"] = args.model_name
    elif args.provider.startswith("foundry-"):
        if not api_key:
            api_key = os.getenv("FOUNDRY_API_KEY")
        if args.base_url:
            kwargs["base_url"] = args.base_url

    try:
        model = create_model_interface(args.provider, api_key=api_key, **kwargs)
    except Exception as e:
        print(f"ERROR: Could not create model interface: {e}")
        return 1

    decoder = CascadingDecoder()
    l3_evaluator = Level3Evaluator()

    # ── Process training set ──────────────────────────────────────────────────
    print(f"\nProcessing {len(train_set)} training instances...")
    train_pairs: list[PreferencePair] = []
    val_pairs: list[PreferencePair] = []

    for split_name, split_set in [("train", train_set), ("val", val_set)]:
        print(f"\n  {split_name.upper()} SET ({len(split_set)} instances)")
        all_pairs: list[PreferencePair] = []

        for idx, inst in enumerate(split_set):
            level = getattr(inst, "level", 2)
            iid = getattr(inst, "id", f"rts-{idx}")
            print(f"    [{idx+1:3d}/{len(split_set)}] {iid} (L{level})", end=" ")

            for modality in args.modalities:
                for strategy in args.strategies:
                    responses = sample_responses(
                        inst, model, modality, strategy,
                        n=args.num_samples,
                        temperature=args.temperature,
                        decoder=decoder,
                        l3_evaluator=l3_evaluator,
                    )
                    rendered = render_prompt(inst, modality, strategy)

                    # Sampled pairs
                    sampled = extract_pairs(
                        inst, responses, rendered.prompt,
                        modality, strategy, args.min_margin,
                    )
                    # Gold-anchored pairs
                    gold_anchored = extract_gold_anchored_pairs(
                        inst, responses, rendered.prompt,
                        modality, strategy,
                    )
                    all_pairs.extend(sampled)
                    all_pairs.extend(gold_anchored)

            scores = [r[1] for r in responses] if responses else []
            avg_score = sum(scores) / len(scores) if scores else 0.0
            print(f"avg_score={avg_score:.3f} pairs={len(all_pairs)}")

        if split_name == "train":
            train_pairs = all_pairs
        else:
            val_pairs = all_pairs

    # ── Save JSONL ────────────────────────────────────────────────────────────
    def _save_jsonl(pairs: list[PreferencePair], path: Path) -> None:
        with open(path, "w") as f:
            for pair in pairs:
                record = {
                    "prompt":   pair.prompt,
                    "chosen":   pair.chosen,
                    "rejected": pair.rejected,
                    "margins":  pair.margin,
                    # Extra metadata useful for analysis
                    "level":       pair.level,
                    "domain":      pair.domain,
                    "instance_id": pair.instance_id,
                    "modality":    pair.modality,
                    "strategy":    pair.strategy,
                    "source":      pair.source,
                }
                f.write(json.dumps(record) + "\n")

    _save_jsonl(train_pairs, output_dir / "rts_preference_train.jsonl")
    _save_jsonl(val_pairs, output_dir / "rts_preference_val.jsonl")

    # ── Statistics ────────────────────────────────────────────────────────────
    def _stats(pairs: list[PreferencePair]) -> dict:
        if not pairs:
            return {"total": 0}
        from collections import Counter
        levels = Counter(p.level for p in pairs)
        sources = Counter(p.source for p in pairs)
        margins = [p.margin for p in pairs]
        return {
            "total": len(pairs),
            "by_level": dict(levels),
            "by_source": dict(sources),
            "mean_margin": sum(margins) / len(margins),
            "min_margin": min(margins),
            "max_margin": max(margins),
        }

    stats = {
        "train": _stats(train_pairs),
        "val": _stats(val_pairs),
        "provider": args.provider,
        "num_samples": args.num_samples,
        "min_margin": args.min_margin,
        "modalities": args.modalities,
        "strategies": args.strategies,
    }
    with open(output_dir / "rts_preference_stats.json", "w") as f:
        json.dump(stats, f, indent=2)

    print("\n" + "=" * 70)
    print("PREFERENCE DATA CONSTRUCTION COMPLETE")
    print("=" * 70)
    print(f"  Training pairs : {stats['train']['total']}")
    print(f"  Validation pairs: {stats['val']['total']}")
    print(f"  Output dir     : {output_dir}")

    print("\nTo fine-tune with DPO, run:")
    print(f"  python experiments/finetuning/train_dpo.py \\")
    print(f"      --train-file {output_dir}/rts_preference_train.jsonl \\")
    print(f"      --val-file   {output_dir}/rts_preference_val.jsonl \\")
    print(f"      --output-dir experiments/finetuning/checkpoints/rts_dpo/")

    print("\nTo fine-tune with GRPO, run:")
    print(f"  python experiments/finetuning/train_grpo.py \\")
    print(f"      --instances-dir instances/ \\")
    print(f"      --domains rts_engagement \\")
    print(f"      --output-dir experiments/finetuning/checkpoints/rts_grpo/")

    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
