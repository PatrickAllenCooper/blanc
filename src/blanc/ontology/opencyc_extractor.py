"""
OpenCyc ontology extraction for multiple knowledge domains.

Extracts concepts, taxonomic relations, and properties from
OpenCyc 4.0 (239K terms, 2M triples) and converts to definite logic
programs.  Supports parameterized domain extraction via DomainProfile.

Author: Patrick Cooper
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

try:
    from rdflib import Graph, Namespace
    from rdflib.namespace import RDF, RDFS, OWL
    RDFLIB_AVAILABLE = True
except ImportError:
    RDFLIB_AVAILABLE = False
    Graph = None  # type: ignore[assignment,misc]
    Namespace = None  # type: ignore[assignment,misc]
    RDF = RDFS = OWL = None  # type: ignore[assignment]

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.domain_profiles import BIOLOGY, DomainProfile


class OpenCycExtractor:
    """Extract knowledge from OpenCyc ontology across domains.

    Strategy:
        1. Load OWL file with rdflib
        2. Identify domain concepts via keyword matching or root traversal
        3. Extract taxonomic relations (rdfs:subClassOf)
        4. Extract OWL object/data properties
        5. Convert to definite logic program

    Complexity: O(n) where n is number of triples (millions).
    """

    def __init__(
        self,
        opencyc_path: Path,
        profile: Optional[DomainProfile] = None,
    ):
        if not RDFLIB_AVAILABLE:
            raise ImportError(
                "rdflib is required for OpenCyc extraction. "
                "Install with: pip install rdflib>=7.0.0"
            )

        if not opencyc_path.exists():
            raise FileNotFoundError(
                f"OpenCyc file not found: {opencyc_path}"
            )

        self.opencyc_path = opencyc_path
        self.profile: DomainProfile = profile or BIOLOGY
        self.graph: Optional[Graph] = None  # type: ignore[assignment]
        self.domain_concepts: Set[str] = set()
        self.taxonomic_relations: List[Tuple[str, str]] = []
        self.property_relations: List[Tuple[str, str, str]] = []

        # Backward-compatible alias
        self.biological_concepts = self.domain_concepts

    # ── Loading ───────────────────────────────────────────────────

    def load(self) -> None:
        """Load OpenCyc OWL file into RDF graph."""
        self.graph = Graph()

        if self.opencyc_path.suffix == ".gz":
            with gzip.open(self.opencyc_path, "rb") as f:
                self.graph.parse(f, format="xml")
        else:
            self.graph.parse(self.opencyc_path, format="xml")

    # ── Domain extraction ─────────────────────────────────────────

    def extract_domain(self) -> None:
        """Extract concepts and relations for the configured domain."""
        if self.graph is None:
            raise ValueError("Must call load() first")

        keywords = self.profile.keywords

        for subject in self.graph.subjects(RDF.type, OWL.Class):
            labels = list(self.graph.objects(subject, RDFS.label))

            if labels:
                label = str(labels[0]).lower()

                if any(kw in label for kw in keywords):
                    concept_name = self._extract_concept_name(subject)
                    if concept_name:
                        self.domain_concepts.add(concept_name)

                        for superclass in self.graph.objects(
                            subject, RDFS.subClassOf
                        ):
                            super_name = self._extract_concept_name(superclass)
                            if super_name:
                                self.taxonomic_relations.append(
                                    (concept_name, super_name)
                                )

        self._extract_properties()

    def extract_biology(self) -> None:
        """Backward-compatible biology extraction."""
        if self.profile.name != "biology":
            self.profile = BIOLOGY
        self.extract_domain()

    # ── Property extraction ───────────────────────────────────────

    def _extract_properties(self) -> None:
        """Extract OWL object and data properties relevant to domain concepts."""
        if self.graph is None:
            return

        for prop_type in (OWL.ObjectProperty, OWL.DatatypeProperty):
            for prop in self.graph.subjects(RDF.type, prop_type):
                prop_name = self._extract_concept_name(prop)
                if not prop_name:
                    continue

                for domain in self.graph.objects(prop, RDFS.domain):
                    domain_name = self._extract_concept_name(domain)
                    if domain_name and domain_name in self.domain_concepts:
                        for range_cls in self.graph.objects(prop, RDFS.range):
                            range_name = self._extract_concept_name(range_cls)
                            if range_name:
                                self.property_relations.append(
                                    (domain_name, prop_name, range_name)
                                )

    # ── Conversion ────────────────────────────────────────────────

    def to_definite_lp(self) -> Theory:
        """Convert extracted concepts to definite logic program.

        Returns:
            Theory with domain KB.
        """
        theory = Theory()

        for concept in sorted(self.domain_concepts):
            norm = self._normalize_for_prolog(concept)
            theory.add_fact(f"domain_concept({norm})")

        added_rules: Set[tuple] = set()
        for sub, super_cls in self.taxonomic_relations:
            sub_norm = self._normalize_for_prolog(sub)
            super_norm = self._normalize_for_prolog(super_cls)

            key = (sub_norm, super_norm)
            if key not in added_rules:
                theory.add_rule(Rule(
                    head=f"isa({sub_norm}, {super_norm})",
                    body=(),
                    rule_type=RuleType.STRICT,
                    label=f"tax_{sub_norm}_{super_norm}",
                ))
                added_rules.add(key)

        for domain_cls, prop_name, range_cls in self.property_relations:
            d_norm = self._normalize_for_prolog(domain_cls)
            p_norm = self._normalize_for_prolog(prop_name)
            r_norm = self._normalize_for_prolog(range_cls)

            key = (d_norm, p_norm, r_norm)
            if key not in added_rules:
                theory.add_rule(Rule(
                    head=f"has_{p_norm}(X, {r_norm})",
                    body=(f"{d_norm}(X)",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"prop_{d_norm}_{p_norm}_{r_norm}",
                    metadata={"source": "OpenCyc",
                              "domain": self.profile.name},
                ))
                added_rules.add(key)

        return theory

    to_theory = to_definite_lp

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.taxonomic_relations:
            taxonomy[child].add(parent)
        return dict(taxonomy)

    # ── Helpers ───────────────────────────────────────────────────

    def _extract_concept_name(self, uri) -> Optional[str]:
        uri_str = str(uri)
        if "#" in uri_str:
            name = uri_str.split("#")[-1]
        elif "/" in uri_str:
            name = uri_str.split("/")[-1]
        else:
            name = uri_str

        if "?" in name:
            name = name.split("?")[0]

        return name if name and name != uri_str else None

    def _normalize_for_prolog(self, name: str) -> str:
        name = name.lower()
        name = name.replace(" ", "_").replace("-", "_")
        name = "".join(c if c.isalnum() or c == "_" else "" for c in name)
        if name and not name[0].isalpha():
            name = "c_" + name
        return name


# ── Convenience functions ─────────────────────────────────────────

def extract_from_opencyc(
    opencyc_path: Optional[Path] = None,
    max_concepts: Optional[int] = None,
    profile: Optional[DomainProfile] = None,
) -> Theory:
    """Extract a domain KB from OpenCyc.

    Args:
        opencyc_path: Path to OpenCyc OWL file.
        max_concepts: Limit number of concepts (None = all).
        profile: Domain profile (default: biology).
    """
    if opencyc_path is None:
        opencyc_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "opencyc"
            / "opencyc-2012-05-10-readable.owl.gz"
        )

    extractor = OpenCycExtractor(opencyc_path, profile)
    extractor.load()
    extractor.extract_domain()

    if max_concepts:
        extractor.domain_concepts = set(
            list(extractor.domain_concepts)[:max_concepts]
        )
        extractor.taxonomic_relations = extractor.taxonomic_relations[
            : max_concepts * 2
        ]

    return extractor.to_definite_lp()


def extract_biology_from_opencyc(
    opencyc_path: Optional[Path] = None,
    max_concepts: Optional[int] = None,
) -> Theory:
    """Backward-compatible biology extraction."""
    return extract_from_opencyc(opencyc_path, max_concepts, BIOLOGY)
