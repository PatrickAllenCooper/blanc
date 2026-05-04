# DeFAb: Defeasible Abduction Benchmark

A dataset and generation pipeline for evaluating foundation models on grounded
abductive reasoning, belief revision, and creative hypothesis generation.

**Author**: Anonymous (NeurIPS 2026 E&D submission; revealed in camera-ready)

**Target venue**: NeurIPS 2026 Evaluations & Datasets Track

---

## Overview

Foundation models excel at forward inference but struggle with abduction and
belief revision: proposing hypotheses that explain observations and retracting
defaults when exceptions arise. DeFAb converts legacy knowledge bases into
defeasible theories and generates evaluation instances with polynomial-time
verifiable gold-standard hypotheses at three difficulty levels:

- **Level 1 (Fact completion)**: Identify a missing observation.
- **Level 2 (Rule abduction)**: Reconstruct a missing generalization.
- **Level 3 (Defeater abduction)**: Construct a conservative exception rule
  that overrides an incorrect default while preserving unrelated expectations.

### Scale

- **33.75 million materialized rules** from 18 knowledge sources
- **372,648+ evaluation instances** across Tiers 0--3 plus a game-grounded
  RTS family
- **4 frontier models evaluated**: GPT-5.2-chat, Claude Sonnet 4.6,
  DeepSeek-R1, Kimi-K2.5
- **Synthetic contamination control** with invented predicate names

---

## Repository contents (review version)

This is a streamlined snapshot of the repository, scoped to what reviewers
need to verify the claims in the paper. The full development repository
(including HPC orchestration, ablation runs, exploratory notebooks, math-side
research thrust, RTS live-integration tooling, and result archives) is on
the anonymous mirror.

```
paper/                       NeurIPS 2026 E&D submission paper
  paper.tex                  LaTeX source (9-page main body + appendices)
  paper.pdf                  Compiled paper PDF
  references.bib             Bibliography
  neurips_2026.sty           NeurIPS 2026 style file
  croissant.json             Croissant metadata (core + RAI fields)
  generate_figures.py        Matplotlib figure generation
  fig_*.tex                  TikZ figure source files
  figures/                   Compiled figure PDFs
  tables/                    Tabular content (Level 3 metrics, error taxonomy)

src/blanc/                   Core library
  core/                      Theory representation, rule types
  author/                    Instance generation pipeline (Author Algorithm)
  generation/                Partition functions, distractors, synthetic generator
  ontology/                  KB extractors (YAGO, GO, UMLS, Wikidata, etc.)
  reasoning/                 Defeasible derivation engine (the polynomial-time verifier)
  codec/                     Rendering codecs (M1-M5 modalities)
  utils/                     Shared utilities

experiments/                 Evaluation pipeline
  evaluation_pipeline.py     End-to-end evaluation orchestration
  run_evaluation.py          CLI entry point
  model_interface.py         API client wrappers (OpenAI / Anthropic / Foundry / vLLM)
  prompting.py               Prompt templates per modality and strategy
  level3_evaluator.py        Level 3 graded scoring function
  symbolic_baseline.py       ASP solver baseline (the 100% / 50us baseline)
  *_analysis.py              Statistics, conservativity, novelty, partition sensitivity
  validate_*.py              Decoder pipeline and API key validation

scripts/                     Generation entry points
  generate_tier1_instances.py        Tier 1 cross-ontology (324K instances)
  generate_multitier_instances.py    Tier 2 domain-specific
  generate_synthetic_instances.py    Synthetic contamination control
  generate_rts_instances.py          Tier RTS engagement KB
  certify_rts_kb.py                  Formal certification of RTS KB
  validate_cross_ontology_scale.py   Tier 1 yield validation

instances/                   Sample instances (50 per tier; full dataset on mirror)
tests/                       Unit tests for core library (verifier, generation, codec)
Guidance_Documents/          Project documentation
```

---

## Quick start

```bash
git clone https://anonymous.4open.science/r/blanc-anon
cd blanc-anon
pip install -r requirements.txt
python -m pytest tests/ --tb=no -q
```

### LLM evaluation

```bash
cp .env.template .env       # Add API keys (Azure AI Foundry, etc.)
python experiments/validate_api_keys.py
python experiments/run_evaluation.py --provider foundry-claude --modalities M4 M2
```

### Instance generation

```bash
python scripts/generate_tier1_instances.py          # Tier 1 cross-ontology
python scripts/generate_multitier_instances.py      # Tier 2 domain-specific
python scripts/generate_synthetic_instances.py      # Synthetic contamination control
```

---

## Knowledge base sources

| Tier | Sources | Rules | Instances |
|------|---------|-------|-----------|
| 0 (baseline) | YAGO, WordNet, LKIF Core, MatOnto | 2,318 | 409 |
| 1 (cross-ontology) | OpenCyc + ConceptNet | 289,305 | 324,511 |
| 2 (domain-specific) | GO, MeSH, SUMO, FrameNet, Wikidata, BabelNet | 535,565 | 31,477 |
| 2+ (biomedical) | UMLS 2025AB | 29,465,582 | 13,425 |
| 3 (encyclopedic) | YAGO 4.5 full | 3,457,940 | 2,580 |
| RTS (game-grounded) | rts_engagement, lux_ai_s3 | 478 | 246+ |

Source knowledge bases span 1984 (Cyc) to 2025 (UMLS 2025AB, YAGO 4.5) and
include government-funded AI programs (DARPA, NSF, NIH, EU ESTRELLA),
encyclopedic projects (Wikidata, DBpedia), and domain ontologies (Gene
Ontology, SNOMED CT, LKIF Core).

---

## Baseline evaluation results

Headline metric: **rendering-robust accuracy** (worst case over text
modalities M1--M4). Random chance for six-choice selection is 16.7%; the
ASP symbolic baseline achieves 100% in under 50 microseconds per instance.

| Model | Rendering-Robust | L2 Direct | L3 Direct | L3 CoT |
|-------|------------------|-----------|-----------|--------|
| DeepSeek-R1 | 23.5% | 73.7% | 37.1% | 92.9% |
| Claude Sonnet 4.6 | 15.5% | 79.3% | 23.6% | 9.3% |
| GPT-5.2-chat | 9.1% | 78.5% | 7.9% | 87.1% |
| Kimi-K2.5 | 7.8% | 71.9% | 0.8% | 27.6% |

Two of four frontier models score at or below random chance on the
rendering-robust metric. Per-cell variance of the chain-of-thought effect
across (model, level) cells: sigma = 36 percentage points, range = 110
percentage points (Appendix K).

---

## Reproducing key results

- **Symbolic baseline (Section 5.1)**: `python experiments/symbolic_baseline.py`
- **Frontier model evaluation (Section 5.3)**: `python experiments/run_evaluation.py --provider <provider>` then `python experiments/analyze_results.py`
- **Difficulty stratification (Appendix F)**: `python experiments/difficulty_analysis.py`
- **Per-cell CoT variance (Appendix K)**: numbers extracted by `experiments/error_taxonomy.py` from foundry result JSONs (results not included in review repo; reproduce by running the evaluation step above)

---

## License

MIT (pipeline and produced instances). Source knowledge base licenses:
YAGO (CC-BY 4.0), WordNet (Princeton License), LKIF Core (Apache 2.0),
MatOnto (CC-BY 4.0), Wikidata (CC0 1.0), ConceptNet (CC-BY-SA 4.0),
Gene Ontology (CC-BY 4.0), UMLS (NLM License), SUMO (GPLv2),
FrameNet (CC-BY 3.0), MeSH (public domain).
