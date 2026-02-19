# Implementation Plan: LLM Evaluation to Submission

**Date**: 2026-02-19  
**Author**: Patrick Cooper  
**Status**: Weeks 1-10 of 14.5 complete (69%). LLM evaluation unblocked.  
**Next action**: Run pilot evaluation against Foundry endpoints.

---

## Where We Are

### Completed (Weeks 1–10)

| Phase | Deliverable | Status |
|-------|-------------|--------|
| 1–2 | Expert KB foundation — 2,318 rules (YAGO, WordNet, LKIF, MatOnto) | Done |
| 3 | Instance generation — 374 Level 2 instances | Done |
| 4 | Statistical analysis (Section 4.3) | Done |
| 5–6 | Full codec: M1–M4 encoders, D1–D3 decoders, cascading decoder | Done |
| 7 | Validation and testing infrastructure (503 tests, 86% coverage) | Done |
| 8 | Evaluation infrastructure (pipeline, prompting, response cache) | Done |
| 8.5a | Level 3 instance generation — 35 defeater instances | Done |
| 8.5b | Pre-evaluation preparation (all analysis scripts written) | Done |
| 9 | Azure AI Foundry integration — three closed-source models live | Done |

### Dataset

| Level | Count | Domains | Notes |
|-------|-------|---------|-------|
| Level 2 (rule abduction) | 374 | Biology 114, Legal 116, Materials 144 | Complete |
| Level 3 (defeater abduction) | 35 | Biology 16, Legal 10, Materials 9 | Complete; 10 with Nov > 0 |

### Evaluation Model Lineup (finalised 2026-02-19)

**Six models total**: 3 closed-source (Foundry, confirmed live) + 3 open-source (CURC).

#### Closed-source — Azure AI Foundry

| Model | HF / Deployment | RPM | Cost/1M in | Cost/1M out | Type |
|-------|-----------------|-----|------------|-------------|------|
| gpt-5.2-chat | `gpt-5.2-chat` | 2,500 | $1.75 | $14.00 | Reasoning |
| Kimi-K2.5 | `Kimi-K2.5` | 250 | $1.40 | $2.80 | Reasoning |
| claude-sonnet-4-6 | `claude-sonnet-4-6` | 250 | $3.00 | $15.00 | Instruction |

- Shared key: `FOUNDRY_API_KEY` in `.env`
- GPT-5.2 rejects `temperature`; silently omitted. Uses `max_completion_tokens`.
- GPT-5.2 `reasoning_effort='none'` (default) disables internal CoT entirely.
- Kimi `reasoning_effort='low'` via `extra_body` required; without it all tokens go to reasoning and response text is empty.
- All three confirmed live via 19 integration tests in `tests/experiments/test_foundry_integration.py`.

#### Open-source — CURC Alpine (A100 80 GB, vLLM AWQ)

| Model | HuggingFace ID | VRAM | License | Type |
|-------|----------------|------|---------|------|
| DeepSeek-R1-Distill-Llama-70B | `casperhansen/deepseek-r1-distill-llama-70b-awq` | ~35 GB | MIT | Reasoning |
| Qwen 2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct-AWQ` | ~36 GB | Apache 2.0 | Instruction |
| Qwen 2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct-AWQ` | ~16 GB | Apache 2.0 | Scaling |

- DeepSeek-R1-Distill emits `<think>...</think>` blocks; `CURCInterface` strips them before the cascading decoder sees the response. Thinking content is preserved in `metadata["thinking"]` for analysis.
- All three fit on a single A100 80 GB GPU.

#### Scientific structure and paper narrative

| Tier | Closed-source | Open-source |
|------|--------------|-------------|
| Reasoning | GPT-5.2, Kimi-K2.5 | DeepSeek-R1-Distill-70B |
| Instruction | Claude Sonnet 4.6 | Qwen 2.5 72B |
| Scaling | — | Qwen 2.5 32B (vs 72B) |

**Key research questions enabled by this design**:
1. Do reasoning models (GPT-5.2, Kimi, DeepSeek-R1) outperform instruction models on defeasible tasks?
2. Does the closed-source advantage persist (GPT-5.2 vs DeepSeek-R1, Claude vs Qwen 72B)?
3. Does scale matter within a family (Qwen 32B vs 72B)?
4. Does reasoning distillation preserve capability (DeepSeek-R1-Distill vs full reasoning models)?

---

## Remaining Work

### Week 9–10: LLM Pilot then Full Evaluation

#### Step 1 — Pilot (run immediately, ~1 hour)

Purpose: confirm end-to-end pipeline against real models before committing to full run.

```powershell
# Validate all three endpoints are reachable
python experiments/validate_api_keys.py

# Pilot: 20 instances/domain, M4 + M2, direct + cot, all three Foundry models
.\hpc\run_local.ps1 foundry-gpt   # ~5 min, ~$0.05
.\hpc\run_local.ps1 foundry-kimi  # ~15 min (250 RPM limit), ~$0.02
.\hpc\run_local.ps1 foundry-claude # ~10 min, ~$0.09

# Or run all three sequentially
.\hpc\run_local.ps1 foundry
```

Default pilot parameters (`hpc/run_local.ps1`):
- `INSTANCE_LIMIT = 20` per domain (60 L2 instances total)
- `LEVEL3_LIMIT = 20`
- `MODALITIES = M4 M2`
- `STRATEGIES = direct cot`

Pilot query budget: 60 L2 + 20 L3 = 80 instances × 3 models × 2 modalities × 2 strategies = **960 queries**  
Estimated cost: < $1.00 total across all three Foundry models.

**Go / No-Go criteria**:
- Pipeline produces `results_*.json` files with non-null accuracy fields
- Decoder distribution is sensible (not 100% FAILED)
- No systematic API errors (rate limit, auth, encoding)

#### Step 2 — Inspect pilot results

```powershell
python experiments/analyze_results.py --results-dir experiments/results/local_foundry-gpt_<timestamp>
python experiments/generate_paper_tables.py --results-dir experiments/results/
```

#### Step 3 — Full evaluation (all instances, all modalities)

Once pilot passes, scale up via SLURM (no rate-limit pressure from local machine):

```bash
# All three Foundry models (sequentially in one SLURM job)
sbatch hpc/slurm_evaluate_foundry.sh

# All three CURC open-source models (three parallel SLURM jobs)
bash hpc/slurm_evaluate_curc_all.sh

# Or individual CURC models:
sbatch hpc/slurm_evaluate_curc_vllm.sh   # default: DeepSeek-R1-Distill-70B
sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ \
       hpc/slurm_evaluate_curc_vllm.sh
sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ,INSTANCE_LIMIT=120 \
       hpc/slurm_evaluate_curc_vllm.sh
```

Override Foundry for full scale:
```bash
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
```

Full evaluation query budget (6 models):
- 374 L2 + 35 L3 = 409 instances × 6 models × 4 modalities × 2 strategies = **19,632 queries**
- Foundry cost: GPT-5.2 ~$8, Claude ~$12, Kimi ~$4 → **~$24 total**
- CURC (3 models): $0 (cluster allocation)

**Rate limit bottleneck**: Kimi and Claude are capped at 250 RPM.
At 409 instances × 4 modalities × 2 strategies = 3,272 queries per model:
- 3,272 / 250 RPM = ~13 minutes of pure API time at cap
- Real wall time with overhead: ~30–60 min per Foundry model

CURC models run on GPU with no rate-limit ceiling — wall time is inference speed only (~2–4 hours per model for the full set).

`RateLimiter` in `model_interface.py` handles Foundry throttling automatically.

---

### Week 11–12: Advanced Analyses

Run once pilot results exist in `experiments/results/`:

```bash
# ASP ceiling (requires clingo; pip install clingo or conda install -c conda-forge clingo)
python experiments/symbolic_baseline.py --results-dir experiments/results/

# Difficulty stratification
python experiments/difficulty_analysis.py --results-dir experiments/results/

# Partition sensitivity (Mann-Whitney / Kruskal-Wallis)
python experiments/partition_sensitivity.py --results-dir experiments/results/

# Novelty vs accuracy correlation (Level 3 only)
python experiments/novelty_analysis.py --results-dir experiments/results/

# Conservativity rate and d_rev distribution (Level 3 only)
python experiments/conservativity_analysis.py --results-dir experiments/results/

# E1-E5 error classification per model
python experiments/error_taxonomy.py --results-dir experiments/results/

# Scaling curves: Qwen 32B vs 72B, Llama family
python experiments/scaling_analysis.py --results-dir experiments/results/
```

Deliverables: figures and LaTeX snippets for Section 5 of the paper.

---

### Week 13–14: Paper Completion and Submission

#### Open TODOs in `paper/paper.tex` (search `% TODO`)

| Location | Issue |
|----------|-------|
| Line ~368 | k=5 distractors: justify choice or add ablation |
| Line ~427–430 | Score weights: even spacing or empirically motivated? Consider reporting under multiple schemes |
| Line ~474 | Theory size ablation values `{50, 100, 200, 500, 1000}` — adjust to actual KB sizes |
| Line ~1100–1224 | NeurIPS checklist: all `\answerTODO{}` → `\answerYes{}`, `\answerNo{}`, or `\answerNA{}` with justification |
| Line ~125–154 | Author field: replace `David S. Hippocampus` placeholder |

#### Results section (Section 5) — fill in after evaluation

1. **Grounding (Level 1–2)**: accuracy by model / modality / domain, decoder stage distribution, error taxonomy.
2. **Novelty (Level 3, Nov > 0)**: can models generate hypotheses with novel predicates? Distribution of Nov(h, D). Accuracy vs novelty correlation.
3. **Belief revision (Level 3, conservativity)**: conservativity rate by model, d_rev distribution, minimal-change adherence vs random distractor baseline.

#### Symbolic ceiling baseline

The symbolic ASP solver (`experiments/symbolic_baseline.py`) provides the ceiling for Level 2 and Level 3.  
Requires `clingo` installed: `pip install clingo`.

#### HPC production run (optional but strengthens submission)

Scale from development set (409 instances) to production set:
- Level 2: increase `--instance-limit` to 120 (full KB coverage)
- Level 3: increase `--level3-limit` to 35 (all instances)

```bash
# Production run — full instance set, all modalities
sbatch --export=ALL,INSTANCE_LIMIT=120,LEVEL3_LIMIT=35,MODALITIES="M4 M2 M1 M3" \
       hpc/slurm_evaluate_foundry.sh
```

---

## Known Issues to Resolve Before Submission

| Issue | Impact | Resolution |
|-------|--------|------------|
| Level 1 instance count not separately reported | Dataset statistics table incomplete | Run `scripts/count_level1.py` or extract from existing JSON |
| M1 round-trip is approximate by design | Decoder validation for M1 section of paper | Manual audit of 200 decode failures; report qualitatively |
| Qwen 2.5 32B not yet evaluated | Within-family scaling comparison incomplete | Add second CURC run: `VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ sbatch hpc/slurm_evaluate_curc_vllm.sh` |
| NeurIPS style file not in repo | Paper does not compile locally | Obtain `neurips_2025.sty` from NeurIPS at submission time |
| GPT-5.2 pricing approximate | Cost estimates may be off | Update `_COST_PER_1K_*` in `FoundryGPT52Interface` once Azure publishes rates |

---

## Cost Summary

| Evaluation phase | Models | Est. queries | Est. cost |
|-----------------|--------|-------------|-----------|
| Pilot (local, 20 inst/domain) | 3 Foundry | ~960 | < $1 |
| Full Foundry evaluation | GPT-5.2, Kimi, Claude | ~9,816 | ~$24 |
| CURC open-source models | DeepSeek-R1, Qwen 72B, Qwen 32B | ~9,816 | $0 |
| **Total** | **6 models** | **~19,632** | **~$25** |

This is substantially below the original $150–200 estimate because:
1. GPT-5.2 with `reasoning_effort='none'` uses far fewer completion tokens than GPT-4o.
2. Kimi-K2.5 is cost-competitive with GPT-3.5-level pricing.
3. All three CURC models run on cluster allocation — no API cost.

---

## Quick-Reference Commands

```powershell
# Validate endpoints
python experiments/validate_api_keys.py

# Pilot (local, default 20 inst/domain)
.\hpc\run_local.ps1 foundry

# Individual models
.\hpc\run_local.ps1 foundry-gpt
.\hpc\run_local.ps1 foundry-kimi
.\hpc\run_local.ps1 foundry-claude

# Dry run (no API calls)
.\hpc\run_local.ps1 mock -InstanceLimit 5

# Inspect results
python experiments/analyze_results.py --results-dir experiments/results/<dir>
python experiments/generate_paper_tables.py --results-dir experiments/results/

# Live integration tests (confirms endpoints are up)
python -m pytest tests/experiments/test_foundry_integration.py -m integration -v --no-cov
```

```bash
# CURC / HPC — Foundry (all 3 models, 1 job)
sbatch hpc/slurm_evaluate_foundry.sh

# CURC / HPC — Open-source (all 3 models, 3 parallel jobs)
bash hpc/slurm_evaluate_curc_all.sh

# CURC / HPC — Single open-source model
sbatch hpc/slurm_evaluate_curc_vllm.sh   # default: DeepSeek-R1-Distill-70B
sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ hpc/slurm_evaluate_curc_vllm.sh
sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ hpc/slurm_evaluate_curc_vllm.sh
```
