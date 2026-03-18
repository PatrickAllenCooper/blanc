"""
BabelNet extraction for defeasible knowledge bases.

Queries the BabelNet REST API (v9) for synset relations and converts them
to a defeasible theory with:
  - Strict rules from hypernymy/hyponymy edges
  - Defeasible rules from other semantic relations
  - Defeaters from cross-language inconsistencies (same synset with
    conflicting relations in different languages)

API docs: https://babelnet.org/guide
Endpoint: https://babelnet.io/v9/

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

BABELNET_API_BASE = "https://babelnet.io/v9"

STRICT_RELATION_GROUPS: frozenset[str] = frozenset({
    "HYPERNYM",
    "HYPONYM",
    "ANY_HYPERNYM",
    "ANY_HYPONYM",
})

DEFEASIBLE_RELATION_GROUPS: frozenset[str] = frozenset({
    "MERONYM",
    "HOLONYM",
    "OTHER",
    "GLOSS_RELATED",
    "SEMANTICALLY_RELATED",
    "ALSO_SEE",
    "PERTAINYM",
    "DERIVATIONALLY_RELATED",
})


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    text = _NORMALIZE_RE.sub("", text)
    if text and not text[0].isalpha():
        text = "c_" + text
    return text


def _bn_id(synset_id: str) -> str:
    """Normalize a BabelNet synset ID: bn:00000001n -> bn_00000001n."""
    return synset_id.replace(":", "_")


class BabelNetExtractor:
    """Extract defeasible knowledge from the BabelNet REST API.

    BabelNet unifies WordNet, Wikipedia, Wiktionary, and other resources
    into a multilingual semantic network of synsets.  Each synset is
    identified by a BabelNet ID (e.g. ``bn:00000001n``).

    Mapping to defeasible logic:
        Hypernymy / hyponymy  -> strict taxonomic rules
        Other relations       -> defeasible rules
        Cross-language conflicts -> defeaters

    Usage::

        ext = BabelNetExtractor(api_key="your-key")
        ext.extract_domain("biology", limit=5000)
        theory = ext.to_theory()
    """

    _SOURCE = "BabelNet"

    def __init__(self, api_key: str, delay: float = 1.0) -> None:
        self.api_key = api_key
        self.delay = delay
        self._last_request_time: float = 0.0

        self.synsets: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Tuple[str, str, str, str, str]] = []
        self._contradictions: List[Tuple[str, str, str, str]] = []

    # -- API access --------------------------------------------------------

    def _request(self, endpoint: str, params: Dict[str, str]) -> Optional[Any]:
        """Make a rate-limited GET request to the BabelNet API."""
        try:
            import urllib.request
            import urllib.parse
            import json as _json
        except ImportError as exc:
            raise ImportError(
                "Standard library modules required for HTTP requests"
            ) from exc

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        params["key"] = self.api_key
        query_string = urllib.parse.urlencode(params)
        url = f"{BABELNET_API_BASE}/{endpoint}?{query_string}"

        max_retries = 3
        backoff = self.delay

        for attempt in range(max_retries):
            try:
                self._last_request_time = time.monotonic()
                req = urllib.request.Request(
                    url,
                    headers={"Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    return _json.loads(resp.read().decode("utf-8"))
            except Exception as exc:
                logger.warning(
                    "BabelNet API request failed (attempt %d/%d): %s",
                    attempt + 1, max_retries, exc,
                )
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    logger.error(
                        "BabelNet request abandoned after %d attempts: %s",
                        max_retries, endpoint,
                    )
                    return None

    # -- Synset retrieval --------------------------------------------------

    def _fetch_synset(self, synset_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a single synset's metadata."""
        data = self._request("getSynset", {"id": synset_id})
        if data is None:
            return None

        main_sense = ""
        senses = data.get("senses", [])
        if senses:
            props = senses[0].get("properties", {})
            main_sense = props.get("simpleLemma", "") or props.get("lemma", "")

        self.synsets[synset_id] = {
            "main_sense": main_sense,
            "senses": senses,
            "raw": data,
        }
        return data

    def _fetch_edges(self, synset_id: str) -> List[Dict[str, Any]]:
        """Fetch outgoing edges (relations) for a synset."""
        data = self._request("getOutgoingEdges", {"id": synset_id})
        if data is None:
            return []
        return data if isinstance(data, list) else []

    # -- Extraction --------------------------------------------------------

    def extract_synset_relations(self, synset_ids: list[str]) -> None:
        """Query BabelNet for relations of a list of synset IDs.

        Each edge is stored as (source_id, target_id, relation_group,
        relation_name, language).  Synset metadata is cached for later
        normalization.
        """
        for sid in synset_ids:
            if sid not in self.synsets:
                self._fetch_synset(sid)

            raw_edges = self._fetch_edges(sid)
            for edge in raw_edges:
                target = edge.get("target", "")
                rel_group = edge.get("pointer", {}).get("relationGroup", "OTHER")
                rel_name = edge.get("pointer", {}).get("shortName", rel_group)
                language = edge.get("language", "EN")

                self.edges.append((sid, target, rel_group, rel_name, language))

                if target not in self.synsets:
                    self._fetch_synset(target)

        logger.info(
            "Extracted %d edges for %d synsets",
            len(self.edges), len(synset_ids),
        )

    def extract_domain(self, domain: str, limit: int = 10000) -> None:
        """Extract synsets and relations for a named domain.

        Uses the BabelNet ``getSynsetIds`` endpoint to find synsets
        matching the domain keyword, then fetches their relations.

        Args:
            domain: A domain keyword (e.g. ``"biology"``, ``"law"``).
            limit: Maximum number of synsets to retrieve.
        """
        data = self._request("getSynsetIds", {
            "lemma": domain,
            "searchLang": "EN",
        })

        if data is None:
            logger.warning("No synset IDs returned for domain '%s'", domain)
            return

        synset_ids: list[str] = []
        for entry in data:
            sid = entry.get("id", "")
            if sid:
                synset_ids.append(sid)
            if len(synset_ids) >= limit:
                break

        if not synset_ids:
            logger.warning("No synsets found for domain '%s'", domain)
            return

        logger.info(
            "Domain '%s': found %d seed synsets, extracting relations...",
            domain, len(synset_ids),
        )

        discovered: set[str] = set(synset_ids)
        queue = list(synset_ids)
        processed = 0

        while queue and processed < limit:
            sid = queue.pop(0)
            processed += 1

            if sid not in self.synsets:
                self._fetch_synset(sid)

            raw_edges = self._fetch_edges(sid)
            for edge in raw_edges:
                target = edge.get("target", "")
                rel_group = edge.get("pointer", {}).get("relationGroup", "OTHER")
                rel_name = edge.get("pointer", {}).get("shortName", rel_group)
                language = edge.get("language", "EN")

                self.edges.append((sid, target, rel_group, rel_name, language))

                if target not in discovered and len(discovered) < limit:
                    discovered.add(target)
                    queue.append(target)
                    if target not in self.synsets:
                        self._fetch_synset(target)

        self._detect_cross_language_conflicts()
        logger.info(
            "Domain '%s': %d synsets, %d edges total",
            domain, len(self.synsets), len(self.edges),
        )

    def _detect_cross_language_conflicts(self) -> None:
        """Find synsets with conflicting relations across languages.

        A conflict arises when the same source-target pair has a hypernym
        edge in one language but a different semantic relation (e.g.
        meronym, holonym) in another language.
        """
        self._contradictions.clear()

        pair_lang_rels: Dict[
            Tuple[str, str], Dict[str, Set[str]]
        ] = defaultdict(lambda: defaultdict(set))

        for source, target, rel_group, _rel_name, language in self.edges:
            pair_lang_rels[(source, target)][language].add(rel_group)

        for (source, target), lang_map in pair_lang_rels.items():
            if len(lang_map) < 2:
                continue

            all_groups: Set[str] = set()
            for groups in lang_map.values():
                all_groups.update(groups)

            has_strict = bool(all_groups & STRICT_RELATION_GROUPS)
            has_other = bool(all_groups - STRICT_RELATION_GROUPS)

            if has_strict and has_other:
                strict_langs = [
                    lang for lang, gs in lang_map.items()
                    if gs & STRICT_RELATION_GROUPS
                ]
                other_langs = [
                    lang for lang, gs in lang_map.items()
                    if gs - STRICT_RELATION_GROUPS
                ]
                self._contradictions.append((
                    source,
                    target,
                    f"strict({','.join(sorted(strict_langs))})",
                    f"other({','.join(sorted(other_langs))})",
                ))

        logger.info(
            "Detected %d cross-language conflicts", len(self._contradictions)
        )

    # -- Conversion --------------------------------------------------------

    def to_theory(self) -> Theory:
        """Convert extracted BabelNet data to a defeasible Theory.

        Produces:
            - Strict ``isa(child, parent)`` from hypernymy/hyponymy
            - Defeasible relation rules from other semantic edges
            - Defeaters from cross-language inconsistencies
        """
        theory = Theory()
        added: Set[tuple] = set()

        for source, target, rel_group, rel_name, language in self.edges:
            s_norm = _bn_id(source)
            t_norm = _bn_id(target)
            rel_norm = _normalize(rel_name)
            if not rel_norm:
                rel_norm = _normalize(rel_group)

            key = ("edge", s_norm, rel_norm, t_norm)
            if key in added:
                continue
            added.add(key)

            if rel_group in STRICT_RELATION_GROUPS:
                if rel_group in ("HYPERNYM", "ANY_HYPERNYM"):
                    head = f"isa({s_norm}, {t_norm})"
                else:
                    head = f"isa({t_norm}, {s_norm})"

                theory.add_rule(Rule(
                    head=head,
                    body=(),
                    rule_type=RuleType.STRICT,
                    label=f"bn_tax_{s_norm}_{rel_norm}_{t_norm}",
                    metadata={
                        "source": self._SOURCE,
                        "relation_group": rel_group,
                        "source_lemma": self._synset_label(source),
                        "target_lemma": self._synset_label(target),
                    },
                ))
            elif rel_group in DEFEASIBLE_RELATION_GROUPS:
                theory.add_rule(Rule(
                    head=f"{rel_norm}({s_norm}, {t_norm})",
                    body=(),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"bn_rel_{s_norm}_{rel_norm}_{t_norm}",
                    metadata={
                        "source": self._SOURCE,
                        "relation_group": rel_group,
                        "source_lemma": self._synset_label(source),
                        "target_lemma": self._synset_label(target),
                    },
                ))

        for source, target, assertion_a, assertion_b in self._contradictions:
            s_norm = _bn_id(source)
            t_norm = _bn_id(target)

            key = ("conflict", s_norm, t_norm)
            if key in added:
                continue
            added.add(key)

            target_label = f"bn_tax_{s_norm}_hypernym_{t_norm}"
            defeater_label = f"bn_conflict_{s_norm}_{t_norm}"

            theory.add_rule(Rule(
                head=f"~isa({s_norm}, {t_norm})",
                body=(),
                rule_type=RuleType.DEFEATER,
                label=defeater_label,
                metadata={
                    "source": self._SOURCE,
                    "conflict": f"{assertion_a} vs {assertion_b}",
                    "source_lemma": self._synset_label(source),
                    "target_lemma": self._synset_label(target),
                },
            ))
            theory.add_superiority(defeater_label, target_label)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return synset -> {parent synsets} mapping from hypernymy edges."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for source, target, rel_group, _rel_name, _language in self.edges:
            if rel_group in ("HYPERNYM", "ANY_HYPERNYM"):
                taxonomy[_bn_id(source)].add(_bn_id(target))
            elif rel_group in ("HYPONYM", "ANY_HYPONYM"):
                taxonomy[_bn_id(target)].add(_bn_id(source))
        return dict(taxonomy)

    # -- Helpers -----------------------------------------------------------

    def _synset_label(self, synset_id: str) -> str:
        """Return the main lemma for a synset, or the raw ID."""
        info = self.synsets.get(synset_id)
        if info and info.get("main_sense"):
            return info["main_sense"]
        return synset_id


# -- Convenience function -------------------------------------------------

def extract_from_babelnet(
    api_key: str,
    domain: str,
    limit: int = 10000,
    delay: float = 1.0,
) -> Theory:
    """Extract a defeasible Theory from BabelNet for a given domain.

    Args:
        api_key: BabelNet REST API key (from https://babelnet.org/register).
        domain: Domain keyword to seed extraction (e.g. ``"biology"``).
        limit: Maximum number of synsets to retrieve.
        delay: Minimum seconds between API requests.

    Returns:
        Theory with strict hypernymy rules, defeasible semantic relations,
        and cross-language conflict defeaters.
    """
    extractor = BabelNetExtractor(api_key=api_key, delay=delay)
    extractor.extract_domain(domain, limit=limit)
    return extractor.to_theory()
