"""Tests for image harvester utilities."""

import pytest

from blanc.codec.image_manifest import EntityImage, ImageManifest
from blanc.core.theory import Rule, RuleType, Theory
from blanc.ontology.image_harvester import (
    _commons_thumb_url,
    _extract_qids_from_theory,
    _guess_media_type,
    _short_hash,
    download_images,
)


class TestCommonsThumbUrl:
    def test_generates_thumb_url(self):
        url = "http://commons.wikimedia.org/wiki/Special:FilePath/Emperor_Penguin.jpg"
        result = _commons_thumb_url(url, 640)
        assert result is not None
        assert "640px" in result
        assert "upload.wikimedia.org" in result

    def test_returns_none_for_non_commons(self):
        assert _commons_thumb_url("https://example.com/img.jpg") is None

    def test_custom_width(self):
        url = "http://commons.wikimedia.org/wiki/Special:FilePath/Test.jpg"
        result = _commons_thumb_url(url, 320)
        assert "320px" in result


class TestGuessMediaType:
    def test_jpeg_default(self):
        assert _guess_media_type("photo.jpg") == "image/jpeg"
        assert _guess_media_type("") == "image/jpeg"

    def test_png(self):
        assert _guess_media_type("icon.png") == "image/png"

    def test_gif(self):
        assert _guess_media_type("anim.gif") == "image/gif"

    def test_webp(self):
        assert _guess_media_type("photo.webp") == "image/webp"

    def test_svg(self):
        assert _guess_media_type("diagram.svg") == "image/svg+xml"


class TestShortHash:
    def test_deterministic(self):
        assert _short_hash("hello") == _short_hash("hello")

    def test_length(self):
        assert len(_short_hash("anything")) == 12

    def test_different_inputs_differ(self):
        assert _short_hash("a") != _short_hash("b")


class TestExtractQidsFromTheory:
    def test_extracts_qids_from_metadata(self):
        theory = Theory()
        theory.add_rule(Rule(
            head="taxon(bird)",
            body=("organism(X)",),
            rule_type=RuleType.DEFEASIBLE,
            label="r1",
            metadata={"domain_class": "Q16521"},
        ))
        qids = _extract_qids_from_theory(theory)
        assert "taxon" in qids
        assert qids["taxon"] == "Q16521"

    def test_empty_theory_returns_empty(self):
        assert _extract_qids_from_theory(Theory()) == {}

    def test_ignores_non_qid_metadata(self):
        theory = Theory()
        theory.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.DEFEASIBLE,
            metadata={"source": "ConceptNet"},
        ))
        assert _extract_qids_from_theory(theory) == {}


class TestDownloadImages:
    def test_skips_already_downloaded(self, tmp_path):
        img_file = tmp_path / "existing.jpg"
        img_file.write_bytes(b"\xff\xd8")

        manifest = ImageManifest()
        manifest.add(EntityImage(
            entity_id="penguin",
            source="test",
            source_id="t1",
            url="",
            local_path=str(img_file),
        ))
        count = download_images(manifest, tmp_path / "out", max_per_entity=1)
        assert count == 0

    def test_skips_entries_without_url(self, tmp_path):
        manifest = ImageManifest()
        manifest.add(EntityImage(
            entity_id="eagle",
            source="test",
            source_id="t2",
            url="",
        ))
        count = download_images(manifest, tmp_path / "out")
        assert count == 0
