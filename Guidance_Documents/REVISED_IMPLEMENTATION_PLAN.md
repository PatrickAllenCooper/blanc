# Implementation Plan: LLM Evaluation to Submission

**Date**: 2026-02-19 (updated)
**Author**: Patrick Cooper
**Status**: Pilot complete (GPT-5.2, Claude). DeepSeek-R1 moving to Foundry. Full evaluation next.
**Next action**: Deploy DeepSeek-R1 on Foundry portal → `sbatch slurm_evaluate_foundry.sh`

---

## Completed Work

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1–2 | Expert KB foundation — 2,318 rules (YAGO, WordNet, LKIF, MatOnto) | Done |
| 3 | Instance generation — 374 Level 2 instances | Done |
| 4 | Statistical analysis (Section 4.3) | Done |
| 5–6 | Full codec: M1–M4 encoders, D1–D3 decoders, cascading decoder | Done |
| 7 | Validation and testing infrastructure (503 tests, 86% coverage) | Done |
| 8 | Evaluation infrastructure (pipeline, prompting, response cache) | Done |
| 8.5a | Level 3 instance generation — 35 defeater instances | Done |
| 8.5b | All analysis scripts written and tested | Done |
| 9a | Azure AI Foundry integration — GPT-5.2, Kimi, Claude confirmed live | Done |
| 9b | Pilot evaluation — GPT-5.2 (88.3% L2 / 1.4% L3), Claude (91.7% / 2.1%) | Done |
| 9c | Pipeline fixes: `.env` auto-load, CoT extraction, empty-cache skip, max_tokens | Done |
| 9d | DeepSeek-R1 added to Foundry as 4th primary model (`foundry-deepseek`) | Done |

### Dataset

| Level | Count | Domains | Notes |
|-------|-------|---------|-------|
| Level 2 (rule abduction) | 374 | Biology 114, Legal 116, Materials 144 | Complete |
| Level 3 (defeater abduction) | 35 | Biology 16, Legal 10, Materials 9 | 10 with Nov > 0 |

---

## Evaluation Model Lineup

### Primary — Azure AI Foundry (all models on same infrastructure, same API key)

**Strategy**: Use Foundry wherever possible. CURC only for models not available as Foundry serverless.

| Model | Provider | Deployment name | RPM | Cost/1M in | Cost/1M out | Type | Status |
|-------|----------|----------------|-----|------------|-------------|------|--------|
| gpt-5.2-chat | Foundry (AzureOpenAI) | `gpt-5.2-chat` | 2,500 | $1.75 | $14.00 | Reasoning | Live |
| Kimi-K2.5 | Foundry (OpenAI-compat) | `Kimi-K2.5` | 250 | $1.40 | $2.80 | Reasoning | Live |
| claude-sonnet-4-6 | Foundry (AnthropicFoundry) | `claude-sonnet-4-6` | 250 | $3.00 | $15.00 | Instruction | Live |
| DeepSeek-R1 | Foundry (OpenAI-compat) | `DeepSeek-R1` | 5,000 | $1.35 | $5.40 | Reasoning, open | **Deploy now** |

**Shared key**: `FOUNDRY_API_KEY` in `.env`

Implementation notes:
- GPT-5.2: `reasoning_effort='none'`; rejects `temperature`; uses `max_completion_tokens`
- Kimi: `reasoning_effort='low'` via `extra_body`; without it all tokens consumed by CoT
- DeepSeek-R1: emits `<think>…</think>` blocks; `FoundryDeepSeekInterface` calls `_strip_thinking_tokens()` before the cascading decoder; thinking preserved in `metadata["thinking"]`
- All four: 19 Foundry integration tests in `tests/experiments/test_foundry_integration.py`

**Scientific structure (4-model primary design)**:

| Tier | Closed-source | Open-source |
|------|--------------|-------------|
| Reasoning | GPT-5.2, Kimi-K2.5 | DeepSeek-R1 |
| Instruction | Claude Sonnet 4.6 | — |

Research questions answered by this design:
1. Do reasoning models (GPT-5.2, Kimi, DeepSeek-R1) outperform instruction models (Claude) on defeasible abduction?
2. Does the closed-source advantage persist against an open-source reasoning model (DeepSeek-R1 vs GPT-5.2, Kimi)?
3. Does the CoT overthinking effect replicate across reasoning-optimized open-source models?

### Optional Extension — CURC Alpine (scaling subplot only)

These models are NOT available as Foundry serverless endpoints. Use CURC only if the within-family scaling comparison is needed for the paper.

| Model | HuggingFace ID | VRAM | Type |
|-------|----------------|------|------|
| Qwen 2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct-AWQ` | ~36 GB | Instruction |
| Qwen 2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct-AWQ` | ~16 GB | Scaling |

CURC env: `vllm-env` (set up by `curc-hoster/scripts/setup_environment.sh`)
HF cache: `/scratch/alpine/paco0228/hf_cache/`
Submit: `bash hpc/slurm_evaluate_curc_all.sh`

---

## Next Steps — Ordered by Priority

### 1. Deploy DeepSeek-R1 on Foundry (5 min, portal)

1. Go to [ai.azure.com](https://ai.azure.com) → open `LLM-Defeasible-Foundry`
2. Model catalog → search "DeepSeek-R1" → Deploy → Global Standard
3. Deployment name: `DeepSeek-R1`
4. Confirm endpoint matches `https://llm-defeasible-foundry.openai.azure.com/openai/v1/`
   If different, update `FoundryDeepSeekInterface.FOUNDRY_BASE_URL` in `experiments/model_interface.py`

### 2. Validate all four endpoints

```powershell
python experiments/validate_api_keys.py
```

Expected: all four `foundry-*` providers return OK.

### 3. Run integration tests

```powershell
python -m pytest tests/experiments/test_foundry_integration.py -m integration -v --no-cov
```

### 4. Submit full Foundry evaluation (all 4 models, all instances, all modalities)

From CURC login node (or locally — no GPU needed):

```bash
cd /projects/paco0228/blanc
git pull   # ensure latest code
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
```

Query budget: 409 instances × 4 models × 4 modalities × 2 strategies = **13,088 queries**
Estimated cost: GPT-5.2 ~$6, Claude ~$11, Kimi ~$4, DeepSeek-R1 ~$2 → **~$23 total**
Rate-limit bottleneck: Kimi and Claude at 250 RPM → ~13 min pure API time per model

Monitor:
```bash
squeue -u paco0228
tail -f logs/eval_foundry_<JID>.out
```

### 5. Submit clingo symbolic baseline (can run in parallel with Step 4)

```bash
pip install clingo
python experiments/symbolic_baseline.py --results-dir experiments/results/
```

### 6. (Optional) Submit CURC Qwen scaling jobs

Only if the within-family scaling comparison is needed:
```bash
bash hpc/slurm_evaluate_curc_all.sh   # Qwen 72B + Qwen 32B
```

### 7. Run all analysis scripts (after Step 4 completes)

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

---

## Code Changes Still Needed (do while evaluation runs)

| Task | File | Effort |
|------|------|--------|
| Add 95% Wilson CIs to all accuracy output | `experiments/analyze_results.py` | ~20 lines |
| Write dataset statistics LaTeX generator | `experiments/generate_dataset_table.py` | ~50 lines (new file) |
| Fix `\cite{openai2023gpt4}` → GPT-5.2 bib entry | `paper/references.bib`, `paper/paper.tex` line 399 | 5 min |
| Add LogicNLI citation (referenced without `\cite{}`) | `paper/references.bib`, `paper/paper.tex` | 5 min |
| Add `\section{Decoder Validation Results}\label{app:decoder}` appendix | `paper/paper.tex` | 15 min |
| Replace `David S. Hippocampus` author block | `paper/paper.tex` lines 125–154 | 2 min |

---

## Paper Sections — Fill After Evaluation

| Section | Needs | Source script |
|---------|-------|--------------|
| §4.3 Dataset Statistics table | Nothing (data exists now) | `generate_dataset_table.py` |
| §5.1 Tables 1–2 (expand to 4 models, 4 modalities) | Full eval | `generate_paper_tables.py` |
| §5.2 Grounding — domain table | Full eval | `analyze_results.py` |
| §5.3 Belief revision — error taxonomy table | Full eval | `error_taxonomy.py` |
| §5.3 Novelty / conservativity | Full eval | `novelty_analysis.py`, `conservativity_analysis.py` |
| §5.5 Scaling analysis | CURC Qwen (optional) | `scaling_analysis.py` |
| §5.6 Symbolic ceiling | clingo baseline | `symbolic_baseline.py` |
| §6 Discussion (expand to 4 models) | Full eval | Manual |
| Abstract (update numbers) | Full eval | Manual |

---

## Cost Summary

| Phase | Models | Queries | Est. cost |
|-------|--------|---------|-----------|
| Pilot (done) | GPT-5.2, Claude | ~640 | ~$2.55 |
| Full Foundry eval | GPT-5.2, Kimi, Claude, DeepSeek-R1 | ~13,088 | ~$23 |
| CURC Qwen (optional) | Qwen 72B, Qwen 32B | ~6,544 | $0 |
| **Total** | **4–6 models** | **~19,632** | **~$26** |

---

## Quick-Reference Commands

```powershell
# Validate all four Foundry endpoints
python experiments/validate_api_keys.py

# Run single model locally (default: 20 inst/domain)
.\hpc\run_local.ps1 foundry-deepseek
.\hpc\run_local.ps1 foundry   # all four sequentially

# Dry run (no API calls)
.\hpc\run_local.ps1 mock -InstanceLimit 5

# Live integration tests
python -m pytest tests/experiments/test_foundry_integration.py -m integration -v --no-cov
```

```bash
# CURC: full Foundry evaluation (4 models, all modalities)
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh

# CURC: Qwen scaling (optional)
bash hpc/slurm_evaluate_curc_all.sh

# Analysis (after results land)
python experiments/analyze_results.py --results-dir experiments/results/
python experiments/generate_paper_tables.py --results-dir experiments/results/
```
