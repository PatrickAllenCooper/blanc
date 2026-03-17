"""
Cross-ontology combiner for large-scale defeasible rule generation.

Combines a taxonomic backbone (e.g. OpenCyc) with a behavioral property
source (e.g. ConceptNet) to produce defeasible theories with inherited
properties, defeaters, and full derivation depth.

Algorithm (from COMPREHENSIVE_KB_PIPELINE.md):
    For each concept C in the taxonomy:
      1. Traverse parent chain: C -> parent -> grandparent -> ... -> root
      2. For each ancestor A, harvest behavioral edges:
         (A, CapableOf, P)   -> P(X) :- A(X)     [DEFEASIBLE - inherited]
         (A, HasProperty, P) -> P(X) :- A(X)      [DEFEASIBLE - inherited]
      3. Harvest concept-specific edges:
         (C, CapableOf, P)   -> P(X) :- C(X)      [DEFEASIBLE - specific]
         (C, NotCapableOf, P)-> ~P(X) :- C(X)     [DEFEATER]
      4. Generate strict rules from IsA edges:
         (C, IsA, A)         -> A(X) :- C(X)      [STRICT]

Author: Patrick Cooper
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.domain_profiles import DomainProfile, BIOLOGY


@dataclass
class CombinationStats:
    """Statistics from a cross-ontology combination run."""

    taxonomy_concepts: int = 0
    taxonomy_relations: int = 0
    property_concepts: int = 0
    property_edges: int = 0
    strict_rules: int = 0
    defeasible_inherited: int = 0
    defeasible_specific: int = 0
    property_rules: int = 0
    causal_rules: int = 0
    functional_rules: int = 0
    defeaters: int = 0

    @property
    def total_rules(self) -> int:
        return (
            self.strict_rules
            + self.defeasible_inherited
            + self.defeasible_specific
            + self.property_rules
            + self.causal_rules
            + self.functional_rules
            + self.defeaters
        )

    def to_dict(self) -> dict:
        return {
            "taxonomy_concepts": self.taxonomy_concepts,
            "taxonomy_relations": self.taxonomy_relations,
            "property_concepts": self.property_concepts,
            "property_edges": self.property_edges,
            "strict_rules": self.strict_rules,
            "defeasible_inherited": self.defeasible_inherited,
            "defeasible_specific": self.defeasible_specific,
            "property_rules": self.property_rules,
            "causal_rules": self.causal_rules,
            "functional_rules": self.functional_rules,
            "defeaters": self.defeaters,
            "total_rules": self.total_rules,
        }


def _normalize(text: str) -> str:
    text = text.lower().replace(" ", "_").replace("-", "_")
    return "".join(c for c in text if c.isalnum() or c == "_")


def _transitive_ancestors(
    taxonomy: Dict[str, Set[str]],
) -> Dict[str, Set[str]]:
    """Compute transitive closure: concept -> all ancestors (parents, grandparents, ...)."""
    ancestors: Dict[str, Set[str]] = {}

    def _get_ancestors(concept: str, visited: Set[str]) -> Set[str]:
        if concept in ancestors:
            return ancestors[concept]
        if concept in visited:
            return set()
        visited.add(concept)
        result: Set[str] = set()
        for parent in taxonomy.get(concept, set()):
            result.add(parent)
            result |= _get_ancestors(parent, visited)
        ancestors[concept] = result
        return result

    for concept in taxonomy:
        _get_ancestors(concept, set())
    return ancestors


def combine_taxonomy_properties(
    taxonomy: Dict[str, Set[str]],
    properties: Dict[str, List[Tuple[str, str]]],
    profile: Optional[DomainProfile] = None,
) -> Tuple[Theory, CombinationStats]:
    """Combine a taxonomy with a property source into a defeasible theory.

    Traverses the full ancestor chain so that properties propagate
    transitively (penguin inherits from bird, animal, organism, etc.).

    Args:
        taxonomy: concept -> {parent1, parent2, ...}
        properties: concept -> [(relation, property), ...]
        profile: Domain profile for metadata (default: biology).

    Returns:
        (theory, stats) tuple.
    """
    profile = profile or BIOLOGY
    theory = Theory()
    stats = CombinationStats()
    rules_added: Set[tuple] = set()

    stats.taxonomy_concepts = len(taxonomy)
    stats.taxonomy_relations = sum(len(ps) for ps in taxonomy.values())
    stats.property_concepts = len(properties)
    stats.property_edges = sum(len(es) for es in properties.values())

    all_ancestors = _transitive_ancestors(taxonomy)

    for concept in taxonomy:
        theory.add_fact(f"concept({concept})")
        # Ground each concept with an instance so rule chains can fire
        theory.add_fact(f"{concept}({concept})")

    for concept, parents in taxonomy.items():
        for parent in parents:
            key = ("tax", concept, parent)
            if key not in rules_added:
                theory.add_rule(Rule(
                    head=f"{parent}(X)",
                    body=(f"{concept}(X)",),
                    rule_type=RuleType.STRICT,
                    label=f"tax_{concept}_{parent}",
                ))
                rules_added.add(key)
                stats.strict_rules += 1

        # Inherited properties from ALL ancestors (full transitive closure)
        inherited: Set[Tuple[str, str]] = set()
        for ancestor in all_ancestors.get(concept, set()):
            for (rel, prop) in properties.get(ancestor, []):
                inherited.add((rel, prop))

        for (rel, prop) in inherited:
            _add_property_rule(
                theory, rules_added, stats, concept, rel, prop,
                inherited=True, profile=profile,
            )

        # Concept-specific properties
        for (rel, prop) in properties.get(concept, []):
            _add_property_rule(
                theory, rules_added, stats, concept, rel, prop,
                inherited=False, profile=profile,
            )

    return theory, stats


def _add_property_rule(
    theory: Theory,
    rules_added: Set[tuple],
    stats: CombinationStats,
    concept: str,
    relation: str,
    prop: str,
    inherited: bool,
    profile: DomainProfile,
) -> None:
    """Add a single property-derived rule to the theory."""
    norm_prop = _normalize(prop)
    tag = "inh" if inherited else "spec"
    meta = {"source": "CrossOntology", "domain": profile.name,
            "inherited": inherited}

    if relation == "CapableOf":
        key = ("cap", concept, norm_prop)
        if key not in rules_added:
            theory.add_rule(Rule(
                head=f"{norm_prop}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"cap_{tag}_{concept}_{norm_prop}",
                metadata=meta,
            ))
            rules_added.add(key)
            if inherited:
                stats.defeasible_inherited += 1
            else:
                stats.defeasible_specific += 1

    elif relation == "NotCapableOf":
        key = ("def", concept, norm_prop)
        if key not in rules_added:
            theory.add_rule(Rule(
                head=f"~{norm_prop}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.DEFEATER,
                label=f"defeater_{concept}_{norm_prop}",
                metadata=meta,
            ))
            rules_added.add(key)
            stats.defeaters += 1

    elif relation == "HasProperty":
        key = ("prop", concept, norm_prop)
        if key not in rules_added:
            theory.add_rule(Rule(
                head=f"has_{norm_prop}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"prop_{tag}_{concept}_{norm_prop}",
                metadata=meta,
            ))
            rules_added.add(key)
            stats.property_rules += 1

    elif relation == "Causes":
        key = ("cause", concept, norm_prop)
        if key not in rules_added:
            theory.add_rule(Rule(
                head=f"causes_{norm_prop}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"cause_{tag}_{concept}_{norm_prop}",
                metadata=meta,
            ))
            rules_added.add(key)
            stats.causal_rules += 1

    elif relation == "UsedFor":
        key = ("use", concept, norm_prop)
        if key not in rules_added:
            theory.add_rule(Rule(
                head=f"used_for_{norm_prop}(X)",
                body=(f"{concept}(X)",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"use_{tag}_{concept}_{norm_prop}",
                metadata=meta,
            ))
            rules_added.add(key)
            stats.functional_rules += 1


def build_cross_ontology_theory(
    taxonomy: Dict[str, Set[str]],
    properties: Dict[str, List[Tuple[str, str]]],
    profile: Optional[DomainProfile] = None,
    output_path: Optional[Path] = None,
) -> Tuple[Theory, CombinationStats]:
    """Full cross-ontology pipeline: combine, optionally save stats.

    Args:
        taxonomy: concept -> {parents}
        properties: concept -> [(relation, property)]
        profile: Domain profile.
        output_path: If given, write stats JSON here.

    Returns:
        (theory, stats)
    """
    theory, stats = combine_taxonomy_properties(taxonomy, properties, profile)

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(stats.to_dict(), f, indent=2)

    return theory, stats
