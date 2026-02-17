# Defeasible Scenarios and the Three Core Objectives

**Brief Guide to What We Test and Why**

---

## The Three Core Objectives

From the paper, we test whether foundation models can:

1. **Grounding**: Trace conclusions to supporting evidence
2. **Novelty**: Generate hypotheses with new concepts/predicates
3. **Belief Revision**: Update knowledge while preserving unrelated commitments (minimal change)

---

## The Three Scenario Types

### Level 1: Fact Completion → Tests GROUNDING

**Scenario**: Missing observation

**Example**:
```
Theory knows: animal(owl), flies(owl)
Theory has: bird(X) → animal(X)
Question: What's missing to derive bird(owl)?
Answer: bird(owl) [the fact itself]
```

**What it tests**: Can models identify which EVIDENCE is missing?

**Measures grounding**: YES - models must trace dependencies  
**Measures novelty**: NO - fact uses existing predicates  
**Measures belief revision**: NO - just adding information

**Current dataset**: 0 instances (not generated yet)

---

### Level 2: Rule Abduction → Tests GROUNDING

**Scenario**: Missing generalization

**Example**:
```
Theory knows: bird(penguin), animal(penguin)
Theory has: bird(X) → animal(X)
Question: What rule explains bird(penguin) given animal(penguin)?
Answer: bird(X) :- penguin(X)
```

**What it tests**: Can models identify which RULE is missing?

**Measures grounding**: YES - must understand support structure  
**Measures novelty**: NO - rule uses existing predicates  
**Measures belief revision**: NO - monotonic extension

**Current dataset**: 374 instances (100% of current dataset)

---

### Level 3: Defeater Abduction → Tests ALL THREE

**Scenario**: Theory makes wrong prediction, need exception

**Example**:
```
Theory has: flies(X) :- bird(X) [DEFEASIBLE DEFAULT]
Theory knows: bird(penguin)
Theory predicts: flies(penguin) [WRONG!]
Observation: ~flies(penguin) [penguin doesn't fly]

Question: What EXCEPTION makes this consistent?
Answer: ~flies(X) :- penguin(X) [DEFEATER]
```

**What it tests**: Can models construct rational exceptions?

**Measures grounding**: ✅ YES
- Must identify which rule causes wrong prediction
- Must trace support for incorrect conclusion

**Measures novelty**: ✅ YES  
- May require novel predicates (amorphous_metal, emancipated_minor)
- Nov(defeater, D) measures predicate novelty

**Measures belief revision**: ✅ YES
- Must preserve OTHER predictions (eagle still flies, robin still flies)
- Conservativity check ensures minimal change
- Revision distance measures how much changed

**Current dataset**: 0 instances (CRITICAL GAP)

---

## Why Level 3 Matters

**Paper title**: "Grounding, Novelty, and Belief Revision"

**Level 1-2**: Only test grounding  
**Level 3**: Tests all three simultaneously

**Without Level 3**: Paper claims unsupported  
**With Level 3**: Full demonstration of all objectives

---

## Real Examples by Domain

### Biology: Penguin Exception

**Default**: Birds fly  
**Exception**: Penguins don't  
**Defeater**: ~flies(X) :- penguin(X)

**Grounding**: Traces incorrect prediction to "flies(X) :- bird(X)"  
**Novelty**: Uses existing predicates (Nov = 0) OR introduces new behavior (Nov > 0)  
**Belief Revision**: Preserves flies(robin), flies(eagle) - only fixes penguin

---

### Legal: Emancipated Minor

**Default**: Minors cannot sign contracts  
**Exception**: Emancipated minors can  
**Defeater**: can_sign_contract(X) :- emancipated_minor(X)

**Grounding**: Identifies conflicting rule about minors  
**Novelty**: Introduces "emancipated_minor" predicate (Nov > 0)  
**Belief Revision**: Preserves rules about adults, other minors - minimal change

---

### Materials: Metallic Glass

**Default**: Crystals are brittle  
**Exception**: Amorphous metals aren't  
**Defeater**: ~brittle(X) :- amorphous_metal(X)

**Grounding**: Traces brittleness prediction to crystal rule  
**Novelty**: Introduces "amorphous_metal" concept (Nov = 0.33)  
**Belief Revision**: Preserves brittle(diamond), brittle(quartz) - targeted fix

---

## How Cross-Ontology Helps

**ConceptNet has**:
- CapableOf relations → defeasible defaults (Level 2)
- NotCapableOf relations → defeaters (Level 3!)

**Example from ConceptNet**:
```
(bird, CapableOf, fly)           → flies(X) :- bird(X)
(penguin, NotCapableOf, fly)     → ~flies(X) :- penguin(X)
```

**Impact**: Automatic Level 3 generation (1,000-5,000 instances vs 35-50 manual)

---

## Summary Table

| Level | Scenario | Grounding | Novelty | Belief Revision | Current Dataset |
|-------|----------|-----------|---------|-----------------|-----------------|
| 1 | Fact completion | ✅ | ❌ | ❌ | 0 instances |
| 2 | Rule abduction | ✅ | ❌ | ❌ | 374 instances |
| 3 | Defeater abduction | ✅ | ✅ | ✅ | 0 instances |

**Critical**: Need Level 3 to test all three objectives

**Solution**: Manual generation (35-50) OR automated via cross-ontology (1K-5K)

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13
