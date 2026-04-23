# Comprehensive Knowledge Base Pipeline

**Author**: Patrick Cooper  
**Date**: 2026-03-22  
**Purpose**: Master plan for ingesting all government-sponsored, encyclopedic, and domain-specific knowledge bases into the DeFAb benchmark pipeline  
**Replaces**: Partial coverage in CROSS_ONTOLOGY_PLAN.md, ALL_GOVERNMENT_KBS.md, SCALE_OPPORTUNITY.md

---

## Overview

The DeFAb benchmark is grounded in decades of publicly funded knowledge engineering. This document defines the complete KB sourcing strategy: what each source provides, how to extract defeasible rules and defeaters from it, and when to do so relative to the NeurIPS submission timeline.

The core argument for the paper: a vast infrastructure of structured knowledge — spanning 1980s government AI initiatives, modern biomedical informatics programs, and global encyclopedic projects — already encodes both default generalizations and documented exceptions. DeFAb provides the first systematic pipeline for converting this infrastructure into formally grounded defeasible abduction benchmarks.

---

## Dataset Paper Status

**Target venue**: NeurIPS 2026 Evaluations & Datasets Track (renamed from "Datasets & Benchmarks")  
**Deadlines**: Abstract May 4, 2026; Full paper May 6, 2026  
**Paper file**: `paper/dataset_paper.tex` (dedicated dataset paper, separate from `paper/paper.tex`)

The original `paper/paper.tex` contains three papers in one (dataset, fine-tuning methods, adversarial debate). The dedicated dataset paper (`dataset_paper.tex`) focuses exclusively on the DeFAb dataset contribution with five contributions: (1) the generation pipeline with polynomial-time instance generation, (2) the cross-ontology KB extraction methodology spanning 15 sources and 33.7M rules, (3) the synthetic contamination control, (4) baseline evaluation of four frontier models, and (5) a multimodal visual grounding modality (M5) for vision-language evaluation. Fine-tuning (DPO/RLHF/GRPO) and adversarial debate (MCTS) are mentioned as future directions only.

### Remaining TODOs for Dataset Paper Submission

**Critical (must complete before submission):**
- ~~Generate and present dataset statistics tables~~ DONE: instance counts reconciled (372,402 total), difficulty distributions and partition sensitivity JSONs regenerated
- Either complete the contamination analysis (run model evaluation on synthetic instances to compute Delta_synth) or reframe as methodology-only with results pending. Synthetic instances generated (409 matched to Tier 0); model evaluation blocked on API keys.
- ~~Upload dataset to HuggingFace and obtain stable URL~~ DONE: all tiers/instances uploaded to `PatrickAllenCooper/DeFAb`; multitier instances (framenet, gene_ontology, sumo, wikidata, umls, yago_full, babelnet) and updated tier1 instances uploaded 2026-04-15
- ~~Generate Croissant metadata JSON-LD file~~ DONE: `paper/croissant.json` with core + RAI fields
- ~~Complete the Dataset Access section (hosting URL, loading instructions, maintenance plan)~~ DONE
- ~~Complete the Datasheet for Datasets appendix (Gebru et al. framework)~~ DONE
- ~~Download and integrate the NeurIPS 2026 LaTeX template (`neurips_2026.sty`)~~ DONE
- ~~Complete the NeurIPS 2026 paper checklist~~ DONE (16 items, all answered)
- ~~Verify 9-page main body limit~~ DONE: body fits exactly in 9 pages

**Important (strengthen the paper):**
- Add Qwen 2.5-72B and Qwen 2.5-32B results for within-family scaling analysis (Qwen 2.5-32B SFT training in progress on Azure)
- ~~Fill in Level 3 metrics table (conservativity, novelty, revision distance)~~ DONE: extracted from full foundry result JSONs. DeepSeek-R1: 59.6% resolves, 59.6% conservative, Nov=0.14. GPT-5.2: 42.9%/42.9%/0.23. Claude: 15.0%/15.0%/0.44. Kimi: 13.9%/13.9%/0.11. Tables written to `paper/tables/table3_level3_metrics.tex` and `paper/tables/table4_error_taxonomy.tex`.
- ~~Fill in error taxonomy table~~ DONE: E1/E2/E5 percentages extracted from foundry results. `tab:ft_errors` Base column populated in `paper/paper.tex`. VITL-RLHF column pending Azure fine-tuning completion.
- ~~Compute and present yield curves, partition sensitivity analysis~~ DONE: `difficulty_analysis.py`, `partition_sensitivity.py`, `statistics.py` all executed; JSON outputs regenerated under `experiments/results/`. NaN issue in `partition_sensitivity.json` fixed.
- Add figures (difficulty distribution histograms, yield curves, contamination gap visualization)

**Nice to have:**
- Complete Tier 3 instance generation from full YAGO 4.5
- Add Level 3 instances from automated defeater extraction at scale (GO NOT-qualifiers + Wikidata P2303)
- Symbolic ceiling evaluation via clingo ASP solver

### NeurIPS 2026 E&D Track Compliance

Verified against the [NeurIPS 2026 Main Track Handbook](https://neurips.cc/Conferences/2026/MainTrackHandbook) and [E&D Call for Papers](https://neurips.cc/Conferences/2026/CallForEvaluationsDatasets):

- **Page limit**: Main body (through Dataset Access, before bibliography) fits within 9 content pages. References, appendices, and checklist do not count. Camera-ready allows 10.
- **PDF structure**: Paper body, references, appendices (formal definitions, proofs, worked example, M5 details, datasheet), then NeurIPS Paper Checklist.
- **Style file**: `neurips_2026.sty` with `[eandd, nonanonymous]` (single-blind, permitted for dataset papers).
- **Croissant metadata**: `paper/croissant.json` includes both core and RAI fields per [Croissant RAI spec 1.0](https://docs.mlcommons.org/croissant/docs/croissant-rai-spec.html). Must be submitted alongside paper in OpenReview.
- **Code and data**: GitHub repo and HuggingFace dataset must be accessible to all reviewers without personal request at submission time. Code release is required since DeFAb is a reusable executable artifact.
- **Supplementary ZIP**: Recommended -- anonymized repo snapshot or build instructions for reviewers.
- **Contribution type on OpenReview**: General or Use-Inspired.
- **Compute reporting**: Separate OpenReview questionnaire (not part of page limit).
- **Checklist**: Completed in `dataset_paper.tex` -- 16 items, all answered (no TODOs remaining).

---

## Source Taxonomy

Sources are organized into four tiers by extraction priority and timeline.

### Tier 0: Currently Integrated (Baseline)

These are already in the codebase and generating instances.

| Source | Sponsor | Current Rules | Domain | Format |
|--------|---------|--------------|--------|--------|
| YAGO 4.5 | Télécom Paris (French govt) | 584 | Biology | TTL/TSV |
| WordNet 3.0 | NSF (Princeton) | 334 | Lexical | DB/RDF |
| LKIF Core | EU ESTRELLA Programme | 201 | Legal | OWL |
| MatOnto | US Materials Genome Initiative | 1,190 | Materials | OWL |

**Total current**: 2,318 rules, 374 instances (all Level 2)

---

### Tier 1: Cross-Ontology Core — NeurIPS Submission (Weeks 8-14)

The cross-ontology combination of a taxonomic source and a behavioral property source is the primary scale-up mechanism.

#### 1A. OpenCyc + ConceptNet 5.8 (Primary Cross-Ontology Pair)

**OpenCyc** (DARPA Strategic Computing Initiative, 1984)
- Scale: 239,000 terms, 2,093,000 triples
- Format: OWL, available on GitHub (therohk/opencyc-kb, 2012 final release)
- Role: **Taxonomy backbone** — provides canonical `IsA` hierarchies at 5-10 depth levels
- Key namespaces: biology (~50K concepts), chemistry (~30K), legal (~10K), medicine (~15K)

**ConceptNet 5.8** (MIT Media Lab / NSF, 2020 final release)
- Scale: 34 million edges, 10+ languages
- Format: CSV, JSON, API (api.conceptnet.io)
- Key relations for extraction:
  - `CapableOf` (~3M edges) → defeasible behavioral defaults
  - `NotCapableOf` (~300K edges) → **direct defeaters** for Level 3
  - `HasProperty` (~2M edges) → property defaults
  - `IsA` (~8M edges) → taxonomic supplement
  - `Causes` (~500K edges) → causal defaults
  - `UsedFor` (~1.5M edges) → functional defaults
- Role: **Behavioral property source** — what members of each class typically do/have

**Extraction algorithm**:
```
For each concept C in OpenCyc taxonomy:
  1. Traverse parent chain: C → parent → grandparent → ... → root
  2. For each ancestor A, harvest ConceptNet behavioral edges:
     - (A, CapableOf, P)     → P(X) :- A(X)    [DEFEASIBLE - inherited]
     - (A, HasProperty, P)   → P(X) :- A(X)    [DEFEASIBLE - inherited]
  3. Harvest concept-specific edges:
     - (C, CapableOf, P)     → P(X) :- C(X)    [DEFEASIBLE - specific]
     - (C, NotCapableOf, P)  → ~P(X) :- C(X)   [DEFEATER - Level 3 gold!]
  4. Generate strict rules from IsA edges:
     - (C, IsA, A)           → A(X) :- C(X)    [STRICT]
```

**Expected yield**:
- Biology: 100,000–220,000 rules, 10,000–20,000 defeaters
- Chemistry/Materials: 30,000–80,000 rules, 3,000–8,000 defeaters
- Legal: 15,000–40,000 rules, 1,500–4,000 defeaters
- Everyday/Common sense: 50,000–120,000 rules, 5,000–12,000 defeaters
- **Total Tier 1**: ~195,000–460,000 rules, ~20,000–44,000 defeaters
- **Instances**: 30,000–75,000 (Levels 1–3)

**Implementation status**: Domain-generic extractors and cross-ontology combiner implemented in `src/blanc/ontology/`. Validation script at `scripts/validate_cross_ontology_scale.py`. Domain profiles for all 5 domains in `src/blanc/ontology/domain_profiles.py`.
**Next action**: Download data files, run cross-ontology extraction for all domains

#### 1B. Full YAGO 4.5 (Supplement to Current Usage)

We currently use only 584 biology rules from YAGO. The full extraction potential is orders of magnitude larger.

- Scale: 50M+ entities, 90M+ facts, Wikidata + Schema.org base
- Available: yago-knowledge.org, TTL format
- Logical constraints enabled — reasoning-safe
- Biology taxonomy: full phylogenetic classification at species level
- New extraction: schema.org typed properties as defeasible rules
  - `schema:typicalAgeRange`, `schema:nutritionInformation`, `schema:material` → property defaults
- **Expected addition**: 50,000–500,000 new rules beyond current 584

---

### Tier 2: Medical and Biomedical Domain (2–6 Months Post-NeurIPS)

These three NIH-funded resources together constitute the most complete biomedical KB in existence.

#### 2A. UMLS 2025AA (NIH/NLM)

- Latest release: 2025AA (May 2025)
- Scale: 3.42 million concepts, 16.7 million unique concept names, 189 source vocabularies
- Semantic network: 127 semantic types, 54 semantic relations
- Format: RRF (Rich Release Format), downloadable with free research license
- Key features for DeFAb:
  - Semantic network encodes typed relations (e.g., `treats`, `causes`, `prevents`) — all defeasible
  - 189 source vocabularies means 189 cross-validated views of the same concepts → exception detection
  - Conflicting assertions across vocabularies are documented defeaters
- **Extraction approach**: Mine semantic relations as defeasible rules; mine inter-vocabulary contradictions as defeaters
- **Expected rules**: 500,000–2,000,000
- **Expected defeaters**: 50,000–200,000 (from inter-vocabulary conflicts)

#### 2B. SNOMED CT (IHTSDO / NHS / NLM — February 2026 Release Available)

- Scale: 360,000+ active concepts, hierarchical OWL ontology
- Format: OWL Functional Syntax, RF2 format, available with free research license
- Architecture: SubClassOf + EquivalentClasses axioms in OWL → maps to strict rules
- General Concept Inclusion (GCI) axioms encode necessary conditions → source of defeasible rules
- Key insight: SNOMED CT's OWL GCI axioms encode "necessary but not sufficient" class membership — exactly defeasible defaults
- Exception patterns: concepts that are subclasses of a parent but override a property (e.g., atypical presentations of diseases)
- **Extraction approach**: SubClassOf → strict rules; GCI axioms → defeasible rules; property exceptions → defeaters
- **Expected rules**: 200,000–600,000
- **Expected defeaters**: 20,000–80,000 (from GCI exceptions and atypical subclasses)

#### 2C. Gene Ontology 2026 (NIH + NSF)

- Scale: 50,000+ GO terms, 1M+ experimental annotations, 1,500+ GO-CAM causal activity models
- Format: OBO, RDF, GAF annotation files
- Important caveat: GO uses an **open-world assumption** — absence of annotation does not mean absence of function. This needs explicit handling in the extraction: we cannot generate negative rules from absent annotations, only from explicitly annotated NOT qualifiers.
- GO `NOT` qualifiers in annotations: gene product does NOT have this function → direct defeater source
- GO-CAM models: causal activity models encode process causality with conditional relations → causal defeasible rules
- **Extraction approach**: 
  - GO term hierarchy → taxonomic strict rules
  - Positive annotations → defeasible property rules (with appropriate confidence)
  - `NOT` qualifier annotations → defeaters
  - GO-CAM causal edges → causal defeasible rules
- **Expected rules**: 100,000–300,000
- **Expected defeaters**: 10,000–50,000 (from NOT-qualified annotations)

#### 2D. MeSH 2026 (NIH/NLM)

- Scale: ~30,000 descriptors, 280,000+ entry terms, 15+ hierarchical categories (A-Z tree)
- Format: XML, RDF
- Availability: Freely available without license
- Architecture: Pure taxonomy with 15 main branches (Anatomy, Diseases, Chemicals, etc.)
- Extraction: Taxonomic strict rules from hierarchy + pair with UMLS semantic relations for behavioral defaults
- Role: Provides clean hierarchy for medical taxonomy backbone (analogous to OpenCyc for biomedicine)
- **Expected rules (as taxonomy + UMLS cross-reference)**: 50,000–150,000

---

### Tier 3: Global Encyclopedic Knowledge (6–12 Months Post-NeurIPS)

#### 3A. Wikidata (Wikimedia Foundation — currently 16.6 billion triples)

This is the most important Tier 3 source. Key findings from research:

- Scale: 16.6 billion RDF triples (2025), 120.6 million entities, growing toward 20B
- Format: SPARQL endpoint (query.wikidata.org), JSON dumps, TTL dumps
- License: CC0 (public domain)
- **Critical discovery: Wikidata P2303 ("exception to constraint")**
  - P2302 (property constraint) encodes a rule: "entities of type X should have property Y"
  - P2303 (exception to constraint) encodes the defeater: "EXCEPT for entity E"
  - This is a community-curated, structured defeater database across ALL domains
  - Example: "countries should have exactly one capital" (P2302) with 15 documented exceptions (P2303)
  - Scale: Thousands of constraint-exception pairs across geography, law, biology, medicine, culture
  - **These are the highest-quality defeaters available in any public KB**
- **Wikidata qualifiers as defeaters**: temporal qualifiers (P580/P582 start/end time) encode temporal exceptions; P1480 (sourcing circumstances) encodes epistemic uncertainty
- **Wikidata WikiProject Reasoning**: active community defining inference rules — can mine their constraint system
- **Extraction approach**:
  - Mine P2302/P2303 pairs as (defeasible rule, defeater) pairs directly
  - Extract `instanceof` + property assertions → defeasible rules per domain
  - Use WikiProject Reasoning constraint templates as rule schemas
  - Apply domain filters via `instanceof` type hierarchy
- **Expected rules**: 2,000,000–10,000,000 (full extraction, all domains)
- **Expected defeaters**: 50,000–500,000 (from P2303 alone, plus qualifier-based exceptions)
- **NeurIPS scope**: 200,000–1,000,000 rules from 3 focused domains

#### 3B. DBpedia (University of Leipzig / FU Berlin — continuous monthly releases)

- Scale: Monthly extraction from ~140 language Wikipedias; English alone: 3B+ triples
- Format: RDF/N-Triples, Databus platform, monthly releases
- Architecture: Mappings-based extraction (high quality, ~40 languages) + generic extraction
- Key relation types: `dbo:` ontology properties → defeasible rules
- Complement to Wikidata: DBpedia extracts from Wikipedia infoboxes while Wikidata is structured directly
- **Extraction approach**: Map DBpedia ontology properties to defeasible rules via type hierarchy; inconsistencies between infobox data and ontology constraints → defeaters
- **Expected rules**: 1,000,000–5,000,000

#### 3C. BabelNet 5.3 (European Research Council, Sapienza University Rome — December 2023)

**Corrected scale** (larger than previously documented):
- 23 million synsets (entries), not 13.8M
- 600 languages (not 272 — expanded 80 new languages in v5.3)
- 1.9 billion semantic relations
- 159.7 million definitions
- 61.4 million images
- Integrates 53 knowledge sources: WordNets (multiple languages), Wikipedia, Wikidata, Wiktionary, VerbAtlas, ImageNet, FrameNet, and more

This makes BabelNet uniquely valuable for **multilingual defeasibility**: the same rule expressed in 600 languages with the same formal backing, enabling multilingual evaluation of the benchmark.

- **Extraction approach**: BabelNet synset relations → defeasible rules; cross-language inconsistencies → defeaters; FrameNet frames embedded in BabelNet → event default structure
- **Expected rules**: 500,000–2,000,000 (English alone); 10M+ (all 600 languages)
- **For NeurIPS**: Use as English supplement and multilingual validation layer

---

### Tier 4: Web-Scale and Archived Sources (1–2 Years Post-NeurIPS)

#### 4A. NELL (DARPA/NSF, Carnegie Mellon — available on Hugging Face as rtw-cmu/nell)

- Scale: 50M+ beliefs (v1115), 2.8M high-confidence; 100M+ candidate beliefs
- Format: Available on Hugging Face (rtw-cmu/nell), tabular
- Quality: ~3% high confidence; quality filtering essential
- Architecture: Confidence-weighted relation triples (entity, relation, entity)
- **Extraction approach**: Filter by confidence > 0.95; extract relation patterns as defeasible rules; conflicting high-confidence assertions → defeaters
- **Expected high-quality rules**: 1,000,000–5,000,000 (after filtering)

#### 4B. Freebase (Google, archived 2016 — CC-BY license)

- Scale: 1.9 billion triples (22 GB gzipped), 72.4M nodes, 306.7M edges, 4,335 edge types
- Available: developers.google.com/freebase (permanent archive, CC-BY)
- Note: ~60% redundancy per processing methodology (Freebase-triples paper)
- **Extraction approach**: Map Freebase compound value types to defeasible rules; type constraints → rules; exceptions in compound values → defeaters
- **Expected rules**: 5,000,000–20,000,000 (quality filtered)

#### 4C. SUMO (DoD / IEEE — actively maintained on GitHub ontologyportal/sumo as of Feb 2026)

- Scale: 20,000 terms, 60,000 axioms (SUO-KIF), 288,000 nodes, 496,000 edges total
- Format: SUO-KIF (higher-order logic), OWL conversion available
- Active development: GitHub activity as of February 2026
- Sigma Knowledge Engineering Environment: web interface for browsing
- Military and government domain concepts well-covered
- **Extraction approach**: SUO-KIF axioms → defeasible rules (those with `=>` vs `:- ` semantics); contradictions in military/legal domain → defeaters
- **Expected rules**: 30,000–80,000

#### 4D. FrameNet (NSF / Berkeley ICSI — FrameNet 1.7)

Not in current documentation but relevant:
- Scale: 1,224 frames, 13,640 lexical units, 202,000+ annotated sentences
- Format: XML, available freely
- Architecture: Each frame defines a situation type with core and non-core frame elements — the distinction between core (obligatory) and non-core (optional) elements maps to strict vs. defeasible argument structure
- Key insight: FrameNet's "default fillers" and "selectional restrictions" are exactly defeasible defaults about event participants
- **Extraction approach**: Frame inheritance hierarchy → strict rules; selectional restrictions → defeasible constraints; frame-to-frame "Inherits from" + "Is Inherited by" with exceptions → defeater patterns
- **Expected rules**: 50,000–200,000

---

### Tier 5: Historical Programs (Best-Effort, Multi-Year)

These require archival research to locate artifacts.

#### 5A. Fifth Generation Computer Systems / ICOT (Japan MITI, 1982–1993)

- Status: ICOT archives partially available through NIST and academic institutions
- Content: Prolog programs, parallel logic (KL1), application KBs
- Formats: Prolog, FGCS-era data structures
- Extraction: Manual curation of accessible Prolog programs → defeasible theories
- **Expected rules**: Unknown; estimate 10,000–50,000 if artifacts located

#### 5B. Alvey Programme (UK DTI, 1983–1990, £200M budget)

- Status: Artifacts scattered; some IKBS demonstrator programs in British Library and university archives
- Content: Expert systems, IKBS demonstrators in legal reasoning, medical diagnosis
- Formats: Various Prolog-based
- **Expected rules**: Unknown; estimate 5,000–30,000

#### 5C. ESPRIT (European Commission, 1983–1993)

- Key projects with accessible artifacts: KADS (knowledge acquisition), NOMOS (legal knowledge)
- KADS: Methodology for knowledge engineering — problem-solving models
- NOMOS: Legal knowledge representation — particularly valuable for our legal domain
- **Expected rules**: 10,000–50,000 from accessible artifacts

---

## Defeater Sources: A Structured Map

Defeaters are the critical ingredient for Level 3 instances. Here is every identified source of structured defeaters:

| Source | Defeater Mechanism | Count Estimate | Quality | Priority |
|--------|-------------------|----------------|---------|----------|
| ConceptNet `NotCapableOf` | Explicit behavioral exceptions | 300K edges | Medium (crowdsourced) | Tier 1 |
| Wikidata P2303 | Documented constraint exceptions | 10K–100K pairs | **Very High** (community-curated) | Tier 3 |
| UMLS inter-vocabulary conflicts | Cross-vocabulary contradictions | 50K–200K | High (expert-curated) | Tier 2 |
| SNOMED CT GCI exceptions | OWL necessary condition exceptions | 20K–80K | **Very High** (clinical expert) | Tier 2 |
| Gene Ontology NOT qualifiers | Explicitly annotated non-functions | 10K–50K | **Very High** (experimental) | Tier 2 |
| YAGO constraint violations | Schema.org constraint exceptions | 5K–50K | High | Tier 1 |
| DBpedia ontology contradictions | Infobox vs. ontology inconsistencies | 50K–500K | Medium | Tier 3 |
| NELL conflicting high-conf beliefs | Contradiction in learned beliefs | 100K–1M | Medium (needs filtering) | Tier 4 |
| FrameNet selectional violations | Non-typical frame element fillers | 10K–50K | High | Tier 4 |

**Total structured defeaters available**: 555,000–2,030,000  
**For NeurIPS (ConceptNet + YAGO constraints)**: 305,000–400,000 candidate defeaters

---

## Extraction Algorithm for Each Defeater Source

### ConceptNet NotCapableOf → Level 3 Instances

```python
for (concept, NotCapableOf, property) in conceptnet.filter(relation='NotCapableOf'):
    # Find the corresponding default rule
    default = find_inherited_default(concept, property, taxonomy)
    if default is None:
        continue  # No rule to defeat, skip
    
    # Verify anomaly structure (Definition def:anomclass in paper)
    if not D_minus.proves_defeasible(complement(property)(concept)):
        continue  # Not a genuine anomaly, skip
    
    # Create Level 3 instance
    defeater = Rule(head=NOT(property(X)), body=[concept(X)], type=DEFEATER)
    yield Level3Instance(
        challenge_theory=D_minus,
        anomaly=property(concept),
        gold_defeater=defeater,
        novelty=Nov(defeater, D_minus)
    )
```

### Wikidata P2303 → Level 3 Instances

```sparql
SELECT ?property ?constraint ?exception WHERE {
  ?property p:P2302 ?constraintStatement .
  ?constraintStatement ps:P2302 ?constraint ;
                        pq:P2303 ?exception .
}
```

This SPARQL query directly extracts (rule, defeater) pairs:
- The property constraint is the defeasible rule
- The exception (P2303) is the defeater
- This is the highest-quality automatic defeater source available

### SNOMED CT GCI Exceptions → Level 3 Instances

```
For each concept C with GCI axiom: (A and R some V) SubClassOf C
where V conflicts with C's primary classification:
  → C(X) is the anomaly (C belongs to class that expects NOT-V)
  → GCI axiom body is the defeater condition
```

---

## Phased Implementation Timeline

### Phase 0: Current State (Week 12, DONE)
- Sources: YAGO, WordNet, LKIF, MatOnto
- Strict taxonomic rules: 2,318
- Defeasible behavioral rules: 482 (biology 220, legal 118, materials 144)
- Defeaters: 244 (biology 94, legal 76, materials 74)
- Superiority relations: 55 (biology 25, legal 15, materials 15) -- lex specialis
- Multi-body compound rules: 70 (biology 30, legal 20, materials 20) -- derivation depth 2+
- Total rules: 3,044
- Entity instances: 261 (biology 135, legal 61, materials 65)
- Instances: 374 (Level 2) + 35 (Level 3)
- Full Def 3.2 quintet: F, R_s, R_d, R_df, succ all populated
- Infrastructure: domain profiles (5 domains), generalized extractors (ConceptNet + OpenCyc), cross-ontology combiner, rule validation framework

### Phase 1a: Cross-Ontology Proof (Day 8.5a, 1 day)
- Script: `scripts/validate_cross_ontology_scale.py`
- Goal: Validate 10x scale is achievable from sample
- Decision gate: ≥5,000 rules from 1K concepts sample

### Phase 1b: Cross-Ontology Full Extraction (Week 8.6, 1 week)
- Sources: OpenCyc + ConceptNet (all domains)
- New rules: 100,000–350,000
- New defeaters: 20,000–44,000
- New Level 3 instances: 3,000–15,000 (automated)
- New Level 1 instances: 15,000–35,000
- New Level 2 instances: 15,000–40,000
- **Total NeurIPS target: 33,000–90,000 instances**

### Phase 2: Medical Domain (Months 2–6 post-NeurIPS)
- Sources: UMLS 2025AA, SNOMED CT (Feb 2026), Gene Ontology 2026, MeSH 2026
- New rules: 850,000–3,050,000
- New defeaters: 80,000–330,000
- New instances: 130,000–480,000
- New domains: Diseases, drugs, anatomy, genetics, molecular biology

### Phase 3: Encyclopedic Layer (Months 6–12 post-NeurIPS)
- Sources: Wikidata (with P2303), DBpedia, BabelNet 5.3
- New rules: 3,000,000–15,000,000
- New defeaters: 100,000–1,000,000 (P2303 alone is 10K–100K pairs)
- New instances: 480,000–2,400,000
- New feature: Multilingual evaluation (600 languages via BabelNet)

### Phase 4: Web-Scale (Months 12–24 post-NeurIPS)
- Sources: NELL, Freebase, SUMO, FrameNet, full YAGO/DBpedia
- New rules: 6,000,000–25,000,000
- New instances: 960,000–4,000,000
- Cumulative total: ~1,570,000–6,870,000 instances

### Phase 5: Historical Completion (Multi-year)
- Sources: FGCS artifacts, Alvey, ESPRIT, ResearchCyc (if licensed)
- Estimated addition: 25,000–130,000 rules
- Goal: Complete the historical government AI program coverage

---

## Cumulative Scale by Phase

| Phase | New Rules | Cumulative Rules | New Instances | Cumulative Instances |
|-------|-----------|-----------------|---------------|---------------------|
| 0 (current) | — | 2,318 | — | 374 |
| 1 (NeurIPS) | 100K–350K | 102K–352K | 33K–90K | 33K–90K |
| 2 (Medical) | 850K–3M | 952K–3.35M | 130K–480K | 163K–570K |
| 3 (Encyclopedic) | 3M–15M | 3.95M–18.35M | 480K–2.4M | 643K–2.97M |
| 4 (Web-scale) | 6M–25M | 9.95M–43.35M | 960K–4M | 1.6M–6.97M |
| 5 (Historical) | 25K–130K | ~10M–43.5M | 4K–21K | ~1.6M–7M |

**Multiplier from current to Phase 1 (NeurIPS)**: ~88x to ~240x  
**Multiplier from current to Phase 3**: ~1,700x to ~7,900x  
**Multiplier from current to full**: ~4,300x to ~18,700x

---

## Domain Coverage Map

| Domain | Primary Sources | Tiers | Defeasible Default Examples | Defeater Examples |
|--------|----------------|-------|----------------------------|-------------------|
| Biology (taxonomy) | OpenCyc+ConceptNet, YAGO | 1 | `flies(X) :- bird(X)` | `~flies(X) :- penguin(X)` |
| Biology (molecular) | Gene Ontology | 2 | `catalyzes_reaction(X) :- enzyme(X)` | `NOT` qualifiers |
| Chemistry | OpenCyc+ConceptNet, MatOnto | 1 | `conductive(X) :- metal(X)` | `~conductive(X) :- insulator_metal(X)` |
| Materials | MatOnto, OpenCyc+ConceptNet | 1 | `brittle(X) :- ceramic(X)` | `~brittle(X) :- metallic_glass(X)` |
| Legal | LKIF, OpenCyc+ConceptNet | 1 | `can_contract(X) :- adult(X)` | `can_contract(X) :- emancipated_minor(X)` |
| Medicine | UMLS, SNOMED CT | 2 | `treated_by(X, antibiotic) :- bacterial_infection(X)` | GCI exceptions |
| Geography | Wikidata, OpenCyc | 3 | `has_one_capital(X) :- country(X)` | P2303 (15 exceptions) |
| Social | Wikidata, DBpedia | 3 | `votes(X) :- adult_citizen(X)` | Felon disenfranchisement |
| Everyday | ConceptNet, BabelNet | 1,3 | `floats(X) :- wood(X)` | `~floats(X) :- waterlogged_wood(X)` |
| Multilingual | BabelNet (600 langs) | 3 | All of above in 600 languages | Language-specific exceptions |
| Military/Govt | SUMO, Wikidata | 3,4 | Domain-specific defaults | Jurisdictional exceptions |
| Events/Actions | FrameNet | 4 | Default frame element fillers | Selectional violations |

---

## Key Technical Decisions for Extraction

### Quality Filtering Thresholds

| Source | Confidence/Quality Filter | Rationale |
|--------|--------------------------|-----------|
| ConceptNet | Weight ≥ 3.0 (for rules), ≥ 2.0 (for defeaters) | Crowdsourced; moderate threshold |
| Wikidata P2303 | No filtering needed | Community-curated exceptions |
| UMLS | Source vocabulary reliability rank ≥ 0.7 | Cross-vocabulary validation |
| SNOMED CT | All axioms (expert-curated) | Highest quality, no filtering |
| Gene Ontology | Evidence code NOT {ND, IEA} for defeaters | Exclude "no data" and electronic inferences |
| NELL | Confidence ≥ 0.95 | Web-learned; strict threshold |
| DBpedia | Mappings-based only (exclude generic extractor) | Mappings are human-curated |

### Derivation Depth Requirement

Per paper Definition def:levels12: instances must have dependency depth ≥ 2. This requires:
- At least one intermediate rule between the base fact and the target conclusion
- Achievable for all sources with IsA + property pattern (IsA gives depth, property gives the target)
- Must be verified per-instance by the generation pipeline

### Type-Grounded Partition (New Structured Family)

When rules are generated from typed relations, the relation type provides a natural partition function κ:
- `IsA` relation → strict rule (κ = s)
- `CapableOf`, `HasProperty`, UMLS semantic relation → defeasible rule (κ = d)
- `NotCapableOf`, P2303, Gene Ontology NOT qualifier → defeater (κ = df)

This is a fifth structured partition family alongside the four defined in Definition def:structpart (paper line 587-593). It should be added to the paper.

---

## Paper Integration Points

### New Related Work Citation Required

**DEFREASING** (Allaway and McKeown, NAACL 2025):
- 95K questions, ~8K inheritance rules, tests defeasible property inheritance in LLMs
- Key differentiator: DEFREASING tests whether a property *still holds* given new information (classification task using generics). DeFAb requires models to *construct* the exception rule from scratch, verify conservativity (AGM minimal change), and measure the novelty of the constructed hypothesis. DeFAb also uses formally verified gold standards derived from complete defeasible theories, not human annotation.
- Must be added to related work with clear differentiation

**LLM-ORBench** (ICLR 2026):
- Evaluates LLMs on ontology-based reasoning with SPARQL
- Differentiator: LLM-ORBench evaluates forward deductive inference from ontologies. DeFAb evaluates abductive hypothesis generation under defeasibility.

### Paper Section Updates (Summary)

1. **Abstract**: Add "across N knowledge bases spanning government AI initiatives from the 1980s through modern encyclopedic projects"
2. **Introduction lines 185–217**: Extend the government KB narrative beyond Cyc/FGCS/Alvey to include modern programs (NIH, NSF, EU ERC, Wikidata)
3. **Related Work**: Add DEFREASING and LLM-ORBench citations with differentiators
4. **Section 3.1 (Source KBs)**: Describe the phased KB architecture; mention P2303 as a Wikidata defeater source
5. **Section 3.2 (Conversion)**: Add type-grounded partition as fifth structured family
6. **Section 3.3 Level 3 bullet**: Replace "hand-authored" with automated extraction from ConceptNet NotCapableOf and Wikidata P2303
7. **Contributions list**: Add fifth contribution for cross-ontology KB extraction methodology
8. **Section 4.3 statistics**: Add confidence-threshold yield curves for quality-volume tradeoff

---

## File Structure for Implementation

```
src/blanc/ontology/
  domain_profiles.py            # DONE - 5 domain profiles (biology, legal, materials, chemistry, everyday)
  opencyc_extractor.py          # DONE - domain-generic, accepts DomainProfile
  conceptnet_extractor.py       # DONE - domain-generic, 6 relation types (IsA, CapableOf, NotCapableOf, HasProperty, Causes, UsedFor)
  cross_ontology.py             # DONE - taxonomy + property combination, inheritance, defeater detection
  rule_validator.py             # DONE - depth, dedup, consistency, anomaly, coverage
  yago_full_extractor.py        # Tier 1 supplement - create
  umls_extractor.py             # Tier 2 - create (post-NeurIPS)
  snomed_extractor.py           # Tier 2 - create (post-NeurIPS)
  gene_ontology_extractor.py    # Tier 2 - create (post-NeurIPS)
  mesh_extractor.py             # Tier 2 - create (post-NeurIPS)
  wikidata_extractor.py         # Tier 3 - create (post-NeurIPS)
  wikidata_p2303_defeaters.py   # Tier 3 - create (post-NeurIPS)
  dbpedia_extractor.py          # Tier 3 - create (post-NeurIPS)
  babelnet_extractor.py         # Tier 3 - create (post-NeurIPS)
  nell_extractor.py             # Tier 4 - create (1+ year)
  freebase_extractor.py         # Tier 4 - create (1+ year)
  sumo_extractor.py             # Tier 4 - create (1+ year)
  framenet_extractor.py         # Tier 4 - create (1+ year)

scripts/
  validate_cross_ontology_scale.py      # Tier 1 proof - EXISTS
  extract_cross_ontology_biology.py     # Tier 1 full - create
  extract_cross_ontology_legal.py       # Tier 1 full - create
  extract_cross_ontology_materials.py   # Tier 1 full - create
  extract_wikidata_p2303.py             # Tier 3 defeaters - create later
  extract_umls_medical.py               # Tier 2 - create later

src/blanc/codec/
  image_manifest.py              # DONE - EntityImage, ImageManifest data model for M5
  m5_encoder.py                  # DONE - M5 visual grounding encoder (replace + supplement variants)

src/blanc/ontology/
  image_harvester.py             # DONE - Wikidata P18, VisualSem, BabelNet image harvesters

scripts/
  download_entity_images.py      # DONE - multi-source image download orchestrator
  analyze_image_coverage.py      # DONE - per-domain image coverage analysis

Guidance_Documents/
  COMPREHENSIVE_KB_PIPELINE.md   # THIS DOCUMENT
  CROSS_ONTOLOGY_PLAN.md         # Tier 1 detail (existing)
  ALL_GOVERNMENT_KBS.md          # Full inventory (existing, update)
```

---

## M5 Visual Grounding Modality (Implemented 2026-04-03)

DeFAb now supports a fifth rendering modality (M5) that presents defeasible reasoning instances with visual entity grounding. This is a strictly additive extension: M1-M4 behavior is unchanged.

### Design

M5 keeps theory rules, target, and candidates in M4 (pure formal) textual format. The extension is that entity-grounding facts can be paired with or replaced by images sourced from external knowledge bases. Two variants:

- **M5-replace**: Entity facts use images instead of names. The model must perceive and classify the entity from the image alone.
- **M5-supplement**: Entity facts retain textual names alongside images as supporting context.

### Image Sources

1. **Wikidata P18** (property "image"): SPARQL-queryable, broadest entity coverage. Thumbnail URLs at configurable resolution.
2. **VisualSem** (iacercalixto/visualsem): 938K images across 90K nodes bridging WordNet and BabelNet synsets. Downloadable.
3. **BabelNet 5.3** (REST API): 61.4M images, requires API key. Lower priority.

### Infrastructure

- `ImageManifest` (`src/blanc/codec/image_manifest.py`): JSON-serializable index mapping entity names to images with source preference ranking and Theory coverage computation.
- `WikidataImageHarvester`, `VisualSemBridge`, `BabelNetImageHarvester` (`src/blanc/ontology/image_harvester.py`): Source-specific harvesters producing ImageManifest output.
- `encode_m5` (`src/blanc/codec/m5_encoder.py`): Encoder producing `MultimodalPrompt` with text and `PromptImage` references.
- `query_multimodal` (`experiments/model_interface.py`): Non-abstract method on `ModelInterface` base class with provider-specific overrides for OpenAI, Anthropic, and Foundry endpoints.
- `ResponseCache.make_key` extended with optional `image_hashes` parameter.
- `render_prompt` and `evaluate_single` updated to route M5 instances through multimodal pipeline.

### Backward Compatibility

All changes are strictly additive. Existing M1-M4 evaluation, text-only model queries, cache keys, and decoder behavior are byte-for-byte unchanged. The `[vision]` optional dependency group in pyproject.toml keeps image libraries (Pillow, requests, sparqlwrapper) separate from core requirements. 58 new tests verify M5 functionality; all 1301 pre-existing tests continue to pass.

### Related Work

- **VISaGE** (EMNLP 2025): Visual generics and exceptions -- VLMs fail on atypical instances, exactly the defeasible case. DeFAb-M5 provides formally verified complement.
- **Black Swan** (CVPR 2025, Chinchure et al.): Abductive and defeasible video reasoning with crowdsourced evaluation. DeFAb-M5 offers verifier-backed gold standards.
- **AbductiveMLLM** (AAAI 2026 Oral): Cross-modal causal alignment for visual abduction. Complementary architecture.
- **PhenoLIP** (2026): Phenotype ontology grounding for medical VLMs. Validates the KB-to-vision bridge for biomedical domain.
- **Babel-ImageNet** (ACL 2024): BabelNet/WordNet synset to ImageNet mapping. Infrastructure DeFAb leverages directly.

---

## Research Notes from Internet Search (2026-02-18)

Key findings that affect implementation:

1. **ConceptNet is stable at v5.8 (2020)** — no new releases. Use as-is. 34M edges confirmed.

2. **BabelNet 5.3 is larger than documented in our files** — 23M synsets, 1.9B relations, 600 languages (our docs said 13.8M synsets, 272 languages — these were v5.2 figures). Update all references.

3. **Wikidata P2303** ("exception to constraint") is a structured defeater source not previously in any of our documents. SPARQL-queryable. High quality. Should be added as a named defeater source alongside ConceptNet NotCapableOf.

4. **OpenCyc is from 2012** — the project is no longer actively developed. The 2012 OWL file is available on GitHub (therohk/opencyc-kb). This does not affect usability but clarifies what "OpenCyc" refers to.

5. **SNOMED CT February 2026 release** is available and integrates into UMLS. The OWL GCI axioms are a rich source of defeasible rules not previously considered in our plan.

6. **Gene Ontology uses open-world assumption** — we cannot infer negative rules from absent annotations. Only explicit `NOT` qualifier annotations are valid defeaters.

7. **DEFREASING** (NAACL 2025, Allaway and McKeown): 95K question defeasible reasoning benchmark. Must be cited and differentiated from in the paper's related work section.

8. **LLM-ORBench** (ICLR 2026): Ontology-based reasoning benchmark. Must be cited.

9. **NELL available on Hugging Face** as `rtw-cmu/nell` — confirmed accessible.

10. **Freebase dumps** still available under CC-BY at developers.google.com/freebase — confirmed.

11. **SUMO actively maintained** on GitHub (ontologyportal/sumo, Feb 2026 activity).

12. **Cyc commercial product** — 25M+ assertions, 40K predicates, but ResearchCyc requires licensing. OpenCyc (239K terms) is the accessible portion.

---

**Maintained by**: Patrick Cooper  
**Next update**: After dataset paper submission (May 6, 2026)  
**See also**: `paper/dataset_paper.tex` (the dedicated NeurIPS 2026 E&D submission), `Guidance_Documents/GOOGLE_ORG_APPLICATION.md` (Google.org grant application draft)

**Recent progress (2026-04-22, fourth pass)**:
- Venue and style-file conformance pass on all three papers. Copied the user's freshly downloaded `neurips_2026.sty` into `paper/` (overwriting the prior copy of identical size to guarantee provenance from the official January 2026 release). `paper/games_for_discovery.tex`: converted the standalone working-note preamble (`\documentclass[11pt]{article}` + `\usepackage[margin=1in]{geometry}`) to NeurIPS 2026 preprint format (`\documentclass{article}` + `\usepackage[preprint]{neurips_2026}`); removed the `\setlength{\parskip}{6pt}`, `\setlength{\parindent}{0pt}`, and `\pagestyle{empty}` hacks (the NeurIPS style controls these); added `\usepackage{url}`; replaced the manual centered title block (`\begin{center}{\Large\bfseries Defeasible Games}...\end{center}\hrule`) with proper `\title{Defeasible Games: Verifier-Backed Preference Optimization, Self-Play, and Neural-Guided Tree Search for Defeasible Reasoning}`, `\author{Patrick Cooper, CU Boulder}`, `\maketitle`, and a substantive `\begin{abstract}...\end{abstract}` covering the four main contributions of the working note (defeasible-conflict games, GRPO self-play, theory-construction MDP with Active Inference vs.\ neural-guided MCTS, AlphaGo-lineage instantiation, DeFAb-Hard pre-registration). All section content from `\section{Core Idea}` onward, including the embedded `\begin{thebibliography}{99}` block, preserved unchanged. `paper/dataset_paper.tex`: verified existing `\usepackage[eandd, nonanonymous]{neurips_2026}` invocation against the freshly copied style file; confirmed `\answerYes` / `\answerNo` / `\answerNA` macros required by the NeurIPS Paper Checklist are defined at lines 378--381 of the style file. No edits required. `paper/paper.tex`: switched the documentclass setup from `\usepackage{neurips_2025}` (which does not exist locally and was preventing compilation) to `\usepackage{tmlr}` targeting Transactions on Machine Learning Research as the journal-of-record appropriate to the manuscript's length (~80 typeset pages with extensive appendices), scope (combined theoretical-empirical ML/AI contribution), and license (open access matches the MIT-licensed dataset). Added a structured documentation block explaining the venue choice, the path to acquire `tmlr.sty` from `https://jmlr.org/tmlr/author-guide.html`, and a fully-specified standalone-preprint fallback (`\usepackage[margin=1in]{geometry}` + `\usepackage{times}` + `\usepackage[round,sort]{natbib}`) for environments where `tmlr.sty` is unavailable. Preserved the entire original NeurIPS 2025 commentary block as comments under a "Historical NeurIPS submission notes (preserved for record)" header so nothing was removed. Converted the `\author{...}` block to TMLR's `\name` / `\email` / `\addr` convention with `\editor{Submitted to TMLR}`, retaining the previous NeurIPS-style `\author` block as a commented fallback for the standalone-preprint path. The `\usepackage[margin=1in]{geometry}` line that conflicts with TMLR's own page geometry was commented out, with a note explaining that it is preserved for the fallback path. All three files lint clean; all substantive content (sections, definitions, propositions, theorems, appendices, bibliography, NeurIPS Paper Checklist) preserved unchanged. Strategic effect: the three papers now have correctly differentiated venues --- `paper.tex` is journal-bound (TMLR, no length limit), `dataset_paper.tex` is the NeurIPS 2026 E&D Track submission (single-blind, 9-page main body), `games_for_discovery.tex` is a NeurIPS 2026 preprint companion document for archival distribution.

**Recent progress (2026-04-22, third pass)**:
- DeFAb-Hard pre-registration. Strengthened the existing `\subsection{DeFAb-Hard: Pre-Registered Difficulty Hardening}` in `paper/paper.tex` with a cross-axis intersection cell (DeFAb-Hard-NovScaleMulti = H1 high-novelty $\cap$ H2 scaled-depth $\cap$ H3 multi-anomaly) plus a fifth pre-registered hypothesis H_HARD ($\geq$30 pp drop on the intersection cell relative to the easy 35-instance baseline) and added "actual count after generation: -- (TBD)" placeholders for each axis. Added new `\subsection{DeFAb-Hard Results}\label{subsec:defab_hard_results}` immediately before the fine-tuning section, with a placeholder Table:defab_hard reporting rendering-robust L3 accuracy across {Easy, H1, H2, H3, H4, intersection} columns for the four-model panel and the predicted ceilings ($\leq$53% on H1, $\leq$78% on H4, $\leq$63% on intersection). Reporting commitments enumerated (Wilson 95% CI, McNemar, error-class distribution with attention to E4, graded-score distribution, $\Delta_\mathrm{synth}$ bootstrap CI on H4). Discussion paragraph "Belief revision capability is latent, not absent" rewritten to scope its claim to the easy subset and forward-reference the DeFAb-Hard subset as the headline empirical question for the next revision. Conclusion extended with an analogous scoping clause. Dataset paper got a compact mirror: a `DeFAb-Hard: pre-registered difficulty hardening` paragraph in §5 (Dataset Statistics), an under-sampling acknowledgment paragraph in §7 (Discussion), and a Datasheet Composition extension noting the planned 1{,}000 + 300 + 100 + $\geq$50 instance targets with TBD actual counts. games_for_discovery.tex got a new `\subsubsection{DeFAb-Hard as the Proper Evaluation Surface}` arguing that the AlphaZero pipeline must be evaluated on DeFAb-Hard rather than on the saturated easy set, plus two new open-questions items (does AlphaZero-style training close the H_HARD gap; what is the difficulty-vs-search-budget Pareto front per axis). All three .tex files lint clean; new labels (`subsec:defab_hard_results`, `tab:defab_hard`) defined and cross-referenced; existing `subsec:defab_hard` reused. Strategic stance: the paper is conditional on completing DeFAb-Hard generation and evaluation; the headline shifts from the 92.9% DeepSeek-R1 CoT figure on the easy set to the H_HARD intersection-cell figure once that figure exists. The objective is to identify the difficulty boundary at which current frontier models reproducibly fail under the strongest available prompting strategy, and only then to test whether the fine-tuning pipeline or neural-guided tree search closes that gap.

**Recent progress (2026-04-22, second pass)**:
- Games-as-tree-search-informed RLVR expansion. Drew on Silver et al.\ 2016 (Nature 16961, AlphaGo) and Silver et al.\ 2017 (Nature 24270, AlphaGo Zero) to expand the neural-guided tree search treatment in both `paper/games_for_discovery.tex` and the matching `\subsection{Neural-Guided Tree Search}` of `paper/paper.tex`. Ten new subsubsections added to each (strictly additive): two-principle (depth/breadth) search-space reduction with branching-factor comparison (Go b ~250 vs defeasible b ~10^12), mixed leaf evaluation V(s_L) = (1-lambda) v_phi + lambda z_L with the exact polynomial-time verifier as deterministic z_L (strict strengthening over AlphaGo's stochastic rollout), the AlphaZero loss l = (z-v)^2 - pi^T log p + c||theta||^2 adapted to the defeasible setting (with the AGZ Fig.4 dual-res / sep-conv ~1200 Elo ablation as architectural prior), classical policy-iteration framing of expert iteration with the >55% AGZ evaluator acceptance gate, diversity-vs-sharpness policy prior insight (SFT vs DPO/GRPO as MCTS prior), MCTS engineering details (virtual loss n_vl=3, Dirichlet noise eta~Dir(0.03) eps=0.25, temperature schedule, resignation threshold), asynchronous APV-MCTS architecture mapped to CURC Alpine, explicit Defeasible AlphaZero domain-knowledge enumeration (derivation rules, verifier, theory-state encoding, predicate-renaming invariance), tabula-rasa feasibility grounded in branching-factor numbers, and a dual-head vs separate-network architecture ablation plan. Two new open-questions added to each file (mixed-evaluation tradeoff under exact verification; tabula-rasa transfer between knowledge bases). Conclusion of `paper.tex` extended with one clause noting that the unified pipeline instantiates the AlphaGo lineage. All 10 new labels (`subsubsec:{two-principle, mixed-leaf, agz-loss, policy-iter, diversity-prior, mcts-engineering, async-apvmcts, domain-knowledge, tabula-rasa, arch-ablation}`) defined and cross-referenced; no new bib entries required (`silver2016alphago`, `silver2017alphagozero`, `silver2018alphazero` already at lines 1028-1050 of `references.bib`); both `.tex` files lint clean.

**Recent progress (2026-04-22)**:
- Paper-currency pass on `paper/paper.tex` and `paper/dataset_paper.tex`: strictly additive revisions bringing both papers into alignment with completed work through April 2026. Added a new Tier~RTS row to `tab:kbsummary` in both papers (rts_engagement / lux_ai_s3 / sc2live, +478 rules, +246 instances; updated materialized totals to 4,285,606 / 33,751,188 rules and 372,648+ instances). Added new subsections to `paper.tex` for the Live StarCraft~II grounding bridge (`subsec:sc2live`, ObservationLifter / ActionCompiler / ReplayTraceExtractor / DeFAbBot), the Lux~AI~S3 parallel game-grounded KB, the ROE compliance B0/B1/B2 verifier-gated commander policy experiment (`subsec:roe-compliance`, three formal hypotheses H_GATE / H_COST / H_REPROMPT, 79 regression tests, both quiz and live backends), the populated Experiment~2 RTS-engagement Level~3 results (`subsec:rts-eval-results`, `tab:rts_eval`: GPT-5.2 75% / DeepSeek-R1 50% / Claude 41.7% / Kimi 25% on six L3 seeds), and the cross-environment transfer experiment (`subsec:cross-env-transfer`, six-environment registry, H5 hypothesis). Added an Azure Spot orchestration hardening paragraph to the fine-tuning Experimental Design section citing the four regression test files. Extended the `paper.tex` abstract and conclusion plus the `dataset_paper.tex` abstract, Tier~2 paragraph, Datasheet (Composition / Uses), and NeurIPS Paper Checklist (New assets) to reference the Tier~RTS additions. Pre-existing typo where the Limitations sentence "the Tier~1 dataset (3" was orphaned from "24K instances)" reunified as "(324,511 instances)". Both `.tex` files lint clean; all new labels (`subsec:sc2live`, `subsec:roe-compliance`, `subsec:rts-eval-results`, `subsec:cross-env-transfer`, `tab:rts_eval`) defined and referenced consistently.

**Recent progress (2026-04-20)**:
- Closed the fourth defect this day: a truncated-checkpoint crash loop after the first preemption. When SIGTERM interrupts the Hugging Face Trainer mid-checkpoint-write (which is exactly what Azure Spot preemption produces at a random byte offset, because the Trainer does not write atomically), `checkpoint-N/adapter_model.safetensors` is left partial on disk. On resume, `safetensors.safe_open` raises `SafetensorError: Error while deserializing header: incomplete metadata, file not fully covered` before step 1, systemd counts a Failure, `Restart=on-failure` retries, we find the same corrupt file, and the service loops until `StartLimitBurst=10/600s` is exhausted. Observed 16:10-16:11 UTC with `checkpoint-25` of `dpo_standard_qwen72`.
  - Fix in `scripts/azure_finetune_spot.sh`: rewrote `latest_checkpoint` to iterate newest -> oldest, deeply validate each candidate's `adapter_model.safetensors`/`.bin` via an inline Python check (`safe_open` or `torch.load(weights_only=True)`), quarantine any that fail to `<dir>/.corrupt/<name>.<ts>` so the loop cannot re-find them, and return the newest survivor or empty string (meaning "start from scratch"). Added two new helpers `_checkpoint_is_valid` and `_quarantine_checkpoint`.
  - Regression tests in `tests/finetuning/test_checkpoint_validation.py` (9 cases): unit tests for the validator snippet against valid safetensors, truncated safetensors (the Apr 20 repro), empty safetensors, valid pickle, corrupt pickle, and a missing file; plus static guards asserting the orchestrator still contains the quarantine helper, iterates newest-first (`sort -t- -k2 -n -r`), and keeps the Python validator body byte-identical to the one exercised by the tests.
- Tightened checkpoint cadence after the first preemption proved the prior default was unsafe: lowered `SAVE_STEPS` default from 25 to 10 in `scripts/azure_finetune_spot.sh`. The 25-step default was set assuming an incorrect 5 s/step throughput estimate; observed Qwen-72B QLoRA DPO is ~58 s/step (24 min between checkpoints) and Qwen-32B SFT is ~25 s/step (10 min). At SAVE_STEPS=10 the worst-case loss to a single Spot eviction drops to ~10 minutes on the slowest workload. LoRA adapter + Adam state checkpoints are ~5 GB each at NVMe write speeds (~2 s per save), with disk pressure bounded by `SAVE_TOTAL_LIMIT=3`. Added two regression tests to `tests/finetuning/test_systemd_unit_safety.py` enforcing `SAVE_STEPS in [5, 15]` and `SAVE_TOTAL_LIMIT in [2, 5]`.
- Fixed a third defect surfaced by the first real Azure Spot preemption of the run (DPO step 24 of `dpo_standard_qwen72`). The IMDS poller correctly detected the scheduled event and SIGTERM'd the orchestrator, the orchestrator's signal handler correctly propagated to torchrun, torchrun closed worker processes, and the orchestrator exited 0 ("Orchestrator exiting cleanly; next boot will resume via state reconciliation"). But systemd then immediately ran the unit's `ExecStop=/bin/kill -SIGTERM $MAINPID`, which by that point had `$MAINPID` empty (the main process had already exited). Bare `kill` printed its usage and exited 1, causing systemd to mis-classify the entire graceful shutdown as a Failure. This fired `Restart=on-failure` on a VM Azure was about to deallocate, wasting a slot from `StartLimitBurst=10/600s`.
  - Fix: removed `ExecStop` entirely from `scripts/defab_finetune.service`. systemd already SIGTERMs MainPID via `KillSignal=SIGTERM`, propagates to the cgroup via `KillMode=mixed`, and SIGKILLs after `TimeoutStopSec=45`. The `ExecStop` line was redundant and racing the orchestrator's own signal handler. Added an explanatory comment in the unit so this is not re-introduced.
  - Regression guard: `tests/finetuning/test_systemd_unit_safety.py` (9 cases) statically asserts (a) no `ExecStop=...$MAINPID` pattern, (b) presence of `KillMode=mixed`, `KillSignal=SIGTERM`, `Restart=on-failure`, (c) `TimeoutStopSec` in [30, 90] s, (d) explicit conda PATH so `python`/`torchrun` resolve under systemd, (e) negative `OOMScoreAdjust` so the orchestrator survives its own training children, (f) `StartLimitBurst <= 20` so a real bug eventually surfaces instead of looping forever, (g) the watchdog runs as root.
- Fixed the second crash uncovered after the QLoRA grad-checkpointing fix landed: TRL `DPOTrainer.log()` raised `TypeError: takes 2 positional arguments but 3 were given` at the first `logging_steps` interval (~10 minutes into Qwen-72B DPO). Cause is a signature drift: `transformers >= 4.43` now calls `Trainer.log(logs, start_time)` to compute throughput metrics, but the installed TRL `DPOTrainer.log` (and `GRPOTrainer.log`, `RewardTrainer.log`) still match the old `(self, logs)` signature. SFT survived because TRL's `SFTTrainer.log` already uses `*args`.
  - Fix: added `experiments/finetuning/_trl_compat.py`, an idempotent in-place patch that introspects each TRL trainer's `log` signature and wraps it to either forward or silently drop the extra positional arg, depending on what the original accepts. Wired the shim into `train_sft.py`, `train_dpo.py`, `train_grpo.py`, and `train_rlhf_vitl.py` via a `sys.path` insert + `import _trl_compat` so the patch fires before any trainer is instantiated under `torchrun`.
  - Regression guard: `tests/finetuning/test_trl_log_compat.py` (8 cases) verifies (a) old-style `log(self, logs)` classes have extras dropped, (b) new-style `log(self, logs, start_time=None)` classes have extras forwarded, (c) the wrapping is idempotent, (d) classes without their own `log` are no-ops, and (e) every at-risk training script imports the shim.
  - This was a pure orchestration win: state reconciliation correctly preserved the just-completed `sft_qwen72` (so we did not lose the Qwen-72B SFT adapter), refused to mark `dpo_standard_qwen72` complete despite the crashed-after-loss-bookkeeping torchrun, and the systemd `Restart=on-failure` retried automatically until the underlying defect was patched.
- Diagnosed and fixed the canonical QLoRA + gradient-checkpointing bug that was crashing every SFT/DPO/RLHF-ViTL run on Azure on the first backward pass:
  - Symptom: `RuntimeError: element 0 of tensors does not require grad and does not have a grad_fn` at `accelerator.backward(loss)`, preceded by `UserWarning: None of the inputs have requires_grad=True. Gradients will be None`. Reproduced on Qwen2.5-72B-Instruct loaded with `bitsandbytes` 4-bit + PEFT LoRA + `gradient_checkpointing=True` + DDP.
  - Cause: when the base model is frozen (4-bit/quantized), its embedding layer outputs lose `requires_grad=True` after gradient-checkpointing recomputation, breaking the autograd graph before it reaches the LoRA adapters.
  - Fix in `experiments/finetuning/train_sft.py`, `train_dpo.py`, `train_rlhf_vitl.py`: import and call `prepare_model_for_kbit_training(model, use_gradient_checkpointing=True, gradient_checkpointing_kwargs={"use_reentrant": False})` before `get_peft_model` whenever `bnb_config is not None`; call `model.enable_input_require_grads()` after `get_peft_model` to cover the AWQ branch; pass `gradient_checkpointing_kwargs={"use_reentrant": False}` through every trainer config (SFT, DPO, GRPO, Reward).
  - Regression guard: `tests/finetuning/test_qlora_grad_setup.py` (13 cases) statically asserts the import, the guarded invocation under `if bnb_config is not None`, the `enable_input_require_grads()` call, and the non-reentrant checkpointing kwarg in every trainer config. Runs in ~0.05 s with no GPU.
  - Orchestrator hardening that proved its worth here: artifact verification refused to mark `sft_qwen72` complete despite an exit-0 from torchrun (the first-step crash never produced a `final/` adapter), and the watchdog correctly let the orchestrator's own `Restart=on-failure` handle the retry rather than masking the bug.

**Recent progress (2026-04-16)**:
- Hardened Azure Spot-VM orchestration end-to-end against deallocation:
  - Added `scripts/verify_and_repair_state.py`: boot-time audit that removes phantom `[done]` entries from `.finetune_state.json` by checking for real on-disk artifacts (`final/adapter_model.*`, non-empty `summary.json`). Motivated by Apr 15 state showing 8 Qwen-72B steps completed with zero outputs on disk.
  - Rewrote `scripts/azure_finetune_spot.sh` with artifact-verified `run_step` (a step is only marked complete after its declared output is confirmed), atomic `flock`+`tmp+rename+fsync` state writes, `spawn_to` helper that uses process substitution instead of pipelines so child PIDs remain signal-addressable, pre-flight disk and GPU checks, and a new `predownload_*` step per model so Qwen 32B/72B/DeepSeek shards are cached once to `/data/hf_cache`.
  - Added `scripts/azure_spot_preemption_poller.sh`: background process that polls the Azure IMDS `scheduledevents` endpoint every 5 s for `Preempt`/`Freeze`/`Reboot`/`Redeploy`/`Terminate` events and signals the orchestrator before the OS SIGTERM arrives.
  - Added `scripts/defab_watchdog.sh` + `scripts/defab_watchdog.service`: stall detector that restarts `defab_finetune` if no `train.log` has been touched for 15 minutes while the service is active, capped at six restarts per boot to avoid looping on deterministic failures.
  - Hardened `scripts/defab_finetune.service`: `KillMode=mixed`, `KillSignal=SIGTERM`, `TimeoutStopSec=45`, `OOMScoreAdjust=-500`, `LimitNOFILE=1048576`, `StartLimitBurst=10/600s`, `NCCL_ASYNC_ERROR_HANDLING=1`, `PYTHONFAULTHANDLER=1`.
  - Fixed silent training bugs: `warmup_steps=100` exceeded total training steps (~54) at current batch size, so no model ever finished warmup. Added `--warmup-ratio` (default 0.05 via orchestrator) to all three training scripts; also added `--save-total-limit` (3, pruning old checkpoints to bound disk) and `--resume-from-checkpoint` (propagated into `trainer.train()`).
  - Updated `hpc/AZURE_FINETUNE.md` with the new deployment procedure, including an upgrade path for VMs that already have the older orchestrator running.
- Fixed `device_map` incompatibility with `torchrun` DDP in all three training scripts (`train_sft.py`, `train_dpo.py`, `train_grpo.py`): replaced `device_map="auto"` with `device_map={"": local_rank}` so each rank loads the model onto its own GPU. Qwen 2.5-32B SFT training restarted on Azure.
- Reconciled instance totals in `paper/paper.tex`: Tier 2 instances updated from 26,693 to 47,482 (added UMLS to source list), total from 351,613 to 372,402 (matches `dataset_paper.tex` and actual instance count on disk).
- Rewrote `scripts/_compute_l3_metrics.py` to extract real L3 metrics (conservativity, novelty, revision distance, error class) from full foundry result JSONs instead of summary-only placeholders. Generated `paper/tables/table3_level3_metrics.tex` and `paper/tables/table4_error_taxonomy.tex` with real values.
- Fixed key name inconsistency in `experiments/error_taxonomy.py` (`E1_correct` -> `correct`, old E2-E5 keys -> actual data keys) and recursive glob for subdirectory results. Ran against all results; saved to `experiments/results/error_taxonomy.json`.
- Populated `tab:ft_errors` Base column in `paper/paper.tex` with foundation model L3 error distribution: E1=37.1%, E2=29.8%, E5=5.1%.
- Regenerated synthetic contamination-control instances (409 matched to Tier 0). Model evaluation pending API access.
- Ran `difficulty_analysis.py`, `partition_sensitivity.py`, `statistics.py` against current instances; regenerated all JSON outputs. Fixed NaN-in-JSON bug in `partition_sensitivity.py`.
- Updated contamination analysis text in `paper/paper.tex` to note synthetic instances are generated.
- Full test suite passes: 1627 passed, 3 skipped, 91% coverage.

**Recent progress (2026-04-15)**:
- Removed `--deepspeed-config` from DPO and GRPO training calls in `scripts/azure_finetune_spot.sh`. DeepSpeed initialization fails without `CUDA_HOME`; 2-GPU DDP via `torchrun` is sufficient.
- Uploaded all new/updated instance files to `PatrickAllenCooper/DeFAb` on HuggingFace: multitier instances (framenet 16 MB, gene_ontology 2 MB, sumo 3.5 MB, wikidata 1.5 MB, umls 11.6 MB, yago_full 2.4 MB, babelnet 219 KB) and updated tier1 instances (biology 61 MB, chemistry 11 MB, everyday 174 MB, legal 42 MB, materials 17 MB).
- Conversion script `scripts/_convert_yago_facts.py` written to stream-convert `tier3/yago_full_facts/theory.pkl` (5.5 GB) to `theory.jsonl.gz` for HuggingFace upload. **NOTE**: local pkl is corrupted (EOFError on load); needs to be regenerated on CURC or re-downloaded before upload is possible.

**Recent progress (2026-04-10)**:
- Integrated all content from `paper/finetuning_games.tex` into `paper/paper.tex`. Section 6 (Fine-Tuning) now includes five new subsections: Defeasible Conflict Games (formal definitions of conflicts and resolution games), Game-Generated Preferences for DPO (structurally grounded preference pairs from game outcomes), Self-Play and Process Reward (self-play training with step-level reward decomposition), Theory Construction as RL Environment (MDP formulation and Active Inference with Expected Free Energy), and Unified Training Pipeline (three-phase SFT/DPO/RLVR pipeline with tikz diagram). Discussion expanded with concrete DeFAb-Math examples (Euler's formula, convergent sequences) and 16 open questions for game-based training. New Appendix E (Game-Theoretic Foundations) added with formal proofs of binarity, zero-sumness, finiteness, determinacy, verifier invariance, and the Lakatos Correspondence. Five bibliography entries added for Active Inference and game-theoretic semantics literature. The standalone `finetuning_games.tex` is now fully subsumed by `paper.tex`.

**Recent progress (2026-04-07)**:
- Google.org Impact Challenge: AI for Science application drafted (deadline April 17, 2026). The application frames DeFAb under "AI for Health & Life Sciences" as DeFAb-Health, emphasizing the biomedical KB extraction pipeline (UMLS, SNOMED CT, GO, MeSH) and verifier-backed fine-tuning. See `Guidance_Documents/GOOGLE_ORG_APPLICATION.md` for the complete drafted responses. PI: Alvaro Velasquez; team: 4 PhD students + 1 postdoc. Funding request: $2M over 36 months.
- Extended vision developed for the application: expanded medical dataset integration roadmap covering Orphanet (16K rare diseases), HPO (18K phenotypic terms), DrugBank (14K+ drug entries), PharmGKB (800+ clinical guidelines), ClinVar (2.5M+ variant submissions), FDA AEMS, NCI Thesaurus (170K cancer concepts), Reactome (2,700+ pathways), and DisGeNET (1.1M+ gene-disease associations). Creative applications identified: rare disease diagnosis as defeater recognition, adverse drug reaction prediction as exception forecasting, pharmacogenomic precision as formalized exception handling, and cancer treatment resistance as scientific belief revision. Trust framed as a set of formally verifiable properties (traceability, revisability, conservativity, accountability, contamination resistance).
- Collaboration brief prepared: `paper/google_org_brief.tex` (DeFAb-Health proposal summary for CU Anschutz outreach)
- Genesis abstract prepared: `paper/genesis_abstract.tex` (multimodal hypothesis generation framing by PI Velasquez)

**Recent progress (2026-03-22)**:
- UMLS 2025AB license obtained and data verified at `D:\datasets\umls-2025AB-metathesaurus-full\2025AB\META\`
- Gene Ontology extractor fixed: annotation rules now have body predicates (was all-empty-body, producing 0 instances)
- Wikidata theory rebuilt: facts now use `isa` and `has_property` predicates matching rule bodies
- Synthetic theory generator built at `src/blanc/generation/synthetic.py`
- 409 synthetic instances generated matched to Tier 0
- `D:\datasets\DeFAb\` canonical directory structure created
- UMLS extraction and GO/Wikidata instance regeneration running

**Recent progress (2026-04-20)**:
- Integrated python-sc2 (BurnySc2) as the live SC2 track alongside the hand-authored
  RTS engagement KB and Lux AI S3 KB.  This closes the loop from real game physics to
  formal defeasible reasoning to LLM training signal.
- New package: `src/blanc/sc2live/` -- ObservationLifter, ActionCompiler, ReplayTraceExtractor,
  DeFAbBot, ScriptedPolicy, LLMPolicy.
- New scripts:
  - `scripts/sc2live_extract_traces.py` -- record game traces (E1/E2)
  - `scripts/generate_sc2live_instances.py` -- traces -> DeFAb L1/L2 instances (E2)
  - `scripts/mine_sc2_conflicts.py` -- extract defeasible conflicts for DPO (E3)
  - `scripts/run_sc2_selfplay.py` -- LLM-vs-LLM self-play, GRPO rollouts (E4)
  - `scripts/run_sc2_evaluation.py` -- evaluate models on sc2live instances
  - `scripts/install_sc2_linux_headless.sh` -- headless SC2 setup for CURC
- New experiments: `experiments/cross_env_transfer.py` (E5 hypothesis H5 tester)
  and `experiments/finetuning/prepare_sc2live_preference_data.py` (DPO from mined conflicts).
- New HPC scripts: `hpc/slurm_sc2_grounding.sh`, `hpc/slurm_sc2_selfplay.sh`;
  extended `hpc/setup_curc_env.sh` with SC2 live track instructions.
- New tests: `tests/sc2live/` (67 unit tests, all pure Python, no SC2 binary required);
  `tests/integration/test_sc2live_engagement_kb.py` (integration + live-binary marker).
- `pyproject.toml` updated: `[project.optional-dependencies] sc2live = ["burnysc2>=7.0", ...]`;
  `pytest.ini_options` now includes `sc2_live` marker.
- Updated `assets/roe_demo/VISUAL_ASSETS.md` to reference `BotAI.state` (python-sc2 API)
  instead of DeepMind's PySC2 screen-pixel API.

### SC2 live track KB row (alongside rts and lux)

| KB | Source | Rules | Facts | Instances | Script |
|----|--------|-------|-------|-----------|--------|
| rts_engagement | Hand-authored SC2 ROE (paper §4) | ~200 | ~80 | ~100+ | `generate_rts_instances.py` |
| lux_ai_s3 | Lux AI S3 NeurIPS 2024 (paper §4) | ~130 | ~60 | ~80+ | `generate_lux_instances.py` |
| **sc2live** | **Live SC2 game traces (python-sc2)** | **~200+** | **per-game** | **~5k (E2)** | **`generate_sc2live_instances.py`** |

**Recent progress (2026-04-20, ROE compliance experiment)**:
- Added `CommanderPolicy` (B0/B1/B2 enforcement modes) and supporting modules: `compliance.py`, `situation_report.py`, `orders_schema.py`.
- Added `scripts/run_roe_compliance_experiment.py` (quiz + live backends) and `experiments/roe_compliance_analysis.py` (bootstrap CI tables, violation breakdown, reprompt histogram).
- Added 79 new tests across `tests/sc2live/{test_orders_schema,test_compliance,test_situation_report,test_commander_policy}.py` and `tests/integration/test_roe_compliance_quiz.py`.
- Widened `DeFAbBot.on_step` to dispatch on `propose_orders` (CommanderPolicy) vs `propose_defeaters` (ScriptedPolicy/LLMPolicy).
- Full test suite: 154 passed, 3 skipped (sc2_live marker).
