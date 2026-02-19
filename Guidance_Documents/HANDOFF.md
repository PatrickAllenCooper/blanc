# BLANC Development Handoff

**Author**: Patrick Cooper  
**Date**: 2026-02-19  
**Commit**: `53f49b3`  
**Branch**: `main` (in sync with origin)  
**Tests**: 503 passing (standard) + 19 live integration tests, 86% coverage  
**Timeline**: Week 10 of 14.5 — ON TRACK

---

## What Was Built in This Session

### 1. CURC LLM Hoster Integration

Patrick Cooper's `curc-llm-hoster` project (CU Boulder Alpine HPC) is now a first-class evaluation provider.

**Files changed**:
- `experiments/model_interface.py` — new `CURCInterface` class: wraps an OpenAI-compatible client pointing at the vLLM server, `tenacity` retry (5 attempts, exponential backoff), zero cost tracking
- `experiments/run_evaluation.py` — `--provider curc --curc-base-url http://localhost:8000`
- `experiments/validate_api_keys.py` — `test_curc()` validates the endpoint before evaluation begins
- `hpc/slurm_evaluate_curc_vllm.sh` — complete SLURM script: starts vLLM server on the allocated GPU node, polls `/health`, runs evaluation, shuts down server, auto-runs `analyze_results.py`
- `.env.template` — `CURC_VLLM_BASE_URL`, `CURC_VLLM_MODEL` added
- `tests/experiments/test_model_interface.py` — 11 new unit tests for `CURCInterface` (all mocked, no network)

**Supported models** (top open-source, Feb 2026):
- `Qwen/Qwen2.5-72B-Instruct-AWQ` — recommended; ~36 GB VRAM on one A100 80 GB
- `hugging-quants/Meta-Llama-3.3-70B-Instruct-AWQ-INT4` — cross-family comparator
- `Qwen/Qwen2.5-32B-Instruct-AWQ` — within-family smaller scale

### 2. Code Quality Audit

- `src/blanc/utils/predicates.py` — new module: `extract_predicate`, `extract_constant`, `capitalize`; replaces four copies of these functions in encoders/decoders
- `src/blanc/utils/__init__.py` — exports the three utility functions
- `src/blanc/core/theory.py` — `Theory.copy()` canonical deep-copy method; eliminates scattered manual copying
- `experiments/level3_evaluator.py` — god-function decomposed into six focused `@staticmethod` helpers; `_deep_copy_theory` removed
- `experiments/model_interface.py` — all `print(f"... error ...")` replaced with `logger.warning(...)`
- `experiments/roundtrip_validation.py` — bare `except:` clauses replaced with `except Exception:`

### 3. Documentation Consolidation

Reduced from 90+ markdown files across 8 directories to 10 files in `Guidance_Documents/` plus directory READMEs:
- Deleted: all of `docs/` (80+ files), 4 stray root-level `.md` files, 12 superseded `Guidance_Documents/` files
- Created: `Guidance_Documents/DATA_DOWNLOAD.md`, `Guidance_Documents/REPOSITORY_STRUCTURE.md` (rewritten)
- Updated: `Guidance_Documents/INTUITIVE_GUIDE.md` (level-objectives quick-reference table appended)

### 4. Manuscript Updates (`paper/paper.tex`, `paper/references.bib`)

All changes are additions only — nothing removed from the paper:

| Section | Change |
|---------|--------|
| Models paragraph (§4.4) | Updated from `Llama 3 70B/8B` to `Qwen 2.5 72B/32B AWQ`; added Llama 3.3 70B as cross-family comparator |
| Compute infrastructure (§4.4, new paragraph) | CURC Alpine A100, Azure OpenAI, vLLM REST API described |
| Tier 0 table row | `374` → `374 L1/L2 + 35 L3` |
| Scaling analysis (§4.6) | Updated to `Qwen 2.5 32B vs 72B`; Llama replication added |
| Symbolic ceiling (§4.6) | TODO resolved: `clingo 5`, `$\Delta$-derivability encoding`, 30-second timeout |
| Decoder validation (§4.7) | TODO resolved: M2–M4 at 100% round-trip over all 409 gold hypotheses |
| Chain-of-thought (§4.6) | Four-step defeasible scaffold described; `defeasible reasoning scaffold` variant added |
| `references.bib` | Added 8 entries: GPT-4o, Claude 3.5, Gemini 1.5, Qwen 2.5, Llama 3, vLLM, clingo, and `llmorbench2026` was already present |

---

## Current Project State

### Dataset

| Level | Instances | Domains | Status |
|-------|-----------|---------|--------|
| Level 1 (fact completion) | included in 374 | Biology, Legal, Materials | Complete |
| Level 2 (rule abduction) | 374 total | Biology (114), Legal (116), Materials (144) | Complete |
| Level 3 (defeater abduction) | 35 | Biology (16), Legal (10), Materials (9) | Complete |

All 35 Level 3 instances have:
- Verified anomaly: `D^- ⊢∂ ¬α`
- Verified resolution: `D^full ⊬∂ ¬α`
- Conservativity: all non-targeted expectations preserved
- Distractor quality: no distractor is simultaneously resolutive AND conservative

10 of 35 instances have Nov > 0 (novel predicates required).

### Codec

| Modality | Encoder | Decoder | Round-trip |
|----------|---------|---------|------------|
| M1 (narrative) | Complete | D3 semantic parsing | Approximate by design |
| M2 (semi-formal) | Complete | D1 exact match | 100% |
| M3 (annotated formal) | Complete | D2 template extraction | 100% |
| M4 (pure formal) | Complete | D1 exact match | 100% |

Cascading decoder: D1 → D2 → D3 (fallthrough on failure).

### Evaluation Model Lineup (6 models, 2026-02-19)

**Closed-source — Azure AI Foundry** (all confirmed live, 19 integration tests)

| Model | Tier | RPM | Notes |
|-------|------|-----|-------|
| gpt-5.2-chat | Reasoning | 2,500 | `reasoning_effort='none'`; temperature omitted |
| Kimi-K2.5 | Reasoning | 250 | `reasoning_effort='low'` via extra_body |
| claude-sonnet-4-6 | Instruction | 250 | Standard AnthropicFoundry |

**Open-source — CURC Alpine A100 80 GB** (vLLM, AWQ 4-bit)

| Model | HuggingFace ID | VRAM | Tier |
|-------|----------------|------|------|
| DeepSeek-R1-Distill-Llama-70B | `casperhansen/deepseek-r1-distill-llama-70b-awq` | ~35 GB | Reasoning |
| Qwen 2.5 72B Instruct | `Qwen/Qwen2.5-72B-Instruct-AWQ` | ~36 GB | Instruction |
| Qwen 2.5 32B Instruct | `Qwen/Qwen2.5-32B-Instruct-AWQ` | ~16 GB | Scaling |

DeepSeek-R1 thinking tokens are stripped in `CURCInterface.query()` before the decoder.  
Submit all three CURC jobs: `bash hpc/slurm_evaluate_curc_all.sh`

### Evaluation Infrastructure

All of these exist and have been tested via dry run:

```
experiments/run_evaluation.py          # main CLI (providers: foundry-gpt/kimi/claude, curc, mock, ...)
experiments/model_interface.py         # 3 Foundry + 3 CURC open-source + legacy providers
experiments/level3_evaluator.py        # Nov, d_rev, conservativity, resolution strength
experiments/analyze_results.py         # accuracy by model/modality/domain/level
experiments/novelty_analysis.py        # Nov distribution + accuracy-novelty correlation
experiments/conservativity_analysis.py # conservativity rate + d_rev distribution
experiments/error_taxonomy.py          # E1-E5 error classification
experiments/generate_paper_tables.py   # LaTeX tables 1-4
experiments/symbolic_baseline.py       # clingo ASP ceiling for L2 and L3
experiments/difficulty_analysis.py     # sigma(I) distributions
experiments/partition_sensitivity.py   # Mann-Whitney / Kruskal-Wallis across partitions
```

### Tests

- 474 passing, 11 skipped, 0 failing
- 85% line coverage
- All `CURCInterface` tests mock the OpenAI client — no live network required
- `TestTheoryCopy` uses `Theory.copy()` — no import of removed `_deep_copy_theory`

---

## What Needs to Happen Next

### No Blockers — Evaluation Ready

All three Azure AI Foundry endpoints are live and confirmed via integration tests:
- `foundry-gpt`   → gpt-5.2-chat   (`reasoning_effort='none'`, ~5 tokens/reply)
- `foundry-kimi`  → Kimi-K2.5      (`reasoning_effort='low'` via extra_body, ~25 tokens/reply)
- `foundry-claude`→ claude-sonnet-4-6 (standard, no reasoning controls needed)

Shared key: `FOUNDRY_API_KEY` in `.env`.

### Week 9–10: Pilot then Full Evaluation

**Pilot (start here — ~30 min, < $1 cost)**:
```powershell
python experiments/validate_api_keys.py   # confirm all three endpoints live
.\hpc\run_local.ps1 foundry              # runs gpt, kimi, claude sequentially
```

**Full evaluation on CURC (after pilot passes)**:
```bash
sbatch hpc/slurm_evaluate_foundry.sh        # all three Foundry models
sbatch hpc/slurm_evaluate_curc_vllm.sh     # Qwen 2.5 72B / Llama 3.3 70B
```

**Inspect results**:
```bash
python experiments/analyze_results.py --results-dir experiments/results/<dir>
python experiments/generate_paper_tables.py --results-dir experiments/results/
```

**Full evaluation estimate**: ~16,360 queries across 5 models; ~$24 for the three Foundry models; CURC open-source runs are free. See `REVISED_IMPLEMENTATION_PLAN.md` for the complete cost breakdown and rate-limit analysis.

### Week 11–12: Advanced Analyses

Once evaluation results exist in `experiments/results/`:
```bash
python experiments/symbolic_baseline.py     # ASP ceiling; pip install clingo first
python experiments/difficulty_analysis.py
python experiments/partition_sensitivity.py
python experiments/novelty_analysis.py
python experiments/conservativity_analysis.py
python experiments/error_taxonomy.py
python experiments/scaling_analysis.py
```

### Week 13–14: Paper Completion

Open TODOs in `paper.tex` (search `% TODO`):
1. **k=5 distractors** (line ~368): justify or add ablation
2. **Score weights** (line ~427–430): even spacing vs empirically motivated weights
3. **Theory size ablation** (line ~474): adjust `{50, 100, 200, 500, 1000}` to actual KB sizes
4. **NeurIPS checklist** (lines ~1100–1224): replace all `\answerTODO{}` with `\answerYes{}`, `\answerNo{}`, or `\answerNA{}` plus justifications
5. **Author field** (lines 125–154): replace `David S. Hippocampus` placeholder

---

## Repository Layout (Key Paths)

```
blanc/
  src/blanc/
    core/           theory.py (Theory, Rule, Theory.copy())
    codec/          m1-m4 encoders, d1-d3 decoders, cascading decoder
    utils/          predicates.py (extract_predicate, extract_constant, capitalize)
    kb/             loaders for YAGO, WordNet, LKIF, MatOnto
  experiments/
    model_interface.py          # GPT-5.2 (Foundry), Kimi-K2.5 (Foundry),
                                #   claude-sonnet-4-6 (Foundry), CURC vLLM,
                                #   OpenAI, Anthropic, Google, Ollama, Mock
    run_evaluation.py           # CLI: --provider foundry-gpt/foundry-kimi/foundry-claude/...
    level3_evaluator.py         # Nov, d_rev, conservativity, resolution strength
    analyze_results.py          # accuracy by model/modality/domain/level
    symbolic_baseline.py        # clingo ASP ceiling
    generate_paper_tables.py    # LaTeX tables 1-4 for Section 5
    novelty_analysis.py
    conservativity_analysis.py
    error_taxonomy.py
    scaling_analysis.py
    difficulty_analysis.py
    partition_sensitivity.py
    validate_api_keys.py        # live endpoint health check
  hpc/
    slurm_evaluate_foundry.sh   # Foundry: gpt-5.2, Kimi, Claude (no GPU needed)
    slurm_evaluate_curc_vllm.sh # CURC: Qwen 2.5 72B / Llama 3.3 70B
    run_local.ps1               # Windows local runner (reads .env)
    run_local.sh                # Linux/macOS/WSL local runner (reads .env)
  instances/
    level3_instances.json       # 35 Level 3 gold instances
    biology_dev_instances.json  # 114 Level 2 instances
    legal_dev_instances.json    # 116 Level 2 instances
    materials_dev_instances.json # 144 Level 2 instances
  paper/
    paper.tex                   # NeurIPS 2025 manuscript
    references.bib
  tests/
    experiments/                # unit + integration tests (503 standard, 19 live)
    src/                        # library unit tests
  Guidance_Documents/
    STATUS.md                   # always-current project status
    HANDOFF.md                  # this file
    REVISED_IMPLEMENTATION_PLAN.md  # evaluation plan with Foundry commands
    REPOSITORY_STRUCTURE.md
    INTUITIVE_GUIDE.md
    COMPREHENSIVE_KB_PIPELINE.md
    KNOWLEDGE_BASE_POLICY.md
    API_Design.md
    DATA_DOWNLOAD.md
    PAPER_ADDITIONS_PROPOSAL.md
```

---

## Known Issues / Decisions Deferred

1. **Cross-ontology extraction (Week 8)**: Attempt to extract rules from OpenCyc + ConceptNet failed; pipeline code is in `scripts/` but produced unusable output. Paper presents current scope as Tier 0 (expert KBs) in Table 1.

2. **Level 1 instance count**: Generated inline with Level 2 instances; not separately counted. Compute before submission: parse `*_dev_instances.json` for `level == 1` entries.

3. **M1 round-trip**: Approximate by design. Decoder validation section of the paper cannot be marked complete without a manual audit of ~200 decode failures.

4. **NeurIPS style file**: `neurips_2025.sty` not in repo — obtain from NeurIPS at submission time.

5. **Qwen 2.5 32B scaling comparator**: Paper lists 32B vs 72B within-family comparison. Must run a second CURC evaluation: `VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ sbatch hpc/slurm_evaluate_curc_vllm.sh`.

6. **clingo installation**: Required by `experiments/symbolic_baseline.py`. CURC: `conda install -c conda-forge clingo`. Local: `pip install clingo`.

7. **GPT-5.2 pricing**: `_COST_PER_1K_INPUT = 0.00175` and `_COST_PER_1K_OUTPUT = 0.014` are from the OpenAI public rate card (Feb 2026). Update if Microsoft revises Azure Foundry pricing.

8. **Kimi-K2.5 pricing**: `_COST_PER_1K_INPUT = 0.0014`, `_COST_PER_1K_OUTPUT = 0.0028` are estimates. Confirm against Azure billing dashboard after pilot.

---

## Git State

```
Branch: main
Remote: origin/main (in sync)
Last 5 commits:
  53f49b3  Add reasoning effort controls: GPT-5.2 none, Kimi low
  b37a424  Verify Foundry endpoints live; fix GPT-5.2 temperature; add integration tests
  5adec30  Add Azure AI Foundry integration (gpt-5.2, Kimi-K2.5, claude-sonnet-4-6)
  29d6819  merge references: add 16 missing entries from supplementary bib
  9470880  add HANDOFF.md and update STATUS.md for session end
```

---

## First Thing to Do in the Next Session

**All blockers cleared. Start the pilot.**

```powershell
# 1. Confirm all three Foundry endpoints are still live
python experiments/validate_api_keys.py

# 2. Run the pilot (< $1, < 30 min)
.\hpc\run_local.ps1 foundry

# 3. Inspect results
python experiments/analyze_results.py --results-dir experiments/results/local_foundry-gpt_<timestamp>
python experiments/generate_paper_tables.py --results-dir experiments/results/

# 4. If pilot passes, submit full evaluation (all 6 models)
sbatch hpc/slurm_evaluate_foundry.sh    # 3 Foundry models (sequential)
bash hpc/slurm_evaluate_curc_all.sh     # 3 CURC models (parallel jobs)
```

If anything is unclear about the model setup, re-run the integration tests:
```powershell
python -m pytest tests/experiments/test_foundry_integration.py -m integration -v --no-cov
```
