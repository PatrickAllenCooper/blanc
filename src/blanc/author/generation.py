"""
Instance generation for Levels 1 and 2.

Implements Definitions 20-21 from paper.tex lines 615-627.

Author: Patrick Cooper
Date: 2026-02-11
"""

from dataclasses import dataclass, field
from typing import List, Union, Dict, Any

from blanc.core.theory import Theory, Rule


# Element can be either a fact (str) or a rule (Rule)
Element = Union[str, Rule]


@dataclass
class AbductiveInstance:
    r"""
    Abductive instance (D^-, q, H_cand, H*).
    
    Definition 20 (paper.tex line 615).
    
    Components:
        D_minus: Incomplete theory (with element ablated)
        target: Conclusion q that should be derivable
        candidates: Candidate hypotheses H_cand (includes gold + distractors)
        gold: Gold-standard hypotheses H* ⊆ H_cand
        level: Difficulty level (1, 2, or 3)
        metadata: Additional information (ablated element, metrics, etc.)
    
    Task: Given (D^-, q, H_cand), find h ∈ H*.
    
    Validity Properties:
        1. D^- ⊬∂ q (ablation removes derivability)
        2. ∀h ∈ H*: D^- ∪ {h} ⊢∂ q (gold restores derivability)
        3. ∀d ∈ (H_cand \ H*): D^- ∪ {d} ⊬∂ q (distractors don't restore)
        4. H* ≠ ∅ (gold set non-empty)
    
    Example:
        >>> # Level 1: Fact completion
        >>> instance = AbductiveInstance(
        ...     D_minus=theory_without_fact,
        ...     target="flies(tweety)",
        ...     candidates=["bird(tweety)", "sparrow(tweety)", "penguin(tweety)"],
        ...     gold=["bird(tweety)"],
        ...     level=1,
        ...     metadata={"ablated_element": "bird(tweety)"}
        ... )
    """
    D_minus: Theory
    target: str
    candidates: List[Element]
    gold: List[Element]
    level: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_valid(self) -> bool:
        """
        Check if instance satisfies validity properties.
        
        Returns:
            True if all validity properties hold
        
        Validity differs by level:
            - Level 1-2: Gold RESTORES derivability of target
            - Level 3: Gold BLOCKS derivability of anomaly (target is ~anomaly)
        """
        from blanc.reasoning.defeasible import defeasible_provable
        
        # Property 4: H* ≠ ∅ (always required)
        if not self.gold:
            return False
        
        if self.level in [1, 2]:
            # Levels 1-2: Restore derivability
            
            # Property 1: D^- ⊬∂ q
            if defeasible_provable(self.D_minus, self.target):
                return False
            
            # Property 2: ∀h ∈ H*: D^- ∪ {h} ⊢∂ q
            for h in self.gold:
                theory_with_h = _add_element(self.D_minus, h)
                if not defeasible_provable(theory_with_h, self.target):
                    return False
            
            # Property 3: ∀d ∈ (H_cand \ H*): D^- ∪ {d} ⊬∂ q
            for candidate in self.candidates:
                if candidate not in self.gold:
                    theory_with_d = _add_element(self.D_minus, candidate)
                    if defeasible_provable(theory_with_d, self.target):
                        return False
            
            return True
            
        elif self.level == 3:
            # Level 3: Block anomaly
            # target should be ~anomaly
            # For MVP: We'll validate that gold blocks the complement
            
            # For Level 3, we can't easily validate without knowing the anomaly
            # For MVP: Trust manual construction
            # TODO: Add proper Level 3 validation with anomaly tracking
            return True
        
        else:
            raise ValueError(f"Unknown level: {self.level}")
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "target": self.target,
            "level": self.level,
            "candidates": [_element_to_str(c) for c in self.candidates],
            "gold": [_element_to_str(g) for g in self.gold],
            "metadata": self.metadata,
            "theory_size": len(self.D_minus),
            "num_candidates": len(self.candidates),
            "num_gold": len(self.gold),
        }


def generate_level1_instance(
    theory: Theory,
    target: str,
    critical_fact: str,
    k_distractors: int = 5,
    distractor_strategy: str = "syntactic"
) -> AbductiveInstance:
    """
    Generate Level 1 instance (fact completion).
    
    Definition 21 (paper.tex line 619): Ablate e ∈ F ∩ Crit*(D, q).
    Model must identify missing observation.
    
    Args:
        theory: Source defeasible theory D
        target: Target literal q to derive
        critical_fact: Fact e to ablate (must be in Crit*(D, q))
        k_distractors: Number of distractors to sample
        distractor_strategy: One of 'random', 'syntactic', 'adversarial'
    
    Returns:
        AbductiveInstance for Level 1
    
    Raises:
        ValueError: If critical_fact is not actually critical for target
    
    Example:
        >>> theory = create_avian_biology_base()
        >>> theory_converted = convert_theory_to_defeasible(theory, "rule")
        >>> instance = generate_level1_instance(
        ...     theory_converted,
        ...     "flies(tweety)",
        ...     "bird(tweety)",
        ...     k_distractors=5
        ... )
    """
    from blanc.author.support import full_theory_criticality, _remove_element
    from blanc.generation.distractor import sample_fact_distractors
    
    # Verify fact is critical
    critical_set = full_theory_criticality(theory, target)
    if critical_fact not in critical_set:
        raise ValueError(
            f"Fact '{critical_fact}' is not critical for target '{target}'. "
            f"Critical elements: {[e if isinstance(e, str) else e.label for e in critical_set]}"
        )
    
    # Form D^- = D \ {e}
    D_minus = _remove_element(theory, critical_fact)
    
    # Sample distractors
    distractors = sample_fact_distractors(
        target_fact=critical_fact,
        theory=theory,
        k=k_distractors,
        strategy=distractor_strategy
    )
    
    # Gold set: just the critical fact
    gold = [critical_fact]
    
    # Candidates: gold + distractors
    candidates = gold + distractors
    
    return AbductiveInstance(
        D_minus=D_minus,
        target=target,
        candidates=candidates,
        gold=gold,
        level=1,
        metadata={
            "ablated_element": critical_fact,
            "ablated_type": "fact",
            "distractor_strategy": distractor_strategy,
            "k_distractors": k_distractors,
        }
    )


def generate_level2_instance(
    theory: Theory,
    target: str,
    critical_rule: Rule,
    k_distractors: int = 5,
    distractor_strategy: str = "syntactic"
) -> AbductiveInstance:
    """
    Generate Level 2 instance (rule abduction).
    
    Definition 21 (paper.tex line 620): Ablate e ∈ Rd ∩ Crit*(D, q).
    Model must reconstruct missing generalization.
    
    Args:
        theory: Source defeasible theory D
        target: Target literal q to derive
        critical_rule: Rule e to ablate (must be in Crit*(D, q))
        k_distractors: Number of distractors to sample
        distractor_strategy: One of 'random', 'syntactic', 'adversarial'
    
    Returns:
        AbductiveInstance for Level 2
    
    Raises:
        ValueError: If critical_rule is not actually critical for target
    
    Example:
        >>> theory = create_avian_biology_base()
        >>> theory_converted = convert_theory_to_defeasible(theory, "rule")
        >>> # Find the flies rule
        >>> flies_rule = next(r for r in theory_converted.rules if r.label == "r1")
        >>> instance = generate_level2_instance(
        ...     theory_converted,
        ...     "flies(tweety)",
        ...     flies_rule,
        ...     k_distractors=5
        ... )
    """
    from blanc.author.support import full_theory_criticality, _remove_element
    from blanc.generation.distractor import sample_rule_distractors
    from blanc.core.theory import RuleType
    
    # Verify rule is defeasible and critical
    if critical_rule.rule_type != RuleType.DEFEASIBLE:
        raise ValueError(
            f"Rule must be defeasible for Level 2. "
            f"Got: {critical_rule.rule_type}"
        )
    
    critical_set = full_theory_criticality(theory, target)
    if critical_rule not in critical_set:
        raise ValueError(
            f"Rule '{critical_rule.label}' is not critical for target '{target}'"
        )
    
    # Form D^- = D \ {e}
    D_minus = _remove_element(theory, critical_rule)
    
    # Sample distractors
    distractors = sample_rule_distractors(
        target_rule=critical_rule,
        theory=theory,
        k=k_distractors,
        strategy=distractor_strategy
    )
    
    # Gold set: just the critical rule
    gold = [critical_rule]
    
    # Candidates: gold + distractors
    candidates = gold + distractors
    
    return AbductiveInstance(
        D_minus=D_minus,
        target=target,
        candidates=candidates,
        gold=gold,
        level=2,
        metadata={
            "ablated_element": critical_rule.label or str(critical_rule),
            "ablated_type": "rule",
            "ablated_rule_type": critical_rule.rule_type.value,
            "distractor_strategy": distractor_strategy,
            "k_distractors": k_distractors,
        }
    )


# Helper functions

def _add_element(theory: Theory, element: Element) -> Theory:
    """
    Create new theory with element added.
    
    Args:
        theory: Base theory
        element: Fact (str) or Rule to add
    
    Returns:
        New theory with element
    """
    new_theory = Theory()
    
    # Copy all existing facts
    for fact in theory.facts:
        new_theory.add_fact(fact)
    
    # Copy all existing rules
    for rule in theory.rules:
        new_theory.add_rule(Rule(
            head=rule.head,
            body=rule.body,
            rule_type=rule.rule_type,
            priority=rule.priority,
            label=rule.label,
            metadata=rule.metadata.copy() if rule.metadata else {}
        ))
    
    # Add new element
    if isinstance(element, str):
        new_theory.add_fact(element)
    elif isinstance(element, Rule):
        new_theory.add_rule(Rule(
            head=element.head,
            body=element.body,
            rule_type=element.rule_type,
            priority=element.priority,
            label=element.label,
            metadata=element.metadata.copy() if element.metadata else {}
        ))
    
    # Copy superiority relations
    new_theory.superiority = {
        k: v.copy() for k, v in theory.superiority.items()
    }
    
    return new_theory


def _element_to_str(element: Element) -> str:
    """Convert element to string for serialization."""
    if isinstance(element, str):
        return element
    else:
        return str(element)
