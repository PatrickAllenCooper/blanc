# Azure Dual-A100 Fine-Tuning Guide

This guide covers running the full DeFAb fine-tuning pipeline on an Azure NC_A100_v4 instance (2x A100 80 GB) or equivalent dual-A100 machine.

---

## Prerequisites

- Azure VM with 2x A100 80 GB GPUs (e.g. Standard_NC48ads_A100_v4)
- Ubuntu 22.04, CUDA 12.x, Python 3.11+
- HuggingFace account with access to `PatrickAllenCooper/DeFAb`
- GitHub access to the blanc repository

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc

# Set your HuggingFace token (for the private DeFAb dataset)
export HF_TOKEN=<your-token>

# Run everything: setup, data download, all 4 methods, all 3 models
bash scripts/azure_finetune.sh
```

Results are written to `results/finetune/`.

---

## What the Script Does

### Phase 0: Environment Setup

Installs all Python dependencies (torch, transformers, trl, peft, bitsandbytes, vllm, deepspeed) and the blanc package.

### Phase 1: Dataset Download

Downloads the DeFAb dataset from `PatrickAllenCooper/DeFAb` on HuggingFace into the `instances/` directory.

### Phase 2: Data Preparation (per model)

1. **SFT data** (`prepare_sft_data.py`): Creates gold demonstration pairs from DeFAb instances (modalities M4+M2, direct prompting). Output: `experiments/finetuning/data/sft_train.jsonl` and `sft_val.jsonl`.

2. **Preference data** (`prepare_preference_data.py`): Starts a vLLM server on GPU 0, samples 16 responses per instance at temperature 0.7, scores each response with the DeFAb verifier, and extracts preference pairs with margin >= 0.25. Output: `experiments/finetuning/data/preferences_{model}.jsonl`.

### Phase 3: Training (4 methods per model)

All training uses LoRA rank 64, alpha 128 on attention and MLP projections. 4-bit AWQ quantization for all models.

| Method | Key hyperparameters | GPU config |
|--------|---------------------|------------|
| SFT | LR 2e-5, 3 epochs, effective batch 32 | 2 GPUs + ZeRO-2 |
| DPO (standard) | beta=0.1, LR 5e-6, 3 epochs | 2 GPUs + ZeRO-2 |
| DPO (margin) | same + gamma=2.0 margin weighting | 2 GPUs + ZeRO-2 |
| GRPO | LR 5e-7, G=8, KL beta=0.04, verifier reward | 2 GPUs + vLLM |
| RLHF/VITL | PPO, KL=0.05, LR 1e-6, exact verifier reward | 1 GPU (PPO limitation) |

### Phase 4: Evaluation

Evaluates each checkpoint on the test split using the same 4-modality protocol as the base model evaluation. Reports fine-tuning lift (delta_FT) per method and model.

---

## Models

| Slug | Model ID | VRAM (4-bit) |
|------|----------|--------------|
| qwen72 | Qwen/Qwen2.5-72B-Instruct-AWQ | ~36 GB |
| qwen32 | Qwen/Qwen2.5-32B-Instruct-AWQ | ~16 GB |
| deepseek | casperhansen/deepseek-r1-distill-llama-70b-awq | ~35 GB |

All models fit on a single A100 80 GB in 4-bit. ZeRO-2 shards optimizer states across 2 GPUs to reduce per-GPU memory for gradient updates.

---

## Partial Runs

Run a single model:
```bash
bash scripts/azure_finetune.sh --model qwen32
```

Run a single method on a single model:
```bash
bash scripts/azure_finetune.sh --model qwen32 --method sft
```

Skip environment setup if already installed:
```bash
bash scripts/azure_finetune.sh --skip-setup
```

Skip data preparation if already done:
```bash
bash scripts/azure_finetune.sh --skip-data
```

---

## Output Structure

```
results/finetune/
  sft/{model}/            # SFT checkpoints
  dpo_standard/{model}/   # DPO standard checkpoints
  dpo_margin/{model}/     # DPO margin-weighted checkpoints
  grpo/{model}/           # GRPO checkpoints
  rlhf_vitl/{model}/      # RLHF/VITL checkpoints
  eval/{model}/           # Evaluation results per method

experiments/finetuning/data/
  sft_train.jsonl         # Gold SFT training examples
  sft_val.jsonl           # Gold SFT validation examples
  preferences_{model}.jsonl  # Preference pairs per model
  splits.json             # Train/val/test instance splits
```

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| HF_TOKEN | (none) | HuggingFace token for private dataset access |
| HF_HOME | /tmp/hf_cache | HuggingFace model/dataset cache directory |
| VLLM_PORT | 8200 | Port for vLLM server during preference sampling |
| REPO_DIR | (auto-detected) | Root of the blanc repository |

---

## Time Estimates on 2x A100 80 GB

| Step | Approximate time |
|------|-----------------|
| Environment setup | 10--15 min |
| Dataset download | 5--10 min |
| Preference sampling (per model, 409 instances x 16 samples) | 2--4 hours |
| SFT training (per model) | 1--2 hours |
| DPO training x 2 variants (per model) | 2--4 hours |
| GRPO training (per model) | 3--6 hours |
| RLHF/VITL training (per model, 1 GPU) | 2--4 hours |
| Evaluation (per model) | 30--60 min |
| **Total (3 models, all methods)** | **~48--72 hours** |

Use `--model qwen32 --skip-setup` for a faster first run (~12 hours for the smallest model).
