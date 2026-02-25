# Implementation Plan: LLM Evaluation, Fine-Tuning, and Submission

**Date**: 2026-02-25 (updated)
**Author**: Patrick Cooper
**Status**: Phase B pipeline implemented. Phase A evaluation not yet run. B6 analysis scripts not yet written. Several paper claims still unsubstantiated.
**Next action**: Run `python experiments/run_foundry_local.py` (full Foundry evaluation), then submit CURC base eval jobs, then build B6 analysis scripts, then run training matrix.

---

## Completed Work

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1--2 | Expert KB foundation -- 2,318 rules (YAGO, WordNet, LKIF, MatOnto) | Done |
| 3 | Instance generation -- 374 Level 2 instances | Done |
| 4 | Statistical analysis (Section 4.3) | Done |
| 5--6 | Full codec: M1--M4 encoders, D1--D3 decoders, cascading decoder | Done |
| 7 | Validation and testing infrastructure (494 tests, 81% coverage) | Done |
| 8 | Evaluation infrastructure (pipeline, prompting, response cache) | Done |
| 8.5a | Level 3 instance generation -- 35 defeater instances | Done |
| 8.5b | All Section 5 analysis scripts written and tested | Done |
| 9a | Azure AI Foundry integration -- GPT-5.2, Kimi, Claude, DeepSeek-R1 confirmed live | Done |
| 9b | Pilot evaluation -- GPT-5.2 (88.3% L2 / 1.4% L3), Claude (91.7% / 2.1%) | Done (60 L2 instances, M4+M2 only) |
| 9c | Pipeline fixes: `.env` auto-load, CoT extraction, empty-cache skip, max_tokens | Done |
| 9d | DeepSeek-R1 added to Foundry as 4th primary model (`foundry-deepseek`) | Done |
| 10 | Paper Section 6: Defeasible Fine-Tuning via Preference Optimization | Done |
| B0 | `defab-train` conda env documented | Done |
| B1 | `prepare_preference_data.py` -- preference data construction | Done |
| B2 | `train_dpo.py` -- standard + margin-weighted DPO with curriculum | Done |
| B3 | `train_rlhf_vitl.py` -- VITL and reward-model RLHF | Done |
| B5 | `evaluate_finetuned.py` -- finetuned checkpoint evaluation | Done |
| B-SLURM | `slurm_sample_responses.sh`, `slurm_train_dpo.sh`, `slurm_train_rlhf.sh`, `slurm_eval_finetuned.sh`, `slurm_train_all.sh` | Done |
| Symbolic | Symbolic baseline: L2=100% (374/374), L3=100% (35/35) | Done |

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
| Kimi-K2.5 | Foundry (OpenAI-compat) | `Kimi-K2.5` | 250 | $1.40 | $2.80 | Reasoning | Live (deferred from pilot) |
| claude-sonnet-4-6 | Foundry (AnthropicFoundry) | `claude-sonnet-4-6` | 250 | $3.00 | $15.00 | Instruction | Live |
| DeepSeek-R1 | Foundry (OpenAI-compat) | `DeepSeek-R1` | 5,000 | $1.35 | $5.40 | Reasoning, open | Live |

**Shared key**: `FOUNDRY_API_KEY` in `.env`

### Open-Source -- CURC Alpine (base evaluation + fine-tuning)

These models are evaluated via CURC vLLM for base accuracy, then fine-tuned via DPO/RLHF on CURC GPUs.

| Model | HuggingFace ID | VRAM (inference) | VRAM (training) | Type |
|-------|----------------|------------------|-----------------|------|
| DeepSeek-R1-Distill-70B | `casperhansen/deepseek-r1-distill-llama-70b-awq` | ~35 GB | 4xA100 (LoRA) | Reasoning |
| Qwen 2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct-AWQ` | ~36 GB | 4xA100 (LoRA) | Instruction |
| Qwen 2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct-AWQ` | ~16 GB | 2xA100 (LoRA) | Scaling |

CURC env: `vllm-env` (inference), `defab-train` (fine-tuning)
HF cache: `/scratch/alpine/paco0228/hf_cache/`

---

## Phase A: Base Model Evaluation (Weeks 9--10) -- NOT YET RUN

### A1. Validate all four Foundry endpoints

```bash
python experiments/validate_api_keys.py
```

### A2. Submit full Foundry evaluation (4 models, all 409 instances, all modalities)

Run locally (no SLURM, rate-limited API calls, ~12h):

```bash
python experiments/run_foundry_local.py
```

Or via SLURM on CURC amilan partition (no GPU required):

```bash
cd /projects/paco0228/blanc && git pull
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
```

Query budget: 409 instances x 4 models x 4 modalities x 2 strategies = **13,088 queries**
Estimated cost: ~$23 total

### A3. Submit CURC open-source base evaluation (3 models)

```bash
bash hpc/slurm_evaluate_curc_all.sh
```

This submits three independent SLURM jobs for DeepSeek-R1-70B, Qwen 72B, and Qwen 32B on `aa100` partition. Each uses 1x A100 80GB with vLLM for inference.

### A4. Run all analysis scripts (after A2--A3 complete)

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

Phase B implements paper Section 6. All training scripts and SLURM jobs exist. The following sub-phases must run in order.

### B0. Environment Setup (CURC) -- Documented, not yet confirmed

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

**Prerequisite**: Phase A must complete so that base model evaluation results and response caches are available.

**SLURM job for response sampling** (`hpc/slurm_sample_responses.sh`):

Submit for each model:
```bash
sbatch --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
```

Each job starts a vLLM server on 1x A100 80GB, samples n=16 responses per training instance at temperature=0.7, decodes and scores all responses via the DeFAb verifier, and writes preference JSONL to `experiments/finetuning/data/`.

Expected output: ~4,200 L1/L2 pairs + ~1,800 L3 pairs per model.

**Note**: The `instances/splits.json` file (70/15/15 stratified split) is created by this script on first run and reused by all subsequent training scripts. Verify it exists after B1 completes before submitting B2/B3.

### B2. DPO Training

**Script**: `experiments/finetuning/train_dpo.py`

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
| Batch size (effective) | 16 (2 per-device x 8 grad accum x 1 node) |
| Epochs | 3 |
| Max sequence length | 2048 |
| Optimizer | AdamW (betas=0.9,0.999) |
| Weight decay | 0.01 |
| Warmup steps | 100 |
| bf16 | True |
| DeepSpeed | ZeRO Stage 2 |

**Training matrix** (12 DPO jobs total via `slurm_train_all.sh`):

| Model | Variant | Curriculum | Job name |
|-------|---------|------------|----------|
| DS-R1-70B | standard | joint | dpo_std_joint_ds |
| DS-R1-70B | margin | joint | dpo_margin_joint_ds |
| DS-R1-70B | standard | weighted | dpo_std_weighted_ds |
| DS-R1-70B | margin | weighted | dpo_margin_weighted_ds |
| Qwen-72B | standard | joint | dpo_std_joint_qwen72 |
| Qwen-72B | margin | joint | dpo_margin_joint_qwen72 |
| Qwen-72B | standard | weighted | dpo_std_weighted_qwen72 |
| Qwen-72B | margin | weighted | dpo_margin_weighted_qwen72 |
| Qwen-32B | standard | joint | dpo_std_joint_qwen32 |
| Qwen-32B | margin | joint | dpo_margin_joint_qwen32 |
| Qwen-32B | standard | weighted | dpo_std_weighted_qwen32 |
| Qwen-32B | margin | weighted | dpo_margin_weighted_qwen32 |

**Sequential curriculum** (3 additional jobs, L1/L2 then L3 in order):
```bash
for MODEL in "casperhansen/deepseek-r1-distill-llama-70b-awq" "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ"; do
    sbatch --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=sequential \
           hpc/slurm_train_dpo.sh
done
```

**Level-transfer ablation** (B4, tests Conjecture 3 -- Qwen-72B only):
The `l12_only` curriculum is currently **not implemented** in `train_dpo.py`. Add it as a fourth curriculum option that filters out all Level 3 preference pairs before training:

```python
# In _load_preference_data(), add to curriculum handling:
elif curriculum == "l12_only":
    records = [r for r in records if r.get("level", 2) != 3]
    print(f"  L1/L2-only curriculum: {len(records)} pairs (L3 excluded)")
```

Then submit:
```bash
sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",DPO_VARIANT=margin,GAMMA=2.0,CURRICULUM=l12_only \
       hpc/slurm_train_dpo.sh
```

**Gamma sweep** (3 additional jobs on Qwen-72B only, to select optimal gamma):
```bash
for G in 0.5 1.0 4.0; do
    sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",DPO_VARIANT=margin,GAMMA=$G,CURRICULUM=joint \
           hpc/slurm_train_dpo.sh
done
```

Submit all 12 standard DPO jobs at once:
```bash
bash hpc/slurm_train_all.sh --dpo-only
```

### B3. RLHF Training (VITL variant)

**Script**: `experiments/finetuning/train_rlhf_vitl.py`

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

**Note**: The current `slurm_train_rlhf.sh` has `KL_COEFF=0.1` and `MINI_BATCH_SIZE=4` as defaults, which conflict with the paper's values (beta=0.05, mini-batch=8). These defaults must be corrected before submission:

```bash
# Correct submission with paper-specified hyperparameters:
sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",RLHF_MODE=vitl,KL_COEFF=0.05,MINI_BATCH_SIZE=8 \
       hpc/slurm_train_rlhf.sh
```

RLHF training matrix (4 jobs, submitted via `bash hpc/slurm_train_all.sh --rlhf-only`):
- VITL for DS-R1-70B, Qwen-72B, Qwen-32B (3 jobs)
- Standard reward-model RLHF for Qwen-72B only (1 job, as control)

### B4. Level Transfer Ablation

Requires `l12_only` curriculum to be added to `train_dpo.py` first (see B2 above). Tests Conjecture 3 (Level Transfer): grounding-only training partially improves Level 3.

### B5. Evaluate Fine-Tuned Models

After training completes, evaluate each checkpoint on the held-out test set.

**Script**: `experiments/finetuning/evaluate_finetuned.py`

**SLURM job**: `hpc/slurm_eval_finetuned.sh`

**Missing**: `hpc/submit_eval_finetuned_all.sh` -- referenced in `slurm_train_all.sh` line 116 but does not exist. Must be written. It should loop over all checkpoint directories and submit an eval job for each:

```bash
#!/bin/bash
# hpc/submit_eval_finetuned_all.sh
for CKPT in experiments/finetuning/checkpoints/*/final; do
    BASE_MODEL=$(cat "$(dirname $CKPT)/base_model.txt" 2>/dev/null || echo "unknown")
    echo "Submitting eval for $CKPT (base: $BASE_MODEL)"
    sbatch --export=ALL,CHECKPOINT="$CKPT",BASE_MODEL="$BASE_MODEL" \
           hpc/slurm_eval_finetuned.sh
done
```

Each `train_dpo.py` and `train_rlhf_vitl.py` run should write `base_model.txt` to the checkpoint directory. Verify this is implemented in both training scripts.

### B6. Fine-Tuning Analysis Scripts -- NOT YET WRITTEN

All scripts listed below are referenced in the implementation plan but **do not exist** in `experiments/finetuning/`. They must be written before paper results can be populated.

| Script | Purpose | Paper table/section |
|--------|---------|---------------------|
| `experiments/finetuning/generate_ft_tables.py` | LaTeX Tables 4--6 (ft_main, curriculum, error_shift) | Section 6.7 |
| `experiments/finetuning/analyze_ft_lift.py` | Test Conjecture 1: L3 lift > 0, VITL > DPO | Section 6.8 |
| `experiments/finetuning/analyze_error_shift.py` | Test Conjecture 2: E1/E2 -> E4/E5 shift | Section 6.8, Table 6 |
| `experiments/finetuning/analyze_level_transfer.py` | Test Conjecture 3: L1/L2 training -> L3 lift | Section 6.8 |
| `experiments/finetuning/analyze_margin_effect.py` | Test Conjecture 4: margin DPO > standard DPO | Section 6.8 |
| `experiments/finetuning/analyze_curriculum.py` | Compare joint vs sequential vs weighted | Section 6.7, Table 5 |
| `experiments/finetuning/analyze_novel_resolutions.py` | Fraction of novel correct resolutions (generalization) | Section 6.8 additional |
| `experiments/finetuning/analyze_scaling_projections.py` | Log-linear scaling at 10/25/50/100% data | Section 6.8 additional |
| `experiments/finetuning/analyze_reward_fidelity.py` | Spearman correlation R_phi vs verifier score | Section 6.8 additional |
| `experiments/finetuning/analyze_reward_overoptimization.py` | Gap between mean R_phi and verifier score at final PPO checkpoint | Section 6.8 additional |

Each script should:
1. Accept `--results-dir` and `--base-results-dir` arguments
2. Load result JSONs from the evaluation pipeline
3. Compute the relevant metric(s)
4. Print a formatted summary and optionally write a `.tex` snippet
5. Handle missing data gracefully (not all checkpoints may have completed)

---

## Phase C: Paper Completion (Weeks 13--14)

### C1. Populate Paper Tables with Results

| Table | Source | Script |
|-------|--------|--------|
| Table 1 (main accuracy, 6+ models) | Phase A results | `generate_paper_tables.py` |
| Table 2 (modality x strategy breakdown) | Phase A results | `generate_paper_tables.py` |
| Table 4 (fine-tuning results) | Phase B results | `generate_ft_tables.py` |
| Table 5 (curriculum comparison) | Phase B results | `generate_ft_tables.py` |
| Table 6 (error taxonomy shift) | Phase B results | `generate_ft_tables.py` |

### C2. Update Paper Sections with Results

| Section | Source | Notes |
|---------|--------|-------|
| Section 5.1 Tables 1--2 (expand to 6 models) | Phase A | Include Kimi-K2.5, DeepSeek-R1, Qwen-72B, Qwen-32B |
| Section 5.2 Grounding results | Phase A | Domain breakdown for all 6 models |
| Section 5.3 Belief revision results | Phase A | Error taxonomy for all 6 models |
| Section 5.4 CoT analysis | Phase A | CoT lift for all 6 models |
| Section 5.5 Theory size scaling | Phase A | Run `difficulty_analysis.py` with size subsets |
| Section 6.7 Fine-tuning results | Phase B | Fill Tables 4--6 |
| Section 6.8 Hypotheses | Phase B | Confirm/reject Conjectures 1--4 |
| Section 7 Discussion | Phase A+B | Update with all model findings |
| Section 8 Conclusion | Phase A+B | Summarize fine-tuning findings |
| Abstract | Phase A+B | Update accuracy figures to full 6-model results |

### C3. Remaining Code and Paper Fixes

| Task | File | Priority |
|------|------|----------|
| Add `l12_only` curriculum to `train_dpo.py` | `experiments/finetuning/train_dpo.py` | **High** (blocks B4) |
| Write `hpc/submit_eval_finetuned_all.sh` | `hpc/submit_eval_finetuned_all.sh` | **High** (blocks B5) |
| Fix `slurm_train_rlhf.sh` default KL_COEFF (0.1 -> 0.05) and MINI_BATCH_SIZE (4 -> 8) | `hpc/slurm_train_rlhf.sh` | **High** (paper accuracy) |
| Write all 10 B6 analysis scripts | `experiments/finetuning/` | **High** (blocks C1) |
| Add 95% Wilson CIs to all accuracy output | `experiments/analyze_results.py` | Medium |
| Write dataset statistics LaTeX generator | `experiments/generate_dataset_table.py` | Medium |
| Fix GPT-5.2 bib entry (`\cite{openai2023gpt4}` is incorrect) | `paper/references.bib` | Medium |
| Add `\appendix\section{Decoder Validation Results}\label{app:decoder}` | `paper/paper.tex` | Medium (referenced at line 527) |
| Replace `David S. Hippocampus` author block | `paper/paper.tex` lines 125--154 | **High** |
| M1 narrative decoder manual audit (200 randomly sampled failures) | Manual + `validate_decoder_pipeline.py` | Medium |
| Add stage-weighted scoring robustness check to appendix | `paper/paper.tex` | Low |
| Verify `base_model.txt` written by training scripts | `experiments/finetuning/train_dpo.py`, `train_rlhf_vitl.py` | Medium |

---

## Experimental Design: Claim Verification Matrix

Every claim in the paper maps to a specific experiment. Unverified claims are marked.

### Section 4.1 Claims (Model Lineup)

| Claim | Status | Verified by |
|-------|--------|-------------|
| Six models evaluated across three tiers | **UNVERIFIED** -- only 2 complete | Phase A full eval |
| GPT-5.2 and Kimi on Foundry (eastus2, 250K TPM) | Partially verified (GPT/Claude live; Kimi deferred) | `validate_api_keys.py` |
| Open-source models fit in single A100 80GB under AWQ 4-bit | **UNVERIFIED** -- not yet run on CURC | Phase A CURC eval |
| DeepSeek-R1 `<think>` tokens stripped by harness | Done (code exists) | `model_interface.py` |

### Section 5 Claims (Base Evaluation -- Phase A)

| Claim | Status | Verified by |
|-------|--------|-------------|
| L2 accuracy >= 88% (closed-source) | Pilot only (60 L2 instances, 2 models) | Full Foundry eval |
| L3 accuracy <= 2% (closed-source) | Pilot only | Full Foundry eval |
| ~90pp gap between L2 and L3 | Pilot only | All 6 models evaluated |
| CoT hurts L2 by 15--20pp (overthinking) | Pilot only (GPT: -20pp, Claude: -15pp) | All 6 models |
| CoT neutral at L3 (GPT: -2.9pp, Claude: +1.4pp) | Pilot only | All 6 models |
| Claude outperforms GPT-5.2 on all metrics | Pilot only | Full Foundry eval |
| Error taxonomy: GPT=E1 dominant (55%), Claude=E2 dominant (64%) | Pilot only | Full eval L3 |
| Domain-agnostic L2 difficulty (>85% all domains) | Pilot only (2 models, 3 domains) | Full 6-model eval |
| Symbolic solver ceiling (L2=100%, L3=100%) | **VERIFIED** | `symbolic_baseline.py` |
| Difficulty ordering L1 < L2 < L3 | **UNVERIFIED** | `difficulty_analysis.py` |
| Rendering-robust < per-modality average | Pilot only | `analyze_results.py` |
| Conjecture modlevel (M1 best for L1, M4 best for L3) | **UNVERIFIED** | Phase A full 4-modality eval |
| Qwen 72B vs 32B scaling gradient per level | **UNVERIFIED** | Phase A CURC eval |
| Reasoning vs instruction tier at ~70B matched scale | **UNVERIFIED** | Phase A CURC eval |
| Theory size scaling (performance vs \|D\|) | **UNVERIFIED** | `difficulty_analysis.py` with size subsets |

### Section 5.4 Decoder Validation Claims

| Claim | Status | Verified by |
|-------|--------|-------------|
| M2--M4 achieve 100% round-trip recovery | **VERIFIED** | `validate_decoder_pipeline.py` |
| M1 narrative decoder: recovery rate reported | **UNVERIFIED** -- rate not computed | `validate_decoder_pipeline.py` M1 mode |
| Manual audit of 200 M1 decode failures | **UNVERIFIED** | Manual audit required |
| Full results in Appendix C (app:decoder) | **UNVERIFIED** -- appendix section missing from paper | Must be added to `paper.tex` |

### Section 6 Claims (Fine-Tuning -- Phase B)

| Claim / Conjecture | Status | Verified by |
|---------------------|--------|-------------|
| Conj 1: L3 lift > 0 under DPO and VITL | **UNVERIFIED** | `analyze_ft_lift.py` |
| Conj 1: VITL > standard DPO | **UNVERIFIED** | `analyze_ft_lift.py` |
| Conj 2: Error shift E1/E2 -> E4/E5 | **UNVERIFIED** | `analyze_error_shift.py` |
| Conj 3: L1/L2 training -> L3 lift > 0 | **UNVERIFIED** | `analyze_level_transfer.py` |
| Conj 4: Margin DPO > standard DPO (advantage at 0.5->0.75 transition) | **UNVERIFIED** | `analyze_margin_effect.py` |
| Sequential curriculum > joint/weighted at L3 | **UNVERIFIED** | `analyze_curriculum.py` |
| Novel correct resolutions exist (generalization) | **UNVERIFIED** | `analyze_novel_resolutions.py` |
| Reward model fidelity: Spearman rho(R_phi, verifier) | **UNVERIFIED** | `analyze_reward_fidelity.py` |
| Reward overoptimization: gap between R_phi and verifier at final PPO ckpt | **UNVERIFIED** | `analyze_reward_overoptimization.py` |
| Scaling projections (log-linear at 10/25/50/100% data) | **UNVERIFIED** | `analyze_scaling_projections.py` |

---

## File Structure: Fine-Tuning Pipeline

```
experiments/finetuning/
    prepare_preference_data.py          # B1: Response sampling + preference extraction [EXISTS]
    train_dpo.py                        # B2: DPO/Margin-DPO training with TRL [EXISTS]
    train_rlhf_vitl.py                  # B3: VITL-RLHF training with exact verifier [EXISTS]
    evaluate_finetuned.py               # B5: Evaluate fine-tuned checkpoints [EXISTS]
    generate_ft_tables.py               # B6: LaTeX Tables 4--6 [MISSING]
    analyze_ft_lift.py                  # B6: Conjecture 1 [MISSING]
    analyze_error_shift.py              # B6: Conjecture 2 [MISSING]
    analyze_level_transfer.py           # B6: Conjecture 3 [MISSING]
    analyze_margin_effect.py            # B6: Conjecture 4 [MISSING]
    analyze_curriculum.py               # B6: Curriculum comparison [MISSING]
    analyze_novel_resolutions.py        # B6: Generalization analysis [MISSING]
    analyze_scaling_projections.py      # B6: Log-linear scaling curves [MISSING]
    analyze_reward_fidelity.py          # B6: Spearman rho(R_phi, verifier) [MISSING]
    analyze_reward_overoptimization.py  # B6: Reward hacking diagnostic [MISSING]
    ds_config_zero2.json                # DeepSpeed ZeRO-2 config [EXISTS]
    data/                               # Generated preference datasets (gitignored)
    checkpoints/                        # LoRA checkpoints (gitignored)

hpc/
    slurm_sample_responses.sh           # B1: Response sampling on GPU [EXISTS]
    slurm_train_dpo.sh                  # B2: DPO training (4xA100) [EXISTS]
    slurm_train_rlhf.sh                 # B3: VITL-RLHF training (4xA100) [EXISTS -- hyperparams need fix]
    slurm_eval_finetuned.sh             # B5: Evaluate checkpoints (1xA100) [EXISTS]
    slurm_train_all.sh                  # Submit all training jobs [EXISTS]
    submit_eval_finetuned_all.sh        # Submit all checkpoint eval jobs [MISSING]
```

---

## CURC Resource Budget

### Phase A: Base Evaluation

| Job | Partition | GPUs | Time | Jobs |
|-----|-----------|------|------|------|
| Foundry eval (4 models, API only, amilan) | amilan | 0 | 12h | 1 |
| CURC eval (DS-R1-70B) | aa100 | 1x A100 | 24h | 1 |
| CURC eval (Qwen-72B) | aa100 | 1x A100 | 24h | 1 |
| CURC eval (Qwen-32B) | aa100 | 1x A100 | 24h | 1 |
| **Subtotal** | | 3 GPU-days | | 4 |

### Phase B: Fine-Tuning

| Job | Partition | GPUs | Time | Jobs |
|-----|-----------|------|------|------|
| Response sampling (3 models) | aa100 | 1x A100 | 8h each | 3 |
| DPO training (12 std configs) | aa100 | 4x A100 | 24h each | 12 |
| DPO sequential curriculum (3 models) | aa100 | 4x A100 | 24h each | 3 |
| DPO l12_only ablation (Qwen-72B) | aa100 | 4x A100 | 24h | 1 |
| DPO gamma sweep (3 extra values, Qwen-72B) | aa100 | 4x A100 | 24h each | 3 |
| VITL-RLHF training (3 models) | aa100 | 4x A100 | 36h each | 3 |
| Standard RM RLHF training (Qwen-72B) | aa100 | 4x A100 | 36h | 1 |
| Evaluation of all checkpoints (~24 ckpts) | aa100 | 1x A100 | 4h each | 24 |
| **Subtotal** | | ~155 GPU-days | | 50 |

### Total CURC Budget: ~158 GPU-days

At CURC Alpine rates (free for CU Boulder researchers), this is $0. The bottleneck is queue wait time on `aa100` partition, not cost. The 4xA100 training jobs (24--36h each) are the long pole.

**Parallelism strategy**: Submit the 3 response sampling jobs first (1 GPU each, run concurrently). Once all three complete and `instances/splits.json` exists, submit all DPO and RLHF training jobs. Evaluation jobs (4h, 1 GPU) are lightweight and can run in gaps. Gamma sweep (Qwen-72B only) can run in parallel with other model training.

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
| 9--10 | A | Base evaluation: all 6 models, all modalities, all levels |
| 10 | B0--B1 | Fine-tuning env setup + confirmation, preference data construction |
| 10--11 | Code | Write 10 B6 analysis scripts; add `l12_only` curriculum; write `submit_eval_finetuned_all.sh` |
| 11 | B2--B3 | DPO and VITL-RLHF training (15+ jobs on CURC) |
| 12 | B4--B5 | Level transfer ablation, fine-tuned model evaluation |
| 12 | B6 | Run all analysis scripts; populate Tables 4--6 |
| 13 | C1--C2 | Populate all paper tables and sections from results |
| 14 | C3 | Author block, bib fix, decoder appendix, final polish, submission |

---

## Quick-Reference Commands

```bash
# Phase A: Base evaluation
python experiments/validate_api_keys.py
python experiments/run_foundry_local.py                   # Full Foundry eval (local)
bash hpc/slurm_evaluate_curc_all.sh                       # CURC open-source eval

# Phase B: Fine-tuning
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq" hpc/slurm_sample_responses.sh

bash hpc/slurm_train_all.sh                               # Submit all DPO + RLHF jobs
bash hpc/submit_eval_finetuned_all.sh                     # Evaluate all checkpoints (write this first)

# Analysis
python experiments/analyze_results.py --results-dir experiments/results/
python experiments/generate_paper_tables.py --results-dir experiments/results/
python experiments/finetuning/generate_ft_tables.py --results-dir experiments/results/finetuned/
python experiments/finetuning/analyze_ft_lift.py --results-dir experiments/results/finetuned/
```
