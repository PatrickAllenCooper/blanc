# Phase 3 Design Complete: Author Algorithm Implementation

**Date**: 2026-02-11  
**Author**: Patrick Cooper  
**Status**: Design phase complete, ready for implementation

## What Was Created

### 1. IMPLEMENTATION_PLAN.md (Primary Technical Specification)

**Purpose**: Complete 80+ page technical specification for implementing the DeFAb benchmark generation pipeline.

**Contents**:
- Mathematical foundation (all 35 definitions from paper)
- Project architecture (directory structure, dependencies)
- Implementation phases (3A-4B, 10 weeks)
- Testing strategy (unit, integration, property-based, benchmarks)
- Risk mitigation (codec 40%, level 3 30%, expectations 20%)
- Validation criteria (propositions, theorems, complexity guarantees)

**Key Sections**:
1. Mathematical Foundation: Maps every definition to code
2. Project Architecture: 7 new directories, 30+ files
3. Implementation Phases: Week-by-week breakdown
4. Testing Strategy: 4 types of tests, >90% coverage target
5. Validation & Verification: All propositions must verify
6. Risk Mitigation: Fallback strategies for each component
7. Implementation Schedule: 10-week timeline
8. Success Criteria: Functional, performance, testing, mathematical

### 2. author.py (Mathematical Reference Implementation)

**Purpose**: Definitive reference mapping all paper definitions to executable Python code.

**Contents**:
- Section 1: Definite Logic Programs (Defs 1-5)
- Section 2: Defeasible Theories (Defs 6-7)
- Section 3: Conversion (Defs 8-10)
- Section 4: Support & Criticality (Defs 17-20)
- Section 5: Instance Generation (Defs 20-22)
- Section 6: Level 3 Defeater Abduction (Defs 11-16)
- Section 7: Metrics (Defs 33-35)

**Key Features**:
- Every function documented with paper definition number and line numbers
- Complexity bounds specified (O(|R|·|F|), O(|D|²·|F|), etc.)
- Propositions to verify listed explicitly
- Paper examples (Tweety, IDP) specified as tests
- Not-implemented stubs point to actual implementation files

### 3. Phase3_Implementation_Plan.md (Structured Development Guide)

**Purpose**: Structured guide for Phase 3 development with milestones and validation criteria.

**Contents**:
- Architecture overview
- Week-by-week implementation phases
- Mathematical correctness checklist
- Risk management strategies
- Testing strategy breakdown
- Validation milestones
- Dependencies and tooling

**Key Features**:
- Clear milestones with validation criteria
- Risk levels quantified (40%, 30%, 20%, 10%)
- Fallback strategies for each risk
- 6 major milestones with pass/fail criteria

### 4. Updated Documentation

**Updated Files**:
- `Guidance_Documents/API_Design.md`: Added Phase 3 sections, updated changelog
- `README.md`: Updated project status to Phase 3
- Both now reflect current implementation state

## Architecture Overview

### New Directories (7)

```
blanc/
├── author/         # Core algorithm (5 files)
├── codec/          # Rendering system (5 files) - CRITICAL
├── reasoning/      # Defeasible logic (4 files)
├── generation/     # Helpers (3 files)
└── experiments/    # Evaluation (4 files)
```

### Critical Components

1. **author/** - The author algorithm (core MVP)
   - `conversion.py`: Defeasible conversion φ_κ(Π) (Defs 8-10)
   - `support.py`: Criticality computation Crit*(D,q) (Defs 17-20)
   - `generation.py`: Level 1-2 instance generation (Defs 20-21)
   - `level3.py`: Defeater abduction (Defs 11-16)
   - `metrics.py`: Novelty, revision distance (Defs 33-35)
   - `pipeline.py`: End-to-end orchestration

2. **codec/** - Rendering system (HIGHEST RISK - 40%)
   - `encoder.py`: 4 modalities M1-M4 (narrative to pure formal)
   - `decoder.py`: 3 strategies D1-D3 (exact, template, semantic)
   - `nl_map.py`: Ontological grounding NL: HB → L*
   - `templates.py`: Rendering templates from Appendix B
   - `validation.py`: Round-trip consistency testing

3. **reasoning/** - Defeasible logic engine
   - `defeasible.py`: D ⊢∂ q in O(|R|·|F|) (Def 7, Theorem 11)
   - `derivation_tree.py`: AND-OR tree T(D,q) (Def 13)
   - `expectations.py`: Exp(D) computation (Def 11)
   - `team_defeat.py`: Team defeat implementation

4. **generation/** - Supporting tools
   - `partition.py`: 4 partition functions (Def 10)
   - `distractor.py`: 3 distractor strategies
   - `language_bias.py`: Candidate space generation (Defs 14-15)

5. **experiments/** - Evaluation pipeline
   - `dataset.py`: DeFAb dataset container
   - `evaluation.py`: Rendering-robust accuracy (Def 31)
   - `partial_credit.py`: Graded scoring for Level 3 (§4.5)
   - `statistics.py`: Dataset statistics (§4.3)

## Mathematical Rigor

### All Definitions Mapped

35 definitions from paper.tex:
- ✓ Defs 1-5: Logic programs, Herbrand models
- ✓ Defs 6-7: Defeasible theories, derivation
- ✓ Defs 8-10: Conversion, partitions
- ✓ Defs 11-16: Anomalies, Level 3 generation
- ✓ Defs 17-20: Support, criticality
- ✓ Defs 21-22: Instance generation, yield
- ✓ Defs 23-32: Rendering codec, evaluation
- ✓ Defs 33-35: Metrics

### Propositions to Verify (6)

1. **Proposition 1**: Conservative conversion (κ ≡ s ⟹ M_Π = {q | D_κ ⊢Δ q})
2. **Proposition 2**: Definite implies defeasible (D ⊢Δ q ⟹ D ⊢∂ q)
3. **Proposition 3**: Yield monotonicity (E[Y(κ_rand(δ))] non-decreasing in δ)
4. **Proposition 4**: Criticality inclusion (Crit*(D,q) ⊆ Crit(D,q))
5. **Proposition 5**: Candidate space size (|R_df(L)| = O(|P⁺|^ar_max · |P⁻|))
6. **Proposition 6**: Gold set non-empty (r* ∈ R* for Level 3)

### Theorems to Verify (1)

**Theorem 11**: Defeasible derivation in P, computable in O(|R|·|F|)

### Complexity Guarantees

| Operation | Target Complexity | Verification Method |
|-----------|------------------|---------------------|
| Defeasible derivation D ⊢∂ q | O(\|R\| · \|F\|) | Benchmark scaling test |
| Full-theory criticality Crit*(D,q) | O(\|D\|² · \|F\|) | Benchmark scaling test |
| Full pipeline per instance | O(\|D\|³) | End-to-end timing |

## Implementation Timeline

### 10-Week Schedule

| Week | Phase | Deliverable | Validation |
|------|-------|-------------|------------|
| 1-2 | 3A | Defeasible reasoning | Tweety, Theorem 11 |
| 2 | 3B | Conversion & partitions | Prop 1, Prop 3 |
| 3 | 3C | Support & criticality | Prop 4, complexity |
| 4 | 3D | Instance gen (L1-2) | Instance validity |
| 5-6 | 3E | Level 3 (defeaters) | **IDP example** |
| 7-8 | 4A | Rendering codec | Round-trip >95% |
| 9 | 4B | Evaluation pipeline | Graded scoring |
| 10 | - | Validation & polish | All tests pass |

### Critical Milestones

1. **Week 2**: Defeasible reasoning works (Tweety + Theorem 11)
2. **Week 4**: Levels 1-2 generate valid instances
3. **Week 6**: **IDP example works** (HEADLINE TEST)
4. **Week 8**: Codec round-trip >95%
5. **Week 10**: MVP complete (1000 instances, >90% coverage)

## Risk Assessment

### Quantified Risks

1. **Codec (40% of total risk)**
   - Challenge: 4 modalities, 3 decoders, injectivity constraints
   - Mitigation: Extensive round-trip testing, fallback to M4 only
   - Libraries: Lark parser + transformers

2. **Level 3 Generation (30% of total risk)**
   - Challenge: Conservative resolution, candidate space enumeration
   - Mitigation: Hand-authored defeaters first, IDP as test
   - Fallback: Focus MVP on Levels 1-2

3. **Expectation Set Computation (20% of total risk)**
   - Challenge: O(|HB| · |R| · |F|) potentially expensive
   - Mitigation: Limit to small Herbrand bases, memoization
   - Fallback: Sample expectations, lazy evaluation

4. **Defeasible Derivation (10% of total risk)**
   - Challenge: Team defeat correctness, complexity guarantee
   - Mitigation: Test against ProofWriter benchmark
   - Libraries: Consider DePYsible, silkie

### Fallback Strategies

Each risk has a documented fallback:
- Codec fails → Use M4 only, multiple-choice evaluation
- Level 3 fails → Focus on L1-2, defer defeaters
- Expectations fail → Sample subset, overapproximate
- Derivation fails → Use existing library (DePYsible)

## Testing Strategy

### 4 Types of Tests

1. **Unit Tests**: Every function, every proposition
   - `test_proposition_1()` through `test_proposition_6()`
   - `test_theorem_11_complexity()`
   - Paper examples: Tweety, IDP, family, medical

2. **Integration Tests**: End-to-end pipelines
   - `test_level1_generation_pipeline()`
   - `test_level2_generation_pipeline()`
   - `test_level3_generation_pipeline()`

3. **Property-Based Tests** (Hypothesis): Random inputs
   - `test_derivation_deterministic()`
   - `test_instance_validity()`
   - `test_round_trip_consistency()`

4. **Benchmark Tests**: Against known datasets
   - `test_proofwriter_benchmark()`
   - `test_performance_regression()`

### Coverage Target

- >90% code coverage overall
- 100% coverage for critical paths (criticality, derivation)
- All paper examples must reproduce exactly

## Success Criteria

### Functional

- [ ] Generate Level 1 instances (fact completion)
- [ ] Generate Level 2 instances (rule abduction)
- [ ] Generate Level 3 instances (defeater abduction)
- [ ] Implement all 4 rendering modalities (M1-M4)
- [ ] Implement all 3 decoder strategies (D1-D3)

### Performance

- [ ] O(|D|² · |F|) criticality computation verified
- [ ] O(|R| · |F|) defeasible derivation verified
- [ ] Generate 1000 instances in <1 hour

### Mathematical

- [ ] All 6 propositions verified
- [ ] Theorem 11 complexity bound met
- [ ] IDP example reproduces exactly
- [ ] Conservativity implements AGM minimal change

### Testing

- [ ] >90% code coverage
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All property-based tests pass

## Key Design Decisions

### 1. Use Crit* (polynomial) not minimal support (NP-complete)

For instance generation, we use full-theory criticality Crit*(D,q) which is O(|D|²·|F|) instead of minimal support sets Supp(D,q) which are NP-complete to compute.

**Justification**: Paper explicitly uses Crit* for generation (line 292-294).

### 2. Codec uses grammar-based + semantic parsing

Decoder architecture:
- D1: Exact match (fast, perfect for round-trip)
- D2: Template + edit distance (handles variations)
- D3: Lark parser + transformer semantic extraction

**Justification**: Modern best practice (semantic parsing literature 2026).

### 3. Level 3 works backwards from complete theory

Generate Level 3 instances by:
1. Start with D^full containing defeater r*
2. Remove r* to create anomaly
3. Verify r* resolves conservatively

**Justification**: Definition 16 (line 676), Proposition 6 guarantees r* ∈ R*.

### 4. Four structured partition families

Implement all four from Definition 10:
- κ_leaf: Facts defeasible, rules strict
- κ_rule: Rules defeasible, facts strict
- κ_depth(k): Depth-based stratification
- κ_rand(δ): Random with defeasibility ratio δ

**Justification**: Paper studies yield as function of partition (§4.2).

## Dependencies Added

### Core

```toml
lark-parser = "^1.1.9"          # Grammar-based parsing
spacy = "^3.7.0"                # NLP for NL map
transformers = "^4.40.0"        # Semantic decoder (D3)
numpy = "^1.26.0"
scipy = "^1.13.0"
networkx = "^3.3"               # Derivation trees
python-Levenshtein = "^0.25.0"  # Edit distance (D2)
pydantic = "^2.7.0"             # Schema validation
```

### Testing

```toml
hypothesis = "^6.100.0"         # Property-based testing
pytest-benchmark = "^4.0.0"     # Performance regression
```

## Next Steps

### Immediate (This Week)

1. **Review this design** with paper.tex open side-by-side
2. **Validate mathematical mappings** (check each definition)
3. **Set up test infrastructure** (pytest, hypothesis, benchmarks)
4. **Create directory structure** (author/, codec/, reasoning/, etc.)
5. **Begin Week 1**: Implement reasoning/defeasible.py

### Week 1 Deliverables

- [ ] `reasoning/defeasible.py` implemented
- [ ] `reasoning/derivation_tree.py` implemented
- [ ] `reasoning/expectations.py` implemented
- [ ] Tweety example works
- [ ] Theorem 11 complexity verified
- [ ] Tests passing

### First Validation Checkpoint (Week 2)

**Criterion**: Defeasible reasoning engine works correctly.

**Tests**:
- Tweety example reproduces paper
- Complexity O(|R|·|F|) verified empirically
- Proposition 2 verified (definite ⟹ defeasible)
- ProofWriter benchmark comparison passing

**If checkpoint fails**: Re-evaluate approach, consider existing libraries.

## Files Created

1. `IMPLEMENTATION_PLAN.md` (80+ pages, primary spec)
2. `author.py` (mathematical reference, all definitions)
3. `Guidance_Documents/Phase3_Implementation_Plan.md` (structured guide)
4. `PHASE3_DESIGN_SUMMARY.md` (this file)

Updated:
- `Guidance_Documents/API_Design.md`
- `README.md`

## Git Commit

Committed as: `6dfb182`
- Message: "Phase 3 Implementation Plan: Author Algorithm"
- Files: 5 changed, 3162 insertions(+)
- New files: IMPLEMENTATION_PLAN.md, author.py, Phase3_Implementation_Plan.md

## References

### Primary

- **paper/paper.tex**: Source of truth (all mathematics)
- **IMPLEMENTATION_PLAN.md**: Complete technical specification
- **author.py**: Executable mathematical reference

### Secondary

- **Phase3_Implementation_Plan.md**: Structured development guide
- **Guidance_Documents/API_Design.md**: Project overview, history
- **README.md**: Current status

## Contact & Notes

**Author**: Patrick Cooper  
**Project**: BLANC - DeFAb Benchmark Generation  
**Paper**: NeurIPS 2026 Submission  
**Status**: Design phase complete, implementation ready to begin

**Critical Success Factor**: IDP Discovery example (Appendix C, Example 1) must work correctly. This is the headline test that validates the entire Level 3 pipeline.

**Philosophy**: Mathematical rigor above all else. Every function maps to a paper definition. No shortcuts. No approximations.

---

**This design is complete and ready for implementation. Follow IMPLEMENTATION_PLAN.md exactly.**
