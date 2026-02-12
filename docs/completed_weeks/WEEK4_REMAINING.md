# Week 4 Remaining Work

**Date**: 2026-02-12  
**Current Status**: Week 4 Day 1 started  
**Goal**: Complete Section 4.3 + Reach 72% coverage

---

## ✅ COMPLETED (Week 4 Day 1)

### Statistical Analysis
- [x] Framework implemented (`experiments/statistics.py`)
- [x] Section 4.3.1: Volume and balance (basic implementation)
- [x] Results structure created (`results/statistical_analysis.json`)
- [x] Yield curves computed (from Week 3)

### Test Coverage
- [x] Test expansion plan created
- [x] 11 new conversion tests added (`test_conversion_extended.py`)
- [x] Coverage baseline established (64%)

---

## ❌ REMAINING (Week 4 Days 2-3)

### Section 4.3.1: Volume and Balance (2-3 hours)

**Complete**:
- [ ] Joint distribution table (KB × partition × level)
- [ ] Chi-square test implementation (fix and run)
- [ ] Identify underpopulated cells
- [ ] Create publication figure for volume/balance

**Files to update**:
- `experiments/statistics.py` (enhance section_4_3_1)

---

### Section 4.3.2: Structural Difficulty Distributions (4-6 hours)

**Implement**:
- [ ] Extract full σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*) from all 374 instances
- [ ] Compute marginal distributions for each component
- [ ] Plot histograms for each difficulty component
- [ ] Compute joint distributions
- [ ] Mutual information estimates
- [ ] Test independence hypotheses

**Files to create/update**:
- `experiments/statistics.py` (complete section_4_3_2)
- `experiments/difficulty_analysis.py` (detailed analysis)
- `figures/difficulty_histograms.png`

---

### Section 4.3.4: Yield Analysis (2-3 hours)

**Complete**:
- [ ] Fit parametric models (linear, logistic, power-law) to yield curves
- [ ] Compute R² for each model
- [ ] Statistical significance tests for monotonicity
- [ ] Test for phase transitions
- [ ] Publication-quality yield curve figure

**Files to update**:
- `scripts/compute_yield_curves_dev.py` (add model fitting)
- `experiments/statistics.py` (integrate yield analysis)
- `figures/yield_curves_publication.png`

**Current**: Curves computed, need model fitting and tests

---

### Section 4.3.5: Partition Sensitivity (3-4 hours)

**Implement**:
- [ ] Group instances by partition family (structured, depth, random)
- [ ] Extract difficulty measures for each group
- [ ] Kolmogorov-Smirnov two-sample tests
- [ ] Mann-Whitney U tests
- [ ] Compare difficulty distributions across families
- [ ] Statistical significance assessment
- [ ] Publication figure

**Files to create**:
- `experiments/partition_sensitivity.py`
- `figures/partition_comparison.png`

---

### Test Coverage: 64% → 72% (+8%)

**Add tests for** (4-6 hours):

1. **Distractor generation** (8-12 tests):
   - [ ] Test random distractor strategy
   - [ ] Test syntactic distractor strategy
   - [ ] Test adversarial distractor strategy
   - [ ] Test distractor validation
   - [ ] Edge cases

2. **Theory operations** (2-3 tests):
   - [ ] Test theory merging
   - [ ] Test theory subsetting
   - [ ] Test rule addition/removal

3. **Results handling** (3-4 tests):
   - [ ] Test result formatting
   - [ ] Test metadata handling
   - [ ] Test error cases

**Files to create**:
- `tests/generation/test_distractor_extended.py`
- `tests/core/test_theory_extended.py`
- `tests/core/test_result_extended.py`

---

## Week 4 Completion Checklist

### Statistical Analysis (5 subsections)

- [x] 4.3.1: Volume and balance (basic) - 40% done
- [ ] 4.3.1: Complete with figures - 60% remaining
- [ ] 4.3.2: Difficulty distributions - 100% remaining
- [x] 4.3.3: Novelty/revision (deferred - need Level 3)
- [x] 4.3.4: Yield curves computed - 60% done
- [ ] 4.3.4: Model fitting and tests - 40% remaining
- [ ] 4.3.5: Partition sensitivity - 100% remaining

**Overall**: 2/5 subsections complete, 3 remaining

---

### Test Coverage

- [x] Coverage plan created
- [x] 11 conversion tests added
- [ ] 8-12 distractor tests
- [ ] 2-3 theory tests
- [ ] 3-4 result tests

**Current**: 64% (estimated with new tests)  
**Target**: 72%  
**Remaining**: ~15-20 more tests

---

### Documentation

- [x] Week 4 checklist created
- [x] Coverage expansion plan created
- [ ] Week 4 completion report
- [ ] Statistical analysis documentation
- [ ] Figure generation for paper

---

## Time Estimate to Complete Week 4

### Remaining Work

**Statistical Analysis**: 11-16 hours
- 4.3.1 complete: 2-3 hours
- 4.3.2 full implementation: 4-6 hours
- 4.3.4 model fitting: 2-3 hours
- 4.3.5 partition sensitivity: 3-4 hours

**Test Coverage**: 4-6 hours
- Distractor tests: 2-3 hours
- Theory tests: 1 hour
- Result tests: 1-2 hours

**Documentation**: 2 hours
- Week 4 completion report
- Figure descriptions

**Total**: 17-24 hours (2-3 full days)

---

## Prioritized Task List (Execute in Order)

### Priority 1: Complete Statistical Analysis (Critical)

1. ✅ Fix and run Section 4.3.1 completely (~1 hour)
2. ❌ Implement Section 4.3.2 difficulty distributions (~4 hours)
3. ❌ Complete Section 4.3.4 yield model fitting (~2 hours)
4. ❌ Implement Section 4.3.5 partition sensitivity (~3 hours)

**Sub-total**: ~10 hours

### Priority 2: Test Coverage to 72% (Important)

5. ❌ Add distractor tests (8-12 tests, ~2 hours)
6. ❌ Add theory tests (2-3 tests, ~1 hour)
7. ❌ Add result tests (3-4 tests, ~1 hour)
8. ✅ Conversion tests done (11 tests)

**Sub-total**: ~4 hours

### Priority 3: Documentation (Nice to have)

9. ❌ Create publication figures (~2 hours)
10. ❌ Week 4 completion report (~1 hour)

**Sub-total**: ~3 hours

---

## TOTAL REMAINING: ~17 hours (2-3 days)

---

## Next Immediate Actions

**Today** (4-6 hours):
1. Fix statistical analysis unicode issue
2. Complete Section 4.3.2 (difficulty distributions)
3. Add distractor tests (8-12 tests)

**Tomorrow** (4-6 hours):
4. Complete yield model fitting (4.3.4)
5. Implement partition sensitivity (4.3.5)
6. Add theory and result tests

**Day 3** (3-4 hours):
7. Create publication figures
8. Week 4 completion documentation
9. Verify 72% coverage achieved

---

## Blockers

**None** ✅

All infrastructure is working, just need execution time.

---

**Summary**: ~17 hours of work remaining to complete Week 4

**Author**: Patrick Cooper  
**Date**: 2026-02-12
