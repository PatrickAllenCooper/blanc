"""
Phase B3: RLHF with Verifier-in-the-Loop (VITL) Training.

Implements Section 6.4 of the paper:

  Reward model training (Equation 11):
    L_RM = -E[(r_w > r_l)] log sigma(R_phi(x, y_w) - R_phi(x, y_l))

  PPO policy optimization (Equation 12):
    L_PPO(theta) = E[min(rho_t * A_t, clip(rho_t, 1-eps, 1+eps) * A_t)]
                 - beta * KL[pi_theta || pi_ref]

  VITL variant (Equation 13):
    r_VITL(y, x) = S_defab(y, x)

  where S_defab is the DeFAb polynomial-time verifier (no reward model
  approximation -- the verifier IS the reward signal).

Two modes:
  --mode reward-model   Train a Bradley-Terry reward model on preference data,
                        then use it as the reward signal in PPO (standard RLHF).
  --mode vitl           Use the DeFAb verifier directly as the reward signal
                        in PPO (Verifier-in-the-Loop).

Usage (CURC Alpine, VITL mode):
  torchrun --nproc_per_node=4 experiments/finetuning/train_rlhf_vitl.py \\
      --mode vitl \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir experiments/finetuning/checkpoints/vitl_qwen72b/

Usage (CURC Alpine, standard RLHF):
  torchrun --nproc_per_node=4 experiments/finetuning/train_rlhf_vitl.py \\
      --mode reward-model \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --data-dir experiments/finetuning/data/ \\
      --output-dir experiments/finetuning/checkpoints/rlhf_qwen72b/

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType
from transformers import (
    AutoModelForCausalLM,
    AutoModelForSequenceClassification,
    AutoTokenizer,
    BitsAndBytesConfig,
)
from trl import (
    PPOConfig,
    PPOTrainer,
    AutoModelForCausalLMWithValueHead,
    create_reference_model,
)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# VITL reward function (Equation 13)
# ---------------------------------------------------------------------------

class VITLRewardFn:
    """
    Verifier-in-the-Loop reward: maps model output text to a DeFAb score.

    This replaces the reward model R_phi with the exact polynomial-time
    DeFAb verifier, eliminating reward model approximation error.

    For Level 2: r in {0.0, 1.0}
    For Level 3: r in {0.0, 0.25, 0.5, 0.75, 1.0}
    """

    def __init__(self):
        from blanc.codec.cascading_decoder import CascadingDecoder
        from level3_evaluator import Level3Evaluator

        self.decoder     = CascadingDecoder()
        self.l3_evaluator = Level3Evaluator()

    def score(
        self,
        response_text: str,
        instance,
    ) -> float:
        """Score *response_text* for *instance* using the DeFAb verifier."""
        try:
            decoded, _ = self.decoder.decode(response_text, instance)
        except Exception:
            return 0.0

        if decoded is None:
            return 0.0

        level = getattr(instance, "level", 2)
        if level < 3:
            gold  = instance.gold or []
            return 1.0 if any(
                decoded.strip().lower() == g.strip().lower() for g in gold
            ) else 0.0

        try:
            result = self.l3_evaluator.evaluate(instance, response_text, decoded)
            return result.graded_score if result.graded_score is not None else 0.0
        except Exception:
            return 0.0


# ---------------------------------------------------------------------------
# Reward model (Bradley-Terry, Equation 11)
# ---------------------------------------------------------------------------

class RewardModelTrainer:
    """
    Train a Bradley-Terry reward model on preference data.

    The model is a causal LM with a scalar head (AutoModelForSequenceClassification
    with num_labels=1) fine-tuned with LoRA on preference pairs.
    """

    def __init__(
        self,
        base_model:    str,
        lora_rank:     int,
        lora_alpha:    int,
        lora_dropout:  float,
        use_4bit:      bool,
    ):
        self.base_model   = base_model
        self.lora_rank    = lora_rank
        self.lora_alpha   = lora_alpha
        self.lora_dropout = lora_dropout
        self.use_4bit     = use_4bit

    def train(
        self,
        train_dataset: Dataset,
        val_dataset:   Dataset,
        output_dir:    str,
        learning_rate: float,
        num_epochs:    int,
        batch_size:    int,
        grad_accum:    int,
        seed:          int,
    ) -> str:
        """Train reward model and return path to saved checkpoint."""
        from transformers import Trainer, TrainingArguments

        print("  Loading reward model backbone...")
        tokenizer = AutoTokenizer.from_pretrained(
            self.base_model, trust_remote_code=True
        )
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        bnb_config = None
        is_awq = "awq" in self.base_model.lower()
        if self.use_4bit and not is_awq:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )

        model = AutoModelForSequenceClassification.from_pretrained(
            self.base_model,
            num_labels=1,
            quantization_config=bnb_config,
            torch_dtype=torch.bfloat16 if not self.use_4bit else None,
            device_map="auto",
            trust_remote_code=True,
        )

        from peft import get_peft_model
        lora_cfg = LoraConfig(
            task_type=TaskType.SEQ_CLS,
            r=self.lora_rank,
            lora_alpha=self.lora_alpha,
            lora_dropout=self.lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
        )
        model = get_peft_model(model, lora_cfg)

        def tokenize(batch):
            chosen_enc  = tokenizer(
                batch["prompt"], batch["chosen"],
                truncation=True, max_length=1024, padding="max_length"
            )
            rejected_enc = tokenizer(
                batch["prompt"], batch["rejected"],
                truncation=True, max_length=1024, padding="max_length"
            )
            return {
                "input_ids_chosen":       chosen_enc["input_ids"],
                "attention_mask_chosen":  chosen_enc["attention_mask"],
                "input_ids_rejected":     rejected_enc["input_ids"],
                "attention_mask_rejected": rejected_enc["attention_mask"],
            }

        train_tok = train_dataset.map(tokenize, batched=True, remove_columns=train_dataset.column_names)
        val_tok   = val_dataset.map(tokenize,   batched=True, remove_columns=val_dataset.column_names)

        training_args = TrainingArguments(
            output_dir=output_dir,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            gradient_accumulation_steps=grad_accum,
            num_train_epochs=num_epochs,
            learning_rate=learning_rate,
            bf16=True,
            gradient_checkpointing=True,
            evaluation_strategy="steps",
            eval_steps=100,
            save_steps=100,
            logging_steps=10,
            seed=seed,
            report_to="tensorboard",
        )

        # Custom trainer for Bradley-Terry loss
        from trl import RewardTrainer, RewardConfig
        reward_config = RewardConfig(
            output_dir=output_dir,
            per_device_train_batch_size=batch_size,
            num_train_epochs=num_epochs,
            learning_rate=learning_rate,
            bf16=True,
            gradient_checkpointing=True,
            evaluation_strategy="steps",
            eval_steps=100,
            save_steps=100,
            logging_steps=10,
            seed=seed,
            report_to="tensorboard",
            max_length=1024,
        )
        reward_trainer = RewardTrainer(
            model=model,
            args=reward_config,
            tokenizer=tokenizer,
            train_dataset=train_tok,
            eval_dataset=val_tok,
        )
        reward_trainer.train()
        reward_trainer.save_model(os.path.join(output_dir, "reward_model_final"))
        print(f"  Reward model saved to {output_dir}/reward_model_final")
        return os.path.join(output_dir, "reward_model_final")


# ---------------------------------------------------------------------------
# PPO training loop
# ---------------------------------------------------------------------------

def _run_ppo(
    base_model:       str,
    reward_fn,        # callable(response_text, instance) -> float
    train_instances:  list,
    output_dir:       Path,
    lora_rank:        int,
    lora_alpha:       int,
    lora_dropout:     float,
    use_4bit:         bool,
    learning_rate:    float,
    ppo_epochs:       int,
    batch_size:       int,
    mini_batch_size:  int,
    kl_coeff:         float,
    max_new_tokens:   int,
    curriculum:       str,
    seed:             int,
) -> None:
    """Core PPO loop (Equation 12) with the provided reward function."""
    import random
    from torch.optim import Adam

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

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_rank,
        lora_alpha=lora_alpha,
        lora_dropout=lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )

    ppo_config = PPOConfig(
        model_name=base_model,
        learning_rate=learning_rate,
        ppo_epochs=ppo_epochs,
        batch_size=batch_size,
        mini_batch_size=mini_batch_size,
        kl_penalty="kl",
        init_kl_coef=kl_coeff,
        target=6.0,          # target KL divergence
        seed=seed,
        log_with="tensorboard",
        project_kwargs={"logging_dir": str(output_dir / "logs")},
    )

    print("  Loading policy model with value head...")
    model = AutoModelForCausalLMWithValueHead.from_pretrained(
        base_model,
        peft_config=peft_config,
        quantization_config=bnb_config,
        torch_dtype=torch.bfloat16 if not use_4bit else None,
        trust_remote_code=True,
    )

    ref_model = create_reference_model(model)
    optimizer = Adam(model.parameters(), lr=learning_rate)

    ppo_trainer = PPOTrainer(
        config=ppo_config,
        model=model,
        ref_model=ref_model,
        tokenizer=tokenizer,
        optimizer=optimizer,
    )

    # Curriculum ordering
    from prompting import render_prompt
    from blanc.author.loaders import load_instances_from_json

    instances = list(train_instances)
    if curriculum == "sequential":
        instances = sorted(instances, key=lambda i: getattr(i, "level", 2))

    rng = random.Random(seed)
    step = 0

    for epoch in range(ppo_epochs):
        rng.shuffle(instances)
        for i in range(0, len(instances), batch_size):
            batch_insts = instances[i : i + batch_size]
            if not batch_insts:
                continue

            # Render prompts (M4 / direct by default)
            prompts = [render_prompt(inst, "M4", "direct").prompt for inst in batch_insts]
            query_tensors = [
                tokenizer.encode(p, return_tensors="pt").squeeze(0)
                for p in prompts
            ]

            # Generate responses
            response_tensors = ppo_trainer.generate(
                query_tensors,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                pad_token_id=tokenizer.pad_token_id,
            )

            # Decode and score
            responses = [
                tokenizer.decode(r.squeeze(), skip_special_tokens=True)
                for r in response_tensors
            ]
            rewards = [
                torch.tensor(reward_fn(resp, inst), dtype=torch.float32)
                for resp, inst in zip(responses, batch_insts)
            ]

            # PPO step
            stats = ppo_trainer.step(query_tensors, response_tensors, rewards)
            ppo_trainer.log_stats(stats, {"query": prompts, "response": responses}, rewards)

            step += 1
            if step % 10 == 0:
                mean_reward = sum(r.item() for r in rewards) / len(rewards)
                print(f"  Epoch {epoch+1}  Step {step}  "
                      f"mean_reward={mean_reward:.3f}  "
                      f"kl={stats.get('objective/kl', 0):.4f}")

        # Save checkpoint after each epoch
        ckpt_dir = output_dir / f"checkpoint_epoch{epoch+1}"
        ppo_trainer.model.save_pretrained(str(ckpt_dir))
        tokenizer.save_pretrained(str(ckpt_dir))
        print(f"  Saved checkpoint: {ckpt_dir}")

    # Final save
    final_dir = output_dir / "final"
    final_dir.mkdir(parents=True, exist_ok=True)
    ppo_trainer.model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"  Final model saved to {final_dir}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train RLHF-PPO (standard or VITL) on DeFAb preference data."
    )

    p.add_argument("--mode", required=True,
                   choices=["reward-model", "vitl"],
                   help=(
                       "reward-model: train Bradley-Terry RM then PPO; "
                       "vitl: use DeFAb verifier directly as reward."
                   ))
    p.add_argument("--base-model", default="Qwen/Qwen2.5-72B-Instruct-AWQ")
    p.add_argument("--reward-model-checkpoint", default=None,
                   help="Pre-trained reward model checkpoint (--mode reward-model only).")
    p.add_argument("--use-4bit", action="store_true")

    # LoRA
    p.add_argument("--lora-rank",    type=int, default=64)
    p.add_argument("--lora-alpha",   type=int, default=128)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--lora-init",    default="default",
                   choices=["default", "spectral"],
                   help="LoRA initialization: default (Kaiming+zero) or spectral (SVD).")

    # PPO
    p.add_argument("--kl-coeff",       type=float, default=0.05,
                   help="PPO KL penalty coefficient beta (paper Section 6.6: 0.05).")
    p.add_argument("--ppo-epochs",     type=int,   default=3)
    p.add_argument("--batch-size",     type=int,   default=16)
    p.add_argument("--mini-batch-size",type=int,   default=8,
                   help="PPO mini-batch size (paper Section 6.6: 8).")
    p.add_argument("--learning-rate",  type=float, default=1e-6,
                   help="Learning rate for PPO policy (paper Section 6.6: 1e-6).")
    p.add_argument("--max-new-tokens", type=int,   default=512,
                   help="Max tokens generated per response during PPO rollout.")

    # Reward model training (only for --mode reward-model)
    p.add_argument("--rm-learning-rate",type=float, default=1e-5)
    p.add_argument("--rm-epochs",       type=int,   default=2)
    p.add_argument("--rm-batch-size",   type=int,   default=4)
    p.add_argument("--rm-grad-accum",   type=int,   default=8)

    # Curriculum
    p.add_argument("--curriculum", default="joint",
                   choices=["joint", "sequential", "weighted"])

    # I/O
    p.add_argument("--data-dir",   default="experiments/finetuning/data")
    p.add_argument("--instances-dir", default="instances")
    p.add_argument("--output-dir", required=True)
    p.add_argument("--seed",       type=int, default=42)

    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print(f"DeFAb RLHF Training  (mode: {args.mode})")
    print("=" * 70)
    print(f"  Base model  : {args.base_model}")
    print(f"  Curriculum  : {args.curriculum}")
    print(f"  KL coeff    : {args.kl_coeff}")
    print(f"  Output dir  : {args.output_dir}")

    output_dir    = Path(args.output_dir)
    data_dir      = ROOT / args.data_dir
    instances_dir = ROOT / args.instances_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load training instances for PPO
    from blanc.author.loaders import load_instances_from_json
    splits_files = list(data_dir.glob("splits_*.json"))
    train_insts: list = []
    if splits_files:
        with open(splits_files[0]) as f:
            splits = json.load(f)
        train_ids = set(splits.get("train", []))
        all_insts = load_instances_from_json(instances_dir)
        train_insts = [i for i in all_insts if i.id in train_ids]
    else:
        all_insts   = load_instances_from_json(instances_dir)
        cut         = int(len(all_insts) * 0.70)
        train_insts = all_insts[:cut]

    print(f"  Training on {len(train_insts)} instances")

    # Set up reward function
    if args.mode == "vitl":
        print("\nMode: VITL -- DeFAb verifier as reward signal (Equation 13)")
        reward_fn = VITLRewardFn().score
        rm_checkpoint = None

    else:  # reward-model
        print("\nMode: Standard RLHF -- training/loading reward model (Equation 11)")
        rm_checkpoint = args.reward_model_checkpoint

        if rm_checkpoint is None:
            # Load preference data and train reward model first
            from finetuning.train_dpo import _load_preference_data as _load
            train_pref, val_pref = _load(data_dir, args.curriculum, args.base_model)
            rm_trainer = RewardModelTrainer(
                base_model=args.base_model,
                lora_rank=args.lora_rank,
                lora_alpha=args.lora_alpha,
                lora_dropout=args.lora_dropout,
                use_4bit=args.use_4bit,
            )
            rm_checkpoint = rm_trainer.train(
                train_dataset=train_pref,
                val_dataset=val_pref,
                output_dir=str(output_dir / "reward_model"),
                learning_rate=args.rm_learning_rate,
                num_epochs=args.rm_epochs,
                batch_size=args.rm_batch_size,
                grad_accum=args.rm_grad_accum,
                seed=args.seed,
            )
        else:
            print(f"  Using existing reward model: {rm_checkpoint}")

        # Wrap reward model as reward function
        from transformers import pipeline
        reward_pipe = pipeline(
            "text-classification", model=rm_checkpoint,
            device="cuda" if torch.cuda.is_available() else "cpu",
        )

        def reward_fn(response_text: str, instance) -> float:
            result = reward_pipe(response_text[:1024], truncation=True)
            return float(result[0]["score"])

    # Save config and base model ID
    with open(output_dir / "training_config.json", "w") as f:
        json.dump(vars(args), f, indent=2)
    (output_dir / "base_model.txt").write_text(args.base_model)

    # Run PPO
    print("\nStarting PPO training...")
    _run_ppo(
        base_model=args.base_model,
        reward_fn=reward_fn,
        train_instances=train_insts,
        output_dir=output_dir,
        lora_rank=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        use_4bit=args.use_4bit,
        learning_rate=args.learning_rate,
        ppo_epochs=args.ppo_epochs,
        batch_size=args.batch_size,
        mini_batch_size=args.mini_batch_size,
        kl_coeff=args.kl_coeff,
        max_new_tokens=args.max_new_tokens,
        curriculum=args.curriculum,
        seed=args.seed,
    )

    # Write base_model.txt to final checkpoint dir for submit_eval_finetuned_all.sh
    final_dir = output_dir / "final"
    if final_dir.exists():
        (final_dir / "base_model.txt").write_text(args.base_model)

    print(f"\nRLHF training complete.  Output: {output_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
