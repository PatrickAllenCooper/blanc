# NeurIPS Submission Roadmap: MVP to Full DeFAb Benchmark

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Current Status**: MVP Complete & Validated  
**Target**: NeurIPS 2026 Submission-Ready Benchmark

## Executive Summary

This document charts the path from the validated MVP (15 instances, 1 KB) to the full DeFAb benchmark (1000+ instances, 3+ KBs, 4 modalities) ready for NeurIPS submission.

**Timeline**: 8 weeks  
**Effort**: Full-time focused development  
**Risk**: LOW (foundation validated)  
**Confidence**: HIGH (all core components working)

---

## Current State (MVP Baseline)

### What We Have

✅ **Complete Pipeline**:
- Defeasible reasoning engine (Definition 7)
- Conversion with 4 partition strategies (Defs 9-10)
- Criticality computation (Definition 18)
- Instance generation (Levels 1-3)
- M4+D1 codec with 100% round-trip

✅ **Validated Implementation**:
- 107/107 tests passing
- 81% average coverage
- 4 propositions verified
- Zero bugs in production

✅ **Proof of Concept**:
- 15 valid instances
- Avian Biology KB
- 100% round-trip accuracy
- 100% conservativity (Level 3)

### What We Need

🎯 **Scale Requirements**:
- 3+ knowledge bases (biology, legal, materials science from paper)
- 1000+ instances (statistically significant)
- 4 modalities (M1-M4 for rendering-robust accuracy)
- LLM evaluation pipeline
- Statistical analysis (Section 4.3 from paper)

🎯 **Quality Requirements**:
- Same rigor (100% test coverage on critical paths)
- Mathematical exactness (every function → definition)
- Empirical validation (all propositions tested)
- Production-ready code

---

## Phase 1: Knowledge Base Expansion (Weeks 1-2)

**Goal**: Scale from 1 KB to 3 KBs with 150+ instances

### Week 1: Medical Diagnosis KB

**Tasks**:
1. Create medical diagnosis knowledge base (50-100 rules)
   - Diseases, symptoms, risk factors
   - Diagnostic rules (flu, COVID, measles, etc.)
   - Treatment recommendations
   - Based on existing examples/knowledge_bases/medical.pl

2. Convert to defeasible with partition_rule
   - Facts (symptoms): strict
   - Diagnostic rules: defeasible
   - Exceptional cases: defeaters

3. Generate 50 instances
   - 15 Level 1 (symptom identification)
   - 30 Level 2 (diagnostic rule abduction)
   - 5 Level 3 (exceptional diagnoses)

4. Validate all instances
   - 100% validity target
   - Document any edge cases

**Deliverables**:
- examples/knowledge_bases/medical_diagnosis/
- 50 instances (medical_diagnosis_v1.json)
- Test suite extended (+15 tests)

**Success Criteria**:
- [ ] 50 instances generated
- [ ] 100% validity rate
- [ ] Medical KB documented
- [ ] All tests passing

### Week 2: Family Relations & Legal Reasoning KBs

**Tasks**:
1. **Family Relations KB** (25 instances)
   - Based on existing examples/knowledge_bases/family.pl
   - Expand to 30-50 rules
   - Kinship, inheritance, family structure
   - Generate 25 instances

2. **Legal Reasoning KB** (25 instances)
   - Based on TaxKB (already downloaded)
   - Extract 50-100 legal rules
   - Statutory rules, precedents, exceptions
   - Generate 25 instances

3. Merge all datasets
   - Total: 100+ instances across 3 domains
   - Validate cross-KB consistency

**Deliverables**:
- examples/knowledge_bases/family_relations/
- examples/knowledge_bases/legal_reasoning/
- 50 additional instances
- Merged dataset (150+ instances total)

**Success Criteria**:
- [ ] 100+ total instances
- [ ] 3 knowledge bases operational
- [ ] All domains represented (bio, medical, legal/family)
- [ ] 100% validity maintained

---

## Phase 2: Additional Modalities (Weeks 3-4)

**Goal**: Implement M1-M3 encoders, D2 decoder for rendering-robust accuracy

### Week 3: M3 (Annotated Formal) & M2 (Semi-Formal)

**Tasks**:
1. **M3 Encoder** (Annotated Formal)
   - Format: Prolog syntax + natural language comments
   - Example: `flies(X) :- bird(X). % Typically, birds fly.`
   - Definition 26, Appendix B line 879

2. **M2 Encoder** (Semi-Formal)
   - Format: Logical connectives + NL predicates
   - Example: `bird(X) ∧ ¬penguin(X) ⇒ flies(X) [defeasible]`
   - Definition 26, Appendix B line 877

3. **Ontological Grounding Map** (for M2-M3)
   - NL: HB → L* mapping (Definition 28)
   - Create for each KB domain
   - Ensure injectivity (critical!)

4. **Round-trip testing**
   - Target: >95% for M3
   - Target: >90% for M2
   - Validate on all 150+ instances

**Deliverables**:
- codec/m3_encoder.py
- codec/m2_encoder.py
- codec/nl_map.py (NL mapping infrastructure)
- 20+ additional round-trip tests

**Success Criteria**:
- [ ] M3 encoder working (>95% round-trip)
- [ ] M2 encoder working (>90% round-trip)
- [ ] NL maps for all 3 KBs
- [ ] All tests passing

### Week 4: M1 (Narrative) & D2 (Template Extraction)

**Tasks**:
1. **M1 Encoder** (Narrative - HARDEST)
   - Full natural language with hedging
   - Example: "Typically, if something is a bird, then it can fly."
   - Appendix B lines 870-875
   - Requires sophisticated NL generation

2. **D2 Decoder** (Template Extraction)
   - Edit distance matching
   - python-Levenshtein for distance
   - Definition 29, Proposition line 894

3. **Rendering-robust accuracy**
   - Definition 31: Worst-case over modalities
   - Test on all 150+ instances
   - Compare M1 vs M4 performance

**Deliverables**:
- codec/m1_encoder.py
- codec/d2_decoder.py
- Rendering-robust accuracy metric
- 30+ additional tests

**Success Criteria**:
- [ ] M1 encoder working (target: >85% round-trip with D2)
- [ ] D2 decoder working (sound + complete)
- [ ] All 4 modalities operational
- [ ] Rendering-robust accuracy computable

---

## Phase 3: Automated Level 3 & Scaling (Weeks 5-6)

**Goal**: Automate Level 3 generation, scale to 500+ instances

### Week 5: Automated Level 3 Generation

**Tasks**:
1. **Candidate defeater space** (Definition 15)
   - Implement R_df(L) generation
   - Language bias constraints
   - Efficient enumeration (lazy evaluation)

2. **Conservativity checking at scale**
   - Optimize expectation set computation
   - Parallel checking
   - Cache aggressively

3. **Automated Level 3 pipeline**
   - Find anomalies in D^-
   - Search candidate space
   - Verify conservativity
   - Generate 50+ Level 3 instances

**Deliverables**:
- author/level3.py (automated generation)
- generation/language_bias.py
- 50+ Level 3 instances
- Conservativity validation report

**Success Criteria**:
- [ ] Automated Level 3 generation working
- [ ] 50+ Level 3 instances
- [ ] >90% conservativity rate
- [ ] Performance acceptable (<5 min for 50 instances)

### Week 6: Scale to 500+ Instances

**Tasks**:
1. Generate instances across all 3 KBs
   - Biology: 200 instances
   - Medical: 200 instances
   - Legal/Family: 100 instances

2. Partition strategy variations
   - Test κ_leaf, κ_depth in addition to κ_rule
   - Compare yield curves
   - Proposition 3 validation at scale

3. Distractor quality analysis
   - Test all 3 strategies (random, syntactic, adversarial)
   - Measure difficulty impact
   - Select optimal strategy per level

4. Dataset validation
   - 100% validity check
   - Round-trip on all instances
   - Statistical analysis (Section 4.3)

**Deliverables**:
- 500+ total instances
- Multi-KB dataset (JSON)
- Statistical analysis report
- Partition comparison study

**Success Criteria**:
- [ ] 500+ instances generated
- [ ] All 3 KBs represented
- [ ] 100% validity maintained
- [ ] Section 4.3 statistics computed

---

## Phase 4: LLM Evaluation & Analysis (Weeks 7-8)

**Goal**: Complete evaluation pipeline, submission-ready results

### Week 7: LLM Evaluation Pipeline

**Tasks**:
1. **Model interface** (Definitions 31-32)
   - OpenAI API (GPT-4, GPT-4o)
   - Anthropic API (Claude 3.5 Sonnet)
   - Google API (Gemini 1.5 Pro)
   - Open models (Llama 3 70B via Ollama/vLLM)

2. **Rendering-robust accuracy** (Definition 31)
   - Evaluate each model on all 4 modalities
   - Compute worst-case accuracy
   - Per-level accuracy breakdown

3. **Graded scoring** (Section 4.5)
   - Implement partial credit for Level 3
   - Score: 0, 0.25, 0.5, 0.75, 1.0
   - Categorize by resolution type

4. **Batch evaluation**
   - Process all 500+ instances
   - All 4 models
   - All 4 modalities
   - Collect results

**Deliverables**:
- experiments/evaluation.py
- experiments/partial_credit.py
- LLM evaluation results (JSON)
- Per-model accuracy reports

**Success Criteria**:
- [ ] 4+ models evaluated
- [ ] All modalities tested
- [ ] Rendering-robust accuracy computed
- [ ] Results stored and reproducible

### Week 8: Analysis & Submission Prep

**Tasks**:
1. **Statistical analysis** (Section 4.3)
   - Volume and balance
   - Structural difficulty distributions
   - Novelty and revision spectrum (Level 3)
   - Yield analysis
   - Partition sensitivity

2. **Results analysis** (Section 4.4-4.7)
   - Per-model performance
   - Per-level accuracy
   - Modality-level interaction
   - Error taxonomy

3. **Visualization**
   - Accuracy plots (by model, level, modality)
   - Difficulty distributions
   - Yield curves
   - Error analysis

4. **Submission materials**
   - Update paper.tex with results
   - Create supplementary materials
   - Code release preparation
   - Dataset documentation

**Deliverables**:
- experiments/statistics.py (Section 4.3)
- Results section for paper
- Figures and tables
- Supplementary materials

**Success Criteria**:
- [ ] Section 4.3 statistics complete
- [ ] All results analyzed
- [ ] Paper updated with findings
- [ ] Submission package ready

---

## Detailed Task Breakdown

### Phase 1, Week 1: Medical Diagnosis KB

**Day 1-2**: KB Construction
```python
# medical_diagnosis.py
- 20+ diseases (flu, covid, measles, pneumonia, etc.)
- 50+ symptoms (fever, cough, fatigue, etc.)
- 30+ diagnostic rules
- 10+ risk factors
- 5+ defeaters (atypical presentations)
```

**Day 3**: Conversion & Validation
- Convert with partition_rule
- Validate all derivations
- Test defeasible reasoning on medical domain

**Day 4-5**: Instance Generation
- Generate 15 L1 (symptom facts)
- Generate 30 L2 (diagnostic rules)
- Generate 5 L3 (atypical cases)
- Validate all instances

**Tests**: +15 tests for medical KB

### Phase 1, Week 2: Family & Legal KBs

**Day 1-2**: Family Relations
- Expand existing family.pl
- Add inheritance rules
- Add complex kinship
- Generate 25 instances

**Day 3-4**: Legal Reasoning
- Extract from TaxKB
- Simplify for testability
- Add precedent-exception structure
- Generate 25 instances

**Day 5**: Integration
- Merge all datasets
- Cross-KB validation
- Statistical summary

### Phase 2, Week 3: M3 & M2 Encoders

**Day 1-2**: M3 Implementation
- Annotated formal templates
- Integrate with NL map
- Test round-trip (target >95%)

**Day 3-4**: M2 Implementation
- Semi-formal templates
- Logical connectives + NL
- Test round-trip (target >90%)

**Day 5**: NL Mapping
- Create maps for all 3 KBs
- Validate injectivity
- Test composition

### Phase 2, Week 4: M1 & D2

**Day 1-3**: M1 Narrative
- Natural language templates
- Hedging for defeasibility
- Universal quantification
- Test round-trip with D2

**Day 4-5**: D2 Template Decoder
- Edit distance implementation
- Template matching
- Soundness and completeness tests

### Phase 3, Week 5: Automated Level 3

**Day 1-2**: Candidate Generation
- Implement R_df(L) enumeration
- Language bias per KB
- Efficient search strategies

**Day 3-4**: Conservativity at Scale
- Optimize expectation computation
- Parallel checking
- Batch validation

**Day 5**: Generate Level 3
- 50+ automated instances
- Validate conservativity
- Quality analysis

### Phase 3, Week 6: Scale to 500+

**Day 1-3**: Mass Generation
- Biology: 200 instances
- Medical: 200 instances
- Legal/Family: 100 instances

**Day 4-5**: Analysis
- Statistical validation
- Difficulty distributions
- Partition comparisons

### Phase 4, Week 7: LLM Evaluation

**Day 1-2**: Infrastructure
- Model APIs
- Batch processing
- Error handling

**Day 3-5**: Evaluation
- Run all models
- All modalities
- Collect results

### Phase 4, Week 8: Final Analysis

**Day 1-3**: Statistical Analysis
- Compute all metrics
- Generate figures
- Write results

**Day 4-5**: Submission Prep
- Update paper
- Prepare supplementary
- Final validation

---

## Success Metrics

### Quantitative Targets

| Metric | MVP | Target | Stretch |
|--------|-----|--------|---------|
| Total instances | 15 | 500 | 1000 |
| Knowledge bases | 1 | 3 | 5 |
| Modalities | 1 (M4) | 4 | 4 |
| Round-trip (M4+D1) | 100% | 100% | 100% |
| Round-trip (M1+D2) | - | 85% | 90% |
| Models evaluated | 0 | 4 | 6 |
| Test coverage | 81% | 85% | 90% |

### Qualitative Targets

- [ ] All propositions verified at scale
- [ ] Error taxonomy documented
- [ ] Difficulty ordering empirically confirmed
- [ ] Modality-level interaction tested
- [ ] Conservativity rate >90%

---

## Risk Assessment & Mitigation

### High-Risk Components

#### 1. M1 Encoder (Narrative) - 30% Risk

**Challenge**: Natural language generation with semantic fidelity

**Mitigation**:
- Start with template-based approach
- Use LLM for paraphrasing (GPT-4 for generation)
- Validate with human review for sample
- Fallback: Use M2 (semi-formal) as "narrative enough"

#### 2. Automated Level 3 - 25% Risk

**Challenge**: Candidate space exponential, conservativity expensive

**Mitigation**:
- Small language bias (ar_max ≤ 3)
- Parallel conservativity checking
- Time limit per instance (discard if too slow)
- Fallback: 50 instances sufficient (vs. 100+)

#### 3. Large-Scale Generation - 20% Risk

**Challenge**: 500+ instances might reveal edge cases

**Mitigation**:
- Incremental scaling (50 → 100 → 200 → 500)
- Validate at each step
- Fix issues before scaling further
- Automated validation catches problems early

#### 4. LLM Evaluation - 15% Risk

**Challenge**: API rate limits, costs, reproducibility

**Mitigation**:
- Cache all responses
- Use smaller subset for pilot (50 instances)
- Deterministic sampling (temperature=0)
- Multiple runs for robustness

#### 5. Statistical Analysis - 10% Risk

**Challenge**: Complex analysis, may not match paper predictions

**Mitigation**:
- Follow Section 4.3 exactly
- Implement incrementally
- Validate on MVP first
- Report observed patterns honestly

### Contingency Plans

**If Week 1-2 Delays**:
- Scale to 2 KBs instead of 3 (bio + medical)
- Target 300 instances vs. 500

**If M1 Too Hard**:
- Focus on M2-M4 (3 modalities sufficient)
- Use M2 as "semi-natural"

**If Automated L3 Fails**:
- Hand-craft 50 Level 3 instances
- Document manual process
- Defer automation to future work

**If LLM Evaluation Blocked**:
- Use oracle evaluation (perfect accuracy baseline)
- Compare modality faithfulness
- Defer LLM results to follow-up

---

## Resource Requirements

### Computational

- **Development**: Standard laptop (current setup)
- **LLM Evaluation**: API credits
  - GPT-4: ~$50-100 for 500 instances × 4 modalities
  - Claude: ~$50-100
  - Gemini: ~$30-50
  - Llama: Local (free)
  - **Total**: ~$200-300

- **Time**: ~2-4 hours per 100 instances (generation + validation)

### Knowledge Base Sources

✅ **Already Available**:
- TaxKB (legal) - downloaded
- Medical KB - have example
- Family KB - have example
- ProofWriter - could mine for additional domains

🎯 **To Create**:
- Expand existing examples to 50-100 rules each
- Mine from open knowledge bases
- Manual curation where needed

### Personnel

- **Solo development**: Feasible (MVP proven)
- **Recommended**: 1-2 additional for:
  - KB curation
  - LLM evaluation monitoring
  - Statistical analysis review

---

## Quality Assurance Plan

### Testing Strategy

**Maintain 90% Coverage**:
- Every new encoder: 10+ round-trip tests
- Every KB: 5+ integration tests
- Every batch: automated validation

**Regression Prevention**:
- Run full test suite after each change
- No commit if tests fail
- Weekly integration tests

**Performance Monitoring**:
- Benchmark critical operations
- Alert if >2x slowdown
- Profile and optimize as needed

### Validation Protocol

**Per KB**:
1. Validate theory is well-formed
2. Test sample derivations manually
3. Generate 10 instances
4. Validate all before scaling

**Per Modality**:
1. Round-trip on 20 examples
2. Test on all instance levels
3. Validate on full dataset
4. Measure accuracy

**Per Batch**:
1. Generate instances
2. Validate 100% before proceeding
3. Encode in all modalities
4. Test round-trip sample

---

## Deliverables Timeline

### End of Phase 1 (Week 2)
- [ ] 3 knowledge bases operational
- [ ] 150+ instances generated
- [ ] All valid and tested
- [ ] Multi-KB dataset released

### End of Phase 2 (Week 4)
- [ ] 4 modalities implemented (M1-M4)
- [ ] 2 decoders working (D1-D2)
- [ ] Rendering-robust accuracy metric
- [ ] Round-trip >85% on all modalities

### End of Phase 3 (Week 6)
- [ ] 500+ instances total
- [ ] 50+ automated Level 3
- [ ] Statistical analysis (Section 4.3)
- [ ] Dataset finalized

### End of Phase 4 (Week 8)
- [ ] 4+ models evaluated
- [ ] Results analysis complete
- [ ] Paper updated with findings
- [ ] Submission package ready

---

## Submission Checklist

### Dataset Requirements

- [ ] 500+ instances minimum (target: 1000+)
- [ ] 3+ knowledge bases
- [ ] All 3 levels represented
- [ ] 4 modalities for each instance
- [ ] JSON format with metadata
- [ ] Documentation complete

### Code Requirements

- [ ] All code released (MIT license)
- [ ] Installation tested on clean environment
- [ ] README with quick start
- [ ] Examples and tutorials
- [ ] API documentation

### Paper Requirements

- [ ] Section 4.3: Dataset statistics complete
- [ ] Section 4.4-4.7: Evaluation results
- [ ] All figures generated
- [ ] All tables populated
- [ ] Supplementary materials prepared

### Reproducibility

- [ ] Random seeds documented
- [ ] Dependencies pinned
- [ ] Scripts for all experiments
- [ ] Cached LLM responses
- [ ] Docker container (optional)

---

## Budget Estimates

### Time Budget

```
Phase 1 (KBs):        80 hours (2 weeks)
Phase 2 (Modalities): 80 hours (2 weeks)
Phase 3 (Scaling):    80 hours (2 weeks)
Phase 4 (Evaluation): 80 hours (2 weeks)
------------------------------------------
Total:                320 hours (8 weeks)
```

### Cost Budget

```
LLM API calls:        $200-300
Compute (optional):   $50-100
Total:                $250-400
```

### Personnel Budget

```
Primary developer:    Full-time (8 weeks)
KB curator (opt):     Part-time (2 weeks)
Reviewer (opt):       Part-time (1 week)
```

---

## Success Criteria

### Minimum Viable Submission

**Required for acceptance**:
- 500+ instances across 3 domains
- 3+ modalities working
- 2+ models evaluated
- Statistical analysis complete
- All core propositions verified

### Strong Submission

**Competitive for acceptance**:
- 1000+ instances across 3+ domains
- 4 modalities (M1-M4)
- 4+ models (GPT-4, Claude, Gemini, Llama)
- Comprehensive analysis (Section 4.3-4.7)
- Novel findings documented

### Exceptional Submission

**Top-tier contribution**:
- 1000+ instances, 5+ domains
- All modalities + multiple decoders
- 6+ models including scaling study
- Deep error analysis
- Reproducibility package
- Public dataset release

---

## Next Actions (This Week)

### Immediate (Day 1-2)

1. **Repo cleanup** (DONE)
   - Archive weekly reports
   - Consolidate MVP docs
   - Update guidance documents

2. **Medical KB preparation**
   - Review existing medical.pl
   - Design expansion (50-100 rules)
   - Plan instance generation

3. **Test infrastructure**
   - Set up multi-KB testing
   - Create integration test suite
   - Prepare benchmarking scripts

### Start of Week 1 (Day 3-5)

1. **Implement Medical KB**
2. **Generate 50 instances**
3. **Validate all**
4. **Update documentation**

---

## Conclusion

The MVP has validated the paper's core framework. The path from 15 instances to 1000+ is clear, with well-defined milestones and manageable risks.

**Recommendation**: Begin Phase 1 immediately.

**Timeline**: 8 weeks to submission-ready benchmark  
**Confidence**: HIGH - foundation is solid  
**Risk**: LOW - all core components validated

---

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Status**: Roadmap approved, ready to begin Phase 1  
**Target**: NeurIPS 2026 Datasets & Benchmarks Track
