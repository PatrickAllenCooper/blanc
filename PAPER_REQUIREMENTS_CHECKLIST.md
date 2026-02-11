# Paper Requirements vs. Implementation Plan: Gap Analysis

**Purpose**: Ensure NEURIPS_ROADMAP.md covers ALL requirements from paper.tex  
**Author**: Patrick Cooper  
**Date**: 2026-02-11

## Gap Analysis Results

After careful review of paper.tex Section 4 (Experiments), I've identified **critical gaps** in the current roadmap. The paper has much more detailed requirements than currently planned.

---

## Section 4.1: Source Knowledge Bases

### Paper Requirements (lines 314-324)

✅ **COVERED**:
- 3 domains: biology, legal, materials science
- Varied size, predicate vocabulary, ontological depth
- Report signature statistics (|C|, |P|, |Π|)
- Dependency graph depth
- Herbrand base size |HB|
- Function-free (datalog) constraint

❌ **GAPS IN ROADMAP**:
1. **Materials science KB** not mentioned (only biology, medical, legal/family)
   - Paper specifically requires materials science domain
   - Example: structure-property relationships, phase behavior
   - Need domain expert validation

2. **Signature statistics reporting** not in roadmap
   - Need to compute |C|, |P|, |Π| for each KB
   - Need dependency graph analysis
   - Need Herbrand base size computation

3. **Provenance types variation** not explicit
   - Paper wants varied provenance (OpenCyc, curated, expert-validated)

---

## Section 4.2: Dataset Generation and Parameterization

### Partition Functions (lines 331-332)

✅ **PARTIALLY COVERED**:
- Four partition families exist in code

❌ **CRITICAL GAPS**:
1. **ALL FOUR partitions must be tested on EACH KB**
   - Current: Only κ_rule tested
   - Need: κ_leaf, κ_rule, κ_depth(k) for k∈{1,2,3}, κ_rand(δ) for δ∈{0.1,...,0.9}
   - That's **13 partition strategies** per KB × 3 KBs = **39 partition-KB pairs**

2. **Yield curves must be plotted** for each KB
   - Current: Single test of Proposition 3
   - Need: Y vs δ plots for each source KB
   - Need: Fitted models (linear, logistic, power-law)
   - Need: Phase transition detection

3. **Target set Q must be systematically defined**
   - Paper: "all ground atoms in M_Π at dependency depth ≥ 2"
   - Need to implement this filtering
   - Need to document target selection

### Instance Generation (lines 333-346)

✅ **COVERED**:
- Level 1-3 generation
- k=5 distractors

❌ **GAPS**:
1. **Generate instance for EVERY critical element**
   - Current: Sample of targets
   - Paper: "For each target q and each e ∈ Crit*(D,q)"
   - This means MANY more instances than 500

2. **Level 3 language bias variation**
   - Paper: Test ar_max ∈ {1, 2, 3}
   - Paper: Test P+ (restricted vs expanded with novel predicates)
   - Need: Generate instances under EACH language bias setting
   - This creates multiple versions of Level 3 instances

3. **Hand-authored defeaters requirement**
   - Paper acknowledges: "pre-existing defeaters... validated by domain experts"
   - Need domain expert involvement for Level 3

### Distractor Strategies (lines 348-349)

❌ **CRITICAL GAP**:
**Parallel instance sets under THREE regimes**
- Current: Single distractor strategy per batch
- Paper: Generate PARALLEL sets (random, syntactic, adversarial)
- Same instance, different distractors
- Report performance separately for each regime
- This TRIPLES the instance count or requires factorial experiment design

**Impact**: For 500 base instances × 3 distractor strategies = 1500 evaluations

---

## Section 4.3: Dataset Statistics and Structural Analysis

### Required Statistics (lines 353-366)

❌ **MISSING FROM ROADMAP** - ENTIRE SUBSECTION:

1. **Volume and balance** (line 357)
   - Joint distribution: (KB, partition, level)
   - Check for underpopulated cells
   - Statistical balance tests

2. **Structural difficulty distributions** (line 359)
   - σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*)
   - Marginal distributions for EACH component
   - Joint distributions
   - Mutual information estimates between components
   - Test independence hypothesis

3. **Novelty and revision spectrum** (Level 3, line 361)
   - Joint distribution: (Nov(r*, D^-), d_rev)
   - Cross-tabulate with resolution strength
   - Test hypothesis: high-novelty → strong/restructuring
   - Test hypothesis: conservative → lower d_rev

4. **Yield analysis** (line 363)
   - Plot Y(κ_rand(δ), Q) vs δ
   - Fit parametric models (linear, logistic, power-law)
   - Test for phase transitions
   - Per source KB

5. **Partition sensitivity** (line 365)
   - Compare distributions across 4 partition families
   - Two-sample tests on σ(I) distributions
   - Test if partitions produce statistically distinguishable instances

**Impact**: Need complete statistical analysis module (experiments/statistics.py)

---

## Section 4.4: Foundation Model Evaluation

### Models (line 375)

✅ **MOSTLY COVERED**:
- GPT-4o, Claude 3.5 Sonnet, Gemini 1.5 Pro
- Llama 3 70B and 8B (scaling pair)

❌ **GAP**:
- Paper requires "panel spanning multiple families"
- Current roadmap says "4+ models" but paper specifies 5 minimum
- Need at least 3 families represented

### Rendering Conditions (line 377)

❌ **GAP**:
**EVERY instance under ALL FOUR modalities**
- Current: Roadmap adds modalities but unclear if EVERY instance tested in EVERY modality
- Paper: Each instance × 4 modalities
- For 500 instances × 4 modalities = **2000 prompts** minimum

### Decoding Pipeline (line 379)

❌ **CRITICAL GAP**:
**Three-stage decoder: D1 → D2 → D3**
- Current: D1 only, D2 planned
- Paper: "exact match (D1) is attempted first; on failure, template extraction (D2) is applied; on further failure, semantic parsing (D3)"
- D3 is semantic parser (not in roadmap yet)
- Need: Implement D3 with dedicated parser model

### Decomposed Metrics (lines 383-391)

❌ **MISSING**:
1. Per-modality accuracy (test Conjecture: modality-level interaction)
2. Per-level accuracy (validate difficulty ordering)
3. **Resolution strength distribution** (Level 3 only)
   - Classify as weak, strong, or restructuring
   - Report fractions
4. **Novelty of correct resolutions** (Level 3)
   - Compute Nov(h, D^-) for model hypotheses h ∈ H*
   - Report distribution
5. **Revision distance of correct resolutions** (Level 3)
   - Compute d_rev(D^-, D^- ∪ {h})
   - Measure adherence to minimal change

**Impact**: Need experiments/decomposed_metrics.py module

---

## Section 4.5: Partial Credit for Level 3

❌ **MISSING FROM ROADMAP**:
**Graded scoring function** (lines 394-414)
- 5-level scoring: 0, 0.25, 0.5, 0.75, 1.0
- Report both binary accuracy AND mean graded score
- Decomposition along AGM revision stages

**Impact**: Need experiments/partial_credit.py module (this was mentioned in original IMPLEMENTATION_PLAN but not in NEURIPS_ROADMAP)

---

## Section 4.6: Error Taxonomy

❌ **ENTIRELY MISSING**:
**Error classification system** (lines 417-429)
- E1: Decoder failure
- E2: Derivation failure (grounding deficit)
- E3: Minimality violation
- E4: Conservativity violation (belief revision deficit)
- E5: Strength shortfall

**Requirements**:
- Classify ALL incorrect outputs
- Report distribution per model, level, modality
- Map to three deficits (grounding, parsimony, belief revision)

**Impact**: Need experiments/error_taxonomy.py module

---

## Section 4.7: Analysis Conditions

❌ **MAJOR GAPS**:

### 1. Scaling Analysis (line 436)
**Missing**:
- Llama 3 8B vs 70B comparison (within-family scaling)
- Compute Δ Acc / Δ log(params) per level
- Test for threshold behavior at Level 3
- Hypothesis: emergent capability at Level 3

### 2. Chain-of-Thought Prompting (line 443)
**Entirely missing from roadmap**:
- Evaluate EACH model under CoT and direct prompting
- CoT scaffold: (a) identify rules, (b) determine gaps, (c) propose hypothesis
- Report ΔCoT = Acc_CoT - Acc_direct per level
- Interpretation: bottleneck diagnosis

**Impact**: DOUBLES evaluation effort (each model × direct + CoT)

### 3. Theory Size Scaling (line 450)
**Missing**:
- Generate instances from subtheories of size |D| ∈ {50, 100, 200, 500, 1000}
- Select connected subgraphs of dependency graph
- Report accuracy vs |D|
- Characterize degradation (gradual vs catastrophic)

### 4. Modality Ablation (line 454-458)
**Missing**:
- Compare accuracy under subsets of modalities
- Test which modality combinations preserve accuracy
- Minimum modality set for reasonable performance

---

## Additional Missing Components

### Decoder Validation (Section 4.8, line 459)

❌ **MISSING**:
- Round-trip validation PRIOR to evaluation
- Report round-trip accuracy for D1, D2, D3 separately
- Synthetic test suite for decoder
- This is prerequisite for model evaluation

### Reproducibility Requirements

❌ **MISSING**:
- Random seed documentation
- Cached LLM responses (for reproducibility)
- Deterministic instance generation
- Version pinning for all dependencies

---

## Summary: What's Missing

### Critical Gaps (Must Fix)

1. **Materials science KB** (not medical) - paper specifies this
2. **All 13 partition strategies** tested (not just κ_rule)
3. **Three-stage decoder** (D1 → D2 → D3) not just two
4. **Parallel distractor sets** (3 strategies × instances)
5. **Complete Section 4.3 statistics** (5 subsections all missing)
6. **Error taxonomy** (5 error types, full classification)
7. **Chain-of-thought evaluation** (doubles evaluation effort)
8. **Scaling analyses** (3 types: model, theory size, modality ablation)
9. **Graded scoring for Level 3** (5-level partial credit)

### Scale Impact

**Instance Count**:
- Current plan: 500-1000 instances
- With all partitions: 39 partition-KB pairs × ~30 instances each = **1170+ instances minimum**
- With distractor variants: Could be 3x if parallel sets

**Evaluation Effort**:
- 5 models × 4 modalities × 1170 instances = **23,400 evaluations** (direct)
- With CoT: ×2 = **46,800 evaluations**
- With theory size variants: +20-30%

### Module Additions Needed

**Not in roadmap but required by paper**:
1. experiments/statistics.py (Section 4.3) - 5 statistical analyses
2. experiments/error_taxonomy.py (Section 4.6)
3. experiments/scaling_analysis.py (Section 4.7)
4. experiments/cot_prompting.py (Section 4.7)
5. experiments/graded_scoring.py (Section 4.5)
6. codec/d3_decoder.py (semantic parser)
7. generation/language_bias.py (ar_max and P+ variations)

---

## Recommendation

The current NEURIPS_ROADMAP underestimates the paper's requirements by approximately **2-3x**.

**Revised Timeline**: 12-16 weeks (not 8) for full paper implementation

**OR**: Adjust paper to match MVP+roadmap scope (reduce to 2 KBs, 2-3 modalities, simpler analyses)

Let me create an updated roadmap that matches the paper exactly.
