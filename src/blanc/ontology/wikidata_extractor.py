"""
Wikidata SPARQL-based extractor for defeasible knowledge bases.

Queries the Wikidata SPARQL endpoint (https://query.wikidata.org/sparql) for
property-constraint exceptions (P2302/P2303) and domain-specific instanceof
assertions, converting them into defeasible rules and defeaters.

Author: Patrick Cooper
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")

DOMAIN_CLASSES: Dict[str, Dict[str, str]] = {
    "biology": {
        "Q16521": "taxon",
        "Q7239": "organism",
    },
    "legal": {
        "Q7748": "law",
        "Q4932206": "legal_concept",
    },
    "materials": {
        "Q214609": "material",
        "Q11173": "chemical_compound",
    },
}


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    return _NORMALIZE_RE.sub("", text)


def _qid(uri: str) -> str:
    """Extract Q-ID or P-ID from a full Wikidata URI."""
    return uri.rsplit("/", 1)[-1] if "/" in uri else uri


class WikidataExtractor:
    """Extract defeasible knowledge from Wikidata via SPARQL.

    Queries the public Wikidata SPARQL endpoint for property constraint
    exceptions (P2302 / P2303) and domain-specific instanceof + property
    assertions.  Rate-limits all requests and applies exponential backoff
    on HTTP errors.

    Mapping:
        P2302 property constraints      -> defeasible rules
        P2303 constraint exceptions      -> defeaters
        Domain instanceof assertions     -> defeasible property rules
    """

    _ENDPOINT = "https://query.wikidata.org/sparql"
    _SOURCE = "Wikidata"
    _SPARQL_TIMEOUT = 60

    def __init__(
        self,
        user_agent: str = "DeFAb/1.0 (patrick.cooper@colorado.edu)",
        delay: float = 2.0,
    ):
        self.user_agent = user_agent
        self.delay = delay
        self._last_query_time: float = 0.0

        self.constraint_exceptions: List[Tuple[str, str, str, str, str, str]] = []
        self.domain_assertions: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    def _query(self, sparql_str: str) -> Optional[Dict[str, Any]]:
        """Execute a SPARQL query against the Wikidata endpoint.

        Enforces rate limiting (minimum ``self.delay`` seconds between
        requests) and retries with exponential backoff on HTTP errors
        (up to 3 attempts).

        Returns parsed JSON results or None on failure.
        """
        try:
            from SPARQLWrapper import SPARQLWrapper, JSON
        except ImportError as exc:
            raise ImportError(
                "The 'sparqlwrapper' package is required for Wikidata extraction. "
                "Install it with: pip install sparqlwrapper"
            ) from exc

        elapsed = time.monotonic() - self._last_query_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        wrapper = SPARQLWrapper(self._ENDPOINT)
        wrapper.setQuery(sparql_str)
        wrapper.setReturnFormat(JSON)
        wrapper.setTimeout(self._SPARQL_TIMEOUT)
        wrapper.addCustomHttpHeader("User-Agent", self.user_agent)

        max_retries = 3
        backoff = self.delay

        for attempt in range(max_retries):
            try:
                self._last_query_time = time.monotonic()
                results = wrapper.query().convert()
                return results
            except Exception as exc:
                msg = str(exc)
                logger.warning(
                    "SPARQL query failed (attempt %d/%d): %s",
                    attempt + 1, max_retries, msg,
                )
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error("SPARQL query abandoned after %d attempts.", max_retries)
                    return None

    def extract_constraint_exceptions(self) -> List[Tuple[str, str, str]]:
        """Extract property-constraint exception triples (P2302/P2303).

        Returns list of (property_label, constraint_type_label, exception_label)
        tuples.
        """
        sparql = """\
SELECT ?property ?propertyLabel ?constraintType ?constraintTypeLabel ?exception ?exceptionLabel
WHERE {
  ?property p:P2302 ?stmt .
  ?stmt ps:P2302 ?constraintType .
  ?stmt pq:P2303 ?exception .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""
        logger.info("Querying Wikidata for P2302/P2303 constraint exceptions...")
        results = self._query(sparql)
        if results is None:
            logger.error("Failed to retrieve constraint exceptions.")
            return []

        triples: List[Tuple[str, str, str]] = []
        for binding in results.get("results", {}).get("bindings", []):
            prop_label = binding.get("propertyLabel", {}).get("value", "")
            ct_label = binding.get("constraintTypeLabel", {}).get("value", "")
            ex_label = binding.get("exceptionLabel", {}).get("value", "")
            prop_uri = binding.get("property", {}).get("value", "")
            ct_uri = binding.get("constraintType", {}).get("value", "")
            ex_uri = binding.get("exception", {}).get("value", "")

            self.constraint_exceptions.append(
                (prop_uri, prop_label, ct_uri, ct_label, ex_uri, ex_label)
            )
            triples.append((
                prop_label or _qid(prop_uri),
                ct_label or _qid(ct_uri),
                ex_label or _qid(ex_uri),
            ))

        logger.info("Retrieved %d constraint-exception triples.", len(triples))
        return triples

    def extract_domain_rules(
        self,
        domain_classes: List[str],
        limit: int = 50000,
    ) -> None:
        """Extract instanceof + property assertions for domain classes.

        For each Q-ID in *domain_classes*, queries Wikidata for items
        that are instanceof that class and collects their property
        assertions (limited to direct claims for performance).

        Args:
            domain_classes: Wikidata Q-IDs (e.g. ``["Q16521", "Q7239"]``).
            limit: Maximum results per class query (Wikidata caps at ~60s).
        """
        for qid in domain_classes:
            sparql = f"""\
SELECT ?item ?itemLabel ?prop ?propLabel ?val ?valLabel
WHERE {{
  ?item wdt:P31 wd:{qid} .
  ?item ?prop ?val .
  FILTER(STRSTARTS(STR(?prop), "http://www.wikidata.org/prop/direct/"))
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
LIMIT {limit}
"""
            logger.info("Querying domain class %s (limit=%d)...", qid, limit)
            results = self._query(sparql)
            if results is None:
                logger.warning("No results for domain class %s.", qid)
                continue

            bindings = results.get("results", {}).get("bindings", [])
            for binding in bindings:
                self.domain_assertions[qid].append({
                    "item": binding.get("item", {}).get("value", ""),
                    "itemLabel": binding.get("itemLabel", {}).get("value", ""),
                    "prop": binding.get("prop", {}).get("value", ""),
                    "propLabel": binding.get("propLabel", {}).get("value", ""),
                    "val": binding.get("val", {}).get("value", ""),
                    "valLabel": binding.get("valLabel", {}).get("value", ""),
                })

            logger.info(
                "Retrieved %d assertions for class %s.", len(bindings), qid,
            )

    def to_theory(self) -> Theory:
        """Build a ``Theory`` from the extracted Wikidata data.

        Conversion strategy:
            - P2302 constraints become defeasible rules asserting the
              constraint holds for the property.
            - P2303 exceptions become defeaters overriding the constraint
              for the excepted item.
            - Domain property assertions become defeasible rules.
        """
        theory = Theory()
        added: Set[tuple] = set()

        for prop_uri, prop_label, ct_uri, ct_label, ex_uri, ex_label in self.constraint_exceptions:
            prop_norm = _normalize(prop_label or _qid(prop_uri))
            ct_norm = _normalize(ct_label or _qid(ct_uri))
            ex_norm = _normalize(ex_label or _qid(ex_uri))

            if not prop_norm or not ct_norm:
                continue

            constraint_key = ("constraint", prop_norm, ct_norm)
            if constraint_key not in added:
                constraint_label = f"wd_constraint_{prop_norm}_{ct_norm}"
                theory.add_rule(Rule(
                    head=f"constraint({prop_norm}, {ct_norm})",
                    body=(f"has_property(X, {prop_norm})",),
                    rule_type=RuleType.DEFEASIBLE,
                    label=constraint_label,
                    metadata={"source": self._SOURCE, "relation": "P2302"},
                ))
                added.add(constraint_key)

            if not ex_norm:
                continue

            defeater_key = ("exception", prop_norm, ct_norm, ex_norm)
            if defeater_key not in added:
                constraint_label = f"wd_constraint_{prop_norm}_{ct_norm}"
                defeater_label = f"wd_except_{prop_norm}_{ct_norm}_{ex_norm}"
                theory.add_rule(Rule(
                    head=f"~constraint({prop_norm}, {ct_norm})",
                    body=(f"isa(X, {ex_norm})",),
                    rule_type=RuleType.DEFEATER,
                    label=defeater_label,
                    metadata={
                        "source": self._SOURCE,
                        "relation": "P2303",
                        "exception_for": prop_norm,
                    },
                ))
                theory.add_superiority(defeater_label, constraint_label)
                added.add(defeater_key)

        for qid, assertions in self.domain_assertions.items():
            class_name = self._resolve_class_name(qid)
            for assertion in assertions:
                item_label = assertion["itemLabel"]
                prop_label = assertion["propLabel"]
                val_label = assertion["valLabel"]

                item_norm = _normalize(item_label or _qid(assertion["item"]))
                prop_norm = _normalize(prop_label or _qid(assertion["prop"]))
                val_norm = _normalize(val_label or _qid(assertion["val"]))

                if not item_norm or not prop_norm or not val_norm:
                    continue

                key = ("domain", item_norm, prop_norm, val_norm)
                if key not in added:
                    theory.add_rule(Rule(
                        head=f"{prop_norm}({item_norm}, {val_norm})",
                        body=(f"isa({item_norm}, {class_name})",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"wd_{class_name}_{item_norm}_{prop_norm}",
                        metadata={
                            "source": self._SOURCE,
                            "domain_class": qid,
                        },
                    ))
                    added.add(key)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner.

        Builds the taxonomy from domain assertions that use the
        ``instance_of`` (P31) or ``subclass_of`` (P279) properties.
        """
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for qid, assertions in self.domain_assertions.items():
            class_name = self._resolve_class_name(qid)
            for assertion in assertions:
                item_norm = _normalize(
                    assertion["itemLabel"] or _qid(assertion["item"])
                )
                prop_uri = assertion["prop"]
                if prop_uri.endswith("/P31") or prop_uri.endswith("/P279"):
                    val_norm = _normalize(
                        assertion["valLabel"] or _qid(assertion["val"])
                    )
                    if item_norm and val_norm:
                        taxonomy[item_norm].add(val_norm)
                elif item_norm and class_name:
                    taxonomy[item_norm].add(class_name)
        return dict(taxonomy)

    @staticmethod
    def _resolve_class_name(qid: str) -> str:
        """Map a Q-ID to a human-readable class name if known."""
        for domain_classes in DOMAIN_CLASSES.values():
            if qid in domain_classes:
                return domain_classes[qid]
        return _normalize(qid)


def extract_from_wikidata(
    domains: Optional[List[str]] = None,
    limit: int = 50000,
    user_agent: str = "DeFAb/1.0 (patrick.cooper@colorado.edu)",
    delay: float = 2.0,
) -> Theory:
    """Extract a defeasible theory from Wikidata.

    Args:
        domains: List of domain names to extract (keys of ``DOMAIN_CLASSES``).
                 Defaults to all available domains.
        limit: Maximum results per domain-class query.
        user_agent: User-Agent header for Wikidata requests.
        delay: Minimum seconds between SPARQL queries.

    Returns:
        Theory with constraint, exception, and domain-property rules.
    """
    if domains is None:
        domains = list(DOMAIN_CLASSES.keys())

    extractor = WikidataExtractor(user_agent=user_agent, delay=delay)
    extractor.extract_constraint_exceptions()

    all_qids: List[str] = []
    for domain in domains:
        if domain in DOMAIN_CLASSES:
            all_qids.extend(DOMAIN_CLASSES[domain].keys())
        else:
            logger.warning("Unknown domain '%s'; skipping.", domain)

    if all_qids:
        extractor.extract_domain_rules(all_qids, limit=limit)

    return extractor.to_theory()
