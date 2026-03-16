# Implementation Plan: LLM Evaluation, Fine-Tuning, and Submission

**Date**: 2026-03-16 (updated)
**Author**: Patrick Cooper
**Status**: Phase A COMPLETE. Phase B finetuning NOT STARTED (blocked on CURC, TP fix committed). Phase C (adversarial debate via MCTS) COMPLETE -- all code, tests, experiments, and paper section implemented.
**Next action**: Push TP fix, pull on CURC, resubmit B1. Run debate experiments on full KBs.

---

## Completed Work

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1--2 | Expert KB foundation -- 2,318 rules (YAGO, WordNet, LKIF, MatOnto) | Done |
| 3 | Instance generation -- 374 Level 2 instances | Done |
| 4 | Statistical analysis (Section 4.3) | Done |
| 5--6 | Full codec: M1--M4 encoders, D1--D3 decoders, cascading decoder | Done |
| 7 | Validation and testing infrastructure (797+ tests) | Done |
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
| B2 | `train_dpo.py` -- standard + margin-weighted DPO with curriculum | Done (fixed: Eq.10 additive margin, `l12_only`, `--data-fraction`, `base_model.txt`) |
| B3 | `train_rlhf_vitl.py` -- VITL and reward-model RLHF | Done (fixed: KL=0.05, mini_batch=8, LR=1e-6, max_tokens=512, `base_model.txt`) |
| B5 | `evaluate_finetuned.py` -- finetuned checkpoint evaluation | Done |
| B5-sub | `hpc/submit_eval_finetuned_all.sh` -- batch checkpoint eval submission | Done |
| B-SLURM | `slurm_sample_responses.sh`, `slurm_train_dpo.sh`, `slurm_train_rlhf.sh`, `slurm_eval_finetuned.sh`, `slurm_train_all.sh` | Done (rlhf hyperparams fixed; dpo DATA_FRACTION added) |
| B6 | All 10 B6 analysis scripts | Done |
| Symbolic | Symbolic baseline: L2=100% (374/374), L3=100% (35/35) | Done |
| A2 | Full Foundry evaluation -- 4 models, 409 instances, 4 modalities, 2 strategies | Done (paper Tables 1-3 populated) |
| A4 | Analysis scripts run on Foundry results (McNemar, Wilson CIs, domain breakdown) | Done |
| SLURM | Fix `BASH_SOURCE` bug in 8 SLURM scripts (use `SLURM_SUBMIT_DIR` fallback) | Done (commit `8e67169`) |
| SLURM | Fix CUDA OOM for 70B+ models: add TP_SIZE support, tensor parallelism, optimized vLLM params | Done (Mar 13) |

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
| DeepSeek-R1 | Foundry (OpenAI-compat) | `DeepSeek-R1` | 250 | $1.35 | $5.40 | Reasoning, open | Live (endpoint: services.ai.azure.com) |

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

## Phase A: Base Model Evaluation (Weeks 9--10) -- FOUNDRY COMPLETE, CURC OPTIONAL

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

Submit for each model (70B+ models require TP=2 and 2 GPUs due to CURC aa100 partition
having a mix of 40GB and 80GB A100 nodes -- 72B/70B AWQ models need ~36-37 GB for weights
alone, which leaves no KV cache room on 40GB nodes):
```bash
sbatch --gres=gpu:2 --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq",TP_SIZE=2 hpc/slurm_sample_responses.sh
sbatch --gres=gpu:2 --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",TP_SIZE=2 hpc/slurm_sample_responses.sh
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
```

Each job starts a vLLM server (TP=2 for 70B+ models, TP=1 for 32B), samples n=16 responses per training instance at temperature=0.7, decodes and scores all responses via the DeFAb verifier, and writes preference JSONL to `experiments/finetuning/data/`.

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

## Phase C-Debate: Adversarial Defeasible Debate (COMPLETE -- Week 12)

### C-D1. MCTS Engine (`src/blanc/search/`) -- DONE

- `mcts.py`: domain-agnostic MCTS with UCB1 selection, configurable exploration constant, convergence detection
- `derivation_space.py`: maps defeasible reasoning to MCTS (DerivationState, DerivationAction, DerivationSpace)
- `reward.py`: derivation strength, novelty, criticality, and composite reward functions

### C-D2. Debate Framework (`src/blanc/debate/`) -- DONE

- `agent.py`: DebateAgent base, ProponentAgent (strength-weighted), OpponentAgent (novelty-weighted)
- `protocol.py`: DebateProtocol with 4 phases (proposal, challenge, defense, resolution)
- `resolution.py`: robustness, grounding, creativity scores; debate_outcome with weighted aggregate

### C-D3. Derivation Tree Extensions -- DONE

- `get_critical_subtree()`, `enumerate_permutations()`, `tree_overlap()`, `extract_support_path()`

### C-D4. Tests -- DONE

- 63 tests across `tests/search/` and `tests/debate/` (all passing)

### C-D5. Experiments -- DONE

- `experiments/debate/run_debate.py`: CLI for running debates across KBs
- `experiments/debate/analyze_debate.py`: analysis + LaTeX table generation (Tables 7-9)

### C-D6. Paper Section 7 -- DONE

- 8 subsections, 6 definitions, 3 theorems with proofs, Tables 7-9
- Abstract, Introduction (contribution 7), Related Work, Discussion, Conclusion updated

---

## Phase C-Paper: Paper Completion (Weeks 13--14)

### C1. Populate Paper Tables with Results

| Table | Source | Status |
|-------|--------|--------|
| Table 1 (main accuracy, 4 models) | Phase A results | **DONE** |
| Table 2 (modality breakdown) | Phase A results | **DONE** |
| Table 3 (domain breakdown) | Phase A results | **DONE** |
| Table 4 (fine-tuning results) | Phase B results | Awaiting B5 |
| Table 5 (curriculum comparison) | Phase B results | Awaiting B5 |
| Table 6 (error taxonomy shift) | Phase B results | Awaiting B5 |
| Table 7 (debate robustness) | Phase C-Debate | **DONE** |
| Table 8 (grounding + creativity) | Phase C-Debate | **DONE** |
| Table 9 (winner distribution) | Phase C-Debate | **DONE** |

### C2. Update Paper Sections with Results

| Section | Source | Status |
|---------|--------|--------|
| Sections 5.1-5.4 (4-model results) | Phase A | **DONE** |
| Section 6.7 Fine-tuning results | Phase B | Awaiting B5/B6 |
| Section 6.8 Hypotheses | Phase B | Awaiting B5/B6 |
| Section 7 Discussion | Phase A done, Phase B pending | Partial |
| Section 8 Conclusion | Phase A done, Phase B pending | Partial |
| Appendix C (decoder validation) | Standalone | **Not written** |

### C3. Remaining Code and Paper Fixes

| Task | File | Status |
|------|------|--------|
| ~~Add `l12_only` curriculum to `train_dpo.py`~~ | | Done |
| ~~Write `hpc/submit_eval_finetuned_all.sh`~~ | | Done |
| ~~Fix `slurm_train_rlhf.sh` hyperparams~~ | | Done |
| ~~Fix `MarginDPOTrainer` to match paper Eq.10~~ | | Done |
| ~~Write all 10 B6 analysis scripts~~ | | Done |
| ~~Run Phase A full Foundry evaluation~~ | | Done |
| ~~Fix author block~~ | | Done (commit `759b06c`) |
| ~~Fix GPT-5.2 bib entry~~ | | Done (commit `759b06c`) |
| ~~Fix SLURM BASH_SOURCE bug~~ | | Done (commit `8e67169`) |
| Add Appendix C (`app:decoder`) | `paper/paper.tex` | **Pending** |
| M1 narrative decoder manual audit | Manual | **Optional** |
| Add stage-weighted scoring robustness check to appendix | `paper/paper.tex` | Low |

---

## Experimental Design: Claim Verification Matrix

Every claim in the paper maps to a specific experiment. Unverified claims are marked.

### Section 4.1 Claims (Model Lineup)

| Claim | Status | Verified by |
|-------|--------|-------------|
| Four frontier models evaluated on Foundry | **VERIFIED** | Full Foundry eval (Feb 28) |
| GPT-5.2, Kimi, Claude, DeepSeek-R1 on Foundry | **VERIFIED** | `validate_api_keys.py` + full eval |
| Open-source models fit in single A100 80GB under AWQ 4-bit | **UNVERIFIED** -- not yet run on CURC | Phase A CURC eval (optional) |
| DeepSeek-R1 `<think>` tokens stripped by harness | **VERIFIED** (code exists and tested) | `model_interface.py` |

### Section 5 Claims (Base Evaluation -- Phase A)

| Claim | Status | Verified by |
|-------|--------|-------------|
| L2 accuracy 62-77% (4 models) | **VERIFIED** | Full Foundry eval, Table 1 |
| L3 accuracy 14-65% (strategy-dependent) | **VERIFIED** | Full Foundry eval, Table 1 |
| L2-to-L3 gap substantial (12-59 pp) | **VERIFIED** | Full Foundry eval |
| CoT hurts L2 by 1.5-31.3 pp (overthinking) | **VERIFIED** | Full Foundry eval, Section 5.4 |
| CoT helps reasoning models at L3 (+27 to +79 pp) | **VERIFIED** | Full Foundry eval, Section 5.4 |
| CoT hurts Claude at L3 (-14.3 pp) | **VERIFIED** | Full Foundry eval |
| Architectural dissociation (reasoning vs instruction) | **VERIFIED** | McNemar tests, p < 0.001 |
| Error taxonomy: model-specific failure signatures | **VERIFIED** | Full L3 eval |
| Domain ordering: biology easiest, legal hardest | **VERIFIED** | Table 3, 4 models |
| Symbolic solver ceiling (L2=100%, L3=100%) | **VERIFIED** | `symbolic_baseline.py` |
| M1 narrative bottleneck (55-70 pp gap) | **VERIFIED** | Table 2, 4 models |
| Rendering-robust accuracy dominated by M1 | **VERIFIED** | Full 4-modality eval |
| Qwen 72B vs 32B scaling gradient per level | **UNVERIFIED** | Phase A CURC eval (optional) |
| Reasoning vs instruction tier at ~70B matched scale | **UNVERIFIED** | Phase A CURC eval (optional) |
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
| Conj 5: GRPO sparser updates than DPO (effective rank, L0) | **UNVERIFIED** | `analyze_parameter_sparsity.py` |
| Conj 6: SFT positive L2 lift, lower L3 lift than DPO/GRPO | **UNVERIFIED** | `analyze_ft_lift.py` (SFT rows) |
| SFT baseline achieves positive L2 lift from gold demonstrations | **UNVERIFIED** | `evaluate_finetuned.py` on SFT checkpoints |
| GRPO/RLVR with DeFAb verifier produces targeted parameter updates | **UNVERIFIED** | `analyze_parameter_sparsity.py` |
| Spectral LoRA init concentrates adaptation on dominant spectral components | **UNVERIFIED** | `analyze_parameter_sparsity.py` (spectral checkpoints) |

---

## Phase B-SFT: Supervised Fine-Tuning (NEW)

SFT is the simplest post-training method: directly optimize the model to reproduce gold hypotheses encoded through the codec.

### B-SFT-1. Generate SFT Data

```bash
python experiments/finetuning/prepare_sft_data.py \
    --modalities M4 --strategies direct \
    --output-dir experiments/finetuning/data/
```

### B-SFT-2. Train SFT

```bash
for MODEL in "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ" "casperhansen/deepseek-r1-distill-llama-70b-awq"; do
    sbatch --export=ALL,BASE_MODEL="$MODEL",CURRICULUM=joint hpc/slurm_train_sft.sh
done
```

Training matrix: 3 models x joint curriculum = 3 jobs.

---

## Phase B-GRPO: RLVR via Group Relative Policy Optimization (NEW)

GRPO uses the DeFAb verifier as a verifiable reward, with group-relative advantage normalization producing sparse gradient signal.

### B-GRPO-1. Train GRPO

```bash
for MODEL in "Qwen/Qwen2.5-72B-Instruct-AWQ" "Qwen/Qwen2.5-32B-Instruct-AWQ" "casperhansen/deepseek-r1-distill-llama-70b-awq"; do
    sbatch --export=ALL,BASE_MODEL="$MODEL",CURRICULUM=joint hpc/slurm_train_grpo.sh
done
```

Training matrix: 3 models x joint curriculum = 3 jobs. GRPO is an online method (generates its own completions, scores with verifier) -- no preference data needed.

---

## Phase B-SPECTRAL: Spectral LoRA Initialization (NEW)

Optional `--lora-init spectral` flag added to all training scripts. Uses SVD of pre-trained weights to initialize LoRA matrices, concentrating adaptation on dominant spectral components.

To run any method with spectral init, add `LORA_INIT=spectral` to the SLURM export:

```bash
sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",LORA_INIT=spectral hpc/slurm_train_grpo.sh
```

---

## File Structure: Fine-Tuning Pipeline

```
experiments/finetuning/
    prepare_preference_data.py          # B1: Response sampling + preference extraction [EXISTS]
    prepare_sft_data.py                 # B-SFT: SFT dataset from gold hypotheses [EXISTS]
    train_dpo.py                        # B2: DPO/Margin-DPO, Eq.10, all curricula, data_fraction [EXISTS]
    train_rlhf_vitl.py                  # B3: VITL-RLHF with correct PPO hyperparams [EXISTS]
    train_sft.py                        # B-SFT: Supervised fine-tuning via TRL SFTTrainer [EXISTS]
    train_grpo.py                       # B-GRPO: RLVR via GRPO with DeFAb verifier reward [EXISTS]
    spectral_lora.py                    # B-SPECTRAL: SVD-based LoRA init + spectral metrics [EXISTS]
    evaluate_finetuned.py               # B5: Evaluate fine-tuned checkpoints [EXISTS]
    generate_ft_tables.py               # B6: LaTeX Tables 4-6 (SFT + GRPO rows added) [EXISTS]
    analyze_ft_lift.py                  # B6: Conjecture 1 -- L3 lift [EXISTS]
    analyze_error_shift.py              # B6: Conjecture 2 -- E1/E2 -> E4/E5 shift [EXISTS]
    analyze_level_transfer.py           # B6: Conjecture 3 -- l12_only transfer [EXISTS]
    analyze_margin_effect.py            # B6: Conjecture 4 -- margin vs std DPO [EXISTS]
    analyze_curriculum.py               # B6: Curriculum comparison [EXISTS]
    analyze_novel_resolutions.py        # B6: Novel correct resolutions [EXISTS]
    analyze_scaling_projections.py      # B6: Log-linear scaling curves [EXISTS]
    analyze_reward_fidelity.py          # B6: Spearman rho(R_phi, verifier) [EXISTS]
    analyze_reward_overoptimization.py  # B6: Reward hacking diagnostic [EXISTS]
    analyze_parameter_sparsity.py       # B6: Conjecture 5 -- GRPO sparse vs DPO dense [EXISTS]
    ds_config_zero2.json                # DeepSpeed ZeRO-2 config [EXISTS]
    data/                               # Generated preference/SFT datasets (gitignored)
    checkpoints/                        # LoRA checkpoints (gitignored)

hpc/
    run_all_experiments.sh              # Comprehensive orchestrator -- submits ALL phases [EXISTS]
    slurm_generate_instances.sh         # A0: Instance generation (Level 2 + Level 3) [EXISTS]
    slurm_evaluate_foundry.sh           # A2: Foundry eval (4 closed-source models) [EXISTS]
    slurm_evaluate_curc_all.sh          # A3: CURC eval coordinator (3 open-source models) [EXISTS]
    slurm_evaluate_curc_vllm.sh         # A3: Single model vLLM eval [EXISTS]
    slurm_analysis.sh                   # A4: Phase A analysis pipeline (11 scripts) [EXISTS]
    slurm_sample_responses.sh           # B1: Response sampling on GPU [EXISTS]
    slurm_train_dpo.sh                  # B2: DPO training (4xA100, DATA_FRACTION support) [EXISTS]
    slurm_train_rlhf.sh                 # B3: VITL-RLHF (KL=0.05, mini_batch=8, LR=1e-6) [EXISTS]
    slurm_train_sft.sh                  # B-SFT: SFT training (4xA100) [EXISTS]
    slurm_train_grpo.sh                 # B-GRPO: GRPO/RLVR training (4xA100) [EXISTS]
    slurm_eval_finetuned.sh             # B5: Evaluate checkpoints (1xA100) [EXISTS]
    slurm_train_all.sh                  # Submit all training jobs (DPO+RLHF+SFT+GRPO) [EXISTS]
    submit_eval_finetuned_all.sh        # Submit all checkpoint eval jobs [EXISTS]
    slurm_ft_analysis.sh                # B6: Fine-tuning analysis (11 scripts, Tables 4-6) [EXISTS]
    slurm_debate.sh                     # C: Adversarial debate experiments (Tables 7-9) [EXISTS]
    setup_curc_env.sh                   # Environment setup [EXISTS]
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
| Response sampling (3 models) | aa100 | 2x A100 (70B+), 1x A100 (32B) | 8h each | 3 |
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

| Week | Phase | Deliverable | Status |
|------|-------|-------------|--------|
| 9--10 | A | Base evaluation: 4 Foundry models, all modalities, all levels | **DONE** |
| 10 | Code | All B6 analysis scripts, l12_only, submit_eval_finetuned_all.sh | **DONE** |
| 10--11 | B0--B1 | CURC env setup, response sampling (3 models) | B1 failed 5 times: 2 SLURM bugs + 3 CUDA OOM (40GB A100) |
| 12 | B1 retry | TP=2 fix committed, resubmit B1 | **NOW** (Mar 13) |
| 11--12 | B2--B3 | DPO and VITL-RLHF training (16 jobs on CURC) | Pending B1 |
| 12--13 | B4--B5 | Level transfer ablation, fine-tuned model evaluation | Pending B2/B3 |
| 13 | B6 | Run all analysis scripts; populate Tables 4--6 | Pending B5 |
| 13--14 | C | Appendix C, final paper updates, submission | Pending B6 |

---

## Quick-Reference Commands

### Run Everything (recommended)

```bash
cd /projects/paco0228/blanc && git pull

# Preview what will be submitted (no actual SLURM jobs):
bash hpc/run_all_experiments.sh --dry-run

# Submit ALL phases (A0-A4, B0-B6, C) with SLURM dependency chains:
bash hpc/run_all_experiments.sh

# Skip phases that are already complete:
bash hpc/run_all_experiments.sh --skip-foundry --skip-instances --skip-debate

# Run only fine-tuning phases:
bash hpc/run_all_experiments.sh --phase B

# Resume from a specific phase:
bash hpc/run_all_experiments.sh --resume-from B1
```

### Run Individual Phases

```bash
# Step 0: Models already downloaded to CURC HF cache (confirmed Mar 9)
# /scratch/alpine/paco0228/hf_cache/models--Qwen--Qwen2.5-32B-Instruct-AWQ
# /scratch/alpine/paco0228/hf_cache/models--Qwen--Qwen2.5-72B-Instruct-AWQ
# /scratch/alpine/paco0228/hf_cache/models--casperhansen--deepseek-r1-distill-llama-70b-awq

# Step 1: B1 response sampling (submit from /projects/paco0228/blanc)
cd /projects/paco0228/blanc && git pull
sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
sbatch --gres=gpu:2 --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",TP_SIZE=2 hpc/slurm_sample_responses.sh
sbatch --gres=gpu:2 --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq",TP_SIZE=2 hpc/slurm_sample_responses.sh

# Step 2: After B1 completes -- verify data then submit training
ls experiments/finetuning/data/preferences_*.jsonl
bash hpc/slurm_train_all.sh

# Step 3: After training completes -- evaluate checkpoints
bash hpc/submit_eval_finetuned_all.sh

# Step 4: After evaluation -- run FT analysis (Tables 4-6, Conjectures 1-6)
sbatch hpc/slurm_ft_analysis.sh

# Step 5: Run debate experiments (Tables 7-9)
sbatch hpc/slurm_debate.sh

# Step 6: Run Phase A analysis (Tables 1-3)
sbatch hpc/slurm_analysis.sh

# Optional: CURC base evaluation for scaling analysis
bash hpc/slurm_evaluate_curc_all.sh
```
