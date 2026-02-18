# Current Status and Implementation Plan

**Last Updated**: February 18, 2026  
**Project**: BLANC - Defeasible Abduction Benchmark  
**Status**: Week 8 Complete, Cross-Ontology Proof FAILED, Starting Manual Level 3

---

## Quick Status

**Progress**: 8.5 of 14.5 weeks (59%)  
**Tests**: 333 passing, 80% coverage  
**Infrastructure**: Complete (evaluation pipeline ready)  
**Cross-Ontology Proof**: FAILED (2026-02-18) - see CROSS_ONTOLOGY_PLAN.md  
**Next Critical Action**: Phase 2B - Manual Level 3 defeater instance generation

---

## Three Critical Insights from 2026-02-13 Session

### 1. The Three Objectives Gap

**Paper claims**: "Grounding, Novelty, and Belief Revision" (title)  
**Current dataset**: Only tests grounding (Level 2 instances)

| Objective | Implementation | Dataset Coverage | Score |
|-----------|----------------|------------------|-------|
| Grounding | ✅ Full | 374/374 (100%) | 8/10 |
| Novelty | ✅ Metric only | 0/374 (0%) | 4/10 |
| Belief Revision | ✅ Framework only | 0/374 (0%) | 3/10 |

**Why**: Need Level 3 (defeater abduction) instances  
**Solution**: Week 8.5 to generate defeater instances

### 2. The 10-100x Scale Opportunity

**Current**: 2,318 rules → 374 instances  
**Potential**: 100K-350K rules → 16K-56K instances

**Method**: Cross-ontology extraction
- OpenCyc: 300K concepts (taxonomy)
- ConceptNet: 21M assertions (properties, defeaters)
- Combine: 100K-350K defeasible rules

**Feasibility**: HIGH - experimental scripts ready

### 3. Automatic Level 3 Generation (RULED OUT)

**Status**: Cross-ontology proof FAILED (2026-02-18)  
**Why**: OpenCyc/ConceptNet concept-name mismatch + ConceptNet quality below expert-only policy  
**Decision**: Manual Level 3 generation (Phase 2B) is the path forward  
**See**: CROSS_ONTOLOGY_PLAN.md for full proof-of-concept results

---

## The Three Scenario Types and Objectives

### Level 1: Fact Completion
- Missing observation
- Example: "bird(owl)" is missing
- Tests: Grounding only
- Current: 0 instances

### Level 2: Rule Abduction  
- Missing generalization
- Example: "flies(X) :- bird(X)" is missing
- Tests: Grounding only
- Current: 374 instances (100% of dataset)

### Level 3: Defeater Abduction
- Wrong prediction needs exception
- Example: Theory predicts flies(penguin) but penguins don't fly
- Answer: ~flies(X) :- penguin(X) (defeater)
- Tests: **ALL THREE** (grounding + novelty + belief revision)
- Current: 0 instances (CRITICAL GAP)

---

## Implementation Plan: Phase 2B (Active)

### Day 8.5a: Cross-Ontology Proof ← COMPLETE (FAILED)

**Result**: FAIL - 0.4x scale, 0 defeaters  
**Decision**: Proceed to Phase 2B  
**Full results**: CROSS_ONTOLOGY_PLAN.md

### Week 8.6: Full Extraction ← CANCELLED

Cross-ontology approach ruled out due to:
1. Concept-name mismatch between OpenCyc and ConceptNet
2. ConceptNet quality incompatible with expert-only KB policy

### Week 8.5b: Manual Level 3 (3-5 days) ← ACTIVE NOW

**Goal**: 35-50 defeater instances manually

**Tasks**:
- Day 1-2: Biology defeaters (15-20)
- Day 3: Legal defeaters (10-15)
- Day 4: Materials defeaters (10-15)
- Day 5: Validation

**Deliverable**: Small-scale Level 3 coverage

### Week 9: Pilot Evaluation

- Test on all three levels
- Validate all three objectives
- Cost: $5-10

### Week 10: Full Evaluation

- 16,600 queries (or 700K if large-scale)
- All models, modalities, strategies
- Complete results for all objectives

### Weeks 11-14: Analysis + Submission

- Advanced analyses
- HPC production (optional)
- Paper integration
- NeurIPS submission

---

## What We Have Now

### Infrastructure ✅
- 5 model interfaces (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3)
- Complete evaluation pipeline
- All metrics (novelty, conservativity, revision distance)
- Response caching
- 343 tests passing, 80% coverage

### Dataset ⚠️
- 2,318 expert rules from 4 sources
- 374 Level 2 instances (rule abduction)
- 0 Level 3 instances (defeater abduction)

### Knowledge Bases
- YAGO 4.5: 584 biology rules
- WordNet 3.0: 334 rules  
- LKIF Core: 201 legal rules
- MatOnto: 1,190 materials rules

---

## Immediate Next Steps

1. **Begin manual Level 3 generation (biology defeaters, Day 1-2)**:
   - 15-20 biology instances: birds that don't fly, mammals that don't walk, etc.
   - Validate each with conservativity checker + novelty metric
   - Generate 5 distractors per instance

2. **Legal defeaters (Day 3)**:
   - 10-15 instances: emancipated minors, good faith exceptions, statutes of limitations
   - Some should introduce novel predicates (Nov > 0)

3. **Materials defeaters (Day 4)**:
   - 10-15 instances: metallic glass, aerogels, superconductors
   - Highest novelty target (materials = most opportunity for Nov > 0)

4. **Validation + testing (Day 5)**:
   - All instances: conservativity, novelty, revision distance
   - Integration into evaluation pipeline
   - Run all tests

---

## Key Resources

### For This Work
- `scripts/validate_cross_ontology_scale.py` - Proof script
- `scripts/method_comparison_experiments.py` - Method comparison
- `Guidance_Documents/CROSS_ONTOLOGY_PLAN.md` - Detailed plan

### For Understanding
- `README.md` - Project overview
- `Guidance_Documents/KNOWLEDGE_BASE_POLICY.md` - Expert-only policy

### For Reference
- `hpc/README.md` - HPC deployment info
- `docs/` - Historical documentation (archived)

---

## Expert Sources (All Peer-Reviewed)

1. **YAGO 4.5** (Télécom Paris, SIGIR 2024) - 927 biology rules
2. **WordNet 3.0** (Princeton) - 334 rules
3. **LKIF Core** (U Amsterdam) - 201 legal rules
4. **MatOnto** (MatPortal/MGI) - 1,190 materials rules

**Total**: 2,318 rules (can be 100K-350K with cross-ontology)

---

## Success Criteria

### For Proof-of-Concept
- [ ] Generates >= 5,000 rules from sample
- [ ] Projects to >= 50,000 full
- [ ] Defeaters >= 100
- [ ] Quality >= 80%

### For Full Extraction  
- [ ] Biology: 100K+ rules
- [ ] Total: 150K+ rules
- [ ] Defeaters: 5K+
- [ ] Level 3: 1K+ instances automatically

### For NeurIPS Submission
- [ ] All three objectives tested
- [ ] Statistical significance achieved
- [ ] Large-scale or proof-of-concept (either publishable)
- [ ] Paper claims match deliverables

---

## Timeline

**Week 8**: ✅ Complete  
**Day 8.5a**: Proof (next)  
**Week 8.5b OR 8.6**: Conditional on proof  
**Week 9-10**: Evaluation  
**Week 11-14**: Analysis + submission

**Target**: NeurIPS 2026 submission (on track)

---

**Author**: Patrick Cooper  
**Maintained**: Guidance_Documents/  
**Next Action**: Run cross-ontology validation
