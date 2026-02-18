# BLANC Development Handoff

**Author**: Patrick Cooper  
**Date**: 2026-02-18  
**Commit**: `133dd86`  
**Branch**: `main` (ahead of origin: pushed)  
**Tests**: 474 passing, 11 skipped, 85% coverage  
**Timeline**: Week 9.5 of 14.5 — ON TRACK

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

### Evaluation Infrastructure

All of these exist and have been tested via dry run:

```
experiments/run_evaluation.py          # main CLI
experiments/model_interface.py         # GPT-4o, Claude, Gemini, CURC, Azure, Ollama
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

### Immediate Blockers

1. **Azure OpenAI credentials**: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT` must be set in `.env` before the closed-source evaluation can run.
2. **CURC provisioning**: Alpine allocation must be active. The CURC LLM Hoster project must be set up on the cluster per its own README.

### Week 9–10: LLM Pilot Evaluation

**To run against Azure (GPT-4o)**:
```bash
# On CURC login node or local machine with Azure creds in .env
sbatch hpc/slurm_evaluate_azure.sh
# or locally:
python experiments/run_evaluation.py \
  --provider azure \
  --dataset instances/level3_instances.json \
  --output results/pilot_azure.json \
  --max-instances 50
```

**To run against CURC vLLM (Qwen 2.5 72B)**:
```bash
sbatch hpc/slurm_evaluate_curc_vllm.sh
```
This script handles the full lifecycle: starts vLLM, waits for health, runs evaluation, shuts down, runs `analyze_results.py`.

**Expected outputs**:
- `results/pilot_*.json` — raw model responses
- `results/analysis/` — tables from `analyze_results.py`
- `results/tables/` — LaTeX from `generate_paper_tables.py`

### Week 11–12: Advanced Analyses

Once pilot results exist, run:
```bash
python experiments/symbolic_baseline.py     # ASP ceiling; needs clingo installed
python experiments/difficulty_analysis.py   # sigma(I) structural distributions
python experiments/partition_sensitivity.py # partition family comparison
python experiments/novelty_analysis.py      # Nov vs accuracy scatter
python experiments/conservativity_analysis.py
python experiments/error_taxonomy.py        # E1-E5 distribution per model
```

### Week 13–14: Paper Completion

Open TODOs in `paper.tex` (search for `% TODO`):
1. **k=5 distractors** (line ~368): justify or add ablation
2. **Score weights** (line ~427–430): decide if even spacing is appropriate or if gaps should be uneven; consider reporting results under multiple weighting schemes
3. **Theory size ablation** (line ~474): values `{50, 100, 200, 500, 1000}` are preliminary — adjust to actual grounded KB sizes
4. **NeurIPS checklist** (lines ~1100–1224): all `\answerTODO{}` entries need to be replaced with `\answerYes{}`, `\answerNo{}`, or `\answerNA{}` plus justifications
5. **Author field** (lines 125–154): still shows the NeurIPS template placeholder (`David S. Hippocampus`)

---

## Repository Layout (Key Paths)

```
blanc/
  src/blanc/
    core/           theory.py (Theory, Rule, Theory.copy())
    codec/          m1-m3 encoders, d2-d3 decoders
    utils/          predicates.py (extract_predicate, extract_constant, capitalize)
    kb/             loaders for YAGO, WordNet, LKIF, MatOnto
  experiments/
    model_interface.py     # all provider interfaces inc. CURCInterface
    run_evaluation.py      # CLI entry point
    level3_evaluator.py    # Level 3 scoring logic
    analyze_results.py     # primary analysis
    symbolic_baseline.py   # clingo ASP baseline
    generate_paper_tables.py
  hpc/
    slurm_evaluate_azure.sh
    slurm_evaluate_curc_vllm.sh
  instances/
    level3_instances.json  # 35 Level 3 gold instances
  paper/
    paper.tex              # NeurIPS 2025 manuscript
    references.bib         # 470 lines, all cited references present
  tests/
    experiments/           # unit tests for all experiment scripts
    src/                   # unit tests for library code
  Guidance_Documents/
    STATUS.md              # always-current project status
    HANDOFF.md             # this file
    REVISED_IMPLEMENTATION_PLAN.md
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

1. **Cross-ontology extraction (Week 8)**: The attempt to extract rules from OpenCyc + ConceptNet failed. The pipeline code is in `scripts/` but produced unusable output. All paper references to this as "Tier 1" are presented as roadmap, not current results. The paper clearly frames current scope as Tier 0 (expert KBs) in Table 1.

2. **Level 1 instance count**: Not separately reported in STATUS (they are generated inline with Level 2 from the same theories). Before paper submission, a precise Level 1 count should be computed and added to the dataset statistics table.

3. **M1 round-trip recovery**: Narrative modality round-trip is approximate by design. A manual audit of 200 decode failures is required before the decoder validation section of the paper can be marked complete.

4. **NeurIPS style file**: `neurips_2025.sty` is not in the repo (expected — obtained from NeurIPS at submission time). The paper does not compile locally without it.

5. **Qwen 2.5 32B**: Listed as a within-family comparator in the paper but `CURCInterface` defaults to 72B. At evaluation time, a second evaluation run must be configured with `VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ`.

6. **clingo installation**: `experiments/symbolic_baseline.py` requires `clingo` to be installed. On CURC: `conda install -c conda-forge clingo`. Locally: `pip install clingo`.

---

## Git State

```
Branch: main
Remote: origin/main (in sync after last push)
Last 5 commits:
  133dd86  update manuscript to reflect implemented evaluation infrastructure
  5f0771f  Consolidate docs: 90+ stale files -> 10 active Guidance_Documents
  48d2462  Code quality: eliminate duplication, fix anti-patterns, decompose god-function
  024c465  Add CURC LLM Hoster integration (CURCInterface, vLLM SLURM script)
  fdfc5c1  store theory_size/level/domain in SingleEvaluation for scaling analysis
```

---

## First Thing to Do in the Next Session

1. Run `python experiments/validate_api_keys.py` to confirm which providers are live.
2. If Azure is ready: `sbatch hpc/slurm_evaluate_azure.sh` (or run locally with `--max-instances 50` for a pilot).
3. If CURC is ready: `sbatch hpc/slurm_evaluate_curc_vllm.sh`.
4. Once results exist in `results/`, run `python experiments/analyze_results.py --results results/pilot_*.json`.
5. Run `python experiments/generate_paper_tables.py` to generate draft LaTeX tables for Section 5.
