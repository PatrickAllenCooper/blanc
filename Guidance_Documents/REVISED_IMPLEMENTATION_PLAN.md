# Implementation Plan: LLM Evaluation, Fine-Tuning, and Submission

**Date**: 2026-02-24 (updated)
**Author**: Patrick Cooper
**Status**: Pilot complete (GPT-5.2, Claude). Section 6 (DPO/RLHF fine-tuning) added to paper. Full evaluation and fine-tuning next.
**Next action**: Deploy DeepSeek-R1 on Foundry portal, then submit full evaluation batch.

---

## Completed Work

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1--2 | Expert KB foundation -- 2,318 rules (YAGO, WordNet, LKIF, MatOnto) | Done |
| 3 | Instance generation -- 374 Level 2 instances | Done |
| 4 | Statistical analysis (Section 4.3) | Done |
| 5--6 | Full codec: M1--M4 encoders, D1--D3 decoders, cascading decoder | Done |
| 7 | Validation and testing infrastructure (503 tests, 86% coverage) | Done |
| 8 | Evaluation infrastructure (pipeline, prompting, response cache) | Done |
| 8.5a | Level 3 instance generation -- 35 defeater instances | Done |
| 8.5b | All analysis scripts written and tested | Done |
| 9a | Azure AI Foundry integration -- GPT-5.2, Kimi, Claude confirmed live | Done |
| 9b | Pilot evaluation -- GPT-5.2 (88.3% L2 / 1.4% L3), Claude (91.7% / 2.1%) | Done |
| 9c | Pipeline fixes: `.env` auto-load, CoT extraction, empty-cache skip, max_tokens | Done |
| 9d | DeepSeek-R1 added to Foundry as 4th primary model (`foundry-deepseek`) | Done |
| 10 | Paper Section 6: Defeasible Fine-Tuning via Preference Optimization | Done |

### Dataset

| Level | Count | Domains | Notes |
|-------|-------|---------|-------|
| Level 2 (rule abduction) | 374 | Biology 114, Legal 116, Materials 144 | Complete |
| Level 3 (defeater abduction) | 35 | Biology 16, Legal 10, Materials 9 | 10 with Nov > 0 |

---

## Evaluation Model Lineup

### Primary -- Azure AI Foundry (all models on same infrastructure, same API key)

**Strategy**: Use Foundry wherever possible. CURC only for models not available as Foundry serverless and for fine-tuning (requires GPU).

| Model | Provider | Deployment name | RPM | Cost/1M in | Cost/1M out | Type | Status |
|-------|----------|----------------|-----|------------|-------------|------|--------|
| gpt-5.2-chat | Foundry (AzureOpenAI) | `gpt-5.2-chat` | 2,500 | $1.75 | $14.00 | Reasoning | Live |
| Kimi-K2.5 | Foundry (OpenAI-compat) | `Kimi-K2.5` | 250 | $1.40 | $2.80 | Reasoning | Live |
| claude-sonnet-4-6 | Foundry (AnthropicFoundry) | `claude-sonnet-4-6` | 250 | $3.00 | $15.00 | Instruction | Live |
| DeepSeek-R1 | Foundry (OpenAI-compat) | `DeepSeek-R1` | 5,000 | $1.35 | $5.40 | Reasoning, open | **Deploy now** |

**Shared key**: `FOUNDRY_API_KEY` in `.env`

### Open-Source -- CURC Alpine (base evaluation + fine-tuning)

These models are evaluated via CURC vLLM for base accuracy, then fine-tuned via DPO/RLHF on CURC GPUs.

| Model | HuggingFace ID | VRAM (inference) | VRAM (training) | Type |
|-------|----------------|------------------|-----------------|------|
| DeepSeek-R1-Distill-70B | `casperhansen/deepseek-r1-distill-llama-70b-awq` | ~35 GB | 4xA100 (LoRA) | Reasoning |
| Qwen 2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct-AWQ` | ~36 GB | 4xA100 (LoRA) | Instruction |
| Qwen 2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct-AWQ` | ~16 GB | 2xA100 (LoRA) | Scaling |

CURC env: `vllm-env` (set up by `curc-hoster/scripts/setup_environment.sh`)
HF cache: `/scratch/alpine/paco0228/hf_cache/`

---

## Phase A: Base Model Evaluation (Weeks 9--10)

### A1. Deploy DeepSeek-R1 on Foundry (5 min, portal)

1. Go to [ai.azure.com](https://ai.azure.com) -> open `LLM-Defeasible-Foundry`
2. Model catalog -> search "DeepSeek-R1" -> Deploy -> Global Standard
3. Deployment name: `DeepSeek-R1`

### A2. Validate all four endpoints

```bash
python experiments/validate_api_keys.py
```

### A3. Submit full Foundry evaluation (4 models, all instances, all modalities)

```bash
cd /projects/paco0228/blanc && git pull
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
```

Query budget: 409 instances x 4 models x 4 modalities x 2 strategies = **13,088 queries**
Estimated cost: ~$23 total

### A4. Submit CURC open-source base evaluation (3 models)

```bash
bash hpc/slurm_evaluate_curc_all.sh
```

This submits three independent SLURM jobs for DeepSeek-R1-70B, Qwen 72B, and Qwen 32B on `aa100` partition. Each uses 1x A100 80GB with vLLM for inference.

### A5. Run symbolic baseline (in parallel, no GPU)

```bash
pip install clingo
python experiments/symbolic_baseline.py --results-dir experiments/results/
```

### A6. Run all analysis scripts (after A3--A4 complete)

```bash
python experiments/analyze_results.py --results-dir experiments/results/
python experiments/generate_paper_tables.py --results-dir experiments/results/
python experiments/error_taxonomy.py --results-dir experiments/results/
python experiments/novelty_analysis.py --results-dir experiments/results/
python experiments/conservativity_analysis.py --results-dir experiments/results/
python experiments/scaling_analysis.py --results-dir experiments/results/
python experiments/difficulty_analysis.py --results-dir experiments/results/
python experiments/partition_sensitivity.py --results-dir experiments/results/
```

**Phase A verifies**: Paper Section 5 claims (L2 vs L3 accuracy gap, CoT overthinking, error taxonomy, rendering robustness). Populates Tables 1--2 and Section 5 analysis.

---

## Phase B: Defeasible Fine-Tuning (Weeks 11--12)

Phase B implements paper Section 6. The goal is to test whether the belief revision deficit (near-zero Level 3 accuracy) can be addressed by fine-tuning open-source models on DeFAb preference data constructed from the benchmark's polynomial-time verifier.

### B0. Environment Setup (CURC)

**New conda environment for training** (separate from inference `vllm-env`):

```bash
ssh paco0228@login.rc.colorado.edu
conda create -n defab-train python=3.11 -y
conda activate defab-train

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate peft trl datasets bitsandbytes
pip install deepspeed
pip install scipy numpy tqdm python-dotenv tenacity

# Install blanc project in editable mode
cd /projects/paco0228/blanc
pip install -e .
```

Verify GPU access:
```bash
sinteractive --partition=aa100 --gres=gpu:1 --time=00:10:00
python -c "import torch; print(torch.cuda.device_count(), torch.cuda.get_device_name(0))"
```

### B1. Data Preparation -- Preference Dataset Construction

**Script**: `experiments/finetuning/prepare_preference_data.py`

**Inputs**:
- `instances/biology_dev_instances.json` (114 L2)
- `instances/legal_dev_instances.json` (116 L2)  
- `instances/materials_dev_instances.json` (144 L2)
- `instances/level3_instances.json` (35 L3)
- Base model evaluation results from Phase A (response cache)

**Process**:

1. **Train/val/test split** (70/15/15, stratified by level and domain):
   - Training: ~286 instances (262 L1/2 + 24 L3)
   - Validation: ~61 instances (56 L1/2 + 5 L3)
   - Test: ~62 instances (56 L1/2 + 6 L3)
   - Save splits to `instances/splits.json` for reproducibility

2. **Response sampling** from each base model:
   - For each training instance, sample n=16 responses at temperature=0.7
   - Use vLLM server on CURC (same setup as base eval)
   - Decode each response via cascading decoder (D1->D2->D3)
   - Score each response via DeFAb verifier (Equation 5 in paper):
     - L1/2: binary (correct selection = 1, else = 0)
     - L3: graded score {0, 0.25, 0.5, 0.75, 1.0}

3. **Preference pair extraction**:
   - From scored responses, extract all pairs where score_w > score_l
   - Filter pairs with score gap < 0.25 (too close to provide signal)
   - Add gold-anchored pairs: gold hypothesis rendered in same modality paired against each incorrect response

4. **Output format** (Hugging Face `datasets` compatible):
   ```json
   {
     "prompt": "<rendered DeFAb instance>",
     "chosen": "<preferred response>",
     "rejected": "<dispreferred response>",
     "score_chosen": 1.0,
     "score_rejected": 0.0,
     "level": 3,
     "domain": "biology",
     "margin": 1.0
   }
   ```
   Save to `experiments/finetuning/data/preferences_{model_name}.jsonl`

**SLURM job for response sampling** (`hpc/slurm_sample_responses.sh`):

```bash
#!/bin/bash
#SBATCH --job-name=defab-sample
#SBATCH --partition=aa100
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/sample_%j.out

module load anaconda
conda activate vllm-env

VLLM_MODEL="${VLLM_MODEL:-casperhansen/deepseek-r1-distill-llama-70b-awq}"
VLLM_PORT=8100

# Start vLLM server
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL" --port "$VLLM_PORT" \
    --dtype auto --max-model-len 8192 \
    --gpu-memory-utilization 0.90 --enforce-eager &
VLLM_PID=$!

# Wait for server
for i in $(seq 1 120); do
    curl -s "http://localhost:${VLLM_PORT}/health" && break
    sleep 5
done

# Sample responses
cd /projects/paco0228/blanc
python experiments/finetuning/prepare_preference_data.py \
    --model-name "$VLLM_MODEL" \
    --base-url "http://localhost:${VLLM_PORT}/v1" \
    --num-samples 16 \
    --temperature 0.7 \
    --output-dir experiments/finetuning/data/

kill $VLLM_PID
```

Submit for each model:
```bash
sbatch --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
```

### B2. DPO Training

**Script**: `experiments/finetuning/train_dpo.py`

Uses Hugging Face TRL `DPOTrainer` with LoRA via PEFT.

**Configuration** (from paper Section 6.6):

| Parameter | Value |
|-----------|-------|
| LoRA rank | 64 |
| LoRA alpha | 128 |
| LoRA target modules | q_proj, k_proj, v_proj, o_proj, gate_proj, up_proj |
| LoRA dropout | 0.05 |
| DPO beta | 0.1 |
| Learning rate | 5e-6 |
| LR schedule | cosine (to 5e-7) |
| Batch size (effective) | 16 (4 grad accum x 4 GPUs) |
| Epochs | 3 |
| Max sequence length | 2048 |
| Optimizer | AdamW (betas=0.9,0.999) |
| Weight decay | 0.01 |
| Warmup ratio | 0.1 |
| bf16 | True |
| DeepSpeed | ZeRO Stage 2 |

**Margin DPO** variant (paper Equation 10): custom loss function wrapping `DPOTrainer` that adds margin term `gamma * (score_chosen - score_rejected)` to the log-ratio difference. Gamma values to sweep: {0, 0.5, 1.0, 2.0, 4.0}. Select by validation Level 3 graded score.

**SLURM job** (`hpc/slurm_train_dpo.sh`):

```bash
#!/bin/bash
#SBATCH --job-name=defab-dpo
#SBATCH --partition=aa100
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --output=logs/dpo_%j.out

module load anaconda
conda activate defab-train

cd /projects/paco0228/blanc

BASE_MODEL="${BASE_MODEL:-casperhansen/deepseek-r1-distill-llama-70b-awq}"
DPO_VARIANT="${DPO_VARIANT:-standard}"
GAMMA="${GAMMA:-0.0}"
CURRICULUM="${CURRICULUM:-joint}"

export CUDA_VISIBLE_DEVICES=0,1,2,3

accelerate launch --num_processes=4 --mixed_precision=bf16 \
    --use_deepspeed --deepspeed_config_file experiments/finetuning/ds_config_zero2.json \
    experiments/finetuning/train_dpo.py \
    --base-model "$BASE_MODEL" \
    --data-dir experiments/finetuning/data/ \
    --output-dir experiments/finetuning/checkpoints/dpo_${DPO_VARIANT}_$(basename $BASE_MODEL)/ \
    --dpo-variant "$DPO_VARIANT" \
    --gamma "$GAMMA" \
    --curriculum "$CURRICULUM" \
    --beta 0.1 \
    --learning-rate 5e-6 \
    --epochs 3 \
    --per-device-batch-size 1 \
    --gradient-accumulation-steps 4 \
    --lora-rank 64 \
    --lora-alpha 128 \
    --max-length 2048 \
    --eval-steps 50 \
    --save-steps 100 \
    --logging-steps 10
```

**Training matrix** (12 DPO jobs total):

| Model | Variant | Gamma | Curriculum | Job name |
|-------|---------|-------|------------|----------|
| DS-R1-70B | standard | 0.0 | joint | dpo_std_ds |
| DS-R1-70B | margin | 2.0 | joint | dpo_margin_ds |
| DS-R1-70B | margin | 2.0 | sequential | dpo_margin_seq_ds |
| DS-R1-70B | margin | 2.0 | weighted | dpo_margin_wt_ds |
| Qwen-72B | standard | 0.0 | joint | dpo_std_qwen72 |
| Qwen-72B | margin | 2.0 | joint | dpo_margin_qwen72 |
| Qwen-72B | margin | 2.0 | sequential | dpo_margin_seq_qwen72 |
| Qwen-72B | margin | 2.0 | weighted | dpo_margin_wt_qwen72 |
| Qwen-32B | standard | 0.0 | joint | dpo_std_qwen32 |
| Qwen-32B | margin | 2.0 | joint | dpo_margin_qwen32 |
| Qwen-32B | margin | 2.0 | sequential | dpo_margin_seq_qwen32 |
| Qwen-32B | margin | 2.0 | weighted | dpo_margin_wt_qwen32 |

Submit all:
```bash
for MODEL in "casperhansen/deepseek-r1-distill-llama-70b-awq" "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ"; do
    # Standard DPO
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=standard,GAMMA=0.0,CURRICULUM=joint \
           hpc/slurm_train_dpo.sh
    # Margin DPO (joint)
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=joint \
           hpc/slurm_train_dpo.sh
    # Margin DPO (sequential)
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=sequential \
           hpc/slurm_train_dpo.sh
    # Margin DPO (weighted)
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=weighted \
           hpc/slurm_train_dpo.sh
done
```

**Gamma sweep** (separate job, best model only):
```bash
for G in 0.5 1.0 4.0; do
    sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",DPO_VARIANT=margin,GAMMA=$G,CURRICULUM=joint \
           hpc/slurm_train_dpo.sh
done
```

### B3. RLHF Training (VITL variant)

**Script**: `experiments/finetuning/train_rlhf_vitl.py`

Uses TRL `GRPOTrainer` (or custom PPO loop) with the DeFAb verifier as the exact reward function. The verifier is called at each PPO step to score generated responses.

**Configuration** (from paper Section 6.6):

| Parameter | Value |
|-----------|-------|
| LoRA rank | 64 |
| LoRA alpha | 128 |
| PPO clip ratio | 0.2 |
| KL coefficient beta | 0.05 |
| Mini-batch size | 8 |
| PPO steps per epoch | 256 |
| Learning rate | 1e-6 |
| Generation temperature | 0.7 |
| Max new tokens | 512 |
| DeepSpeed | ZeRO Stage 2 |

**Architecture**: The VITL variant replaces the learned reward model with the DeFAb verifier called directly:

1. Model generates response to DeFAb prompt
2. Response is decoded by cascading decoder (D1->D2->D3)
3. Decoded hypothesis is scored by `Level3Evaluator.compute_score()` (or binary check for L1/2)
4. Score is returned as exact reward to PPO optimizer

This requires the blanc library (`src/blanc/`) to be importable during training, which is handled by `pip install -e .` in the training environment.

**SLURM job** (`hpc/slurm_train_rlhf.sh`):

```bash
#!/bin/bash
#SBATCH --job-name=defab-rlhf
#SBATCH --partition=aa100
#SBATCH --nodes=1
#SBATCH --gres=gpu:4
#SBATCH --cpus-per-task=32
#SBATCH --mem=256G
#SBATCH --time=24:00:00
#SBATCH --output=logs/rlhf_%j.out

module load anaconda
conda activate defab-train

cd /projects/paco0228/blanc

BASE_MODEL="${BASE_MODEL:-casperhansen/deepseek-r1-distill-llama-70b-awq}"

export CUDA_VISIBLE_DEVICES=0,1,2,3

accelerate launch --num_processes=4 --mixed_precision=bf16 \
    --use_deepspeed --deepspeed_config_file experiments/finetuning/ds_config_zero2.json \
    experiments/finetuning/train_rlhf_vitl.py \
    --base-model "$BASE_MODEL" \
    --instances-dir instances/ \
    --output-dir experiments/finetuning/checkpoints/vitl_$(basename $BASE_MODEL)/ \
    --kl-coeff 0.05 \
    --clip-ratio 0.2 \
    --ppo-steps 256 \
    --learning-rate 1e-6 \
    --per-device-batch-size 2 \
    --gradient-accumulation-steps 2 \
    --lora-rank 64 \
    --lora-alpha 128 \
    --max-new-tokens 512 \
    --generation-temperature 0.7 \
    --eval-steps 50 \
    --save-steps 100
```

Submit for each model:
```bash
for MODEL in "casperhansen/deepseek-r1-distill-llama-70b-awq" "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ"; do
    sbatch --export=ALL,BASE_MODEL="$MODEL" hpc/slurm_train_rlhf.sh
done
```

### B4. Level Transfer Ablation

Tests paper Conjecture 8 (Level Transfer): train on L1/L2 data only, evaluate on L3.

```bash
for MODEL in "casperhansen/deepseek-r1-distill-llama-70b-awq" "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ"; do
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=l12_only \
           hpc/slurm_train_dpo.sh
done
```

The `l12_only` curriculum filters out all Level 3 preference pairs from the training set.

### B5. Evaluate Fine-Tuned Models

After training completes, evaluate each checkpoint on the held-out test set using the same protocol as base models.

**Script**: `experiments/finetuning/evaluate_finetuned.py`

Process:
1. Load base model + LoRA adapter from checkpoint
2. Merge LoRA weights (or serve via vLLM with LoRA adapter support)
3. Run the standard evaluation pipeline against the test split
4. Report fine-tuning lift per level, graded scores, error taxonomy shift

**SLURM job** (`hpc/slurm_eval_finetuned.sh`):

```bash
#!/bin/bash
#SBATCH --job-name=defab-eval-ft
#SBATCH --partition=aa100
#SBATCH --nodes=1
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/eval_ft_%j.out

module load anaconda
conda activate defab-train

cd /projects/paco0228/blanc

CHECKPOINT="${CHECKPOINT:-experiments/finetuning/checkpoints/dpo_margin_qwen72/}"
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-72B-Instruct-AWQ}"

python experiments/finetuning/evaluate_finetuned.py \
    --base-model "$BASE_MODEL" \
    --checkpoint "$CHECKPOINT" \
    --instances-dir instances/ \
    --splits-file instances/splits.json \
    --split test \
    --modalities M4 M2 M1 M3 \
    --strategies direct cot \
    --output-dir experiments/results/finetuned/$(basename $CHECKPOINT)/
```

Submit all trained checkpoints:
```bash
for CKPT in experiments/finetuning/checkpoints/*/; do
    MODEL_NAME=$(cat "$CKPT/base_model.txt")
    sbatch --export=ALL,CHECKPOINT="$CKPT",BASE_MODEL="$MODEL_NAME" hpc/slurm_eval_finetuned.sh
done
```

### B6. Fine-Tuning Analysis

**Scripts** (run after B5 completes):

```bash
# Generate Tables 3--5 from paper Section 6.7
python experiments/finetuning/generate_ft_tables.py \
    --results-dir experiments/results/finetuned/ \
    --base-results-dir experiments/results/ \
    --output-dir paper/tables/

# Test Conjecture 6 (L3 Improvement)
python experiments/finetuning/analyze_ft_lift.py \
    --results-dir experiments/results/finetuned/ \
    --base-results-dir experiments/results/

# Test Conjecture 7 (Error Taxonomy Shift)
python experiments/finetuning/analyze_error_shift.py \
    --results-dir experiments/results/finetuned/ \
    --base-results-dir experiments/results/

# Test Conjecture 8 (Level Transfer)
python experiments/finetuning/analyze_level_transfer.py \
    --results-dir experiments/results/finetuned/ \
    --base-results-dir experiments/results/

# Test Conjecture 9 (Margin DPO Advantage)
python experiments/finetuning/analyze_margin_effect.py \
    --results-dir experiments/results/finetuned/

# Curriculum comparison
python experiments/finetuning/analyze_curriculum.py \
    --results-dir experiments/results/finetuned/

# Novel correct resolutions (generalization beyond memorization)
python experiments/finetuning/analyze_novel_resolutions.py \
    --results-dir experiments/results/finetuned/ \
    --instances-dir instances/

# Scaling projections
python experiments/finetuning/analyze_scaling_projections.py \
    --results-dir experiments/results/finetuned/
```

---

## Phase C: Paper Completion (Weeks 13--14)

### C1. Populate Paper Tables with Results

| Table | Source | Script |
|-------|--------|--------|
| Table 1 (main accuracy) | Phase A results | `generate_paper_tables.py` |
| Table 2 (modality breakdown) | Phase A results | `generate_paper_tables.py` |
| Table 3 (fine-tuning results) | Phase B results | `generate_ft_tables.py` |
| Table 4 (curriculum comparison) | Phase B results | `generate_ft_tables.py` |
| Table 5 (error taxonomy shift) | Phase B results | `generate_ft_tables.py` |

### C2. Update Paper Sections with Results

| Section | Source | Notes |
|---------|--------|-------|
| Section 5.1 Tables 1--2 (expand to 6+ models) | Phase A | Include all Foundry + CURC models |
| Section 5.2 Grounding results | Phase A | Domain breakdown for all models |
| Section 5.3 Belief revision results | Phase A | Error taxonomy for all models |
| Section 5.4 CoT analysis | Phase A | CoT lift for all models |
| Section 6.7 Fine-tuning results | Phase B | Fill Tables 3--5 |
| Section 6.8 Hypotheses | Phase B | Confirm/reject Conjectures 6--9 |
| Section 7 Discussion (expand) | Phase A+B | Fine-tuning diagnostic paragraph |
| Section 8 Conclusion (update) | Phase A+B | Summarize fine-tuning findings |
| Abstract (update numbers) | Phase A+B | Final accuracy figures |

### C3. Remaining Code Changes

| Task | File | Effort |
|------|------|--------|
| Add 95% Wilson CIs to all accuracy output | `experiments/analyze_results.py` | ~20 lines |
| Write dataset statistics LaTeX generator | `experiments/generate_dataset_table.py` | ~50 lines |
| Fix `\cite{openai2023gpt4}` -> GPT-5.2 bib entry | `paper/references.bib` | 5 min |
| Add `\section{Decoder Validation Results}\label{app:decoder}` appendix | `paper/paper.tex` | 15 min |
| Replace `David S. Hippocampus` author block | `paper/paper.tex` lines 125--154 | 2 min |

---

## Experimental Design: Claim Verification Matrix

Every claim in the paper maps to a specific experiment. This matrix ensures rigorous verification.

### Section 5 Claims (Base Evaluation -- Phase A)

| Claim | Experiment | Metric | Verified by |
|-------|-----------|--------|-------------|
| L2 accuracy >= 88% (closed-source) | Full Foundry eval, 4 models | Rendering-robust accuracy | `analyze_results.py` |
| L3 accuracy <= 2% (closed-source) | Full Foundry eval, 4 models | Rendering-robust accuracy | `analyze_results.py` |
| ~90pp gap between L2 and L3 | All 6+ models evaluated | Per-level accuracy | `analyze_results.py` |
| CoT hurts L2 (overthinking) | All models, direct vs CoT | Delta_CoT per level | `analyze_results.py` |
| CoT neutral at L3 | All models, direct vs CoT | Delta_CoT at L3 | `analyze_results.py` |
| Claude outperforms GPT-5.2 | Foundry eval | Per-metric comparison | `analyze_results.py` |
| Error taxonomy: GPT=E1, Claude=E2 | Full eval L3 | E1-E5 distribution | `error_taxonomy.py` |
| Rendering-robust < per-modality avg | All models | Min-modality vs mean | `analyze_results.py` |
| Domain-agnostic L2 difficulty | Per-domain breakdown | Accuracy by domain | `analyze_results.py` |
| Symbolic solver ceiling | clingo on same instances | ASP accuracy | `symbolic_baseline.py` |
| Difficulty ordering L1 < L2 < L3 | All models, all levels | Accuracy monotonicity | `difficulty_analysis.py` |
| Yield monotonicity (Prop 8) | Partition sensitivity | Yield vs delta | `partition_sensitivity.py` |
| Qwen 72B vs 32B scaling gradient | CURC Qwen pair | Delta_Acc / Delta_log(params) | `scaling_analysis.py` |
| Reasoning vs instruction tier | DS-R1 vs Qwen-72B at ~70B | Per-level accuracy | `analyze_results.py` |

### Section 6 Claims (Fine-Tuning -- Phase B)

| Claim / Conjecture | Experiment | Metric | Verified by |
|---------------------|-----------|--------|-------------|
| Conj 6: L3 lift > 0 under DPO and VITL | DPO + VITL for all 3 models | Delta_FT per level | `analyze_ft_lift.py` |
| Conj 6: VITL > DPO | Compare VITL vs DPO per model | L3 accuracy and graded score | `analyze_ft_lift.py` |
| Conj 7: Error shift E1/E2 -> E4/E5 | Error taxonomy before/after FT | E1-E5 distribution shift | `analyze_error_shift.py` |
| Conj 8: L1/L2 training -> L3 transfer | DPO on L1/L2 only, eval L3 | L3 Delta_FT | `analyze_level_transfer.py` |
| Conj 9: Margin DPO > standard DPO | Gamma=2.0 vs gamma=0 | L3 graded score | `analyze_margin_effect.py` |
| Conj 9: Advantage at 0.5->0.75 transition | Score distribution analysis | Per-tier improvement | `analyze_margin_effect.py` |
| Sequential curriculum > joint | Compare 3 curriculum schedules | L3 accuracy | `analyze_curriculum.py` |
| Novel correct resolutions exist | Check FT outputs against training gold | Fraction novel-correct | `analyze_novel_resolutions.py` |
| Scaling projections (log-linear) | Subsample training at 10/25/50/100% | Fitted slope b per level | `analyze_scaling_projections.py` |
| Training data deficit vs architectural | L3 lift magnitude | Delta_FT >> 0 vs ~0 | `analyze_ft_lift.py` |

---

## File Structure: Fine-Tuning Pipeline

```
experiments/finetuning/
    prepare_preference_data.py     # B1: Response sampling + preference extraction
    train_dpo.py                   # B2: DPO/Margin-DPO training with TRL
    train_rlhf_vitl.py             # B3: VITL-RLHF training with exact verifier
    evaluate_finetuned.py          # B5: Evaluate fine-tuned checkpoints
    generate_ft_tables.py          # B6: LaTeX Tables 3--5
    analyze_ft_lift.py             # B6: Conjecture 6
    analyze_error_shift.py         # B6: Conjecture 7
    analyze_level_transfer.py      # B6: Conjecture 8
    analyze_margin_effect.py       # B6: Conjecture 9
    analyze_curriculum.py          # B6: Curriculum comparison
    analyze_novel_resolutions.py   # B6: Generalization analysis
    analyze_scaling_projections.py # B6: Log-linear scaling curves
    ds_config_zero2.json           # DeepSpeed ZeRO-2 config
    data/                          # Generated preference datasets (gitignored)
    checkpoints/                   # LoRA checkpoints (gitignored)

hpc/
    slurm_sample_responses.sh      # B1: Response sampling on GPU
    slurm_train_dpo.sh             # B2: DPO training (4xA100)
    slurm_train_rlhf.sh            # B3: VITL-RLHF training (4xA100)
    slurm_eval_finetuned.sh        # B5: Evaluate checkpoints (1xA100)
    slurm_train_all.sh             # Submit all training jobs
```

---

## CURC Resource Budget

### Phase A: Base Evaluation

| Job | Partition | GPUs | Time | Jobs |
|-----|-----------|------|------|------|
| Foundry eval (4 models, API only) | amilan | 0 | 12h | 1 |
| CURC eval (DS-R1-70B) | aa100 | 1x A100 | 24h | 1 |
| CURC eval (Qwen-72B) | aa100 | 1x A100 | 24h | 1 |
| CURC eval (Qwen-32B) | aa100 | 1x A100 | 24h | 1 |
| **Subtotal** | | 3 GPU-days | | 4 |

### Phase B: Fine-Tuning

| Job | Partition | GPUs | Time | Jobs |
|-----|-----------|------|------|------|
| Response sampling (3 models) | aa100 | 1x A100 | 12h each | 3 |
| DPO training (12 configs) | aa100 | 4x A100 | 24h each | 12 |
| VITL-RLHF training (3 models) | aa100 | 4x A100 | 24h each | 3 |
| Level transfer ablation (3 models) | aa100 | 4x A100 | 24h each | 3 |
| Gamma sweep (3 extra values) | aa100 | 4x A100 | 24h each | 3 |
| Evaluation of checkpoints (~24 ckpts) | aa100 | 1x A100 | 12h each | 24 |
| **Subtotal** | | ~120 GPU-days | | 48 |

### Total CURC Budget: ~123 GPU-days

At CURC Alpine rates (free for CU Boulder researchers), this is $0. The bottleneck is queue wait time on `aa100` partition, not cost. Jobs can be submitted in parallel to the extent queue capacity allows. The 4xA100 training jobs are the long pole; prioritize these.

**Parallelism strategy**: Submit the 3 response sampling jobs first (1 GPU each, can run concurrently). Once complete, submit all DPO training jobs (12 jobs x 4 GPUs = 48 GPUs requested; queue will serialize as needed). VITL-RLHF jobs can wait until DPO results indicate which model benefits most. Evaluation jobs (1 GPU each) are lightweight and can run in gaps.

---

## Cost Summary

| Phase | Models | Queries | Est. cost |
|-------|--------|---------|-----------|
| Pilot (done) | GPT-5.2, Claude | ~640 | ~$2.55 |
| Full Foundry eval | GPT-5.2, Kimi, Claude, DeepSeek-R1 | ~13,088 | ~$23 |
| CURC base eval | DS-R1-70B, Qwen 72B, Qwen 32B | ~9,816 | $0 |
| CURC fine-tuning | 3 models x multiple configs | N/A | $0 |
| CURC FT evaluation | ~24 checkpoints | ~24,000 | $0 |
| **Total** | | | **~$26** |

---

## Timeline

| Week | Phase | Deliverable |
|------|-------|-------------|
| 9--10 | A | Base evaluation: all 6+ models, all modalities, all levels |
| 10 | B0--B1 | Fine-tuning env setup, preference data construction |
| 11 | B2--B3 | DPO and VITL-RLHF training (12+ jobs on CURC) |
| 12 | B4--B6 | Level transfer ablation, fine-tuned model evaluation, analysis |
| 13 | C1--C2 | Populate all paper tables and sections from results |
| 14 | C3 | Final paper polish, submission |

---

## Quick-Reference Commands

```bash
# Phase A: Base evaluation
python experiments/validate_api_keys.py
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
bash hpc/slurm_evaluate_curc_all.sh

# Phase B: Fine-tuning
sbatch hpc/slurm_sample_responses.sh                    # Response sampling
sbatch hpc/slurm_train_dpo.sh                           # DPO training
sbatch hpc/slurm_train_rlhf.sh                          # VITL-RLHF training
for CKPT in experiments/finetuning/checkpoints/*/; do   # Evaluate all checkpoints
    sbatch --export=ALL,CHECKPOINT="$CKPT" hpc/slurm_eval_finetuned.sh
done

# Analysis
python experiments/analyze_results.py --results-dir experiments/results/
python experiments/finetuning/generate_ft_tables.py --results-dir experiments/results/finetuned/
python experiments/finetuning/analyze_ft_lift.py --results-dir experiments/results/finetuned/
```
