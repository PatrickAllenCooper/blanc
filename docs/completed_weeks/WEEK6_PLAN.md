# Week 6 Plan: M1 Encoder + D3 Decoder + 85% Coverage

**Goal**: Complete all modalities and decoders  
**Timeline**: Week 6 of 14  
**Target Coverage**: 79% → 85% (+6%)

---

## Week 6 Requirements

### 1. M1 Encoder (Narrative - HARDEST)

**What it does**:
- Full natural language encoding
- Linguistic hedging for defeasibility ("typically", "usually")
- Implicit universal quantification
- Domain-appropriate templates

**Complexity**: HIGH (most challenging modality)

**Example**:
- Rule: `bird(X) => flies(X)`
- M1: "Birds typically can fly"

**Implementation**:
- Template-based generation
- Domain-specific phrasing
- Defeasibility markers (typically, usually, generally)
- ~300-400 lines

**Estimate**: 10-15 hours

---

### 2. D3 Decoder (Semantic Parser)

**What it does**:
- Parses natural language back to formal
- Grammar-based (using Lark)
- Handles paraphrases
- Semantic extraction

**Complexity**: HIGH (needs parsing)

**Implementation**:
- Lark grammar for logic
- Pattern matching for predicates
- NL predicate recognition
- ~250-350 lines

**Estimate**: 8-12 hours

---

### 3. Three-Stage Decoder Integration

**What it does**:
- Cascading decoder: D1 → D2 → D3
- Try exact match, then template, then semantic parsing
- Track which stage succeeds

**Implementation**:
```python
def decode_cascading(text, candidates):
    # Try D1 (exact)
    result = decode_d1(text, candidates)
    if result: return result, 'D1'
    
    # Try D2 (template)
    result = decode_d2(text, candidates)
    if result: return result, 'D2'
    
    # Try D3 (semantic)
    result = decode_d3(text, candidates)
    if result: return result, 'D3'
    
    return None, None
```

**Estimate**: 2-3 hours

---

### 4. Coverage to 85% (+6%)

**Current**: 79%  
**Target**: 85%  
**Gap**: +6%

**Add tests for**:
- M1 encoder tests: 10-15 tests
- D3 decoder tests: 10-15 tests
- Integration tests: 5-10 tests
- Coverage gap filling: 5-10 tests

**Total new tests**: 30-50 tests

**Estimate**: 6-8 hours

---

## Total Week 6 Estimate

| Task | Hours | Difficulty |
|------|-------|------------|
| M1 Encoder | 10-15 | HIGH |
| D3 Decoder | 8-12 | HIGH |
| Cascading Decoder | 2-3 | MEDIUM |
| Test Coverage +6% | 6-8 | MEDIUM |
| Documentation | 2-3 | LOW |
| **TOTAL** | **28-41 hours** | **HIGH** |

**Timeline**: 4-6 days of focused work

---

## Implementation Order

### Phase 1: M1 Encoder (10-15 hours)

**Day 1-2**:
1. Create template system for M1
2. Implement fact → narrative conversion
3. Implement rule → narrative conversion
4. Handle defeasibility markers
5. Test on all 3 domains

**Deliverable**: `src/blanc/codec/m1_encoder.py`

---

### Phase 2: D3 Decoder (8-12 hours)

**Day 2-3**:
6. Create Lark grammar for logic parsing
7. Implement semantic extraction
8. NL predicate recognition
9. Test parsing accuracy

**Deliverable**: `src/blanc/codec/d3_decoder.py`

---

### Phase 3: Integration + Testing (8-11 hours)

**Day 3-4**:
10. Build cascading decoder
11. Add 30-50 comprehensive tests
12. Round-trip validation
13. Coverage verification

**Deliverables**: 
- `src/blanc/codec/cascading_decoder.py`
- 30-50 new tests
- 85% coverage

---

## Success Criteria

- [ ] M1 encoder implemented
- [ ] D3 decoder implemented
- [ ] Cascading decoder (D1→D2→D3)
- [ ] M1: >85% round-trip (with D2/D3)
- [ ] Coverage: 85%
- [ ] All tests passing
- [ ] Ready for Week 7 validation

---

## Starting Now

**First task**: Implement M1 encoder template system

**Approach**: Start simple, iterate
- Basic templates first
- Add complexity incrementally
- Test as we build

---

**Ready to begin Week 6** ✅

**Author**: Patrick Cooper  
**Date**: 2026-02-12
