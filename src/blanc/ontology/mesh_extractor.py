"""
MeSH (Medical Subject Headings) extraction for taxonomic knowledge bases.

Extracts descriptor hierarchy, tree-number parent-child relations, and
category labels from the NLM MeSH XML distribution and converts them to
strict taxonomic rules in a defeasible Theory.

XML source: https://nlmpubs.nlm.nih.gov/projects/mesh/MESH_FILES/xmlmesh/

Author: Patrick Cooper
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterator, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType


MESH_CATEGORIES: Dict[str, str] = {
    "A": "anatomy",
    "B": "organisms",
    "C": "diseases",
    "D": "chemicals",
    "E": "analytical",
    "F": "psychiatry",
    "G": "phenomena",
    "H": "disciplines",
    "I": "anthropology",
    "J": "technology",
    "K": "humanities",
    "L": "information",
    "M": "named_groups",
    "N": "health_care",
    "V": "publication",
    "Z": "geographicals",
}


class MeshExtractor:
    """Extract taxonomic knowledge from NLM MeSH XML descriptors.

    MeSH organises biomedical terms into a polyhierarchical tree.  Each
    DescriptorRecord carries one or more TreeNumbers (e.g. ``A01.456.505``)
    that encode its position in the hierarchy.  A parent is derived by
    trimming the last ``.NNN`` segment, giving strict ``isa`` relations
    suitable for defeasible reasoning.

    Typical usage::

        ext = MeshExtractor(Path("desc2025.xml"))
        ext.load()
        ext.extract()
        theory = ext.to_theory()
    """

    def __init__(self, xml_path: Path) -> None:
        if not xml_path.exists():
            raise FileNotFoundError(f"MeSH XML file not found: {xml_path}")

        self.xml_path = xml_path
        self.descriptors: Dict[str, str] = {}
        self.tree_to_descriptor: Dict[str, str] = {}
        self.parent_child: list[Tuple[str, str]] = []
        self._loaded = False

    # ── Loading ───────────────────────────────────────────────────

    def load(self) -> None:
        """Parse MeSH XML using iterparse for memory-efficient streaming."""
        self.descriptors.clear()
        self.tree_to_descriptor.clear()

        for desc_ui, desc_name, tree_numbers in self._iter_descriptors():
            self.descriptors[desc_ui] = desc_name
            for tn in tree_numbers:
                self.tree_to_descriptor[tn] = desc_ui

        self._loaded = True

    def _iter_descriptors(
        self,
    ) -> Iterator[Tuple[str, str, list[str]]]:
        """Yield (DescriptorUI, DescriptorName, [TreeNumber, ...]) tuples."""
        context = ET.iterparse(self.xml_path, events=("end",))
        for _event, elem in context:
            if elem.tag != "DescriptorRecord":
                continue

            ui_el = elem.find("DescriptorUI")
            name_el = elem.find("DescriptorName/String")
            if ui_el is None or name_el is None:
                elem.clear()
                continue

            desc_ui = (ui_el.text or "").strip()
            desc_name = (name_el.text or "").strip()

            tree_numbers: list[str] = []
            tn_list = elem.find("TreeNumberList")
            if tn_list is not None:
                for tn_el in tn_list.findall("TreeNumber"):
                    if tn_el.text:
                        tree_numbers.append(tn_el.text.strip())

            if desc_ui and desc_name:
                yield desc_ui, desc_name, tree_numbers

            elem.clear()

    # ── Extraction ────────────────────────────────────────────────

    def extract(self) -> None:
        """Derive parent-child relations from tree numbers.

        For every tree number with at least one ``.`` separator the parent is
        the prefix obtained by dropping the last segment.  Single-segment
        tree numbers (e.g. ``A01``) are children of their top-level category
        letter (``A``).
        """
        if not self._loaded:
            raise ValueError("Must call load() before extract()")

        self.parent_child.clear()
        seen: Set[Tuple[str, str]] = set()

        for tree_number in sorted(self.tree_to_descriptor):
            child_ui = self.tree_to_descriptor[tree_number]

            if "." in tree_number:
                parent_tn = tree_number.rsplit(".", 1)[0]
                parent_ui = self.tree_to_descriptor.get(parent_tn)
                if parent_ui and (child_ui, parent_ui) not in seen:
                    self.parent_child.append((child_ui, parent_ui))
                    seen.add((child_ui, parent_ui))

            category_letter = tree_number[0] if tree_number else None
            if category_letter and category_letter in MESH_CATEGORIES:
                cat_name = MESH_CATEGORIES[category_letter]
                pair = (child_ui, f"category_{cat_name}")
                if pair not in seen:
                    self.parent_child.append(pair)
                    seen.add(pair)

    # ── Conversion ────────────────────────────────────────────────

    def to_theory(self) -> Theory:
        """Convert extracted MeSH hierarchy to a defeasible Theory.

        Produces:
            - ``mesh_descriptor(norm_name)`` facts for every descriptor
            - ``mesh_category(cat)`` facts for the 16 top-level categories
            - Strict ``isa(child, parent)`` rules from the tree hierarchy
            - Strict ``isa(descriptor, category_X)`` for category membership
        """
        theory = Theory()
        facts_added: Set[str] = set()
        rules_added: Set[Tuple[str, str]] = set()

        for cat_key, cat_name in sorted(MESH_CATEGORIES.items()):
            fact = f"mesh_category(category_{cat_name})"
            if fact not in facts_added:
                theory.add_fact(fact)
                facts_added.add(fact)

        for desc_ui, desc_name in sorted(self.descriptors.items()):
            norm = self._normalize(desc_name)
            fact = f"mesh_descriptor({norm})"
            if fact not in facts_added:
                theory.add_fact(fact)
                facts_added.add(fact)

        for child_id, parent_id in self.parent_child:
            child_norm = self._resolve_norm(child_id)
            parent_norm = self._resolve_norm(parent_id)

            if not child_norm or not parent_norm:
                continue

            key = (child_norm, parent_norm)
            if key in rules_added:
                continue
            rules_added.add(key)

            theory.add_rule(Rule(
                head=f"isa({child_norm}, {parent_norm})",
                body=(),
                rule_type=RuleType.STRICT,
                label=f"mesh_tax_{child_norm}_{parent_norm}",
                metadata={"source": "MeSH"},
            ))

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for cross-ontology combination."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child_id, parent_id in self.parent_child:
            child_norm = self._resolve_norm(child_id)
            parent_norm = self._resolve_norm(parent_id)
            if child_norm and parent_norm:
                taxonomy[child_norm].add(parent_norm)
        return dict(taxonomy)

    # ── Helpers ───────────────────────────────────────────────────

    def _resolve_norm(self, identifier: str) -> Optional[str]:
        """Resolve a descriptor UI or synthetic category id to a normalised name."""
        if identifier.startswith("category_"):
            return identifier
        name = self.descriptors.get(identifier)
        return self._normalize(name) if name else None

    @staticmethod
    def _normalize(name: str) -> str:
        """Lowercase, replace whitespace/hyphens with underscores, strip non-alnum."""
        name = name.lower().replace(" ", "_").replace("-", "_")
        name = re.sub(r"[^a-z0-9_]", "", name)
        if name and not name[0].isalpha():
            name = "c_" + name
        return name


# ── Convenience function ──────────────────────────────────────────

def extract_from_mesh(xml_path: Path) -> Theory:
    """Extract a taxonomic Theory from a MeSH XML descriptor file.

    Args:
        xml_path: Path to the MeSH descriptor XML
                  (e.g. ``desc2025.xml`` from NLM).

    Returns:
        Theory with strict taxonomic rules derived from the MeSH hierarchy.
    """
    extractor = MeshExtractor(xml_path)
    extractor.load()
    extractor.extract()
    return extractor.to_theory()
