"""
Phase B-GRPO: Reinforcement Learning with Verifiable Rewards via GRPO.

Implements Group Relative Policy Optimization (GRPO) with the DeFAb
verifier as a verifiable reward signal.  This is the RLVR paradigm:
the verifier provides exact, polynomial-time scoring (no learned reward
model, no human labels) and GRPO normalizes advantages within groups
of completions to produce sparse, targeted parameter updates.

GRPO loss:
  L_GRPO(theta) = -(1 / sum|o_i|) * sum_i sum_t [
      min(r_t * A_hat_i,t, clip(r_t, 1-eps, 1+eps) * A_hat_i,t)
  ]

where:
  r_t = pi_theta(o_i,t | q, o_i,<t) / pi_old(o_i,t | q, o_i,<t)
  A_hat_i,t = (r_i - mean(r)) / std(r)   (group-relative advantage)
  r_i = Score(rho_dec(o_i), D, alpha)     (DeFAb verifier)

The key sparsity property: if all G completions for a prompt receive
the same verifier score, std(r) -> 0 and no gradient flows.  Only
prompts with diverse reward outcomes contribute to parameter updates,
concentrating learning on the model's decision boundary.

Usage (CURC Alpine):
  torchrun --nproc_per_node=4 experiments/finetuning/train_grpo.py \\
      --base-model Qwen/Qwen2.5-72B-Instruct-AWQ \\
      --instances-dir instances/ \\
      --output-dir experiments/finetuning/checkpoints/grpo_qwen72b/ \\
      --num-generations 8

Usage (local smoke test):
  python experiments/finetuning/train_grpo.py \\
      --base-model Qwen/Qwen2.5-7B-Instruct \\
      --instances-dir instances/ \\
      --output-dir /tmp/grpo_test/ \\
      --num-generations 4 \\
      --max-steps 10

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
from transformers import AutoTokenizer, BitsAndBytesConfig
from trl import GRPOConfig, GRPOTrainer

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# DeFAb verifier reward function for GRPO
# ---------------------------------------------------------------------------

class DeFAbRewardFunction:
    """Wraps the DeFAb verifier as a GRPO-compatible reward function.

    The verifier provides exact scores:
      Level 1-2: r in {0.0, 1.0}  (binary correctness)
      Level 3:   r in {0.0, 0.25, 0.5, 0.75, 1.0}  (graded)
    """

    def __init__(self, instances: list):
        from blanc.codec.cascading_decoder import CascadingDecoder
        from level3_evaluator import Level3Evaluator

        self.decoder      = CascadingDecoder()
        self.l3_evaluator = Level3Evaluator()
        self._instance_map = {
            getattr(inst, "id", f"inst-{i}"): inst
            for i, inst in enumerate(instances)
        }

    def score_single(self, response_text: str, instance) -> float:
        """Score a single response against an instance."""
        try:
            decoded, _ = self.decoder.decode(response_text, instance)
        except Exception:
            return 0.0

        if decoded is None:
            return 0.0

        level = getattr(instance, "level", 2)
        if level < 3:
            gold = instance.gold or []
            return 1.0 if any(
                decoded.strip().lower() == g.strip().lower() for g in gold
            ) else 0.0

        try:
            result = self.l3_evaluator.evaluate(instance, response_text, decoded)
            return result.graded_score if result.graded_score is not None else 0.0
        except Exception:
            return 0.0

    def __call__(self, completions, prompts, instance_ids, **kwargs):
        """GRPO reward function interface.

        Parameters
        ----------
        completions : list of list of dict
            Each element is a conversation turn list with {"role": ..., "content": ...}.
        prompts : list of str
            The rendered prompts (unused here, context comes from instance_ids).
        instance_ids : list of str
            Maps each completion to its DeFAb instance for verifier scoring.

        Returns
        -------
        list of float
            Verifier scores for each completion.
        """
        scores = []
        for completion, iid in zip(completions, instance_ids):
            if isinstance(completion, list):
                text = completion[-1]["content"] if completion else ""
            else:
                text = str(completion)

            instance = self._instance_map.get(iid)
            if instance is None:
                scores.append(0.0)
                continue
            scores.append(self.score_single(text, instance))
        return scores


# ---------------------------------------------------------------------------
# Dataset construction
# ---------------------------------------------------------------------------

def _build_prompt_dataset(
    instances:  list,
    modality:   str,
    strategy:   str,
    curriculum: str,
) -> Dataset:
    """Build a HuggingFace Dataset of prompts for GRPO generation."""
    from prompting import render_prompt

    records = []
    for inst in instances:
        rendered = render_prompt(inst, modality, strategy)
        records.append({
            "prompt": [{"role": "user", "content": rendered.prompt}],
            "instance_id": getattr(inst, "id", "unknown"),
        })

    if curriculum == "weighted":
        l3    = [r for r in records
                 if any(getattr(i, "id", "") == r["instance_id"]
                        and getattr(i, "level", 2) == 3
                        for i in instances)]
        other = [r for r in records if r not in l3]
        records = other + l3 * 5
        import random
        random.shuffle(records)
    elif curriculum == "l12_only":
        l3_ids = {getattr(i, "id", "") for i in instances
                  if getattr(i, "level", 2) == 3}
        records = [r for r in records if r["instance_id"] not in l3_ids]

    return Dataset.from_list(records)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Train GRPO/RLVR on DeFAb with verifiable rewards."
    )

    p.add_argument("--base-model", default="Qwen/Qwen2.5-72B-Instruct-AWQ")
    p.add_argument("--use-4bit", action="store_true")

    p.add_argument("--lora-rank",    type=int,   default=64)
    p.add_argument("--lora-alpha",   type=int,   default=128)
    p.add_argument("--lora-dropout", type=float, default=0.05)
    p.add_argument("--lora-init",    default="default",
                   choices=["default", "spectral"])

    p.add_argument("--num-generations",      type=int,   default=8,
                   help="Group size G: completions per prompt.")
    p.add_argument("--max-completion-length", type=int,   default=512)
    p.add_argument("--learning-rate",        type=float, default=5e-7)
    p.add_argument("--num-epochs",           type=int,   default=3)
    p.add_argument("--max-steps",            type=int,   default=-1)
    p.add_argument("--per-device-batch-size",type=int,   default=2)
    p.add_argument("--grad-accum-steps",     type=int,   default=4)
    p.add_argument("--warmup-steps",         type=int,   default=0,
                   help="Fixed warmup step count. Ignored if --warmup-ratio is set.")
    p.add_argument("--warmup-ratio",         type=float, default=None,
                   help="Warmup as a fraction of total steps; preferred for short runs.")
    p.add_argument("--beta",                 type=float, default=0.04,
                   help="KL penalty coefficient (0 = no KL penalty).")
    p.add_argument("--temperature",          type=float, default=0.7)
    p.add_argument("--epsilon",              type=float, default=0.2,
                   help="Clipping parameter for surrogate objective.")
    p.add_argument("--scale-rewards",        default="True",
                   choices=["True", "False", "batch"],
                   help="GRPO reward scaling strategy.")

    p.add_argument("--use-vllm", action="store_true",
                   help="Use vLLM for accelerated generation.")

    p.add_argument("--modality", default="M4",
                   choices=["M1", "M2", "M3", "M4"])
    p.add_argument("--strategy", default="direct",
                   choices=["direct", "cot"])
    p.add_argument("--curriculum", default="joint",
                   choices=["joint", "sequential", "weighted", "l12_only"])

    p.add_argument("--instances-dir", default="instances")
    p.add_argument("--splits-file",   default="instances/splits.json")
    p.add_argument("--output-dir",    required=True)
    p.add_argument("--logging-dir",   default=None)
    p.add_argument("--save-steps",    type=int, default=100)
    p.add_argument("--save-total-limit", type=int, default=3,
                   help="Keep at most N most-recent checkpoints; older are pruned.")
    p.add_argument("--resume-from-checkpoint", default=None,
                   help="Path to a checkpoint-N directory to resume from.")
    p.add_argument("--seed",          type=int, default=42)

    p.add_argument("--deepspeed-config", default=None)

    return p.parse_args()


def main() -> int:
    args = parse_args()

    print("=" * 70)
    print("DeFAb GRPO/RLVR Training")
    print("=" * 70)
    print(f"  Base model        : {args.base_model}")
    print(f"  Curriculum        : {args.curriculum}")
    print(f"  LoRA init         : {args.lora_init}")
    print(f"  Num generations G : {args.num_generations}")
    print(f"  Beta (KL)         : {args.beta}")
    print(f"  LR                : {args.learning_rate}")
    print(f"  Output dir        : {args.output_dir}")

    output_dir  = Path(args.output_dir)
    logging_dir = Path(args.logging_dir) if args.logging_dir else output_dir / "logs"
    instances_dir = ROOT / args.instances_dir

    output_dir.mkdir(parents=True, exist_ok=True)
    logging_dir.mkdir(parents=True, exist_ok=True)

    # --- Load instances ---
    print("\nLoading instances...")
    from blanc.author.loaders import load_instances_from_json
    all_instances = load_instances_from_json(instances_dir, include_level3=True)
    print(f"  Total instances: {len(all_instances)}")

    splits_file = ROOT / args.splits_file
    if splits_file.exists():
        with open(splits_file) as f:
            splits = json.load(f)
        train_ids = set(splits.get("train", []))
        train_instances = [i for i in all_instances
                          if getattr(i, "id", "") in train_ids]
    else:
        cut = int(len(all_instances) * 0.70)
        train_instances = all_instances[:cut]

    print(f"  Training instances: {len(train_instances)}")

    # --- Build reward function ---
    print("\nInitializing DeFAb verifier reward function...")
    reward_fn = DeFAbRewardFunction(train_instances)

    # --- Build prompt dataset ---
    print("\nBuilding prompt dataset...")
    train_dataset = _build_prompt_dataset(
        train_instances, args.modality, args.strategy, args.curriculum,
    )
    print(f"  Prompt dataset size: {len(train_dataset)}")

    # --- LoRA config ---
    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=args.lora_rank,
        lora_alpha=args.lora_alpha,
        lora_dropout=args.lora_dropout,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        bias="none",
    )

    # --- GRPO config ---
    scale_rewards = args.scale_rewards
    if scale_rewards == "True":
        scale_rewards = True
    elif scale_rewards == "False":
        scale_rewards = False

    warmup_kwargs = (
        {"warmup_ratio": args.warmup_ratio}
        if args.warmup_ratio is not None
        else {"warmup_steps": args.warmup_steps}
    )

    grpo_config = GRPOConfig(
        output_dir=str(output_dir),
        logging_dir=str(logging_dir),
        num_generations=args.num_generations,
        max_completion_length=args.max_completion_length,
        per_device_train_batch_size=args.per_device_batch_size,
        gradient_accumulation_steps=args.grad_accum_steps,
        learning_rate=args.learning_rate,
        num_train_epochs=args.num_epochs,
        max_steps=args.max_steps,
        beta=args.beta,
        epsilon_low=args.epsilon,
        epsilon_high=args.epsilon,
        scale_rewards=scale_rewards,
        save_steps=args.save_steps,
        save_total_limit=args.save_total_limit,
        save_strategy="steps",
        **warmup_kwargs,
        logging_steps=10,
        bf16=torch.cuda.is_available() and torch.cuda.is_bf16_supported(),
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="adamw_torch_fused",
        lr_scheduler_type="cosine",
        seed=args.seed,
        deepspeed=args.deepspeed_config,
        report_to="tensorboard",
        use_vllm=args.use_vllm,
        temperature=args.temperature,
    )

    # --- Trainer ---
    print("\nInitializing GRPOTrainer...")

    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    model_kwargs = {"trust_remote_code": True, "device_map": {"": local_rank}}
    is_awq = "awq" in args.base_model.lower()
    if args.use_4bit and not is_awq:
        model_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
        )
    else:
        model_kwargs["torch_dtype"] = torch.bfloat16
        model_kwargs["attn_implementation"] = "sdpa"

    trainer = GRPOTrainer(
        model=args.base_model,
        reward_funcs=reward_fn,
        args=grpo_config,
        train_dataset=train_dataset,
        peft_config=peft_config,
        model_init_kwargs=model_kwargs,
    )

    if args.lora_init == "spectral":
        from finetuning.spectral_lora import spectral_init_lora
        spectral_init_lora(trainer.model, peft_config)
        print("  Applied spectral LoRA initialization")

    # --- Train ---
    print("\nStarting GRPO training...")
    resume = args.resume_from_checkpoint
    if resume and not Path(resume).exists():
        print(f"  resume path {resume} does not exist; starting fresh.")
        resume = None
    trainer.train(resume_from_checkpoint=resume)
    trainer.save_model(str(output_dir / "final"))

    tokenizer = AutoTokenizer.from_pretrained(args.base_model, trust_remote_code=True)
    tokenizer.save_pretrained(str(output_dir / "final"))

    config_path = output_dir / "training_config.json"
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)
    print(f"\nTraining config saved to {config_path}")

    base_model_path = output_dir / "base_model.txt"
    base_model_path.write_text(args.base_model)
    (output_dir / "final" / "base_model.txt").write_text(args.base_model)

    print(f"\nGRPO training complete.  Checkpoint: {output_dir / 'final'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
