# MVP Implementation: Avian Abduction Benchmark v0.1

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Timeline**: 3-4 weeks  
**Goal**: Prove DeFAb mathematics end-to-end with minimal scope

## Executive Summary

This MVP implements the complete author algorithm pipeline for a single knowledge base (Avian Biology), generating 25 validated instances across all 3 levels using pure formal encoding (M4) and exact match decoding (D1).

**Key Constraint**: Uses existing BLANC infrastructure (KnowledgeBase, Theory, Query APIs) with minimal extensions.

## Integration with Existing BLANC Infrastructure

### Existing Components (Phase 1-2)

✅ **Already Implemented**:
- `blanc.core.theory.Theory` - Theory representation
- `blanc.core.theory.Rule` - Rule with RuleType enum
- `blanc.core.theory.RuleType` - STRICT, DEFEASIBLE, DEFEATER, FACT
- `blanc.core.knowledge_base.KnowledgeBase` - Main KB interface
- `blanc.core.query.Query` - Query builder
- `blanc.core.result.ResultSet` - Result container
- `blanc.backends.base.KnowledgeBaseBackend` - Backend interface
- `blanc.backends.prolog.PrologBackend` - Prolog adapter (PySwip)
- `blanc.backends.asp.ASPBackend` - ASP adapter (Clingo)

### New Components (MVP)

🚧 **To Be Implemented**:
- `blanc.reasoning.defeasible` - Pure Python defeasible engine
- `blanc.author.*` - Author algorithm modules
- `blanc.codec.*` - Rendering/decoding (M4+D1 only)
- `blanc.experiments.*` - Evaluation pipeline

### Design Decision: Standalone Defeasible Engine

**Why not use existing Prolog/ASP backends?**

The existing backends are designed for their native semantics:
- **Prolog**: SLD resolution (definite clause logic)
- **ASP**: Stable model semantics

Defeasible logic has different semantics (team defeat, superiority relations) that don't map cleanly to either. We implement a **standalone pure Python defeasible reasoning engine** that:

1. Works directly with `Theory` objects
2. Implements Definition 7 (tagged proof procedure) exactly
3. Provides O(|R|·|F|) performance guarantee
4. Serves as reference implementation for paper

**Future**: Could implement defeasible logic encodings in ASP/Prolog as optimizations.

## Knowledge Base: Avian Biology

### File Structure

```
examples/knowledge_bases/avian_biology/
├── avian_biology.pl           # Full Prolog KB (for reference)
├── avian_biology_base.py      # Python version (for MVP)
├── README.md                  # Domain documentation
└── expected_results.json      # Gold standard derivations
```

### avian_biology_base.py

```python
"""
Avian Biology Knowledge Base
Domain: Bird classification and behavior
Purpose: MVP for DeFAb benchmark generation
"""

from blanc.core.theory import Theory, Rule, RuleType

def create_avian_biology_base() -> Theory:
    """
    Create base Avian Biology theory (D^-).
    
    This is the incomplete theory used for instance generation.
    Defeaters are in create_avian_biology_full().
    """
    theory = Theory()
    
    # =========================================================================
    # FACTS - Ground observations (depth 0)
    # =========================================================================
    
    # Bird individuals
    theory.add_fact("bird(tweety)")
    theory.add_fact("bird(polly)")
    theory.add_fact("bird(opus)")
    theory.add_fact("bird(chirpy)")
    theory.add_fact("bird(donald)")
    theory.add_fact("bird(daffy)")
    
    # Species classifications
    theory.add_fact("sparrow(tweety)")
    theory.add_fact("parrot(polly)")
    theory.add_fact("penguin(opus)")
    theory.add_fact("canary(chirpy)")
    theory.add_fact("duck(donald)")
    theory.add_fact("duck(daffy)")
    
    # Physical properties
    theory.add_fact("small(tweety)")
    theory.add_fact("small(chirpy)")
    theory.add_fact("large(opus)")
    theory.add_fact("large(donald)")
    
    # Environmental conditions
    theory.add_fact("aquatic_environment(opus)")
    theory.add_fact("aquatic_environment(donald)")
    theory.add_fact("aquatic_environment(daffy)")
    
    # Injuries
    theory.add_fact("wing_injury(chirpy)")
    
    # =========================================================================
    # STRICT RULES - Taxonomic facts (always true, depth 1)
    # =========================================================================
    
    # Taxonomy (these become bird(X) after grounding, but at higher depth)
    theory.add_rule(Rule(
        head="bird(X)",
        body=("sparrow(X)",),
        rule_type=RuleType.STRICT,
        label="s1"
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("parrot(X)",),
        rule_type=RuleType.STRICT,
        label="s2"
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("penguin(X)",),
        rule_type=RuleType.STRICT,
        label="s3"
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("canary(X)",),
        rule_type=RuleType.STRICT,
        label="s4"
    ))
    
    theory.add_rule(Rule(
        head="bird(X)",
        body=("duck(X)",),
        rule_type=RuleType.STRICT,
        label="s5"
    ))
    
    # Size inference
    theory.add_rule(Rule(
        head="small(X)",
        body=("sparrow(X)",),
        rule_type=RuleType.STRICT,
        label="s6"
    ))
    
    theory.add_rule(Rule(
        head="small(X)",
        body=("canary(X)",),
        rule_type=RuleType.STRICT,
        label="s7"
    ))
    
    # =========================================================================
    # DEFEASIBLE RULES - Behavioral defaults (depth 2)
    # =========================================================================
    
    # r1: Birds typically fly
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
        metadata={"description": "Birds typically fly"}
    ))
    
    # r2: Flying birds typically migrate
    theory.add_rule(Rule(
        head="migrates(X)",
        body=("bird(X)", "flies(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r2",
        metadata={"description": "Flying birds typically migrate"}
    ))
    
    # r3: Small birds typically sing
    theory.add_rule(Rule(
        head="sings(X)",
        body=("bird(X)", "small(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r3",
        metadata={"description": "Small birds typically sing"}
    ))
    
    # r4: Aquatic birds typically swim
    theory.add_rule(Rule(
        head="swims(X)",
        body=("bird(X)", "aquatic_environment(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r4",
        metadata={"description": "Aquatic birds typically swim"}
    ))
    
    # r5: Large birds are typically predators
    theory.add_rule(Rule(
        head="predator(X)",
        body=("bird(X)", "large(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r5",
        metadata={"description": "Large birds are typically predators"}
    ))
    
    return theory


def create_avian_biology_full() -> Theory:
    """
    Create complete Avian Biology theory (D^full).
    
    Includes defeaters that will be ablated for Level 3 instances.
    """
    theory = create_avian_biology_base()
    
    # =========================================================================
    # DEFEATERS - Exceptions to defaults
    # =========================================================================
    
    # d1: Penguins don't fly (flightless birds)
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d1",
        metadata={"description": "Penguins are flightless"}
    ))
    theory.add_superiority("d1", "r1")
    
    # d2: Injured birds may not fly
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("wing_injury(X)",),
        rule_type=RuleType.DEFEATER,
        label="d2",
        metadata={"description": "Wing injury prevents flight"}
    ))
    theory.add_superiority("d2", "r1")
    
    # d3: Ducks don't migrate (resident waterfowl)
    theory.add_rule(Rule(
        head="~migrates(X)",
        body=("duck(X)",),
        rule_type=RuleType.DEFEATER,
        label="d3",
        metadata={"description": "Ducks are non-migratory"}
    ))
    theory.add_superiority("d3", "r2")
    
    # d4: Parrots are not predators (despite size)
    theory.add_rule(Rule(
        head="~predator(X)",
        body=("parrot(X)",),
        rule_type=RuleType.DEFEATER,
        label="d4",
        metadata={"description": "Parrots are herbivores"}
    ))
    theory.add_superiority("d4", "r5")
    
    return theory
```

### Expected Derivations (Gold Standard)

```python
# From D_base (without defeaters)
EXPECTED_DERIVABLE_BASE = {
    # Depth 0: Facts
    "bird(tweety)", "sparrow(tweety)", "small(tweety)",
    "bird(polly)", "parrot(polly)",
    "bird(opus)", "penguin(opus)", "large(opus)", "aquatic_environment(opus)",
    "bird(chirpy)", "canary(chirpy)", "small(chirpy)", "wing_injury(chirpy)",
    "bird(donald)", "duck(donald)", "large(donald)", "aquatic_environment(donald)",
    "bird(daffy)", "duck(daffy)", "aquatic_environment(daffy)",
    
    # Depth 1: Direct strict inference
    # (already in facts, but also derivable via strict rules)
    
    # Depth 2: Defeasible inference
    "flies(tweety)",      # r1: bird(tweety) => flies(tweety)
    "flies(polly)",       # r1: bird(polly) => flies(polly)
    "flies(opus)",        # r1: bird(opus) => flies(opus) - WILL BE DEFEATED
    "flies(chirpy)",      # r1: bird(chirpy) => flies(chirpy) - WILL BE DEFEATED
    "flies(donald)",      # r1: bird(donald) => flies(donald)
    "flies(daffy)",       # r1: bird(daffy) => flies(daffy)
    
    "migrates(tweety)",   # r2: bird(tweety), flies(tweety) => migrates(tweety)
    "migrates(polly)",    # r2: bird(polly), flies(polly) => migrates(polly)
    "migrates(donald)",   # r2: bird(donald), flies(donald) => migrates(donald) - WILL BE DEFEATED
    "migrates(daffy)",    # r2: bird(daffy), flies(daffy) => migrates(daffy) - WILL BE DEFEATED
    
    "sings(tweety)",      # r3: bird(tweety), small(tweety) => sings(tweety)
    "sings(chirpy)",      # r3: bird(chirpy), small(chirpy) => sings(chirpy)
    
    "swims(opus)",        # r4: bird(opus), aquatic(opus) => swims(opus)
    "swims(donald)",      # r4: bird(donald), aquatic(donald) => swims(donald)
    "swims(daffy)",       # r4: bird(daffy), aquatic(daffy) => swims(daffy)
    
    "predator(opus)",     # r5: bird(opus), large(opus) => predator(opus)
    "predator(donald)",   # r5: bird(donald), large(donald) => predator(donald)
}

# From D_full (with defeaters)
EXPECTED_DERIVABLE_FULL = {
    # All from BASE except:
    # - NOT "flies(opus)" (defeated by d1: penguin)
    # - NOT "flies(chirpy)" (defeated by d2: wing_injury)
    # - NOT "migrates(donald)" (defeated by d3: duck)
    # - NOT "migrates(daffy)" (defeated by d3: duck)
    # - NOT "predator(polly)" - wait, polly is not large, so never derived
}
```

## Implementation Plan

### Week 1: Defeasible Reasoning Engine

**Deliverable**: Pure Python defeasible logic engine

**Files**:

#### 1. `src/blanc/reasoning/__init__.py`

```python
"""Reasoning engines for different logical frameworks."""

from blanc.reasoning.defeasible import (
    DefeasibleEngine,
    defeasible_provable,
    strictly_provable,
)

__all__ = [
    "DefeasibleEngine",
    "defeasible_provable",
    "strictly_provable",
]
```

#### 2. `src/blanc/reasoning/defeasible.py`

```python
"""
Pure Python defeasible reasoning engine.

Implements Definition 7 (tagged proof procedure) from paper.
Complexity: O(|R| · |F|) per Theorem 11.
"""

from dataclasses import dataclass
from typing import Set, Dict, List, Optional
from blanc.core.theory import Theory, Rule, RuleType


@dataclass
class ProofTag:
    """Tagged proof step (+Δ, -Δ, +∂, -∂)."""
    literal: str
    tag: str  # "definite", "defeasible"
    polarity: bool  # True for +, False for -


class DefeasibleEngine:
    """
    Defeasible reasoning engine.
    
    Implements tagged proof procedure from Definition 7.
    """
    
    def __init__(self, theory: Theory):
        """
        Initialize engine with theory.
        
        Args:
            theory: Defeasible theory to reason over
        """
        self.theory = theory
        self._proof_cache: Dict[str, Optional[ProofTag]] = {}
    
    def is_defeasibly_provable(self, literal: str) -> bool:
        """
        Check if literal is defeasibly provable (D ⊢∂ q).
        
        Definition 7, line 548-561 in paper.
        
        +∂q holds iff:
        (1) +Δq; OR
        (2) All of:
            (a) -Δ¬q
            (b) ∃r ∈ Rd: C(r) = q and ∀a ∈ A(r): +∂a
            (c) ∀s ∈ Rd ∪ Rdf: C(s) = ¬q ⟹
                  (i) ∃a ∈ A(s): -∂a OR
                  (ii) ∃t ∈ Rd: C(t) = q, ∀a ∈ A(t): +∂a, t ≻ s
        
        Args:
            literal: Literal to check (e.g., "flies(tweety)")
        
        Returns:
            True if defeasibly provable, False otherwise
        
        Complexity: O(|R| · |F|) per Theorem 11
        """
        # Check cache
        if literal in self._proof_cache:
            tag = self._proof_cache[literal]
            return tag is not None and tag.tag == "defeasible" and tag.polarity
        
        # (1) Check if definitely provable
        if self.is_definitely_provable(literal):
            self._proof_cache[literal] = ProofTag(literal, "defeasible", True)
            return True
        
        # (2a) Check complement not definitely provable
        complement = self._complement(literal)
        if self.is_definitely_provable(complement):
            self._proof_cache[literal] = ProofTag(literal, "defeasible", False)
            return False
        
        # (2b) Find applicable defeasible rule for literal
        applicable_rules = self._find_applicable_defeasible_rules(literal)
        if not applicable_rules:
            self._proof_cache[literal] = ProofTag(literal, "defeasible", False)
            return False
        
        # (2c) Team defeat: check all attacking rules
        attacking_rules = self._find_attacking_rules(literal)
        for attack in attacking_rules:
            if not self._is_neutralized(attack, applicable_rules):
                # Attack not neutralized - literal not defeasibly provable
                self._proof_cache[literal] = ProofTag(literal, "defeasible", False)
                return False
        
        # All attacks neutralized - literal is defeasibly provable
        self._proof_cache[literal] = ProofTag(literal, "defeasible", True)
        return True
    
    def is_definitely_provable(self, literal: str) -> bool:
        """
        Check if literal is definitely provable (D ⊢Δ q).
        
        Uses only facts F and strict rules Rs.
        
        Args:
            literal: Literal to check
        
        Returns:
            True if definitely provable
        """
        # Base case: literal is a fact
        if literal in self.theory.facts:
            return True
        
        # Recursive case: find strict rule with this head
        for rule in self.theory.get_rules_by_type(RuleType.STRICT):
            if self._unify(rule.head, literal):
                # Check if all body literals are definitely provable
                if all(self.is_definitely_provable(b) for b in rule.body):
                    return True
        
        return False
    
    def expectation_set(self) -> Set[str]:
        """
        Compute Exp(D) = {q | D ⊢∂ q}.
        
        Definition 11, line 630.
        
        Returns:
            Set of all defeasibly derivable ground literals
        """
        expectations = set()
        
        # Enumerate Herbrand base
        herbrand_base = self._compute_herbrand_base()
        
        for literal in herbrand_base:
            if self.is_defeasibly_provable(literal):
                expectations.add(literal)
        
        return expectations
    
    def _find_applicable_defeasible_rules(self, literal: str) -> List[Rule]:
        """Find defeasible rules whose head unifies with literal and body is provable."""
        applicable = []
        
        for rule in self.theory.get_rules_by_type(RuleType.DEFEASIBLE):
            if self._unify(rule.head, literal):
                # Check if all body literals are defeasibly provable
                if all(self.is_defeasibly_provable(b) for b in rule.body):
                    applicable.append(rule)
        
        return applicable
    
    def _find_attacking_rules(self, literal: str) -> List[Rule]:
        """Find rules that attack literal (conclude its complement)."""
        complement = self._complement(literal)
        attacking = []
        
        # Check defeasible rules
        for rule in self.theory.get_rules_by_type(RuleType.DEFEASIBLE):
            if self._unify(rule.head, complement):
                attacking.append(rule)
        
        # Check defeaters
        for rule in self.theory.get_rules_by_type(RuleType.DEFEATER):
            if self._unify(rule.head, complement):
                attacking.append(rule)
        
        return attacking
    
    def _is_neutralized(self, attack: Rule, defenders: List[Rule]) -> bool:
        """
        Check if attacking rule is neutralized.
        
        An attack is neutralized if:
        (i) It's inapplicable (body not provable), OR
        (ii) It's overridden by superior defending rule
        """
        # (i) Check if attack is applicable
        if not all(self.is_defeasibly_provable(b) for b in attack.body):
            return True  # Inapplicable
        
        # (ii) Check if overridden by superior defender
        for defender in defenders:
            if self._is_superior(defender, attack):
                return True  # Overridden
        
        return False  # Not neutralized
    
    def _is_superior(self, rule1: Rule, rule2: Rule) -> bool:
        """Check if rule1 > rule2 in superiority relation."""
        if rule1.label and rule2.label:
            superiors = self.theory.superiority.get(rule1.label, set())
            return rule2.label in superiors
        return False
    
    def _complement(self, literal: str) -> str:
        """Compute complement: p ↦ ~p, ~p ↦ p."""
        if literal.startswith("~"):
            return literal[1:]
        else:
            return f"~{literal}"
    
    def _unify(self, pattern: str, literal: str) -> bool:
        """
        Simple unification check.
        
        For MVP: exact match or variable matching.
        Full unification deferred to later.
        """
        # Exact match
        if pattern == literal:
            return True
        
        # Variable matching (simplified)
        # Pattern has variables (uppercase), literal is ground
        # For MVP: just check predicate matches
        pattern_pred = pattern.split("(")[0] if "(" in pattern else pattern
        literal_pred = literal.split("(")[0] if "(" in literal else literal
        
        return pattern_pred == literal_pred
    
    def _compute_herbrand_base(self) -> Set[str]:
        """
        Compute Herbrand base (all ground atoms).
        
        For MVP: extract from facts and instantiate rules.
        Full implementation: proper grounding.
        """
        herbrand_base = set()
        
        # Add all facts
        herbrand_base.update(self.theory.facts)
        
        # Add instantiated rule heads (simplified)
        # For MVP: just add the literals we care about
        # Full implementation: proper Herbrand base construction
        
        return herbrand_base


# Convenience functions

def defeasible_provable(theory: Theory, literal: str) -> bool:
    """Check if theory defeasibly proves literal."""
    engine = DefeasibleEngine(theory)
    return engine.is_defeasibly_provable(literal)


def strictly_provable(theory: Theory, literal: str) -> bool:
    """Check if theory definitely proves literal."""
    engine = DefeasibleEngine(theory)
    return engine.is_definitely_provable(literal)
```

**Tests**: `tests/reasoning/test_defeasible.py`

```python
"""Tests for defeasible reasoning engine."""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable, strictly_provable
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
    create_avian_biology_full,
)


def test_tweety_basic():
    """Classic Tweety example."""
    theory = Theory()
    theory.add_fact("bird(tweety)")
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    ))
    
    assert defeasible_provable(theory, "bird(tweety)")
    assert defeasible_provable(theory, "flies(tweety)")


def test_tweety_with_defeater():
    """Tweety with penguin defeater."""
    theory = Theory()
    theory.add_fact("bird(tweety)")
    theory.add_fact("penguin(tweety)")
    
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    ))
    
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d1"
    ))
    theory.add_superiority("d1", "r1")
    
    assert defeasible_provable(theory, "bird(tweety)")
    assert not defeasible_provable(theory, "flies(tweety)")  # Defeated!


def test_avian_biology_base():
    """Test Avian Biology base theory."""
    theory = create_avian_biology_base()
    
    # Facts should be provable
    assert defeasible_provable(theory, "bird(tweety)")
    assert defeasible_provable(theory, "sparrow(tweety)")
    
    # Defeasible conclusions should be provable
    assert defeasible_provable(theory, "flies(tweety)")
    assert defeasible_provable(theory, "flies(opus)")  # No defeater yet!


def test_avian_biology_full():
    """Test Avian Biology full theory with defeaters."""
    theory = create_avian_biology_full()
    
    # Tweety still flies (no defeater)
    assert defeasible_provable(theory, "flies(tweety)")
    
    # Opus doesn't fly (penguin defeater)
    assert not defeasible_provable(theory, "flies(opus)")
    
    # Chirpy doesn't fly (wing injury defeater)
    assert not defeasible_provable(theory, "flies(chirpy)")


def test_proposition_2_definite_implies_defeasible():
    """Proposition 2: D ⊢Δ q ⟹ D ⊢∂ q."""
    theory = Theory()
    theory.add_fact("p")
    theory.add_rule(Rule(
        head="q",
        body=("p",),
        rule_type=RuleType.STRICT
    ))
    
    # If definitely provable, then defeasibly provable
    assert strictly_provable(theory, "q")
    assert defeasible_provable(theory, "q")


@pytest.mark.benchmark
def test_theorem_11_complexity():
    """Theorem 11: Defeasible derivation in O(|R| · |F|)."""
    import time
    
    # Create theories of increasing size
    sizes = [10, 20, 40, 80]
    times = []
    
    for n in sizes:
        theory = Theory()
        # Add n facts
        for i in range(n):
            theory.add_fact(f"p{i}")
        
        # Add n rules
        for i in range(n):
            theory.add_rule(Rule(
                head=f"q{i}",
                body=(f"p{i}",),
                rule_type=RuleType.DEFEASIBLE
            ))
        
        # Time defeasible query
        start = time.perf_counter()
        for i in range(n):
            defeasible_provable(theory, f"q{i}")
        elapsed = time.perf_counter() - start
        
        times.append(elapsed)
        print(f"n={n}: {elapsed:.4f}s")
    
    # Verify roughly linear scaling
    # (times should grow roughly as n²/n = n)
    assert times[-1] / times[0] < (sizes[-1] / sizes[0]) * 2
```

### Week 2: Conversion & Criticality

**Files to implement**: 
- `src/blanc/author/conversion.py`
- `src/blanc/author/support.py`
- `src/blanc/generation/partition.py`

**(Implementation details in separate sections to keep this document manageable)**

### Week 3: Instance Generation & Codec

**Files to implement**:
- `src/blanc/author/generation.py`
- `src/blanc/author/level3.py`
- `src/blanc/codec/encoder.py`
- `src/blanc/codec/decoder.py`

### Week 4: Pipeline & Evaluation

**Files to implement**:
- `src/blanc/author/pipeline.py`
- `src/blanc/experiments/dataset.py`
- `src/blanc/experiments/evaluation.py`

## Extending Existing Interfaces

### Minimal Extensions Needed

#### 1. Add `DerivationTree` to `result.py`

```python
# In src/blanc/core/result.py

@dataclass
class DerivationNode:
    """Node in derivation tree."""
    literal: str
    rule: Optional[Rule]
    children: List['DerivationNode']


@dataclass
class DerivationTree:
    """AND-OR derivation tree."""
    root: DerivationNode
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        ...
```

#### 2. Add helper to `Theory` class

```python
# In src/blanc/core/theory.py

class Theory:
    # ... existing methods ...
    
    def ground(self, constants: Set[str]) -> 'Theory':
        """
        Ground theory over constants.
        
        For MVP: simple instantiation.
        For full: proper Herbrand grounding.
        """
        grounded = Theory()
        # Ground each rule...
        return grounded
```

## Dataset Generation Workflow

### End-to-End Example

```python
from blanc.author.pipeline import DatasetGenerator
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
    create_avian_biology_full,
)

# Create generator
generator = DatasetGenerator(
    theory_base=create_avian_biology_base(),
    theory_full=create_avian_biology_full(),
    partition_function="rule",  # κ_rule
    modality="M4",  # Pure formal
    decoder="D1",   # Exact match
)

# Generate dataset
dataset = generator.generate_dataset(
    level1_count=10,
    level2_count=10,
    level3_count=5,
    distractor_strategy="syntactic",
    k_distractors=5,
)

# Validate
validation_report = dataset.validate()
print(f"Instances: {len(dataset.instances)}")
print(f"Valid: {validation_report['valid_count']}/{len(dataset.instances)}")
print(f"Round-trip accuracy: {validation_report['round_trip_accuracy']:.2%}")

# Save
dataset.save("avian_abduction_v0.1.json")

# Statistics
stats = dataset.statistics()
print(stats)
```

## Success Criteria

### Must-Have (Week 4 Completion)

- [ ] **25 valid instances generated**
  - 10 Level 1 (fact completion)
  - 10 Level 2 (rule abduction)
  - 5 Level 3 (defeater abduction)

- [ ] **All instances validated**
  - D^- ⊬∂ q (ablation removes derivability)
  - D^- ∪ {h*} ⊢∂ q (gold restores)
  - D^- ∪ {d} ⊬∂ q (distractors don't restore)

- [ ] **100% round-trip accuracy** (M4 + D1)

- [ ] **Propositions verified**
  - Proposition 1: Conservative conversion
  - Proposition 2: Definite ⟹ defeasible
  - Proposition 4: Crit* ⊆ Crit

- [ ] **Theorem 11 verified**
  - O(|R|·|F|) complexity measured

- [ ] **Tests passing**
  - >90% code coverage
  - All unit tests pass
  - All integration tests pass

### Should-Have

- [ ] Level 3 conservativity working
- [ ] Performance: <1 minute for 25 instances
- [ ] Documentation complete
- [ ] Visualization of sample derivation trees

### Nice-to-Have

- [ ] Multiple distractor strategies tested
- [ ] Yield analysis (Proposition 3)
- [ ] Comparison with hand-crafted instances

## Deliverables

### Code (5000 lines)

- `src/blanc/reasoning/`: 800 lines
- `src/blanc/author/`: 1800 lines  
- `src/blanc/generation/`: 400 lines
- `src/blanc/codec/`: 500 lines
- `src/blanc/experiments/`: 500 lines
- `tests/`: 1000 lines
- `examples/knowledge_bases/avian_biology/`: 300 lines

### Dataset

**Avian Abduction Benchmark v0.1**:
- 25 instances (JSON format)
- Validation report
- Statistics summary
- Example instances (one per level)

### Documentation

- `MVP_RESULTS.md`: Findings and validation
- `examples/knowledge_bases/avian_biology/README.md`: KB documentation
- Updated `README.md` with MVP status

## Scaling to Full DeFAb

### After MVP Success

**Phase 2A: Additional Modalities** (1 week)
- Add M3 (annotated formal)
- Add D2 (template extraction)
- Target: >95% round-trip

**Phase 2B: Additional KBs** (1 week)
- Medical diagnosis
- Family relations
- Generate 100 instances each

**Phase 2C: Scale Generation** (1 week)
- Remaining partition functions
- 1000+ instances

**Phase 3: Full Benchmark** (2-3 weeks)
- All modalities (M1-M4)
- All decoders (D1-D3)
- LLM evaluation
- Submission-ready

### If MVP Reveals Issues

**Defeasible reasoning slow**:
- Profile and optimize
- Consider DePYsible/silkie library
- Implement caching aggressively

**Level 3 too complex**:
- Focus on L1-L2 for MVP
- Simplify defeaters
- Hand-craft Level 3 instances

**Codec issues**:
- Stay with M4+D1
- Defer other modalities

## Next Steps

1. **Review this design** - Verify compatibility with existing code
2. **Create directory structure** - Set up new modules
3. **Begin Week 1** - Implement `reasoning/defeasible.py`
4. **Daily testing** - Run tests continuously
5. **Weekly milestones** - Validate at end of each week

## Questions for Review

1. **Defeasible engine approach**: Standalone Python vs. encoding in ASP/Prolog?
   - **Decision**: Standalone for MVP, encodings later

2. **Theory grounding**: Full Herbrand or simplified?
   - **Decision**: Simplified for MVP (function-free, small domain)

3. **Level 3 complexity**: Hand-craft defeaters or generate?
   - **Decision**: Hand-craft 4 defeaters, validate pipeline

4. **Testing depth**: How comprehensive for MVP?
   - **Decision**: Core propositions + example instances

**Shall I proceed with implementing Week 1 (defeasible reasoning engine)?**

---

**Author**: Patrick Cooper  
**Date**: 2026-02-11  
**Status**: Design ready for implementation
