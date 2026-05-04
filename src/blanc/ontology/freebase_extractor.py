"""
Freebase N-Triples extractor for defeasible knowledge bases.

Stream-parses gzipped N-Triples from the Freebase RDF dump and extracts
type assignments, instance relations, typed properties, and conflicting
type assertions as defeaters.

Conversion rules:
    type.object.type        -> strict type assignment fact
    type.type.instance      -> ground instance fact
    Other typed relations   -> defeasible property rules
    Conflicting types       -> defeaters

Primary source: freebase-rdf-latest.gz from
https://developers.google.com/freebase.

Author: Anonymous Authors
"""

from __future__ import annotations

import gzip
import logging
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")

_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_FREEBASE_NS = "http://rdf.freebase.com/ns/"
_FREEBASE_KEY = "http://rdf.freebase.com/key/"

_TYPE_OBJECT_TYPE = "type.object.type"
_TYPE_TYPE_INSTANCE = "type.type.instance"

_NT_LINE_RE = re.compile(
    r"<([^>]+)>\s+<([^>]+)>\s+(?:<([^>]+)>|\"((?:[^\"\\]|\\.)*)\""
    r"(?:\^\^<[^>]+>|@[a-zA-Z-]+)?)\s*\.\s*$"
)

_SKIP_PREDICATES: frozenset[str] = frozenset({
    "type.object.name",
    "type.object.key",
    "type.object.id",
    "common.topic.alias",
    "common.topic.description",
    "common.topic.notable_types",
    "common.topic.topic_equivalent_webpage",
    "kg.object_profile.prominent_type",
})


def _normalize(name: str) -> str:
    """Lowercase, replace dots/slashes/hyphens with underscores, strip non-alnum."""
    name = name.replace(".", "_").replace("/", "_")
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = _NORMALIZE_RE.sub("", name)
    if name and not name[0].isalpha():
        name = "c_" + name
    return name


def _freebase_local(uri: str) -> str:
    """Extract the Freebase local path from a full URI.

    ``<http://rdf.freebase.com/ns/m.012abc>`` -> ``m.012abc``
    ``<http://rdf.freebase.com/ns/type.object.type>`` -> ``type.object.type``
    """
    if uri.startswith(_FREEBASE_NS):
        return uri[len(_FREEBASE_NS):]
    if uri.startswith(_FREEBASE_KEY):
        return uri[len(_FREEBASE_KEY):]
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    if "/" in uri:
        return uri.rsplit("/", 1)[-1]
    return uri


def _mid_to_id(mid: str) -> str:
    """Convert a Freebase MID to a normalized entity identifier.

    ``m.012abc`` -> ``m_012abc``
    ``/m/012abc`` -> ``m_012abc``
    """
    mid = mid.lstrip("/").replace("/", "_").replace(".", "_")
    return mid


def _type_path_to_name(type_path: str) -> str:
    """Convert a Freebase type path to a readable name.

    ``biology.organism`` -> ``biology_organism``
    ``/type/typename``   -> ``type_typename``
    """
    return type_path.lstrip("/").replace("/", "_").replace(".", "_")


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


def _is_mid(local: str) -> bool:
    """Check whether a Freebase local name is a MID (machine ID)."""
    return local.startswith("m.") or local.startswith("g.")


class FreebaseExtractor:
    """Extract defeasible knowledge from Freebase gzipped N-Triples.

    Stream-parses the gzipped NT file line by line.  Collects:

        - ``type.object.type`` triples  (strict type assignment facts)
        - ``type.type.instance`` triples (instance facts)
        - Other typed relations          (defeasible property rules)
        - Conflicting type assertions    (defeaters)

    Freebase entities are identified by MIDs (``/m/012abc``) and types
    follow the ``/type/typename`` convention.
    """

    _SOURCE = "Freebase"

    def __init__(
        self,
        nt_path: Path,
        max_triples: int | None = None,
    ):
        self.nt_path = Path(nt_path)
        if not self.nt_path.exists():
            raise FileNotFoundError(f"N-Triples file not found: {self.nt_path}")

        self.max_triples = max_triples

        self.type_assignments: List[Tuple[str, str]] = []
        self.instance_pairs: List[Tuple[str, str]] = []
        self.typed_relations: List[Tuple[str, str, str]] = []
        self._entity_types: Dict[str, Set[str]] = defaultdict(set)

        self._triples_parsed = 0
        self._triples_skipped = 0

    def extract(self) -> None:
        """Stream-parse the (optionally gzipped) N-Triples file."""
        self._triples_parsed = 0
        self._triples_skipped = 0

        logger.info("Streaming Freebase N-Triples from %s ...", self.nt_path)

        opener = (
            gzip.open if self.nt_path.suffix == ".gz" else open
        )

        with opener(self.nt_path, "rt", encoding="utf-8", errors="replace") as fh:
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

                if self._triples_parsed % 1_000_000 == 0:
                    logger.info(
                        "  ... %d triples parsed (%d type assignments, "
                        "%d instances, %d relations)",
                        self._triples_parsed,
                        len(self.type_assignments),
                        len(self.instance_pairs),
                        len(self.typed_relations),
                    )

        logger.info(
            "Freebase extraction complete: %d triples parsed, %d skipped. "
            "type_assignments=%d, instances=%d, relations=%d",
            self._triples_parsed,
            self._triples_skipped,
            len(self.type_assignments),
            len(self.instance_pairs),
            len(self.typed_relations),
        )

    def _classify_triple(self, subj: str, pred: str, obj: str) -> None:
        """Route a parsed triple into the appropriate collection."""
        pred_local = _freebase_local(pred)

        if pred_local in _SKIP_PREDICATES:
            return

        subj_local = _freebase_local(subj)

        if pred_local == _TYPE_OBJECT_TYPE or pred == _RDF_TYPE:
            obj_local = _freebase_local(obj)
            type_name = _type_path_to_name(obj_local)
            entity_id = _mid_to_id(subj_local) if _is_mid(subj_local) else subj_local
            self.type_assignments.append((entity_id, type_name))
            self._entity_types[entity_id].add(type_name)

        elif pred_local == _TYPE_TYPE_INSTANCE:
            obj_local = _freebase_local(obj)
            type_name = _type_path_to_name(subj_local)
            entity_id = _mid_to_id(obj_local) if _is_mid(obj_local) else obj_local
            self.instance_pairs.append((entity_id, type_name))
            self._entity_types[entity_id].add(type_name)

        else:
            obj_local = _freebase_local(obj)
            if not _is_mid(pred_local):
                entity_id = (
                    _mid_to_id(subj_local) if _is_mid(subj_local) else subj_local
                )
                obj_id = (
                    _mid_to_id(obj_local) if _is_mid(obj_local) else obj_local
                )
                self.typed_relations.append(
                    (entity_id, _type_path_to_name(pred_local), obj_id)
                )

    def _find_type_conflicts(self) -> List[Tuple[str, str, str]]:
        """Detect entities with mutually-inconsistent type assertions.

        Freebase often assigns both a general and a conflicting specific
        type to the same entity.  This method pairs types from different
        Freebase domains (e.g. ``people.person`` vs ``fictional_universe.*``)
        to generate defeaters.
        """
        conflicts: List[Tuple[str, str, str]] = []
        for entity, types in self._entity_types.items():
            if len(types) < 2:
                continue
            type_list = sorted(types)
            domains_seen: Dict[str, str] = {}
            for t in type_list:
                domain = t.split("_", 1)[0] if "_" in t else t
                if domain in domains_seen and domains_seen[domain] != t:
                    conflicts.append((entity, domains_seen[domain], t))
                domains_seen[domain] = t
        return conflicts

    def to_theory(self) -> Theory:
        """Build a ``Theory`` from the extracted Freebase relations.

        Returns:
            Theory containing strict type facts, instance facts,
            defeasible relation rules, and type-conflict defeaters.
        """
        theory = Theory()
        added: Set[tuple] = set()

        for entity, type_name in self.type_assignments:
            en = _normalize(entity)
            tn = _normalize(type_name)
            if not en or not tn:
                continue
            fact = f"instance({en}, {tn})"
            if fact not in theory.facts:
                theory.add_fact(fact)

        for entity, type_name in self.instance_pairs:
            en = _normalize(entity)
            tn = _normalize(type_name)
            if not en or not tn:
                continue
            fact = f"instance({en}, {tn})"
            if fact not in theory.facts:
                theory.add_fact(fact)

        for subj, rel, obj in self.typed_relations:
            sn = _normalize(subj)
            rn = _normalize(rel)
            on = _normalize(obj)
            if not sn or not rn or not on:
                continue
            key = ("rel", sn, rn, on)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"{rn}({sn}, {on})",
                    body=(),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"fb_rel_{rn}_{sn}_{on}",
                    metadata={
                        "source": self._SOURCE,
                        "relation": rel,
                    },
                ))
                added.add(key)

        for entity, type_a, type_b in self._find_type_conflicts():
            en = _normalize(entity)
            an = _normalize(type_a)
            bn = _normalize(type_b)
            if not en or not an or not bn:
                continue
            key = ("conflict", en, an, bn)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"~instance({en}, {an})",
                    body=(f"instance({en}, {bn})",),
                    rule_type=RuleType.DEFEATER,
                    label=f"fb_conflict_{en}_{an}_{bn}",
                    metadata={
                        "source": self._SOURCE,
                        "relation": "type_conflict",
                        "type_a": type_a,
                        "type_b": type_b,
                    },
                ))
                added.add(key)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner.

        Freebase does not have an explicit subclass hierarchy, so the
        taxonomy is built from type assignments: each entity maps to its
        assigned types.
        """
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for entity, type_name in self.type_assignments:
            en = _normalize(entity)
            tn = _normalize(type_name)
            if en and tn:
                taxonomy[en].add(tn)
        for entity, type_name in self.instance_pairs:
            en = _normalize(entity)
            tn = _normalize(type_name)
            if en and tn:
                taxonomy[en].add(tn)
        return dict(taxonomy)

    @property
    def stats(self) -> Dict[str, int]:
        """Summary statistics from the most recent extraction."""
        return {
            "triples_parsed": self._triples_parsed,
            "triples_skipped": self._triples_skipped,
            "type_assignments": len(self.type_assignments),
            "instance_pairs": len(self.instance_pairs),
            "typed_relations": len(self.typed_relations),
            "type_conflicts": len(self._find_type_conflicts()),
        }


def extract_from_freebase(
    nt_path: Optional[Path] = None,
    max_triples: int | None = None,
) -> Theory:
    """Extract a defeasible theory from a Freebase N-Triples dump.

    Args:
        nt_path: Path to the ``.nt.gz`` or ``.nt`` file.  Defaults to
            ``data/freebase/freebase-rdf-latest.gz``.
        max_triples: Cap on triples retained (None = all).

    Returns:
        Theory with Freebase-derived type facts and defeasible property rules.
    """
    if nt_path is None:
        nt_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "freebase"
            / "freebase-rdf-latest.gz"
        )

    extractor = FreebaseExtractor(nt_path, max_triples=max_triples)
    extractor.extract()
    return extractor.to_theory()
