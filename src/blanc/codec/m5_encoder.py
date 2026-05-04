"""
M5 Encoder: Visual Grounding Modality.

Produces a multimodal prompt that pairs entity-grounding facts with
images while keeping theory rules, target, and candidates in M4
(pure formal) text.  Two variants:

- **replace**: Entity facts are replaced by image placeholders. The
  model must identify the entity from the image alone.
- **supplement**: Entity facts retain their textual names and images
  are added alongside as supporting context.

The output is not a plain string but a ``MultimodalPrompt`` that
carries both a text component and a list of ``PromptImage`` references.
Downstream consumers (``render_prompt``, ``query_multimodal``) use
this to build provider-specific API payloads.

Author: Anonymous Authors
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Union

from blanc.author.generation import AbductiveInstance
from blanc.codec.encoder import PureFormalEncoder
from blanc.codec.image_manifest import ImageManifest
from blanc.core.theory import Rule, RuleType, Theory


@dataclass
class PromptImage:
    """An image to be included in a multimodal prompt."""

    entity: str
    local_path: str
    media_type: str = "image/jpeg"
    placement: str = "inline_fact"


@dataclass
class MultimodalPrompt:
    """A prompt consisting of text interspersed with image references."""

    text: str
    images: List[PromptImage] = field(default_factory=list)

    @property
    def is_multimodal(self) -> bool:
        return bool(self.images)


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def encode_m5(
    instance: AbductiveInstance,
    manifest: ImageManifest,
    variant: str = "replace",
    domain: str = "biology",
) -> MultimodalPrompt:
    """Encode an abductive instance in the M5 visual grounding modality.

    Args:
        instance: The abductive instance to encode.
        manifest: Image manifest mapping entities to images.
        variant: ``"replace"`` (entity names hidden, image only) or
            ``"supplement"`` (entity names shown alongside images).
        domain: Domain hint (currently unused; reserved for future
            domain-specific image selection heuristics).

    Returns:
        A ``MultimodalPrompt`` with text and image references.
    """
    if variant not in ("replace", "supplement"):
        raise ValueError(f"Unknown M5 variant: {variant!r}. Use 'replace' or 'supplement'.")

    encoder = PureFormalEncoder()
    images: List[PromptImage] = []

    grounded = _identify_groundable_entities(instance.D_minus, manifest)

    theory_text = _encode_theory_m5(
        instance.D_minus, encoder, manifest, grounded, variant, images,
    )

    lines: List[str] = []
    lines.append("THEORY:")
    lines.append("-" * 60)
    lines.append(theory_text)
    lines.append("-" * 60)
    lines.append("")

    lines.append(f"TARGET: {instance.target}")
    lines.append("")

    if instance.level == 1:
        lines.append("TASK: Which fact, when added to the theory, allows deriving the target?")
    elif instance.level == 2:
        lines.append("TASK: Which rule, when added to the theory, allows deriving the target?")
    elif instance.level == 3:
        lines.append("TASK: Which defeater or exception, when added, resolves the anomaly?")
    lines.append("")

    lines.append("CANDIDATES:")
    for i, candidate in enumerate(instance.candidates, 1):
        if isinstance(candidate, str):
            lines.append(f"  {i}. {candidate}")
        else:
            lines.append(f"  {i}. {encoder.encode_rule(candidate)}")
    lines.append("")

    lines.append("ANSWER (select number or provide element):")

    if grounded:
        note = (
            "NOTE: Some entities in this theory are identified by images "
            "rather than names. Examine the provided images to determine "
            "what each entity is."
            if variant == "replace"
            else "NOTE: Images are provided alongside entity facts as "
            "additional context."
        )
        lines.insert(0, note)
        lines.insert(1, "")

    return MultimodalPrompt(text="\n".join(lines), images=images)


def groundability_score(
    instance: AbductiveInstance,
    manifest: ImageManifest,
) -> float:
    """Fraction of entity-identifying facts whose entities have images."""
    entities = _fact_entities(instance.D_minus)
    if not entities:
        return 0.0
    return sum(1 for e in entities if manifest.has_image(e)) / len(entities)


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------

_PRED_RE = re.compile(r"^~?([a-z_][a-z0-9_]*)\(")
_CONST_RE = re.compile(r"\(([^()]+)\)")


def _fact_entities(theory: Theory) -> Set[str]:
    """Extract entity names that appear as constants in ground facts."""
    entities: Set[str] = set()
    for fact in theory.facts:
        m = _CONST_RE.search(fact)
        if m:
            for arg in m.group(1).split(","):
                arg = arg.strip()
                if arg and arg[0].islower():
                    entities.add(arg)
    return entities


def _identify_groundable_entities(
    theory: Theory,
    manifest: ImageManifest,
) -> Dict[str, PromptImage]:
    """Find entities with available images, returning PromptImage per entity."""
    grounded: Dict[str, PromptImage] = {}
    for entity in _fact_entities(theory):
        img = manifest.get_image(entity)
        if img is None:
            continue
        path = img.local_path or img.url
        if not path:
            continue
        grounded[entity] = PromptImage(
            entity=entity,
            local_path=path,
            media_type=img.media_type,
            placement="inline_fact",
        )
    return grounded


def _encode_theory_m5(
    theory: Theory,
    encoder: PureFormalEncoder,
    manifest: ImageManifest,
    grounded: Dict[str, PromptImage],
    variant: str,
    images_out: List[PromptImage],
) -> str:
    """Encode theory with M5 visual grounding applied to facts."""
    lines: List[str] = []

    # --- Facts ---
    fact_lines: List[str] = []
    for fact in sorted(theory.facts):
        entity = _fact_entity_name(fact)
        if entity and entity in grounded:
            pimg = grounded[entity]
            if pimg not in images_out:
                images_out.append(pimg)
            if variant == "replace":
                fact_lines.append(f"{fact.split('(')[0]}([IMAGE:{entity.upper()}]).")
            else:
                fact_lines.append(f"{encoder.encode_fact(fact)}  % [IMAGE:{entity.upper()}]")
        else:
            fact_lines.append(encoder.encode_fact(fact))

    if fact_lines:
        lines.append("% Facts")
        lines.extend(fact_lines)
        lines.append("")

    # --- Rules (unchanged from M4) ---
    for rule_type, header in [
        (RuleType.STRICT, "% Strict Rules"),
        (RuleType.DEFEASIBLE, "% Defeasible Rules"),
        (RuleType.DEFEATER, "% Defeaters"),
    ]:
        rules = theory.get_rules_by_type(rule_type)
        if rules:
            lines.append(header)
            for rule in rules:
                lines.append(encoder.encode_rule(rule))
            lines.append("")

    # --- Superiority (unchanged from M4) ---
    if theory.superiority:
        lines.append("% Superiority")
        for superior, inferiors in sorted(theory.superiority.items()):
            for inferior in sorted(inferiors):
                lines.append(f"{superior} > {inferior}.")

    return "\n".join(lines)


def _fact_entity_name(fact: str) -> Optional[str]:
    """Extract the primary constant from a ground fact like ``bird(tweety)``."""
    m = _CONST_RE.search(fact)
    if not m:
        return None
    args = [a.strip() for a in m.group(1).split(",")]
    for arg in args:
        if arg and arg[0].islower():
            return arg
    return None
