# Weeks 4-7 Ready: Statistical Analysis + Codec Development

**Date**: 2026-02-12  
**Status**: ✅ READY TO EXECUTE  
**Timeline**: 4 weeks (Week 4-7 of 14)

---

## What's Complete (Weeks 1-3)

✅ **Expert KB Foundation**: 2,318 rules from 4 institutions  
✅ **Development Instances**: 374 from all 3 domains  
✅ **Infrastructure**: All working, 208 tests passing  
✅ **Week 3**: Complete with yield analysis

**Ready to proceed with Weeks 4-7** ✅

---

## Week 4: Statistical Analysis + Coverage to 72%

### Checklist Created ✅

- `WEEK4_CHECKLIST.md` - Complete task breakdown
- `COVERAGE_EXPANSION_PLAN.md` - 64% → 90% roadmap

### Tasks (2-3 days)

**Statistical Analysis** (Section 4.3):
1. Complete volume/balance (chi-square tests)
2. Difficulty distributions (extract σ(I) tuples)
3. Yield model fitting (linear, logistic, power-law)
4. Partition sensitivity (two-sample tests)

**Test Coverage** (+8%):
5. Add conversion tests (5-8 tests)
6. Add distractor tests (8-12 tests)
7. Add theory tests (2-3 tests)

**Deliverables**:
- `experiments/statistics.py` (framework created ✅)
- `results/statistical_analysis.json`
- Publication figures
- +8% test coverage (64% → 72%)

**Status**: Framework implemented, ready to execute

---

## Week 5: M2-M3 Encoders + Coverage to 80%

### Tasks (5-7 days)

**Codec Development**:
1. M3 encoder (annotated formal)
2. M2 encoder (semi-formal)
3. D2 decoder (template extraction)
4. NL mapping for all 3 KBs

**Test Coverage** (+8%):
5. Encoder tests as we build (10-15 tests)
6. KB loading tests (5-8 tests)
7. Result handling tests (3-4 tests)

**Deliverables**:
- `src/blanc/codec/m3_encoder.py`
- `src/blanc/codec/m2_encoder.py`
- `src/blanc/codec/d2_decoder.py`
- `src/blanc/codec/nl_mapping.py`
- +8% coverage (72% → 80%)

---

## Week 6: M1 Encoder + D3 + Coverage to 85%

### Tasks (5-7 days)

**Codec Development**:
1. M1 encoder (narrative - hardest)
2. D3 decoder (semantic parser)
3. Three-stage decoder integration (D1→D2→D3)

**Test Coverage** (+5%):
4. M1 encoder tests (5-10 tests)
5. D2-D3 decoder tests (8-12 tests)
6. Generation tests (2-3 tests)

**Deliverables**:
- `src/blanc/codec/m1_encoder.py`
- `src/blanc/codec/d3_decoder.py`
- `src/blanc/codec/cascading_decoder.py`
- +5% coverage (80% → 85%)

---

## Week 7: Decoder Validation + Coverage to 90%

### Tasks (3-5 days)

**Validation**:
1. Round-trip testing (all modalities)
2. >95% recovery target validation
3. Pre-evaluation validation

**Test Coverage** (+5%):
4. Validation tests
5. Integration tests
6. Edge case tests

**Deliverables**:
- Complete round-trip validation
- Decoder validation report
- +5% coverage (85% → 90%) ✅

---

## Coverage Progression

| Week | Tasks | Coverage | Gain |
|------|-------|----------|------|
| 3 (done) | Instances | 64% | baseline |
| 4 | Statistics | 72% | +8% |
| 5 | M2-M3, D2 | 80% | +8% |
| 6 | M1, D3 | 85% | +5% |
| 7 | Validation | 90% | +5% |

**Total gain**: +26% over 4 weeks

---

## Test-Driven Development

### Approach

**For each new feature**:
1. Write test first (or alongside)
2. Implement feature
3. Verify test passes
4. Check coverage increase

### Daily Routine

**Each day**:
```bash
# After development
python -m pytest tests/ --cov=src/blanc --cov-report=term

# Check coverage increase
# Target: ~1-2% gain per day
```

### Weekly Check

**End of each week**:
- Verify coverage target met
- Document new tests
- Update coverage report

---

## Immediate Next Steps (Week 4 Day 1)

### Morning (3-4 hours)

1. **Complete volume/balance analysis**
   - Joint distribution table
   - Chi-square tests
   - Publication figure

2. **Add conversion tests**
   - Create `tests/author/test_conversion_extended.py`
   - Test all partition functions
   - Test edge cases
   - **Target**: +1.5% coverage

### Afternoon (3-4 hours)

3. **Extract difficulty tuples**
   - Parse all 374 instances
   - Extract σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*)
   - Compute distributions

4. **Add distractor tests**
   - Create `tests/generation/test_distractor_extended.py`
   - Test random strategy
   - Test adversarial strategy
   - **Target**: +2.4% coverage

**Day 1 Goal**: 64% → 68% (+4%)

---

## Resources Needed

**Python packages**: scipy, numpy, matplotlib (have these) ✅  
**Instances**: 374 development instances (have these) ✅  
**Infrastructure**: All working (have this) ✅  
**Time**: 11-16 hours per week for 4 weeks

**Blockers**: None ✅

---

## Success Criteria (Weeks 4-7)

**By Week 7 end**:
- [ ] Section 4.3 complete (all 5 subsections)
- [ ] Complete codec (M1-M4, D1-D3)
- [ ] Round-trip >95% validated
- [ ] Test coverage 90%
- [ ] Ready for Week 8 (LLM evaluation)

---

**Ready to begin Week 4 Day 1 development** ✅

**Approach**: Build features + add tests as we go  
**Target**: 90% coverage by Week 7  
**Timeline**: 4 weeks focused work

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Weeks 4-7 plan complete, ready to execute
