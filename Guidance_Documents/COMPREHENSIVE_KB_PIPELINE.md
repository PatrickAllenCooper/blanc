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

The original `paper/paper.tex` contains three papers in one (dataset, fine-tuning methods, adversarial debate). The dedicated dataset paper (`dataset_paper.tex`) focuses exclusively on the DeFAb dataset contribution with four contributions: (1) the generation pipeline, (2) the cross-ontology KB extraction, (3) the synthetic contamination control, and (4) baseline evaluation results. Fine-tuning (DPO/RLHF/GRPO) and adversarial debate (MCTS) are mentioned as future directions only.

### Remaining TODOs for Dataset Paper Submission

**Critical (must complete before submission):**
- Generate and present dataset statistics tables (instance counts by level/domain/partition, difficulty distributions, novelty/revision spectra)
- Either complete the contamination analysis (generate matched synthetic instances, compute Delta_synth) or reframe as methodology-only with results pending
- Upload dataset to HuggingFace and obtain stable URL
- Generate Croissant metadata JSON-LD file
- Complete the Dataset Access section (hosting URL, loading instructions, maintenance plan)
- Complete the Datasheet for Datasets appendix (Gebru et al. framework)
- Download and integrate the NeurIPS 2026 LaTeX template (`neurips_2026.sty`) from https://neurips.cc/Downloads/2026
- Complete the NeurIPS 2026 paper checklist

**Important (strengthen the paper):**
- Add Qwen 2.5-72B and Qwen 2.5-32B results for within-family scaling analysis
- Fill in Level 3 metrics table (conservativity, novelty, revision distance columns currently placeholder)
- Fill in error taxonomy table (currently all zeros)
- Compute and present yield curves, partition sensitivity analysis
- Add figures (difficulty distribution histograms, yield curves, contamination gap visualization)

**Nice to have:**
- Complete Tier 3 instance generation from full YAGO 4.5
- Add Level 3 instances from automated defeater extraction at scale (GO NOT-qualifiers + Wikidata P2303)
- Symbolic ceiling evaluation via clingo ASP solver

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

Guidance_Documents/
  COMPREHENSIVE_KB_PIPELINE.md   # THIS DOCUMENT
  CROSS_ONTOLOGY_PLAN.md         # Tier 1 detail (existing)
  ALL_GOVERNMENT_KBS.md          # Full inventory (existing, update)
```

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
**See also**: `paper/dataset_paper.tex` (the dedicated NeurIPS 2026 E&D submission)

**Recent progress (2026-03-22)**:
- UMLS 2025AB license obtained and data verified at `D:\datasets\umls-2025AB-metathesaurus-full\2025AB\META\`
- Gene Ontology extractor fixed: annotation rules now have body predicates (was all-empty-body, producing 0 instances)
- Wikidata theory rebuilt: facts now use `isa` and `has_property` predicates matching rule bodies
- Synthetic theory generator built at `src/blanc/generation/synthetic.py`
- 409 synthetic instances generated matched to Tier 0
- `D:\datasets\DeFAb\` canonical directory structure created
- UMLS extraction and GO/Wikidata instance regeneration running
