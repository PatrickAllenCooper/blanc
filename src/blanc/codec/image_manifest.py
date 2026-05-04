"""
Image manifest for M5 visual grounding modality.

Maps entity identifiers to image metadata for visually grounding
defeasible reasoning instances. Supports multiple image sources
(Wikidata P18, VisualSem, BabelNet) with preference-based selection.

Author: Anonymous Authors
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from blanc.core.theory import Theory


@dataclass
class EntityImage:
    """A single image associated with a knowledge base entity."""

    entity_id: str
    source: str
    source_id: str
    url: str
    local_path: Optional[str] = None
    media_type: str = "image/jpeg"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_downloaded(self) -> bool:
        if self.local_path is None:
            return False
        return Path(self.local_path).is_file()


SOURCE_PRIORITY = ["wikidata", "visualsem", "babelnet", "imagenet"]


@dataclass
class ImageManifest:
    """
    Index mapping entity names to available images.

    Designed for lookup during M5 encoding: given an entity predicate
    name from a Theory, find the best available image to ground it.
    """

    entities: Dict[str, List[EntityImage]] = field(default_factory=dict)

    def add(self, image: EntityImage) -> None:
        key = _normalize_entity(image.entity_id)
        if key not in self.entities:
            self.entities[key] = []
        self.entities[key].append(image)

    def has_image(self, entity: str) -> bool:
        return _normalize_entity(entity) in self.entities

    def get_image(
        self,
        entity: str,
        preferred_source: Optional[str] = None,
    ) -> Optional[EntityImage]:
        """Return the best available image for *entity*.

        Selection order:
        1. If *preferred_source* is given and present, use it.
        2. Otherwise fall back to SOURCE_PRIORITY ordering.
        3. Within a source, prefer downloaded images.
        """
        key = _normalize_entity(entity)
        candidates = self.entities.get(key)
        if not candidates:
            return None

        if preferred_source:
            src_matches = [c for c in candidates if c.source == preferred_source]
            if src_matches:
                downloaded = [c for c in src_matches if c.is_downloaded()]
                return downloaded[0] if downloaded else src_matches[0]

        for source in SOURCE_PRIORITY:
            src_matches = [c for c in candidates if c.source == source]
            if src_matches:
                downloaded = [c for c in src_matches if c.is_downloaded()]
                return downloaded[0] if downloaded else src_matches[0]

        return candidates[0]

    def get_all_images(self, entity: str) -> List[EntityImage]:
        return list(self.entities.get(_normalize_entity(entity), []))

    def entity_count(self) -> int:
        return len(self.entities)

    def image_count(self) -> int:
        return sum(len(imgs) for imgs in self.entities.values())

    def downloaded_count(self) -> int:
        return sum(
            1
            for imgs in self.entities.values()
            for img in imgs
            if img.is_downloaded()
        )

    # ------------------------------------------------------------------
    # Theory coverage
    # ------------------------------------------------------------------

    def covered_entities(self, theory: Theory) -> Set[str]:
        """Return the set of theory entities that have at least one image."""
        theory_entities = _extract_entity_names(theory)
        return {e for e in theory_entities if self.has_image(e)}

    def coverage_ratio(self, theory: Theory) -> float:
        """Fraction of distinct entity names in *theory* that have images."""
        theory_entities = _extract_entity_names(theory)
        if not theory_entities:
            return 0.0
        covered = sum(1 for e in theory_entities if self.has_image(e))
        return covered / len(theory_entities)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "version": 1,
            "entities": {
                k: [asdict(img) for img in imgs]
                for k, imgs in self.entities.items()
            },
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ImageManifest:
        path = Path(path)
        raw = json.loads(path.read_text(encoding="utf-8"))
        manifest = cls()
        for _key, img_list in raw.get("entities", {}).items():
            for img_dict in img_list:
                manifest.add(EntityImage(**img_dict))
        return manifest

    def merge(self, other: ImageManifest) -> None:
        """Merge another manifest into this one, deduplicating by (entity, source, source_id)."""
        for _key, imgs in other.entities.items():
            for img in imgs:
                key = _normalize_entity(img.entity_id)
                existing = self.entities.get(key, [])
                already = any(
                    e.source == img.source and e.source_id == img.source_id
                    for e in existing
                )
                if not already:
                    self.add(img)


def _normalize_entity(name: str) -> str:
    """Lowercase, strip whitespace, collapse underscores/hyphens."""
    return re.sub(r"[\s_-]+", "_", name.strip().lower())


def _extract_entity_names(theory: Theory) -> Set[str]:
    """Extract distinct entity/concept names from theory facts and rule predicates."""
    names: Set[str] = set()
    _pred_re = re.compile(r"^~?([a-z_][a-z0-9_]*)\(")
    _const_re = re.compile(r"\(([^()]+)\)")

    for fact in theory.facts:
        m = _pred_re.match(fact)
        if m:
            names.add(m.group(1))
        cm = _const_re.search(fact)
        if cm:
            for arg in cm.group(1).split(","):
                arg = arg.strip()
                if arg and arg[0].islower():
                    names.add(arg)

    for rule in theory.rules:
        atoms = [rule.head] + list(rule.body)
        for atom in atoms:
            m = _pred_re.match(atom)
            if m:
                names.add(m.group(1))

    return names
