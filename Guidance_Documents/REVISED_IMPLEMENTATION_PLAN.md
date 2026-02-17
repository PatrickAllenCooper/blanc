# REVISED Implementation Plan: Addressing All Three Objectives

**Date**: 2026-02-13  
**Revision**: Based on OBJECTIVE_ACCOUNTING.md analysis  
**Critical Change**: Added Level 3 instance generation to test novelty and belief revision  
**Timeline**: Weeks 8-14 (adjusted)

---

## Executive Summary

### The Critical Gap

**Paper claims** (paper.tex line 113, title):
> "Defeasible Reasoning as a Framework for Foundation Model Grounding, Novelty, and Belief Revision"

**Current dataset** (OBJECTIVE_ACCOUNTING.md):
- ✅ Grounding: 374 Level 1-2 instances (100% coverage)
- ❌ Novelty: 0 instances with Nov > 0 (0% coverage)
- ❌ Belief Revision: 0 Level 3 instances (0% coverage)

### The Solution

**Insert Week 8.5**: Level 3 Instance Generation (3-5 days)
- Generate 20-50 defeater abduction instances
- Test novelty (predicate novelty Nov(r, D))
- Test belief revision (conservativity, revision distance)
- Enable empirical validation of **all three objectives**

### Revised Timeline

```
Week 8:    Evaluation Infrastructure           ✅ COMPLETE
Week 8.5:  Level 3 Instance Generation         ← NEW (3-5 days)
Week 9:    Pilot Evaluation (All 3 Levels)     (2-3 days)
Week 10:   Full Evaluation + Analysis          (5-7 days)
Week 11-12: Advanced Analyses                   (2 weeks)
Week 13-14: HPC Production + Submission         (2 weeks)
```

**Total addition**: 3-5 days to critical path  
**Benefit**: Can claim all three objectives empirically  
**Risk mitigation**: Pilot approach (20-50 instances, not 200+)

---

## Current Status (Week 8 Complete)

### What's Done ✅

**Evaluation Infrastructure** (343 tests passing, 80% coverage):
1. ✅ 5 model interfaces (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3 70B/8B)
2. ✅ Prompting system (direct + CoT, all 4 modalities)
3. ✅ Response caching (persistent storage)
4. ✅ Evaluation pipeline (end-to-end orchestration)
5. ✅ Decoder integration (D1→D2→D3)
6. ✅ Metrics computation (accuracy, novelty, conservativity fields ready)

**Dataset** (374 instances):
1. ✅ Biology: 114 instances (all Level 2 - rule abduction)
2. ✅ Legal: 168 instances (all Level 2 - rule abduction)
3. ✅ Materials: 92 instances (all Level 2 - rule abduction)

**Framework for Level 3**:
1. ✅ Conservativity check implemented (`author.py` lines 594-619)
2. ✅ Revision distance metric (`author.py` lines 620-639)
3. ✅ Predicate novelty metric (`author.py` lines 640-667)
4. ✅ 3 hand-validated examples (penguin, ostrich, duck)

### What's Missing ❌

**Critical for Paper Claims**:
1. ❌ Level 3 instances in development dataset (0 of 374)
2. ❌ Systematic testing of novelty (all instances have Nov = 0)
3. ❌ Systematic testing of belief revision (no conservativity testing)
4. ❌ Empirical evidence for "novelty and belief revision" claims

---

## Week 8.5: Cross-Ontology Extraction + Level 3 (REVISED)

**Duration**: 4-9 days total (phased approach)  
**Priority**: CRITICAL for scale AND paper claims  
**Goal**: 
  1. Validate 10-100x scale via cross-ontology extraction (1 day)
  2. Generate Level 3 instances (manual OR automated based on #1)

### Why This Changed

**User insight**: OpenCyc (300K concepts) + ConceptNet (21M assertions) can 10-100x our ruleset!

**Current**: 2,318 rules → 374 instances  
**Potential**: 100K-350K rules → 16K-56K instances

**Bonus**: ConceptNet NotCapableOf relations = automatic defeaters for Level 3!

### Why This is Essential

From paper.tex lines 192, 252:
> "Level 3 (defeater abduction) asks models to construct novel exception rules satisfying the conservativity constraint, performing rational belief revision in the defeasible setting."

Without Level 3 instances:
- Cannot test novelty (Nov > 0 hypotheses)
- Cannot test belief revision (conservativity)
- Cannot claim to address "all three objectives"
- Paper title is not supported by experiments

### Phase 1: Cross-Ontology Proof-of-Concept (Day 8.5a, 1 day) ← NEW!

**Goal**: Validate we can 10-100x our ruleset

**Critical Decision Point**: Determines whether to pursue large-scale extraction

**Tasks**:

**Morning** (2-4 hours):
```bash
# Run validation script
python scripts/validate_cross_ontology_scale.py

# Tests:
#   1. Load 1K OpenCyc concepts (sample)
#   2. Load 100K ConceptNet assertions (sample)
#   3. Combine to generate rules
#   4. Measure: rules, defeaters, quality
#   5. Project to full scale
```

**Afternoon** (2-4 hours):
```bash
# Method comparison
python scripts/method_comparison_experiments.py

# Compares 5 approaches:
#   1. Cross-ontology (OpenCyc + ConceptNet)
#   2. Property templates
#   3. Closed world assumption
#   4. YAGO full extraction
#   5. ConceptNet standalone

# Output: Best method + recommendation
```

**Decision Criteria**:
- ✅ If >= 5x scale → PROCEED to Week 8.6 (full extraction)
- ❌ If < 5x scale → SKIP to manual Level 3 generation

**Deliverable**: Go/No-Go decision with data

---

### Phase 2A: Full Cross-Ontology Extraction (Week 8.6, 1 week) ← CONDITIONAL

**Only if**: Proof-of-concept achieves >= 5x scale

**Goal**: Generate 100K-350K rules from OpenCyc + ConceptNet

**Day 1-2**: Enhance extractors
- Modify `opencyc_extractor.py` for full taxonomy extraction
- Modify `conceptnet_extractor.py` for all behavioral relations
- Create `cross_ontology.py` for combination logic

**Day 3-4**: Biology extraction
- Extract 50K concepts from OpenCyc
- Extract 500K bio assertions from ConceptNet
- Generate 100K-200K defeasible rules
- Validate on sample

**Day 5**: Legal + Materials
- Legal: 10K concepts, 50K assertions → 10K-50K rules
- Materials: 30K concepts, 100K assertions → 50K-100K rules

**Day 6**: Automatic Level 3 Generation
- Extract all defeaters (NotCapableOf relations)
- Generate Level 3 instances automatically
- **Yield**: 1,000-5,000 defeater instances!

**Day 7**: Validation
- Quality check (sample 100 rules)
- Test instance generation
- Run all tests
- Documentation

**Deliverable**: 
- 100K-350K rules
- 1,000-5,000 Level 3 instances (automatic!)
- 10,000-50,000 Level 2 instances

---

### Phase 2B: Manual Level 3 (3-5 days) ← FALLBACK

**Only if**: Cross-ontology proof fails

**This is the original plan**: Manual defeater generation

**Goal**: 35-50 Level 3 instances

### Phase 1 (ORIGINAL): Biology Defeaters (Day 1-2, 1-2 days)

**Goal**: 15-20 biology instances with defeater abduction

**Strategy**: Mine textbook exceptions
1. Birds that don't fly: penguin, ostrich, emu, kiwi, cassowary
2. Mammals that don't walk: whale, dolphin, bat (fly/swim instead)
3. Fish that don't swim: seahorse (limited locomotion)
4. Animals with exceptional diets: panda (herbivore carnivore)
5. Animals with exceptional behaviors: cuckoo (brood parasite)

**Template**:
```python
# Example: Penguin defeater
Instance = {
    'level': 3,
    'anomaly': 'flies(penguin)',  # Theory predicts this, but false
    'challenge_theory': D_minus,  # D without penguin defeater
    'gold_resolution': {
        'defeater': "~flies(X) :- penguin(X)",
        'Nov': 0.0,  # Uses existing predicates
        'd_rev': 1,  # Adds 1 rule, loses 0 expectations
        'conservative': True
    },
    'candidates': [
        "~flies(X) :- penguin(X)",  # Gold
        "~flies(X) :- bird(X)",      # Too broad (breaks other birds)
        "swims(X) :- penguin(X)",    # Doesn't resolve anomaly
        "walks(X) :- penguin(X)",    # Doesn't resolve anomaly
        "bird(X) :- penguin(X)",     # Already derivable
        "aquatic(X) :- penguin(X)"   # Doesn't resolve anomaly
    ]
}
```

**Validation Checklist**:
- [ ] Anomaly is defeasible (not strict)
- [ ] Gold defeater resolves anomaly
- [ ] Gold defeater is conservative (preserves other expectations)
- [ ] Compute Nov(gold, D) and d_rev(D, D')
- [ ] Generate 5 plausible distractors

**Deliverable**: 15-20 biology Level 3 instances

---

### Phase 2: Legal Defeaters (Day 2-3, 1 day)

**Goal**: 10-15 legal instances with statutory exceptions

**Strategy**: Use legal exception patterns
1. Age exceptions: "Minors typically cannot sign contracts" → defeater for emancipated minors
2. Jurisdictional exceptions: "Federal law applies" → defeater for state sovereignty cases
3. Good faith exceptions: "Contracts are binding" → defeater for fraud/duress
4. Statute of limitations: "Claims are valid" → defeater for expired claims
5. Qualified immunity: "Officials are liable" → defeater for official acts

**Template**:
```python
# Example: Emancipated minor exception
Instance = {
    'level': 3,
    'anomaly': 'can_sign_contract(minor_jones)',
    'challenge_theory': D_minus,  # Without emancipation exception
    'gold_resolution': {
        'defeater': "can_sign_contract(X) :- emancipated_minor(X)",
        'superiority': "emancipated_rule > minor_rule",
        'Nov': 0.0,  # Uses emancipated_minor predicate (may need to add)
        'd_rev': 2,  # Rule + superiority
        'conservative': True
    }
}
```

**Novel predicate option**: Some instances can introduce `emancipated_minor` → Nov > 0

**Deliverable**: 10-15 legal Level 3 instances

---

### Phase 3: Materials Defeaters (Day 3-4, 1 day)

**Goal**: 10-15 materials instances with property exceptions

**Strategy**: Use materials science exceptions
1. Metallic glass: "Crystals are brittle" → exception for amorphous metals
2. Shape-memory alloys: "Metals don't recover shape" → exception for NiTi
3. Graphene: "Carbon is opaque" → exception for single-layer graphene
4. Aerogels: "Solids are dense" → exception for ultra-light materials
5. Superconductors: "Metals have resistance" → exception at low temperature

**Template**:
```python
# Example: Metallic glass exception
Instance = {
    'level': 3,
    'anomaly': 'brittle(metallic_glass)',  # Predicted, but false
    'challenge_theory': D_minus,
    'gold_resolution': {
        'defeater': "~brittle(X) :- amorphous_metal(X)",
        'Nov': 0.33,  # Introduces 'amorphous_metal' (novel)
        'd_rev': 1,
        'conservative': True
    }
}
```

**Higher novelty**: Materials science is ideal for Nov > 0 instances

**Deliverable**: 10-15 materials Level 3 instances

---

### Phase 4: Validation & Testing (Day 4-5, 1 day)

**Tasks**:
1. **Verify all instances**:
   - [ ] Anomaly is defeasible (check with `defeasible_provable`)
   - [ ] Gold defeater resolves anomaly
   - [ ] Conservativity holds (`is_conservative_resolution`)
   - [ ] Compute Nov(gold, D) correctly
   - [ ] Compute d_rev(D, D') correctly

2. **Generate distractors**:
   - [ ] 5 plausible but incorrect defeaters per instance
   - [ ] Mix of: too broad, too narrow, doesn't resolve, non-conservative

3. **Unit tests**:
   - [ ] Test conservativity checking on all instances
   - [ ] Test novelty computation
   - [ ] Test revision distance
   - [ ] Verify round-trip encoding/decoding

4. **Integration tests**:
   - [ ] Load Level 3 instances into pipeline
   - [ ] Encode in all 4 modalities
   - [ ] Verify prompts are well-formed
   - [ ] Test decoder on mock responses

**Deliverable**: 35-50 validated Level 3 instances, tested and ready

---

### Success Criteria

**Minimum Viable** (20-30 instances):
- 10 biology, 10 legal, 10 materials
- All validated for conservativity
- At least 5 instances with Nov > 0
- Ready for pilot evaluation

**Target** (35-50 instances):
- 15-20 biology, 10-15 legal, 10-15 materials
- 10-15 instances with Nov > 0
- Mix of weak, strong, restructuring resolutions
- Comprehensive coverage of exception types

**Stretch** (60+ instances):
- 20+ per domain
- Systematic variation of Nov* (0, 0.25, 0.5, 0.75, 1.0)
- Language bias variation (controlled novel vocabulary)
- Statistical power for per-model comparisons

---

## Week 9: Pilot Evaluation (Revised)

**Duration**: 2-3 days  
**Goal**: Validate all three objectives empirically

### Pilot Design

**Test Set**:
- 10 Level 2 instances (grounding baseline)
- 10-15 Level 3 instances (novelty + belief revision)
- **Total**: 20-25 instances

**Models**:
- GPT-4o (strongest)
- Claude 3.5 Sonnet (strong reasoning)
- Llama 3 70B (open source baseline)

**Modalities**:
- M4 (pure formal) - control
- M2 (semi-formal) - hybrid

**Strategies**:
- Direct prompting
- Chain-of-Thought prompting

**Total Queries**: 20-25 instances × 3 models × 2 modalities × 2 strategies = **240-300 queries**

**Estimated Cost**: $5-10 (much cheaper than original pilot)

### What We'll Measure

**Grounding (Level 2)**:
- Accuracy at identifying missing rules
- Decoder stage distribution (D1, D2, D3)
- Error taxonomy

**Novelty (Level 3 with Nov > 0)**:
- Can models generate hypotheses with novel predicates?
- Distribution of Nov(model_hypothesis, D)
- Correlation between Nov and accuracy

**Belief Revision (Level 3 conservativity)**:
- What % of model hypotheses are conservative?
- Distribution of d_rev (revision distance)
- Do models understand minimal change?

### Validation Targets

**Success criteria**:
- [ ] All 3 objectives tested empirically
- [ ] Grounding accuracy: baseline established
- [ ] Novelty: at least some instances have Nov > 0 responses
- [ ] Belief revision: can measure conservativity rate
- [ ] Cost estimates validated
- [ ] Pipeline stable

**Go/No-Go for Week 10**:
- If pilot succeeds → proceed to full evaluation
- If issues found → debug and re-run pilot
- If costs too high → adjust model/modality selection

---

## Week 10: Full Evaluation (Revised)

**Duration**: 5-7 days  
**Goal**: Complete evaluation across all instances and models

### Full Test Set

**Level 2** (existing): 374 instances
- Biology: 114
- Legal: 168
- Materials: 92

**Level 3** (new): 35-50 instances
- Biology: 15-20
- Legal: 10-15
- Materials: 10-15

**Total**: 410-425 instances

### Evaluation Matrix

**Models**: 5 (GPT-4o, Claude 3.5, Gemini 1.5, Llama 3 70B/8B)  
**Modalities**: 4 (M1, M2, M3, M4)  
**Strategies**: 2 (direct, CoT)

**Total Queries**:
- Level 2: 374 × 5 × 4 × 2 = 14,960 queries
- Level 3: 40 × 5 × 4 × 2 = 1,600 queries
- **Grand Total**: ~16,600 queries

**Estimated Cost** (revised):
- GPT-4o: 3,320 queries × $0.02 = $66
- Claude 3.5: 3,320 queries × $0.015 = $50 (batch discount)
- Gemini 1.5: 3,320 queries × $0.01 = $33
- Llama: Free (local)
- **Total**: $150-200 (slight increase from original $135-200)

### Analysis Deliverables

**By Objective**:

1. **Grounding Analysis** (Level 1-2):
   - Accuracy by model, modality, domain
   - Decoder stage distribution
   - Error taxonomy (E1-E5)
   - Support set complexity effects

2. **Novelty Analysis** (Level 3):
   - Distribution of Nov(h, D) for model responses
   - Accuracy vs novelty correlation
   - Can models generate Nov > 0 hypotheses?
   - Language bias effects

3. **Belief Revision Analysis** (Level 3):
   - Conservativity rate by model
   - Distribution of d_rev
   - Accuracy vs conservativity trade-off
   - AGM minimal change adherence

**Cross-Cutting**:
- Rendering robustness (worst-case across modalities)
- Prompting strategy effects (direct vs CoT)
- Scaling effects (Llama 8B vs 70B)
- Domain effects (biology vs legal vs materials)

---

## Week 11-12: Advanced Analyses (Unchanged)

**Duration**: 2 weeks  
**No changes needed** - these analyses apply to whatever dataset we have

**Tasks**:
1. Scaling analysis (Llama 8B vs 70B)
2. Theory size scaling
3. Symbolic ceiling (ASP solver baseline)
4. Partition sensitivity analysis
5. Difficulty stratification

**Deliverables**:
- Scaling curves
- Symbolic baseline comparison
- Sensitivity analysis
- Statistical analysis

---

## Week 13-14: HPC Production + Submission (Adjusted)

**Duration**: 2 weeks  
**Adjusted for Level 3 inclusion**

### Tasks

**Week 13: HPC Deployment**
1. Deploy instance generation to CURC Alpine
2. Generate production-scale dataset:
   - Level 2: Scale from 374 to 10,000+ instances (full expert KBs)
   - Level 3: Scale from 40 to 200-500 instances (expert-authored defeaters)
3. Run production evaluations
4. Analyze at scale

**Week 14: Paper Integration + Submission**
1. **Results section** (Section 5):
   - Grounding results (Level 1-2)
   - Novelty results (Level 3, Nov > 0)
   - Belief revision results (Level 3, conservativity)
2. **Discussion section** (Section 6):
   - Three objectives addressed
   - Model strengths/weaknesses per objective
   - Implications for foundation model design
3. **Related work** (Section 2):
   - Position relative to knowledge editing (ROME, MEMIT)
   - Connection to AGM belief revision
   - Novelty relative to existing benchmarks
4. **Final polish**:
   - Abstract update (three objectives)
   - Introduction alignment
   - Conclusion
5. **Submission**

---

## Updated Timeline Summary

| Week | Task | Duration | Status |
|------|------|----------|--------|
| 1-7 | Infrastructure & Dataset | 7 weeks | ✅ Complete |
| 8 | Evaluation Infrastructure | 5-7 days | ✅ Complete |
| **8.5** | **Level 3 Instance Generation** | **3-5 days** | **⏳ New** |
| 9 | Pilot Evaluation (All 3 Levels) | 2-3 days | ⏳ Pending |
| 10 | Full Evaluation + Analysis | 5-7 days | ⏳ Pending |
| 11-12 | Advanced Analyses | 2 weeks | ⏳ Pending |
| 13 | HPC Production | 1 week | ⏳ Pending |
| 14 | Paper Integration + Submission | 1 week | ⏳ Pending |

**Total Timeline**: 14.5 weeks (added 0.5 weeks for Level 3)  
**Current Progress**: 8 of 14.5 weeks (55%)  
**Remaining**: 6.5 weeks

---

## Risk Assessment & Mitigation

### Risk 1: Level 3 Generation Takes Longer Than Expected

**Likelihood**: Medium  
**Impact**: High (blocks paper claims)

**Mitigation**:
- Start with minimum viable (20-30 instances)
- Parallelize domains (different team members if available)
- Use templates from hand-validated examples
- Accept lower novelty initially (Nov = 0 acceptable for pilot)

**Contingency**:
- If blocked: revert to Option 3 from OBJECTIVE_ACCOUNTING.md (scope reduction)
- Update paper to "grounding framework with extension to novelty/revision"
- Position Level 3 as "validated framework, full evaluation future work"

### Risk 2: Level 3 Instances Don't Validate

**Likelihood**: Low (framework already validated on 3 examples)  
**Impact**: High

**Mitigation**:
- Unit test every instance during generation
- Use existing conservativity checker
- Start with simple defeaters (penguin-style)
- Gradual complexity increase

**Contingency**:
- Debug conservativity checker
- Simplify defeater complexity
- Accept subset of valid instances

### Risk 3: Models Fail Completely on Level 3

**Likelihood**: Medium  
**Impact**: Medium (still publishable, shows limitation)

**Mitigation**:
- This is actually a finding (models can't do belief revision)
- Paper value: showing gap between grounding and revision
- CoT prompting may help

**Contingency**:
- Frame as "novel benchmark revealing limitations"
- Focus on ceiling analysis (symbolic solver can do it)
- Implications for future model design

### Risk 4: Timeline Slippage

**Likelihood**: Medium  
**Impact**: Medium

**Mitigation**:
- Week 8.5 is well-scoped (3-5 days realistic)
- Can work in parallel with Week 9 prep
- Pilot can proceed with subset

**Contingency**:
- Reduce Week 11-12 scope if needed
- HPC production is optional for initial submission
- Focus on development dataset results

---

## Resource Requirements

### Compute Resources

**Local Development** (Weeks 8.5-10):
- Standard laptop sufficient for instance generation
- Llama 3 requires ~40GB RAM (have this)
- API calls for GPT/Claude/Gemini

**HPC Production** (Week 13):
- CURC Alpine allocation (existing)
- Parallel instance generation
- Large-scale evaluation

### API Costs (Revised)

**Week 9 Pilot**:
- 240-300 queries × ~$0.015 avg = $4-5
- **Budget**: $10 (with buffer)

**Week 10 Full Evaluation**:
- 16,600 queries vs original 14,960
- Cost increase: ~10%
- **Budget**: $150-200 (vs original $135-200)

**Total Project**: $160-210 (vs original $136-201)

**Increase**: ~$25-35 for Level 3 coverage  
**Value**: Can claim all three objectives

### Human Time

**Week 8.5** (Level 3 generation):
- Instance creation: 2-3 days
- Validation & testing: 1 day
- Documentation: 0.5 day
- **Total**: 3.5-4.5 days concentrated work

**Week 9-14**: As originally planned

---

## Success Metrics

### Week 8.5 Success

- [ ] 20-30 Level 3 instances minimum (35-50 target)
- [ ] All instances validated for conservativity
- [ ] At least 5 instances with Nov > 0
- [ ] All tests passing
- [ ] Ready for pilot evaluation

### Week 9 Success

- [ ] Pilot evaluation runs successfully
- [ ] All three objectives measured empirically
- [ ] Cost estimates validated (<$10)
- [ ] Pipeline stability confirmed
- [ ] Results are sensible/interpretable

### Week 10 Success

- [ ] Full evaluation complete (16,600 queries)
- [ ] Results for all three objectives
- [ ] Statistical significance achieved
- [ ] Cost within budget ($150-200)
- [ ] Ready for paper integration

### Project Success

**Minimum (Publishable)**:
- ✅ All three objectives addressed in implementation
- ✅ Empirical evidence for all three (even if preliminary for Level 3)
- ✅ Framework validated and tested
- ✅ Clear future work trajectory

**Target (Strong Paper)**:
- ✅ Comprehensive grounding evaluation (374 instances)
- ✅ Substantive novelty evaluation (35-50 Level 3 instances)
- ✅ Substantive belief revision evaluation (conservativity analysis)
- ✅ All analyses complete
- ✅ HPC production validation

---

## Immediate Next Steps

### This Week (Week 8.5 Start)

**Day 1-2: Biology Defeaters**
1. Review textbook exceptions for vertebrates
2. Create 15-20 defeater instances
3. Validate conservativity for each
4. Generate distractors

**Day 3: Legal Defeaters**
1. Identify statutory exception patterns
2. Create 10-15 legal defeater instances
3. Validate conservativity
4. Some with novel predicates (Nov > 0)

**Day 4: Materials Defeaters**
1. Materials science exception cases
2. Create 10-15 materials defeater instances
3. High novelty target (Nov > 0.3)
4. Validate conservativity

**Day 5: Validation**
1. Run all unit tests
2. Integration testing
3. Documentation
4. Prepare for pilot

### Next Week (Week 9)

**Pilot Evaluation**:
1. Run 240-300 queries
2. Analyze results
3. Validate all three objectives
4. Go/no-go for full evaluation

---

## Conclusion

### The Critical Addition

Adding **Week 8.5: Level 3 Instance Generation** addresses the gap identified in OBJECTIVE_ACCOUNTING.md:

**Before**: Could only test grounding (Level 2)  
**After**: Can test all three objectives (grounding, novelty, belief revision)

**Cost**: 3-5 days + $25-35 additional API costs  
**Benefit**: Can deliver on paper's full promise

### Alignment with Paper

This revised plan ensures we can make all claims from paper.tex:

1. ✅ "Grounding, Novelty, and Belief Revision" (title)
2. ✅ "Three-level evaluation hierarchy" (line 192)
3. ✅ "Controlled measures of novelty, revision, and difficulty" (line 194)
4. ✅ "Testing grounding, novelty, and rational revision" (line 192)

### The Path Forward

**Recommended**: Implement Week 8.5 immediately
- 3-5 days of focused work
- Generates 35-50 Level 3 instances
- Enables full paper claims
- Publishable at NeurIPS with all three objectives

**Alternative**: If time-constrained, generate minimum viable (20-30 instances)
- Still demonstrates all three objectives
- Frame as "preliminary" for Level 3
- Honest about scope

**Not Recommended**: Skip Level 3 entirely
- Violates paper's core claims
- Reduces novelty of contribution
- Misses opportunity to test belief revision

---

**Author**: Patrick Cooper  
**Date**: 2026-02-13  
**Next Action**: Begin Week 8.5 (Level 3 instance generation)  
**Timeline**: On track for NeurIPS submission with all objectives addressed
