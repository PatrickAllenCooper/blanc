# Test Coverage Expansion Plan: 64% → 90%

**Current**: 64% overall, 91-99% critical paths  
**Target**: 90% overall  
**Gap**: 26 percentage points  
**Timeline**: Weeks 4-7 (as we develop)

---

## Strategy

**Approach**: Add tests incrementally as we develop new features

**NOT**: Stop development to write tests  
**BUT**: Add tests for each new feature as we build it

**Target**: 90% by end of Week 7 (codec complete)

---

## Current Coverage Gaps

### HIGH PRIORITY (Core Functionality)

**1. author/conversion.py: 65% → 90% (+25%)**

**Missing lines**: 80, 151-162, 171-177
- Wrapper functions (convert_theory_to_defeasible variations)
- Edge cases in partition handling

**Impact**: +1.5% overall coverage  
**Effort**: 5-8 tests, ~2 hours  
**When**: Week 4 (during statistical analysis)

**2. codec/encoder.py: 38% → 90% (+52%)**

**Missing lines**: 56, 82, 86, 99, 115-155, 175-209, 224, 239, 244, 259-260
- M4 encoding edge cases
- Format variations

**Impact**: +3% overall coverage  
**Effort**: 10-15 tests, ~4 hours  
**When**: Week 5-6 (as we build M2-M3)

**3. generation/distractor.py: 59% → 90% (+31%)**

**Missing lines**: 55-58, 103-106, 121, 144, 162, 177, 206-211, 225-250, 263-274, 280, 283
- Adversarial distractor generation
- Random distractor strategies

**Impact**: +2.4% overall coverage  
**Effort**: 8-12 tests, ~3 hours  
**When**: Week 4 (during instance analysis)

**4. core/knowledge_base.py: 29% → 90% (+61%)**

**Missing lines**: 44-48, 64-107, 123-128, 147-149, 153, 157, 161, 176, 192, 197, 202
- KB loading
- Backend integration

**Impact**: +3.8% overall coverage  
**Effort**: 10-12 tests, ~3 hours  
**When**: Week 5 (as we integrate KBs with codec)

---

### MEDIUM PRIORITY (Supporting Code)

**5. core/theory.py: 87% → 95% (+8%)**

**Impact**: +0.8% overall  
**Effort**: 2-3 tests, ~1 hour  
**When**: Week 4

**6. core/result.py: 80% → 95% (+15%)**

**Impact**: +0.9% overall  
**Effort**: 3-4 tests, ~1 hour  
**When**: Week 5

**7. author/generation.py: 87% → 95% (+8%)**

**Impact**: +0.6% overall  
**Effort**: 2-3 tests, ~1 hour  
**When**: Week 5-6 (as we develop Level 3)

---

### LOW PRIORITY (Alternative Implementations)

**8. backends/**: 0-48% (not used currently)

**Skip for now**: Alternative backends not in critical path

---

## Weekly Test Goals

### Week 4: 64% → 72% (+8%)

**Add tests for**:
- author/conversion.py edge cases (5-8 tests)
- generation/distractor.py strategies (8-12 tests)
- core/theory.py improvements (2-3 tests)

**Effort**: ~6 hours total  
**Integration**: As we do statistical analysis

**Target**: 72% by end of Week 4

---

### Week 5: 72% → 80% (+8%)

**Add tests for**:
- codec/encoder.py (M2-M3 as we build them) (10-15 tests)
- core/knowledge_base.py (KB integration) (5-8 tests)
- core/result.py (result handling) (3-4 tests)

**Effort**: ~8 hours total  
**Integration**: As we build M2-M3 encoders

**Target**: 80% by end of Week 5

---

### Week 6: 80% → 85% (+5%)

**Add tests for**:
- codec/encoder.py (M1 encoder) (5-10 tests)
- codec/decoder.py (D2-D3 decoders) (8-12 tests)
- author/generation.py (Level 3) (2-3 tests)

**Effort**: ~6 hours total  
**Integration**: As we build M1 and D2-D3

**Target**: 85% by end of Week 6

---

### Week 7: 85% → 90% (+5%)

**Add tests for**:
- Round-trip validation
- Decoder edge cases
- Integration tests

**Effort**: ~4 hours total  
**Integration**: During decoder validation

**Target**: 90% by end of Week 7 ✅

---

## Total Effort to 90%

**Hours**: ~24 hours (spread over 4 weeks)  
**Per week**: ~6 hours  
**Integration**: As we build features (not separate)

**Approach**: Test-driven development for Weeks 4-7

---

## Week 4 Specific Plan

### Day 1: Statistical Analysis + Conversion Tests

**Development**:
- Complete 4.3.1 volume/balance (2 hours)
- Begin 4.3.2 difficulty distributions (2 hours)

**Testing** (2 hours):
- Add 5-8 tests for author/conversion.py
- Test partition edge cases
- Test theory conversion variations

**Coverage gain**: +1.5%

### Day 2: Difficulty Analysis + Distractor Tests

**Development**:
- Complete 4.3.2 difficulty distributions (2 hours)
- Begin 4.3.5 partition sensitivity (2 hours)

**Testing** (2 hours):
- Add 8-12 tests for generation/distractor.py
- Test random distractor generation
- Test adversarial distractors

**Coverage gain**: +2.4%

### Day 3: Yield Analysis + Theory Tests

**Development**:
- Complete 4.3.4 yield model fitting (2 hours)
- Complete 4.3.5 partition tests (2 hours)

**Testing** (2 hours):
- Add 2-3 tests for core/theory.py
- Test theory operations
- Integration tests

**Coverage gain**: +0.8%

**Week 4 Total**: +4.7% (64% → 68.7%)

---

## Testing Guidelines

### Test-Driven Development

**For each new feature**:
1. Write test first (TDD)
2. Implement feature
3. Verify test passes
4. Check coverage increase

### Focus Areas

**Week 4**: Conversion, distractor, theory  
**Week 5**: Encoder, KB loading  
**Week 6**: Decoder, M1 encoder  
**Week 7**: Validation, integration

### Coverage Tracking

**After each day**:
```bash
python -m pytest tests/ --cov=src/blanc --cov-report=term
```

**Target progression**:
- Week 4 end: 72%
- Week 5 end: 80%
- Week 6 end: 85%
- Week 7 end: 90% ✅

---

## Immediate Action (Week 4 Day 1)

### Morning: Statistical Analysis + Tests

**Development** (2 hours):
1. Complete volume/balance analysis
2. Chi-square tests
3. Joint distribution tables

**Testing** (2 hours):
4. Add tests for `author/conversion.py`
   - Test partition_leaf edge cases
   - Test partition_depth with empty depths
   - Test partition_random with different seeds
   - Test theory conversion error handling
   - Test wrapper function variations

**Files to create**:
- `tests/author/test_conversion_extended.py` (new)

**Expected coverage**: 64% → 66%

---

## Success Metrics

**Week 4**: 64% → 72% (+8%)  
**Week 5**: 72% → 80% (+8%)  
**Week 6**: 80% → 85% (+5%)  
**Week 7**: 85% → 90% (+5%)

**Total**: 64% → 90% (+26%) over 4 weeks

**Integrated with development**: ✅  
**No separate testing sprint**: ✅  
**Test as we build**: ✅

---

## Commitment

**Every new feature gets tests**  
**Coverage checked daily**  
**90% target by Week 7 end**

**Starting now with Week 4** ✅

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Coverage expansion plan created, ready to execute
