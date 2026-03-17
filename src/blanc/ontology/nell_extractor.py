"""
NELL (Never-Ending Language Learner) knowledge base extractor.

Extracts beliefs from the NELL knowledge base (rtw-cmu/nell on HuggingFace)
and converts them into defeasible theories. NELL contains millions of beliefs
learned continuously from the web, each with a confidence score.

Conversion rules:
    - ``generalizations`` relation -> strict IsA taxonomic rules
    - Other relations              -> defeasible property/behavioral rules
    - Conflicting beliefs           -> defeaters with superiority ordering

Author: Patrick Cooper
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    return _NORMALIZE_RE.sub("", text)


class NellExtractor:
    """Extract defeasible knowledge from the NELL belief dataset.

    NELL data is loaded from HuggingFace (``rtw-cmu/nell``, subset
    ``nell_belief``).  Each row contains ``entity``, ``relation``,
    ``value``, and ``score`` (confidence as a string float).

    The extractor filters beliefs by confidence, converts them to
    defeasible rules, and detects conflicting beliefs to generate
    defeaters with superiority relations.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.95,
        max_beliefs: int | None = None,
    ):
        self.confidence_threshold = confidence_threshold
        self.max_beliefs = max_beliefs
        self.beliefs: list[dict] = []

    def extract(self, csv_path: str | None = None) -> None:
        """Load NELL beliefs from CSV and filter by confidence.

        Args:
            csv_path: Path to NELL beliefs CSV/TSV file. If None, attempts
                      to download from the CMU RTW server.
        """
        import csv
        import gzip
        import urllib.request
        from pathlib import Path

        if csv_path is None:
            data_dir = Path(__file__).parent.parent.parent.parent / "data" / "nell"
            data_dir.mkdir(parents=True, exist_ok=True)
            csv_path = data_dir / "NELL.08m.1115.esv.csv.gz"
            if not csv_path.exists():
                url = "http://rtw.ml.cmu.edu/rtw/resources/NELL.08m.1115.esv.csv.gz"
                logger.info("Downloading NELL beliefs from %s ...", url)
                print(f"    Downloading NELL beliefs (~500 MB)...", flush=True)
                urllib.request.urlretrieve(url, csv_path)
        else:
            csv_path = Path(csv_path)

        logger.info(
            "Loading NELL beliefs from %s (threshold=%.3f)...",
            csv_path, self.confidence_threshold,
        )

        opener = (
            lambda p: gzip.open(p, "rt", encoding="utf-8", errors="replace")
            if str(p).endswith(".gz")
            else open(p, encoding="utf-8", errors="replace")
        )

        count = 0
        with opener(csv_path) as fh:
            reader = csv.reader(fh, delimiter="\t")
            header = None
            for row_list in reader:
                if self.max_beliefs is not None and count >= self.max_beliefs:
                    break
                if not row_list or row_list[0].startswith("#"):
                    continue
                if header is None:
                    header = row_list
                    continue
                if len(row_list) < 4:
                    continue
                row = {
                    "entity": row_list[0] if len(row_list) > 0 else "",
                    "relation": row_list[1] if len(row_list) > 1 else "",
                    "value": row_list[2] if len(row_list) > 2 else "",
                    "score": row_list[3] if len(row_list) > 3 else "0",
                }

                try:
                    score = float(row["score"])
                except (ValueError, TypeError):
                    continue

                if score < self.confidence_threshold:
                    continue

                self.beliefs.append({
                    "entity": str(row["entity"]),
                    "relation": str(row["relation"]),
                    "value": str(row["value"]),
                    "score": score,
                })
                count += 1

        logger.info("Extracted %d beliefs above threshold.", len(self.beliefs))

    def to_theory(self) -> Theory:
        """Convert extracted beliefs to a defeasible Theory.

        Conversion strategy:
            - ``generalizations`` relation produces strict IsA rules:
              ``parent(X) :- child(X)``
            - All other relations produce defeasible rules:
              ``relation(entity, value)``
            - When the same (entity, relation) pair maps to multiple
              distinct values with high confidence, conflicting beliefs
              are emitted as defeaters with superiority ordering favoring
              the higher-confidence belief.
        """
        theory = Theory()
        rules_added: set[tuple] = set()
        source = "NELL"

        belief_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for belief in self.beliefs:
            key = (belief["entity"], belief["relation"])
            belief_groups[key].append(belief)

        for belief in self.beliefs:
            entity = _normalize(belief["entity"])
            relation = belief["relation"]
            value = _normalize(belief["value"])
            score = belief["score"]

            if not entity or not value:
                continue

            if relation == "generalizations":
                key = ("isa", entity, value)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"{value}(X)",
                        body=(f"{entity}(X)",),
                        rule_type=RuleType.STRICT,
                        label=f"nell_isa_{entity}_{value}",
                        metadata={"score": score, "source": source},
                    ))
                    rules_added.add(key)
            else:
                rel_norm = _normalize(relation)
                key = ("rel", rel_norm, entity, value)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"{rel_norm}({entity}, {value})",
                        body=(),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"nell_{rel_norm}_{entity}_{value}",
                        metadata={"score": score, "source": source},
                    ))
                    rules_added.add(key)

        self._add_defeaters(theory, belief_groups, rules_added)
        return theory

    def _add_defeaters(
        self,
        theory: Theory,
        belief_groups: dict[tuple[str, str], list[dict]],
        rules_added: set[tuple],
    ) -> None:
        """Detect conflicting beliefs and emit defeaters.

        Two beliefs conflict when they share the same (entity, relation)
        but assert different values, both above the confidence threshold.
        The higher-confidence belief gets a superiority relation over
        the lower-confidence defeater.
        """
        for (raw_entity, raw_relation), group in belief_groups.items():
            if len(group) < 2:
                continue

            entity = _normalize(raw_entity)
            rel_norm = _normalize(raw_relation)

            if raw_relation == "generalizations" or not entity:
                continue

            values = {_normalize(b["value"]) for b in group}
            if len(values) < 2:
                continue

            ranked = sorted(group, key=lambda b: b["score"], reverse=True)
            winner = ranked[0]
            winner_value = _normalize(winner["value"])
            winner_label = f"nell_{rel_norm}_{entity}_{winner_value}"

            for loser in ranked[1:]:
                loser_value = _normalize(loser["value"])
                if loser_value == winner_value:
                    continue

                defeater_label = f"nell_defeat_{rel_norm}_{entity}_{loser_value}"
                key = ("defeat", rel_norm, entity, loser_value)
                if key not in rules_added:
                    theory.add_rule(Rule(
                        head=f"~{rel_norm}({entity}, {loser_value})",
                        body=(),
                        rule_type=RuleType.DEFEATER,
                        label=defeater_label,
                        metadata={
                            "score": loser["score"],
                            "source": "NELL",
                            "conflict_with": winner_value,
                        },
                    ))
                    rules_added.add(key)
                    theory.add_superiority(winner_label, defeater_label)

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for belief in self.beliefs:
            if belief["relation"] == "generalizations":
                child = _normalize(belief["entity"])
                parent = _normalize(belief["value"])
                if child and parent:
                    taxonomy[child].add(parent)
        return dict(taxonomy)

    def get_properties(self) -> Dict[str, List[Tuple[str, str]]]:
        """Return concept -> [(relation, value), ...] for the cross-ontology combiner."""
        properties: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        for belief in self.beliefs:
            if belief["relation"] == "generalizations":
                continue
            entity = _normalize(belief["entity"])
            relation = belief["relation"]
            value = _normalize(belief["value"])
            if entity and value:
                properties[entity].append((relation, value))
        return dict(properties)


def extract_from_nell(
    confidence_threshold: float = 0.95,
    max_beliefs: int | None = None,
) -> Theory:
    """Extract a defeasible theory from the NELL knowledge base.

    Args:
        confidence_threshold: Minimum belief confidence (0.0--1.0).
        max_beliefs: Cap on beliefs retained after filtering (None = all).

    Returns:
        Theory with NELL-derived defeasible rules.
    """
    extractor = NellExtractor(confidence_threshold, max_beliefs)
    extractor.extract()
    return extractor.to_theory()
