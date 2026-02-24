"""
Phase B1: Preference Dataset Construction for DeFAb Fine-Tuning.

Implements Section 6.2 of the paper (Preference Data Construction):

  1. Load all DeFAb instances and create stratified 70/15/15 splits.
  2. For each training instance, sample n responses from a model at
     temperature > 0 (default n=16, T=0.7).
  3. Decode each response via the D1->D2->D3 cascade.
  4. Score each response using the DeFAb verifier (Equation 5 in paper):
       r(y) = S_defab(y, x)
     Level 2: binary {0, 1}
     Level 3: graded {0, 0.25, 0.5, 0.75, 1.0}
  5. Extract preference pairs (y_w, y_l) where r(y_w) > r(y_l) and
     margin r(y_w) - r(y_l) >= min_margin.
  6. Add gold-anchored pairs: gold vs each incorrect sampled response.
  7. Save as JSONLines with HuggingFace DPO format.

Provider support
----------------
Designed to work with any ModelInterface.  The two primary use cases are:
  - CURC vLLM (--provider curc  --base-url http://localhost:8000)
  - Azure AI Foundry (--provider foundry-gpt | foundry-kimi | foundry-claude | foundry-deepseek)

Usage
-----
  # Foundry (run locally, no SLURM needed)
  python experiments/finetuning/prepare_preference_data.py \\
      --provider foundry-gpt \\
      --num-samples 8 \\
      --output-dir experiments/finetuning/data/

  # CURC vLLM (inside SLURM job; vLLM server already running)
  python experiments/finetuning/prepare_preference_data.py \\
      --provider curc \\
      --base-url http://localhost:8000 \\
      --model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --num-samples 16 \\
      --output-dir experiments/finetuning/data/

Author: Patrick Cooper
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
from blanc.author.loaders import load_instances_from_json
from model_interface import create_model_interface, ModelInterface
from prompting import render_prompt
from blanc.codec.cascading_decoder import CascadingDecoder
from level3_evaluator import Level3Evaluator


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_response(
    response_text: str,
    instance: AbductiveInstance,
    decoder: CascadingDecoder,
    l3_evaluator: Level3Evaluator,
) -> tuple[float, str]:
    """
    Score *response_text* against *instance* using the DeFAb verifier.

    Returns (score, decoded_hypothesis):
      Level 2: score in {0.0, 1.0}
      Level 3: score in {0.0, 0.25, 0.5, 0.75, 1.0}
    """
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

    # Level 3: graded score via Level3Evaluator
    try:
        result = l3_evaluator.evaluate(instance, response_text, decoded)
        return result.graded_score if result.graded_score is not None else 0.0, decoded
    except Exception:
        return 0.0, decoded


# ---------------------------------------------------------------------------
# Stratified split
# ---------------------------------------------------------------------------

def make_splits(
    instances: list[AbductiveInstance],
    train_frac: float = 0.70,
    val_frac:   float = 0.15,
    seed:       int   = 42,
) -> tuple[list[AbductiveInstance], list[AbductiveInstance], list[AbductiveInstance]]:
    """
    Stratified 70/15/15 split by (level, domain).  Returns (train, val, test).
    """
    from collections import defaultdict
    rng = random.Random(seed)

    strata: dict[tuple, list[AbductiveInstance]] = defaultdict(list)
    for inst in instances:
        level  = getattr(inst, "level", 2)
        domain = inst.metadata.get("domain", "unknown") if hasattr(inst, "metadata") else "unknown"
        strata[(level, domain)].append(inst)

    train_set: list[AbductiveInstance] = []
    val_set:   list[AbductiveInstance] = []
    test_set:  list[AbductiveInstance] = []

    for key, group in strata.items():
        rng.shuffle(group)
        n      = len(group)
        n_tr   = max(1, round(n * train_frac))
        n_val  = max(1, round(n * val_frac))
        train_set.extend(group[:n_tr])
        val_set.extend(group[n_tr : n_tr + n_val])
        test_set.extend(group[n_tr + n_val :])

    return train_set, val_set, test_set


# ---------------------------------------------------------------------------
# Preference pair record
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Response sampling
# ---------------------------------------------------------------------------

def sample_responses(
    instance:     AbductiveInstance,
    model:        ModelInterface,
    modality:     str,
    strategy:     str,
    n:            int,
    temperature:  float,
    decoder:      CascadingDecoder,
    l3_evaluator: Level3Evaluator,
) -> list[tuple[str, float, str]]:
    """
    Sample *n* responses from *model* and score them.

    Returns list of (response_text, score, decoded_hypothesis).
    """
    rendered = render_prompt(instance, modality, strategy)
    results  = []

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


# ---------------------------------------------------------------------------
# Preference pair extraction
# ---------------------------------------------------------------------------

def extract_pairs(
    instance:    AbductiveInstance,
    responses:   list[tuple[str, float, str]],
    rendered_prompt: str,
    modality:    str,
    strategy:    str,
    min_margin:  float,
) -> list[PreferencePair]:
    """Extract (chosen, rejected) pairs with margin >= min_margin."""
    level  = getattr(instance, "level", 2)
    domain = (instance.metadata or {}).get("domain", "unknown")
    iid    = getattr(instance, "id", "unknown")
    pairs  = []

    for i in range(len(responses)):
        for j in range(len(responses)):
            if i == j:
                continue
            text_i, score_i, _ = responses[i]
            text_j, score_j, _ = responses[j]
            margin = score_i - score_j
            if margin >= min_margin:
                pairs.append(PreferencePair(
                    prompt         = rendered_prompt,
                    chosen         = text_i,
                    rejected       = text_j,
                    score_chosen   = score_i,
                    score_rejected = score_j,
                    margin         = margin,
                    level          = level,
                    domain         = domain,
                    instance_id    = iid,
                    modality       = modality,
                    strategy       = strategy,
                    source         = "sampled",
                ))
    return pairs


def extract_gold_anchored_pairs(
    instance:    AbductiveInstance,
    responses:   list[tuple[str, float, str]],
    rendered_prompt: str,
    modality:    str,
    strategy:    str,
) -> list[PreferencePair]:
    """Anchor gold hypothesis against each incorrect sampled response."""
    level  = getattr(instance, "level", 2)
    domain = (instance.metadata or {}).get("domain", "unknown")
    iid    = getattr(instance, "id", "unknown")
    gold   = instance.gold[0] if instance.gold else ""
    if not gold:
        return []

    pairs = []
    for text, score, _ in responses:
        if score < 1.0:
            pairs.append(PreferencePair(
                prompt         = rendered_prompt,
                chosen         = gold,
                rejected       = text,
                score_chosen   = 1.0,
                score_rejected = score,
                margin         = 1.0 - score,
                level          = level,
                domain         = domain,
                instance_id    = iid,
                modality       = modality,
                strategy       = strategy,
                source         = "gold_anchored",
            ))
    return pairs


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build DeFAb preference dataset for DPO/RLHF fine-tuning."
    )
    # Model
    p.add_argument("--provider", default="foundry-gpt",
                   choices=["curc", "foundry-gpt", "foundry-kimi",
                            "foundry-claude", "foundry-deepseek",
                            "openai", "anthropic", "mock"],
                   help="Model provider for response sampling.")
    p.add_argument("--model-name", default=None,
                   help="Model name (for curc/openai providers).")
    p.add_argument("--base-url", default=None,
                   help="Base URL (for curc provider).")
    p.add_argument("--api-key", default=None,
                   help="API key. Falls back to FOUNDRY_API_KEY or OPENAI_API_KEY.")

    # Sampling
    p.add_argument("--num-samples", type=int, default=16,
                   help="Number of responses to sample per instance (default 16).")
    p.add_argument("--temperature", type=float, default=0.7,
                   help="Sampling temperature (default 0.7).")
    p.add_argument("--min-margin", type=float, default=0.25,
                   help="Minimum score gap to form a preference pair (default 0.25).")

    # Instances
    p.add_argument("--instances-dir", default="instances",
                   help="Directory containing instance JSON files.")
    p.add_argument("--domains", nargs="+",
                   default=["biology", "legal", "materials"])
    p.add_argument("--modalities", nargs="+", default=["M4"],
                   help="Modalities to render prompts in (default M4).")
    p.add_argument("--strategies", nargs="+", default=["direct"],
                   help="Prompting strategies (default direct).")
    p.add_argument("--instance-limit", type=int, default=None,
                   help="Max instances per domain (for smoke tests).")
    p.add_argument("--level3-limit", type=int, default=None,
                   help="Max Level 3 instances.")

    # Output
    p.add_argument("--output-dir", default="experiments/finetuning/data",
                   help="Where to write preference JSONL files.")
    p.add_argument("--splits-file", default="instances/splits.json",
                   help="Where to save/load train/val/test split IDs.")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed for splits and shuffling.")

    return p.parse_args()


def _build_model(args: argparse.Namespace) -> ModelInterface:
    api_key = (
        args.api_key
        or os.environ.get("FOUNDRY_API_KEY", "")
        or os.environ.get("OPENAI_API_KEY", "")
    )

    kwargs: dict = {}
    if args.provider == "curc":
        if args.base_url:
            kwargs["base_url"] = args.base_url
        if args.model_name:
            kwargs["model"] = args.model_name
    elif args.provider == "openai":
        kwargs["api_key"] = api_key
        if args.model_name:
            kwargs["model"] = args.model_name
    elif args.provider == "anthropic":
        kwargs["api_key"] = api_key
    elif args.provider.startswith("foundry"):
        kwargs["api_key"] = api_key

    return create_model_interface(args.provider, **kwargs)


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb Preference Data Construction")
    print("=" * 70)
    print(f"  Provider     : {args.provider}")
    print(f"  Num samples  : {args.num_samples}")
    print(f"  Temperature  : {args.temperature}")
    print(f"  Min margin   : {args.min_margin}")
    print(f"  Modalities   : {args.modalities}")
    print(f"  Strategies   : {args.strategies}")
    print()

    instances_dir = ROOT / args.instances_dir
    output_dir    = ROOT / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- Load all instances ---
    print("Loading instances...")
    all_instances = load_instances_from_json(
        instances_dir,
        domains=args.domains,
        include_level3=True,
        level2_limit=args.instance_limit,
        level3_limit=args.level3_limit,
    )
    print(f"  Loaded {len(all_instances)} instances")

    # --- Train/val/test split ---
    splits_file = ROOT / args.splits_file
    if splits_file.exists():
        print(f"Loading existing splits from {splits_file}")
        with open(splits_file) as f:
            splits_data = json.load(f)
        train_ids = set(splits_data["train"])
        val_ids   = set(splits_data["val"])
        test_ids  = set(splits_data["test"])
        train_set = [i for i in all_instances if i.id in train_ids]
        val_set   = [i for i in all_instances if i.id in val_ids]
        test_set  = [i for i in all_instances if i.id in test_ids]
    else:
        print("Creating new stratified 70/15/15 split...")
        train_set, val_set, test_set = make_splits(
            all_instances, train_frac=0.70, val_frac=0.15, seed=args.seed
        )
        splits_data = {
            "train": [i.id for i in train_set],
            "val":   [i.id for i in val_set],
            "test":  [i.id for i in test_set],
        }
        splits_file.parent.mkdir(parents=True, exist_ok=True)
        with open(splits_file, "w") as f:
            json.dump(splits_data, f, indent=2)
        print(f"  Saved splits to {splits_file}")

    print(f"  Train: {len(train_set)}  Val: {len(val_set)}  Test: {len(test_set)}")

    # --- Build model interface ---
    print(f"\nConnecting to {args.provider}...")
    try:
        model = _build_model(args)
        # Warm-up check
        _ = model.query("Say OK.", max_tokens=5)
        print(f"  Connected: {model.model_name}")
    except Exception as exc:
        print(f"  ERROR: Could not connect to model: {exc}")
        return 1

    # --- Set up decoder and evaluator ---
    decoder      = CascadingDecoder()
    l3_evaluator = Level3Evaluator()

    # --- Determine output file name ---
    model_slug = args.model_name or args.provider
    model_slug = model_slug.replace("/", "_").replace(":", "_")
    output_file = output_dir / f"preferences_{model_slug}.jsonl"
    splits_out  = output_dir / f"splits_{model_slug}.json"

    print(f"\nOutput: {output_file}")
    total_pairs = 0

    with open(output_file, "w") as out_f:
        for inst_idx, instance in enumerate(train_set):
            level  = getattr(instance, "level", 2)
            domain = (instance.metadata or {}).get("domain", "")
            iid    = getattr(instance, "id", f"inst-{inst_idx}")

            print(f"\n[{inst_idx+1}/{len(train_set)}] {iid}  L{level}  {domain}")

            for modality in args.modalities:
                for strategy in args.strategies:
                    rendered = render_prompt(instance, modality, strategy)

                    # Sample n responses
                    responses = sample_responses(
                        instance, model, modality, strategy,
                        args.num_samples, args.temperature,
                        decoder, l3_evaluator,
                    )
                    if not responses:
                        print(f"    No responses for {modality}/{strategy}, skipping")
                        continue

                    scores = [sc for _, sc, _ in responses]
                    print(f"    {modality}/{strategy}: "
                          f"{len(responses)} samples, "
                          f"scores=[{min(scores):.2f}..{max(scores):.2f}]")

                    # Sampled preference pairs
                    pairs = extract_pairs(
                        instance, responses, rendered.prompt,
                        modality, strategy, args.min_margin,
                    )
                    # Gold-anchored pairs
                    pairs += extract_gold_anchored_pairs(
                        instance, responses, rendered.prompt,
                        modality, strategy,
                    )

                    for pair in pairs:
                        out_f.write(json.dumps(asdict(pair)) + "\n")
                    total_pairs += len(pairs)
                    print(f"    Extracted {len(pairs)} preference pairs")

    print(f"\n{'='*70}")
    print(f"Done.  Total preference pairs written: {total_pairs}")
    print(f"Output : {output_file}")

    # Save split membership to data dir for reproducibility
    with open(splits_out, "w") as f:
        json.dump({
            "model": args.provider,
            "num_samples": args.num_samples,
            "temperature": args.temperature,
            "min_margin": args.min_margin,
            **splits_data,
        }, f, indent=2)
    print(f"Splits : {splits_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
