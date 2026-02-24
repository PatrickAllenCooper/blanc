# BLANC Repository Structure

**Last Updated**: 2026-02-18
**Status**: Pre-evaluation — infrastructure complete, awaiting cloud/CURC evaluation runs

---

## Root

```
blanc/
├── README.md                       # Project overview (read first)
├── INSTALL.md                      # Environment setup and dependencies
├── .env.template                   # API key template (copy to .env)
├── requirements.txt                # Python dependencies
├── setup.py / pyproject.toml       # Package configuration
├── pytest.ini                      # Test configuration
└── .gitignore
```

---

## Source library (`src/blanc/`)

```
src/blanc/
├── core/
│   ├── theory.py          # Theory, Rule, RuleType dataclasses
│   ├── query.py           # Query builder
│   ├── result.py          # ResultSet
│   └── knowledge_base.py  # KnowledgeBase wrapper
│
├── reasoning/
│   ├── defeasible.py      # D ⊢∂ q engine (Definition 7, paper.tex)
│   └── derivation_tree.py # AND-OR proof trees (Definition 13)
│
├── author/
│   ├── generation.py      # AbductiveInstance; L2/L3 generation (Defs 20-21)
│   ├── conversion.py      # φ_κ(Π) knowledge-base conversion (Definition 9)
│   ├── support.py         # Crit*(D,q) criticality (Definition 18)
│   └── metrics.py         # Y(κ,Q) yield metrics (Definition 22)
│
├── generation/
│   ├── partition.py       # 4 partition functions (Definition 10)
│   └── distractor.py      # 3 distractor sampling strategies (Section 4.2)
│
├── codec/
│   ├── encoder.py         # PureFormalEncoder: M4 formal encoding
│   ├── m1_encoder.py      # M1: Narrative modality
│   ├── m2_encoder.py      # M2: Semi-formal modality
│   ├── m3_encoder.py      # M3: Annotated formal modality
│   ├── decoder.py         # D1: Exact match decoder
│   ├── d2_decoder.py      # D2: Template extraction (Levenshtein)
│   ├── d3_decoder.py      # D3: Semantic parser (Lark grammar)
│   ├── cascading_decoder.py  # D1 → D2 → D3 pipeline
│   └── nl_mapping.py      # Predicate ↔ natural-language mapping
│
├── ontology/
│   ├── conceptnet_extractor.py  # ConceptNet edge extraction
│   └── opencyc_extractor.py     # OpenCyc OWL extraction
│
└── utils/
    ├── __init__.py        # Re-exports extract_predicate, etc.
    └── predicates.py      # Shared atom-parsing utilities
```

---

## Experiments (`experiments/`)

All evaluation and analysis scripts. Run from the repository root.

```
experiments/
│
├── # Model interfaces and pipeline
├── model_interface.py          # OpenAI, Azure, Anthropic, Google, CURC, Ollama, Mock
├── evaluation_pipeline.py      # EvaluationPipeline: orchestrates LLM queries
├── prompting.py                # Prompt rendering for M1-M4 × direct/CoT
├── response_cache.py           # Persistent response cache (SHA-256 keyed)
│
├── # Evaluation entry points
├── run_evaluation.py           # CLI: --provider curc|azure|openai|mock …
├── run_pilot_evaluation.py     # Quick 20-instance pilot
├── validate_api_keys.py        # Verify credentials before a run
├── validate_decoder_pipeline.py # Round-trip codec validation
│
├── # Level 3 evaluation
├── level3_evaluator.py         # Level3Evaluator: metrics, partial credit, E1-E5 errors
│
├── # Analysis scripts (run after evaluation)
├── analyze_results.py          # Accuracy, robust accuracy, CoT lift
├── error_taxonomy.py           # E1-E5 error classification
├── novelty_analysis.py         # Nov distribution and accuracy-novelty correlation
├── conservativity_analysis.py  # Conservativity rate and d_rev distribution
├── difficulty_analysis.py      # σ(I) difficulty metric distributions
├── scaling_analysis.py         # Theory-size and model-size scaling
├── partition_sensitivity.py    # Partition sensitivity (Mann-Whitney/KW tests)
├── generate_paper_tables.py    # LaTeX tables 1-4 for Section 5
├── symbolic_baseline.py        # ASP solver ceiling baseline
│
├── # Legacy/reference
│   ├── statistics.py           # Section 4.3 statistics
│   ├── roundtrip_validation.py # Basic round-trip validation
│   └── yield_model_fitting.py  # Yield model fitting
│
└── finetuning/                        # Section 6: DPO/RLHF fine-tuning pipeline (IMPLEMENTED)
    ├── __init__.py
    ├── prepare_preference_data.py     # Response sampling + preference extraction (Foundry or CURC)
    ├── train_dpo.py                   # DPO/Margin-DPO training (TRL DPOTrainer + LoRA/PEFT)
    ├── train_rlhf_vitl.py             # VITL-RLHF: PPO with DeFAb verifier as reward
    ├── evaluate_finetuned.py          # Evaluate LoRA checkpoint on test split via EvaluationPipeline
    ├── ds_config_zero2.json           # DeepSpeed ZeRO-2 for 4xA100 CURC Alpine
    ├── data/                          # Preference datasets (gitignored)
    └── checkpoints/                   # LoRA checkpoints (gitignored)

# Local runner (no SLURM)
├── run_foundry_local.py           # Full 4-model Foundry evaluation, runs locally
```

---

## Tests (`tests/`)

494 tests, 81% coverage (new modules included). Run with `python -m pytest tests/ -q`.

```
tests/
├── blanc/                  # Core library tests
│   ├── test_theory.py
│   ├── test_defeasible.py
│   ├── test_derivation_tree.py
│   ├── test_generation.py
│   ├── test_conversion.py
│   ├── test_support.py
│   ├── test_partition.py
│   ├── test_distractor.py
│   └── codec/
│       ├── test_m1_encoder.py … test_m4_encoder.py
│       ├── test_d1_decoder.py … test_d3_decoder.py
│       └── test_cascading_decoder.py
│
└── experiments/            # Experiment module tests
    ├── test_model_interface.py   # Includes CURCInterface (mocked)
    ├── test_prompting.py
    ├── test_evaluation_pipeline.py
    ├── test_level3_evaluator.py
    └── test_analysis_scripts.py
```

---

## HPC scripts (`hpc/`)

```
hpc/
├── slurm_evaluate_curc_vllm.sh  # PRIMARY: vLLM (Qwen 2.5 72B / Llama 3.3 70B)
├── slurm_evaluate_foundry.sh    # Azure AI Foundry (4 models, no GPU)
├── slurm_evaluate_curc_all.sh   # Submit all 3 CURC models in parallel
├── slurm_evaluate_azure.sh      # Azure OpenAI (GPT-4o)
├── slurm_evaluate_llama.sh      # Legacy: Ollama on compute node
├── slurm_generate_instances.sh  # Large-scale instance generation
├── slurm_sample_responses.sh    # Fine-tuning: response sampling (1xA100)
├── slurm_train_dpo.sh           # Fine-tuning: DPO training (4xA100)
├── slurm_train_rlhf.sh          # Fine-tuning: VITL-RLHF training (4xA100)
├── slurm_eval_finetuned.sh      # Fine-tuning: evaluate checkpoints (1xA100)
├── slurm_train_all.sh           # Submit all training jobs
└── README.md                    # Alpine cluster usage guide
```

---

## Instances (`instances/`)

Development datasets — committed to git (small JSON files).

```
instances/
├── biology_dev_instances.json    # 114 Level 2 instances
├── legal_dev_instances.json      # 168 Level 2 instances
├── materials_dev_instances.json  # 92  Level 2 instances
├── level3_instances.json         # 35  Level 3 instances (10 with Nov > 0)
└── instance_statistics.json      # Difficulty and yield statistics
```

---

## Expert knowledge bases (`examples/knowledge_bases/`)

Committed Python modules — no large data download needed for local dev.

```
examples/knowledge_bases/
├── biology_kb.py            # Full biology KB (927 rules, from YAGO + WordNet)
├── biology_kb_subset.py     # Dev subset (16 rules, fast iteration)
├── legal_kb.py              # Full legal KB (201 rules, LKIF + DAPRECO)
├── materials_kb.py          # Full materials KB (1,190 rules, MatOnto)
└── materials_kb_subset.py   # Dev subset
```

Raw source data (2.7 GB, not committed) — see `Guidance_Documents/DATA_DOWNLOAD.md`.

---

## Paper (`paper/`)

```
paper/
├── paper.tex                    # NeurIPS submission (1,228 lines, authoritative spec)
└── references.bib               # Bibliography
```

---

## Guidance Documents (`Guidance_Documents/`)

Active reference documents — the authoritative source of truth for the project.

```
Guidance_Documents/
├── STATUS.md                    # Current status and completed-week log (READ FIRST)
├── REVISED_IMPLEMENTATION_PLAN.md  # Week-by-week execution plan (Weeks 9-14)
├── REPOSITORY_STRUCTURE.md      # This file
├── INTUITIVE_GUIDE.md           # Non-expert explanation of the benchmark
├── KNOWLEDGE_BASE_POLICY.md     # Expert-only KB policy (critical constraint)
├── API_Design.md                # API design decisions and changelog
├── COMPREHENSIVE_KB_PIPELINE.md # KB sourcing plan (5-tier architecture)
├── PAPER_ADDITIONS_PROPOSAL.md  # Exact paper changes with LaTeX snippets
└── DATA_DOWNLOAD.md             # How to download the 2.7 GB raw KB data
```
