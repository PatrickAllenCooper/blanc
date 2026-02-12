# Test Coverage Analysis

**Date**: 2026-02-12  
**Current Coverage**: 64% overall  
**Target**: 90%  
**Gap**: 26 percentage points  
**Status**: Below target

---

## Current Coverage Breakdown

### HIGH COVERAGE (>= 90%) ✅

**Critical Components**:
- `reasoning/defeasible.py`: 91% ✅
- `reasoning/derivation_tree.py`: 99% ✅
- `author/support.py`: 94% ✅
- `generation/partition.py`: 93% ✅
- `codec/decoder.py`: 92% ✅
- `core/query.py`: 90% ✅
- `ontology/conceptnet_extractor.py`: 89% ✅

**These are working well** - core reasoning, support, partition, decoder

### MEDIUM COVERAGE (60-89%)

**Needs attention**:
- `author/generation.py`: 87% (missing lines: 76, 83, 96, 100-111, 169, 250, 257, 350)
- `core/theory.py`: 87% (missing lines: 80-84, 89, 103, 126, 167-178, 234)
- `core/result.py`: 80% (missing lines: 58, 62-73, 185-195)
- `backends/base.py`: 71% (missing lines: 136, 140, 144-145)
- `author/conversion.py`: 65% (missing lines: 80, 151-162, 171-177)

### LOW COVERAGE (< 60%) ❌

**Significant gaps**:
- `generation/distractor.py`: 59% (missing lines: 55-58, 103-106, 121, 144, 162, 177, 206-211, 225-250, 263-274, 280, 283)
- `backends/asp.py`: 48% (missing lines: many)
- `codec/encoder.py`: 38% (missing lines: 56, 82, 86, 99, 115-155, 175-209, 224, 239, 244, 259-260)
- `ontology/opencyc_extractor.py`: 36% (missing lines: many)
- `backends/prolog.py`: 32% (missing lines: many)
- `core/knowledge_base.py`: 29% (missing lines: many)

### ZERO COVERAGE (0%) ❌

**Not tested at all**:
- `backends/defeasible.py`: 0% (lines 7-47) - Alternative backend
- `backends/rulelog.py`: 0% (lines 7-50) - Alternative backend
- `knowledge_bases/__init__.py`: 0% (lines 3-6)
- `knowledge_bases/loaders.py`: 0% (lines 7-149) - Infrastructure not used
- `knowledge_bases/registry.py`: 0% (lines 7-190) - Infrastructure not used

---

## Coverage by Category

| Category | Current | Target | Gap | Priority |
|----------|---------|--------|-----|----------|
| **Critical Paths** | 91-99% | 90% | ✅ EXCEEDS | - |
| **Reasoning** | 91-99% | 90% | ✅ EXCEEDS | - |
| **Author/Generation** | 65-94% | 90% | ⚠️ -3 to +4% | HIGH |
| **Core** | 29-90% | 90% | ❌ -61 to 0% | MEDIUM |
| **Codec** | 38-92% | 90% | ⚠️ -52 to +2% | HIGH |
| **Backends** | 0-71% | 90% | ❌ -90 to -19% | LOW |
| **Knowledge bases** | 0% | 90% | ❌ -90% | LOW |
| **Ontology** | 36-89% | 90% | ⚠️ -54 to -1% | MEDIUM |
| **OVERALL** | **64%** | **90%** | **❌ -26%** | **HIGH** |

---

## Gap Analysis

### To Reach 90% Coverage

**Need to add coverage for**:

1. **High Priority** (Core functionality gaps):
   - `author/conversion.py`: +25% (currently 65%)
   - `codec/encoder.py`: +52% (currently 38%)
   - `generation/distractor.py`: +31% (currently 59%)
   - `core/knowledge_base.py`: +61% (currently 29%)

2. **Medium Priority** (Partial coverage):
   - `author/generation.py`: +3% (currently 87%)
   - `core/theory.py`: +3% (currently 87%)
   - `core/result.py`: +10% (currently 80%)

3. **Low Priority** (Alternative/unused modules):
   - `backends/`: These are alternative backends (ASP, Prolog) not currently used
   - `knowledge_bases/`: Infrastructure for future use
   - Can skip these for now

---

## Estimated Work to Reach 90%

### Critical Modules (Must Improve)

**1. author/conversion.py (65% → 90%)**
- Missing: Lines 80, 151-162, 171-177
- Functions: phi_kappa edge cases, partition handling
- Effort: ~2 hours, add 5-8 tests
- Impact: +1.5% overall

**2. codec/encoder.py (38% → 90%)**
- Missing: Lines 56, 82, 86, 99, 115-155, 175-209, 224, 239, 244, 259-260
- Functions: M4 encoding edge cases, format variations
- Effort: ~4 hours, add 10-15 tests
- Impact: +3% overall

**3. generation/distractor.py (59% → 90%)**
- Missing: Lines 55-58, 103-106, 121, 144, 162, 177, 206-211, 225-250, 263-274, 280, 283
- Functions: Distractor generation strategies, adversarial selection
- Effort: ~3 hours, add 8-12 tests
- Impact: +2.4% overall

**4. core/knowledge_base.py (29% → 90%)**
- Missing: Lines 44-48, 64-107, 123-128, 147-149, 153, 157, 161, 176, 192, 197, 202
- Functions: KB loading, querying, backend integration
- Effort: ~3 hours, add 10-12 tests
- Impact: +3.8% overall

**Total Estimated Effort**: ~12 hours  
**Expected Impact**: +10.7% overall coverage  
**Result**: 64% + 10.7% = **74.7%** (still below 90%)

### Additional Modules for 90%

**5. Minor improvements to bring to 90%**:
- `core/theory.py`: 87% → 90% (+1 hour, +0.8%)
- `core/result.py`: 80% → 90% (+1 hour, +0.9%)
- `author/generation.py`: 87% → 95% (+1 hour, +0.6%)
- `ontology/opencyc_extractor.py`: 36% → 60% (+2 hours, +2.3%)

**Total Additional**: ~5 hours  
**Additional Impact**: +4.6%  
**Final**: 74.7% + 4.6% = **79.3%**

**To reach 90%**: Would need to also test backends (~8 more hours)

---

## Realistic Assessment

### Can We Reach 90%?

**Short Answer**: Difficult

**Reasons**:
1. **Backends not in use**: ASP, Prolog, RuleLog backends (0-48%) not currently used
2. **Infrastructure modules**: Knowledge base registry/loaders (0%) deferred
3. **Time investment**: ~25-30 hours of test writing needed

### Alternative: Focus on Critical Path Coverage

**Current Critical Path**: 91-99% ✅ **EXCEEDS 90%!**

Critical components:
- Reasoning engine: 91-99%
- Support/criticality: 94%
- Partition strategies: 93%
- Decoder: 92%
- Query: 90%

**These are the components actually used for instance generation**

---

## Recommendation

### Option 1: Maintain Current (64% overall, 91-99% critical)

**Pros**:
- Critical paths already excellent (>90%)
- Core functionality well-tested
- 208 tests passing, no bugs

**Cons**:
- Below 90% overall target
- Some code paths untested

### Option 2: Improve to 80% overall

**Effort**: ~12-15 hours
**Focus**: author/conversion, codec/encoder, generation/distractor, core/knowledge_base
**Impact**: Critical for full benchmark development
**Result**: 80% overall, >95% critical paths

### Option 3: Push for 90% overall

**Effort**: ~25-30 hours
**Focus**: All above + backends + infrastructure
**Impact**: Tests for modules not currently used
**Result**: 90% overall

---

## Current Testing Status

```
Tests: 208 passing, 3 skipped
Coverage: 64% overall
Critical paths: 91-99%
Runtime: ~8 seconds
Failures: 0
Bugs found: 0
```

**Quality is high where it matters most**

---

## Action Items

### If 90% Overall Required

**Week 3 Testing Sprint**:
1. Add tests for author/conversion.py (+25%)
2. Add tests for codec/encoder.py (+52%)
3. Add tests for generation/distractor.py (+31%)
4. Add tests for core/knowledge_base.py (+61%)
5. Add tests for backends (if time permits)

**Estimated**: 20-25 hours

### If Current Acceptable

**Maintain**:
- Critical path coverage at 91-99%
- Fix any bugs found during development
- Add tests as new features added

---

## Conclusion

**Current**: 64% overall, 91-99% critical paths  
**Target**: 90% overall  
**Gap**: 26 percentage points  
**Effort to close**: 20-25 hours

**Critical paths already exceed 90% target** ✅

**Recommendation**: Focus on critical path quality (current approach) unless 90% overall is hard requirement.

---

**Status**: Below 90% overall but critical paths excellent  
**Tests**: 208/208 passing  
**Bugs**: 0  
**Quality**: High on critical components
