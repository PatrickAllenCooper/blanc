"""Integration tests for M5 visual grounding through the evaluation pipeline.

Tests the full chain: AbductiveInstance + ImageManifest -> M5 encoding ->
RenderedPrompt with images -> model query routing -> cache key extension.
"""

import hashlib
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from blanc.author.generation import AbductiveInstance
from blanc.codec.image_manifest import EntityImage, ImageManifest
from blanc.codec.m5_encoder import PromptImage
from blanc.core.theory import Rule, RuleType, Theory
from model_interface import ModelInterface, ModelResponse
from prompting import RenderedPrompt, render_prompt
from response_cache import ResponseCache


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def theory():
    t = Theory()
    t.add_fact("bird(tweety)")
    t.add_fact("penguin(opus)")
    t.add_rule(Rule(
        head="flies(X)", body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE, label="r1",
    ))
    return t


@pytest.fixture
def instance(theory):
    inst = AbductiveInstance(
        D_minus=theory,
        target="flies(tweety)",
        candidates=["bird(tweety)", "penguin(tweety)"],
        gold=["bird(tweety)"],
        level=2,
    )
    inst.id = "m5_int_001"
    return inst


@pytest.fixture
def manifest_with_image(tmp_path):
    img = tmp_path / "tweety.jpg"
    img.write_bytes(b"\xff\xd8\xff\xe0")
    m = ImageManifest()
    m.add(EntityImage(
        entity_id="tweety",
        source="wikidata",
        source_id="Q12345",
        url="https://example.com/tweety.jpg",
        local_path=str(img),
    ))
    return m


# -------------------------------------------------------------------
# render_prompt with M5
# -------------------------------------------------------------------


class TestRenderPromptM5:
    def test_m5_returns_rendered_prompt(self, instance, manifest_with_image):
        rendered = render_prompt(
            instance, "M5", "direct", manifest=manifest_with_image,
        )
        assert isinstance(rendered, RenderedPrompt)
        assert rendered.modality == "M5"

    def test_m5_has_images(self, instance, manifest_with_image):
        rendered = render_prompt(
            instance, "M5", "direct", manifest=manifest_with_image,
        )
        assert len(rendered.images) >= 1

    def test_m5_replace_variant(self, instance, manifest_with_image):
        rendered = render_prompt(
            instance, "M5", "direct",
            manifest=manifest_with_image, m5_variant="replace",
        )
        assert "[IMAGE:TWEETY]" in rendered.prompt

    def test_m5_supplement_variant(self, instance, manifest_with_image):
        rendered = render_prompt(
            instance, "M5", "direct",
            manifest=manifest_with_image, m5_variant="supplement",
        )
        assert "bird(tweety)" in rendered.prompt
        assert "[IMAGE:TWEETY]" in rendered.prompt

    def test_m5_without_manifest_raises(self, instance):
        with pytest.raises(ValueError, match="manifest"):
            render_prompt(instance, "M5", "direct")

    def test_m5_metadata_includes_variant(self, instance, manifest_with_image):
        rendered = render_prompt(
            instance, "M5", "direct", manifest=manifest_with_image,
        )
        assert rendered.metadata["m5_variant"] == "replace"


# -------------------------------------------------------------------
# M1-M4 backward compatibility
# -------------------------------------------------------------------


class TestM1M4Unchanged:
    """Ensure M1-M4 rendering is unaffected by M5 additions."""

    @pytest.mark.parametrize("modality", ["M1", "M2", "M3", "M4"])
    def test_text_modality_no_images(self, instance, modality):
        rendered = render_prompt(instance, modality, "direct")
        assert rendered.images == []

    @pytest.mark.parametrize("modality", ["M1", "M2", "M3", "M4"])
    def test_text_modality_prompt_is_string(self, instance, modality):
        rendered = render_prompt(instance, modality, "direct")
        assert isinstance(rendered.prompt, str)
        assert len(rendered.prompt) > 0


# -------------------------------------------------------------------
# query_multimodal on ModelInterface
# -------------------------------------------------------------------


class TestQueryMultimodal:
    def test_fallback_to_query_when_no_images(self):
        """query_multimodal with no images should fall through to query."""

        class StubModel(ModelInterface):
            def query(self, prompt, temperature=0.0, max_tokens=512, **kw):
                return ModelResponse(
                    text="ok", model="stub", tokens_input=1,
                    tokens_output=1, cost=0.0, latency=0.0,
                )

            @property
            def cost_per_1k_input(self): return 0.0

            @property
            def cost_per_1k_output(self): return 0.0

        model = StubModel("stub")
        resp = model.query_multimodal("hello", images=None)
        assert resp.text == "ok"

    def test_raises_when_images_and_not_implemented(self):
        """query_multimodal with images should raise for base impl."""

        class StubModel(ModelInterface):
            def query(self, prompt, temperature=0.0, max_tokens=512, **kw):
                return ModelResponse(
                    text="ok", model="stub", tokens_input=1,
                    tokens_output=1, cost=0.0, latency=0.0,
                )

            @property
            def cost_per_1k_input(self): return 0.0

            @property
            def cost_per_1k_output(self): return 0.0

        model = StubModel("stub")
        fake_images = [PromptImage(entity="x", local_path="/x.jpg")]
        with pytest.raises(NotImplementedError, match="does not support multimodal"):
            model.query_multimodal("hello", images=fake_images)


# -------------------------------------------------------------------
# Cache key extension
# -------------------------------------------------------------------


class TestCacheKeyWithImages:
    def test_no_images_same_as_before(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key_without = cache.make_key("i1", "m", "M4", "direct", prompt="hello")
        key_with_none = cache.make_key(
            "i1", "m", "M4", "direct", prompt="hello", image_hashes=None,
        )
        assert key_without == key_with_none

    def test_images_change_key(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key_no_img = cache.make_key("i1", "m", "M5", "direct", prompt="hello")
        key_with_img = cache.make_key(
            "i1", "m", "M5", "direct", prompt="hello",
            image_hashes=["abc123"],
        )
        assert key_no_img != key_with_img

    def test_different_images_different_keys(self, tmp_path):
        cache = ResponseCache(cache_dir=tmp_path / "cache")
        key_a = cache.make_key(
            "i1", "m", "M5", "direct", prompt="hello",
            image_hashes=["aaa"],
        )
        key_b = cache.make_key(
            "i1", "m", "M5", "direct", prompt="hello",
            image_hashes=["bbb"],
        )
        assert key_a != key_b
