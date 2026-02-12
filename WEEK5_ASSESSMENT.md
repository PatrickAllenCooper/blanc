# Week 5 Assessment: Codec Development

**Date**: 2026-02-12  
**Current Status**: Starting Week 5  
**Goal**: M3 & M2 Encoders + D2 Decoder + 80% coverage

---

## Week 5 Requirements

From NEURIPS_FULL_ROADMAP.md:

### Goal: Add annotated formal and semi-formal modalities

**Tasks**:
1. **M3 Encoder** (Annotated Formal)
   - Format: Code + comments
   - Target: >95% round-trip accuracy

2. **M2 Encoder** (Semi-Formal)
   - Format: Logical symbols + NL predicates
   - Requires NL mapping for each KB
   - Target: >90% round-trip accuracy

3. **D2 Decoder** (Template Extraction)
   - Edit distance (Levenshtein)
   - Sound + complete (Proposition in paper)
   - Fallback from D1

4. **NL Mapping** (Definition 28 from paper)
   - Create for all 3 KBs
   - Ensure injectivity
   - Compositional via NL_P and NL_C
   - Domain coherence

**Deliverables**:
- `src/blanc/codec/m3_encoder.py`
- `src/blanc/codec/m2_encoder.py`
- `src/blanc/codec/d2_decoder.py`
- `src/blanc/codec/nl_mapping.py`
- 40+ round-trip tests
- 80% test coverage target

**Estimate**: 5-7 days

---

## Current State

### What We Have ✅

**Existing Codec**:
- `encoder.py` - M4 encoder (pure formal) ✅
- `decoder.py` - D1 decoder (exact match) ✅
- `__init__.py` - Package structure

**Tests**:
- `tests/codec/` - 26 tests for M4+D1
- 92% coverage on decoder
- 38% coverage on encoder (only M4 tested)

**Round-trip**: 100% for M4+D1 ✅

---

### What We Need ❌

**New Encoders** (0% complete):
- M3 encoder (annotated formal) - NOT STARTED
- M2 encoder (semi-formal) - NOT STARTED

**New Decoder** (0% complete):
- D2 decoder (template extraction) - NOT STARTED

**NL Mapping** (0% complete):
- Mapping for biology KB - NOT STARTED
- Mapping for legal KB - NOT STARTED
- Mapping for materials KB - NOT STARTED

**Tests** (0% added):
- M3 round-trip tests - NOT STARTED
- M2 round-trip tests - NOT STARTED
- D2 decoder tests - NOT STARTED
- NL mapping tests - NOT STARTED

**Coverage**: Need +14% (66% → 80%)

---

## Week 5 Work Breakdown

### Task 1: M3 Encoder (Annotated Formal) - 8-12 hours

**What it does**:
- Takes rule/fact
- Outputs formal syntax with comments
- Example: `bird(X) => flies(X)  # Birds typically fly`

**Implementation**:
```python
def encode_m3(element, nl_mapping=None):
    \"\"\"Encode element in M3 (annotated formal) format.\"\"\"
    formal = encode_m4(element)  # Reuse M4
    comment = generate_comment(element, nl_mapping)
    return f"{formal}  # {comment}"
```

**Effort**:
- Core encoder: 200-300 lines (~4 hours)
- Comment generation: 100-150 lines (~2 hours)
- Round-trip tests: 10-15 tests (~2 hours)
- Debug and refine: ~2 hours

**Total**: 8-12 hours

---

### Task 2: M2 Encoder (Semi-Formal) - 10-15 hours

**What it does**:
- Takes rule/fact  
- Outputs logical operators + natural language predicates
- Example: `∀X: bird(X) → flies(X)` where predicates use NL

**Implementation**:
```python
def encode_m2(element, nl_mapping):
    \"\"\"Encode element in M2 (semi-formal) format.\"\"\"
    # Logical structure with NL predicates
    # bird(X) becomes "is a bird(X)"
    # flies(X) becomes "can fly(X)"
```

**Effort**:
- Core encoder: 250-350 lines (~5 hours)
- NL mapping integration: 100-150 lines (~2 hours)
- Round-trip tests: 15-20 tests (~3 hours)
- Debug and refine: ~3 hours

**Total**: 10-15 hours

**Dependency**: Requires NL mapping first

---

### Task 3: NL Mapping - 6-8 hours

**What it is**:
- Maps predicates to natural language
- bird(X) → "is a bird"
- flies(X) → "can fly"
- Must be injective (one-to-one)

**Implementation** (for each KB):
```python
NL_MAPPING_BIOLOGY = {
    'bird': 'is a bird',
    'mammal': 'is a mammal',
    'flies': 'can fly',
    'swims': 'can swim',
    ...
}
```

**Effort per KB**: ~2 hours
- Biology: ~50 predicates
- Legal: ~100 predicates
- Materials: ~400 predicates (subset)

**Total**: 6-8 hours for all 3 KBs

---

### Task 4: D2 Decoder (Template Extraction) - 8-12 hours

**What it does**:
- Takes text output from model
- Extracts structure via edit distance (Levenshtein)
- Fallback when D1 (exact match) fails

**Implementation**:
```python
def decode_d2(text, candidates):
    \"\"\"Decode using template extraction.\"\"\"
    # Find closest candidate via Levenshtein distance
    best_match = min(candidates, 
                     key=lambda c: levenshtein(text, c))
    return best_match if distance < threshold else None
```

**Effort**:
- Core decoder: 200-250 lines (~4 hours)
- Template matching: 100-150 lines (~2 hours)
- Round-trip tests: 10-15 tests (~2 hours)  
- Debug and refine: ~2 hours

**Total**: 8-12 hours

---

### Task 5: Test Coverage +14% - 6-8 hours

**Target**: 66% → 80%

**Add tests for**:
- M3 encoder tests: 10-15 tests (~2 hours)
- M2 encoder tests: 15-20 tests (~3 hours)
- D2 decoder tests: 10-15 tests (~2 hours)
- Integration tests: 5-10 tests (~1 hour)

**Total**: 6-8 hours

---

### Task 6: Round-Trip Validation - 4-6 hours

**Test round-trip for each modality**:
- M3+D1 round-trip: Target >95%
- M2+D2 round-trip: Target >90%
- Measure accuracy on all 374 instances

**Effort**:
- Validation script: ~2 hours
- Run on all instances: ~1 hour
- Debug failures: ~2 hours
- Documentation: ~1 hour

**Total**: 4-6 hours

---

## Total Week 5 Estimate

| Task | Hours | Status |
|------|-------|--------|
| M3 Encoder | 8-12 | ❌ Not started |
| M2 Encoder | 10-15 | ❌ Not started |
| NL Mapping | 6-8 | ❌ Not started |
| D2 Decoder | 8-12 | ❌ Not started |
| Test Coverage +14% | 6-8 | ❌ Not started |
| Round-Trip Validation | 4-6 | ❌ Not started |
| **TOTAL** | **42-61 hours** | **0% complete** |

**Days**: 5-8 days of focused work  
**Weeks**: 1-1.5 weeks

---

## Current Dependencies

**Have**:
- ✅ M4 encoder (baseline)
- ✅ D1 decoder (baseline)
- ✅ 374 instances for testing
- ✅ 3 expert KBs

**Need**:
- ❌ NL mappings (create first - needed for M2)
- ❌ M3 encoder
- ❌ M2 encoder (depends on NL mapping)
- ❌ D2 decoder

**Suggested order**:
1. NL mapping (6-8 hours) - foundation
2. M3 encoder (8-12 hours) - easier than M2
3. D2 decoder (8-12 hours) - parallel with M3
4. M2 encoder (10-15 hours) - uses NL mapping
5. Tests and validation (10-14 hours)

---

## Week 5 Complexity

**Complexity**: HIGH

**Why**:
- Building 2 new encoders from scratch
- Building new decoder with edit distance
- Creating NL mappings for 3 KBs
- Round-trip validation with new modalities
- Large code volume (~1,000+ new lines)

**Compared to Week 4**: Week 4 was analysis (use existing data), Week 5 is implementation (build new components)

---

## Recommended Approach

### Phase 1: Foundations (8-12 hours)

**Day 1-2**:
1. Create NL mappings for all 3 KBs (6-8 hours)
2. Test NL mappings (2-3 hours)
3. Basic tests passing

### Phase 2: Encoders (16-24 hours)

**Day 3-4**:
4. Implement M3 encoder (8-12 hours)
5. M3 round-trip tests (2-3 hours)
6. M3 validation on instances

**Day 5-6**:
7. Implement M2 encoder (10-15 hours)
8. M2 round-trip tests (3-4 hours)

### Phase 3: Decoder (12-16 hours)

**Day 6-7**:
9. Implement D2 decoder (8-12 hours)
10. D2 tests (2-3 hours)
11. Cascading decoder (D1→D2) (2-3 hours)

### Phase 4: Validation (6-8 hours)

**Day 7-8**:
12. Round-trip validation all modalities
13. Coverage verification (80% target)
14. Documentation

**Total**: 42-60 hours over 5-8 days

---

## Week 5 Readiness

**Current**: Week 4 complete ✅  
**Ready**: All infrastructure working ✅  
**Instances**: 374 for testing ✅  
**Blockers**: NONE ✅

**Can start Week 5 immediately** ✅

---

## Estimated Completion

**If starting now**: 5-8 days to complete Week 5  
**Effort**: 42-60 hours total  
**Complexity**: High (new implementations)

**Realistic**: Week 5 will take 1-1.5 weeks of focused work

---

**Summary**: ~50 hours of work remaining for Week 5 (codec development)

---

**Author**: Patrick Cooper  
**Date**: 2026-02-12  
**Status**: Week 5 assessed, ready to begin
