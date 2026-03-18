"""
DBpedia N-Triples extractor for defeasible knowledge bases.

Stream-parses N-Triples (.nt) files from DBpedia and extracts taxonomic
relations, type assertions, ontology properties, and inconsistency defeaters.

Conversion rules:
    rdf:type                -> ground instance fact
    rdfs:subClassOf         -> strict taxonomic rule
    dbo:* properties        -> defeasible property rules
    Infobox/ontology clash  -> defeater

Primary sources: instance-types, mappingbased-objects from
https://databus.dbpedia.org/.

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

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")

_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_RDFS_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
_DBO_PREFIX = "http://dbpedia.org/ontology/"
_DBR_PREFIX = "http://dbpedia.org/resource/"
_DBP_PREFIX = "http://dbpedia.org/property/"

_NT_LINE_RE = re.compile(
    r"<([^>]+)>\s+<([^>]+)>\s+(?:<([^>]+)>|\"((?:[^\"\\]|\\.)*)\""
    r"(?:\^\^<[^>]+>|@[a-zA-Z-]+)?)\s*\.\s*$"
)


def _normalize(name: str) -> str:
    """Lowercase, replace spaces/hyphens/camelCase with underscores, strip non-alnum."""
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = _NORMALIZE_RE.sub("", name)
    if name and not name[0].isalpha():
        name = "c_" + name
    return name


def _local_name(uri: str) -> str:
    """Extract the local name from a full URI.

    For ``<http://dbpedia.org/ontology/Person>`` returns ``Person``.
    """
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    if "/" in uri:
        return uri.rsplit("/", 1)[-1]
    return uri


def _parse_nt_line(line: str) -> Optional[Tuple[str, str, str]]:
    """Parse a single N-Triples line into (subject, predicate, object).

    Returns None for comments, blank lines, or unparseable lines.
    """
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    m = _NT_LINE_RE.match(stripped)
    if not m:
        return None

    subj = m.group(1)
    pred = m.group(2)
    obj = m.group(3) if m.group(3) is not None else m.group(4)
    return subj, pred, obj


class DbpediaExtractor:
    """Extract defeasible knowledge from DBpedia N-Triples dumps.

    Stream-parses the NT file line by line so that multi-gigabyte files
    never need to reside in memory.  Collects:

        - ``rdf:type`` pairs          (ground instance facts)
        - ``rdfs:subClassOf`` pairs   (strict taxonomy)
        - ``dbo:*`` properties        (defeasible property rules)
        - infobox/ontology clashes    (defeaters)

    Infobox-derived type triples (from ``dbp:`` predicates) that conflict
    with ontology-derived types (from ``dbo:`` predicates) for the same
    subject are emitted as defeaters.
    """

    _SOURCE = "DBpedia"

    def __init__(
        self,
        nt_path: Path,
        max_triples: int | None = None,
    ):
        self.nt_path = Path(nt_path)
        if not self.nt_path.exists():
            raise FileNotFoundError(f"N-Triples file not found: {self.nt_path}")

        self.max_triples = max_triples

        self.type_pairs: List[Tuple[str, str]] = []
        self.subclass_pairs: List[Tuple[str, str]] = []
        self.dbo_properties: List[Tuple[str, str, str]] = []
        self.dbp_type_map: Dict[str, Set[str]] = defaultdict(set)
        self.dbo_type_map: Dict[str, Set[str]] = defaultdict(set)

        self._triples_parsed = 0
        self._triples_skipped = 0

    def extract(self) -> None:
        """Stream-parse the N-Triples file and populate relation lists."""
        self._triples_parsed = 0
        self._triples_skipped = 0

        logger.info("Streaming DBpedia N-Triples from %s ...", self.nt_path)

        with open(self.nt_path, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh, 1):
                if self.max_triples and self._triples_parsed >= self.max_triples:
                    logger.info(
                        "Reached max_triples=%d at line %d.",
                        self.max_triples, line_no,
                    )
                    break

                triple = _parse_nt_line(line)
                if triple is None:
                    continue

                subj, pred, obj = triple
                if not subj or not pred or not obj:
                    self._triples_skipped += 1
                    continue

                self._classify_triple(subj, pred, obj)
                self._triples_parsed += 1

                if self._triples_parsed % 500_000 == 0:
                    logger.info(
                        "  ... %d triples parsed (%d type, %d subClassOf, "
                        "%d dbo properties)",
                        self._triples_parsed,
                        len(self.type_pairs),
                        len(self.subclass_pairs),
                        len(self.dbo_properties),
                    )

        logger.info(
            "DBpedia extraction complete: %d triples parsed, %d skipped. "
            "type=%d, subClassOf=%d, dbo_properties=%d",
            self._triples_parsed,
            self._triples_skipped,
            len(self.type_pairs),
            len(self.subclass_pairs),
            len(self.dbo_properties),
        )

    def _classify_triple(self, subj: str, pred: str, obj: str) -> None:
        """Route a parsed triple into the appropriate collection."""
        subj_local = _local_name(subj)
        obj_local = _local_name(obj)

        if pred == _RDF_TYPE:
            self.type_pairs.append((subj_local, obj_local))
            if subj.startswith(_DBO_PREFIX) or obj.startswith(_DBO_PREFIX):
                self.dbo_type_map[subj_local].add(obj_local)
            elif subj.startswith(_DBP_PREFIX) or obj.startswith(_DBP_PREFIX):
                self.dbp_type_map[subj_local].add(obj_local)
            else:
                self.dbo_type_map[subj_local].add(obj_local)

        elif pred == _RDFS_SUBCLASS:
            self.subclass_pairs.append((subj_local, obj_local))

        elif pred.startswith(_DBO_PREFIX):
            prop_name = pred[len(_DBO_PREFIX):]
            self.dbo_properties.append((subj_local, prop_name, obj_local))

    def _find_type_conflicts(self) -> List[Tuple[str, str, str]]:
        """Detect entities whose infobox-derived types conflict with ontology types.

        Returns (entity, infobox_type, ontology_type) triples where the two
        type sources disagree.
        """
        conflicts: List[Tuple[str, str, str]] = []
        shared_entities = set(self.dbp_type_map.keys()) & set(self.dbo_type_map.keys())
        for entity in shared_entities:
            infobox_types = self.dbp_type_map[entity]
            ontology_types = self.dbo_type_map[entity]
            infobox_only = infobox_types - ontology_types
            for ib_type in infobox_only:
                for ont_type in ontology_types:
                    conflicts.append((entity, ib_type, ont_type))
        return conflicts

    def to_theory(self) -> Theory:
        """Build a ``Theory`` from the extracted DBpedia relations.

        Returns:
            Theory containing strict taxonomy, ground type facts,
            defeasible property rules, and type-conflict defeaters.
        """
        theory = Theory()
        added: Set[tuple] = set()

        for child, parent in self.subclass_pairs:
            cn, pn = _normalize(child), _normalize(parent)
            if not cn or not pn or cn == pn:
                continue
            key = ("subclass", cn, pn)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"isa({cn}, {pn})",
                    body=(),
                    rule_type=RuleType.STRICT,
                    label=f"dbp_tax_{cn}_{pn}",
                    metadata={"source": self._SOURCE, "relation": "subClassOf"},
                ))
                added.add(key)

        for inst, cls in self.type_pairs:
            in_norm, cn = _normalize(inst), _normalize(cls)
            if not in_norm or not cn:
                continue
            fact = f"instance({in_norm}, {cn})"
            if fact not in theory.facts:
                theory.add_fact(fact)

        for subj, prop, obj in self.dbo_properties:
            sn = _normalize(subj)
            pn = _normalize(prop)
            on = _normalize(obj)
            if not sn or not pn or not on:
                continue
            key = ("dbo", sn, pn, on)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"{pn}({sn}, {on})",
                    body=(),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"dbp_dbo_{pn}_{sn}_{on}",
                    metadata={
                        "source": self._SOURCE,
                        "relation": f"dbo:{prop}",
                    },
                ))
                added.add(key)

        for entity, ib_type, ont_type in self._find_type_conflicts():
            en = _normalize(entity)
            ibn = _normalize(ib_type)
            onn = _normalize(ont_type)
            if not en or not ibn or not onn:
                continue
            key = ("conflict", en, ibn, onn)
            if key not in added:
                defeater_label = f"dbp_conflict_{en}_{ibn}_{onn}"
                theory.add_rule(Rule(
                    head=f"~instance({en}, {ibn})",
                    body=(f"instance({en}, {onn})",),
                    rule_type=RuleType.DEFEATER,
                    label=defeater_label,
                    metadata={
                        "source": self._SOURCE,
                        "relation": "type_conflict",
                        "infobox_type": ib_type,
                        "ontology_type": ont_type,
                    },
                ))
                added.add(key)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.subclass_pairs:
            cn, pn = _normalize(child), _normalize(parent)
            if cn and pn and cn != pn:
                taxonomy[cn].add(pn)
        return dict(taxonomy)

    @property
    def stats(self) -> Dict[str, int]:
        """Summary statistics from the most recent extraction."""
        return {
            "triples_parsed": self._triples_parsed,
            "triples_skipped": self._triples_skipped,
            "type_pairs": len(self.type_pairs),
            "subclass_pairs": len(self.subclass_pairs),
            "dbo_properties": len(self.dbo_properties),
            "type_conflicts": len(self._find_type_conflicts()),
        }


def extract_from_dbpedia(
    nt_path: Optional[Path] = None,
    max_triples: int | None = None,
) -> Theory:
    """Extract a defeasible theory from a DBpedia N-Triples dump.

    Args:
        nt_path: Path to the ``.nt`` file.  Defaults to
            ``data/dbpedia/instance-types_lang=en.ttl``.
        max_triples: Cap on triples retained (None = all).

    Returns:
        Theory with DBpedia-derived strict taxonomy and defeasible property rules.
    """
    if nt_path is None:
        nt_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "dbpedia"
            / "instance-types_lang=en.ttl"
        )

    extractor = DbpediaExtractor(nt_path, max_triples=max_triples)
    extractor.extract()
    return extractor.to_theory()
