# NeurIPS Full Implementation Roadmap: Complete Paper Requirements

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Status**: Comprehensive plan matching ALL paper.tex requirements  
**Timeline**: 14-16 weeks (revised from 8 weeks)

## Executive Summary

After comprehensive review of paper.tex Section 4 (Experiments), the original 8-week roadmap significantly underestimated requirements. This document provides a **complete and realistic plan** that implements EVERY requirement from the paper.

**Key Findings**:
- Paper requires **3 specific domains**: Biology, Legal, **Materials Science** (not medical)
- Paper requires **13 partition strategies** tested on each KB (not just 1)
- Paper requires **parallel distractor sets** (3 strategies × instances)
- Paper requires **complete statistical analysis** (5 subsections, ~10 different tests)
- Paper requires **three-stage decoder** (D1 → D2 → D3)
- Paper requires **multiple analysis conditions** (scaling, CoT, theory size, symbolic ceiling)

**Estimated Instance Count**: 1500-2000 instances (not 500)  
**Estimated Evaluations**: 30,000-60,000 LLM calls  
**Revised Timeline**: 14-16 weeks full-time

---

## Gap Analysis Summary

See `PAPER_REQUIREMENTS_CHECKLIST.md` for complete gap analysis.

**Critical Missing Components**:
1. Materials science KB (paper-specified, not optional)
2. All 13 partition strategies (×3 KBs = 39 configurations)
3. Complete Section 4.3 statistics (5 major analyses)
4. Error taxonomy (5 error types)
5. Scaling analyses (3 types)
6. Chain-of-thought evaluation (doubles work)
7. Graded scoring for Level 3
8. D3 semantic decoder
9. Symbolic ceiling (ASP solver comparison)

---

## Revised Phased Plan

### Phase 1: Knowledge Bases & Comprehensive Instance Generation (Weeks 1-4)

#### Week 1: Biology KB with All Partitions

**Goal**: Implement first KB with complete partition coverage

**Tasks**:
1. Expand Avian Biology to full biology KB
   - Add: phylogenetic classification (from OpenCyc subset)
   - Add: morphological properties
   - Add: functional mechanisms
   - Add: IDP examples (intrinsically disordered proteins)
   - Target size: 100-150 rules

2. Generate instances under ALL 13 partition strategies
   - κ_leaf
   - κ_rule  
   - κ_depth(k) for k ∈ {1, 2, 3}
   - κ_rand(δ) for δ ∈ {0.1, 0.2, ..., 0.9}

3. For EACH partition strategy:
   - Generate Level 1-2 instances
   - Sample with k=5 distractors
   - Use syntactic strategy initially

4. Compute yield curves
   - Y vs δ for κ_rand
   - Fit parametric models (linear, logistic, power-law)
   - Test for phase transitions

**Deliverables**:
- examples/knowledge_bases/biology_full/ (~150 rules)
- ~400 instances from biology (13 partitions × ~30 instances)
- Yield analysis plots and fitted models
- Statistical validation of Proposition 3

**Success Criteria**:
- [ ] Biology KB: 100+ rules, function-free
- [ ] All 13 partition strategies working
- [ ] ~400 instances generated
- [ ] Yield curves validate Proposition 3
- [ ] All instances 100% valid

#### Week 2: Legal Reasoning KB

**Goal**: Second domain (legal) with full partition coverage

**Tasks**:
1. Extract and curate legal KB from TaxKB
   - Statutory rules
   - Case-based precedents
   - Jurisdictional hierarchies
   - Exceptions and overrides
   - Target: 80-120 rules

2. Generate instances under all 13 partitions
   - Focus on natural legal defeaters
   - Precedent overruling for Level 3

3. Parallel distractor generation
   - Generate SAME instances with random, syntactic, AND adversarial distractors
   - This creates 3× variants for distractor comparison

**Deliverables**:
- examples/knowledge_bases/legal_reasoning/ (~100 rules)
- ~400 instances from legal (13 partitions)
- ~1200 distractor variants (3 strategies)

**Success Criteria**:
- [ ] Legal KB operational
- [ ] 400 instances from legal domain
- [ ] Parallel distractor sets created
- [ ] All instances valid

#### Week 3: Materials Science KB

**Goal**: Third domain (materials) - paper-specified requirement

**Tasks**:
1. Create materials science KB (NEW - most challenging)
   - Structure-property relationships
   - Synthesis conditions, phase behavior
   - Defaults: "crystalline materials are brittle"
   - Exceptions: shape-memory alloys, metallic glasses
   - **Requires domain expert consultation**
   - Target: 60-100 rules

2. Generate instances under all 13 partitions
   - Technical scientific defaults
   - Material exceptions

**Deliverables**:
- examples/knowledge_bases/materials_science/ (~80 rules)
- ~350 instances from materials
- Domain expert validation report

**Success Criteria**:
- [ ] Materials science KB created
- [ ] Domain expert validates rules
- [ ] 350 instances generated
- [ ] All instances valid

#### Week 4: Statistical Analysis (Section 4.3)

**Goal**: Implement complete Section 4.3

**Tasks**:
1. **Volume and balance** (§4.3.1)
   - Joint distribution (KB, partition, level)
   - Chi-square test for balance
   - Identify underpopulated cells

2. **Structural difficulty distributions** (§4.3.2)
   - Compute σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*) for all instances
   - Marginal distributions for each component
   - Joint distributions
   - Mutual information estimates
   - Test independence hypotheses

3. **Novelty and revision spectrum** (§4.3.3)
   - For Level 3: compute (Nov, d_rev) for all instances
   - Cross-tabulate with resolution strength
   - Test hypotheses: (i) high-novelty → strong, (ii) conservative → low d_rev

4. **Yield analysis** (§4.3.4)
   - Already have yield curves from Week 1
   - Fit parametric models
   - Statistical tests

5. **Partition sensitivity** (§4.3.5)
   - Two-sample tests on σ(I) across partition families
   - Test if partitions produce distinguishable difficulties

**Deliverables**:
- experiments/statistics.py (complete Section 4.3)
- Statistical analysis report
- All figures and tables for paper

**Success Criteria**:
- [ ] All 5 subsections of §4.3 implemented
- [ ] Statistical tests documented
- [ ] Figures generated
- [ ] Results ready for paper

**Total Phase 1**: ~1150 instances across 3 KBs, full statistical analysis

---

### Phase 2: Complete Codec Implementation (Weeks 5-7)

#### Week 5: M3 & M2 Encoders + D2 Decoder

**Goal**: Add annotated formal and semi-formal modalities

**Tasks**:
1. **M3 Encoder** (Annotated Formal)
   - Implementation: 200 lines
   - Format: code + comments
   - Round-trip target: >95%

2. **M2 Encoder** (Semi-Formal)
   - Implementation: 250 lines
   - Format: logical symbols + NL predicates
   - Requires NL mapping for each KB
   - Round-trip target: >90%

3. **D2 Decoder** (Template Extraction)
   - Implementation: 200 lines
   - Edit distance (Levenshtein)
   - Sound + complete (Proposition line 894)
   - Fallback from D1

4. **NL Mapping** (Definition 28)
   - Create for all 3 KBs
   - Ensure injectivity (critical!)
   - Compositional via NL_P and NL_C
   - Domain coherence

**Deliverables**:
- codec/m3_encoder.py
- codec/m2_encoder.py
- codec/d2_decoder.py
- codec/nl_mapping.py (for all 3 KBs)
- 40+ round-trip tests

**Success Criteria**:
- [ ] M3: >95% round-trip
- [ ] M2: >90% round-trip
- [ ] D2: Sound + complete
- [ ] All NL maps injective

#### Week 6: M1 Encoder + D3 Decoder

**Goal**: Complete all modalities and decoders

**Tasks**:
1. **M1 Encoder** (Narrative - HARDEST)
   - Full natural language
   - Linguistic hedging for defeasibility
   - Implicit universal quantification
   - Templates per KB domain
   - May use LLM for paraphrasing
   - Round-trip target: >85% (with D2/D3)

2. **D3 Decoder** (Semantic Parser - NEW REQUIREMENT)
   - Grammar-based parser (Lark)
   - Semantic extraction model (transformer)
   - Definition 29: "parser M_parse(y | schema(L))"
   - Handles paraphrases
   - Sound (conditional on M_parse)

3. **Three-stage decoder integration**
   - D1 (exact) → D2 (template) → D3 (semantic)
   - Cascading fallback
   - Track which stage succeeds

**Deliverables**:
- codec/m1_encoder.py
- codec/d3_decoder.py
- codec/cascading_decoder.py (D1→D2→D3)
- Grammar files for logic parsing
- 50+ round-trip tests

**Success Criteria**:
- [ ] M1: >85% round-trip with D2/D3
- [ ] D3: Handles paraphrases
- [ ] Three-stage pipeline working
- [ ] Decoder validation (§4.8) complete

#### Week 7: Decoder Validation & Round-Trip Testing

**Goal**: Section 4.8 - validate codec before evaluation

**Tasks**:
1. Round-trip validation for ALL decoders
   - D1: Should be 100%
   - D2: Target >95%
   - D3: Target >90%
   - Per modality reporting

2. Synthetic test suite
   - Generate paraphrases
   - Test edge cases
   - Stress test normalization

3. Pre-evaluation validation
   - Encode all gold hypotheses
   - Apply three-stage decoder
   - Report recovery rates
   - Must exceed 95% threshold (paper line 461)

**Deliverables**:
- codec/validation.py
- Decoder validation report (§4.8)
- Round-trip accuracy tables
- Prerequisite for model evaluation

**Success Criteria**:
- [ ] D1: 100% round-trip
- [ ] D2: >95% round-trip  
- [ ] D3: >90% round-trip
- [ ] Overall: >95% recovery
- [ ] Validation report complete

**Total Phase 2**: 4 modalities, 3 decoders, validated codec

---

### Phase 3: LLM Evaluation (Weeks 8-10)

#### Week 8: Model Evaluation Infrastructure

**Goal**: Set up evaluation for 5 models × 4 modalities × 2 prompting styles

**Tasks**:
1. **Model interfaces**
   - OpenAI API: GPT-4o
   - Anthropic API: Claude 3.5 Sonnet
   - Google API: Gemini 1.5 Pro
   - Local/API: Llama 3 70B
   - Local/API: Llama 3 8B

2. **Prompting infrastructure**
   - Direct prompt (baseline)
   - Chain-of-thought prompt (§4.7)
     - Step (a): Identify rules
     - Step (b): Determine gaps
     - Step (c): Propose hypothesis

3. **Evaluation pipeline**
   - Batch processing
   - Rate limiting
   - Error handling
   - Progress tracking
   - Response caching (for reproducibility)

4. **Graded scoring** (§4.5)
   - Implement 5-level scoring (0, 0.25, 0.5, 0.75, 1.0)
   - Check: decoder success, anomaly resolution, well-formedness, conservativity, strength
   - Report binary AND mean graded score

**Deliverables**:
- experiments/model_interface.py
- experiments/prompting.py
- experiments/graded_scoring.py
- experiments/evaluation_pipeline.py

**Success Criteria**:
- [ ] All 5 model interfaces working
- [ ] Both prompting styles implemented
- [ ] Graded scoring operational
- [ ] Batch evaluation ready

#### Week 9: Core Evaluation

**Goal**: Evaluate models on full dataset

**Tasks**:
1. Run evaluation
   - 5 models
   - ~1150 instances
   - 4 modalities
   - 2 prompting styles (direct + CoT)
   - **Total**: ~46,000 evaluations

2. Collect results
   - Response caching
   - Decoder application (D1→D2→D3)
   - Graded scoring
   - Error classification

3. Compute primary metrics
   - Rendering-robust accuracy (Definition 31)
   - Per-model, per-level accuracy
   - Per-modality accuracy
   - CoT lift (ΔCoT)

**Deliverables**:
- Cached responses (JSON)
- Primary results table
- Accuracy breakdowns

**Success Criteria**:
- [ ] All evaluations complete
- [ ] Responses cached
- [ ] Primary metrics computed
- [ ] No evaluation errors

#### Week 10: Error Taxonomy & Decomposed Metrics

**Goal**: Complete §4.6 (Error Taxonomy) and §4.4 decomposed metrics

**Tasks**:
1. **Error classification** (§4.6)
   - E1: Decoder failure
   - E2: Derivation failure (grounding deficit)
   - E3: Minimality violation
   - E4: Conservativity violation (belief revision deficit)
   - E5: Strength shortfall
   - Classify ALL incorrect outputs
   - Report distribution per model, level, modality

2. **Decomposed metrics** (§4.4)
   - Per-modality accuracy
   - Per-level accuracy
   - Resolution strength distribution (Level 3)
   - Novelty of correct resolutions (Level 3)
   - Revision distance of correct resolutions (Level 3)

3. **Mapping to deficits**
   - Analyze error patterns
   - Diagnose which deficit each model has
   - Model-specific characterizations

**Deliverables**:
- experiments/error_taxonomy.py
- experiments/decomposed_metrics.py
- Error distribution tables
- Deficit diagnosis per model

**Success Criteria**:
- [ ] All errors classified
- [ ] Distribution computed
- [ ] Decomposed metrics ready
- [ ] Deficit mapping clear

**Total Phase 3**: Complete model evaluation with full analysis

---

### Phase 4: Advanced Analyses (Weeks 11-12)

#### Week 11: Scaling Analyses

**Goal**: Complete §4.7 analysis conditions

**Tasks**:
1. **Model scaling analysis** (§4.7, line 436)
   - Llama 3 8B vs 70B on identical instances
   - Compute ΔAcc / Δlog(params) per level
   - Test for threshold behavior at Level 3
   - Characterize emergent capabilities

2. **Theory size scaling** (§4.7, line 450)
   - Generate instances from subtheories |D| ∈ {50, 100, 200, 500, 1000}
   - Use connected subgraphs of dependency graph
   - Report accuracy vs |D|
   - Characterize degradation pattern

3. **Symbolic ceiling** (§4.7, line 456)
   - Implement ASP solver evaluation
   - Exact solutions for Levels 1-2
   - Enumeration for Level 3 (with timeout)
   - Compute neural-symbolic gap per level

**Deliverables**:
- experiments/scaling_analysis.py
- experiments/symbolic_solver.py (ASP interface)
- Scaling plots and analysis
- Neural-symbolic gap tables

**Success Criteria**:
- [ ] Scaling gradient computed
- [ ] Threshold behavior tested
- [ ] Theory size scaling characterized
- [ ] Symbolic ceiling established

#### Week 12: Partition & Distractor Analysis

**Goal**: Complete remaining analyses

**Tasks**:
1. **Partition sensitivity** (§4.3, line 365)
   - Compare σ(I) distributions across 4 partition families
   - Two-sample tests (Kolmogorov-Smirnov, Mann-Whitney)
   - Test if partitions produce distinguishable difficulties
   - Characterize partition impact

2. **Distractor strategy comparison** (§4.2, line 348)
   - Evaluate on parallel instance sets (random, syntactic, adversarial)
   - Report performance separately per strategy
   - Isolate distractor design effect
   - Recommend optimal strategy

3. **Language bias variation** (§4.2, line 350)
   - Level 3 with ar_max ∈ {1, 2, 3}
   - Level 3 with P+ (restricted vs expanded)
   - Test novelty impact
   - Measure difficulty increase

**Deliverables**:
- Partition sensitivity analysis
- Distractor comparison report
- Language bias study

**Success Criteria**:
- [ ] Partition comparison complete
- [ ] Distractor strategies compared
- [ ] Language bias effects characterized

**Total Phase 4**: All supplementary analyses complete

---

### Phase 5: Paper Integration & Submission (Weeks 13-14)

#### Week 13: Results Integration

**Goal**: Populate paper with all results

**Tasks**:
1. **Section 4.3**: Dataset statistics
   - All 5 subsections
   - Tables and figures

2. **Section 4.4-4.7**: Evaluation results
   - Primary metrics table
   - Decomposed metrics
   - Error taxonomy
   - All analyses

3. **Figures and tables**
   - Generate all required figures
   - Format tables for NeurIPS
   - Ensure consistency

4. **Supplementary materials**
   - Extended results
   - Additional plots
   - Code documentation
   - Dataset description

**Deliverables**:
- Updated paper.tex with all results
- All figures generated
- Supplementary materials PDF

**Success Criteria**:
- [ ] All sections populated
- [ ] All figures generated
- [ ] Paper compiles
- [ ] Supplementary complete

#### Week 14: Final Validation & Submission Prep

**Goal**: Final checks and submission

**Tasks**:
1. **Reproducibility package**
   - Pin all dependencies
   - Document random seeds
   - Cache all LLM responses
   - Test installation on clean environment

2. **Code release preparation**
   - Clean up code
   - Final documentation pass
   - License verification (MIT)
   - README for public release

3. **Final validation**
   - Re-run key experiments
   - Verify all numbers in paper
   - Check all references
   - Proofread thoroughly

4. **Submission**
   - Prepare submission package
   - Upload to NeurIPS system
   - Supplementary materials
   - Code/data availability statements

**Deliverables**:
- Reproducibility package
- Public code release
- Final paper PDF
- Submission confirmation

**Success Criteria**:
- [ ] All experiments reproducible
- [ ] Code publicly available
- [ ] Paper submitted
- [ ] Checklist complete

---

## Detailed Requirements by Paper Section

### §4.1: Source Knowledge Bases

- [ ] 3 domains: Biology, Legal, Materials Science
- [ ] Report |C|, |P|, |Π| for each
- [ ] Report dependency graph depth
- [ ] Report |HB| after grounding
- [ ] Ensure function-free (datalog)
- [ ] Vary size, vocabulary, ontological depth

### §4.2: Dataset Generation

- [ ] Test all 4 partition families on each KB
- [ ] κ_depth for k ∈ {1,2,3}
- [ ] κ_rand for δ ∈ {0.1, 0.2, ..., 0.9}
- [ ] Compute δ(κ) for each
- [ ] Compute Y(κ, Q) for each
- [ ] Target set Q: depth ≥ 2 atoms
- [ ] k=5 distractors for Levels 1-2
- [ ] 3 distractor strategies (parallel sets)
- [ ] Language bias variation for Level 3 (ar_max, P+)
- [ ] Hand-authored defeaters for Level 3

### §4.3: Dataset Statistics

- [ ] Volume and balance (joint distribution)
- [ ] Structural difficulty σ(I) distributions
- [ ] Mutual information between components
- [ ] Novelty-revision spectrum (Level 3)
- [ ] Resolution strength cross-tabulation
- [ ] Yield curves with fitted models
- [ ] Phase transition tests
- [ ] Partition sensitivity (two-sample tests)

### §4.4: Foundation Model Evaluation

- [ ] 5 models: GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro, Llama 3 70B, Llama 3 8B
- [ ] Two from same family (Llama) for scaling
- [ ] All 4 modalities per instance
- [ ] Three-stage decoder (D1→D2→D3)
- [ ] Greedy decoding (temperature=0)
- [ ] Standardized system prompt
- [ ] Rendering-robust accuracy (worst-case over modalities)
- [ ] Per-modality accuracy
- [ ] Per-level accuracy
- [ ] Resolution strength distribution (Level 3)
- [ ] Novelty distribution (Level 3)
- [ ] Revision distance distribution (Level 3)

### §4.5: Partial Credit

- [ ] Implement 5-level graded scoring
- [ ] Report binary accuracy
- [ ] Report mean graded score
- [ ] Decomposition by AGM revision stages

### §4.6: Error Taxonomy

- [ ] Classify into 5 error types (E1-E5)
- [ ] Report distribution per model, level, modality
- [ ] Map to three deficits
- [ ] Diagnose per-model limitations

### §4.7: Analysis Conditions

- [ ] Scaling analysis (Llama 8B vs 70B)
- [ ] ΔAcc / Δlog(params) per level
- [ ] Threshold behavior test (Level 3)
- [ ] Chain-of-thought prompting
- [ ] CoT lift ΔCoT per level
- [ ] Theory size scaling (|D| ∈ {50, 100, 200, 500, 1000})
- [ ] Subgraph selection algorithm
- [ ] Symbolic ceiling (ASP solver)
- [ ] Neural-symbolic gap computation
- [ ] Modality ablation (optional)

### §4.8: Decoder Validation

- [ ] Pre-evaluation validation
- [ ] Round-trip on all gold hypotheses
- [ ] Per-modality recovery rates
- [ ] >95% threshold requirement
- [ ] Synthetic test suite

---

## Revised Timeline Estimate

### Conservative (16 weeks)

```
Phase 1 (KBs + Stats):        4 weeks (Materials science is hard)
Phase 2 (Complete Codec):     3 weeks (M1 + D3 are hard)
Phase 3 (LLM Evaluation):     3 weeks (46K+ evaluations)
Phase 4 (Advanced Analyses):  2 weeks (Scaling, CoT, etc.)
Phase 5 (Integration):        2 weeks (Paper writing)
Phase 6 (Submission):         2 weeks (Buffer)
-------------------------------------------------
Total:                        16 weeks
```

### Aggressive (12 weeks)

```
Phase 1:  3 weeks (parallel KB development)
Phase 2:  2 weeks (focus on M2-M4, defer M1)
Phase 3:  2 weeks (smaller instance set)
Phase 4:  2 weeks (essential analyses only)
Phase 5:  2 weeks (paper + submission)
Buffer:   1 week
-------------------------------------------------
Total:    12 weeks
```

### Realistic (14 weeks)

**Recommended timeline balancing quality and speed**

---

## Critical Path Items

**Must Have** (for acceptance):
1. 3 knowledge bases (biology, legal, materials)
2. 500+ instances minimum
3. 3+ modalities (M2, M3, M4 sufficient if M1 too hard)
4. 3+ models evaluated
5. Section 4.3 statistics complete
6. Error taxonomy (§4.6)
7. Basic scaling analysis

**Should Have** (for strong paper):
8. 1000+ instances
9. All 4 modalities including M1
10. All 5 models
11. Chain-of-thought analysis
12. Symbolic ceiling
13. Complete §4.7 analyses

**Nice to Have** (for exceptional paper):
14. 5+ domains
15. Modality ablation
16. Theory size scaling
17. All partition strategies fully analyzed
18. Public dataset release

---

## Resource Requirements (Revised)

### Time

- **Personnel**: 1 FTE × 14 weeks = 560 hours
- **Domain expert**: 40 hours (materials science KB validation)
- **Total**: 600 hours

### Computational

- **LLM API costs**: 
  - GPT-4o: $200-300
  - Claude: $150-250
  - Gemini: $100-150
  - Total: **$450-700** (for 46K evaluations)

- **Compute**: 
  - Local Llama: GPU recommended (can use CPU)
  - ASP solver: Negligible
  - Statistical analysis: Standard laptop

### Knowledge Bases

- **Biology**: Can expand from MVP ✓
- **Legal**: Have TaxKB ✓
- **Materials Science**: Need domain expert consultation ✗

---

## Recommendations

### Option 1: Full Paper Implementation (14 weeks)

**Follow this roadmap exactly**
- Implement ALL paper requirements
- 1000+ instances
- Complete analyses
- Strongest submission

**Pros**: Complete, rigorous, publishable  
**Cons**: Long timeline, requires domain expert

### Option 2: Core Paper Implementation (10 weeks)

**Simplifications**:
- Skip materials science (use medical instead)
- Reduce to 500 instances
- Skip some analyses (theory size scaling, modality ablation)
- Focus on core evaluation

**Pros**: Faster, still strong  
**Cons**: Deviates from paper as written

### Option 3: MVP+ Implementation (6 weeks)

**Minimal viable for paper**:
- 2 KBs (biology, legal)
- 300 instances
- 3 modalities (M2, M3, M4)
- 3 models
- Essential statistics only

**Pros**: Fastest path to submission  
**Cons**: Weaker paper, may not be competitive

---

## Recommended Approach

**Start with Option 1 (Full Implementation), with fallback to Option 2 if needed**

**Week-by-week decision points**:
- After Week 2: Can we get materials science expert? If no → Option 2
- After Week 6: Is M1 working? If no → proceed without it
- After Week 10: On schedule? If no → cut optional analyses

**This provides maximum flexibility while targeting the strongest possible submission.**

---

## Next Steps

1. **Review this roadmap** carefully
2. **Decide on approach** (Option 1, 2, or 3)
3. **Begin Phase 1, Week 1** (Biology KB expansion)
4. **Secure domain expert** for materials science KB
5. **Set up evaluation infrastructure** early

---

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Status**: Comprehensive roadmap matching ALL paper requirements  
**Recommendation**: Option 1 (full) with fallback to Option 2 if needed
