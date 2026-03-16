"""
ConceptNet5 extraction for multiple knowledge domains.

Extracts behavioral defaults, taxonomic relations, and exceptions from
ConceptNet5 (34M edges) to create rich defeasible knowledge bases.
Supports parameterized domain extraction via DomainProfile.

Author: Patrick Cooper
"""

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.domain_profiles import BIOLOGY, DomainProfile


_RELATION_TO_RULE_TYPE = {
    "IsA": RuleType.STRICT,
    "CapableOf": RuleType.DEFEASIBLE,
    "NotCapableOf": RuleType.DEFEATER,
    "HasProperty": RuleType.DEFEASIBLE,
    "Causes": RuleType.DEFEASIBLE,
    "UsedFor": RuleType.DEFEASIBLE,
}

_SUPPORTED_RELATIONS = frozenset(_RELATION_TO_RULE_TYPE)


class ConceptNetExtractor:
    """Extract domain knowledge from ConceptNet5.

    ConceptNet5 format (CSV, tab-separated)::

        /a/[/r/Relation]/[start]/[end]/ <tab> relation <tab> start <tab> end <tab> metadata

    The extractor accepts a ``DomainProfile`` that controls which concepts
    are retained and how each relation is converted to a defeasible rule.
    When no profile is supplied, the biology profile is used for backward
    compatibility.
    """

    def __init__(
        self,
        conceptnet_path: Path,
        weight_threshold: float = 2.0,
        profile: Optional[DomainProfile] = None,
    ):
        if not conceptnet_path.exists():
            raise FileNotFoundError(
                f"ConceptNet5 file not found: {conceptnet_path}"
            )

        self.conceptnet_path = conceptnet_path
        self.weight_threshold = weight_threshold
        self.profile: DomainProfile = profile or BIOLOGY
        self.edges: List[dict] = []
        self.domain_edges: List[dict] = []
        # Backward-compatible alias
        self.biological_edges = self.domain_edges

    # ── Extraction ────────────────────────────────────────────────

    def extract(self, max_edges: Optional[int] = None) -> None:
        """Extract edges matching the configured domain profile.

        Args:
            max_edges: Stop after processing this many lines (None = all).
        """
        keywords = self.profile.keywords
        edges_processed = 0

        with gzip.open(self.conceptnet_path, "rt", encoding="utf-8") as f:
            for line in f:
                if max_edges and edges_processed >= max_edges:
                    break

                edges_processed += 1

                try:
                    parts = line.strip().split("\t")
                    if len(parts) < 5:
                        continue

                    _uri, relation, start, end, metadata_json = parts[:5]

                    if "/c/en/" not in start or "/c/en/" not in end:
                        continue

                    metadata = json.loads(metadata_json)
                    weight = metadata.get("weight", 0.0)

                    if weight < self.weight_threshold:
                        continue

                    rel_name = self._extract_relation(relation)
                    if rel_name not in _SUPPORTED_RELATIONS:
                        continue

                    start_concept = self._extract_concept(start)
                    end_concept = self._extract_concept(end)

                    if any(
                        kw in start_concept.lower() or kw in end_concept.lower()
                        for kw in keywords
                    ):
                        self.domain_edges.append(
                            {
                                "relation": rel_name,
                                "start": start_concept,
                                "end": end_concept,
                                "weight": weight,
                            }
                        )
                except Exception:
                    continue

    def extract_biology(self, max_edges: Optional[int] = None) -> None:
        """Backward-compatible wrapper -- forces biology profile."""
        if self.profile.name != "biology":
            self.profile = BIOLOGY
        self.extract(max_edges)

    # ── Conversion ────────────────────────────────────────────────

    def to_theory(self) -> Theory:
        """Convert extracted edges to a defeasible ``Theory``.

        Conversion rules:
            - IsA         -> strict taxonomic facts
            - CapableOf   -> defeasible behavioral defaults
            - NotCapableOf-> defeaters (exceptions)
            - HasProperty -> defeasible property rules
            - Causes      -> defeasible causal rules
            - UsedFor     -> defeasible functional rules
        """
        theory = Theory()
        facts_added: Set[str] = set()
        rules_added: Set[tuple] = set()
        source = "ConceptNet5"
        domain = self.profile.name

        for edge in self.domain_edges:
            rel = edge["relation"]
            start = self._normalize(edge["start"])
            end = self._normalize(edge["end"])
            weight = edge["weight"]

            if rel == "IsA":
                fact = f"isa({start}, {end})"
                if fact not in facts_added:
                    theory.add_fact(fact)
                    facts_added.add(fact)

            elif rel == "CapableOf":
                action = self._action_to_predicate(end)
                key = (action, start)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"{action}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_{action}_{start}",
                        metadata={"weight": weight, "source": source,
                                  "domain": domain},
                    ))
                    rules_added.add(key)

            elif rel == "NotCapableOf":
                action = self._action_to_predicate(end)
                key = (f"~{action}", start)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"~{action}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEATER,
                        label=f"d_{action}_{start}",
                        metadata={"weight": weight, "source": source,
                                  "domain": domain},
                    ))
                    rules_added.add(key)

            elif rel == "HasProperty":
                prop = self._normalize(end)
                key = (f"has_{prop}", start)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"has_{prop}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_has_{prop}_{start}",
                        metadata={"weight": weight, "source": source,
                                  "domain": domain},
                    ))
                    rules_added.add(key)

            elif rel == "Causes":
                effect = self._normalize(end)
                key = (f"causes_{effect}", start)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"causes_{effect}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_causes_{effect}_{start}",
                        metadata={"weight": weight, "source": source,
                                  "domain": domain},
                    ))
                    rules_added.add(key)

            elif rel == "UsedFor":
                use = self._normalize(end)
                key = (f"used_for_{use}", start)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"used_for_{use}(X)",
                        body=(f"isa(X, {start})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"r_used_for_{use}_{start}",
                        metadata={"weight": weight, "source": source,
                                  "domain": domain},
                    ))
                    rules_added.add(key)

        return theory

    # ── Helpers ───────────────────────────────────────────────────

    def _extract_concept(self, uri: str) -> str:
        parts = uri.split("/")
        if len(parts) >= 4 and parts[1] == "c" and parts[2] == "en":
            return parts[3]
        return uri

    def _extract_relation(self, uri: str) -> str:
        parts = uri.split("/")
        if len(parts) >= 3 and parts[1] == "r":
            return parts[2]
        return uri

    def _normalize(self, text: str) -> str:
        text = text.lower().replace(" ", "_").replace("-", "_")
        return "".join(c for c in text if c.isalnum() or c == "_")

    def _action_to_predicate(self, action: str) -> str:
        return self._normalize(action)


# ── Convenience functions ─────────────────────────────────────────

def extract_from_conceptnet(
    conceptnet_path: Optional[Path] = None,
    weight_threshold: float = 2.0,
    max_edges: Optional[int] = None,
    profile: Optional[DomainProfile] = None,
) -> Theory:
    """Extract a domain KB from ConceptNet5.

    Args:
        conceptnet_path: Path to ConceptNet5 CSV (defaults to data/).
        weight_threshold: Minimum confidence weight.
        max_edges: Max edges to process (None = all 34M).
        profile: Domain profile to use (default: biology).

    Returns:
        Theory with domain-specific behavioral rules.
    """
    if conceptnet_path is None:
        conceptnet_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "conceptnet"
            / "conceptnet-assertions-5.7.0.csv.gz"
        )

    extractor = ConceptNetExtractor(conceptnet_path, weight_threshold, profile)
    extractor.extract(max_edges)
    return extractor.to_theory()


def extract_biology_from_conceptnet(
    conceptnet_path: Optional[Path] = None,
    weight_threshold: float = 2.0,
    max_edges: Optional[int] = None,
) -> Theory:
    """Backward-compatible biology extraction."""
    return extract_from_conceptnet(
        conceptnet_path, weight_threshold, max_edges, BIOLOGY
    )
