# Phase 3: Author Algorithm & Dataset Generation

**Start Date**: 2026-02-11  
**Status**: Design Complete, Implementation Starting  
**Goal**: Implement the complete DeFAb benchmark generation pipeline

## Overview

Phase 3 implements the **author algorithm** - the core mathematical framework for generating defeasible abduction instances as specified in the paper "Defeasible Reasoning as a Framework for Foundation Model Grounding, Novelty, and Belief Revision."

**Key Principle**: Every function maps 1:1 to a numbered Definition or Proposition in `paper/paper.tex`. No approximations. Mathematical exactness is non-negotiable.

## Critical Documents

1. **IMPLEMENTATION_PLAN.md** - Complete technical specification (80+ pages)
2. **author.py** - Mathematical reference implementation (all definitions)
3. **paper/paper.tex** - Source of truth for all mathematics

## Architecture

```
blanc/
├── author/                    # Core MVP
│   ├── conversion.py          # Defs 1-10: Defeasible conversion
│   ├── support.py             # Defs 17-20: Criticality computation
│   ├── generation.py          # Defs 20-21: Level 1-2 instances
│   ├── level3.py              # Defs 11-16: Defeater abduction
│   ├── metrics.py             # Defs 33-35: Novelty, revision distance
│   └── pipeline.py            # End-to-end orchestration
│
├── codec/                     # CRITICAL FAILURE POINT
│   ├── encoder.py             # 4 modalities (M1-M4)
│   ├── decoder.py             # 3 strategies (D1-D3)
│   ├── nl_map.py              # Ontological grounding
│   ├── templates.py           # Rendering templates
│   └── validation.py          # Round-trip testing
│
├── reasoning/
│   ├── defeasible.py          # Def 7: Defeasible derivation
│   ├── derivation_tree.py     # AND-OR derivation trees
│   ├── expectations.py        # Expectation set computation
│   └── team_defeat.py         # Team defeat implementation
│
├── generation/
│   ├── partition.py           # Partition functions
│   ├── distractor.py          # Distractor generation
│   └── language_bias.py       # Candidate space generation
│
└── experiments/
    ├── dataset.py             # Dataset container
    ├── evaluation.py          # Rendering-robust accuracy
    ├── partial_credit.py      # Graded scoring (Level 3)
    └── statistics.py          # Dataset statistics
```

## Implementation Phases

### Phase 3A: Defeasible Reasoning Engine (Weeks 1-2)

**Files**: `reasoning/defeasible.py`, `reasoning/derivation_tree.py`, `reasoning/expectations.py`

**Key Functions**:
- `defeasible_provable(D, q)` - Definition 7, O(|R| · |F|) complexity
- `build_derivation_tree(D, q)` - Definition 13, AND-OR tree
- `expectation_set(D)` - Definition 11, forward chaining

**Tests**:
- Tweety example (paper §1, §4)
- IDP example (Appendix C, Example 1)
- Proposition 2: Definite ⟹ Defeasible
- Theorem 11: Polynomial time complexity

**Validation**: ProofWriter benchmark comparison

### Phase 3B: Conversion & Partition Functions (Week 2)

**Files**: `author/conversion.py`, `generation/partition.py`

**Key Functions**:
- `phi_kappa(pi, kappa)` - Definition 9, defeasible conversion
- `partition_{leaf,rule,depth,random}` - Definition 10, structured partitions
- `defeasibility_ratio(kappa, pi)` - Compute δ(κ)

**Tests**:
- Proposition 1: Conservative conversion (κ ≡ s)
- Proposition 3: Yield monotonicity in δ
- Validate dependency graph computation

### Phase 3C: Support & Criticality (Week 3)

**Files**: `author/support.py`

**Key Functions**:
- `full_theory_criticality(D, q)` - Definition 18, O(|D|² · |F|)
- `redundancy_degree(e, D, q)` - Definition 19

**Tests**:
- Proposition 4: Crit*(D,q) ⊆ Crit(D,q)
- Complexity benchmarks (verify O(|D|² · |F|))
- Random theory testing

### Phase 3D: Instance Generation (Levels 1-2) (Week 4)

**Files**: `author/generation.py`, `generation/distractor.py`

**Key Functions**:
- `generate_level1_instance(D, q, e_fact, k)` - Fact completion
- `generate_level2_instance(D, q, e_rule, k)` - Rule abduction
- `sample_syntactic_distractors(...)` - Three strategies

**Tests**:
- Instance validity properties
- Distractor strategies (random, syntactic, adversarial)
- Gold set verification

### Phase 3E: Level 3 - Defeater Abduction (Weeks 5-6)

**Files**: `author/level3.py`, `author/metrics.py`, `generation/language_bias.py`

**Key Functions**:
- `is_defeasible_anomaly(D, alpha)` - Definition 12
- `anomaly_support(D, alpha)` - Definition 13
- `candidate_defeater_space(L)` - Definition 15
- `is_conservative_resolution(D, alpha, r, gamma)` - Conservativity check
- `revision_distance(D, D_prime)` - Revision distance metric
- `predicate_novelty(r, D)` - Definition 33
- `generate_level3_instance(D_full, r_star, alpha, L)` - Definition 16

**Tests**:
- **IDP Discovery example** (HEADLINE TEST)
- Conservativity ⟺ AGM minimal change
- Proposition 5: Candidate space size
- Proposition 6: Gold set non-empty

### Phase 4A: Rendering Codec (Weeks 7-8) - **CRITICAL**

**Risk Level**: 40% of project risk

**Files**: `codec/encoder.py`, `codec/decoder.py`, `codec/nl_map.py`, `codec/templates.py`, `codec/validation.py`

**Components**:

1. **Encoder (4 modalities)**:
   - M1: Narrative (linguistic hedging)
   - M2: Semi-formal (logical connectives + NL predicates)
   - M3: Annotated formal (symbolic + glosses)
   - M4: Pure formal (raw syntax)

2. **Decoder (3 strategies)**:
   - D1: Exact match (sound, faithful, incomplete)
   - D2: Template extraction (sound, complete, conditionally faithful)
   - D3: Semantic extraction (conditionally sound, complete, approximate)

3. **Ontological Grounding Map**:
   - NL: HB → L* (injective mapping)
   - Compositional via NL_P and NL_C
   - Domain coherent

**Tests**:
- Round-trip consistency (Def 30): D1=100%, D2≥95%, D3≥80%
- Modality ordering (Def 27): Naturalness/faithfulness tradeoff
- Injectivity verification (Def 28)
- Faithfulness testing

**Libraries**:
- `lark-parser`: Grammar-based parsing
- `transformers`: Semantic extraction (D3)
- `Levenshtein`: Edit distance (D2)

### Phase 4B: Evaluation Pipeline (Week 9)

**Files**: `experiments/evaluation.py`, `experiments/partial_credit.py`, `experiments/statistics.py`

**Key Functions**:
- `rendering_robust_accuracy(model, instances)` - Definition 31
- `graded_score_level3(D, alpha, hypothesis, gamma, L)` - §4.5
- `dataset_statistics(dataset)` - §4.3

**Graded Scoring** (Level 3):
- 0.00: Decoder failure or anomaly unresolved
- 0.25: Resolves but violates language bias
- 0.50: Valid weak resolution, non-conservative
- 0.75: Conservative weak OR non-conservative strong
- 1.00: Conservative resolution

## Mathematical Correctness Checklist

### Propositions to Verify

- [ ] Proposition 1: Conservative conversion (κ ≡ s)
- [ ] Proposition 2: Definite ⟹ Defeasible
- [ ] Proposition 3: Yield monotonicity
- [ ] Proposition 4: Criticality inclusion
- [ ] Proposition 5: Candidate space size O(|P⁺|^ar_max · |P⁻|)
- [ ] Proposition 6: Gold set non-empty

### Theorems to Verify

- [ ] Theorem 11: Defeasible derivation in P, O(|R| · |F|)

### Complexity Guarantees

| Operation | Target | Verification |
|-----------|--------|--------------|
| Defeasible derivation | O(\|R\| · \|F\|) | Benchmark scaling |
| Full-theory criticality | O(\|D\|² · \|F\|) | Benchmark scaling |
| Full pipeline | O(\|D\|³) | End-to-end timing |

### Paper Examples to Reproduce

- [ ] Tweety (§1, §4)
- [ ] IDP Discovery (Appendix C, Example 1) - **CRITICAL**
- [ ] Family relations
- [ ] Medical diagnosis

## Risk Management

### High-Risk Components

1. **Codec (40% risk)**
   - Mitigation: Extensive round-trip testing
   - Fallback: Start with M4 (pure formal) only
   - Library choice: Lark parser + transformers

2. **Level 3 Generation (30% risk)**
   - Mitigation: Hand-authored defeaters first
   - Fallback: Focus on Levels 1-2 for MVP
   - Test: IDP example must work

3. **Expectation Set Computation (20% risk)**
   - Mitigation: Limit to small Herbrand bases
   - Fallback: Sample expectations, don't enumerate all
   - Optimization: Memoization/caching

4. **Defeasible Derivation (10% risk)**
   - Mitigation: Test against benchmarks
   - Libraries: Consider DePYsible, silkie
   - Validation: ProofWriter comparison

### Fallback Strategies

**If codec fails**:
- Use M4 (pure formal) only
- Multiple-choice evaluation (no generation)
- Restrict to template-based decoding

**If Level 3 too complex**:
- Focus MVP on Levels 1-2
- Defer defeater abduction to future work
- Use hand-authored Level 3 instances only

**If expectation sets too expensive**:
- Sample random subset of expectations
- Use conservative overapproximation
- Lazy evaluation with caching

## Success Criteria

### Functional Requirements

- [ ] Generate Level 1 instances (fact completion)
- [ ] Generate Level 2 instances (rule abduction)
- [ ] Generate Level 3 instances (defeater abduction)
- [ ] Implement all 4 rendering modalities
- [ ] Implement all 3 decoder strategies
- [ ] Round-trip consistency >95% for D1, D2

### Performance Requirements

- [ ] O(|D|² · |F|) criticality computation
- [ ] O(|R| · |F|) defeasible derivation
- [ ] Generate 1000 instances in <1 hour
- [ ] Expectation set computation tractable

### Testing Requirements

- [ ] >90% code coverage
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All property-based tests pass
- [ ] All paper examples reproduce exactly

### Mathematical Requirements

- [ ] All 6 propositions verified
- [ ] Theorem 11 complexity bound met
- [ ] IDP example works correctly
- [ ] Conservativity check implements AGM

## Dependencies

### New Requirements

```toml
[project.dependencies]
# Parsing & NLP
lark-parser = "^1.1.9"          # Grammar-based parsing
spacy = "^3.7.0"                # NLP for NL map
transformers = "^4.40.0"        # Semantic decoder (D3)

# Scientific computing
numpy = "^1.26.0"
scipy = "^1.13.0"
networkx = "^3.3"               # Derivation trees

# String matching
python-Levenshtein = "^0.25.0"  # Edit distance (D2)

# Data validation
pydantic = "^2.7.0"             # Schema validation
```

### Testing Dependencies

```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "hypothesis>=6.100.0",      # Property-based testing
    "pytest-benchmark>=4.0.0",  # Performance regression
]
```

## Testing Strategy

### Unit Tests

Every mathematical function:
```python
def test_proposition_1_conservative_conversion(): ...
def test_proposition_2_definite_implies_defeasible(): ...
def test_proposition_3_yield_monotonicity(): ...
def test_proposition_4_criticality_inclusion(): ...
def test_proposition_5_candidate_space_size(): ...
def test_proposition_6_gold_nonempty(): ...
def test_theorem_11_polynomial_derivation(): ...
```

Paper examples:
```python
def test_tweety_example(): ...
def test_idp_example(): ...  # CRITICAL
def test_family_relations(): ...
def test_medical_diagnosis(): ...
```

### Integration Tests

End-to-end instance generation:
```python
def test_level1_generation_pipeline(): ...
def test_level2_generation_pipeline(): ...
def test_level3_generation_pipeline(): ...
```

### Property-Based Tests (Hypothesis)

```python
from hypothesis import given, strategies as st

@given(st.from_type(DefeasibleTheory), st.text())
def test_derivation_deterministic(D, q):
    """Defeasible derivation is deterministic."""
    assert defeasible_provable(D, q) == defeasible_provable(D, q)

@given(st.from_type(AbductiveInstance))
def test_instance_validity(instance):
    """All generated instances satisfy correctness properties."""
    # Ablation removes derivability
    assert not defeasible_provable(instance.D_minus, instance.target)
    # Gold restores derivability
    for h in instance.gold:
        D_restored = add_element(instance.D_minus, h)
        assert defeasible_provable(D_restored, instance.target)
```

### Benchmark Tests

Validate against known datasets:
```python
def test_proofwriter_benchmark():
    """Verify our derivations match ProofWriter gold labels."""
    dataset = load_proofwriter()
    for example in dataset:
        D = convert_to_defeasible(example.theory)
        for fact, label in example.questions:
            assert defeasible_provable(D, fact) == label
```

### Performance Regression Tests

```python
@pytest.mark.benchmark
def test_criticality_performance():
    """Ensure O(|D|² · |F|) complexity holds."""
    sizes = [10, 20, 40, 80, 160]
    times = []
    for n in sizes:
        D, q = generate_theory_of_size(n)
        result = pytest.benchmark(full_theory_criticality, D, q)
        times.append(result)
    # Verify quadratic scaling
    assert_quadratic_scaling(sizes, times)
```

## Implementation Schedule

| Week | Phase | Deliverables |
|------|-------|-------------|
| 1-2  | 3A    | Defeasible reasoning engine |
| 2    | 3B    | Conversion & partitions |
| 3    | 3C    | Support & criticality |
| 4    | 3D    | Instance generation (L1-2) |
| 5-6  | 3E    | Level 3 defeater abduction |
| 7-8  | 4A    | Rendering codec |
| 9    | 4B    | Evaluation pipeline |
| 10   | -     | Validation & polish |

## Validation Milestones

### Milestone 1: Defeasible Reasoning Works (Week 2)
- [ ] Tweety example works
- [ ] Theorem 11 complexity verified
- [ ] ProofWriter comparison passing

### Milestone 2: Conversion Works (Week 2)
- [ ] Proposition 1 verified
- [ ] Proposition 3 verified
- [ ] Yield curves plotted

### Milestone 3: Instance Generation Works (Week 4)
- [ ] Level 1 instances generated
- [ ] Level 2 instances generated
- [ ] All instances valid

### Milestone 4: Level 3 Works (Week 6)
- [ ] IDP example works (CRITICAL)
- [ ] Conservativity check correct
- [ ] Proposition 6 verified

### Milestone 5: Codec Works (Week 8)
- [ ] Round-trip >95% for D1, D2
- [ ] All 4 modalities implemented
- [ ] Injectivity verified

### Milestone 6: MVP Complete (Week 10)
- [ ] All propositions verified
- [ ] All examples reproduce
- [ ] Generate 1000 instances successfully
- [ ] Tests >90% coverage

## Next Steps

1. **Review this plan** with paper.tex open
2. **Validate mathematical mappings** (Defs → code)
3. **Set up test infrastructure** (pytest, hypothesis, benchmarks)
4. **Begin Week 1**: Defeasible reasoning engine
5. **Daily check-ins**: Compare generated instances with paper examples

## References

- **Paper**: `paper/paper.tex` (source of truth)
- **Plan**: `IMPLEMENTATION_PLAN.md` (80+ pages, complete spec)
- **Reference**: `author.py` (all definitions in code)
- **Status**: `Guidance_Documents/API_Design.md` (project status)

---

**This is the blueprint. Follow it exactly. Every deviation risks mathematical incorrectness.**

**Author**: Patrick Cooper  
**Date**: 2026-02-11
