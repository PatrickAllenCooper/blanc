"""
Phase B5: Evaluate a fine-tuned DeFAb model checkpoint.

Runs the standard DeFAb evaluation pipeline (identical methodology to base
model evaluation) on a locally saved LoRA or merged checkpoint, then writes
results to the same JSON format used by analyze_results.py and
generate_paper_tables.py so the fine-tuned and base model results can be
directly compared.

This script populates Table 3 (tab:ft_main) and Table 4 (tab:ft_curriculum)
from Section 6.7 of the paper.

Usage
-----
  # Evaluate a DPO-trained Qwen 72B checkpoint on the held-out test split
  python experiments/finetuning/evaluate_finetuned.py \\
      --checkpoint experiments/finetuning/checkpoints/dpo_standard_qwen72b/final \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --split test \\
      --modalities M4 M2 \\
      --results-dir experiments/results/

  # Quick smoke test (5 instances per domain)
  python experiments/finetuning/evaluate_finetuned.py \\
      --checkpoint /path/to/checkpoint \\
      --base-model Qwen/Qwen2.5-7B-Instruct \\
      --instance-limit 5 \\
      --level3-limit 5

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Thin wrapper -- makes the LoRA checkpoint look like a ModelInterface
# ---------------------------------------------------------------------------

class FinetunedModelInterface:
    """
    Wraps a locally-loaded LoRA checkpoint to satisfy the ModelInterface
    protocol expected by EvaluationPipeline.
    """

    def __init__(
        self,
        checkpoint:  str,
        base_model:  str,
        use_4bit:    bool = False,
        max_new_tokens: int = 512,
    ):
        self._max_new_tokens = max_new_tokens
        self.model_name = f"finetuned:{Path(checkpoint).name}"

        tokenizer_path = checkpoint if Path(checkpoint, "tokenizer_config.json").exists() else base_model
        print(f"  Loading tokenizer from {tokenizer_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(
            tokenizer_path, trust_remote_code=True
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        dtype = torch.bfloat16

        if use_4bit:
            from transformers import BitsAndBytesConfig
            bnb_cfg = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
            print(f"  Loading base model (4-bit) from {base_model}")
            base = AutoModelForCausalLM.from_pretrained(
                base_model,
                quantization_config=bnb_cfg,
                device_map="auto",
                trust_remote_code=True,
            )
        else:
            print(f"  Loading base model from {base_model}")
            base = AutoModelForCausalLM.from_pretrained(
                base_model,
                torch_dtype=dtype,
                device_map="auto",
                trust_remote_code=True,
                attn_implementation="flash_attention_2",
            )

        # Check if checkpoint has adapter_config.json (LoRA) or is a merged model
        if (Path(checkpoint) / "adapter_config.json").exists():
            print(f"  Loading LoRA adapter from {checkpoint}")
            self.model = PeftModel.from_pretrained(base, checkpoint)
            self.model = self.model.merge_and_unload()
        else:
            # Treat checkpoint as a merged model
            print(f"  Loading merged checkpoint from {checkpoint}")
            self.model = AutoModelForCausalLM.from_pretrained(
                checkpoint,
                torch_dtype=dtype,
                device_map="auto",
                trust_remote_code=True,
                attn_implementation="flash_attention_2",
            )

        self.model.eval()
        self._device = next(self.model.parameters()).device

    @property
    def total_cost(self) -> float:
        return 0.0

    def query(
        self,
        prompt:     str,
        max_tokens: Optional[int] = None,
        temperature: float = 0.0,
        **_kwargs,
    ):
        """Generate a response for *prompt*."""
        import time
        from model_interface import ModelResponse

        max_new = max_tokens or self._max_new_tokens
        inputs  = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048,
        ).to(self._device)

        t0 = time.time()
        with torch.inference_mode():
            out_ids = self.model.generate(
                **inputs,
                max_new_tokens=max_new,
                do_sample=(temperature > 0),
                temperature=temperature if temperature > 0 else None,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
        latency = time.time() - t0

        # Strip input tokens
        gen_ids = out_ids[0, inputs["input_ids"].shape[1]:]
        text    = self.tokenizer.decode(gen_ids, skip_special_tokens=True)

        return ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=int(inputs["input_ids"].shape[1]),
            tokens_output=int(len(gen_ids)),
            cost=0.0,
            latency=latency,
            metadata={},
        )


# ---------------------------------------------------------------------------
# CLI and main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Evaluate a fine-tuned DeFAb checkpoint on the test split."
    )
    p.add_argument("--checkpoint", required=True,
                   help="Path to LoRA adapter or merged model checkpoint.")
    p.add_argument("--base-model", required=True,
                   help="HuggingFace ID of the base model (for LoRA checkpoints).")
    p.add_argument("--use-4bit", action="store_true",
                   help="Load base model in 4-bit for memory efficiency.")
    p.add_argument("--max-new-tokens", type=int, default=512)

    # Dataset
    p.add_argument("--split", default="test",
                   choices=["train", "val", "test", "all"],
                   help="Which split to evaluate on.")
    p.add_argument("--instances-dir",   default="instances")
    p.add_argument("--splits-file",     default=None,
                   help="Path to splits JSON (auto-detected from data-dir if omitted).")
    p.add_argument("--data-dir",        default="experiments/finetuning/data",
                   help="Directory with splits_*.json files.")
    p.add_argument("--instance-limit",  type=int, default=None)
    p.add_argument("--level3-limit",    type=int, default=None)

    # Evaluation
    p.add_argument("--modalities", nargs="+", default=["M4", "M2"],
                   help="Modalities to evaluate.")
    p.add_argument("--strategies", nargs="+", default=["direct"],
                   help="Prompting strategies.")
    p.add_argument("--results-dir", default="experiments/results",
                   help="Root directory for output JSON files.")
    p.add_argument("--run-label", default=None,
                   help="Label appended to results filename (default: checkpoint name).")

    return p.parse_args()


def _find_splits_file(data_dir: Path) -> Optional[Path]:
    candidates = sorted(data_dir.glob("splits_*.json"))
    return candidates[0] if candidates else None


def main() -> int:
    args = parse_args()

    label = args.run_label or Path(args.checkpoint).name
    ts    = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print(f"DeFAb Fine-Tuned Model Evaluation")
    print("=" * 70)
    print(f"  Checkpoint : {args.checkpoint}")
    print(f"  Base model : {args.base_model}")
    print(f"  Split      : {args.split}")
    print(f"  Modalities : {args.modalities}")
    print(f"  Strategies : {args.strategies}")

    # --- Load instances ---
    from blanc.author.loaders import load_instances_from_json
    instances_dir = ROOT / args.instances_dir
    data_dir      = ROOT / args.data_dir

    all_instances = load_instances_from_json(
        instances_dir,
        include_level3=True,
        level2_limit=args.instance_limit,
        level3_limit=args.level3_limit,
    )

    if args.split == "all":
        eval_instances = all_instances
    else:
        # Find splits file
        splits_file = None
        if args.splits_file:
            splits_file = Path(args.splits_file)
        else:
            splits_file = _find_splits_file(data_dir)

        if splits_file and splits_file.exists():
            with open(splits_file) as f:
                splits_data = json.load(f)
            split_ids = set(splits_data.get(args.split, []))
            eval_instances = [i for i in all_instances if i.id in split_ids]
            print(f"\n  Using split file: {splits_file}")
        else:
            print(f"\n  Warning: No splits file found; evaluating all {len(all_instances)} instances.")
            eval_instances = all_instances

    print(f"  Evaluating {len(eval_instances)} instances")

    # --- Load fine-tuned model ---
    print("\nLoading fine-tuned model...")
    finetuned = FinetunedModelInterface(
        checkpoint=args.checkpoint,
        base_model=args.base_model,
        use_4bit=args.use_4bit,
        max_new_tokens=args.max_new_tokens,
    )

    # --- Run evaluation pipeline ---
    from evaluation_pipeline import EvaluationPipeline
    from response_cache import ResponseCache

    cache_dir = Path("experiments/cache") / f"finetuned_{label}"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = ResponseCache(cache_dir=str(cache_dir))

    pipeline = EvaluationPipeline(cache=cache)

    evaluations = []
    total = len(eval_instances) * len(args.modalities) * len(args.strategies)
    done  = 0

    for instance in eval_instances:
        for modality in args.modalities:
            for strategy in args.strategies:
                result = pipeline.evaluate_single(
                    instance=instance,
                    model=finetuned,
                    model_name=finetuned.model_name,
                    modality=modality,
                    strategy=strategy,
                )
                evaluations.append(result.to_dict() if hasattr(result, "to_dict") else result)
                done += 1
                if done % 20 == 0:
                    pct = 100.0 * done / total
                    print(f"  {done}/{total} ({pct:.0f}%)")

    # --- Save results ---
    results_dir = Path(args.results_dir) / f"finetuned_{label}_{ts}"
    results_dir.mkdir(parents=True, exist_ok=True)

    results_path = results_dir / f"results_finetuned_{label}.json"
    with open(results_path, "w") as f:
        json.dump({"evaluations": evaluations, "metadata": {
            "checkpoint": args.checkpoint,
            "base_model": args.base_model,
            "split": args.split,
            "timestamp": ts,
            "label": label,
        }}, f, indent=2)

    print(f"\nResults written to {results_path}")

    # --- Inline summary ---
    correct    = sum(1 for e in evaluations if e.get("metrics", {}).get("correct", False))
    total_eval = len(evaluations)
    accuracy   = correct / total_eval if total_eval else 0.0
    print(f"\nOverall accuracy: {correct}/{total_eval} = {accuracy:.1%}")

    # Level breakdown
    for level in [2, 3]:
        level_evals = [e for e in evaluations if e.get("level") == level or
                       (e.get("instance_id", "").startswith("l3") and level == 3) or
                       (not e.get("instance_id", "").startswith("l3") and level == 2)]
        if level_evals:
            lv_correct = sum(1 for e in level_evals if e.get("metrics", {}).get("correct", False))
            print(f"  Level {level}: {lv_correct}/{len(level_evals)} = {lv_correct/len(level_evals):.1%}")

    # Run analyze_results for full table
    try:
        import subprocess
        subprocess.run(
            [sys.executable, str(ROOT / "experiments" / "analyze_results.py"),
             "--results-dir", str(results_dir),
             "--save", str(results_dir / "summary.json")],
            cwd=str(ROOT),
        )
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
