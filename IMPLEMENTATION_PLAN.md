# BLANC MVP Implementation Plan: Author Algorithm & Experimental Framework

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Status**: Design Phase  
**Target**: DeFAb Benchmark Generation (NeurIPS 2026 Submission)

## Executive Summary

This document specifies the precise implementation of the **author algorithm**: the complete pipeline for generating defeasible abduction instances as described in "Defeasible Reasoning as a Framework for Foundation Model Grounding, Novelty, and Belief Revision."

**Core Principle**: Every function maps 1:1 to a numbered Definition or Proposition in `paper/paper.tex`. No shortcuts. No approximations. Mathematical exactness is non-negotiable.

**Critical Components**:
1. **Defeasible conversion** (§3.2, Defs 8-10)
2. **Support & criticality computation** (§3.3, Defs 17-20)  
3. **Instance generation** (§3.3-3.4, Defs 21-22, 16)
4. **Rendering codec** (§3.5, Defs 23-30) - **HIGHEST RISK**
5. **Evaluation pipeline** (§4, Defs 31-32)

## 1. Mathematical Foundation

### 1.1 Core Definitions (paper.tex §A)

```
Signature (Def 1)           →  author/conversion.py::Signature
Definite LP (Def 2)         →  author/conversion.py::DefiniteLogicProgram
Immediate Conseq (Def 3)    →  author/conversion.py::immediate_consequence()
Least Herbrand Model (Def 4) → author/conversion.py::least_herbrand_model()
SLD Derivability (Def 5)    →  backends/prolog.py (existing)

Defeasible Theory (Def 6)   →  core/theory.py::Theory (extend)
Defeasible Derivation (Def 7) → reasoning/defeasible.py::defeasible_provable()

Partition Function (Def 8)  →  generation/partition.py::PartitionFunction
Defeasible Conversion (Def 9) → author/conversion.py::phi_kappa()
Structured Partitions (Def 10) → generation/partition.py::{leaf, rule, depth, random}

Expectation Set (Def 11)    →  reasoning/expectations.py::expectation_set()
Anomaly (Def 12)            →  author/level3.py::is_defeasible_anomaly()
Anomaly Support (Def 13)    →  reasoning/derivation_tree.py::anomaly_support()
Language Bias (Def 14)      →  generation/language_bias.py::LanguageBias
Candidate Spaces (Def 15)   →  generation/language_bias.py::candidate_defeater_space()
Defeater Abduction (Def 16) →  author/level3.py::generate_level3_instance()

Support Set (Def 17)        →  author/support.py::support_sets() [NP-complete]
Full-Theory Critical (Def 18) → author/support.py::full_theory_criticality() [O(|D|²·|F|)]
Redundancy Degree (Def 19)  →  author/support.py::redundancy_degree()
Abductive Instance (Def 20) →  author/generation.py::AbductiveInstance
Complexity Strat (Def 21)   →  author/generation.py::{level1, level2, level3}
Yield (Def 22)              →  author/metrics.py::defeasible_yield()

Rendering Codec (Def 23)    →  codec/encoder.py, codec/decoder.py
Faithfulness (Def 24)       →  codec/validation.py::check_faithfulness()
Naturalness (Def 25)        →  codec/validation.py::compute_naturalness()
Modalities (Def 26)         →  codec/encoder.py::{M1, M2, M3, M4}
Modality Ordering (Def 27)  →  codec/validation.py::validate_modality_ordering()
NL Map (Def 28)             →  codec/nl_map.py::OntologicalGroundingMap
Decoder Strat (Def 29)      →  codec/decoder.py::{D1_exact, D2_template, D3_semantic}
Round-Trip (Def 30)         →  codec/validation.py::round_trip_test()

Robust Accuracy (Def 31)    →  experiments/evaluation.py::rendering_robust_accuracy()
Empirical Difficulty (Def 32) → experiments/evaluation.py::empirical_difficulty()

Predicate Novelty (Def 33)  →  author/metrics.py::predicate_novelty()
Revision Distance (Def 34)  →  author/metrics.py::revision_distance()
Structural Difficulty (Def 35) → author/metrics.py::structural_difficulty()
```

### 1.2 Complexity Guarantees

| Operation | Complexity | Implementation |
|-----------|------------|----------------|
| Defeasible derivation D ⊢∂ q | O(\|R\| · \|F\|) | reasoning/defeasible.py |
| Full-theory criticality Crit*(D,q) | O(\|D\|² · \|F\|) | author/support.py |
| Full pipeline per instance | O(\|D\|³) | author/pipeline.py |
| Minimum support set | NP-complete | Not used in generation |
| Weak DAP resolution | NP-complete | Level 3 validation only |
| Strong DAP resolution | Σ₂ᴾ-complete | Level 3 validation only |

**Design Decision**: Use Crit* (polynomial) for generation, not minimal support (NP-hard).

## 2. Project Architecture

### 2.1 Directory Structure

```
blanc/
├── author/                    # NEW - Core MVP (maps to §3 of paper)
│   ├── __init__.py
│   ├── conversion.py          # Defs 1-10: Signatures, Conversion, Partitions
│   ├── support.py             # Defs 17-20: Support sets, Criticality
│   ├── generation.py          # Defs 20-21: Level 1-2 Instance Generation
│   ├── level3.py              # Defs 11-16: Defeater Abduction
│   ├── metrics.py             # Defs 33-35: Novelty, Revision Distance
│   └── pipeline.py            # End-to-end orchestration
│
├── codec/                     # NEW - CRITICAL FAILURE POINT
│   ├── __init__.py
│   ├── encoder.py             # Defs 23-28: M1-M4 modalities
│   ├── decoder.py             # Def 29: D1-D3 strategies
│   ├── nl_map.py              # Def 28: NL: HB → L*
│   ├── templates.py           # Appendix B: Encoder templates
│   └── validation.py          # Defs 24-25, 30: Faithfulness, Round-trip
│
├── reasoning/                 # EXTEND - Phase 3
│   ├── __init__.py
│   ├── defeasible.py          # Def 7: Defeasible derivation
│   ├── derivation_tree.py     # Def 13: AND-OR derivation trees
│   ├── expectations.py        # Def 11: Expectation set computation
│   └── team_defeat.py         # Def 7(2c): Team defeat implementation
│
├── generation/                # EXTEND - Phase 3
│   ├── __init__.py
│   ├── partition.py           # Defs 8-10: Partition functions
│   ├── distractor.py          # §4.2: Syntactic distractors
│   └── language_bias.py       # Def 14-15: Language bias, candidate spaces
│
├── experiments/               # NEW - Phase 4
│   ├── __init__.py
│   ├── dataset.py             # Dataset container (DeFAb)
│   ├── evaluation.py          # Defs 31-32: Evaluation protocol
│   ├── partial_credit.py      # §4.5: Graded scoring function
│   └── statistics.py          # §4.3: Dataset statistics
│
└── tests/
    ├── author/                # NEW - Comprehensive test suite
    │   ├── test_conversion.py
    │   ├── test_support.py
    │   ├── test_generation.py
    │   └── test_level3.py
    ├── codec/                 # NEW - Critical codec tests
    │   ├── test_encoder.py
    │   ├── test_decoder.py
    │   ├── test_round_trip.py
    │   └── test_modalities.py
    └── reasoning/
        ├── test_defeasible.py
        └── test_expectations.py
```

### 2.2 Dependencies

**Core Logic Engines** (existing):
- `pyswip>=0.2.10` - SWI-Prolog interface
- `clingo>=5.8.0` - ASP solver
- `clorm>=1.5.0` - Clingo ORM

**New Requirements**:
```toml
[project.dependencies]
# Parsing & NLP
lark-parser = "^1.1.9"          # Grammar-based parsing for logic syntax
spacy = "^3.7.0"                # NLP for NL map construction
transformers = "^4.40.0"        # For semantic decoder (D3)

# Scientific computing
numpy = "^1.26.0"
scipy = "^1.13.0"
networkx = "^3.3"               # Derivation tree visualization

# Data validation
pydantic = "^2.7.0"             # Schema validation for instances
```

**Testing**:
```toml
[project.optional-dependencies]
test = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "hypothesis>=6.100.0",      # Property-based testing
    "pytest-benchmark>=4.0.0",  # Performance regression tests
]
```

## 3. Implementation Phases

### Phase 3A: Defeasible Reasoning Engine (Week 1-2)

**Goal**: Implement Def 7 (defeasible derivation) with polynomial time guarantee.

**Files**:
- `reasoning/defeasible.py`
- `reasoning/derivation_tree.py`
- `reasoning/expectations.py`

**Key Functions**:
```python
def defeasible_provable(D: DefeasibleTheory, q: str) -> bool:
    """
    Definition 7: D ⊢∂ q via tagged proof procedure.
    
    Complexity: O(|R| · |F|) per Theorem 11.
    
    Implements:
    - +Δq: definite provability (facts + strict rules)
    - +∂q: defeasible provability with team defeat
    
    Returns: True iff q is defeasibly provable from D.
    """
    pass

def build_derivation_tree(D: DefeasibleTheory, q: str) -> DerivationTree:
    """
    Definition 13: Construct AND-OR tree T(D, q) of proof of +∂q.
    
    Used for:
    - Anomaly support computation (Def 13)
    - Provenance tracking
    - Visualization
    """
    pass

def expectation_set(D: DefeasibleTheory) -> Set[str]:
    """
    Definition 11: Exp(D) = {q | D ⊢∂ q}.
    
    Implementation: Forward chaining to fixpoint over Herbrand base.
    For function-free theories: polynomial in |HB|.
    """
    pass
```

**Tests**:
```python
# Test against paper examples
def test_tweety_example():
    """Tweety example from paper (§1, §4)."""
    D = DefeasibleTheory(
        F={'bird(tweety)'},
        Rs=set(),
        Rd={
            Rule('flies(X)', ('bird(X)',), RuleType.DEFEASIBLE, label='r1'),
            Rule('~flies(X)', ('penguin(X)',), RuleType.DEFEASIBLE, label='r2')
        },
        Rdf=set(),
        superiority={}
    )
    
    assert defeasible_provable(D, 'bird(tweety)')
    assert defeasible_provable(D, 'flies(tweety)')
    
    # Add penguin fact
    D.F.add('penguin(tweety)')
    # Now team defeat blocks r1
    assert not defeasible_provable(D, 'flies(tweety)')

def test_idp_example():
    """IDP example from paper (Appendix C, Example 1)."""
    # Implementation of full IDP discovery scenario
    pass

# Property-based tests
@given(random_defeasible_theory())
def test_definite_implies_defeasible(D, q):
    """Proposition 2: If D ⊢Δ q then D ⊢∂ q."""
    if strictly_provable(D, q):
        assert defeasible_provable(D, q)

@given(random_defeasible_theory())
def test_complexity_bound(D, q):
    """Verify O(|R| · |F|) complexity."""
    start = time.perf_counter()
    defeasible_provable(D, q)
    elapsed = time.perf_counter() - start
    
    predicted = (len(D.Rs) + len(D.Rd)) * len(D.F) * CONSTANT
    assert elapsed < predicted
```

**Validation**: ProofWriter benchmark (existing KB, compare with our derivations).

### Phase 3B: Conversion & Partition Functions (Week 2)

**Goal**: Implement Defs 8-10 (partition functions, conversion).

**Files**:
- `author/conversion.py`
- `generation/partition.py`

**Key Functions**:
```python
def phi_kappa(pi: DefiniteLogicProgram, kappa: PartitionFunction) -> DefeasibleTheory:
    """
    Definition 9: Defeasible conversion φ_κ(Π).
    
    Correctness: Proposition 1 (when κ ≡ s, conversion is conservative).
    """
    pass

# Four structured partition families (Def 10)
def partition_leaf(rule: Rule) -> str: ...
def partition_rule(rule: Rule) -> str: ...
def partition_depth(k: int) -> PartitionFunction: ...
def partition_random(delta: float) -> PartitionFunction: ...
```

**Tests**:
```python
def test_proposition1_conservativity():
    """Proposition 1: κ ≡ s ⟹ M_Π = {q | D_κ ⊢Δ q}."""
    pi = load_example_lp('family.pl')
    kappa_strict = lambda r: 's'
    
    D = phi_kappa(pi, kappa_strict)
    M_pi = pi.least_herbrand_model()
    
    for q in M_pi:
        assert strictly_provable(D, q)
    
    # Converse
    exp_D = {q for q in expectation_set(D) if strictly_provable(D, q)}
    assert exp_D == M_pi

def test_proposition3_yield_monotonicity():
    """Proposition 3: E[Y(κ_rand(δ), Q)] non-decreasing in δ."""
    pi = load_example_lp('medical.pl')
    Q = {q for q in pi.least_herbrand_model() if depth(q) >= 2}
    
    deltas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    yields = []
    
    for delta in deltas:
        # Average over 100 random partitions
        avg_yield = np.mean([
            defeasible_yield(partition_random(delta, seed=i), Q, pi)
            for i in range(100)
        ])
        yields.append(avg_yield)
    
    # Check monotonicity
    assert all(y2 >= y1 for y1, y2 in zip(yields, yields[1:]))
```

### Phase 3C: Support & Criticality (Week 3)

**Goal**: Implement Defs 17-20 (support sets, criticality).

**Files**:
- `author/support.py`

**Key Functions**:
```python
def full_theory_criticality(D: DefeasibleTheory, q: str) -> Set[Element]:
    """
    Definition 18: Crit*(D, q) = {e ∈ F ∪ Rs ∪ Rd | D \ {e} ⊬∂ q}.
    
    Complexity: O(|D|² · |F|) - iterate over elements, test derivability.
    
    This is the WORKHORSE for instance generation.
    Use this, NOT minimal support (which is NP-complete).
    """
    critical = set()
    
    all_elements = list(D.F) + list(D.Rs) + list(D.Rd)
    
    for e in all_elements:
        D_minus = remove_element(D, e)
        if not defeasible_provable(D_minus, q):
            critical.add(e)
    
    return critical

def redundancy_degree(e: Element, D: DefeasibleTheory, q: str) -> int:
    """
    Definition 19: red(e, D, q) = |{S ∈ Supp(D,q) | e ∉ S}|.
    
    If red(e, D, q) = 0, then e ∈ Crit*(D, q).
    """
    pass
```

**Tests**:
```python
def test_proposition4_criticality_inclusion():
    """Proposition 4: Crit*(D, q) ⊆ Crit(D, q)."""
    # Generate random theory
    D, q = random_theory_with_derivable_conclusion()
    
    crit_star = full_theory_criticality(D, q)
    support_sets = compute_all_support_sets(D, q)  # Expensive!
    
    crit = {e for S in support_sets for e in S}
    
    assert crit_star.issubset(crit)

@pytest.mark.benchmark
def test_criticality_complexity():
    """Verify O(|D|² · |F|) complexity empirically."""
    sizes = [10, 20, 40, 80, 160]
    times = []
    
    for n in sizes:
        D, q = generate_theory_of_size(n)
        
        start = time.perf_counter()
        full_theory_criticality(D, q)
        elapsed = time.perf_counter() - start
        
        times.append(elapsed)
    
    # Fit quadratic model
    coeffs = np.polyfit(sizes, times, deg=2)
    # Verify quadratic term dominates
    assert coeffs[0] > 0
```

### Phase 3D: Instance Generation (Week 4)

**Goal**: Implement Defs 20-22 (Levels 1-2 generation).

**Files**:
- `author/generation.py`
- `generation/distractor.py`

**Key Functions**:
```python
@dataclass
class AbductiveInstance:
    """Definition 20: Complete instance specification."""
    D_minus: DefeasibleTheory
    target: str
    candidates: Set[Element]
    gold: Set[Element]
    level: int
    metadata: dict

def generate_level1_instance(
    D: DefeasibleTheory,
    q: str,
    e_fact: str,
    k: int = 5
) -> AbductiveInstance:
    """Level 1: Fact completion (e ∈ F)."""
    assert e_fact in full_theory_criticality(D, q)
    
    D_minus = DefeasibleTheory(
        F=D.F - {e_fact},
        Rs=D.Rs,
        Rd=D.Rd,
        Rdf=D.Rdf,
        superiority=D.superiority
    )
    
    # §4.2: Three distractor strategies
    distractors = sample_syntactic_distractors(e_fact, D, k, strategy='syntactic')
    
    return AbductiveInstance(
        D_minus=D_minus,
        target=q,
        candidates=distractors | {e_fact},
        gold={e_fact},
        level=1,
        metadata={'ablated': e_fact}
    )

def generate_level2_instance(
    D: DefeasibleTheory,
    q: str,
    e_rule: Rule,
    k: int = 5
) -> AbductiveInstance:
    """Level 2: Rule abduction (e ∈ Rd)."""
    # Similar structure to Level 1
    pass
```

**Distractor Strategies** (§4.2):
```python
def sample_syntactic_distractors(
    target: Element,
    D: DefeasibleTheory,
    k: int,
    strategy: str  # 'random' | 'syntactic' | 'adversarial'
) -> Set[Element]:
    """
    §4.2: Three distractor regimes.
    
    - random: uniform sample from appropriate component
    - syntactic: share predicate symbols with target
    - adversarial: satisfy strict subset of derivability conditions
    """
    if strategy == 'syntactic':
        # For facts: share predicate
        if isinstance(target, str):  # fact
            pred = extract_predicate(target)
            candidates = {f for f in D.F if extract_predicate(f) == pred}
            return random.sample(candidates - {target}, min(k, len(candidates)-1))
        
        # For rules: substitute predicates or permute arguments
        elif isinstance(target, Rule):
            candidates = generate_rule_variants(target, D)
            return random.sample(candidates, min(k, len(candidates)))
    
    elif strategy == 'adversarial':
        # §4.2: Ablate proper subset of antecedents
        # Requires verification that distractor does NOT restore derivability
        pass
```

**Tests**:
```python
def test_instance_validity():
    """Every generated instance must satisfy correctness properties."""
    D, q = load_example_theory('tweety')
    e = choose_critical_element(D, q)
    
    instance = generate_level1_instance(D, q, e, k=5)
    
    # 1. Ablation removes derivability
    assert not defeasible_provable(instance.D_minus, q)
    
    # 2. Gold element restores derivability
    for h in instance.gold:
        D_restored = add_element(instance.D_minus, h)
        assert defeasible_provable(D_restored, q)
    
    # 3. Distractors do NOT restore derivability
    for d in (instance.candidates - instance.gold):
        D_with_distractor = add_element(instance.D_minus, d)
        assert not defeasible_provable(D_with_distractor, q)
    
    # 4. Gold set is minimal
    for h in instance.gold:
        # No strict subset of h restores derivability
        pass

def test_distractor_strategies():
    """§4.2: Compare three distractor regimes."""
    D, q = load_example_theory('medical')
    e = choose_critical_element(D, q)
    
    for strategy in ['random', 'syntactic', 'adversarial']:
        distractors = sample_syntactic_distractors(e, D, k=10, strategy=strategy)
        
        # All must be invalid
        for d in distractors:
            D_test = add_element(remove_element(D, e), d)
            assert not defeasible_provable(D_test, q)
```

### Phase 3E: Level 3 - Defeater Abduction (Week 5-6)

**Goal**: Implement Defs 11-16 (anomaly resolution, conservative revision).

**Files**:
- `author/level3.py`
- `author/metrics.py`
- `generation/language_bias.py`

**Key Functions**:
```python
def is_defeasible_anomaly(D: DefeasibleTheory, alpha: str) -> bool:
    """
    Definition 12: α is defeasible anomaly iff:
    - D ⊢∂ ¬α (predicted)
    - D ⊬Δ ¬α (not strictly provable, can be blocked)
    """
    return (
        defeasible_provable(D, f"~{alpha}") and
        not strictly_provable(D, f"~{alpha}")
    )

def anomaly_support(D: DefeasibleTheory, alpha: str) -> Set[Rule]:
    """
    Definition 13: AnSup(D, α) = {r ∈ Rd | r appears in T(D, ¬α)}.
    
    Extracts defeasible rules from derivation tree of ¬α.
    These are the rules that must be defeated or overridden.
    """
    tree = build_derivation_tree(D, f"~{alpha}")
    return {node.rule for node in tree.nodes if node.rule in D.Rd}

@dataclass
class LanguageBias:
    """Definition 14: L = (P⁺, P⁻, ar_max, d_max)."""
    antecedent_predicates: Set[str]
    consequent_predicates: Set[str]
    max_antecedent_length: int
    max_nesting_depth: int

def candidate_defeater_space(L: LanguageBias) -> Set[Rule]:
    """
    Definition 15: R_df(L) = {r: b1,...,bm ↝ ¬h | constraints}.
    
    Generates all defeaters satisfying language bias.
    
    WARNING: Exponential in ar_max.
    Proposition 5: |R_df(L)| = O(|P⁺|^ar_max · |P⁻|).
    
    In practice: enumerate lazily or restrict to small L.
    """
    defeaters = set()
    
    # Generate all valid defeater rules
    for consequent_pred in L.consequent_predicates:
        for m in range(1, L.max_antecedent_length + 1):
            for antecedent_combo in itertools.combinations_with_replacement(
                L.antecedent_predicates, m
            ):
                # Build rule: b1, ..., bm ↝ ¬consequent_pred(...)
                r = construct_defeater(antecedent_combo, consequent_pred, L)
                if satisfies_safety(r):  # vars(head) ⊆ vars(body)
                    defeaters.add(r)
    
    return defeaters

def is_conservative_resolution(
    D: DefeasibleTheory,
    alpha: str,
    r: Rule,
    gamma: Dict[str, Set[str]]  # superiority assertions
) -> bool:
    """
    Conservativity check (§3.4, Remark 2):
    
    Resolution is conservative iff:
    Exp(D ∪ {r} ∪ Γ ∪ {α}) ⊇ Exp(D) \ {¬α}
    
    This is the operationalization of AGM minimal change.
    Tractable because each expectation check is polynomial (Theorem 11).
    """
    D_prime = DefeasibleTheory(
        F=D.F | {alpha},
        Rs=D.Rs,
        Rd=D.Rd | {r},
        Rdf=D.Rdf,
        superiority=merge_superiority(D.superiority, gamma)
    )
    
    original_exp = expectation_set(D)
    revised_exp = expectation_set(D_prime)
    
    # Check: all expectations preserved except ¬α
    for q in original_exp:
        if q == f"~{alpha}":
            continue
        if q not in revised_exp:
            return False  # Non-conservative: lost expectation q
    
    return True

def revision_distance(D: DefeasibleTheory, D_prime: DefeasibleTheory) -> int:
    """
    Revision distance (§3.4, Remark 3):
    
    d_rev(D, D') = |Δ| + |Exp(D) \ Exp(D')|
    
    Conservative resolutions achieve d_rev = |Δ| (no expectation loss).
    """
    # Structural delta
    delta_F = len(D_prime.F - D.F)
    delta_Rs = len(D_prime.Rs - D.Rs)
    delta_Rd = len(D_prime.Rd - D.Rd)
    delta_Rdf = len(D_prime.Rdf - D.Rdf)
    structural_delta = delta_F + delta_Rs + delta_Rd + delta_Rdf
    
    # Expectation loss
    lost = expectation_set(D) - expectation_set(D_prime)
    
    return structural_delta + len(lost)

def predicate_novelty(r: Rule, D: DefeasibleTheory) -> float:
    """
    Definition 33: Nov(r, D) = |pred(r) \ pred(D)| / |pred(r)|.
    
    Fraction of predicates in r that are novel (absent from D).
    Nov = 0: no novelty (all predicates known)
    Nov = 1: maximal novelty (all predicates new)
    """
    preds_r = extract_predicates(r)
    preds_D = extract_all_predicates(D)
    
    novel = preds_r - preds_D
    
    return len(novel) / len(preds_r) if preds_r else 0.0

def generate_level3_instance(
    D_full: DefeasibleTheory,
    r_star: Rule,  # defeater or exception to remove
    alpha: str,     # observation that will become anomalous
    L: LanguageBias
) -> AbductiveInstance:
    """
    Definition 16: Level 3 instance generation.
    
    Working BACKWARDS from complete theory D^full:
    1. Select r* ∈ Rdf or exception rule
    2. Find α: D^full ⊢∂ α and D^full \ {r*} ⊢∂ ¬α
    3. Form D^- by removing r* and its superiority assertions
    4. Verify α is defeasible anomaly in D^-
    5. Compute gold set R* of conservative resolutions
    
    Proposition 6: r* ∈ R* (gold set non-empty).
    """
    # Remove r* and superiority
    D_minus = DefeasibleTheory(
        F=D_full.F,
        Rs=D_full.Rs,
        Rd=D_full.Rd - {r_star} if r_star in D_full.Rd else D_full.Rd,
        Rdf=D_full.Rdf - {r_star} if r_star in D_full.Rdf else D_full.Rdf,
        superiority={
            sup: inf for sup, inf in D_full.superiority.items()
            if r_star.label not in {sup} | inf
        }
    )
    
    # Verify α is now anomalous
    assert is_defeasible_anomaly(D_minus, alpha), (
        f"α={alpha} must be defeasible anomaly after removing r*={r_star}"
    )
    
    # Compute gold set
    # In practice: r* is guaranteed gold (Proposition 6)
    # Could enumerate candidate_defeater_space(L) to find other valid resolutions
    gold = compute_conservative_resolutions(D_minus, alpha, L)
    
    assert r_star in gold, "Proposition 6: r* must be in gold set"
    
    # Compute metadata
    metadata = {
        'ablated_defeater': r_star,
        'anomaly': alpha,
        'language_bias': L,
        'novelty': predicate_novelty(r_star, D_minus),
        'revision_distance': revision_distance(D_minus, D_full),
        'conservative': is_conservative_resolution(
            D_minus, alpha, r_star,
            extract_superiority_for_rule(D_full.superiority, r_star)
        )
    }
    
    return AbductiveInstance(
        D_minus=D_minus,
        target=alpha,
        candidates=gold,  # Could expand with candidates from language bias
        gold=gold,
        level=3,
        metadata=metadata
    )

def compute_conservative_resolutions(
    D: DefeasibleTheory,
    alpha: str,
    L: LanguageBias
) -> Set[Rule]:
    """
    Compute all conservative resolutions for anomaly α.
    
    Algorithm:
    1. Generate candidate space R_df(L) ∪ R_d^exc(L)
    2. For each candidate r (with optional superiority Γ):
       - Test if D ∪ {r} ∪ Γ ∪ {α} ⊬∂ ¬α (resolves anomaly)
       - Test if resolution is conservative
    3. Return all valid conservative resolutions
    
    Complexity: Exponential in |L| due to candidate space size.
    Tractable for small language bias (ar_max ≤ 3, |P⁺| ≤ 20).
    """
    resolutions = set()
    
    # Generate candidates
    candidates = (
        candidate_defeater_space(L) |
        candidate_exception_space(L)
    )
    
    for r in candidates:
        # Test with no superiority first
        if test_resolution(D, alpha, r, {}):
            if is_conservative_resolution(D, alpha, r, {}):
                resolutions.add(r)
        
        # Test with superiority assertions
        # (only if r is defeasible rule, not defeater)
        if r.rule_type == RuleType.DEFEASIBLE:
            for gamma in generate_superiority_candidates(r, D):
                if test_resolution(D, alpha, r, gamma):
                    if is_conservative_resolution(D, alpha, r, gamma):
                        resolutions.add((r, gamma))
    
    return resolutions
```

**Tests**:
```python
def test_idp_discovery_example():
    """
    Full IDP discovery scenario (Appendix C, Example 1).
    
    This is the HEADLINE test - if this works, Level 3 is correct.
    """
    # Build D_bio from paper (lines 918-925)
    D_bio = DefeasibleTheory(
        F={'protein(p53_idr)', 'functional(p53_idr)', 'disordered(p53_idr)'},
        Rs=set(),
        Rd={
            Rule('has_stable_3d(X)', ('protein(X)',), RuleType.DEFEASIBLE, label='r1'),
            Rule('func_mech(X,lock_key)', ('protein(X)', 'has_stable_3d(X)'),
                 RuleType.DEFEASIBLE, label='r2')
        },
        Rdf=set(),
        superiority={}
    )
    
    # Extend to D_full with IDP exception (lines 927-932)
    r3 = Rule('~has_stable_3d(X)', ('disordered(X)',), RuleType.DEFEASIBLE, label='r3')
    r4 = Rule('func_mech(X,conf_ensemble)', ('disordered(X)', 'protein(X)'),
              RuleType.DEFEASIBLE, label='r4')
    
    D_full = DefeasibleTheory(
        F=D_bio.F,
        Rs=D_bio.Rs,
        Rd=D_bio.Rd | {r3, r4},
        Rdf=D_bio.Rdf,
        superiority={'r3': {'r1'}, 'r4': {'r2'}}
    )
    
    # Generate Level 3 instance
    alpha = 'func_mech(p53_idr, conf_ensemble)'
    L = LanguageBias(
        antecedent_predicates={'protein', 'disordered', 'functional'},
        consequent_predicates={'func_mech'},
        max_antecedent_length=2,
        max_nesting_depth=1
    )
    
    instance = generate_level3_instance(D_full, r4, alpha, L)
    
    # Verify properties
    assert instance.level == 3
    assert r4 in instance.gold  # Proposition 6
    
    # Verify anomaly
    assert is_defeasible_anomaly(instance.D_minus, alpha)
    
    # Verify conservativity
    assert is_conservative_resolution(
        instance.D_minus, alpha, r4, {'r4': {'r2'}}
    )
    
    # Verify novelty
    nov = instance.metadata['novelty']
    assert nov == 1/4  # 'conf_ensemble' is novel predicate

def test_conservativity_agm_correspondence():
    """
    Verify conservativity corresponds to AGM minimal change.
    
    Remark 2 (lines 672-674): Conservative resolutions preserve all
    expectations except the targeted anomaly.
    """
    D, alpha, r = create_test_scenario()
    
    original_exp = expectation_set(D)
    
    # Non-conservative resolution: loses unrelated expectations
    r_bad = create_non_conservative_resolution()
    D_bad = add_resolution(D, alpha, r_bad, {})
    bad_exp = expectation_set(D_bad)
    
    # Should lose more than just ¬α
    assert len(original_exp - bad_exp) > 1
    assert not is_conservative_resolution(D, alpha, r_bad, {})
    
    # Conservative resolution: loses only ¬α
    r_good = create_conservative_resolution()
    D_good = add_resolution(D, alpha, r_good, {})
    good_exp = expectation_set(D_good)
    
    # Should lose exactly ¬α
    lost = original_exp - good_exp
    assert lost == {f"~{alpha}"}
    assert is_conservative_resolution(D, alpha, r_good, {})

@pytest.mark.parametrize("ar_max,expected_size", [
    (1, "O(|P⁺| · |P⁻|)"),
    (2, "O(|P⁺|² · |P⁻|)"),
    (3, "O(|P⁺|³ · |P⁻|)"),
])
def test_candidate_space_size(ar_max, expected_size):
    """
    Proposition 5: |R_df(L)| = O(|P⁺|^ar_max · |P⁻|).
    
    Verify exponential growth in ar_max.
    """
    L = LanguageBias(
        antecedent_predicates={'p1', 'p2', 'p3', 'p4', 'p5'},  # |P⁺| = 5
        consequent_predicates={'q1', 'q2'},  # |P⁻| = 2
        max_antecedent_length=ar_max,
        max_nesting_depth=1
    )
    
    candidates = candidate_defeater_space(L)
    
    # Verify size matches theoretical bound
    expected = 5**ar_max * 2
    assert len(candidates) <= expected * 2  # Allow some slack for safety constraints
```

### Phase 4A: Rendering Codec (Week 7-8) - **CRITICAL**

**This is the HIGHEST RISK component.** The codec is where most failures will occur.

**Goal**: Implement Defs 23-30 (encoder, decoder, round-trip).

**Files**:
- `codec/encoder.py`
- `codec/decoder.py`
- `codec/nl_map.py`
- `codec/templates.py`
- `codec/validation.py`

**Architecture Decision**: Use **grammar-based parsing** (Lark) + **semantic extraction** (transformer-based).

**Encoder: Four Modalities** (Appendix B, lines 867-883):

```python
from enum import Enum
from typing import Protocol

class Modality(Enum):
    """Definition 26: Four rendering modalities."""
    NARRATIVE = "M1"      # Linguistic hedging
    SEMI_FORMAL = "M2"    # Logical connectives + NL predicates
    ANNOTATED = "M3"      # Symbolic + glosses
    PURE_FORMAL = "M4"    # Raw syntax

class Encoder(Protocol):
    """Definition 23: ρ_enc: (D, q, H_cand) → token sequence."""
    
    def encode(
        self,
        instance: AbductiveInstance,
        modality: Modality
    ) -> str:
        """Render instance as natural language prompt."""
        ...

class NarrativeEncoder:
    """
    M1: Narrative rendering (Appendix B, lines 871-874).
    
    Templates:
    - Strict: "It is always the case that if ... then ..."
    - Defeasible: "Typically, if ... then ..."
    - Defeater: "The fact that ... may cast doubt on ..."
    - Superiority: "The principle in [r] takes precedence over [s]"
    """
    
    def __init__(self, nl_map: OntologicalGroundingMap):
        self.nl_map = nl_map
    
    def encode_rule(self, rule: Rule) -> str:
        """Encode single rule to narrative text."""
        if rule.is_fact:
            return self.nl_map(rule.head)
        
        # Convert body literals
        body_nl = [self.nl_map(lit) for lit in rule.body]
        body_str = " and ".join(body_nl)
        
        # Convert head
        head_nl = self.nl_map(rule.head)
        
        # Template selection based on rule type
        if rule.rule_type == RuleType.STRICT:
            return f"It is always the case that if {body_str}, then {head_nl}."
        elif rule.rule_type == RuleType.DEFEASIBLE:
            return f"Typically, if {body_str}, then {head_nl}."
        elif rule.rule_type == RuleType.DEFEATER:
            return f"The fact that {body_str} may cast doubt on whether {head_nl}."
    
    def encode(self, instance: AbductiveInstance, modality: Modality) -> str:
        """Encode full instance."""
        assert modality == Modality.NARRATIVE
        
        # Encode theory
        theory_text = "\n".join([
            self.encode_rule(Rule(head=f, body=(), rule_type=RuleType.FACT))
            for f in instance.D_minus.F
        ] + [
            self.encode_rule(r)
            for r in instance.D_minus.Rs | instance.D_minus.Rd
        ])
        
        # Encode task
        target_nl = self.nl_map(instance.target)
        
        # Construct prompt
        if instance.level == 1:
            prompt = f"""{theory_text}

Given the above knowledge, we would expect: {target_nl}.

However, this conclusion cannot be derived from the current facts. What observation is missing?

Candidates:
{self._format_candidates(instance.candidates)}

Answer:"""
        
        elif instance.level == 2:
            prompt = f"""{theory_text}

Given the above knowledge, we would expect: {target_nl}.

However, this conclusion cannot be derived from the current rules. What generalization is missing?

Candidates:
{self._format_candidates(instance.candidates)}

Answer:"""
        
        elif instance.level == 3:
            anomaly = instance.metadata['anomaly']
            anomaly_nl = self.nl_map(anomaly)
            
            prompt = f"""{theory_text}

Based on this knowledge, we would predict: {self.nl_map(f"~{anomaly}")}.

However, we observe: {anomaly_nl}.

What principle or exception would explain this observation while preserving other expectations?

Answer:"""
        
        return prompt

class SemiFormalEncoder:
    """
    M2: Semi-formal rendering (Appendix B, line 877).
    
    Example: "bird(X) ∧ ¬penguin(X) ⇒ flies(X) [defeasible]"
    """
    pass

class AnnotatedFormalEncoder:
    """
    M3: Annotated formal (Appendix B, line 879).
    
    Example: 
    flies(X) :- bird(X), \\+ penguin(X).  % Typically, birds fly.
    """
    pass

class PureFormalEncoder:
    """
    M4: Pure formal (Appendix B, line 881).
    
    Raw Prolog/ASP syntax with no natural language.
    """
    pass
```

**Ontological Grounding Map** (Def 28, line 719):

```python
class OntologicalGroundingMap:
    """
    Definition 28: NL: HB → L*.
    
    Maps ground atoms to natural language strings.
    
    Properties (line 720):
    (i) Injectivity: NL(a1) = NL(a2) ⟹ a1 = a2
    (ii) Compositionality: NL decomposes via NL_P (predicates) and NL_C (constants)
    (iii) Domain coherence: Respects domain semantics
    
    Implementation strategies:
    1. Hand-crafted mappings (small domains)
    2. Template-based generation
    3. LLM-assisted paraphrasing with injectivity checks
    """
    
    def __init__(self, domain: str):
        self.domain = domain
        self.predicate_map: Dict[str, str] = {}
        self.constant_map: Dict[str, str] = {}
        self._inverse_cache: Dict[str, str] = {}
    
    def register_predicate(self, pred: str, nl: str) -> None:
        """Register predicate mapping."""
        assert nl not in self._inverse_cache, "Violates injectivity"
        self.predicate_map[pred] = nl
        self._inverse_cache[nl] = pred
    
    def register_constant(self, const: str, nl: str) -> None:
        """Register constant mapping."""
        assert nl not in self._inverse_cache, "Violates injectivity"
        self.constant_map[const] = nl
        self._inverse_cache[nl] = const
    
    def __call__(self, atom: str) -> str:
        """Map ground atom to NL via composition."""
        pred, args = parse_atom(atom)
        
        pred_nl = self.predicate_map.get(pred, pred)
        args_nl = [self.constant_map.get(arg, arg) for arg in args]
        
        # Compose via template
        if len(args) == 1:
            return f"{args_nl[0]} {pred_nl}"
        elif len(args) == 2:
            return f"{args_nl[0]} {pred_nl} {args_nl[1]}"
        else:
            return f"{pred_nl}({', '.join(args_nl)})"
    
    def inverse(self, nl: str) -> str:
        """Inverse map (for decoder)."""
        return self._inverse_cache.get(nl)
```

**Decoder: Three Strategies** (Def 29, line 723):

```python
class Decoder(Protocol):
    """Definition 29: ρ_dec: token sequence → Rule | ⊥."""
    
    def decode(self, response: str, instance: AbductiveInstance) -> Optional[Element]:
        """Parse model response to formal rule or fact."""
        ...

class ExactMatchDecoder:
    """
    D1: Exact match.
    
    Properties (Proposition 7, line 893):
    - Sound: ✓
    - Complete: ✗ (fails on paraphrases)
    - Faithful: ✓
    """
    
    def decode(self, response: str, instance: AbductiveInstance) -> Optional[Element]:
        response_clean = response.strip().lower()
        
        for candidate in instance.candidates:
            candidate_str = str(candidate).strip().lower()
            if response_clean == candidate_str:
                return candidate
        
        return None  # ⊥

class TemplateExtractionDecoder:
    """
    D2: Template extraction via edit distance.
    
    Strategy: Find candidate c minimizing d_edit(response, τ(c)).
    
    Properties (Proposition 7, line 894):
    - Sound: ✓
    - Complete: ✓
    - Faithful: conditional (iff τ injective and minimum unique)
    """
    
    def __init__(self, template_func: Callable[[Element], str]):
        self.template = template_func
    
    def decode(self, response: str, instance: AbductiveInstance) -> Optional[Element]:
        from Levenshtein import distance
        
        best_candidate = None
        best_distance = float('inf')
        
        for candidate in instance.candidates:
            template_str = self.template(candidate)
            dist = distance(response, template_str)
            
            if dist < best_distance:
                best_distance = dist
                best_candidate = candidate
        
        # Threshold to reject bad matches
        if best_distance > len(response) * 0.5:
            return None
        
        return best_candidate

class SemanticExtractionDecoder:
    """
    D3: Semantic extraction via parser.
    
    Strategy: Use grammar-based parser (Lark) + semantic parser (transformer).
    
    Properties (Proposition 7, line 895):
    - Sound: conditional (iff M_parse outputs well-formed rules only)
    - Complete: ✓
    - Faithful: approximate
    """
    
    def __init__(self, grammar_path: str, semantic_model: str = None):
        from lark import Lark
        
        with open(grammar_path) as f:
            grammar = f.read()
        
        self.parser = Lark(grammar, start='rule')
        self.semantic_model = semantic_model  # Optional: GPT-4/Claude for parsing
    
    def decode(self, response: str, instance: AbductiveInstance) -> Optional[Element]:
        # Strategy 1: Grammar-based parsing
        try:
            tree = self.parser.parse(response)
            return self._tree_to_rule(tree)
        except Exception:
            pass
        
        # Strategy 2: Semantic extraction via LLM
        if self.semantic_model:
            try:
                return self._semantic_parse(response, instance)
            except Exception:
                pass
        
        return None
    
    def _tree_to_rule(self, tree) -> Rule:
        """Convert parse tree to Rule object."""
        # Implementation depends on grammar
        pass
    
    def _semantic_parse(self, response: str, instance: AbductiveInstance) -> Optional[Rule]:
        """Use LLM to extract formal rule from natural language."""
        # Prompt LLM: "Convert this to formal logic: {response}"
        # Validate output is well-formed
        pass
```

**Round-Trip Validation** (Def 30, line 727):

```python
def round_trip_test(
    encoder: Encoder,
    decoder: Decoder,
    instances: List[AbductiveInstance],
    modality: Modality
) -> float:
    """
    Definition 30: Round-trip consistency.
    
    For each candidate c:
    1. Encode: s = encoder.encode_candidate(c)
    2. Decode: c' = decoder.decode(s, instance)
    3. Check: c' == c
    
    Returns: Fraction of successful round-trips.
    """
    successes = 0
    total = 0
    
    for instance in instances:
        for candidate in instance.candidates:
            # Encode candidate
            encoded = encoder.encode_candidate(candidate, modality)
            
            # Decode
            decoded = decoder.decode(encoded, instance)
            
            # Check
            if decoded == candidate:
                successes += 1
            
            total += 1
    
    return successes / total if total > 0 else 0.0
```

**Critical Tests**:

```python
def test_round_trip_consistency():
    """
    Definition 30: Verify round-trip for all modality-decoder pairs.
    
    Requirements (Proposition 8, lines 903-905):
    - D1 (exact): 100% round-trip by construction
    - D2 (template): 100% iff τ injective
    - D3 (semantic): approximate (test empirically)
    """
    instances = generate_test_instances()
    
    for modality in [Modality.NARRATIVE, Modality.SEMI_FORMAL,
                     Modality.ANNOTATED, Modality.PURE_FORMAL]:
        
        encoder = get_encoder(modality)
        
        # D1: Exact match
        decoder_exact = ExactMatchDecoder()
        accuracy = round_trip_test(encoder, decoder_exact, instances, modality)
        assert accuracy == 1.0, f"D1 must have perfect round-trip, got {accuracy}"
        
        # D2: Template extraction
        decoder_template = TemplateExtractionDecoder(lambda c: encoder.encode_candidate(c, modality))
        accuracy = round_trip_test(encoder, decoder_template, instances, modality)
        assert accuracy >= 0.95, f"D2 should have high round-trip, got {accuracy}"
        
        # D3: Semantic extraction
        decoder_semantic = SemanticExtractionDecoder('grammars/logic.lark')
        accuracy = round_trip_test(encoder, decoder_semantic, instances, modality)
        # No hard requirement, but warn if too low
        if accuracy < 0.8:
            warnings.warn(f"D3 round-trip low for {modality}: {accuracy}")

def test_modality_ordering():
    """
    Definition 27: Verify naturalness-faithfulness tradeoff.
    
    Nat(M1) ≥ Nat(M2) ≥ Nat(M3) ≥ Nat(M4)
    Faith(M4) ≥ Faith(M3) ≥ Faith(M2) ≥ Faith(M1)
    """
    instances = generate_test_instances()
    
    # Compute naturalness (via reference LM perplexity)
    naturalness = {}
    for mod in [Modality.NARRATIVE, Modality.SEMI_FORMAL,
                Modality.ANNOTATED, Modality.PURE_FORMAL]:
        encoder = get_encoder(mod)
        perplexity = compute_perplexity(encoder, instances)
        naturalness[mod] = -perplexity  # Higher is more natural
    
    # Check ordering
    assert naturalness[Modality.NARRATIVE] >= naturalness[Modality.SEMI_FORMAL]
    assert naturalness[Modality.SEMI_FORMAL] >= naturalness[Modality.ANNOTATED]
    assert naturalness[Modality.ANNOTATED] >= naturalness[Modality.PURE_FORMAL]
    
    # Compute faithfulness (via ideal reasoner accuracy)
    faithfulness = {}
    for mod in [Modality.NARRATIVE, Modality.SEMI_FORMAL,
                Modality.ANNOTATED, Modality.PURE_FORMAL]:
        encoder = get_encoder(mod)
        decoder = SemanticExtractionDecoder('grammars/logic.lark')
        faithfulness[mod] = round_trip_test(encoder, decoder, instances, mod)
    
    # Check ordering
    assert faithfulness[Modality.PURE_FORMAL] >= faithfulness[Modality.ANNOTATED]
    assert faithfulness[Modality.ANNOTATED] >= faithfulness[Modality.SEMI_FORMAL]
    assert faithfulness[Modality.SEMI_FORMAL] >= faithfulness[Modality.NARRATIVE]

def test_injectivity():
    """
    Definition 28(i): NL map must be injective.
    
    NL(a1) = NL(a2) ⟹ a1 = a2
    
    This is CRITICAL for decoder correctness.
    """
    nl_map = OntologicalGroundingMap('biology')
    
    # Register mappings
    nl_map.register_predicate('bird', 'is a bird')
    nl_map.register_predicate('flies', 'can fly')
    nl_map.register_constant('tweety', 'Tweety')
    
    # Generate all atoms
    atoms = ['bird(tweety)', 'flies(tweety)']
    nl_strings = [nl_map(a) for a in atoms]
    
    # Check injectivity: no duplicates
    assert len(nl_strings) == len(set(nl_strings)), "NL map violates injectivity"
    
    # Check inverse
    for atom in atoms:
        nl_str = nl_map(atom)
        recovered = nl_map.inverse(nl_str)
        assert recovered == atom, f"Inverse failed: {atom} → {nl_str} → {recovered}"
```

### Phase 4B: Evaluation Pipeline (Week 9)

**Goal**: Implement Defs 31-32 (rendering-robust accuracy, partial credit).

**Files**:
- `experiments/evaluation.py`
- `experiments/partial_credit.py`
- `experiments/statistics.py`

**Key Functions**:

```python
def rendering_robust_accuracy(
    model: LanguageModel,
    instances: List[AbductiveInstance],
    modalities: List[Modality] = None
) -> float:
    """
    Definition 31: Rendering-robust accuracy.
    
    Acc_robust(M) = (1/N) Σ_i min_j Pr_M[h ∈ H*_i | ρ^(j)_enc(I_i)]
    
    where j ranges over modalities M1-M4.
    
    Headline metric: worst-case accuracy across all modalities.
    Ensures scores reflect reasoning, not surface-form sensitivity.
    """
    if modalities is None:
        modalities = list(Modality)
    
    total_score = 0.0
    
    for instance in instances:
        # Evaluate on all modalities
        modality_accuracies = []
        
        for modality in modalities:
            encoder = get_encoder(modality)
            decoder = get_decoder(modality)
            
            # Encode instance
            prompt = encoder.encode(instance, modality)
            
            # Query model
            response = model.generate(prompt)
            
            # Decode response
            hypothesis = decoder.decode(response, instance)
            
            # Check if correct
            is_correct = hypothesis in instance.gold
            modality_accuracies.append(1.0 if is_correct else 0.0)
        
        # Worst-case accuracy for this instance
        instance_score = min(modality_accuracies)
        total_score += instance_score
    
    return total_score / len(instances)

def graded_score_level3(
    D: DefeasibleTheory,
    alpha: str,
    hypothesis: Optional[Rule],
    gamma: Dict[str, Set[str]],
    language_bias: LanguageBias
) -> float:
    """
    §4.5: Graded scoring function for Level 3.
    
    Scores (lines 404-410):
    0.00: ⊥ (decoder failure) or anomaly unresolved
    0.25: Resolves but violates language bias
    0.50: Valid weak resolution, non-conservative
    0.75: Conservative weak OR non-conservative strong
    1.00: Conservative resolution
    
    Decomposes failures along stages of rational belief revision.
    """
    if hypothesis is None:
        return 0.0  # Decoder failure
    
    # Augment theory
    D_prime = DefeasibleTheory(
        F=D.F | {alpha},
        Rs=D.Rs,
        Rd=D.Rd | {hypothesis},
        Rdf=D.Rdf,
        superiority=merge_superiority(D.superiority, gamma)
    )
    
    # Check if anomaly resolved
    if defeasible_provable(D_prime, f"~{alpha}"):
        return 0.0  # Anomaly still provable
    
    # Check language bias
    if not satisfies_language_bias(hypothesis, language_bias):
        return 0.25  # Syntactically valid but violates constraints
    
    # Check conservativity
    is_conservative = is_conservative_resolution(D, alpha, hypothesis, gamma)
    
    # Check resolution strength
    is_weak = not defeasible_provable(D_prime, alpha)
    is_strong = defeasible_provable(D_prime, alpha)
    
    if is_conservative:
        return 1.0  # Full credit
    elif is_strong:
        return 0.75  # Non-conservative strong
    elif is_weak:
        return 0.50  # Non-conservative weak
    else:
        return 0.25  # Shouldn't reach here

def dataset_statistics(dataset: List[AbductiveInstance]) -> Dict:
    """
    §4.3: Dataset statistics and structural analysis.
    
    Reports:
    - Volume and balance (per level, per KB, per partition)
    - Structural difficulty distributions
    - Novelty and revision spectrum (Level 3)
    - Yield analysis
    - Partition sensitivity
    """
    stats = {}
    
    # Volume
    stats['total_instances'] = len(dataset)
    stats['by_level'] = {
        1: len([i for i in dataset if i.level == 1]),
        2: len([i for i in dataset if i.level == 2]),
        3: len([i for i in dataset if i.level == 3])
    }
    
    # Structural difficulty
    difficulties = [structural_difficulty(i) for i in dataset]
    stats['difficulty_distribution'] = {
        'mean': np.mean(difficulties),
        'std': np.std(difficulties),
        'quantiles': np.quantile(difficulties, [0.25, 0.5, 0.75])
    }
    
    # Level 3 specific
    level3_instances = [i for i in dataset if i.level == 3]
    stats['level3_novelty'] = [
        i.metadata['novelty'] for i in level3_instances
    ]
    stats['level3_revision_distance'] = [
        i.metadata['revision_distance'] for i in level3_instances
    ]
    
    return stats
```

## 4. Testing Strategy

### 4.1 Unit Tests

Every mathematical function gets a unit test:

```python
# Test against paper propositions
def test_proposition_1_conservative_conversion(): ...
def test_proposition_2_definite_implies_defeasible(): ...
def test_proposition_3_yield_monotonicity(): ...
def test_proposition_4_criticality_inclusion(): ...
def test_proposition_5_candidate_space_size(): ...
def test_proposition_6_gold_nonempty(): ...
def test_theorem_11_polynomial_derivation(): ...

# Test examples from paper
def test_tweety_example(): ...
def test_idp_example(): ...
def test_family_relations(): ...
def test_medical_diagnosis(): ...
```

### 4.2 Integration Tests

End-to-end instance generation:

```python
def test_level1_generation_pipeline():
    """Generate 100 Level 1 instances, verify all properties."""
    ...

def test_level2_generation_pipeline():
    """Generate 100 Level 2 instances, verify all properties."""
    ...

def test_level3_generation_pipeline():
    """Generate 10 Level 3 instances (expensive), verify conservativity."""
    ...
```

### 4.3 Property-Based Tests (Hypothesis)

```python
from hypothesis import given, strategies as st

@given(st.from_type(DefeasibleTheory), st.text())
def test_derivation_deterministic(D, q):
    """Defeasible derivation is deterministic."""
    result1 = defeasible_provable(D, q)
    result2 = defeasible_provable(D, q)
    assert result1 == result2

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

### 4.4 Benchmark Tests

Validate against known datasets:

```python
def test_proofwriter_benchmark():
    """Verify our derivations match ProofWriter gold labels."""
    dataset = load_proofwriter()
    
    for example in dataset:
        D = convert_to_defeasible(example.theory)
        
        for fact, label in example.questions:
            our_derivation = defeasible_provable(D, fact)
            assert our_derivation == label
```

### 4.5 Performance Regression Tests

```python
@pytest.mark.benchmark
def test_criticality_performance():
    """Ensure O(|D|² · |F|) complexity holds."""
    sizes = [10, 20, 40, 80, 160]
    
    for n in sizes:
        D, q = generate_theory_of_size(n)
        
        result = pytest.benchmark(
            full_theory_criticality, D, q
        )
        
        # Verify quadratic scaling
        ...
```

## 5. Validation & Verification

### 5.1 Mathematical Correctness

**Propositions to verify**:
- ✓ Proposition 1: Conservative conversion
- ✓ Proposition 2: Definite implies defeasible
- ✓ Proposition 3: Yield monotonicity
- ✓ Proposition 4: Criticality inclusion
- ✓ Proposition 5: Candidate space size
- ✓ Proposition 6: Gold set non-empty

**Theorems to verify**:
- ✓ Theorem 11: Defeasible derivation in P

### 5.2 Example Validation

**Work through paper examples**:
- § Tweety (introduction)
- § IDP Discovery (Appendix C, Example 1)
- § Family relations
- § Medical diagnosis
- § Citizenship

### 5.3 Codec Validation

**Critical**: Round-trip tests for all modality-decoder pairs.

**Injectivity tests**: NL map must be bijective on relevant domain.

**Faithfulness tests**: Ideal reasoner should solve all instances.

## 6. Risk Mitigation

### 6.1 High-Risk Components

1. **Codec (encoder/decoder)** - 40% risk
   - Mitigation: Extensive round-trip testing
   - Fallback: Start with M4 (pure formal), expand to M1-M3

2. **Level 3 generation** - 30% risk
   - Mitigation: Start with hand-authored defeaters
   - Fallback: Focus on Levels 1-2 for MVP

3. **Expectation set computation** - 20% risk
   - Mitigation: Limit to small Herbrand bases
   - Fallback: Sample expectations, don't enumerate

4. **Defeasible derivation** - 10% risk
   - Mitigation: Test against known benchmarks
   - Libraries: Consider existing defeasible logic implementations

### 6.2 Fallback Strategies

**If codec fails**:
- Use M4 (pure formal) only
- Restrict to multiple-choice evaluation (no generation)

**If Level 3 too complex**:
- Focus MVP on Levels 1-2
- Defer defeater abduction to future work

**If expectation sets too expensive**:
- Sample random subset of expectations
- Use conservative overapproximation

## 7. Implementation Schedule

### Week 1-2: Defeasible Reasoning
- [ ] reasoning/defeasible.py
- [ ] reasoning/derivation_tree.py
- [ ] reasoning/expectations.py
- [ ] Tests: Tweety, team defeat, complexity

### Week 2: Conversion & Partitions
- [ ] author/conversion.py
- [ ] generation/partition.py
- [ ] Tests: Proposition 1, Proposition 3

### Week 3: Support & Criticality
- [ ] author/support.py
- [ ] Tests: Proposition 4, complexity bounds

### Week 4: Instance Generation (Levels 1-2)
- [ ] author/generation.py
- [ ] generation/distractor.py
- [ ] Tests: Instance validity, distractor strategies

### Week 5-6: Level 3
- [ ] author/level3.py
- [ ] author/metrics.py
- [ ] generation/language_bias.py
- [ ] Tests: IDP example, conservativity, AGM correspondence

### Week 7-8: Codec
- [ ] codec/encoder.py (M1-M4)
- [ ] codec/decoder.py (D1-D3)
- [ ] codec/nl_map.py
- [ ] codec/validation.py
- [ ] Tests: Round-trip, injectivity, faithfulness

### Week 9: Evaluation
- [ ] experiments/evaluation.py
- [ ] experiments/partial_credit.py
- [ ] experiments/statistics.py
- [ ] End-to-end integration tests

### Week 10: Validation & Polish
- [ ] Validate all propositions
- [ ] Benchmark tests
- [ ] Documentation
- [ ] Performance optimization

## 8. Success Criteria

**Mathematical Correctness**:
- [ ] All 6 propositions verified
- [ ] Theorem 11 complexity bound met
- [ ] Paper examples reproduce exactly

**Functionality**:
- [ ] Generate Levels 1-3 instances
- [ ] All 4 rendering modalities
- [ ] All 3 decoder strategies
- [ ] Round-trip >95% for D1, D2

**Performance**:
- [ ] O(|D|² · |F|) criticality
- [ ] O(|R| · |F|) defeasible derivation
- [ ] Generate 1000 instances in <1 hour

**Testing**:
- [ ] >90% code coverage
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] All property-based tests pass

## 9. Next Steps

1. **Read this plan carefully**
2. **Validate mathematical mappings** (Defs → code)
3. **Set up test infrastructure** (pytest, hypothesis, benchmarks)
4. **Begin Week 1**: Defeasible reasoning engine
5. **Regular check-ins**: Compare generated instances with paper examples

---

**This plan is the blueprint. Follow it exactly. Every deviation risks mathematical incorrectness.**
