"""
SNOMED CT extraction for defeasible knowledge bases.

Parses SNOMED CT distributions in either OWL Functional Syntax (via rdflib)
or RF2 snapshot format (line-by-line) to produce a defeasible theory with:
  - Strict taxonomic rules from SubClassOf / Is-a (116680003) relationships
  - Defeasible defining-property rules from EquivalentClasses intersections
  - Defeasible GCI (General Concept Inclusion) axioms
  - Defeaters where child concepts override inherited parent properties

RF2 Relationship snapshot columns:
    id | effectiveTime | active | moduleId | sourceId | destinationId |
    relationshipGroup | typeId | characteristicTypeId | modifierId

OWL source: SNOMED CT International Edition OWL distribution
RF2 source: https://www.nlm.nih.gov/healthit/snomedct/

Author: Anonymous Authors
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")

ISA_TYPE_ID = "116680003"

SNOMED_DEFINING_RELATIONS: Dict[str, str] = {
    "116676008": "associated_morphology",
    "363698007": "finding_site",
    "246075003": "causative_agent",
    "370135005": "pathological_process",
    "405813007": "procedure_site",
    "260686004": "method",
    "363713009": "has_interpretation",
    "363714003": "interprets",
    "127489000": "has_active_ingredient",
    "411116001": "has_manufactured_dose_form",
    "726542003": "has_disposition",
    "246454002": "occurrence",
    "255234002": "after",
    "363589002": "associated_procedure",
    "47429007": "associated_with",
}

_SCT_CONCEPT_RE = re.compile(r"<http://snomed\.info/id/(\d+)>")


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    text = _NORMALIZE_RE.sub("", text)
    if text and not text[0].isalpha():
        text = "c_" + text
    return text


def _sct_id(concept_id: str) -> str:
    """Normalize a SNOMED concept ID: 123456789 -> sct_123456789."""
    return f"sct_{concept_id}"


class SnomedExtractor:
    """Extract defeasible knowledge from SNOMED CT distributions.

    Supports two input formats:

    1. **OWL Functional Syntax** -- parsed with ``rdflib`` to extract
       SubClassOf, EquivalentClasses, and GCI axioms.
    2. **RF2 snapshot** -- parsed line-by-line from the
       ``sct2_Relationship_Snapshot`` file for Is-a and defining
       relationships.

    Mapping to defeasible logic:
        SubClassOf / Is-a (116680003)     -> strict taxonomic rules
        EquivalentClasses intersections   -> defeasible defining properties
        GCI axioms                        -> defeasible rules
        Property overrides in children    -> defeaters

    Usage::

        ext = SnomedExtractor(Path("sct2_Relationship_Snapshot_INT_20250131.txt"))
        ext.load()
        ext.extract()
        theory = ext.to_theory()
    """

    _SOURCE = "SNOMED_CT"

    def __init__(self, owl_path: Path) -> None:
        self.path = owl_path
        if not self.path.exists():
            raise FileNotFoundError(f"SNOMED file not found: {self.path}")

        self._format: Optional[str] = None

        self.isa_edges: List[Tuple[str, str]] = []
        self.defining_rels: List[Tuple[str, str, str, str]] = []
        self.gci_axioms: List[Tuple[str, str, str]] = []
        self._property_overrides: List[Tuple[str, str, str, str, str]] = []

        self.concept_names: Dict[str, str] = {}

        self._loaded = False

    # -- Loading -----------------------------------------------------------

    def load(self) -> None:
        """Detect format and parse the SNOMED distribution file."""
        self._format = self._detect_format()
        logger.info("Detected SNOMED format: %s", self._format)

        if self._format == "rf2":
            self._load_rf2()
        elif self._format == "owl":
            self._load_owl()
        else:
            raise ValueError(f"Unsupported SNOMED format for: {self.path}")

        self._loaded = True

    def _detect_format(self) -> str:
        """Heuristic format detection from the first few lines."""
        with open(self.path, encoding="utf-8") as fh:
            header = fh.readline()

        if header.startswith("id\t") or "effectiveTime" in header:
            return "rf2"

        suffix = self.path.suffix.lower()
        if suffix in (".owl", ".ofn", ".rdf", ".ttl"):
            return "owl"

        if "SubClassOf" in header or "OWL" in header or "Ontology" in header:
            return "owl"

        return "rf2"

    def _load_rf2(self) -> None:
        """Parse an RF2 sct2_Relationship_Snapshot file.

        Columns (tab-delimited):
            0  id
            1  effectiveTime
            2  active          (1 = active, 0 = inactive)
            3  moduleId
            4  sourceId        (child / source concept)
            5  destinationId   (parent / target concept)
            6  relationshipGroup
            7  typeId          (116680003 = Is a; others = defining rels)
            8  characteristicTypeId
            9  modifierId
        """
        count_isa = 0
        count_def = 0

        with open(self.path, encoding="utf-8") as fh:
            header = fh.readline()
            if not header.startswith("id"):
                logger.warning("RF2 header not recognised; attempting parse anyway")

            for line in fh:
                fields = line.rstrip("\n").split("\t")
                if len(fields) < 10:
                    continue

                active = fields[2]
                if active != "1":
                    continue

                source_id = fields[4]
                dest_id = fields[5]
                rel_group = fields[6]
                type_id = fields[7]

                if type_id == ISA_TYPE_ID:
                    self.isa_edges.append((source_id, dest_id))
                    count_isa += 1
                else:
                    rel_name = SNOMED_DEFINING_RELATIONS.get(type_id, type_id)
                    self.defining_rels.append(
                        (source_id, rel_name, dest_id, rel_group)
                    )
                    count_def += 1

        logger.info(
            "RF2: %d Is-a edges, %d defining relationships", count_isa, count_def
        )

    def _load_owl(self) -> None:
        """Parse a SNOMED OWL distribution using rdflib."""
        try:
            import rdflib
        except ImportError as exc:
            raise ImportError(
                "The 'rdflib' package is required for OWL parsing. "
                "Install with: pip install rdflib"
            ) from exc

        g = rdflib.Graph()

        suffix = self.path.suffix.lower()
        fmt_map = {
            ".ttl": "turtle",
            ".rdf": "xml",
            ".owl": "xml",
            ".ofn": "xml",
            ".nt": "nt",
        }
        rdf_format = fmt_map.get(suffix, "xml")

        logger.info("Parsing OWL file with rdflib (format=%s)...", rdf_format)
        g.parse(str(self.path), format=rdf_format)

        rdfs_sub = rdflib.RDFS.subClassOf
        owl_equiv = rdflib.OWL.equivalentClass

        for s, _p, o in g.triples((None, rdfs_sub, None)):
            s_id = self._extract_concept_id(str(s))
            o_id = self._extract_concept_id(str(o))
            if s_id and o_id:
                self.isa_edges.append((s_id, o_id))

        for s, _p, o in g.triples((None, owl_equiv, None)):
            s_id = self._extract_concept_id(str(s))
            o_id = self._extract_concept_id(str(o))
            if s_id and o_id:
                self.gci_axioms.append((s_id, "equivalent_to", o_id))

        logger.info(
            "OWL: %d SubClassOf, %d EquivalentClasses",
            len(self.isa_edges),
            len(self.gci_axioms),
        )

    @staticmethod
    def _extract_concept_id(uri: str) -> Optional[str]:
        """Extract a SNOMED concept ID from an IRI."""
        match = _SCT_CONCEPT_RE.search(uri)
        if match:
            return match.group(1)
        if uri.startswith("http://snomed.info/id/"):
            return uri.split("/")[-1]
        parts = uri.rsplit("/", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[1]
        return None

    # -- Extraction --------------------------------------------------------

    def extract(self) -> None:
        """Run the full extraction pipeline.

        After loading, detects property overrides where a child concept
        redefines a relationship that its parent also defines -- these
        become defeaters in the output theory.
        """
        if not self._loaded:
            raise ValueError("Must call load() before extract()")

        self._detect_property_overrides()

    def _detect_property_overrides(self) -> None:
        """Find cases where a child overrides a parent's defining relationship.

        If concept A is-a B, and both A and B define the same relationship
        type to different targets, A's definition defeats B's inherited one.
        """
        self._property_overrides.clear()

        parent_map: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.isa_edges:
            parent_map[child].add(parent)

        concept_props: Dict[str, Dict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        for source, rel, dest, _group in self.defining_rels:
            concept_props[source][rel].add(dest)

        for child, parents in parent_map.items():
            if child not in concept_props:
                continue
            child_rels = concept_props[child]

            for parent in parents:
                if parent not in concept_props:
                    continue
                parent_rels = concept_props[parent]

                for rel_type in child_rels:
                    if rel_type not in parent_rels:
                        continue
                    child_targets = child_rels[rel_type]
                    parent_targets = parent_rels[rel_type]

                    overridden = parent_targets - child_targets
                    for old_target in overridden:
                        new_targets = child_targets - parent_targets
                        for new_target in new_targets:
                            self._property_overrides.append(
                                (child, parent, rel_type, old_target, new_target)
                            )

        logger.info(
            "Detected %d property overrides", len(self._property_overrides)
        )

    # -- Conversion --------------------------------------------------------

    def to_theory(self) -> Theory:
        """Convert extracted SNOMED data to a defeasible Theory.

        Produces:
            - Strict ``isa(child, parent)`` from SubClassOf / Is-a
            - Defeasible defining property rules from RF2 relationships
            - Defeasible GCI axioms from OWL EquivalentClasses
            - Defeaters from property overrides
        """
        theory = Theory()
        added: Set[tuple] = set()

        for child, parent in self.isa_edges:
            c_norm = _sct_id(child)
            p_norm = _sct_id(parent)
            key = ("isa", c_norm, p_norm)
            if key in added:
                continue
            added.add(key)

            theory.add_rule(Rule(
                head=f"isa({c_norm}, {p_norm})",
                body=(),
                rule_type=RuleType.STRICT,
                label=f"sct_tax_{c_norm}_{p_norm}",
                metadata={"source": self._SOURCE},
            ))

        for source, rel, dest, group in self.defining_rels:
            s_norm = _sct_id(source)
            d_norm = _sct_id(dest)
            rel_norm = _normalize(rel)
            key = ("defrel", s_norm, rel_norm, d_norm)
            if key in added:
                continue
            added.add(key)

            theory.add_rule(Rule(
                head=f"{rel_norm}({s_norm}, {d_norm})",
                body=(f"isa(X, {s_norm})",),
                rule_type=RuleType.DEFEASIBLE,
                label=f"sct_def_{s_norm}_{rel_norm}_{d_norm}",
                metadata={
                    "source": self._SOURCE,
                    "relationship_group": group,
                },
            ))

        for concept, rel_type, target in self.gci_axioms:
            c_norm = _sct_id(concept)
            t_norm = _sct_id(target)
            rel_norm = _normalize(rel_type)
            key = ("gci", c_norm, rel_norm, t_norm)
            if key in added:
                continue
            added.add(key)

            theory.add_rule(Rule(
                head=f"{rel_norm}({c_norm}, {t_norm})",
                body=(),
                rule_type=RuleType.DEFEASIBLE,
                label=f"sct_gci_{c_norm}_{rel_norm}_{t_norm}",
                metadata={"source": self._SOURCE, "axiom_type": "GCI"},
            ))

        for child, parent, rel_type, old_target, new_target in self._property_overrides:
            child_norm = _sct_id(child)
            parent_norm = _sct_id(parent)
            rel_norm = _normalize(rel_type)
            old_norm = _sct_id(old_target)
            new_norm = _sct_id(new_target)

            key = ("override", child_norm, rel_norm, old_norm)
            if key in added:
                continue
            added.add(key)

            parent_rule_label = f"sct_def_{parent_norm}_{rel_norm}_{old_norm}"
            defeater_label = (
                f"sct_override_{child_norm}_{rel_norm}_{old_norm}"
            )

            theory.add_rule(Rule(
                head=f"~{rel_norm}(X, {old_norm})",
                body=(f"isa(X, {child_norm})",),
                rule_type=RuleType.DEFEATER,
                label=defeater_label,
                metadata={
                    "source": self._SOURCE,
                    "overrides_parent": parent_norm,
                    "new_target": new_norm,
                },
            ))
            theory.add_superiority(defeater_label, parent_rule_label)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping from Is-a relationships."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.isa_edges:
            taxonomy[_sct_id(child)].add(_sct_id(parent))
        return dict(taxonomy)


# -- Convenience function -------------------------------------------------

def extract_from_snomed(path: Path) -> Theory:
    """Extract a defeasible Theory from a SNOMED CT distribution.

    Auto-detects RF2 vs OWL format from the file contents.

    Args:
        path: Path to an RF2 snapshot file (sct2_Relationship_Snapshot_*)
              or an OWL distribution file.

    Returns:
        Theory with strict taxonomic rules, defeasible defining properties,
        GCI axioms, and property-override defeaters.
    """
    extractor = SnomedExtractor(path)
    extractor.load()
    extractor.extract()
    return extractor.to_theory()
