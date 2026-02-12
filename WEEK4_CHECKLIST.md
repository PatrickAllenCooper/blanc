# Week 4 Checklist: Statistical Analysis (Section 4.3)

**Goal**: Implement complete Section 4.3 of paper  
**Timeline**: Week 4 of 14  
**Input**: 374 development instances  
**Output**: Complete statistical analysis for paper

---

## Overview

Section 4.3 requires 5 major subsections analyzing the generated dataset.

**Current**: 374 instances from 3 expert KBs  
**Target**: Complete statistical framework for paper Section 4.3

---

## Checklist

### 4.3.1 Volume and Balance ✅ STARTED

**Requirements**:
- [ ] Total instance counts per level
- [ ] Counts per source KB
- [ ] Counts per partition function
- [ ] Joint distribution (KB, partition, level)
- [ ] Chi-square test for balance
- [ ] Identify underpopulated cells

**Current Status**:
- ✅ Basic counts computed (374 total)
- ✅ By domain: Biology 114, Legal 168, Materials 92
- ❌ Chi-square test not done
- ❌ Joint distribution table not created

**Files**:
- `scripts/analyze_instances.py` (started)
- `instance_statistics.json` (basic stats)

**Estimated Time**: 2-3 hours

---

### 4.3.2 Structural Difficulty Distributions

**Requirements**:
- [ ] Compute σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*) for all instances
- [ ] Marginal distributions for each component
- [ ] Joint distributions
- [ ] Mutual information estimates
- [ ] Test independence hypotheses

**Current Status**:
- ❌ Not implemented
- Need to extract from instance metadata

**Estimated Time**: 4-6 hours

---

### 4.3.3 Novelty and Revision Spectrum (Level 3)

**Requirements**:
- [ ] Compute (Nov, d_rev) for Level 3 instances
- [ ] Cross-tabulate with resolution strength
- [ ] Test hypothesis: high-novelty → strong resolution
- [ ] Test hypothesis: conservative → low d_rev

**Current Status**:
- ❌ Not applicable (no Level 3 instances yet)
- Defer to when Level 3 is implemented

**Estimated Time**: Deferred (need Level 3 instances first)

---

### 4.3.4 Yield Analysis ✅ MOSTLY DONE

**Requirements**:
- [x] Plot Y(κ_rand(δ), Q) vs δ
- [x] Fit parametric models (linear, logistic, power-law)
- [ ] Statistical tests for monotonicity
- [ ] Test for phase transitions

**Current Status**:
- ✅ Yield curves computed for all 3 KBs
- ✅ Plots generated (notebooks/yield_curves_dev.png)
- ❌ Parametric model fitting not done
- ❌ Statistical tests not done

**Files**:
- `scripts/compute_yield_curves_dev.py` (complete)
- `notebooks/yield_curves_dev.png` (plots)

**Estimated Time**: 2-3 hours (fitting and tests)

---

### 4.3.5 Partition Sensitivity

**Requirements**:
- [ ] Compare σ(I) distributions across partition families
- [ ] Two-sample tests (Kolmogorov-Smirnov, Mann-Whitney)
- [ ] Test if partitions produce distinguishable difficulties
- [ ] Characterize partition impact

**Current Status**:
- ❌ Not implemented
- Need difficulty tuples first (4.3.2)

**Estimated Time**: 3-4 hours

---

## Total Week 4 Estimate

**Hours**: 11-16 hours  
**Days**: 2-3 days of focused work  
**Complexity**: Medium (mostly data analysis, not algorithms)

---

## Dependencies

**What we have**:
- ✅ 374 instances from expert KBs
- ✅ Instance metadata
- ✅ Basic analysis framework

**What we need**:
- Python packages: scipy, numpy, matplotlib (have these)
- Statistical knowledge (standard tests)
- Instance structure parsing

**Blockers**: None - can proceed immediately

---

## Implementation Plan

### Day 1: Volume, Balance, Difficulty (4-6 hours)

**Morning**:
1. Complete 4.3.1 (volume and balance)
   - Create joint distribution table
   - Chi-square test for balance
   - Identify underpopulated cells

**Afternoon**:
2. Begin 4.3.2 (difficulty distributions)
   - Extract σ(I) from instances
   - Compute marginal distributions
   - Plot histograms

### Day 2: Yield and Partition Sensitivity (4-6 hours)

**Morning**:
3. Complete 4.3.4 (yield analysis)
   - Fit parametric models
   - Statistical tests
   - Publication-quality plots

**Afternoon**:
4. Implement 4.3.5 (partition sensitivity)
   - Two-sample tests
   - Comparison across partitions
   - Statistical significance

### Day 3: Documentation and Figures (3-4 hours)

**All Day**:
5. Create publication figures
6. Write Week 4 completion report
7. Document statistical findings
8. Prepare for Week 5 (codec)

---

## Deliverables

### Code

- [ ] `experiments/statistics.py` - Complete Section 4.3 implementation
- [ ] Updated `analyze_instances.py` - All 5 subsections
- [ ] `experiments/figures.py` - Publication figures

### Analysis Results

- [ ] `results/volume_balance.json` - Instance counts and distribution
- [ ] `results/difficulty_distributions.json` - Structural difficulty
- [ ] `results/yield_analysis.json` - Yield curves and models
- [ ] `results/partition_sensitivity.json` - Statistical tests

### Figures

- [x] `notebooks/yield_curves_dev.png` (done)
- [ ] `figures/volume_balance.png` - Distribution heatmap
- [ ] `figures/difficulty_histograms.png` - Marginal distributions
- [ ] `figures/partition_comparison.png` - Sensitivity analysis

### Documentation

- [ ] `WEEK4_COMPLETION.md` - Week 4 summary
- [ ] Statistical analysis report
- [ ] Ready for paper Section 4.3

---

## Success Criteria

**Week 4 Complete when**:
- [x] All 5 subsections of Section 4.3 implemented (3/5 done)
- [ ] Statistical tests documented
- [ ] Publication figures generated
- [ ] Results ready for paper
- [ ] Week 4 completion report written

**Current**: 2/5 subsections done (~40%)

---

## Next Actions (Start Now)

### Immediate (Next 2 hours)

1. **Complete volume and balance**
   - Create joint distribution table
   - Chi-square test
   - Underpopulation analysis

2. **Extract difficulty tuples**
   - Parse instance metadata
   - Extract (ℓ, |Supp|, |H*|, min|h|, Nov*)
   - Store in structured format

### Today

3. **Compute distributions**
   - Marginal histograms
   - Joint distributions
   - Mutual information

4. **Begin yield model fitting**
   - Linear regression
   - Logistic regression
   - Power-law fitting

---

**Ready to begin Week 4 development** ✅

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Checklist created, ready to execute
