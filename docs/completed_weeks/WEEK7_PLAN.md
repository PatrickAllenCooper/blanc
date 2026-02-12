# Week 7 Plan: Decoder Validation + 90% Coverage

**Goal**: Validate complete codec and achieve 90% test coverage  
**Timeline**: Week 7 of 14  
**Current Coverage**: 77%  
**Target Coverage**: 90% (+13%)

---

## Week 7 Objectives

### 1. Round-Trip Validation (Section 4.8)

**Tasks**:
- Validate all modality/decoder combinations
- Measure recovery rates on 374 instances
- Targets:
  - D1 (exact): 100%
  - D2 (template): >95%
  - D3 (semantic): >90%
  - Per modality reporting

**Estimate**: 4-6 hours

---

### 2. Coverage to 90% (+13%)

**Current**: 77%  
**Target**: 90%  
**Gap**: 13 percentage points

**Add tests for**:
- Conversion edge cases (65% → 85%)
- Encoder M4 completeness (38% → 70%)
- Knowledge base operations (29% → 60%)
- Core modules gap filling

**New tests needed**: 40-60 tests

**Estimate**: 8-12 hours

---

### 3. Pre-Evaluation Validation

**Tasks**:
- Encode all 374 gold hypotheses
- Apply three-stage decoder
- Report recovery rates
- Verify >95% threshold

**Estimate**: 2-3 hours

---

### 4. Documentation

**Tasks**:
- Decoder validation report
- Round-trip accuracy tables
- Week 7 completion report

**Estimate**: 2-3 hours

---

## Total Week 7 Estimate

**Hours**: 16-24 hours  
**Days**: 2-3 days focused work  
**Complexity**: MEDIUM

---

## Week 7 Execution Plan

### Day 1: Round-Trip Validation (6-8 hours)

**Morning**:
1. Create round-trip validation script
2. Test M4+D1 (baseline - should be 100%)
3. Test M3+D1/D2

**Afternoon**:
4. Test M2+D2
5. Test M1+D2/D3
6. Collect recovery statistics

---

### Day 2: Coverage Push (8-10 hours)

**Morning**:
7. Add conversion tests (15-20 tests)
8. Add encoder tests (10-15 tests)

**Afternoon**:
9. Add KB operation tests (10-15 tests)
10. Add integration tests (5-10 tests)
11. Verify 90% target reached

---

### Day 3: Documentation (2-3 hours)

**All Day**:
12. Week 7 completion report
13. Validation documentation
14. Prepare for Week 8

---

## Success Criteria

- [ ] All modality/decoder pairs validated
- [ ] Round-trip >95% overall
- [ ] Coverage >=90%
- [ ] Validation report complete
- [ ] Ready for Week 8 (LLM evaluation)

---

**Ready to execute Week 7** ✅

**Author**: Patrick Cooper  
**Date**: 2026-02-12
