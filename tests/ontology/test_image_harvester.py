"""Tests for image harvester utilities."""

from unittest.mock import MagicMock, patch

import pytest

from blanc.codec.image_manifest import EntityImage, ImageManifest
from blanc.core.theory import Rule, RuleType, Theory
from blanc.ontology.image_harvester import (
    WikidataImageHarvester,
    _commons_thumb_url,
    _extract_qids_from_theory,
    _guess_media_type,
    _normalize,
    _short_hash,
    _url_extension,
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


class TestNormalize:
    def test_basic(self):
        assert _normalize("Emperor Penguin") == "emperor_penguin"

    def test_hyphens(self):
        assert _normalize("blue-footed") == "blue_footed"

    def test_strips_special(self):
        result = _normalize("hello@world!")
        assert "@" not in result


class TestUrlExtension:
    def test_jpg_default(self):
        assert _url_extension("https://example.com/photo") == ".jpg"

    def test_png(self):
        assert _url_extension("https://example.com/icon.png?v=1") == ".png"

    def test_gif(self):
        assert _url_extension("https://example.com/anim.gif") == ".gif"

    def test_webp(self):
        assert _url_extension("https://example.com/photo.webp") == ".webp"


class TestWikidataImageHarvester:
    def test_init_defaults(self):
        h = WikidataImageHarvester()
        assert h.thumb_width == 640
        assert h.delay == 2.0

    def test_harvest_from_theory_empty(self):
        h = WikidataImageHarvester()
        manifest = h.harvest_from_theory(Theory())
        assert manifest.entity_count() == 0

    def test_harvest_from_theory_with_qid_map(self):
        h = WikidataImageHarvester()
        theory = Theory()
        theory.add_fact("bird(tweety)")
        with patch.object(h, "harvest_by_qids", return_value=ImageManifest()) as mock:
            h.harvest_from_theory(theory, qid_map={"bird": "Q5113"})
            mock.assert_called_once()

    def test_harvest_by_qids_empty(self):
        h = WikidataImageHarvester()
        with patch.object(h, "_query", return_value=None):
            manifest = h.harvest_by_qids({})
            assert manifest.entity_count() == 0

    def test_harvest_by_qids_parses_results(self):
        h = WikidataImageHarvester()
        mock_result = {
            "results": {
                "bindings": [
                    {
                        "item": {"value": "http://www.wikidata.org/entity/Q9482"},
                        "itemLabel": {"value": "penguin"},
                        "image": {"value": "http://commons.wikimedia.org/wiki/Special:FilePath/Penguin.jpg"},
                    }
                ]
            }
        }
        with patch.object(h, "_query", return_value=mock_result):
            manifest = h.harvest_by_qids({"Q9482": "penguin"})
            assert manifest.has_image("penguin")


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

    def test_respects_max_per_entity(self, tmp_path):
        manifest = ImageManifest()
        for i in range(5):
            manifest.add(EntityImage(
                entity_id="penguin",
                source="test",
                source_id=f"t{i}",
                url=f"https://example.com/img{i}.jpg",
            ))

        mock_resp = MagicMock()
        mock_resp.iter_content.return_value = [b"\xff\xd8"]
        mock_resp.raise_for_status = MagicMock()

        mock_requests = MagicMock()
        mock_requests.get.return_value = mock_resp

        import sys
        sys.modules["requests"] = mock_requests
        try:
            count = download_images(manifest, tmp_path / "out", max_per_entity=2)
            assert count == 2
        finally:
            del sys.modules["requests"]
            import requests  # restore real module
