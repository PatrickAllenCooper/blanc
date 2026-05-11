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

- **33.75 million materialized rules** from 18 knowledge sources
- **372,648+ evaluation instances** across Tiers 0--2 plus a 235-instance DeFAb-Hard pilot (H1 high-novelty, H2 deep-chain, H3 multi-anomaly)
- **4 frontier models evaluated**: GPT-5.2-chat, Claude Sonnet 4.6, DeepSeek-R1, Kimi-K2.5
- **DeFAb-Hard frontier accuracy (M4, provisional)**: GPT-5.2 39.1% pooled (74.3% H1 CoT, 79.8% H2 CoT, 54.5% H3 CoT); Claude Sonnet 4.6 1.5% pooled (collapses on every axis); DeepSeek-R1 and Kimi-K2.5 in progress. Failure-mode audit shows the Claude collapse is task-format brittleness (Claude returns the antecedent fact instead of a defeater rule under direct prompts; CoT reasoning never terminates in a parseable rule), not a reasoning failure.
- **Synthetic contamination control** with invented predicate names; matched fact-injection ablation isolates true contamination gap (mean Delta_synth = +19.4 pp)
- **Cross-benchmark comparison** with DEFREASING reveals reasoning-vs-instruction architectural divide (97--100% empty responses on short classification, normal performance on construction)

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

| Model | L2 (Rule Abduction) | L3 (Defeater Abduction) | L3 Rendering-Robust |
|-------|---------------------|-------------------------|----------------------|
| DeepSeek-R1 | 73.7 | 65.0 (CoT: 92.9) | 23.5 |
| GPT-5.2-chat | 78.5 | 47.5 (CoT: 87.1) | 9.1 |
| Claude Sonnet 4.6 | 79.3 | 16.4 (direct: 23.6) | 15.5 |
| Kimi-K2.5 | 71.9 | 14.2 (CoT: 27.6) | 7.8 |

Key findings:
- Grounding is largely solved at L2 (73--79%) but L3 collapses on the rendering-robust metric (worst case over four surface renderings of the same logical content): 7.8--23.5%, while a symbolic solver achieves 100% in <50 us per instance.
- Belief revision at L3 is latent and highly prompt-sensitive, with a 36 pp prompting-strategy variance and a 56--79 pp swing between direct and CoT prompting for reasoning-optimized models. CoT helps reasoning models (+79 pp) but hurts instruction-tuned models (-14 pp).
- Constrained-output ablation (JSON schema): reasoning models gain accuracy under constraints (DeepSeek +1.4 pp, GPT +6.2 pp, Kimi +32.4 pp on L3 CoT) while Claude's instruction-tuned model collapses (97.1% decoder failures).
- Matched fact-injection ablation reveals the true Delta_synth contamination gap is +19.4 pp (vs +13.6 pp uncorrected), strengthening the structural-deficit claim for reasoning models.

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
  full_paper.tex          Primary project document (no length limit). Reflects all
                          results, ablations, theory, and the live SC2 bridge in full.
  paper.tex               NeurIPS 2026 E&D track submission (9-page main + appendix)
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

- **`paper/full_paper.tex`** (PRIMARY) -- The comprehensive project document. No length limit; reflects all results, ablations, theory, and the live SC2 bridge in full detail. Covers: dataset design and 18-KB cross-ontology extraction, synthetic contamination control with matched fact-injection ablation (Delta_synth = +19.4 pp), constrained-output ablation, DEFREASING cross-benchmark comparison, Tier 2 coverage probe, DeFAb-Hard pilot (235 instances, H1/H2/H3 axes), the verifier-backed fine-tuning substrate (DPO/RLHF/RLVR/GRPO + spectral LoRA + curriculum), defeasible conflict games and theory construction MDP, neural-guided MCTS with adversarial debate, and the deeply-expanded SC2 live bridge (ObservationLifter signature with soundness theorem, Order schema and tolerant parser, B0/B1/B2 verifier-gated commander policy with K-budget convergence theorem, replay extraction protocol, practical utility, limitations, edge cases, ROE evaluation experiments E1--E5, and a conservativity-under-noise theorem). Compiles to ~89 pages.

- **`paper/paper.tex`** -- NeurIPS 2026 Evaluations & Datasets track submission (9-page main + unlimited appendix). A trimmed presentation of the same work calibrated to the track page limit.

- **`paper/paper_tmlr_archive.tex`** -- Archived TMLR-targeted long-form paper. Superseded by `full_paper.tex` going forward.

---

## DeFAb-Math-Topology

The math-side analogue of the main pipeline. The Lean 4 kernel replaces the polynomial-time defeasible verifier; everything above the harness layer (dropper, scorer, novelty filter, SFT/DPO/GRPO data prep, expert-iteration scaffold) is shared in shape with the main project.

The cardinal risk is *trivial restoration*: the model just memorises the dropped hypothesis and Lean accepts it back. The novelty filter scores trivially-restored defeaters at zero, and the Lakatos positive control (M2) tests this on Euler V-E+F=2 / genus before any novel-discovery claim is made.

### Prerequisites

```bash
# 1. Install elan (Lean version manager)
curl -sSf https://raw.githubusercontent.com/leanprover/elan/master/elan-init.sh | sh -s -- -y
export PATH="$HOME/.elan/bin:$PATH"

# 2. Get pre-compiled Mathlib cache (a few minutes, not hours)
cd lean/
lake exe cache get   # uses Lean 4.25.0, pinned in lean/lean-toolchain

# 3. Install Python harness
pip install lean-interact
```

The `lean/` project tracks `lakefile.lean` and `lean-toolchain` (pinned to `leanprover/lean4:v4.25.0`). Build artifacts go into `lean/.lake/` which is gitignored.

### End-to-end smoke run (mock, no Lean needed)

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

### Real-Lean dry run on Euler V-E+F=2 (requires elan + FOUNDRY_API_KEY)

```bash
# Build Mathlib novelty index (~350ms after cache is populated):
python scripts/extract_mathlib_topology_index.py  # writes experiments/math_topology/data/mathlib_topology_index.jsonl

# Single-theorem dry run (4 samples, foundry-claude, real Lean):
python experiments/math_topology/at_scale_dropping.py \
  --provider foundry-claude \
  --corpus-filter EulerCharacteristic.convex_polytope_v_minus_e_plus_f \
  --policy single_critical \
  --samples-per-challenge 4 \
  --mathlib-index experiments/math_topology/data/mathlib_topology_index.jsonl \
  --output-dir experiments/math_topology/results/m0_real
```

Observed per-call Lean latency: first call ~1500ms (REPL startup), subsequent calls 0--10ms (connection reuse).

### M2 SFT/DPO data with real Lean verdicts

```bash
# Mock (default, CI-safe):
python experiments/math_topology/prepare_sft_data.py \
    --output experiments/math_topology/data/lakatos_sft.jsonl

# Real Lean (requires lean-interact):
python experiments/math_topology/prepare_sft_data.py \
    --harness lean_interact \
    --output experiments/math_topology/data/m2_real/sft.jsonl
python experiments/math_topology/prepare_dpo_data.py \
    --harness lean_interact \
    --output experiments/math_topology/data/m2_real/dpo.jsonl
```

### Tests

```bash
# Mock tests (CI-safe, 130 tests):
python -m pytest tests/math/ --no-cov -q

# Real-Lean tests (requires lean-interact + Lean 4 toolchain):
python -m pytest tests/math/test_lean_interact_harness.py -m lean_real -v
```

See `Guidance_Documents/COMPREHENSIVE_KB_PIPELINE.md` for milestone status (M0--M3 implemented; M4/M5 deferred with stub interfaces) and the agenda in `.cursor/plans/`.

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
