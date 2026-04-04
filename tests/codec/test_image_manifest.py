"""Tests for ImageManifest and EntityImage."""

import json
from pathlib import Path

import pytest

from blanc.codec.image_manifest import (
    EntityImage,
    ImageManifest,
    _extract_entity_names,
    _normalize_entity,
)
from blanc.core.theory import Rule, RuleType, Theory


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------


@pytest.fixture
def sample_images():
    return [
        EntityImage(
            entity_id="penguin",
            source="wikidata",
            source_id="Q9482",
            url="https://commons.wikimedia.org/wiki/Special:FilePath/Penguin.jpg",
            local_path=None,
            media_type="image/jpeg",
            metadata={"item_label": "Emperor penguin"},
        ),
        EntityImage(
            entity_id="penguin",
            source="visualsem",
            source_id="bn:00061756n",
            url="",
            local_path="/data/images/visualsem/penguin_01.jpg",
            media_type="image/jpeg",
            metadata={},
        ),
        EntityImage(
            entity_id="eagle",
            source="wikidata",
            source_id="Q2092297",
            url="https://commons.wikimedia.org/wiki/Special:FilePath/Eagle.jpg",
            local_path=None,
            media_type="image/jpeg",
            metadata={},
        ),
    ]


@pytest.fixture
def manifest(sample_images):
    m = ImageManifest()
    for img in sample_images:
        m.add(img)
    return m


@pytest.fixture
def simple_theory():
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


# -------------------------------------------------------------------
# Normalize
# -------------------------------------------------------------------


class TestNormalize:
    def test_lowercase(self):
        assert _normalize_entity("Penguin") == "penguin"

    def test_spaces_to_underscore(self):
        assert _normalize_entity("Emperor Penguin") == "emperor_penguin"

    def test_hyphens_to_underscore(self):
        assert _normalize_entity("blue-footed") == "blue_footed"

    def test_collapse_multiple(self):
        assert _normalize_entity("a  b__c") == "a_b_c"


# -------------------------------------------------------------------
# ImageManifest basics
# -------------------------------------------------------------------


class TestImageManifest:
    def test_add_and_has(self, manifest):
        assert manifest.has_image("penguin")
        assert manifest.has_image("eagle")
        assert not manifest.has_image("ostrich")

    def test_case_insensitive_lookup(self, manifest):
        assert manifest.has_image("PENGUIN")
        assert manifest.has_image("Eagle")

    def test_entity_count(self, manifest):
        assert manifest.entity_count() == 2

    def test_image_count(self, manifest):
        assert manifest.image_count() == 3

    def test_get_image_preferred_source(self, manifest):
        img = manifest.get_image("penguin", preferred_source="visualsem")
        assert img is not None
        assert img.source == "visualsem"

    def test_get_image_fallback_priority(self, manifest):
        img = manifest.get_image("penguin")
        assert img is not None
        assert img.source == "wikidata"

    def test_get_image_missing(self, manifest):
        assert manifest.get_image("ostrich") is None

    def test_get_all_images(self, manifest):
        imgs = manifest.get_all_images("penguin")
        assert len(imgs) == 2

    def test_get_all_images_missing(self, manifest):
        assert manifest.get_all_images("ostrich") == []


# -------------------------------------------------------------------
# Theory coverage
# -------------------------------------------------------------------


class TestCoverage:
    def test_coverage_ratio(self, manifest, simple_theory):
        ratio = manifest.coverage_ratio(simple_theory)
        assert 0.0 < ratio <= 1.0

    def test_covered_entities(self, manifest, simple_theory):
        covered = manifest.covered_entities(simple_theory)
        assert "penguin" in covered

    def test_empty_theory(self, manifest):
        assert manifest.coverage_ratio(Theory()) == 0.0


# -------------------------------------------------------------------
# Serialization round-trip
# -------------------------------------------------------------------


class TestSerialization:
    def test_save_load_roundtrip(self, manifest, tmp_path):
        path = tmp_path / "manifest.json"
        manifest.save(path)

        loaded = ImageManifest.load(path)
        assert loaded.entity_count() == manifest.entity_count()
        assert loaded.image_count() == manifest.image_count()
        assert loaded.has_image("penguin")
        assert loaded.has_image("eagle")

    def test_saved_json_is_valid(self, manifest, tmp_path):
        path = tmp_path / "manifest.json"
        manifest.save(path)
        data = json.loads(path.read_text())
        assert "version" in data
        assert data["version"] == 1
        assert "entities" in data


# -------------------------------------------------------------------
# Merge
# -------------------------------------------------------------------


class TestMerge:
    def test_merge_deduplicates(self, manifest, sample_images):
        other = ImageManifest()
        other.add(sample_images[0])  # duplicate
        other.add(EntityImage(
            entity_id="ostrich",
            source="wikidata",
            source_id="Q7368",
            url="https://example.com/ostrich.jpg",
        ))

        manifest.merge(other)
        assert manifest.entity_count() == 3
        assert manifest.has_image("ostrich")
        assert manifest.image_count() == 4  # 3 original + 1 new

    def test_merge_empty(self, manifest):
        before = manifest.image_count()
        manifest.merge(ImageManifest())
        assert manifest.image_count() == before


# -------------------------------------------------------------------
# Entity extraction from theory
# -------------------------------------------------------------------


class TestExtractEntities:
    def test_extracts_predicate_names(self, simple_theory):
        names = _extract_entity_names(simple_theory)
        assert "bird" in names
        assert "penguin" in names
        assert "flies" in names

    def test_extracts_constants(self, simple_theory):
        names = _extract_entity_names(simple_theory)
        assert "tweety" in names
        assert "opus" in names

    def test_empty_theory(self):
        assert _extract_entity_names(Theory()) == set()
