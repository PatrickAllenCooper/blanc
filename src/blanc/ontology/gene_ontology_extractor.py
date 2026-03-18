"""
Gene Ontology (GO) extraction for defeasible knowledge bases.

Parses the GO ontology (OBO format) and gene annotation files (GAF format)
to produce a defeasible theory with:
  - Strict taxonomic rules from the GO is_a hierarchy
  - Defeasible rules from positive gene-function annotations
  - Defeaters from NOT-qualified annotations

OBO source: http://current.geneontology.org/ontology/go-basic.obo
GAF source: http://current.geneontology.org/annotations/

Author: Patrick Cooper
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_GO_ID_PATTERN = re.compile(r"GO:\d{7}")

_DEFEATER_EXCLUDED_EVIDENCE = frozenset({"ND", "IEA"})

_GO_NAMESPACES = frozenset({
    "biological_process",
    "molecular_function",
    "cellular_component",
})


class GeneOntologyExtractor:
    """Extract knowledge from the Gene Ontology and GAF annotation files.

    Two data sources are combined:

    1. **OBO ontology** -- the directed acyclic graph of GO terms linked by
       ``is_a`` relations.  Each edge becomes a strict taxonomic rule.
    2. **GAF annotations** -- gene-to-GO-term associations curated by model
       organism databases.  Positive annotations become defeasible rules;
       NOT-qualified annotations become defeaters.

    Usage::

        extractor = GeneOntologyExtractor(Path("go-basic.obo"), [Path("goa_human.gaf")])
        extractor.load_ontology()
        for gaf in gaf_paths:
            extractor.load_annotations(gaf)
        extractor.extract()
        theory = extractor.to_theory()
    """

    def __init__(
        self,
        obo_path: Path,
        gaf_paths: list[Path] | None = None,
    ):
        if not obo_path.exists():
            raise FileNotFoundError(f"OBO file not found: {obo_path}")

        self.obo_path = obo_path
        self.gaf_paths: list[Path] = list(gaf_paths) if gaf_paths else []

        self.terms: Dict[str, Dict] = {}
        self.isa_edges: List[Tuple[str, str]] = []
        self.positive_annotations: List[Tuple[str, str, str]] = []
        self.negative_annotations: List[Tuple[str, str, str]] = []

    # ── OBO parsing ──────────────────────────────────────────────

    def load_ontology(self) -> None:
        """Parse the OBO file for GO terms, names, and is_a relations.

        Skips obsolete terms.  Only ``[Term]`` stanzas are processed;
        ``[Typedef]`` stanzas are ignored.
        """
        current: Optional[Dict] = None

        with open(self.obo_path, encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()

                if line == "[Term]":
                    if current and not current["is_obsolete"] and current["id"]:
                        self._commit_term(current)
                    current = {
                        "id": "",
                        "name": "",
                        "namespace": "",
                        "is_a": [],
                        "is_obsolete": False,
                    }
                    continue

                if line.startswith("[") and line.endswith("]"):
                    if current and not current["is_obsolete"] and current["id"]:
                        self._commit_term(current)
                    current = None
                    continue

                if current is None:
                    continue

                if line.startswith("id:"):
                    current["id"] = line[len("id:"):].strip()
                elif line.startswith("name:"):
                    current["name"] = line[len("name:"):].strip()
                elif line.startswith("namespace:"):
                    current["namespace"] = line[len("namespace:"):].strip()
                elif line.startswith("is_a:"):
                    parent_id = line[len("is_a:"):].strip().split("!")[0].strip()
                    if _GO_ID_PATTERN.match(parent_id):
                        current["is_a"].append(parent_id)
                elif line.startswith("is_obsolete:"):
                    if "true" in line.lower():
                        current["is_obsolete"] = True

        if current and not current["is_obsolete"] and current["id"]:
            self._commit_term(current)

        logger.info(
            "Loaded %d GO terms with %d is_a edges",
            len(self.terms),
            len(self.isa_edges),
        )

    def _commit_term(self, term: Dict) -> None:
        go_id = term["id"]
        self.terms[go_id] = {
            "name": term["name"],
            "namespace": term["namespace"],
        }
        for parent_id in term["is_a"]:
            self.isa_edges.append((go_id, parent_id))

    # ── GAF parsing ──────────────────────────────────────────────

    def load_annotations(self, gaf_path: Path) -> None:
        """Parse a GAF 2.x file for gene-GO term annotations.

        GAF columns (0-indexed):
            0  DB
            1  DB Object ID
            2  DB Object Symbol  (gene/protein name)
            3  Qualifier          (NOT | contributes_to | colocalizes_with | ...)
            4  GO ID
            5  DB:Reference
            6  Evidence Code
            7  With/From
            8  Aspect
            9  DB Object Name
            10 DB Object Synonym
            11 DB Object Type
            12 Taxon
            13 Date
            14 Assigned By
        """
        if not gaf_path.exists():
            raise FileNotFoundError(f"GAF file not found: {gaf_path}")

        import gzip as _gzip

        opener = (
            lambda p: _gzip.open(p, "rt", encoding="utf-8")
            if str(p).endswith(".gz")
            else open(p, encoding="utf-8")
        )
        with opener(gaf_path) as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line or line.startswith("!"):
                    continue

                cols = line.split("\t")
                if len(cols) < 15:
                    continue

                gene_symbol = cols[2]
                qualifier = cols[3]
                go_id = cols[4]
                evidence_code = cols[6]

                if not _GO_ID_PATTERN.match(go_id):
                    continue

                is_negative = "NOT" in qualifier.upper()

                if is_negative:
                    if evidence_code in _DEFEATER_EXCLUDED_EVIDENCE:
                        continue
                    self.negative_annotations.append(
                        (gene_symbol, go_id, evidence_code)
                    )
                else:
                    self.positive_annotations.append(
                        (gene_symbol, go_id, evidence_code)
                    )

        logger.info(
            "Loaded annotations from %s: %d positive, %d negative",
            gaf_path.name,
            len(self.positive_annotations),
            len(self.negative_annotations),
        )

    # ── Full extraction ──────────────────────────────────────────

    def extract(self) -> None:
        """Run the complete extraction pipeline.

        Loads the ontology (if not already loaded), then loads all
        configured GAF files.
        """
        if not self.terms:
            self.load_ontology()

        for gaf_path in self.gaf_paths:
            self.load_annotations(gaf_path)

    # ── Conversion ───────────────────────────────────────────────

    def to_theory(self) -> Theory:
        """Convert extracted GO data to a defeasible Theory.

        Mapping:
            is_a edges           -> strict rules   ``isa(child, parent)``
            positive annotations -> defeasible     ``has_function(gene, term)``
            negative annotations -> defeaters      ``~has_function(gene, term)``
        """
        theory = Theory()
        added: Set[tuple] = set()

        for child_id, parent_id in self.isa_edges:
            child_norm = self._normalize_go_id(child_id)
            parent_norm = self._normalize_go_id(parent_id)
            key = ("isa", child_norm, parent_norm)
            if key in added:
                continue
            added.add(key)

            child_name = self._term_label(child_id)
            parent_name = self._term_label(parent_id)

            theory.add_rule(Rule(
                head=f"isa({child_norm}, {parent_norm})",
                body=(),
                rule_type=RuleType.STRICT,
                label=f"go_tax_{child_norm}_{parent_norm}",
                metadata={
                    "source": "GeneOntology",
                    "child_name": child_name,
                    "parent_name": parent_name,
                },
            ))

        for gene, go_id, evidence in self.positive_annotations:
            gene_norm = self._normalize_name(gene)
            go_norm = self._normalize_go_id(go_id)
            key = ("has_function", gene_norm, go_norm)
            if key in added:
                continue
            added.add(key)

            theory.add_rule(Rule(
                head=f"has_function({gene_norm}, {go_norm})",
                body=(),
                rule_type=RuleType.DEFEASIBLE,
                label=f"go_fn_{gene_norm}_{go_norm}",
                metadata={
                    "source": "GeneOntology",
                    "evidence": evidence,
                    "go_name": self._term_label(go_id),
                },
            ))

        for gene, go_id, evidence in self.negative_annotations:
            gene_norm = self._normalize_name(gene)
            go_norm = self._normalize_go_id(go_id)
            key = ("~has_function", gene_norm, go_norm)
            if key in added:
                continue
            added.add(key)

            theory.add_rule(Rule(
                head=f"~has_function({gene_norm}, {go_norm})",
                body=(),
                rule_type=RuleType.DEFEATER,
                label=f"go_dfn_{gene_norm}_{go_norm}",
                metadata={
                    "source": "GeneOntology",
                    "evidence": evidence,
                    "go_name": self._term_label(go_id),
                },
            ))

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return GO term -> {parent terms} mapping.

        Compatible with the cross-ontology combiner interface.
        """
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.isa_edges:
            taxonomy[child].add(parent)
        return dict(taxonomy)

    # ── Helpers ───────────────────────────────────────────────────

    def _normalize_go_id(self, go_id: str) -> str:
        """GO:0008150 -> go_0008150"""
        return go_id.lower().replace(":", "_")

    def _normalize_name(self, name: str) -> str:
        name = name.lower().replace(" ", "_").replace("-", "_")
        return "".join(c for c in name if c.isalnum() or c == "_")

    def _term_label(self, go_id: str) -> str:
        info = self.terms.get(go_id)
        if info and info["name"]:
            return info["name"]
        return go_id


# ── Convenience function ─────────────────────────────────────────

def extract_from_gene_ontology(
    obo_path: Path,
    gaf_paths: list[Path] | None = None,
) -> Theory:
    """Extract a defeasible theory from Gene Ontology data.

    Args:
        obo_path: Path to go-basic.obo ontology file.
        gaf_paths: Optional list of GAF annotation files to include.

    Returns:
        Theory with GO taxonomic rules and gene-function annotations.
    """
    extractor = GeneOntologyExtractor(obo_path, gaf_paths)
    extractor.extract()
    return extractor.to_theory()
