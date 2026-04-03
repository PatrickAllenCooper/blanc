"""Tests for M5 visual grounding encoder."""

import pytest

from blanc.author.generation import AbductiveInstance
from blanc.codec.image_manifest import EntityImage, ImageManifest
from blanc.codec.m5_encoder import (
    MultimodalPrompt,
    PromptImage,
    encode_m5,
    groundability_score,
)
from blanc.core.theory import Rule, RuleType, Theory


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def theory_with_entities():
    theory = Theory()
    theory.add_fact("bird(tweety)")
    theory.add_fact("penguin(opus)")
    theory.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1",
    ))
    theory.add_rule(Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d1",
    ))
    return theory


@pytest.fixture
def instance(theory_with_entities):
    inst = AbductiveInstance(
        D_minus=theory_with_entities,
        target="flies(tweety)",
        candidates=["bird(tweety)", "penguin(tweety)"],
        gold=["bird(tweety)"],
        level=2,
    )
    inst.id = "test_m5_001"
    return inst


@pytest.fixture
def manifest_with_images(tmp_path):
    img_path = tmp_path / "tweety.jpg"
    img_path.write_bytes(b"\xff\xd8\xff\xe0")  # minimal JPEG header

    manifest = ImageManifest()
    manifest.add(EntityImage(
        entity_id="tweety",
        source="wikidata",
        source_id="Q12345",
        url="https://example.com/tweety.jpg",
        local_path=str(img_path),
        media_type="image/jpeg",
    ))
    return manifest


@pytest.fixture
def empty_manifest():
    return ImageManifest()


# -------------------------------------------------------------------
# encode_m5
# -------------------------------------------------------------------


class TestEncodeM5:
    def test_returns_multimodal_prompt(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images)
        assert isinstance(result, MultimodalPrompt)

    def test_replace_variant_hides_entity_name(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images, variant="replace")
        assert "[IMAGE:TWEETY]" in result.text

    def test_supplement_variant_shows_both(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images, variant="supplement")
        assert "[IMAGE:TWEETY]" in result.text
        assert "bird(tweety)" in result.text

    def test_images_populated(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images, variant="replace")
        assert len(result.images) >= 1
        assert all(isinstance(img, PromptImage) for img in result.images)

    def test_is_multimodal_flag(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images)
        assert result.is_multimodal

    def test_no_images_when_manifest_empty(self, instance, empty_manifest):
        result = encode_m5(instance, empty_manifest)
        assert not result.is_multimodal
        assert result.images == []

    def test_invalid_variant_raises(self, instance, empty_manifest):
        with pytest.raises(ValueError, match="Unknown M5 variant"):
            encode_m5(instance, empty_manifest, variant="invalid")

    def test_contains_task_description(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images)
        assert "TASK:" in result.text
        assert "CANDIDATES:" in result.text
        assert "TARGET:" in result.text

    def test_candidates_preserved(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images)
        assert "1." in result.text
        assert "2." in result.text

    def test_note_added_when_images_present(self, instance, manifest_with_images):
        result = encode_m5(instance, manifest_with_images, variant="replace")
        assert "NOTE:" in result.text

    def test_no_note_when_no_images(self, instance, empty_manifest):
        result = encode_m5(instance, empty_manifest)
        assert "NOTE:" not in result.text


# -------------------------------------------------------------------
# groundability_score
# -------------------------------------------------------------------


class TestGroundabilityScore:
    def test_full_coverage(self, instance, manifest_with_images):
        score = groundability_score(instance, manifest_with_images)
        assert 0.0 < score <= 1.0

    def test_zero_coverage(self, instance, empty_manifest):
        score = groundability_score(instance, empty_manifest)
        assert score == 0.0

    def test_empty_theory(self, empty_manifest):
        inst = AbductiveInstance(
            D_minus=Theory(),
            target="x",
            candidates=["a"],
            gold=["a"],
            level=1,
        )
        assert groundability_score(inst, empty_manifest) == 0.0


# -------------------------------------------------------------------
# PromptImage dataclass
# -------------------------------------------------------------------


class TestPromptImage:
    def test_defaults(self):
        pi = PromptImage(entity="bird", local_path="/img.jpg")
        assert pi.media_type == "image/jpeg"
        assert pi.placement == "inline_fact"

    def test_custom_placement(self):
        pi = PromptImage(entity="bird", local_path="/img.jpg", placement="before_theory")
        assert pi.placement == "before_theory"
