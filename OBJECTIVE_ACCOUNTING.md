# BLANC: Accounting for the Three Core Objectives

**Relating Implementation to Paper.tex Framework**

Patrick Cooper  
February 13, 2026

---

## The Three Core Objectives

From `paper.tex` (lines 164, 175-177, 222):

> Foundation models suffer three entangled structural deficits:
> 1. **Grounding deficit**: Cannot trace conclusions to supporting evidence (root cause of hallucination)
> 2. **Novelty deficit**: Cannot generate hypotheses that revise their training distribution
> 3. **Belief revision deficit**: Cannot update knowledge while preserving unrelated commitments

The paper proposes defeasible reasoning as the unifying framework:

> "Our approach addresses the three deficits...by constructing evaluation instances from knowledge bases whose epistemic structure is fully explicit." (line 222)

This document provides a comprehensive accounting of how well we measure each objective in our current implementation.

---

## 1. Grounding: Traceable Support Sets

### Paper's Definition

**Grounding** means making epistemic structure explicit:
- Every conclusion has a **traceable support set**
- Can determine **why** the theory concludes what it does
- Can identify which elements are **critical** for a derivation

From paper.tex line 179:
> "In a defeasible theory, every conclusion is derived through a traceable chain of strict and defeasible rules, every default is explicitly revisable, and every piece of evidence participates in identifiable support sets. This provides grounding (one can determine why the theory concludes what it does)..."

### What We Have Implemented

#### ✅ Full-Theory Criticality (Definition 18, line 607)

**File**: `src/blanc/author/support.py`

```python
def full_theory_criticality(theory: Theory, target: str) -> List[Element]:
    """
    Compute Crit*(D, q) = {e ∈ F ∪ Rs ∪ Rd | D \ {e} ⊬∂ q}
    
    Complexity: O(|D|² · |F|) - polynomial time
    """
```

**What it does**:
- For any derivable conclusion `q`, identifies exactly which elements are **necessary**
- Removes each element one at a time and checks if `q` is still derivable
- Returns the set of critical elements (facts + rules)

**Paper reference**: Lines 607-609, 292 (complexity)

**Status**: ✅ **FULLY IMPLEMENTED**
- 186 test cases passing
- Used in all instance generation (374 instances generated)
- Verified O(|D|²·|F|) complexity experimentally

#### ✅ Instance Generation via Ablation (Definition 21, lines 619-620)

**File**: `src/blanc/author/generation.py`

```python
def generate_level1_instance(theory, target, critical_fact):
    """Ablate e ∈ F ∩ Crit*(D, q) - Level 1"""

def generate_level2_instance(theory, target, critical_rule):
    """Ablate e ∈ Rd ∩ Crit*(D, q) - Level 2"""
```

**What it does**:
- Uses criticality to identify **which elements matter**
- Ablates (removes) critical elements to create gaps in reasoning
- Forces models to identify what's missing to restore derivability

**Paper reference**: "we generate evaluation instances by exploiting the grounding structure: because every conclusion has an identifiable support set, we can determine precisely which elements are necessary for a given derivation" (line 244)

**Status**: ✅ **FULLY IMPLEMENTED**
- Level 1 (fact completion): 374 instances generated
- Level 2 (rule abduction): 374 instances generated
- All use criticality-based ablation

#### ⚠️ Support Set Enumeration (Definition 17, line 603)

**Paper**: Minimal support sets Supp(D,q)
**Implementation**: NOT FULLY IMPLEMENTED (NP-complete)

We use **Crit*(D,q)** (polynomial) as a conservative approximation:
- Paper line 767: "Crit*(D, q) ⊆ Crit(D, q) (possibly strict)"
- Line 301: "Since we use Crit* (polynomial) rather than full support enumeration (NP-hard)..."

**Status**: ⚠️ **APPROXIMATED** (acceptable for MVP)
- Criticality gives us **necessary** elements
- Doesn't enumerate all **minimal sufficient** sets
- Future work: SAT-based enumeration for exact support sets

### Grounding in Evaluation

**Dataset Statistics**:
- **374 instances** generated via criticality-based ablation
- **Every instance** has explicit dependency structure
- **100% traceability**: Can identify which elements support each conclusion

**What This Tests**:
1. Can models identify **why** a conclusion doesn't follow?
2. Can they recognize **what's missing** to restore derivability?
3. Do they understand **dependency structure** (facts vs rules)?

### Grounding Score: 8/10

**Strengths**:
- ✅ Polynomial-time criticality fully implemented
- ✅ All instances use grounding structure
- ✅ Tests whether models understand "why" questions
- ✅ 343 tests passing, 80% coverage

**Gaps**:
- ⚠️ Support set enumeration is approximated (NP-hard)
- ⚠️ No explicit metrics for "grounding quality" in results
- ⚠️ Evaluation doesn't measure if models **explain** their answers

**Recommendation**: 
- Add "explanation depth" metric: Do models cite specific rules?
- Current implementation is **publication-ready** for Levels 1-2

---

## 2. Novelty: Generating Novel Hypotheses

### Paper's Definition

**Novelty** means generating hypotheses with predicates/concepts **not in the training data**:
- Models must identify where **creative exceptions** apply
- Must introduce **new predicates** to resolve anomalies
- "The very hypotheses a model would need to generate are precisely those it has never seen" (line 183)

From paper.tex line 175:
> "The second is a novelty deficit: without knowing which beliefs are revisable, models cannot identify where creative exceptions might apply."

### What We Have Implemented

#### ✅ Predicate Novelty Metric (Definition 33, line 683)

**File**: `author.py` (lines 640-667)

```python
def predicate_novelty(r: Rule, D: DefeasibleTheory) -> float:
    """
    Nov(r, D) = |pred(r) \ pred(D)| / |pred(r)|
    
    Fraction of predicates in r that are novel to D.
    
    Nov = 0: No novelty (all predicates already known)
    Nov = 1: Maximal novelty (all predicates new)
    """
```

**What it measures**:
- How many predicates in hypothesis `r` are **absent** from theory `D`
- Quantifies "out-of-distribution" generation
- 0 = extending existing knowledge, 1 = completely novel concepts

**Paper reference**: Line 194 "Predicate novelty quantifies symbols introduced beyond the theory"

**Status**: ✅ **IMPLEMENTED** but not yet in dataset

#### ⚠️ Level 3 Instances (Defeater Abduction)

**Paper goal** (lines 252, 340):
> "The model must construct a novel defeater or exception rule to resolve the contradiction while preserving unrelated expectations, performing rational belief revision in the defeasible setting."

**Current status**:
- Level 3 generation framework exists (`scripts/generate_level3_instances.py`)
- **Hand-authored examples** exist (penguin, ostrich, duck)
- **Not yet in development dataset** (only Level 2 instances)

**Why not included**:
- Requires **complete theories** D^full with pre-existing defeaters
- Need domain expert validation for each defeater
- Time-intensive manual curation

**What exists**:
```python
# Example from scripts/generate_level3_instances.py
defeater = Rule(
    head="~flies(X)",
    body=("penguin(X)",),
    rule_type=RuleType.DEFEATER,
    label="penguin_exception"
)
# Nov(defeater, D) = 0 (uses existing predicates: penguin, flies)
# But structure is novel: blocking rule, not generalization
```

#### 📊 Language Bias & Novel Predicate Control (Definition 32, line 677)

**Paper** (line 350):
> "We parameterize the language bias L along two axes: the permitted predicate set P+ (restricted to predicates appearing in D^-, or expanded to include a controlled novel vocabulary)..."

**Implementation**: Partially exists in Level 3 framework

```python
# From scripts/generate_level3_instances.py
language_bias = {
    'predicates': ['bird', 'penguin', 'flies', 'conf_ensemble'],  # Novel!
    'max_antecedent_length': 3,
    'nesting_depth': 1
}
```

**Status**: ⚠️ **FRAMEWORK EXISTS** but not systematically varied

### Novelty in Current Dataset

**Level 1 (Fact Completion)**: Nov = 0 always
- Task: "bird(owl)" - uses existing predicate `bird`
- No novelty possible (facts use known predicates)

**Level 2 (Rule Abduction)**: Nov = 0 for all 374 instances
- Task: Reconstruct "flies(X) :- bird(X)"
- Uses existing predicates from theory
- Structural novelty (rule form) but not predicate novelty

**Level 3 (Defeater Abduction)**: NOT IN DATASET YET
- Would require novel predicates or novel rule structures
- Examples exist but not systematically generated

### Novelty in Evaluation Pipeline

**What's Ready**:
- `predicate_novelty()` function implemented
- Can compute Nov(h, D) for any hypothesis
- Evaluation pipeline has `novelty` field in metrics

**File**: `experiments/evaluation_pipeline.py` (line 52)
```python
@dataclass
class EvaluationMetrics:
    novelty: Optional[float] = None
```

**What's Missing**:
- No instances with Nov > 0 in current dataset
- Can't test if models generate novel predicates
- Can't measure "creative abduction" yet

### Novelty Score: 4/10

**Strengths**:
- ✅ Novelty metric implemented and tested
- ✅ Framework exists for Level 3 (defeater abduction)
- ✅ Language bias parameterization defined
- ✅ Evaluation pipeline ready to measure novelty

**Gaps**:
- ❌ **No Level 3 instances in development dataset** (374 instances)
- ❌ All current instances have Nov = 0
- ❌ Cannot test creative hypothesis generation
- ❌ No systematic variation of language bias

**Critical Issue**: 
The paper claims to test novelty (line 192: "testing grounding, novelty, and rational revision"), but our **current dataset only tests grounding and basic abduction**.

**Recommendation**:
1. **Urgent**: Generate 20-50 Level 3 instances for pilot
2. **Medium-term**: Systematic Level 3 generation with varying Nov*
3. **Publication**: Either:
   - Add Level 3 instances before submission, OR
   - Acknowledge in paper: "Level 3 deferred to future work"

---

## 3. Belief Revision: Conservative Updates

### Paper's Definition

**Belief revision** means updating knowledge while preserving unrelated commitments:
- Follow **AGM minimal change** principle (Alchourrón-Gärdenfors-Makinson)
- Resolve one anomaly **without introducing new ones**
- Measure adherence via **revision distance**

From paper.tex line 175:
> "The third...is a belief revision deficit: even when models do update their knowledge...they lack the formal machinery to ensure that changes satisfy the principle of minimal change: accommodating new evidence while disturbing as few existing commitments as possible."

From line 265:
> "This is our operationalization of the AGM principle of minimal change: just as rational belief revision requires that an agent accommodate new evidence while disturbing as few existing commitments as possible, conservative resolution requires that correcting one anomaly not introduce new ones."

### What We Have Implemented

#### ✅ Conservativity Check (Definition 30, line 670)

**File**: `author.py` (lines 594-619), `scripts/generate_level3_instances.py` (line 26)

```python
def is_conservative_resolution(
    D_minus: DefeasibleTheory,
    Delta: Set[Element],
    anomaly: str,
    expectations: Set[str]
) -> bool:
    """
    Conservativity check (§3.4, line 265; Remark 2, line 672).
    
    Resolution (r, Γ) is conservative iff:
      ∀q ∈ Exp(D^-) \ {¬α}: (D^- ∪ Δ) ⊢∂ q
    
    Preserves all expectations except the anomaly.
    This operationalizes AGM minimal change.
    """
```

**What it checks**:
- Theory D^- has set of expectations Exp(D^-) 
- After adding resolution Δ, all expectations **except ¬α** are preserved
- No "side effects" from the update

**Paper reference**: Lines 265, 670-672

**Status**: ✅ **IMPLEMENTED** in Level 3 framework

#### ✅ Revision Distance (Definition 34, line 687)

**File**: `author.py` (lines 620-639)

```python
def revision_distance(D: DefeasibleTheory, D_prime: DefeasibleTheory) -> int:
    """
    Revision distance (§3.4, line 269; Remark 3, line 687).
    
    d_rev(D, D') = |Δ| + |Exp(D) \ Exp(D')|
    
    = Elements added + Expectations lost
    
    Conservative resolutions achieve d_rev = |Δ| (no expectation loss).
    Measures adherence to minimal change principle.
    """
```

**What it measures**:
- Δ = structural changes (elements added)
- |Exp(D) \ Exp(D')| = lost expectations (side effects)
- Lower distance = more conservative
- Perfect conservativity: d_rev = |Δ| (no lost expectations)

**Paper reference**: "our defeasible analogue of Dalal's distance-based approach to belief revision" (line 269)

**Status**: ✅ **IMPLEMENTED** in Level 3 framework

#### 📝 Level 3 Hand-Authored Examples

**File**: `scripts/generate_level3_instances.py`

**Example 1: Penguin (Weak Blocking)**
```python
# Anomaly: penguins don't fly
# Resolution: Add defeater "¬flies(X) :- penguin(X)"
# Conservativity: Preserves flies(robin), flies(eagle), etc.
# Nov(defeater, D) = 0 (uses existing predicates)
# d_rev = 1 (adds 1 rule, loses 0 expectations)
```

**Example 2: Ostrich (Strong Exception)**
```python
# Anomaly: ostriches don't fly  
# Resolution: Add "runs(X) :- ostrich(X)" with superiority
# Conservativity: Preserves all other bird behaviors
# Nov = 0, d_rev = 2 (rule + superiority)
```

**Example 3: Duck (Restructuring)**
```python
# Anomaly: ducks don't migrate (some do, some don't)
# Resolution: Add conditional exception
# Conservativity: Preserves migration for other birds
# Nov = 0, d_rev = variable
```

**Status**: ✅ **3 EXAMPLES EXIST** with full conservativity checks

### Belief Revision in Current Dataset

**Level 1 & Level 2**: Not applicable
- These levels test **monotonic extension** (adding facts/rules)
- No revision or retraction involved
- Cannot test conservativity

**Level 3**: Framework exists, examples validated, **but not in development dataset**

### Belief Revision in Evaluation

**What's Ready**:
```python
# experiments/evaluation_pipeline.py
@dataclass
class EvaluationMetrics:
    conservativity: Optional[bool] = None  # Line 53
```

**What Would Be Measured** (if we had Level 3 instances):
1. Does model-generated hypothesis resolve the anomaly?
2. Is it conservative (preserves unrelated expectations)?
3. What is the revision distance d_rev?
4. How does it compare to gold standard?

### Belief Revision Score: 3/10

**Strengths**:
- ✅ Conservativity check fully implemented
- ✅ Revision distance metric implemented
- ✅ 3 hand-validated examples with full checks
- ✅ Evaluation pipeline ready to measure

**Gaps**:
- ❌ **No Level 3 instances in development dataset** (0 of 374)
- ❌ Cannot test if models perform conservative updates
- ❌ Cannot measure adherence to minimal change
- ❌ No systematic variation of conservativity difficulty

**Critical Issue**:
The paper's **main claim** (line 113, title) is about "Belief Revision", but we **cannot evaluate it** with current dataset.

**Recommendation**:
1. **URGENT**: Generate Level 3 pilot dataset (20-50 instances)
2. **Before submission**: Either include Level 3 results or revise paper scope
3. **Alternative**: Reframe paper as "Levels 1-2 with Level 3 framework"

---

## Summary Table: Objective Coverage

| Objective | Paper Claim | Implementation Status | Dataset Coverage | Evaluation Ready? | Score |
|-----------|-------------|----------------------|------------------|-------------------|-------|
| **Grounding** | Traceable support sets, criticality | ✅ Full | 374/374 instances (100%) | ✅ Yes | 8/10 |
| **Novelty** | Generate novel predicates, creative abduction | ✅ Metric exists | 0/374 instances (0%) | ✅ Pipeline ready | 4/10 |
| **Belief Revision** | Conservative updates, minimal change | ✅ Full framework | 0/374 instances (0%) | ✅ Pipeline ready | 3/10 |

---

## What We Can Claim Now

### Strong Claims ✅

1. **Grounding is fully operational**
   - "We provide a polynomial-time algorithm for computing full-theory criticality"
   - "374 instances test whether models understand support structure"
   - "Every instance has explicit dependency traceability"

2. **Framework is complete**
   - "We implement all three objectives: grounding, novelty, belief revision"
   - "Evaluation pipeline supports all metrics"
   - "Proof-of-concept Level 3 instances validate framework"

### Weak Claims ⚠️

3. **Novelty testing is preliminary**
   - "We provide a metric for predicate novelty Nov(r, D)"
   - "Level 3 framework supports novel hypothesis generation"
   - But: "Current dataset focuses on Levels 1-2 (grounding)"

4. **Belief revision testing is deferred**
   - "We operationalize AGM minimal change via conservativity"
   - "Hand-validated examples demonstrate feasibility"
   - But: "Systematic Level 3 evaluation is future work"

### Claims We CANNOT Make ❌

5. **Cannot claim to evaluate all three objectives empirically**
   - Paper line 192 claims "testing grounding, novelty, and rational revision"
   - Reality: Only testing grounding systematically (Levels 1-2)
   - Novelty and revision have **0% dataset coverage**

6. **Cannot claim full NeurIPS contribution**
   - Title: "Grounding, Novelty, and Belief Revision"
   - Current dataset: Grounding only
   - Mismatch between claims and deliverables

---

## Gap Analysis

### The Core Problem

**Paper's Ambition**: Test all three deficits (grounding, novelty, belief revision)

**Current Reality**: Only grounding is systematically tested

**Gap**: 
- Level 3 (defeater abduction) is essential for novelty and belief revision
- Level 3 instances: 0 in development dataset, 3 hand-crafted examples
- Need: ~50-100 Level 3 instances for credible evaluation

### Why the Gap?

From paper.tex line 341:
> "TODO: Level 3 instance generation requires complete theories D^full with pre-existing defeaters. This is the main bottleneck: we need domain experts to author the defeaters/exceptions for each source KB."

**Time Cost**:
- Level 1: Automated (facts from KB)
- Level 2: Automated (rules from KB)  
- Level 3: **Manual** (requires expert-authored defeaters + validation)

**Domain Expertise Required**:
- Biology: Which biological rules have well-known exceptions?
- Legal: Which legal statutes have codified exceptions?
- Materials: Which material properties have exceptional cases?

### What Would Fill the Gap?

**Minimum Viable** (1-2 days):
- 20 Level 3 instances per domain (60 total)
- Hand-curate defeaters from textbook exception cases
- Validate conservativity for each
- Run pilot evaluation

**Publication Quality** (1-2 weeks):
- 50-100 Level 3 instances per domain (150-300 total)
- Systematic variation of Nov* and d_rev
- Full evaluation across all models
- Statistical analysis of conservativity

**Comprehensive** (1-2 months):
- 200+ Level 3 instances per domain
- Multiple resolution types (weak, strong, restructuring)
- Language bias variation (controlled novel vocabulary)
- Scaling analysis

---

## Recommendations

### Option 1: Full Implementation (Recommended if Time Permits)

**Timeline**: 2-3 weeks

1. **Week 1**: Generate 60-100 Level 3 instances
   - Biology: 20-30 instances (penguin-style exceptions)
   - Legal: 20-30 instances (statutory exceptions)
   - Materials: 20-30 instances (property exceptions)

2. **Week 2**: Run pilot evaluation
   - Test models on Level 3 instances
   - Measure Nov(h, D) and d_rev
   - Validate conservativity checking

3. **Week 3**: Analysis and paper integration
   - Statistical analysis of novelty and revision
   - Update paper with full results
   - Complete all three objectives

**Pros**: 
- Delivers on paper's promise
- Strong NeurIPS contribution
- All three objectives tested

**Cons**:
- Requires domain expertise
- Time-intensive manual validation
- May delay submission

### Option 2: Partial Implementation (Pragmatic)

**Timeline**: 3-5 days

1. Generate 20-30 Level 3 instances (proof of concept)
2. Run pilot evaluation on these instances
3. Update paper to acknowledge limited Level 3 coverage
4. Frame as "Levels 1-2 comprehensive, Level 3 preliminary"

**Pros**:
- Feasible within tight timeline
- Demonstrates all three objectives
- Honest about scope

**Cons**:
- Weaker empirical results for novelty/revision
- Reviewers may question limited Level 3 coverage

### Option 3: Scope Reduction (Conservative)

**Timeline**: 1-2 days (paper revisions only)

1. Revise paper title and abstract
2. Reframe as "Grounding framework with extension to novelty/revision"
3. Present Levels 1-2 as primary contribution
4. Position Level 3 as "framework validated, full evaluation future work"

**Pros**:
- Honest about current state
- No risk of over-claiming
- Still solid contribution (grounding is valuable)

**Cons**:
- Less ambitious
- May reduce novelty perception
- Doesn't leverage full framework

---

## Technical Debt Summary

### Implemented and Ready ✅

1. Full-theory criticality (Crit*)
2. Level 1 & 2 instance generation
3. All 4 modalities (M1-M4)
4. All 3 decoders (D1-D3)
5. Predicate novelty metric
6. Conservativity check
7. Revision distance metric
8. Evaluation pipeline with all metrics
9. 343 tests passing, 80% coverage

### Framework Exists but Not Populated ⚠️

10. Level 3 generation pipeline (3 examples, need 50-300)
11. Language bias variation (defined, not systematically varied)
12. Novel predicate control (framework exists, not tested)

### Not Implemented (Low Priority) 📝

13. Minimal support set enumeration (NP-complete, approximated by Crit*)
14. Full redundancy computation (uses heuristic)
15. Automated defeater discovery (requires ML/synthesis)

---

## Conclusion

### Current State

We have **excellent implementation of grounding** (8/10), but **weak coverage of novelty and belief revision** (4/10 and 3/10 respectively) due to lack of Level 3 instances in the development dataset.

### The Disconnect

**Paper's framing**: "Defeasible Reasoning as a Framework for Foundation Model Grounding, Novelty, and Belief Revision"

**Current deliverable**: "Defeasible Reasoning for Grounding (Levels 1-2), with Framework for Novelty and Belief Revision (Level 3)"

### Path Forward

**My recommendation**: Option 2 (Partial Implementation)

1. **This week**: Generate 20-30 Level 3 instances, run pilot
2. **Next week**: Update paper with preliminary Level 3 results
3. **Frame**: "Comprehensive grounding evaluation (374 instances) + proof-of-concept novelty/revision (20-30 instances)"
4. **Future work**: "Scaling Level 3 to production dataset"

This gives us:
- Honest accounting of all three objectives
- Empirical evidence for all three (even if limited for Levels 2-3)
- Publishable NeurIPS contribution
- Clear path for follow-up work

### Final Assessment

**Can we claim to address all three objectives?**
- Grounding: **YES** (comprehensive)
- Novelty: **PARTIALLY** (metric ready, instances needed)
- Belief Revision: **PARTIALLY** (framework validated, evaluation limited)

**Is this publishable?**
- **YES**, if we're honest about scope
- Grounding alone is a solid contribution
- Framework for novelty/revision is valuable even without full evaluation
- Need to align paper claims with actual deliverables

---

**Author**: Patrick Cooper  
**Date**: February 13, 2026  
**Purpose**: Relate implementation to paper's core objectives  
**Recommendation**: Generate Level 3 pilot dataset before submission
