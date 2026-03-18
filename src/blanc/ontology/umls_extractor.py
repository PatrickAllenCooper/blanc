"""
UMLS (Unified Medical Language System) extraction for defeasible knowledge bases.

Parses the RRF (Rich Release Format) distribution files -- MRCONSO.RRF,
MRREL.RRF, MRSTY.RRF, and MRDEF.RRF -- to produce a defeasible theory with:
  - Strict semantic-type assignments from MRSTY
  - Defeasible inter-concept relations from MRREL
  - Defeaters from inter-vocabulary contradictions across the 189+ source
    vocabularies encoded in MRCONSO

RRF files use pipe-delimited (|) columns in a fixed order per file.

Source: https://www.nlm.nih.gov/research/umls/licensedcontent/umlsknowledgesources.html

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

RELATION_MAP: Dict[str, str] = {
    "RB": "broader",
    "RN": "narrower",
    "RO": "related",
    "PAR": "parent",
    "CHD": "child",
    "SIB": "sibling",
    "AQ": "qualifier",
    "QB": "qualified_by",
}

CLINICAL_RELA: Dict[str, str] = {
    "treats": "treats",
    "causes": "causes",
    "prevents": "prevents",
    "diagnoses": "diagnoses",
    "associated_with": "associated_with",
    "manifestation_of": "manifestation_of",
    "finding_site_of": "finding_site_of",
    "has_mechanism_of_action": "mechanism_of_action",
    "induces": "induces",
    "contraindicated_with": "contraindicated_with",
    "may_treat": "may_treat",
    "may_prevent": "may_prevent",
}


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    text = _NORMALIZE_RE.sub("", text)
    if text and not text[0].isalpha():
        text = "c_" + text
    return text


def _cui_id(cui: str) -> str:
    """Normalize a CUI identifier: C0000001 -> cui_c0000001."""
    return f"cui_{cui.lower()}"


class UmlsExtractor:
    """Extract defeasible knowledge from UMLS RRF distribution files.

    The UMLS bundles concepts from 189+ biomedical vocabularies into a
    unified CUI (Concept Unique Identifier) space.  This extractor reads
    four core RRF files:

    - **MRCONSO.RRF** -- concept names and source vocabulary mappings
    - **MRREL.RRF** -- inter-concept relations
    - **MRSTY.RRF** -- semantic type assignments
    - **MRDEF.RRF** -- concept definitions (used for provenance metadata)

    Mapping to defeasible logic:
        Semantic type assignments  -> defeasible type rules
        Inter-concept relations    -> defeasible rules
        Cross-vocabulary conflicts -> defeaters

    Usage::

        ext = UmlsExtractor(Path("data/umls/2025AA/META"))
        ext.load()
        ext.extract()
        theory = ext.to_theory()
    """

    _SOURCE = "UMLS"

    def __init__(self, rrf_dir: Path) -> None:
        self.rrf_dir = rrf_dir
        self._validate_rrf_dir()

        self.concepts: Dict[str, str] = {}
        self.concept_sources: Dict[str, Dict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        self.semantic_types: List[Tuple[str, str, str]] = []
        self.relations: List[Tuple[str, str, str, str, str]] = []
        self.definitions: Dict[str, str] = {}

        self._contradictions: List[Tuple[str, str, str, str]] = []
        self._loaded = False

    def _validate_rrf_dir(self) -> None:
        if not self.rrf_dir.is_dir():
            raise FileNotFoundError(f"UMLS RRF directory not found: {self.rrf_dir}")

        required = ["MRCONSO.RRF", "MRREL.RRF", "MRSTY.RRF"]
        missing = [f for f in required if not (self.rrf_dir / f).exists()]
        if missing:
            raise FileNotFoundError(
                f"Missing required RRF files in {self.rrf_dir}: {', '.join(missing)}"
            )

    # -- Loading -----------------------------------------------------------

    def load(self) -> None:
        """Parse all RRF files in the distribution directory."""
        self._load_mrconso()
        self._load_mrsty()
        self._load_mrrel()
        self._load_mrdef()
        self._loaded = True

    def _load_mrconso(self) -> None:
        """Parse MRCONSO.RRF for concept names and source vocabulary mappings.

        Columns: CUI|LAT|TS|LUI|STT|SUI|ISPREF|AUI|SAUI|SCUI|SDUI|SAB|TTY|CODE|STR|SRL|SUPPRESS|CVF
        """
        path = self.rrf_dir / "MRCONSO.RRF"
        count = 0

        with open(path, encoding="utf-8") as fh:
            for line in fh:
                fields = line.rstrip("\n").split("|")
                if len(fields) < 17:
                    continue

                cui = fields[0]
                lat = fields[1]
                sab = fields[11]
                tty = fields[12]
                name = fields[14]
                suppress = fields[16]

                if suppress in ("O", "E", "Y"):
                    continue
                if lat != "ENG":
                    continue

                if cui not in self.concepts:
                    self.concepts[cui] = name

                self.concept_sources[cui][sab].add(name)
                count += 1

        logger.info(
            "MRCONSO: loaded %d atoms for %d concepts",
            count,
            len(self.concepts),
        )

    def _load_mrsty(self) -> None:
        """Parse MRSTY.RRF for semantic type assignments.

        Columns: CUI|TUI|STN|STY|ATUI|CVF
        """
        path = self.rrf_dir / "MRSTY.RRF"
        count = 0

        with open(path, encoding="utf-8") as fh:
            for line in fh:
                fields = line.rstrip("\n").split("|")
                if len(fields) < 4:
                    continue

                cui = fields[0]
                tui = fields[1]
                sty = fields[3]
                self.semantic_types.append((cui, tui, sty))
                count += 1

        logger.info("MRSTY: loaded %d semantic type assignments", count)

    def _load_mrrel(self) -> None:
        """Parse MRREL.RRF for inter-concept relations.

        Columns: CUI1|AUI1|STYPE1|REL|CUI2|AUI2|STYPE2|RELA|RUI|SRUI|SAB|SL|RG|DIR|SUPPRESS|CVF
        """
        path = self.rrf_dir / "MRREL.RRF"
        count = 0

        with open(path, encoding="utf-8") as fh:
            for line in fh:
                fields = line.rstrip("\n").split("|")
                if len(fields) < 11:
                    continue

                cui1 = fields[0]
                rel = fields[3]
                cui2 = fields[4]
                rela = fields[7]
                sab = fields[10]
                suppress = fields[14] if len(fields) > 14 else ""

                if suppress in ("O", "E", "Y"):
                    continue
                if cui1 == cui2:
                    continue

                self.relations.append((cui1, rel, cui2, rela, sab))
                count += 1

        logger.info("MRREL: loaded %d relations", count)

    def _load_mrdef(self) -> None:
        """Parse MRDEF.RRF for concept definitions (optional).

        Columns: CUI|AUI|ATUI|SATUI|SAB|DEF|SUPPRESS|CVF
        """
        path = self.rrf_dir / "MRDEF.RRF"
        if not path.exists():
            logger.info("MRDEF.RRF not found; skipping definitions")
            return

        count = 0
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                fields = line.rstrip("\n").split("|")
                if len(fields) < 7:
                    continue

                cui = fields[0]
                definition = fields[5]
                suppress = fields[6]

                if suppress in ("O", "E", "Y"):
                    continue

                if cui not in self.definitions:
                    self.definitions[cui] = definition
                    count += 1

        logger.info("MRDEF: loaded %d definitions", count)

    # -- Extraction --------------------------------------------------------

    def extract(self) -> None:
        """Run the full extraction pipeline.

        Identifies cross-vocabulary contradictions by scanning concepts
        that appear in multiple source vocabularies with conflicting
        relational assertions.
        """
        if not self._loaded:
            raise ValueError("Must call load() before extract()")

        self._detect_contradictions()

    def _detect_contradictions(self) -> None:
        """Find inter-vocabulary contradictions for the same CUI.

        A contradiction arises when two source vocabularies (SABs) assert
        conflicting relations for the same concept pair -- e.g. vocabulary A
        says ``cui_X treats cui_Y`` while vocabulary B says
        ``cui_X contraindicated_with cui_Y``.
        """
        self._contradictions.clear()

        pair_assertions: Dict[
            Tuple[str, str], Dict[str, Set[str]]
        ] = defaultdict(lambda: defaultdict(set))

        for cui1, rel, cui2, rela, sab in self.relations:
            effective_rel = rela if rela else rel
            if effective_rel:
                pair_assertions[(cui1, cui2)][effective_rel].add(sab)

        contradictory_pairs = {
            ("treats", "contraindicated_with"),
            ("causes", "prevents"),
            ("induces", "prevents"),
            ("treats", "causes"),
            ("may_treat", "contraindicated_with"),
        }

        for (cui1, cui2), rel_map in pair_assertions.items():
            rels_present = set(rel_map.keys())
            for rel_a, rel_b in contradictory_pairs:
                if rel_a in rels_present and rel_b in rels_present:
                    sabs_a = ", ".join(sorted(rel_map[rel_a]))
                    sabs_b = ", ".join(sorted(rel_map[rel_b]))
                    self._contradictions.append(
                        (cui1, cui2, f"{rel_a}({sabs_a})", f"{rel_b}({sabs_b})")
                    )

        logger.info(
            "Detected %d cross-vocabulary contradictions", len(self._contradictions)
        )

    # -- Conversion --------------------------------------------------------

    def to_theory(self) -> Theory:
        """Convert extracted UMLS data to a defeasible Theory.

        Produces:
            - Defeasible semantic type assignments from MRSTY
            - Defeasible inter-concept relations from MRREL
            - Defeaters from cross-vocabulary contradictions
        """
        theory = Theory()
        added: Set[tuple] = set()

        for cui, tui, sty in self.semantic_types:
            cui_norm = _cui_id(cui)
            sty_norm = _normalize(sty)
            key = ("semtype", cui_norm, sty_norm)
            if key in added:
                continue
            added.add(key)

            concept_name = self.concepts.get(cui, cui)
            theory.add_rule(Rule(
                head=f"has_semantic_type({cui_norm}, {sty_norm})",
                body=(),
                rule_type=RuleType.DEFEASIBLE,
                label=f"umls_sty_{cui_norm}_{sty_norm}",
                metadata={
                    "source": self._SOURCE,
                    "concept_name": concept_name,
                    "tui": tui,
                },
            ))

        for cui1, rel, cui2, rela, sab in self.relations:
            effective_rel = rela if rela else rel
            mapped_rel = (
                CLINICAL_RELA.get(effective_rel)
                or RELATION_MAP.get(effective_rel)
                or _normalize(effective_rel)
            )
            if not mapped_rel:
                continue

            cui1_norm = _cui_id(cui1)
            cui2_norm = _cui_id(cui2)
            key = ("rel", cui1_norm, mapped_rel, cui2_norm)
            if key in added:
                continue
            added.add(key)

            if mapped_rel in ("parent", "child", "broader", "narrower"):
                rule_type = RuleType.STRICT
            else:
                rule_type = RuleType.DEFEASIBLE

            theory.add_rule(Rule(
                head=f"{mapped_rel}({cui1_norm}, {cui2_norm})",
                body=(),
                rule_type=rule_type,
                label=f"umls_rel_{cui1_norm}_{mapped_rel}_{cui2_norm}",
                metadata={
                    "source": self._SOURCE,
                    "sab": sab,
                    "original_rel": rel,
                    "original_rela": rela,
                },
            ))

        for cui1, cui2, assertion_a, assertion_b in self._contradictions:
            cui1_norm = _cui_id(cui1)
            cui2_norm = _cui_id(cui2)

            rel_a = assertion_a.split("(")[0]
            mapped_a = (
                CLINICAL_RELA.get(rel_a)
                or RELATION_MAP.get(rel_a)
                or _normalize(rel_a)
            )
            if not mapped_a:
                continue

            key = ("contradict", cui1_norm, cui2_norm, mapped_a)
            if key in added:
                continue
            added.add(key)

            target_label = f"umls_rel_{cui1_norm}_{mapped_a}_{cui2_norm}"
            defeater_label = (
                f"umls_contradict_{cui1_norm}_{cui2_norm}_{mapped_a}"
            )

            theory.add_rule(Rule(
                head=f"~{mapped_a}({cui1_norm}, {cui2_norm})",
                body=(),
                rule_type=RuleType.DEFEATER,
                label=defeater_label,
                metadata={
                    "source": self._SOURCE,
                    "conflict": f"{assertion_a} vs {assertion_b}",
                },
            ))
            theory.add_superiority(defeater_label, target_label)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping from broader/narrower relations."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for cui1, rel, cui2, rela, _sab in self.relations:
            effective = rela if rela else rel
            if effective in ("PAR", "RB", "isa", "parent_of"):
                taxonomy[_cui_id(cui1)].add(_cui_id(cui2))
            elif effective in ("CHD", "RN", "child_of"):
                taxonomy[_cui_id(cui2)].add(_cui_id(cui1))
        return dict(taxonomy)


# -- Convenience function -------------------------------------------------

def extract_from_umls(rrf_dir: Path) -> Theory:
    """Extract a defeasible Theory from a UMLS RRF distribution.

    Args:
        rrf_dir: Path to the META directory containing MRCONSO.RRF,
                 MRREL.RRF, MRSTY.RRF, and optionally MRDEF.RRF.

    Returns:
        Theory with semantic type assignments, inter-concept relations,
        and cross-vocabulary contradiction defeaters.
    """
    extractor = UmlsExtractor(rrf_dir)
    extractor.load()
    extractor.extract()
    return extractor.to_theory()
