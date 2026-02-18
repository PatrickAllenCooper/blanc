# Project Status

**Last Updated**: 2026-02-18  
**Current**: CURC integration complete; documentation consolidated; manuscript updated; ready for live evaluation  
**Progress**: 9.5 of 14.5 weeks (65%)  
**Timeline**: ON TRACK

---

## Quick Summary

**Weeks Complete**: 9.5 of 14.5  
**Tests**: 474 passing ✅  
**Coverage**: 85% ✅  
**Expert KBs**: 2,318 rules ✅  
**Instances**: 374 Level 2 + 35 Level 3 (all validated)  
**Codec**: ALL 4 modalities + 3 decoders, 100% round-trip (M2-M4) ✅  
**Pipeline**: dry run passing with MockModelInterface + Level3Evaluator ✅  
**Level 3 Generation**: COMPLETE - 35 instances, 10 with Nov > 0  
**Analysis scripts**: COMPLETE - all paper Section 5 analysis ready

---

## Completed Weeks

- **Week 1-2**: Expert KB foundation (2,318 rules)
- **Week 3**: Instance generation (374 Level 2 instances)
- **Week 4**: Statistical analysis (Section 4.3)
- **Week 5**: M2, M3, D2 codec
- **Week 6**: M1, D3, Cascading decoder
- **Week 7**: Validation + testing infrastructure
- **Week 8**: Cross-ontology proof-of-concept (failed; documented)
- **Week 8.5a**: Phase 2B - Manual Level 3 generation (33 instances)
- **Week 8.5b**: Pre-evaluation preparation
  - AzureOpenAIInterface added to `experiments/model_interface.py`
  - Full pipeline dry run (`scripts/dry_run_pipeline.py`) passing
  - SLURM evaluation scripts: `hpc/slurm_evaluate_azure.sh`, `hpc/slurm_evaluate_llama.sh`
  - `experiments/run_evaluation.py` CLI with all provider support
  - Related Work (Section 2) expanded: LLM-ASPIC+ (ECAI 2025), LogiDynamics (EMNLP 2025)
  - Pipeline bug fixed: `EvaluationPipeline` now routes through `CascadingDecoder` (D1→D2→D3)
  - Prompting bug fixed: M4 candidate encoding no longer attempts to re-encode formal strings
- **Week 9 preparation**: All analysis scripts written and tested (no cloud needed)
  - `experiments/level3_evaluator.py`: parses model responses, computes Nov/conservativity/d_rev
  - `experiments/validate_decoder_pipeline.py`: confirmed 100% round-trip M2-M4
  - `experiments/analyze_results.py`: accuracy by model/modality/domain/level
  - `experiments/novelty_analysis.py`: Nov distribution + accuracy-novelty correlation
  - `experiments/conservativity_analysis.py`: conservativity rate + d_rev distribution
  - `experiments/error_taxonomy.py`: E1-E5 error classification
  - `experiments/generate_paper_tables.py`: LaTeX tables 1-4 for Section 5
  - `experiments/symbolic_baseline.py`: ASP ceiling evaluation for Levels 2 and 3
  - `experiments/difficulty_analysis.py`: rewritten with correct sigma(I) extraction
  - `experiments/partition_sensitivity.py`: rewritten with real Mann-Whitney/KW tests
  - Azure OpenAI added to `experiments/validate_api_keys.py` and `.env.template`
- **CURC LLM Hoster integration** (2026-02-18):
  - `CURCInterface` added to `experiments/model_interface.py`: OpenAI-compatible client
    pointed at the vLLM server (Patrick Cooper's CURC LLM Hoster project). Uses
    `openai.OpenAI(base_url=..., api_key="not-needed")` with retry logic.
  - Supported models: Qwen 2.5 72B AWQ (recommended), Llama 3.3 70B AWQ-INT4,
    Qwen 2.5 32B AWQ, Llama 3.1 70B AWQ-INT4.
  - `--provider curc --curc-base-url http://localhost:8000` added to `run_evaluation.py`.
  - `hpc/slurm_evaluate_curc_vllm.sh`: replaces Ollama-based SLURM script.
    Starts the vLLM server (tensor-parallel across all node GPUs), waits for the
    /health endpoint, runs evaluation, shuts down server. Automatically runs
    `analyze_results.py` on completion.
  - `test_curc()` added to `validate_api_keys.py`; CURC counted as a valid
    provider for pilot readiness.
  - `.env.template` updated with `CURC_VLLM_BASE_URL` and `CURC_VLLM_MODEL`.
  - 11 new unit tests for `CURCInterface` in `tests/experiments/test_model_interface.py`
    using mocked OpenAI client (no network required).

**ALL INFRASTRUCTURE COMPLETE**  
**LEVEL 3 INSTANCES COMPLETE**  
**EVALUATION PIPELINE READY**  
**ANALYSIS INFRASTRUCTURE COMPLETE**  
**CURC LLM HOSTER INTEGRATION COMPLETE**  
**MANUSCRIPT UPDATED (2026-02-18)**

### Manuscript updates (2026-02-18)

All additions to `paper/paper.tex`; nothing removed:

- Models paragraph: `Llama 3 70B/8B` replaced by `Qwen 2.5 72B/32B AWQ` (CURC top model);
  Llama 3.3 70B added as cross-family comparator; TODO removed
- New paragraph: compute infrastructure (CURC Alpine A100, Azure OpenAI, vLLM REST API)
- Tier 0 table row: `374` updated to `374 L1/L2 + 35 L3`
- Scaling analysis: updated to Qwen 2.5 32B vs 72B with Llama cross-family replication
- Symbolic ceiling TODO resolved: clingo 5, $\Delta$-derivability encoding, 30s timeout
- Decoder validation TODO resolved: M2-M4 at 100% round-trip over all 409 gold hypotheses
- Chain-of-thought TODO replaced: full four-step defeasible scaffold described
- `references.bib`: added 8 new entries (GPT-4o, Claude, Gemini, Qwen 2.5, Llama 3, vLLM, clingo)

### Documentation consolidation (2026-02-18)

Reduced from 90+ markdown files across 8 directories to 10 files in
`Guidance_Documents/` plus directory READMEs. All historical session
artefacts (Phase_* summaries, CONTINUE_DEVELOPMENT, CROSS_ONTOLOGY_PLAN,
completed_weeks/, session_reports/, week3_docs/, planning/, audits/,
and root-level stray files) deleted. Unique content merged:

- Level-objectives quick-reference table added to `INTUITIVE_GUIDE.md`
- `DATA_DOWNLOAD.md` created from `docs/DATA_DOWNLOAD_INSTRUCTIONS.md`
- `REPOSITORY_STRUCTURE.md` rewritten from scratch to reflect current state
- Cross-ontology failure already captured in STATUS.md (Week 8.5a entry)

---

## Phase 2B Results (2026-02-18)

**Script**: `scripts/generate_level3_manual.py`  
**Output**: `instances/level3_instances.json`

| Domain | Instances | Nov > 0 | Valid |
|--------|-----------|---------|-------|
| Biology | 16 | 4 | 16/16 |
| Legal | 10 | 2 | 10/10 |
| Materials | 9 | 4 | 9/9 |
| **Total** | **35** | **10** | **35/35** |

**Verified properties for each instance**:
- D^- ⊢∂ anomaly (anomaly is defeasibly provable in challenge theory)
- D^full ⊬∂ anomaly (gold defeater resolves the anomaly)
- Conservativity: all preserved expectations hold after defeater is added
- Distractor quality: no distractor is simultaneously resolutive AND conservative

**Two-entity pattern** used for all Nov > 0 instances: two entities of the same
species/type appear in D^-, where only one has the novel property (in the gold
`novel_facts`). This ensures the "no-novel" distractor is non-conservative
(it would incorrectly block the second entity), while the gold is conservative
(targets only the entity with the novel property).

---

## Next: LLM Evaluation (Weeks 9-10)

**Immediate blockers**: Azure API credentials, CURC provisioning (in progress)

**Pipeline is ready to run**:
- Submit `sbatch hpc/slurm_evaluate_azure.sh` once Azure credentials are provisioned
- Submit `sbatch hpc/slurm_evaluate_llama.sh` once CURC allocation is active
- Or run locally: `python experiments/run_evaluation.py --provider openai ...`

---

## Remaining Work: ~6 Weeks

- Weeks 9-10: LLM evaluation (Azure + CURC)
- Weeks 11-12: Advanced analyses (rendering robustness, difficulty curves)
- Weeks 13-14: HPC production + paper submission

---

**For details**: See `Guidance_Documents/CURRENT_STATUS_AND_PLAN.md`  
**For roadmap**: See `Guidance_Documents/NEURIPS_FULL_ROADMAP.md`
