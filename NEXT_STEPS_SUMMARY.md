# Next Steps: Executive Summary

**Date**: February 13, 2026  
**Current Status**: Week 8 Complete (Evaluation Infrastructure)  
**Critical Next Step**: Week 8.5 - Level 3 Instance Generation

---

## The Situation

### What We Have ✅

**Infrastructure** (343 tests passing, 80% coverage):
- ✅ 5 model interfaces ready (GPT-4o, Claude, Gemini, Llama)
- ✅ Complete evaluation pipeline
- ✅ All metrics implemented (novelty, conservativity, revision distance)

**Dataset** (374 instances):
- ✅ 114 biology instances (Level 2)
- ✅ 168 legal instances (Level 2)
- ✅ 92 materials instances (Level 2)

### The Problem ❌

**Paper claims** (title): "Grounding, Novelty, and Belief Revision"

**Current dataset tests**:
- ✅ Grounding: 100% coverage (Level 2)
- ❌ Novelty: 0% coverage (need Level 3)
- ❌ Belief Revision: 0% coverage (need Level 3)

**Gap**: Cannot claim to test all three objectives without Level 3 instances

---

## The Solution

### Add Week 8.5: Level 3 Instance Generation

**Timeline**: 3-5 days  
**Goal**: Generate 35-50 defeater abduction instances  
**Impact**: Enables testing of all three objectives

### What to Build

**Biology Defeaters** (Day 1-2): 15-20 instances
- Birds that don't fly: penguin, ostrich, emu
- Mammals that don't walk: whale, dolphin
- Example: "~flies(X) :- penguin(X)"

**Legal Defeaters** (Day 3): 10-15 instances
- Age exceptions, jurisdictional exceptions
- Example: "can_sign_contract(X) :- emancipated_minor(X)"

**Materials Defeaters** (Day 4): 10-15 instances
- Metallic glass, shape-memory alloys
- Example: "~brittle(X) :- amorphous_metal(X)"

**Validation** (Day 5): Test everything
- Conservativity checks
- Novelty computation
- Distractor generation

---

## Why This Matters

### Paper Claims We Can Make

**Without Level 3**:
- "We provide a framework for grounding, novelty, and belief revision"
- "Comprehensive evaluation of grounding"
- "Framework validated on proof-of-concept examples"

**With Level 3** (35-50 instances):
- "We empirically evaluate all three objectives"
- "Models achieve X% accuracy on belief revision tasks"
- "Novelty correlates with difficulty"
- "Conservativity rate is Y%"

### Publication Impact

**Without Level 3**: Solid contribution, but claims don't match deliverables  
**With Level 3**: Full delivery on paper's promise, stronger NeurIPS contribution

---

## Detailed Plans Available

1. **OBJECTIVE_ACCOUNTING.md**: Gap analysis (what's missing and why)
2. **REVISED_IMPLEMENTATION_PLAN.md**: Week-by-week plan with Level 3 insertion
3. **INTUITIVE_GUIDE.md**: Explains the benchmark to non-experts
4. **PI_REPORT_2026-02-13.md**: Current status for your PI

---

## Immediate Action Items

### This Week (Start Week 8.5)

**Day 1-2: Biology**
```bash
# 1. Review examples in scripts/generate_level3_instances.py
# 2. Create 15-20 new defeater instances
# 3. Validate each with conservativity checker
# 4. Generate distractors
```

**Day 3: Legal**
```bash
# Similar process for legal defeaters
# Focus on statutory exceptions
# Some with novel predicates (Nov > 0)
```

**Day 4: Materials**
```bash
# Materials science exceptions
# Target higher novelty (Nov > 0.3)
# Property exceptions well-documented
```

**Day 5: Validation**
```bash
# Run all tests
# Integration testing
# Document instances
# Prepare for pilot
```

### Next Week (Week 9)

**Pilot Evaluation**:
- 20-25 instances (mix of Level 2 + Level 3)
- 3 models (GPT-4o, Claude, Llama)
- Cost: ~$5-10
- Validates all three objectives

---

## Risk Assessment

### Low Risk ✅
- Framework already exists and validated
- 3 hand-crafted examples work
- Conservativity checker tested
- Templates available

### Medium Risk ⚠️
- Time estimate (3-5 days realistic but tight)
- Domain expertise (may need research)
- Validation thoroughness

### Mitigation
- Start with minimum viable (20-30 instances)
- Use textbook exception cases
- Parallelize if possible
- Accept lower novelty initially

---

## Cost Analysis

### Time Cost
- Week 8.5: 3-5 days (concentrated work)
- Added to timeline: 0.5 weeks
- New total: 14.5 weeks vs 14 weeks

### Money Cost
- Level 3 adds ~1,600 queries to evaluation
- Additional cost: ~$25-35
- New total: $160-210 vs $136-201
- 15% increase for 2x coverage of objectives

### Value
- Can claim all three objectives empirically
- Stronger paper contribution
- Reviewers see comprehensive evaluation
- Future work has clear baseline

---

## Decision Point

### Option 1: Full Implementation (Recommended)
- Generate 35-50 Level 3 instances
- Test all three objectives
- Deliver on paper's promise
- **Cost**: 3-5 days + $25-35
- **Value**: Strong NeurIPS contribution

### Option 2: Minimum Viable
- Generate 20-30 Level 3 instances
- Proof-of-concept for novelty/revision
- Frame as "preliminary"
- **Cost**: 2-3 days + $15-20
- **Value**: Honest, publishable

### Option 3: Skip Level 3
- Revise paper scope to "grounding framework"
- Level 3 as "validated, future work"
- **Cost**: 1-2 days (paper revisions)
- **Value**: Conservative, less ambitious

**Recommendation**: Option 1 (Full Implementation)

---

## Success Criteria

### Week 8.5 Success
- [ ] 35-50 Level 3 instances generated
- [ ] All validated for conservativity
- [ ] 5+ instances with Nov > 0
- [ ] Tests passing
- [ ] Ready for pilot

### Project Success
- [ ] All three objectives addressed
- [ ] Empirical evidence for each
- [ ] Paper claims match deliverables
- [ ] NeurIPS submission ready

---

## Getting Started

### Today
1. Read OBJECTIVE_ACCOUNTING.md (understand the gap)
2. Read REVISED_IMPLEMENTATION_PLAN.md (see the solution)
3. Review scripts/generate_level3_instances.py (see examples)
4. Start biology defeater list

### This Week
1. Generate defeater instances (3-4 days)
2. Validate conservativity (1 day)
3. Document and test
4. Prepare for pilot

### Next Week
1. Run pilot evaluation
2. Validate all three objectives
3. Proceed to full evaluation

---

## Questions?

**Why is this critical?**
- Paper's title and claims require all three objectives
- Current dataset only tests grounding
- 3-5 days now vs major revision later

**What if we don't have time?**
- Minimum viable: 20-30 instances (2-3 days)
- Still demonstrates all objectives
- Frame as preliminary for Level 3

**What if models fail on Level 3?**
- That's actually a finding (interesting negative result)
- Shows gap in current models
- Justifies the benchmark

**Can we parallelize?**
- Yes! Biology, legal, materials can be done independently
- If team members available, assign domains

---

## Resources

**All documentation**:
- OBJECTIVE_ACCOUNTING.md - Gap analysis
- REVISED_IMPLEMENTATION_PLAN.md - Detailed week-by-week plan
- INTUITIVE_GUIDE.md - Explains benchmark to non-experts
- PI_REPORT_2026-02-13.md - Status report

**Code locations**:
- scripts/generate_level3_instances.py - Working examples
- src/blanc/author/ - Generation framework
- experiments/ - Evaluation pipeline

**Tests**:
- tests/author/ - Unit tests for generation
- tests/experiments/ - Evaluation pipeline tests

---

## Bottom Line

**Current state**: Can only test 1 of 3 objectives (grounding)

**With Week 8.5**: Can test all 3 objectives (grounding, novelty, belief revision)

**Cost**: 3-5 days of focused work

**Benefit**: Deliver on paper's full promise, stronger NeurIPS contribution

**Recommendation**: Start Week 8.5 immediately

---

**Author**: Patrick Cooper  
**Date**: February 13, 2026  
**Action**: Begin Level 3 instance generation
