"""
FrameNet ontology extractor for DeFAb knowledge bases.

Extracts frame definitions, frame elements, and inter-frame relations
from Berkeley FrameNet 1.7 via NLTK and converts them into a defeasible
theory.

Conversion rules:
    - Inheritance relations     -> strict taxonomic rules
    - Core frame elements       -> defeasible role rules (priority 1)
    - Non-core frame elements   -> defeasible role rules (priority 2-3)
    - Using relations           -> defeasible presupposition rules

Author: Anonymous Authors
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Dict, List, Set

from blanc.core.theory import Theory, Rule, RuleType

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")

_CORE_TYPE_PRIORITY = {
    "Core": 1,
    "Core-Unexpressed": 1,
    "Peripheral": 2,
    "Extra-Thematic": 3,
}


def _normalize(text: str) -> str:
    """Lowercase, replace spaces/hyphens with underscores, strip non-alphanumeric."""
    text = text.lower().replace(" ", "_").replace("-", "_")
    return _NORMALIZE_RE.sub("", text)


class FrameNetExtractor:
    """Extract defeasible knowledge from Berkeley FrameNet 1.7.

    FrameNet organises lexical knowledge around semantic frames --
    schematic representations of situations with participant roles
    (frame elements).  Frames are connected via typed relations
    (Inheritance, Using, Subframe, Perspective_on, etc.).

    The extractor maps these structures onto defeasible logic:

    Inheritance
        Strict rules encoding IS-A between parent and child frames:
        ``parent_frame(X) :- child_frame(X)``
    Core FEs
        Defeasible rules asserting that instances of a frame typically
        fill a core role: ``has_role_fe(X) :- frame(X)`` (priority 1).
    Non-core FEs
        Lower-priority defeasible rules for peripheral (priority 2)
        and extra-thematic (priority 3) roles.
    Using
        Defeasible presupposition rules connecting a child frame to
        the background frame it presupposes.
    """

    _SOURCE = "FrameNet"

    def __init__(self) -> None:
        """Validate that the NLTK FrameNet corpus is available.

        Raises:
            ImportError: If NLTK is not installed or the framenet_v17
                corpus has not been downloaded.
        """
        try:
            from nltk.corpus import framenet as fn
        except ImportError as exc:
            raise ImportError(
                "NLTK is required for FrameNet extraction. "
                "Install it with: pip install nltk"
            ) from exc

        try:
            fn.frame_ids_and_names()
        except LookupError as exc:
            raise ImportError(
                "NLTK FrameNet corpus not found. Install it with:\n"
                "  import nltk; nltk.download('framenet_v17')"
            ) from exc

        self._fn = fn
        self.frames: list[dict] = []
        self.relations: list[dict] = []

    def extract(self) -> None:
        """Load all frames, frame elements, and inter-frame relations.

        Populates :attr:`frames` with frame data (name and FE list) and
        :attr:`relations` with typed inter-frame relation triples.  Uses
        ``fn.frames()`` for frame/FE data and ``fn.frame_relations()``
        for the global relation index (each relation appears once).
        """
        fn = self._fn

        raw_frames = fn.frames()
        logger.info("Loading %d FrameNet frames...", len(raw_frames))

        for frame in raw_frames:
            fe_list: list[dict] = []
            for fe_name, fe_obj in frame.FE.items():
                fe_list.append({
                    "name": fe_name,
                    "core_type": getattr(fe_obj, "coreType", "Peripheral"),
                })
            self.frames.append({
                "name": frame.name,
                "fes": fe_list,
            })

        raw_relations = fn.frame_relations()
        for rel in raw_relations:
            self.relations.append({
                "type": rel.type.name,
                "super_frame": rel.superFrameName,
                "sub_frame": rel.subFrameName,
            })

        logger.info(
            "Extracted %d frames, %d inter-frame relations.",
            len(self.frames),
            len(self.relations),
        )

    def to_theory(self) -> Theory:
        """Build a defeasible Theory from the extracted FrameNet data.

        Returns:
            Theory with strict inheritance rules, defeasible frame-element
            rules, and defeasible presupposition rules from Using relations.
        """
        theory = Theory()
        added: set[tuple] = set()

        for rel in self.relations:
            if rel["type"] == "Inheritance":
                parent = _normalize(rel["super_frame"])
                child = _normalize(rel["sub_frame"])
                key = ("inherit", child, parent)
                if key not in added:
                    theory.add_rule(Rule(
                        head=f"{parent}(X)",
                        body=(f"{child}(X)",),
                        rule_type=RuleType.STRICT,
                        label=f"fn_inherit_{child}_{parent}",
                        metadata={
                            "source": self._SOURCE,
                            "relation": "Inheritance",
                        },
                    ))
                    added.add(key)

        for rel in self.relations:
            if rel["type"] == "Using":
                parent = _normalize(rel["super_frame"])
                child = _normalize(rel["sub_frame"])
                key = ("using", child, parent)
                if key not in added:
                    theory.add_rule(Rule(
                        head=f"presupposes_{parent}(X)",
                        body=(f"{child}(X)",),
                        rule_type=RuleType.DEFEASIBLE,
                        label=f"fn_uses_{child}_{parent}",
                        metadata={
                            "source": self._SOURCE,
                            "relation": "Using",
                        },
                    ))
                    added.add(key)

        for frame_data in self.frames:
            frame_norm = _normalize(frame_data["name"])
            theory.add_fact(f"{frame_norm}({frame_norm})")
            for fe in frame_data["fes"]:
                fe_norm = _normalize(fe["name"])
                core_type = fe["core_type"]
                priority = _CORE_TYPE_PRIORITY.get(core_type, 3)
                key = ("fe", frame_norm, fe_norm)
                if key not in added:
                    theory.add_rule(Rule(
                        head=f"has_role_{fe_norm}(X)",
                        body=(f"{frame_norm}(X)",),
                        rule_type=RuleType.DEFEASIBLE,
                        priority=priority,
                        label=f"fn_fe_{frame_norm}_{fe_norm}",
                        metadata={
                            "source": self._SOURCE,
                            "core_type": core_type,
                            "frame": frame_data["name"],
                        },
                    ))
                    added.add(key)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return child_frame -> {parent_frames} from Inheritance relations.

        Used by the cross-ontology combiner to align frame hierarchies
        with other ontologies.
        """
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for rel in self.relations:
            if rel["type"] == "Inheritance":
                child = _normalize(rel["sub_frame"])
                parent = _normalize(rel["super_frame"])
                if child and parent:
                    taxonomy[child].add(parent)
        return dict(taxonomy)


def extract_from_framenet() -> Theory:
    """Extract a defeasible theory from FrameNet 1.7 via NLTK.

    Returns:
        Theory with frame inheritance, role, and presupposition rules.

    Raises:
        ImportError: If NLTK or the framenet_v17 corpus is not installed.
    """
    extractor = FrameNetExtractor()
    extractor.extract()
    return extractor.to_theory()
