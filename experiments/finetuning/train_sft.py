"""
Phase B-SFT: Supervised Fine-Tuning on DeFAb Gold Hypotheses.

The simplest post-training method: directly optimize the model to reproduce
gold-standard hypotheses encoded through the DeFAb codec.  Unlike DPO, SFT
requires no preference pairs -- the gold hypothesis IS the target.

  L_SFT(theta) = -E_{(x, y*) ~ D_sft} [ log pi_theta(y* | x) ]

where y* = rho_enc(h*) is the gold hypothesis rendered in the prompt modality.

This serves as a lower bound on what contrastive/RL methods can achieve:
if SFT alone closes the Level-3 gap, the deficit is purely a training data
issue; if contrastive methods outperform SFT, the relative signal provides
information beyond what gold demonstrations supply.

Configuration mirrors train_dpo.py for fair comparison:
  - LoRA: rank=64, alpha=128, target all attention + MLP projections
  - Curriculum: joint | sequential | weighted | l12_only

Usage (CURC Alpine):
  torchrun --nproc_per_node=4 experiments/finetuning/train_sft.py \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir experiments/finetuning/checkpoints/sft_qwen72b/ \\
      --curriculum joint

Usage (local smoke test):
  python experiments/finetuning/train_sft.py \\
      --base-model Qwen/Qwen2.5-7B-Instruct \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir /tmp/sft_test/ \\
      --max-steps 10

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import SFTConfig, SFTTrainer

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Dataset loading
# ---------------------------------------------------------------------------

def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_sft_data(
    data_dir:   Path,
    curriculum: str,
) -> tuple[Dataset, Dataset]:
    """Load SFT JSONL files and return (train, val) Datasets."""
    train_file = data_dir / "sft_train.jsonl"
    val_file   = data_dir / "sft_val.jsonl"

    if not train_file.exists():
        raise FileNotFoundError(
            f"No sft_train.jsonl found in {data_dir}. "
            "Run prepare_sft_data.py first."
        )

    train_records = _load_jsonl(train_file)
    val_records   = _load_jsonl(val_file) if val_file.exists() else []

    print(f"  Loaded {len(train_records)} train + {len(val_records)} val SFT records")

    if curriculum == "weighted":
        l3    = [r for r in train_records if r.get("level", 2) == 3]
        other = [r for r in train_records if r.get("level", 2) != 3]
        train_records = other + l3 * 5
        import random
        random.shuffle(train_records)
        print(f"  Weighted curriculum: {len(other)} L2 + {len(l3)*5} L3 (5x)")
    elif curriculum == "l12_only":
        train_records = [r for r in train_records if r.get("level", 2) != 3]
        print(f"  L1/L2-only: {len(train_records)} records")

    def _format(records: list[dict]) -> Dataset:
        texts = []
        for r in records:
            texts.append(r["prompt"] + "\n" + r["completion"])
        return Dataset.from_dict({"text": texts})

    return _format(train_records), _format(val_records)


# ---------------------------------------------------------------------------
# Model loading (mirrors train_dpo.py)
# ---------------------------------------------------------------------------

def _load_model_and_tokenizer(
    base_model:   str,
    use_4bit:     bool,
    lora_rank:    int,
    lora_alpha:   int,
    lora_dropout: float,
    lora_init:    str,
):
    print(f"  Loading tokenizer: {base_model}")
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = None
    if use_4bit:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )

    print(f"  Loading base model: {base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16 if not use_4bit else None,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="flash_attention_2" if not use_4bit else "sdpa",
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

    if lora_init == "spectral":
        from finetuning.spectral_lora import spectral_init_lora
        spectral_init_lora(model, lora_config)
        print("  Applied spectral LoRA initialization")

    return model, tokenizer


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train SFT on DeFAb gold hypothesis data."
    )

    p.add_argument("--base-model", default="Qwen/Qwen2.5-72B-Instruct-AWQ")
    p.add_argument("--use-4bit", action="store_true")

    p.add_argument("--lora-rank",    type=int,   default=64)
    p.add_argument("--lora-alpha",   type=int,   default=128)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--lora-init",    default="default",
                   choices=["default", "spectral"],
                   help="LoRA initialization strategy.")

    p.add_argument("--curriculum", default="joint",
                   choices=["joint", "sequential", "weighted", "l12_only"])
    p.add_argument("--learning-rate",          type=float, default=2e-5)
    p.add_argument("--num-epochs",             type=int,   default=3)
    p.add_argument("--max-steps",              type=int,   default=-1)
    p.add_argument("--per-device-batch-size",  type=int,   default=2)
    p.add_argument("--grad-accum-steps",       type=int,   default=8)
    p.add_argument("--warmup-steps",           type=int,   default=100)
    p.add_argument("--max-seq-length",         type=int,   default=1024)

    p.add_argument("--data-dir",  default="experiments/finetuning/data")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--logging-dir", default=None)
    p.add_argument("--save-steps",  type=int, default=200)
    p.add_argument("--eval-steps",  type=int, default=200)
    p.add_argument("--seed",        type=int, default=42)

    p.add_argument("--deepspeed-config", default=None)

    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb SFT Training")
    print("=" * 70)
    print(f"  Base model   : {args.base_model}")
    print(f"  Curriculum   : {args.curriculum}")
    print(f"  LoRA init    : {args.lora_init}")
    print(f"  LR           : {args.learning_rate}")
    print(f"  Output dir   : {args.output_dir}")

    output_dir  = Path(args.output_dir)
    logging_dir = Path(args.logging_dir) if args.logging_dir else output_dir / "logs"
    data_dir    = ROOT / args.data_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    print("\nLoading SFT data...")
    train_dataset, val_dataset = _load_sft_data(data_dir, args.curriculum)

    print("\nLoading model and applying LoRA...")
    model, tokenizer = _load_model_and_tokenizer(
        args.base_model,
        args.use_4bit,
        args.lora_rank,
        args.lora_alpha,
        args.lora_dropout,
        args.lora_init,
    )

    sft_config = SFTConfig(
        output_dir=str(output_dir),
        logging_dir=str(logging_dir),
        per_device_train_batch_size=args.per_device_batch_size,
        per_device_eval_batch_size=args.per_device_batch_size,
        gradient_accumulation_steps=args.grad_accum_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        max_steps=args.max_steps,
        warmup_steps=args.warmup_steps,
        max_seq_length=args.max_seq_length,
        save_steps=args.save_steps,
        eval_steps=args.eval_steps,
        evaluation_strategy="steps" if val_dataset else "no",
        logging_steps=10,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        fp16=torch.cuda.is_available() and not torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        optim="adamw_torch_fused",
        lr_scheduler_type="cosine",
        seed=args.seed,
        deepspeed=args.deepspeed_config,
        report_to="tensorboard",
        dataset_text_field="text",
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        eval_dataset=val_dataset if val_dataset else None,
        tokenizer=tokenizer,
    )

    print("\nStarting SFT training...")
    trainer.train()
    trainer.save_model(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))

    config_path = output_dir / "training_config.json"
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)
    print(f"\nTraining config saved to {config_path}")

    base_model_path = output_dir / "base_model.txt"
    base_model_path.write_text(args.base_model)
    (output_dir / "final" / "base_model.txt").write_text(args.base_model)

    print(f"\nSFT training complete.  Checkpoint: {output_dir / 'final'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
