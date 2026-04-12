"""
Phase B2: Direct Preference Optimization (DPO) Training.

Implements Section 6.3 of the paper:

  Standard DPO (Rafailov et al. 2023, Equation 9):
    L_DPO(theta) = -E_{(x,y_w,y_l)} [
      log sigma(beta * (log pi_theta(y_w|x) / pi_ref(y_w|x)
                      - log pi_theta(y_l|x) / pi_ref(y_l|x)))
    ]

  Margin-weighted DPO (Equation 10):
    L_mDPO(theta) = -E_{(x,y_w,y_l)} [
      log sigma(beta * log_ratio_w - beta * log_ratio_l - gamma * delta_r)
    ]
    where delta_r = r(y_w) - r(y_l) is the verifier score gap.
    The margin shifts the decision boundary so that pairs with larger
    verifier score gaps require proportionally larger log-ratio differences
    to contribute positively to the loss.

Configuration (from paper Section 6.6):
  - LoRA: rank=64, alpha=128, target all attention + MLP projections
  - beta=0.1, learning_rate=5e-6, per_device_batch=2
  - Curriculum: joint | sequential | weighted | l12_only

Supports three DPO variants:
  --dpo-variant standard       (Equation 9)
  --dpo-variant margin         (Equation 10, additive margin shift in sigmoid)
  --dpo-variant margin-strict  (Equation 10, margin capped at level boundary)

Requires TRL >= 0.9 for MarginDPOTrainer (uses dpo_loss override).

Usage (CURC Alpine):
  torchrun --nproc_per_node=4 experiments/finetuning/train_dpo.py \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir experiments/finetuning/checkpoints/dpo_standard_qwen72b/ \\
      --dpo-variant standard \\
      --curriculum joint

Usage (local, 1 GPU for smoke test):
  python experiments/finetuning/train_dpo.py \\
      --base-model Qwen/Qwen2.5-7B-Instruct \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir /tmp/dpo_test/ \\
      --dpo-variant standard \\
      --curriculum joint \\
      --max-steps 10 \\
      --per-device-batch-size 1

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Optional

import torch
import torch.nn.functional as F
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import DPOConfig, DPOTrainer

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Margin-weighted DPO loss (Equation 10)
# ---------------------------------------------------------------------------

class MarginDPOTrainer(DPOTrainer):
    """
    DPO with additive margin shift inside the sigmoid (paper Equation 10).

    For each preference pair with verifier score gap delta_r = r(y_w) - r(y_l):

        L = -E[ log sigma( beta*(log_ratio_w - log_ratio_l) - gamma*delta_r ) ]

    The margin shifts the decision boundary: larger score gaps require
    proportionally larger log-ratio differences to contribute positively to
    the loss, encoding the ordinal structure of Level-3 graded scoring.
    When gamma=0 this reduces to standard DPO.

    Requires TRL >= 0.9 (overrides dpo_loss method).
    """

    def __init__(self, *args, gamma: float = 2.0, **kwargs):
        super().__init__(*args, **kwargs)
        self.gamma = gamma
        self._margins_buffer: Optional[torch.Tensor] = None

    def get_batch_loss_metrics(self, model, batch, train_eval="train"):
        # Stash margins then remove so TRL internals don't see an unexpected key.
        self._margins_buffer = batch.pop("margins", None)
        return super().get_batch_loss_metrics(model, batch, train_eval)

    def dpo_loss(
        self,
        policy_chosen_logps: torch.FloatTensor,
        policy_rejected_logps: torch.FloatTensor,
        reference_chosen_logps: torch.FloatTensor,
        reference_rejected_logps: torch.FloatTensor,
    ):
        """Paper Equation 10: margin shifts the sigmoid decision boundary."""
        chosen_logratios   = policy_chosen_logps   - reference_chosen_logps
        rejected_logratios = policy_rejected_logps - reference_rejected_logps

        logits = self.beta * (chosen_logratios - rejected_logratios)

        if self._margins_buffer is not None and self.gamma > 0:
            delta_r = self._margins_buffer.float().to(logits.device)
            logits  = logits - self.gamma * delta_r
            self._margins_buffer = None  # consume once per batch

        losses           = -F.logsigmoid(logits)
        chosen_rewards   = self.beta * chosen_logratios.detach()
        rejected_rewards = self.beta * rejected_logratios.detach()
        return losses, chosen_rewards, rejected_rewards


# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_preference_data(
    data_dir:      Path,
    curriculum:    str,
    model_name:    str,
    data_fraction: float = 1.0,
) -> tuple[Dataset, Dataset]:
    """
    Load preference JSONL files from *data_dir* and return (train, val) Datasets.

    Curriculum options (Equation 8 in paper):
      joint       -- all levels mixed uniformly
      sequential  -- Level 1/2 then Level 3 (handled via warmup steps externally)
      weighted    -- Level 3 pairs weighted 5x relative to Level 1/2

    Files searched: preferences_{model_name}.jsonl or any preferences_*.jsonl
    """
    # Find data file
    slug    = model_name.replace("/", "_").replace(":", "_")
    exact   = data_dir / f"preferences_{slug}.jsonl"
    pattern = list(data_dir.glob("preferences_*.jsonl"))

    if exact.exists():
        src = exact
    elif pattern:
        src = pattern[0]
        print(f"  Warning: using {src.name} (no exact match for {slug})")
    else:
        raise FileNotFoundError(
            f"No preferences_*.jsonl found in {data_dir}. "
            "Run prepare_preference_data.py first."
        )

    print(f"  Loading {src}")
    records = _load_jsonl(src)
    print(f"  Loaded {len(records)} preference pairs")

    # Apply data fraction before curriculum weighting (B6 scaling ablation).
    # Stratify the subsample by level so L3 coverage is preserved.
    if data_fraction < 1.0:
        import random as _random
        _rng = _random.Random(42)
        l3_recs   = [r for r in records if r.get("level", 2) == 3]
        other_recs = [r for r in records if r.get("level", 2) != 3]
        k_l3    = max(1, round(len(l3_recs)   * data_fraction))
        k_other = max(1, round(len(other_recs) * data_fraction))
        records = _rng.sample(l3_recs, min(k_l3, len(l3_recs))) + \
                  _rng.sample(other_recs, min(k_other, len(other_recs)))
        print(f"  Data fraction {data_fraction:.0%}: {len(records)} pairs retained")

    # Apply curriculum weighting
    if curriculum == "weighted":
        l3    = [r for r in records if r.get("level", 2) == 3]
        other = [r for r in records if r.get("level", 2) != 3]
        records = other + l3 * 5
        import random
        random.shuffle(records)
        print(f"  Weighted curriculum: {len(other)} L2 + {len(l3)*5} L3 (5x)")
    elif curriculum == "l12_only":
        records = [r for r in records if r.get("level", 2) != 3]
        print(f"  L1/L2-only curriculum: {len(records)} pairs (Level 3 excluded)")

    # Split: find val from val split info, else 85/15
    val_file = data_dir / f"splits_{slug}.json"
    if val_file.exists():
        with open(val_file) as f:
            splits = json.load(f)
        val_ids  = set(splits.get("val", []))
        val_recs  = [r for r in records if r.get("instance_id", "") in val_ids]
        train_recs = [r for r in records if r.get("instance_id", "") not in val_ids]
    else:
        split_idx  = int(len(records) * 0.85)
        train_recs = records[:split_idx]
        val_recs   = records[split_idx:]

    print(f"  Train pairs: {len(train_recs)}  Val pairs: {len(val_recs)}")

    def _to_hf(recs: list[dict]) -> Dataset:
        return Dataset.from_dict({
            "prompt":   [r["prompt"]   for r in recs],
            "chosen":   [r["chosen"]   for r in recs],
            "rejected": [r["rejected"] for r in recs],
            "margins":  [r.get("margin", 1.0) for r in recs],
        })

    return _to_hf(train_recs), _to_hf(val_recs)


# ---------------------------------------------------------------------------
# Model loading
# ---------------------------------------------------------------------------

def _load_model_and_tokenizer(
    base_model: str,
    use_4bit:   bool,
    lora_rank:  int,
    lora_alpha: int,
    lora_dropout: float,
):
    print(f"  Loading tokenizer: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = None
    is_awq = "awq" in base_model.lower()
    if use_4bit and not is_awq:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
    elif is_awq:
        print("  Detected AWQ model -- skipping BitsAndBytes (model is already quantized)")

    print(f"  Loading base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="sdpa",
    )

    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    return model, tokenizer, lora_config


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Train DPO on DeFAb preference data.")

    # Model
    p.add_argument("--base-model", default="Qwen/Qwen2.5-72B-Instruct-AWQ",
                   help="HuggingFace model ID or local checkpoint path.")
    p.add_argument("--use-4bit", action="store_true",
                   help="Load base model in 4-bit quantization (QLoRA).")

    # LoRA
    p.add_argument("--lora-rank",    type=int, default=64)
    p.add_argument("--lora-alpha",   type=int, default=128)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--lora-init",    default="default",
                   choices=["default", "spectral"],
                   help="LoRA initialization: default (Kaiming+zero) or spectral (SVD).")

    # DPO
    p.add_argument("--dpo-variant", default="standard",
                   choices=["standard", "margin", "margin-strict"],
                   help="DPO loss variant (Equations 9-10 in paper).")
    p.add_argument("--beta",           type=float, default=0.1)
    p.add_argument("--margin-delta",   type=float, default=2.0,
                   help="Delta for margin-weighted DPO (Equation 10).")
    p.add_argument("--gamma",          type=float, default=0.0,
                   help="RPO gamma parameter (0 = standard DPO).")

    # Training
    p.add_argument("--curriculum", default="joint",
                   choices=["joint", "sequential", "weighted", "l12_only"],
                   help="Curriculum strategy (Section 6.5). l12_only excludes Level-3 pairs (B4 ablation).")
    p.add_argument("--learning-rate", type=float, default=5e-6)
    p.add_argument("--num-epochs",    type=int,   default=3)
    p.add_argument("--max-steps",     type=int,   default=-1,
                   help="Override num-epochs with a fixed step count.")
    p.add_argument("--per-device-batch-size", type=int, default=2)
    p.add_argument("--grad-accum-steps",      type=int, default=8)
    p.add_argument("--warmup-steps",          type=int, default=100)
    p.add_argument("--max-length",            type=int, default=1024)
    p.add_argument("--max-prompt-length",     type=int, default=512)

    # Data
    p.add_argument("--data-dir",      default="experiments/finetuning/data",
                   help="Directory with preferences_*.jsonl files.")
    p.add_argument("--data-fraction", type=float, default=1.0,
                   help="Fraction of training pairs to use (B6 scaling ablation). "
                        "Range: (0, 1]. E.g. 0.5 uses 50%% of pairs.")
    p.add_argument("--output-dir", required=True,
                   help="Checkpoint output directory.")
    p.add_argument("--logging-dir", default=None,
                   help="TensorBoard log dir (default: output-dir/logs).")
    p.add_argument("--save-steps",  type=int, default=200)
    p.add_argument("--eval-steps",  type=int, default=200)
    p.add_argument("--seed",        type=int, default=42)

    # DeepSpeed
    p.add_argument("--deepspeed-config", default=None,
                   help="DeepSpeed config JSON (for multi-GPU on CURC).")

    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb DPO Training")
    print("=" * 70)
    print(f"  Base model   : {args.base_model}")
    print(f"  DPO variant  : {args.dpo_variant}")
    print(f"  Curriculum   : {args.curriculum}")
    print(f"  Beta         : {args.beta}")
    print(f"  LR           : {args.learning_rate}")
    print(f"  Output dir   : {args.output_dir}")

    output_dir  = Path(args.output_dir)
    logging_dir = Path(args.logging_dir) if args.logging_dir else output_dir / "logs"
    data_dir    = ROOT / args.data_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    # --- Load data ---
    print("\nLoading preference data...")
    train_dataset, val_dataset = _load_preference_data(
        data_dir, args.curriculum, args.base_model, args.data_fraction
    )

    # --- Load model + LoRA ---
    print("\nLoading model and applying LoRA...")
    model, tokenizer, lora_config = _load_model_and_tokenizer(
        args.base_model,
        args.use_4bit,
        args.lora_rank,
        args.lora_alpha,
        args.lora_dropout,
    )

    if args.lora_init == "spectral":
        from finetuning.spectral_lora import spectral_init_lora
        n = spectral_init_lora(model, lora_config)
        print(f"  Applied spectral LoRA initialization to {n} layers")

    # --- DPO config ---
    dpo_config = DPOConfig(
        beta=args.beta,
        loss_type="sigmoid",
        output_dir=str(output_dir),
        logging_dir=str(logging_dir),
        per_device_train_batch_size=args.per_device_batch_size,
        per_device_eval_batch_size=args.per_device_batch_size,
        gradient_accumulation_steps=args.grad_accum_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        max_steps=args.max_steps,
        warmup_steps=args.warmup_steps,
        max_length=args.max_length,
        max_prompt_length=args.max_prompt_length,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        evaluation_strategy="steps",
        logging_steps=10,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="adamw_torch_fused",
        lr_scheduler_type="cosine",
        seed=args.seed,
        deepspeed=args.deepspeed_config,
        remove_unused_columns=False,
        report_to="tensorboard",
    )

    # --- Trainer selection ---
    TrainerClass = DPOTrainer
    trainer_kwargs: dict = {}

    if args.dpo_variant in ("margin", "margin-strict"):
        TrainerClass = MarginDPOTrainer
        trainer_kwargs["gamma"] = args.margin_delta

    trainer = TrainerClass(
        model=model,
        ref_model=None,  # uses peft implicit reference
        args=dpo_config,
        train_dataset=train_dataset,
        eval_dataset=val_dataset,
        tokenizer=tokenizer,
        **trainer_kwargs,
    )

    # --- Train ---
    print("\nStarting DPO training...")
    trainer.train()
    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))

    # Save training config for reproducibility
    config_path = output_dir / "training_config.json"
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)
    print(f"\nTraining config saved to {config_path}")

    # Save base model ID so submit_eval_finetuned_all.sh can read it
    base_model_path = output_dir / "base_model.txt"
    base_model_path.write_text(args.base_model)
    (output_dir / "final" / "base_model.txt").write_text(args.base_model)
    print(f"Base model ID written to {base_model_path}")

    print(f"\nDPO training complete.  Checkpoint: {output_dir / 'final'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
