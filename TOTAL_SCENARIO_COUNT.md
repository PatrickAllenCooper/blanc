# Total Scenario Count: All Three Levels Combined

**Quick Answer to "How many scenarios total?"**

---

## Current Benchmark

**Rules**: 2,318  
**Scenarios**: 374 (all Level 2 only)

---

## With Cross-Ontology Extraction

### Conservative Estimate (3 Core Domains)

**Rules Generated**: 115,000-280,000

**Scenarios by Level**:
- **Level 1** (fact completion): 20,000-45,000
- **Level 2** (rule abduction): 26,200-58,700  
- **Level 3** (defeater abduction): 3,400-8,500

**TOTAL: 49,600-112,200 scenarios**

**Multiplier**: 132x-300x vs current 374

---

### Aggressive Estimate (10 Domains)

**Rules Generated**: 352,000-850,000

**Scenarios by Level**:
- **Level 1** (fact completion): 80,000-250,000
- **Level 2** (rule abduction): 57,500-126,800
- **Level 3** (defeater abduction): 5,150-16,700

**TOTAL: 142,650-393,500 scenarios**

**Multiplier**: 381x-1,052x vs current 374

---

## By Domain (Conservative - 3 Core Domains)

### Biology
- Level 1: 12,000-25,000
- Level 2: 16,000-32,000
- Level 3: 2,000-5,000
- **Total: 30,000-62,000**

### Chemistry & Materials  
- Level 1: 5,000-12,000
- Level 2: 5,000-13,000
- Level 3: 500-1,500
- **Total: 10,500-26,500**

### Legal & Governance
- Level 1: 3,000-8,000
- Level 2: 2,400-6,400
- Level 3: 300-800
- **Total: 5,700-15,200**

**GRAND TOTAL (3 domains): 46,200-103,700 scenarios**

---

## Recommended for NeurIPS Paper

**Target**: 50,000-60,000 scenarios across 3 domains

**Breakdown**:
- Level 1: 25,000-30,000 (fact completion)
- Level 2: 20,000-25,000 (rule abduction)  
- Level 3: 5,000-7,000 (defeater abduction)

**This gives**:
- Comprehensive coverage (all three levels)
- All three objectives tested (grounding, novelty, belief revision)
- Large-scale benchmark (not proof-of-concept)
- Statistical power for all analyses
- Automatic Level 3 generation (from ConceptNet NotCapableOf)

---

## Comparison

| Metric | Current | Conservative | Aggressive |
|--------|---------|--------------|------------|
| Domains | 3 | 3 | 10 |
| Rules | 2,318 | 115K-280K | 352K-850K |
| Level 1 | 0 | 20K-45K | 80K-250K |
| Level 2 | 374 | 26K-59K | 57K-127K |
| Level 3 | 0 | 3.4K-8.5K | 5K-17K |
| **TOTAL** | **374** | **49K-112K** | **143K-394K** |
| Multiplier | 1x | 132-300x | 381-1,052x |

---

## Bottom Line

**If cross-ontology extraction succeeds**:

**Minimum** (conservative, 3 domains):
- **~50,000 scenarios** across all three levels

**Maximum** (aggressive, 10 domains):
- **~400,000 scenarios** across all three levels

**Recommended for NeurIPS**:
- **50,000-60,000 scenarios** from 3 core domains
- All three levels represented
- All three objectives testable

**Current**: 374 scenarios (Level 2 only)

**Multiplier**: **133-1,052x** depending on scale pursued

---

**Date**: 2026-02-13  
**Conditional on**: Cross-ontology proof-of-concept succeeding
