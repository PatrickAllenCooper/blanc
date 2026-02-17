"""
author.py - The Author Algorithm

This file contains the essential mathematics of the defeasible abduction
framework as specified in "Defeasible Reasoning as a Framework for Foundation
Model Grounding, Novelty, and Belief Revision" (NeurIPS 2026).

Author: Patrick Cooper
Date: 2026-02-11

CRITICAL: Every function in this file maps 1:1 to a numbered Definition or
Proposition in paper/paper.tex. This is the REFERENCE IMPLEMENTATION.

Organization:
  1. Definite Logic Programs (§A.1, Defs 1-5)
  2. Defeasible Theories (§A.2, Defs 6-7)
  3. Conversion (§A.3, Defs 8-10)
  4. Support & Criticality (§A.4, Defs 17-20)
  5. Instance Generation (§A.4, Defs 20-22)
  6. Level 3: Defeater Abduction (§A.5, Defs 11-16)
  7. Metrics (Defs 33-35)

Usage:
  This file is primarily a SPECIFICATION. Concrete implementations live in:
  - author/conversion.py
  - author/support.py
  - author/generation.py
  - author/level3.py
  - author/metrics.py
  
  Use this file to:
  - Understand the mathematical structure
  - Verify correctness of implementations
  - Trace paper definitions to code
"""

from dataclasses import dataclass, field
from typing import Set, List, Tuple, Optional, Callable, Dict, Any
from enum import Enum

# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

# Element of a defeasible theory (fact or rule)
Element = 'Rule | str'

# Partition function: maps rules to {s, d} (strict or defeasible)
PartitionFunction = Callable[['Rule'], str]


# =============================================================================
# SECTION 1: DEFINITE LOGIC PROGRAMS (§A.1, Definitions 1-5)
# Paper: lines 485-531
# =============================================================================

@dataclass(frozen=True)
class Signature:
    """
    Definition 1 (line 485): First-order signature Σ = (C, F, P).
    
    Attributes:
        constants: C - finite set of constants
        function_symbols: F → arity - finite set of function symbols
        predicate_symbols: P → arity - finite set of predicate symbols
    
    The Herbrand universe HU(Σ) is the set of all ground terms.
    The Herbrand base HB(Σ) is the set of all ground atoms.
    
    When F = ∅, Σ is function-free (datalog case) and HU(Σ) = C is finite.
    """
    constants: Set[str]
    function_symbols: Dict[str, int]  # name → arity
    predicate_symbols: Dict[str, int]  # name → arity
    
    def is_function_free(self) -> bool:
        """Function-free (datalog) case: F = ∅."""
        return len(self.function_symbols) == 0
    
    def herbrand_universe(self) -> Set[str]:
        """
        HU(Σ) = C ∪ {f(t1,...,t_ar(f)) | f ∈ F, ti ∈ HU(Σ)}.
        
        For function-free: HU(Σ) = C (finite).
        For full first-order: recursive construction (potentially infinite).
        """
        if self.is_function_free():
            return self.constants.copy()
        else:
            raise NotImplementedError(
                "Full first-order grounding is potentially infinite. "
                "Use function-free (datalog) fragment for tractability."
            )
    
    def herbrand_base(self) -> Set[str]:
        """
        HB(Σ) = {p(t1,...,t_ar(p)) | p ∈ P, ti ∈ HU(Σ)}.
        
        For function-free theories with |C| = n and max predicate arity k:
        |HB(Σ)| ≤ |P| · n^k (polynomial).
        """
        raise NotImplementedError("See implementation in author/conversion.py")


@dataclass
class Rule:
    """
    Logical rule: h :- b1, ..., bn (n ≥ 0).
    
    When n = 0, this is a fact.
    When n > 0, this is a rule with head h and body {b1, ..., bn}.
    
    rule_type distinguishes strict (→), defeasible (⇒), defeater (↝).
    """
    head: str
    body: Tuple[str, ...] = field(default_factory=tuple)
    rule_type: 'RuleType' = None  # Filled in by RuleType enum
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_fact(self) -> bool:
        """A rule is a fact iff it has empty body."""
        return len(self.body) == 0


class RuleType(Enum):
    """Type of logical rule in defeasible logic."""
    FACT = "fact"          # Ground fact (no body)
    STRICT = "strict"      # Classical deductive rule (→)
    DEFEASIBLE = "defeasible"  # Defeasible rule (⇒)
    DEFEATER = "defeater"  # Defeater rule (↝)


class DefiniteLogicProgram:
    """
    Definition 2 (line 503): Definite logic program Π over signature Σ.
    
    A finite set of definite clauses h :- b1, ..., bn (n ≥ 0).
    
    Semantics given by least Herbrand model M_Π = lfp(T_Π).
    
    Key property (monotonicity): Π ⊆ Π' ⟹ M_Π ⊆ M_Π'.
    """
    
    def __init__(self, pi: Set[Rule], sigma: Signature):
        """
        Args:
            pi: Set of definite clauses (facts and rules)
            sigma: Signature over which program is defined
        """
        self.pi = pi
        self.sigma = sigma
    
    def immediate_consequence(self, interpretation: Set[str]) -> Set[str]:
        """
        Definition 3 (line 514): Immediate consequence operator T_Π.
        
        T_Π(I) = {hθ | (h :- b1, ..., bn) ∈ Π, θ: V → HU(Σ), 
                       {b1θ, ..., bnθ} ⊆ I}
        
        Complexity: O(|Π| · |HU|^k) where k is max clause arity.
        For ground programs: O(|Π| · |I|).
        """
        raise NotImplementedError("See implementation in author/conversion.py")
    
    def least_herbrand_model(self) -> Set[str]:
        """
        Definition 4 (line 521): Least Herbrand model M_Π = lfp(T_Π).
        
        M_Π = ⋃_{i=0}^∞ T_Π^i(∅)
        
        Computed via fixpoint iteration: T_Π^0(∅) = ∅, T_Π^{i+1} = T_Π(T_Π^i).
        Terminates in at most |HB(Σ)| iterations.
        
        Returns:
            Set of all ground atoms derivable from Π.
        """
        raise NotImplementedError("See implementation in author/conversion.py")
    
    def sld_derivable(self, q: str) -> bool:
        """
        Definition 5 (line 529): SLD-derivability Π ⊢_SLD q.
        
        For definite programs: Π ⊢_SLD q ⟺ q ∈ M_Π.
        
        In practice: Use Prolog backend (existing).
        """
        raise NotImplementedError("Use backends/prolog.py (existing)")


# =============================================================================
# SECTION 2: DEFEASIBLE THEORIES (§A.2, Definitions 6-7)
# Paper: lines 534-565
# =============================================================================

@dataclass
class DefeasibleTheory:
    """
    Definition 6 (line 536): Defeasible theory D = (F, Rs, Rd, Rdf, ≻).
    
    Components:
        F: Facts (⊆ HB)
        Rs: Strict rules (b1,...,bn → h)
        Rd: Defeasible rules (b1,...,bn ⇒ h)
        Rdf: Defeaters (b1,...,bn ↝ ¬h)
        superiority: ≻ - acyclic superiority relation on Rd ∪ Rdf
    
    Size: |D| = |F| + |R| where R = Rs ∪ Rd ∪ Rdf.
    """
    F: Set[str]  # Facts
    Rs: Set[Rule]  # Strict rules
    Rd: Set[Rule]  # Defeasible rules
    Rdf: Set[Rule]  # Defeaters
    superiority: Dict[str, Set[str]]  # rule_label → {inferior_labels}
    
    def size(self) -> int:
        """|D| = |F| + |R|."""
        return len(self.F) + len(self.Rs) + len(self.Rd) + len(self.Rdf)
    
    def all_rules(self) -> Set[Rule]:
        """R = Rs ∪ Rd ∪ Rdf."""
        return self.Rs | self.Rd | self.Rdf


def defeasible_provable(D: DefeasibleTheory, q: str) -> bool:
    """
    Definition 7 (line 548): Defeasible provability D ⊢∂ q.
    
    Implements tagged proof procedure with two provability relations:
    - +Δq: definite provability (facts + strict rules)
    - +∂q: defeasible provability (with team defeat)
    
    +∂q holds iff:
    (1) +Δq; OR
    (2) All of:
        (a) -Δ¬q (complement not definitely provable)
        (b) ∃r ∈ Rd: C(r) = q and ∀a ∈ A(r): +∂a (applicable rule exists)
        (c) ∀s ∈ Rd ∪ Rdf: C(s) = ¬q ⟹ 
              (i) ∃a ∈ A(s): -∂a OR
              (ii) ∃t ∈ Rd: C(t) = q, ∀a ∈ A(t): +∂a, t ≻ s
    
    Condition (2c) is TEAM DEFEAT: every attacking rule must be individually
    neutralized (inapplicable or overridden).
    
    Complexity: O(|R| · |F|) per Theorem 11 (line 775).
    
    Implementation: See reasoning/defeasible.py.
    """
    raise NotImplementedError("See implementation in reasoning/defeasible.py")


def strictly_provable(D: DefeasibleTheory, q: str) -> bool:
    """
    Definite provability D ⊢Δ q (Definition 7 condition 1).
    
    Uses only facts F and strict rules Rs.
    Equivalent to least Herbrand model of (F, Rs).
    
    Proposition 2 (line 751): If D ⊢Δ q then D ⊢∂ q.
    """
    raise NotImplementedError("See implementation in reasoning/defeasible.py")


# =============================================================================
# SECTION 3: CONVERSION (§A.3, Definitions 8-10)
# Paper: lines 566-600
# =============================================================================

def phi_kappa(pi: DefiniteLogicProgram, kappa: PartitionFunction) -> DefeasibleTheory:
    """
    Definition 9 (line 572): Defeasible conversion φ_κ(Π).
    
    Given partition κ: Π → {s, d}, construct D = (F_κ, Rs^κ, Rd^κ, ∅, ∅):
    
    F_κ = {h | (h :-) ∈ Π, κ(h :-) = s}
    Rs^κ = {b1,...,bn → h | (h :- b1,...,bn) ∈ Π, n > 0, κ(...) = s}
    Rd^κ = {b1,...,bn ⇒ h | (h :- b1,...,bn) ∈ Π, κ(...) = d}
          ∪ {⊤ ⇒ h | (h :-) ∈ Π, κ(h :-) = d}
    
    The conversion makes epistemic commitments explicit:
    - Every conclusion has a traceable support set
    - Every default is revisable
    - Every element's criticality is computable
    
    Proposition 1 (line 743): When κ ≡ s (all strict),
    q ∈ M_Π ⟺ D_κ ⊢Δ q (conservative conversion).
    
    Implementation: See author/conversion.py.
    """
    raise NotImplementedError("See implementation in author/conversion.py")


def partition_leaf(rule: Rule) -> str:
    """Definition 10(i): κ_leaf - facts defeasible, rules strict."""
    return 'd' if rule.is_fact() else 's'


def partition_rule(rule: Rule) -> str:
    """Definition 10(ii): κ_rule - rules defeasible, facts strict."""
    return 's' if rule.is_fact() else 'd'


def partition_depth(k: int, dependency_depths: Dict[str, int]) -> PartitionFunction:
    """
    Definition 10(iii): κ_depth(k) - clauses at depth ≤k strict.
    
    Requires dependency graph (Definition 8, line 582):
    G_Π = (P, E) where (p, q) ∈ E iff some clause has head predicate q
    and body predicate p.
    
    depth(p) = longest path from any source to p.
    """
    def partition(rule: Rule) -> str:
        # Extract head predicate
        head_pred = extract_predicate(rule.head)
        depth = dependency_depths.get(head_pred, 0)
        return 's' if depth <= k else 'd'
    return partition


def partition_random(delta: float, seed: Optional[int] = None) -> PartitionFunction:
    """
    Definition 10(iv): κ_rand(δ) - each clause defeasible with prob δ.
    
    Used to study yield as function of defeasibility ratio.
    Proposition 3 (line 759): E[Y(κ_rand(δ), Q)] non-decreasing in δ.
    """
    import random
    if seed is not None:
        random.seed(seed)
    
    def partition(rule: Rule) -> str:
        return 'd' if random.random() < delta else 's'
    
    return partition


def defeasibility_ratio(kappa: PartitionFunction, pi: DefiniteLogicProgram) -> float:
    """
    Definition 9 (line 597): δ(κ) = |{c ∈ Π | κ(c) = d}| / |Π|.
    
    Fraction of clauses classified as defeasible.
    Controls the "revisability surface" of the converted theory.
    """
    defeasible_count = sum(1 for c in pi.pi if kappa(c) == 'd')
    return defeasible_count / len(pi.pi) if pi.pi else 0.0


# =============================================================================
# SECTION 4: SUPPORT & CRITICALITY (§A.4, Definitions 17-20)
# Paper: lines 601-627
# =============================================================================

def support_sets(D: DefeasibleTheory, q: str) -> Set[frozenset]:
    """
    Definition 17 (line 603): Supp(D, q) = all minimal support sets.
    
    A support set S ⊆ (F ∪ Rs ∪ Rd) is minimal such that:
    (S ∩ F, S ∩ Rs, S ∩ Rd, ∅, ≻|_S) ⊢∂ q
    
    Computing minimal support is NP-complete (Complexity Table, line 294).
    
    NOTE: We do NOT use this for instance generation (too expensive).
    Instead we use Crit* (polynomial).
    """
    raise NotImplementedError(
        "Computing minimal support is NP-complete. "
        "Use full_theory_criticality (polynomial) instead."
    )


def full_theory_criticality(D: DefeasibleTheory, q: str) -> Set[Element]:
    """
    Definition 18 (line 607): Crit*(D, q) = {e ∈ F ∪ Rs ∪ Rd | D \ {e} ⊬∂ q}.
    
    Set of elements whose removal blocks derivation of q.
    
    Complexity: O(|D|² · |F|) per line 292.
    Algorithm:
    1. For each element e ∈ F ∪ Rs ∪ Rd:
    2.   Form D' = D \ {e}
    3.   Test if D' ⊢∂ q
    4.   If not, e ∈ Crit*(D, q)
    
    This is the WORKHORSE for instance generation.
    Polynomial time makes ablation tractable.
    
    Proposition 4 (line 767): Crit*(D, q) ⊆ Crit(D, q) (possibly strict).
    
    Implementation: See author/support.py.
    """
    raise NotImplementedError("See implementation in author/support.py")


def redundancy_degree(e: Element, D: DefeasibleTheory, q: str) -> int:
    """
    Definition 19 (line 611): red(e, D, q) = |{S ∈ Supp(D,q) | e ∉ S}|.
    
    Number of support sets that do NOT contain e.
    If red(e, D, q) = 0, then e ∈ Crit*(D, q).
    
    Measures redundancy: higher redundancy ⟹ e less critical.
    """
    raise NotImplementedError("See implementation in author/support.py")


def defeasible_yield(kappa: PartitionFunction, Q: Set[str], 
                     pi: DefiniteLogicProgram) -> int:
    """
    Definition 22 (line 623): Y(κ, Q) = Σ_{q∈Q} |Crit*(D_κ, q)|.
    
    Total number of ablatable elements across target set Q.
    
    Used to measure instance generation capacity:
    - Higher yield ⟹ more instances can be generated
    - Proposition 3: Yield increases with defeasibility ratio δ
    
    Implementation: See author/metrics.py.
    """
    raise NotImplementedError("See implementation in author/metrics.py")


# =============================================================================
# SECTION 5: INSTANCE GENERATION (Definitions 20-21)
# Paper: lines 615-627
# =============================================================================

@dataclass
class AbductiveInstance:
    """
    Definition 20 (line 615): Abductive instance (D^-, q, H_cand, H*).
    
    Components:
        D_minus: Incomplete theory (with element ablated)
        target: Conclusion q that should be derivable
        candidates: Candidate hypotheses H_cand (includes gold + distractors)
        gold: Gold-standard hypotheses H* ⊆ H_cand
        level: Difficulty level (1, 2, or 3)
        metadata: Additional information (ablated element, metrics, etc.)
    
    Task: Given (D^-, q, H_cand), find h ∈ H*.
    """
    D_minus: DefeasibleTheory
    target: str
    candidates: Set[Element]
    gold: Set[Element]
    level: int
    metadata: Dict[str, Any] = field(default_factory=dict)


def generate_level1_instance(
    D: DefeasibleTheory,
    q: str,
    e_fact: str,
    k_distractors: int = 5
) -> AbductiveInstance:
    """
    Level 1: Fact completion (Definition 21, line 619).
    
    Ablate e ∈ F ∩ Crit*(D, q).
    Model must identify missing observation.
    
    Gold set: H* = {e} (unique in most cases).
    Distractors: Facts sharing predicate symbols with e.
    
    Implementation: See author/generation.py.
    """
    raise NotImplementedError("See implementation in author/generation.py")


def generate_level2_instance(
    D: DefeasibleTheory,
    q: str,
    e_rule: Rule,
    k_distractors: int = 5
) -> AbductiveInstance:
    """
    Level 2: Rule abduction (Definition 21, line 620).
    
    Ablate e ∈ Rd ∩ Crit*(D, q).
    Model must reconstruct missing generalization.
    
    Gold set: H* = {e} (unique in most cases).
    Distractors: Rules with predicate substitutions or argument permutations.
    
    Implementation: See author/generation.py.
    """
    raise NotImplementedError("See implementation in author/generation.py")


# =============================================================================
# SECTION 6: LEVEL 3 - DEFEATER ABDUCTION (§A.5, Definitions 11-16)
# Paper: lines 628-680
# =============================================================================

def expectation_set(D: DefeasibleTheory) -> Set[str]:
    """
    Definition 11 (line 630): Exp(D) = {q | D ⊢∂ q}.
    
    Set of all defeasibly derivable conclusions.
    
    For function-free theories: Iterate over Herbrand base and test.
    Complexity: O(|HB| · |R| · |F|).
    
    Implementation: See reasoning/expectations.py.
    """
    raise NotImplementedError("See implementation in reasoning/expectations.py")


def is_defeasible_anomaly(D: DefeasibleTheory, alpha: str) -> bool:
    """
    Definition 12 (line 634): α is defeasible anomaly iff:
    - D ⊢∂ ¬α (theory predicts ¬α)
    - D ⊬Δ ¬α (not strictly provable, so can be blocked)
    
    Strict anomalies (D ⊢Δ ¬α) are excluded from Level 3:
    They cannot be resolved by defeaters (would violate strict rules).
    
    Implementation: See author/level3.py.
    """
    complement = complement_literal(alpha)
    return (
        defeasible_provable(D, complement) and
        not strictly_provable(D, complement)
    )


def anomaly_support(D: DefeasibleTheory, alpha: str) -> Set[Rule]:
    """
    Definition 13 (line 638): AnSup(D, α) = {r ∈ Rd | r in T(D, ¬α)}.
    
    Defeasible rules appearing in derivation tree of ¬α.
    These are the rules that must be defeated or overridden to resolve α.
    
    Requires: Derivation tree T(D, q) - AND-OR tree of proof of +∂q.
    
    Implementation: See reasoning/derivation_tree.py.
    """
    raise NotImplementedError("See implementation in reasoning/derivation_tree.py")


@dataclass
class LanguageBias:
    """
    Definition 14 (line 642): L = (P⁺, P⁻, ar_max, d_max).
    
    Constrains the hypothesis space for Level 3.
    
    Components:
        antecedent_predicates: P⁺ - predicates allowed in rule bodies
        consequent_predicates: P⁻ - predicates allowed in rule heads
        max_antecedent_length: ar_max - maximum number of antecedents
        max_nesting_depth: d_max - maximum term nesting
    
    Expanding P⁺ increases candidate space size (exponentially in ar_max).
    Expanding P⁺ with novel predicates increases required novelty Nov*.
    """
    antecedent_predicates: Set[str]  # P⁺
    consequent_predicates: Set[str]  # P⁻
    max_antecedent_length: int       # ar_max
    max_nesting_depth: int           # d_max


def candidate_defeater_space(L: LanguageBias) -> Set[Rule]:
    """
    Definition 15 (line 646): R_df(L) = {r: b1,...,bm ↝ ¬h | constraints}.
    
    All defeater rules satisfying language bias:
    - m ≤ ar_max
    - pred(bi) ∈ P⁺
    - pred(h) ∈ P⁻
    - vars(h) ⊆ ⋃_i vars(bi) (safety)
    
    Proposition 5: |R_df(L)| = O(|P⁺|^{ar_max} · |P⁻|) - exponential in ar_max.
    
    WARNING: Candidate space grows exponentially.
    In practice: Use small ar_max (≤3) or enumerate lazily.
    
    Implementation: See generation/language_bias.py.
    """
    raise NotImplementedError("See implementation in generation/language_bias.py")


def candidate_exception_space(L: LanguageBias) -> Set[Rule]:
    """
    Exception space R_d^exc(L): Same as R_df(L) but with ⇒ instead of ↝.
    
    Exceptions can support positive conclusions (strong resolutions).
    Defeaters can only block conclusions (weak resolutions).
    """
    raise NotImplementedError("See implementation in generation/language_bias.py")


def is_conservative_resolution(
    D: DefeasibleTheory,
    alpha: str,
    r: Rule,
    gamma: Dict[str, Set[str]]
) -> bool:
    """
    Conservativity check (referenced §3.4, line 265; Remark 2, line 672).
    
    Resolution (r, Γ) is conservative iff:
    Exp(D ∪ {r} ∪ Γ ∪ {α}) ⊇ Exp(D) \ {¬α}
    
    I.e., all expectations are preserved except the targeted anomaly ¬α.
    
    This operationalizes AGM minimal change (Alchourrón-Gärdenfors-Makinson):
    "Accommodate new evidence while disturbing as few existing commitments
    as possible."
    
    Tractability: Each expectation check is O(|R| · |F|) (Theorem 11).
    For |Exp(D)| = n: Total complexity O(n · |R| · |F|).
    
    Implementation: See author/level3.py.
    """
    raise NotImplementedError("See implementation in author/level3.py")


def revision_distance(D: DefeasibleTheory, D_prime: DefeasibleTheory) -> int:
    """
    Revision distance (§3.4, line 269; Remark 3, line 687).
    
    d_rev(D, D') = |Δ| + |Exp(D) \ Exp(D')|
    
    Where:
    - Δ: Structural changes (rules/facts added)
    - Exp(D) \ Exp(D'): Lost expectations
    
    Conservative resolutions achieve d_rev = |Δ| (no expectation loss).
    
    This is the defeasible analogue of Dalal distance for belief revision.
    Measures adherence to minimal change principle.
    
    Implementation: See author/metrics.py.
    """
    raise NotImplementedError("See implementation in author/metrics.py")


def predicate_novelty(r: Rule, D: DefeasibleTheory) -> float:
    """
    Definition 33 (line 683): Nov(r, D) = |pred(r) \ pred(D)| / |pred(r)|.
    
    Fraction of predicate symbols in r that are novel (absent from D).
    
    Nov(r, D) = 0: No novelty (all predicates already in D)
    Nov(r, D) = 1: Maximal novelty (all predicates new)
    
    Measures "creativity" of hypothesis.
    
    Implementation: See author/metrics.py.
    """
    raise NotImplementedError("See implementation in author/metrics.py")


def generate_level3_instance(
    D_full: DefeasibleTheory,
    r_star: Rule,
    alpha: str,
    L: LanguageBias
) -> AbductiveInstance:
    """
    Definition 16 (line 676): Level 3 instance generation.
    
    Working BACKWARDS from complete theory D^full:
    1. Select r* ∈ Rdf or exception rule
    2. Find α: D^full ⊢∂ α and D^full \ {r*} ⊢∂ ¬α
    3. Form D^- by removing r* and its superiority assertions
    4. Verify α is defeasible anomaly in D^-
    5. Compute gold set R* of all conservative resolutions
    
    Proposition 6: r* ∈ R* (gold set is non-empty).
    
    Complexity: Computing R* requires enumerating candidate space
    (exponential in |L|) and testing each candidate (polynomial).
    Tractable for small language bias.
    
    Implementation: See author/level3.py.
    """
    raise NotImplementedError("See implementation in author/level3.py")


# =============================================================================
# SECTION 7: METRICS (Definitions 33-35)
# Paper: lines 681-693
# =============================================================================

def structural_difficulty(instance: AbductiveInstance) -> Tuple[int, int, int, int, float]:
    """
    Definition 35 (line 691): Structural difficulty tuple.
    
    σ(I) = (ℓ(I), |Supp(D,q)|, |H*|, min_{h∈H*} |h|, Nov*(I))
    
    Where:
    - ℓ(I): Level (1, 2, or 3)
    - |Supp(D,q)|: Number of support sets (redundancy)
    - |H*|: Size of gold set (ambiguity)
    - min |h|: Minimum hypothesis complexity
    - Nov*(I): Minimum novelty among gold hypotheses
    
    Used to characterize instance difficulty and stratify dataset.
    
    Implementation: See author/metrics.py.
    """
    raise NotImplementedError("See implementation in author/metrics.py")


# =============================================================================
# HELPER FUNCTIONS (Not in paper, needed for implementation)
# =============================================================================

def extract_predicate(atom: str) -> str:
    """Extract predicate symbol from ground atom."""
    raise NotImplementedError()


def complement_literal(literal: str) -> str:
    """Compute complement: p ↦ ¬p, ¬p ↦ p."""
    raise NotImplementedError()


# =============================================================================
# PROPOSITIONS TO VERIFY
# =============================================================================

def verify_proposition_1(pi: DefiniteLogicProgram) -> bool:
    """
    Proposition 1 (line 743): Conservative conversion.
    
    If κ ≡ s (all clauses strict), then:
    q ∈ M_Π ⟺ D_κ ⊢Δ q
    
    Test: Generate random LP, convert with all-strict partition,
    verify M_Π = {q | D_κ ⊢Δ q}.
    """
    raise NotImplementedError("See tests/author/test_conversion.py")


def verify_proposition_2(D: DefeasibleTheory, q: str) -> bool:
    """
    Proposition 2 (line 751): Definite implies defeasible.
    
    If D ⊢Δ q then D ⊢∂ q.
    
    Test: For random D and q, if strictly provable, check defeasibly provable.
    """
    raise NotImplementedError("See tests/reasoning/test_defeasible.py")


def verify_proposition_3(pi: DefiniteLogicProgram, Q: Set[str]) -> bool:
    """
    Proposition 3 (line 759): Yield monotonicity.
    
    E[Y(κ_rand(δ), Q)] is non-decreasing in δ.
    
    Test: Plot yield curves for δ ∈ [0, 1], verify monotonicity.
    """
    raise NotImplementedError("See tests/author/test_conversion.py")


def verify_proposition_4(D: DefeasibleTheory, q: str) -> bool:
    """
    Proposition 4 (line 767): Criticality inclusion.
    
    Crit*(D, q) ⊆ Crit(D, q) (possibly strict).
    
    Test: Compute both, verify inclusion.
    """
    raise NotImplementedError("See tests/author/test_support.py")


def verify_proposition_5(L: LanguageBias) -> bool:
    """
    Proposition 5 (implied by line 649): Candidate space size.
    
    |R_df(L)| = O(|P⁺|^{ar_max} · |P⁻|)
    
    Test: Vary ar_max, verify exponential growth.
    """
    raise NotImplementedError("See tests/generation/test_language_bias.py")


def verify_proposition_6(D_full: DefeasibleTheory, r_star: Rule, 
                         alpha: str) -> bool:
    """
    Proposition 6 (implied by line 676): Gold set non-empty.
    
    For Level 3 instance generated from (D^full, r*, α):
    r* ∈ R* (gold set contains at least r*).
    
    Test: Generate Level 3 instance, verify r* in gold.
    """
    raise NotImplementedError("See tests/author/test_level3.py")


def verify_theorem_11(D: DefeasibleTheory, q: str) -> bool:
    """
    Theorem 11 (line 775): Defeasible derivation in P.
    
    For propositional defeasible theories (no defeaters, acyclic ≻):
    Deciding D ⊢∂ q is in P, computable in O(|R| · |F|).
    
    Test: Benchmark derivation time, verify linear scaling in |R| · |F|.
    """
    raise NotImplementedError("See tests/reasoning/test_defeasible.py")


# =============================================================================
# PAPER EXAMPLES TO REPRODUCE
# =============================================================================

def example_tweety() -> AbductiveInstance:
    """
    Tweety example (§1, §4).
    
    D = (
      F = {bird(tweety)},
      Rs = {},
      Rd = {r1: bird(X) ⇒ flies(X)},
      Rdf = {},
      ≻ = {}
    )
    
    Query: flies(tweety)
    Expected: D ⊢∂ flies(tweety)
    
    Variation: Add penguin(tweety) → team defeat blocks r1
    """
    raise NotImplementedError("See tests/examples/test_paper_examples.py")


def example_idp_discovery() -> AbductiveInstance:
    """
    IDP Discovery (Appendix C, Example 1, lines 917-941).
    
    The headline Level 3 example.
    
    D_bio with defaults:
    - r1: protein(X) ⇒ has_stable_3d(X)
    - r2: protein(X), has_stable_3d(X) ⇒ func_mech(X, lock_key)
    
    D_full with IDP exception:
    - r3: disordered(X) ⇒ ¬has_stable_3d(X)
    - r4: disordered(X), protein(X) ⇒ func_mech(X, conf_ensemble)
    - r3 ≻ r1, r4 ≻ r2
    
    Anomaly: α = func_mech(p53_idr, conf_ensemble)
    
    Remove r4 → α becomes anomalous.
    Gold: r4 (with superiority)
    Nov(r4, D^-) = 1/4 (conf_ensemble is novel)
    """
    raise NotImplementedError("See tests/examples/test_paper_examples.py")


# =============================================================================
# END OF AUTHOR.PY
# =============================================================================

if __name__ == "__main__":
    print(__doc__)
    print("\nThis is a SPECIFICATION file.")
    print("Implementations live in:")
    print("  - author/conversion.py")
    print("  - author/support.py")
    print("  - author/generation.py")
    print("  - author/level3.py")
    print("  - author/metrics.py")
    print("  - reasoning/defeasible.py")
    print("  - reasoning/expectations.py")
    print("  - codec/encoder.py")
    print("  - codec/decoder.py")
    print("\nRun tests with: pytest tests/")
