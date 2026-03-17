# Project Status

**Last Updated**: 2026-03-17
**Current**: Phase A (Foundry evaluation) COMPLETE. Phase B (finetuning) NOT STARTED -- blocked on CURC. Phase C (adversarial debate) COMPLETE. Multi-tier KB extraction COMPLETE: 4.23M rules from 7 sources (YAGO, OpenCyc+ConceptNet, SUMO, Gene Ontology, MeSH, FrameNet, Wikidata).
**Progress**: 12 of 14 weeks (86% -- infrastructure, base evaluation, debate, multi-tier dataset done; finetuning pending)
**Timeline**: TIGHT -- B1 must resume; multi-million rule dataset ready

---

## Quick Summary

**Tests**: 947+ passing (63 new debate/search tests) + new ontology/behavioral/integration tests
**Expert KBs (Tier 0)**: 2,318 strict taxonomic rules + 482 defeasible behavioral rules + 244 defeaters + 55 superiority relations + 70 multi-body compound rules across 3 domains (3,044 total rules)
**Tier 0 Instances**: 374 Level 2 + 35 Level 3 (all validated)
**Tier 1 Rules**: 290,576 cross-ontology rules (125.4x Tier 0) across 5 domains from OpenCyc + ConceptNet
**Tier 1 Instances**: 313,314 total (176,982 L1 + 136,332 L2) across 4 domains (766x multiplier)
**Multi-Tier Rules (Tiers 2-4)**: 3,934,480 additional rules from 6 new sources:
  - YAGO 4.5 full: 3,457,940 rules (166K strict, 3.29M defeasible)
  - Gene Ontology: 350,580 rules (349K defeasible, 1,250 defeaters)
  - MeSH: 76,650 rules (76K strict medical taxonomy)
  - Wikidata: 23,228 rules (11,555 defeaters -- highest defeater density)
  - SUMO: 13,317 rules (3,465 defeasible, 792 defeaters)
  - FrameNet: 12,765 rules (781 strict, 11,984 defeasible)
**Grand Total Rules**: 4,227,374 across all tiers (1,826x Tier 0)
**Codec**: ALL 4 modalities + 3 decoders, 100% round-trip (M2-M4)
**Base Evaluation**: COMPLETE -- 4 Foundry models, all instances, all modalities
**Paper Tables 1-3**: Populated with real results
**Symbolic Baseline**: L2=100% (374/374), L3=100% (35/35)
**Fine-Tuning Scripts**: All written and tested (B1-B6 + SLURM)
**Paper Tables 4-6**: EMPTY -- awaiting finetuning results
**Debate Infrastructure**: COMPLETE -- MCTS engine, debate agents, protocol, resolution, experiments, Tables 7-9
**Comprehensive Orchestrator**: `hpc/run_all_experiments.sh` -- single script submits ALL phases (A0-A4, B0-B6, C) with SLURM dependency chains
**Presentation**: `paper/mvp_validation_slides.tex` fully updated to current project state (metropolis theme, real results, 7 contributions, debate section, KB expansion, 947 tests, ~35 slides)

---

## What Is Done

### Phase A: Base Evaluation (COMPLETE)

Four frontier models evaluated via Azure AI Foundry across 374 L2 + 35 L3 instances, 4 modalities (M1-M4), 2 prompting strategies (direct + CoT):

| Model | L2 | L3 | L3 CoT | Rendering-Robust |
|-------|----|----|--------|-----------------|
| DeepSeek-R1 | 73.0% | 65.0% | 92.9% | 23.5% |
| GPT-5.2-chat | 62.8% | 47.5% | 87.1% | 9.1% |
| Claude Sonnet 4.6 | 77.2% | 16.4% | 9.3% | 15.5% |
| Kimi-K2.5 | 65.5% | 14.2% | 27.6% | 7.8% |

Key findings substantiated in paper:
- Architectural dissociation: CoT helps reasoning models (+56-79 pp at L3), hurts instruction models (-14 pp)
- M1 narrative bottleneck: 55-70 pp gap between M1 and formal modalities
- Domain ordering: biology easiest, legal hardest (stable across all 4 models)
- All McNemar tests significant (p < 0.001) except Claude vs Kimi at L3

### Infrastructure (COMPLETE)

- All analysis scripts: `analyze_results.py`, `generate_paper_tables.py`, `error_taxonomy.py`, `novelty_analysis.py`, `conservativity_analysis.py`, `scaling_analysis.py`, `difficulty_analysis.py`, `partition_sensitivity.py`
- All B6 finetuning analysis scripts (10 scripts in `experiments/finetuning/`)
- All SLURM scripts for B1-B5 pipeline
- `submit_eval_finetuned_all.sh` for batch checkpoint evaluation
- `l12_only` curriculum implemented in `train_dpo.py`
- `slurm_train_rlhf.sh` hyperparams corrected (KL=0.05, mini_batch=8)
- `base_model.txt` written by both training scripts
- Margin DPO matches paper Eq.10 (additive, not multiplicative)
- `hpc/run_all_experiments.sh`: comprehensive orchestrator submitting all ~65 SLURM jobs across phases A0-A4, B0-B6, C with dependency chains
- `hpc/slurm_debate.sh`: SLURM wrapper for adversarial debate experiments (Section 7)
- `hpc/slurm_analysis.sh`: SLURM wrapper for Phase A analysis pipeline (11 scripts)
- `hpc/slurm_ft_analysis.sh`: SLURM wrapper for Phase B6 fine-tuning analysis (11 scripts)
- `hpc/slurm_generate_instances.sh`: fixed to reference correct script (`generate_all_instances.py`)

### Phase C: Adversarial Defeasible Debate (COMPLETE)

- `src/blanc/search/`: MCTS engine (`mcts.py`), derivation space adapter (`derivation_space.py`), reward functions (`reward.py`)
- `src/blanc/debate/`: debate agents (`agent.py`), protocol (`protocol.py`), resolution scoring (`resolution.py`)
- `src/blanc/reasoning/derivation_tree.py`: extended with `get_critical_subtree`, `enumerate_permutations`, `tree_overlap`, `extract_support_path`
- `experiments/debate/`: `run_debate.py` CLI, `analyze_debate.py` analysis, LaTeX table generation
- `tests/search/` and `tests/debate/`: 63 tests all passing
- Paper Section 7: 8 subsections, 6 new definitions, 3 new theorems with proofs, Tables 7-9
- Abstract, Introduction, Related Work, Discussion, Conclusion all updated to reference debate

### Paper (Sections 1-7 COMPLETE, Section 6 tables empty)

- Abstract, Introduction, Related Work, Method, Results: all written with real numbers
- Section 6 (Defeasible Fine-Tuning): methodology written, Tables 4-6 placeholders
- Section 7 (Adversarial Defeasible Debate): complete with definitions, theorems, experiments
- Discussion and Conclusion: updated to reference debate alongside finetuning
- Author block: Patrick Cooper (fixed)
- Bibliography: all entries present (added MCTS and debate references)

---

## What Is Not Done

### Phase B: Finetuning on CURC (BLOCKED -- fix committed, ready to resubmit)

**Full failure history** (5 B1 attempts, all failed):

| Job | Date | Duration | Failure |
|-----|------|----------|---------|
| 24442872 | Mar 3 | 12s | `PYTHONPATH: unbound variable` -- fixed in `b009a48` |
| 24482007 | Mar 5 | 18s | `mkdir: Permission denied` -- `BASH_SOURCE` resolves to SLURM spool dir. Fixed in `8e67169` |
| 24552735 | Mar 9 | 5m09s | CUDA OOM (see below) |
| 24552736 | Mar 9 | 5m06s | CUDA OOM -- Qwen 72B AWQ: 36 GB weights, 39.49 GiB GPU total. OOM during `awq_marlin_repack` |
| 24552737 | Mar 9 | 5m07s | CUDA OOM -- DS-R1 70B AWQ: 37.09 GB weights loaded, `Available KV cache memory: -2.00 GiB` |

**Root cause of Mar 9 OOM**: CURC `aa100` partition has a mix of 40GB and 80GB A100 nodes. All three Mar 9 jobs landed on `c3gpu-c2-u9` (40GB A100-SXM4-40GB). The 72B and 70B AWQ models require ~36-37 GB for weights alone, leaving no room for KV cache or AWQ kernel repacking on 40GB GPUs.

**Fix**: Use tensor parallelism (TP=2) for 70B+ models. Updated `slurm_sample_responses.sh` to accept `TP_SIZE` env var and `--tensor-parallel-size` flag. Override `--gres=gpu:2` at submission time for 70B+ models. Also: `--dtype auto`, `--max-model-len 2048`, `--gpu-memory-utilization 0.95`, `PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True`.

**Models downloaded**: All three models present in CURC HF cache (`/scratch/alpine/paco0228/hf_cache/`, dated Mar 9).

**CURC repo status**: At commit `d426c7d` (missing only `3e9163b` which is slides/gitignore). Needs `git pull` to get the TP fix.

**CURC environment status**: Both `defab-train` and `vllm-env` conda envs exist and are ready.

**Pipeline sequence**: B1 (response sampling, ~8h each, 2x A100 for 70B+) -> B2 (DPO, 12 jobs, 24h, 4x A100) -> B3 (RLHF, 4 jobs, 36h, 4x A100) -> B5 (eval, ~4h each, 2x A100 for 70B+) -> B6 (analysis)

### Paper Claims Not Yet Substantiated

- Tables 4-6: finetuning results (all "--")
- Conjectures 1-4 (Section 6.8): unverified
- M1 decoder recovery rate: not computed; 200-failure manual audit not done
- Appendix C (decoder validation): referenced as `app:decoder` but not written
- Scaling analysis (Qwen 72B vs 32B): requires CURC base eval (optional -- deprioritized vs finetuning)

---

## Remaining Work

### Immediate (today -- Mar 13)
- [x] Fix SLURM `BASH_SOURCE` bug -- commit `8e67169`
- [x] Fix SLURM `PYTHONPATH` bug -- commit `b009a48`
- [x] Download 3 models to CURC HF cache (~87 GB) -- confirmed present Mar 9
- [x] Diagnose Mar 9 CUDA OOM failures -- 40GB A100 nodes, models too large for single GPU
- [x] Fix `slurm_sample_responses.sh` -- add TP_SIZE, tensor parallelism, optimized vLLM params
- [ ] Push TP fix, pull on CURC, resubmit B1 for all 3 models
- [x] Update guidance documents

### Phase B Execution (~2 weeks)
- [ ] B1: Response sampling (3 models, ~8h each)
- [ ] B2: DPO training (12 jobs, ~24h each)
- [ ] B3: RLHF training (4 jobs, ~36h each)
- [ ] B4: Level transfer ablation (l12_only curriculum, Qwen-72B)
- [ ] B5: Evaluate all checkpoints (~24 jobs, ~4h each)
- [ ] B6: Run all 10 analysis scripts, populate Tables 4-6

### Paper Completion (~1 week after B6)
- [ ] Populate Tables 4-6 from finetuning results
- [ ] Confirm/reject Conjectures 1-4
- [ ] Write Appendix C (decoder validation)
- [ ] Update Discussion and Conclusion with finetuning findings
- [ ] Final polish and submission

### Tier 1: Cross-Ontology Dataset (COMPLETE -- Mar 17)

**Extraction**: 290,576 rules from OpenCyc (taxonomy) + ConceptNet (behavioral properties) via `scripts/extract_cross_ontology_all.py`:
- Biology: 40,728 rules (10,712 defeasible, 56 defeaters)
- Legal: 34,724 rules (809 defeasible)
- Materials: 13,776 rules (278 defeasible)
- Chemistry: 72,306 rules (8,276 defeasible)
- Everyday: 129,042 rules (87,062 defeasible)

**Instance Generation**: 313,314 instances from `scripts/generate_tier1_instances.py`:
- Biology: 56,634 (L1=31,239, L2=25,395)
- Everyday: 212,365 (L1=122,758, L2=89,607)
- Legal: 29,618 (L1=14,848, L2=14,770)
- Materials: 14,697 (L1=8,137, L2=6,560)
- Chemistry: pending (process memory limit on local machine; run on CURC)

**Infrastructure fixes applied**:
- Full ancestor chain traversal in `cross_ontology.py` (transitive closure)
- Concept name normalization for OpenCyc/ConceptNet alignment
- Self-typed grounding facts for derivation chains
- Sub-theory partitioning by taxonomy subtree (hard cap 100 rules)
- Fast ablation (random element removal) instead of full Crit* computation
- Forward-chaining target discovery instead of full defeasible proof
- Automated Level 3 generation from NotCapableOf defeaters

### KB Expansion Infrastructure (COMPLETE -- Mar 16)
- [x] Domain profile system: `src/blanc/ontology/domain_profiles.py` -- 5 domain profiles (biology, legal, materials, chemistry, everyday) with keywords, relation mappings, behavioral predicates, known exceptions
- [x] Generalized ConceptNet extractor: accepts DomainProfile, supports Causes + UsedFor relations (6 total)
- [x] Generalized OpenCyc extractor: accepts DomainProfile for multi-domain extraction with OWL property extraction
- [x] Cross-ontology combiner: `src/blanc/ontology/cross_ontology.py` -- taxonomy + property combination, property inheritance, defeater detection
- [x] Rule validation framework: `src/blanc/ontology/rule_validator.py` -- depth, deduplication, consistency, anomaly, superiority, multi-body tracking
- [x] KB composers updated to integrate behavioral rules and superiority relations
- [x] Comprehensive tests for all new modules

### Maximal Behavioral Rule Expansion (COMPLETE -- Mar 16)
- [x] Biology: 314 behavioral rules (220 defeasible + 94 defeaters) across 14 categories (locomotion, morphology, thermoregulation, reproduction, diet, habitat, behavior, respiration, sensory, social, development, communication, defense, ecology) + 30 multi-body compound rules + 25 superiority relations
- [x] Legal: 194 behavioral rules (118 defeasible + 76 defeaters) across 11 categories (capacity, liability, procedural, property, normative, constitutional, criminal, corporate, family, employment, administrative) + 20 multi-body compound rules + 15 superiority relations
- [x] Materials: 218 behavioral rules (144 defeasible + 74 defeaters) across 15 categories (electrical, thermal, mechanical, corrosion, optical, magnetic, structural, processing, biocompatibility, phase transitions, failure modes, surface, composites, semiconductors, recyclability) + 20 multi-body compound rules + 15 superiority relations
- [x] Entity instances expanded: biology 85 -> 135 organisms, legal 40 -> 61 entities, materials 43 -> 65 materials
- [x] All five components of Def 3.2 quintet now populated: F, R_s, R_d, R_df, and succ (previously succ was empty)

### Optional (if time permits)
- [ ] CURC base evaluation (Qwen-72B, Qwen-32B, DS-R1-70B) for scaling analysis
- [ ] M1 decoder 200-failure manual audit
- [ ] Run cross-ontology extraction with downloaded OpenCyc + ConceptNet data (100K-350K rules)

**Total CURC GPU budget**: ~158 GPU-days (free for CU Boulder researchers)
**Total API cost**: ~$26 (Foundry eval already spent)
