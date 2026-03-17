"""
YAGO 4.5 full extractor for defeasible knowledge bases.

Stream-parses Turtle (TTL) files from YAGO 4.5 without loading them into
rdflib (which cannot handle 12 GB files).  Extracts taxonomic relations,
type assertions, and schema.org / yago property triples, converting them
into strict rules, defeasible rules, and ground facts.

Conversion rules:
    rdfs:subClassOf         -> strict taxonomic rule
    rdf:type                -> ground instance fact
    schema:* properties     -> defeasible property rules
    yago:* properties       -> defeasible property rules

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

SCHEMA_PROPERTIES_OF_INTEREST: frozenset[str] = frozenset({
    "typicalAgeRange",
    "material",
    "nutritionInformation",
    "memberOf",
    "isPartOf",
    "about",
    "gender",
    "nationality",
    "birthPlace",
    "deathPlace",
    "knownFor",
    "worksFor",
    "alumniOf",
    "affiliation",
    "spouse",
    "parent",
    "children",
    "sibling",
    "award",
    "genre",
    "author",
    "director",
    "producer",
    "composer",
    "performer",
    "containedInPlace",
    "containsPlace",
    "locatedIn",
    "occupationalCategory",
    "category",
})


def _normalize(name: str) -> str:
    """Lowercase, replace spaces/hyphens/camelCase with underscores, strip non-alnum."""
    name = re.sub(r"([a-z])([A-Z])", r"\1_\2", name)
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = _NORMALIZE_RE.sub("", name)
    if name and not name[0].isalpha():
        name = "c_" + name
    return name


def _local_name(uri: str) -> str:
    """Extract the local name from a full URI or prefixed name.

    For ``<http://schema.org/Person>`` returns ``Person``.
    For ``schema:Person`` returns ``Person``.
    """
    if "#" in uri:
        return uri.rsplit("#", 1)[-1]
    if "/" in uri:
        return uri.rsplit("/", 1)[-1]
    if ":" in uri:
        return uri.split(":", 1)[-1]
    return uri


class _TtlLineParser:
    """Minimal streaming parser for Turtle (TTL) triples.

    Handles one triple per line plus multi-line continuations terminated
    by `` .``.  Resolves prefixed names using ``@prefix`` declarations
    collected during the parse.
    """

    def __init__(self) -> None:
        self.prefixes: Dict[str, str] = {}
        self._buffer: str = ""

    def feed_line(self, line: str) -> Optional[Tuple[str, str, str]]:
        """Feed a single line and return a (subject, predicate, object) triple
        if the line completes one, or None otherwise.
        """
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            return None

        if stripped.startswith("@prefix") or stripped.startswith("PREFIX"):
            self._register_prefix(stripped)
            return None

        if stripped.startswith("@base") or stripped.startswith("BASE"):
            return None

        self._buffer += " " + stripped if self._buffer else stripped

        if not self._buffer.endswith("."):
            return None

        statement = self._buffer[:-1].strip()
        self._buffer = ""

        return self._parse_triple(statement)

    def _register_prefix(self, line: str) -> None:
        m = re.match(
            r'(?:@prefix|PREFIX)\s+(\S*?:)\s+<([^>]+)>\s*\.?', line, re.IGNORECASE
        )
        if m:
            self.prefixes[m.group(1)] = m.group(2)

    def _parse_triple(self, statement: str) -> Optional[Tuple[str, str, str]]:
        """Split a statement into subject, predicate, object.

        Handles ``<URI>``, ``prefix:local``, and ``"literal"^^<type>`` forms.
        Splits on semicolons/commas are not supported (YAGO TTL uses one
        triple per statement in practice).
        """
        tokens = self._tokenize(statement)
        if len(tokens) < 3:
            return None

        subj = self._resolve(tokens[0])
        pred = self._resolve(tokens[1])
        obj = self._resolve(" ".join(tokens[2:]))

        if subj and pred and obj:
            return subj, pred, obj
        return None

    def _tokenize(self, statement: str) -> List[str]:
        """Tokenize a TTL statement respecting angle brackets and quotes."""
        tokens: List[str] = []
        i = 0
        n = len(statement)
        while i < n:
            ch = statement[i]
            if ch in " \t\r\n":
                i += 1
                continue
            if ch == "<":
                j = statement.index(">", i) + 1
                tokens.append(statement[i:j])
                i = j
            elif ch == '"':
                j = i + 1
                while j < n:
                    if statement[j] == "\\" and j + 1 < n:
                        j += 2
                        continue
                    if statement[j] == '"':
                        j += 1
                        break
                    j += 1
                while j < n and statement[j] not in " \t\r\n":
                    j += 1
                tokens.append(statement[i:j])
                i = j
            else:
                j = i
                while j < n and statement[j] not in " \t\r\n":
                    j += 1
                tokens.append(statement[i:j])
                i = j
        return tokens

    def _resolve(self, token: str) -> str:
        """Resolve a token to a full URI string."""
        if token.startswith("<") and token.endswith(">"):
            return token[1:-1]

        if token.startswith('"'):
            return self._resolve_literal(token)

        if token.startswith("_:"):
            return ""

        if ":" in token:
            prefix, _, local = token.partition(":")
            prefix_key = prefix + ":"
            if prefix_key in self.prefixes:
                return self.prefixes[prefix_key] + local
            return token

        return token

    @staticmethod
    def _resolve_literal(token: str) -> str:
        """Extract value from a quoted literal, stripping datatype/lang tags."""
        if "^^" in token:
            value_part = token.split("^^")[0]
        elif token.endswith('"'):
            value_part = token
        elif '"@' in token:
            value_part = token.split('"@')[0] + '"'
        else:
            value_part = token

        if value_part.startswith('"') and value_part.endswith('"'):
            return value_part[1:-1]
        return value_part


_RDF_TYPE = "http://www.w3.org/1999/02/22-rdf-syntax-ns#type"
_RDFS_SUBCLASS = "http://www.w3.org/2000/01/rdf-schema#subClassOf"
_SCHEMA_ORG = "http://schema.org/"
_YAGO_PREFIX = "http://yago-knowledge.org/resource/"


class YagoFullExtractor:
    """Extract defeasible knowledge from YAGO 4.5 Turtle dumps.

    Stream-parses the TTL file line by line so that multi-gigabyte files
    never need to reside in memory.  Collects:

        - ``rdfs:subClassOf`` pairs   (strict taxonomy)
        - ``rdf:type`` pairs          (ground instance facts)
        - ``schema:*`` properties     (defeasible property rules)
        - ``yago:*`` properties       (defeasible property rules)
    """

    _SOURCE = "YAGO4.5"

    def __init__(
        self,
        ttl_path: Path,
        max_triples: int | None = None,
        domain_profile: Optional[object] = None,
    ):
        self.ttl_path = Path(ttl_path)
        if not self.ttl_path.exists():
            raise FileNotFoundError(f"TTL file not found: {self.ttl_path}")

        self.max_triples = max_triples
        self.domain_profile = domain_profile

        self.subclass_pairs: List[Tuple[str, str]] = []
        self.type_pairs: List[Tuple[str, str]] = []
        self.schema_properties: List[Tuple[str, str, str]] = []
        self.yago_properties: List[Tuple[str, str, str]] = []

        self._triples_parsed = 0
        self._triples_skipped = 0

    def extract(self) -> None:
        """Stream-parse the TTL file and populate relation lists."""
        parser = _TtlLineParser()
        self._triples_parsed = 0
        self._triples_skipped = 0

        logger.info("Streaming YAGO TTL from %s ...", self.ttl_path)

        with open(self.ttl_path, "r", encoding="utf-8", errors="replace") as fh:
            for line_no, line in enumerate(fh, 1):
                if self.max_triples and self._triples_parsed >= self.max_triples:
                    logger.info(
                        "Reached max_triples=%d at line %d.",
                        self.max_triples, line_no,
                    )
                    break

                triple = parser.feed_line(line)
                if triple is None:
                    continue

                subj, pred, obj = triple
                if not subj or not pred or not obj:
                    self._triples_skipped += 1
                    continue

                subj_local = _local_name(subj)
                obj_local = _local_name(obj)

                if self.domain_profile is not None:
                    if not self._matches_domain(subj_local, obj_local):
                        self._triples_skipped += 1
                        continue

                self._classify_triple(subj, pred, obj, subj_local, obj_local)
                self._triples_parsed += 1

                if self._triples_parsed % 500_000 == 0:
                    logger.info(
                        "  ... %d triples parsed (%d subClassOf, %d type, "
                        "%d schema, %d yago)",
                        self._triples_parsed,
                        len(self.subclass_pairs),
                        len(self.type_pairs),
                        len(self.schema_properties),
                        len(self.yago_properties),
                    )

        logger.info(
            "YAGO extraction complete: %d triples parsed, %d skipped. "
            "subClassOf=%d, type=%d, schema=%d, yago=%d",
            self._triples_parsed,
            self._triples_skipped,
            len(self.subclass_pairs),
            len(self.type_pairs),
            len(self.schema_properties),
            len(self.yago_properties),
        )

    def _classify_triple(
        self,
        subj: str,
        pred: str,
        obj: str,
        subj_local: str,
        obj_local: str,
    ) -> None:
        """Route a parsed triple into the appropriate collection."""
        if pred == _RDFS_SUBCLASS:
            self.subclass_pairs.append((subj_local, obj_local))

        elif pred == _RDF_TYPE:
            self.type_pairs.append((subj_local, obj_local))

        elif pred.startswith(_SCHEMA_ORG):
            prop_name = pred[len(_SCHEMA_ORG):]
            self.schema_properties.append((subj_local, prop_name, obj_local))

        elif pred.startswith(_YAGO_PREFIX):
            prop_name = pred[len(_YAGO_PREFIX):]
            self.yago_properties.append((subj_local, prop_name, obj_local))

    def _matches_domain(self, subj_local: str, obj_local: str) -> bool:
        """Check whether subject or object matches the active domain profile."""
        profile = self.domain_profile
        if hasattr(profile, "matches"):
            return profile.matches(subj_local) or profile.matches(obj_local)
        return True

    def to_theory(self) -> Theory:
        """Build a ``Theory`` from the extracted YAGO relations.

        Returns:
            Theory containing strict taxonomy, ground type facts, and
            defeasible schema/yago property rules.
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
                    label=f"yago_tax_{cn}_{pn}",
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

        for subj, prop, obj in self.schema_properties:
            sn = _normalize(subj)
            pn = _normalize(prop)
            on = _normalize(obj)
            if not sn or not pn or not on:
                continue
            key = ("schema", sn, pn, on)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"{pn}({sn}, {on})",
                    body=(),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"yago_schema_{pn}_{sn}_{on}",
                    metadata={
                        "source": self._SOURCE,
                        "relation": f"schema:{prop}",
                    },
                ))
                added.add(key)

        for subj, prop, obj in self.yago_properties:
            sn = _normalize(subj)
            pn = _normalize(prop)
            on = _normalize(obj)
            if not sn or not pn or not on:
                continue
            key = ("yago", sn, pn, on)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"{pn}({sn}, {on})",
                    body=(),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"yago_prop_{pn}_{sn}_{on}",
                    metadata={
                        "source": self._SOURCE,
                        "relation": f"yago:{prop}",
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

    def get_properties(self) -> Dict[str, List[Tuple[str, str]]]:
        """Return concept -> [(relation, value), ...] for the cross-ontology combiner."""
        properties: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for subj, prop, obj in self.schema_properties:
            sn = _normalize(subj)
            on = _normalize(obj)
            if sn and on:
                properties[sn].append((f"schema:{prop}", on))
        for subj, prop, obj in self.yago_properties:
            sn = _normalize(subj)
            on = _normalize(obj)
            if sn and on:
                properties[sn].append((f"yago:{prop}", on))
        return dict(properties)

    @property
    def stats(self) -> Dict[str, int]:
        """Summary statistics from the most recent extraction."""
        return {
            "triples_parsed": self._triples_parsed,
            "triples_skipped": self._triples_skipped,
            "subclass_pairs": len(self.subclass_pairs),
            "type_pairs": len(self.type_pairs),
            "schema_properties": len(self.schema_properties),
            "yago_properties": len(self.yago_properties),
        }


def extract_from_yago_full(
    ttl_path: Optional[Path] = None,
    max_triples: int | None = None,
) -> Theory:
    """Extract a defeasible theory from a YAGO 4.5 TTL dump.

    Args:
        ttl_path: Path to the ``.ttl`` file.  Defaults to
            ``data/yago/yago-4.5.0.2-tiny/yago-tiny.ttl``.
        max_triples: Cap on triples retained (None = all).

    Returns:
        Theory with YAGO-derived strict taxonomy and defeasible property rules.
    """
    if ttl_path is None:
        ttl_path = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "yago"
            / "yago-4.5.0.2-tiny"
            / "yago-tiny.ttl"
        )

    extractor = YagoFullExtractor(ttl_path, max_triples=max_triples)
    extractor.extract()
    return extractor.to_theory()
