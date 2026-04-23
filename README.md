# DeFAb: Defeasible Abduction Benchmark

A dataset and generation pipeline for evaluating foundation models on grounded abductive reasoning, belief revision, and creative hypothesis generation.

**Author**: Patrick Cooper, University of Colorado Boulder

**Target venue**: NeurIPS 2026 Evaluations & Datasets Track

---

## Overview

Foundation models excel at forward inference but struggle with abduction and belief revision: proposing hypotheses that explain observations and retracting defaults when exceptions arise. DeFAb converts legacy knowledge bases into defeasible theories and generates evaluation instances with polynomial-time verifiable gold-standard hypotheses at three difficulty levels:

- **Level 1 (Fact completion)**: Identify a missing observation.
- **Level 2 (Rule abduction)**: Reconstruct a missing generalization.
- **Level 3 (Defeater abduction)**: Construct a conservative exception rule that overrides an incorrect default while preserving unrelated expectations.

### Scale

- **33.7 million materialized rules** from 15 knowledge sources
- **356,000+ evaluation instances** across Tiers 0--2
- **4 frontier models evaluated**: GPT-5.2-chat, Claude Sonnet 4.6, DeepSeek-R1, Kimi-K2.5
- **Synthetic contamination control** with invented predicate names

---

## Quick Start

```bash
git clone https://github.com/PatrickAllenCooper/blanc.git
cd blanc
pip install -r requirements.txt
python -m pytest tests/ --tb=no -q
```

### LLM Evaluation

```bash
cp .env.template .env       # Add API keys (Azure AI Foundry, etc.)
python experiments/validate_api_keys.py
python experiments/run_evaluation.py --provider foundry-claude --modalities M4 M2
```

### Instance Generation

```bash
python scripts/generate_tier1_instances.py          # Tier 1 cross-ontology (324K instances)
python scripts/generate_multitier_instances.py       # Tier 2 domain-specific
python scripts/generate_synthetic_instances.py       # Synthetic contamination control
```

---

## Knowledge Base Sources

| Tier | Sources | Rules | Instances |
|------|---------|-------|-----------|
| 0 (baseline) | YAGO, WordNet, LKIF Core, MatOnto | 2,318 | 409 |
| 1 (cross-ontology) | OpenCyc + ConceptNet | 289,305 | 324,511 |
| 2 (domain-specific) | GO, MeSH, SUMO, FrameNet, Wikidata | 535,565 | 31,500+ |
| 2+ (biomedical) | UMLS 2025AB | 29,465,582 | pending |
| 3 (encyclopedic) | YAGO 4.5 full | 3,457,940 | pending |

Source knowledge bases span 1984 (Cyc) to 2025 (UMLS 2025AB, YAGO 4.5) and include government-funded AI programs (DARPA, NSF, NIH, EU ESTRELLA), encyclopedic projects (Wikidata, DBpedia), and domain ontologies (Gene Ontology, SNOMED CT, LKIF Core).

---

## Baseline Evaluation Results

Accuracy (%) by model and task level (formal modalities, best prompting strategy):

| Model | Level 2 (Rule Abduction) | Level 3 (Defeater Abduction) |
|-------|--------------------------|------------------------------|
| DeepSeek-R1 | 73.7 | 65.0 (CoT: 92.9) |
| GPT-5.2-chat | 78.5 | 47.5 (CoT: 87.1) |
| Claude Sonnet 4.6 | 79.3 | 23.6 (direct) |
| Kimi-K2.5 | 71.9 | 27.6 (CoT) |

Key finding: Grounding is largely solved at Level 2 (73--79%). Belief revision at Level 3 is latent and highly prompt-sensitive, with a 56--79 pp swing between direct and chain-of-thought prompting for reasoning-optimized models.

---

## Project Structure

```
src/blanc/              Core library
  core/                   Theory representation, rule types
  author/                 Instance generation pipeline (the "Author Algorithm")
  generation/             Partition functions, distractors, synthetic generator
  ontology/               KB extractors (YAGO, GO, UMLS, Wikidata, SNOMED, etc.)
  reasoning/              Defeasible derivation engine
  codec/                  Rendering codecs (M1--M4 modalities)
  math/                   DeFAb-Math-Topology: Lean kernel adapter, topology
                          extractor, hypothesis dropper, novelty filter,
                          defeater scorer
paper/                  LaTeX papers
  dataset_paper.tex       NeurIPS 2026 E&D track submission
  paper.tex               Full technical paper (includes fine-tuning + debate)
experiments/            Evaluation pipeline, model interfaces, analysis
  math_topology/          DeFAb-Math-Topology benchmark generator, baseline,
                          Lakatos rediscovery, at-scale dropping, GRPO
                          assembly, discovery harvester, M4/M5 scaffolds
instances/              Generated evaluation instances by tier
scripts/                Data download, extraction, generation scripts
hpc/                    SLURM scripts for CURC Alpine HPC
tests/                  Test suite (incl. tests/math/ for the topology pipeline)
Guidance_Documents/     Project planning and documentation
```

---

## Papers

- **`paper/dataset_paper.tex`** -- NeurIPS 2026 Evaluations & Datasets track submission. Focused on the DeFAb dataset: generation pipeline, cross-ontology extraction, contamination control, and baseline evaluation.

- **`paper/paper.tex`** -- Full technical paper including fine-tuning via preference optimization (DPO, RLHF, GRPO) and adversarial defeasible debate via Monte Carlo Tree Search.

---

## DeFAb-Math-Topology

The math-side analogue of the main pipeline. The Lean 4 kernel replaces the polynomial-time defeasible verifier; everything above the harness layer (dropper, scorer, novelty filter, SFT/DPO/GRPO data prep, expert-iteration scaffold) is shared in shape with the main project.

The cardinal risk is *trivial restoration*: the model just memorises the dropped hypothesis and Lean accepts it back. The novelty filter scores trivially-restored defeaters at zero, and the Lakatos positive control (M2) tests this on Euler V-E+F=2 / genus before any novel-discovery claim is made.

End-to-end smoke run on the mock harness:

```bash
python experiments/math_topology/at_scale_dropping.py \
  --provider mock \
  --output-dir experiments/math_topology/results/m3_v0 \
  --samples-per-challenge 8 --policy single_critical
python experiments/math_topology/grpo_dataset.py \
  --groups experiments/math_topology/results/m3_v0/groups.jsonl \
  --output experiments/math_topology/results/m3_v0/grpo.jsonl
python experiments/math_topology/discovery_harvester.py \
  --survivors experiments/math_topology/results/m3_v0/survivors.jsonl \
  --output experiments/math_topology/results/m3_v0/discoveries.jsonl
```

Tests: `python -m pytest tests/math/ --no-cov -q` (130 tests). See `Guidance_Documents/COMPREHENSIVE_KB_PIPELINE.md` for milestone status (M0--M3 implemented; M4/M5 deferred with stub interfaces) and the agenda in `.cursor/plans/`.

---

## HPC (CURC Alpine)

Open-source model evaluations and large-scale instance generation run on the University of Colorado Research Computing Alpine cluster. See `hpc/` for SLURM submission scripts:

- `slurm_evaluate_curc_vllm.sh` -- vLLM-based evaluation of DeepSeek-R1, Qwen 2.5
- `slurm_gen_go.sh` -- Gene Ontology instance generation (409K rules)
- `slurm_gen_wikidata.sh` -- Wikidata L3 defeater generation (11K defeaters)
- `slurm_gen_umls.sh` -- UMLS subsampled generation (29.5M rules)
- `slurm_yago_full_generate.sh` -- Full YAGO 4.5 generation (3.5M rules)

---

## License

MIT. See [LICENSE](LICENSE).

Source knowledge base licenses: YAGO (CC-BY 4.0), WordNet (Princeton License), LKIF Core (Apache 2.0), MatOnto (CC-BY 4.0), Wikidata (CC0 1.0), ConceptNet (CC-BY-SA 4.0), Gene Ontology (CC-BY 4.0), UMLS (NLM License), SUMO (GPLv2), FrameNet (CC-BY 3.0), MeSH (public domain).
