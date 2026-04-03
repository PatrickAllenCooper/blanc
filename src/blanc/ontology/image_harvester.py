"""
Image harvester for M5 visual grounding.

Queries external image sources (Wikidata P18, VisualSem, BabelNet)
to build an ImageManifest that maps DeFAb entity identifiers to
representative images.

Author: Patrick Cooper
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import unquote

from blanc.codec.image_manifest import EntityImage, ImageManifest
from blanc.core.theory import Theory

logger = logging.getLogger(__name__)

_NORMALIZE_RE = re.compile(r"[^a-z0-9_]")


def _normalize(text: str) -> str:
    text = text.lower().replace(" ", "_").replace("-", "_")
    return _NORMALIZE_RE.sub("", text)


# ---------------------------------------------------------------
# Wikidata P18 harvester
# ---------------------------------------------------------------

class WikidataImageHarvester:
    """Harvest representative images from Wikidata P18 properties.

    Uses the same SPARQL endpoint and rate-limiting approach as
    ``WikidataExtractor`` but queries only for image (P18) values.
    """

    _ENDPOINT = "https://query.wikidata.org/sparql"
    _BATCH_SIZE = 40

    def __init__(
        self,
        user_agent: str = "DeFAb/1.0 (patrick.cooper@colorado.edu)",
        delay: float = 2.0,
        thumb_width: int = 640,
    ):
        self.user_agent = user_agent
        self.delay = delay
        self.thumb_width = thumb_width
        self._last_query: float = 0.0

    def _query(self, sparql: str) -> Optional[Dict[str, Any]]:
        try:
            from SPARQLWrapper import JSON, SPARQLWrapper
        except ImportError as exc:
            raise ImportError(
                "Install 'sparqlwrapper' for Wikidata image harvesting: "
                "pip install sparqlwrapper"
            ) from exc

        elapsed = time.monotonic() - self._last_query
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

        wrapper = SPARQLWrapper(self._ENDPOINT)
        wrapper.setQuery(sparql)
        wrapper.setReturnFormat(JSON)
        wrapper.setTimeout(60)
        wrapper.addCustomHttpHeader("User-Agent", self.user_agent)

        for attempt in range(3):
            try:
                self._last_query = time.monotonic()
                return wrapper.query().convert()
            except Exception as exc:
                logger.warning("P18 query attempt %d failed: %s", attempt + 1, exc)
                if attempt < 2:
                    time.sleep(self.delay * (2 ** attempt))
        return None

    def harvest_by_qids(
        self,
        qid_to_entity: Dict[str, str],
    ) -> ImageManifest:
        """Query P18 images for a mapping of Wikidata Q-IDs to entity names."""
        manifest = ImageManifest()
        qids = list(qid_to_entity.keys())

        for start in range(0, len(qids), self._BATCH_SIZE):
            batch = qids[start : start + self._BATCH_SIZE]
            values = " ".join(f"wd:{q}" for q in batch)
            sparql = f"""\
SELECT ?item ?itemLabel ?image WHERE {{
  VALUES ?item {{ {values} }}
  ?item wdt:P18 ?image .
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
"""
            results = self._query(sparql)
            if results is None:
                continue

            for binding in results.get("results", {}).get("bindings", []):
                item_uri = binding.get("item", {}).get("value", "")
                item_label = binding.get("itemLabel", {}).get("value", "")
                image_url = binding.get("image", {}).get("value", "")

                qid = item_uri.rsplit("/", 1)[-1] if "/" in item_uri else item_uri
                entity_name = qid_to_entity.get(qid, _normalize(item_label or qid))

                thumb_url = _commons_thumb_url(image_url, self.thumb_width)

                manifest.add(EntityImage(
                    entity_id=entity_name,
                    source="wikidata",
                    source_id=qid,
                    url=thumb_url or image_url,
                    media_type=_guess_media_type(image_url),
                    metadata={
                        "original_url": image_url,
                        "item_label": item_label,
                    },
                ))

            logger.info(
                "P18 batch %d-%d: %d images found",
                start, start + len(batch),
                sum(1 for b in results.get("results", {}).get("bindings", [])),
            )

        return manifest

    def harvest_from_theory(
        self,
        theory: Theory,
        qid_map: Optional[Dict[str, str]] = None,
    ) -> ImageManifest:
        """Harvest images for entities present in a Theory.

        Args:
            theory: Theory whose entity names we want images for.
            qid_map: Optional mapping ``{entity_name: "Qxxx"}``. If not
                provided, attempts to find QIDs in rule metadata.
        """
        if qid_map is None:
            qid_map = _extract_qids_from_theory(theory)

        if not qid_map:
            logger.warning("No QID mapping available; cannot harvest images.")
            return ImageManifest()

        qid_to_entity = {v: k for k, v in qid_map.items()}
        return self.harvest_by_qids(qid_to_entity)


# ---------------------------------------------------------------
# VisualSem bridge
# ---------------------------------------------------------------

class VisualSemBridge:
    """Map VisualSem node data to an ImageManifest.

    VisualSem stores a join DataFrame (``join_df.pkl``) with columns
    including ``node_id``, ``bnid`` (BabelNet synset), ``wnid``
    (WordNet offset), and ``image_path``.
    """

    def __init__(self, visualsem_dir: Path):
        self.root = Path(visualsem_dir)

    def build_manifest(
        self,
        entity_filter: Optional[Set[str]] = None,
    ) -> ImageManifest:
        """Load VisualSem data and produce an ImageManifest.

        Args:
            entity_filter: If given, only include entities whose
                normalised name appears in this set.
        """
        try:
            import pandas as pd
        except ImportError as exc:
            raise ImportError(
                "Install 'pandas' for VisualSem integration: pip install pandas"
            ) from exc

        df_path = self.root / "join_df.pkl"
        if not df_path.is_file():
            logger.error("VisualSem join_df.pkl not found at %s", df_path)
            return ImageManifest()

        df = pd.read_pickle(df_path)
        manifest = ImageManifest()

        for _, row in df.iterrows():
            bnid = str(row.get("bnid", ""))
            wnid = str(row.get("wnid", ""))
            img_rel = str(row.get("image_path", ""))
            label = str(row.get("label", row.get("lemma", "")))

            entity_name = _normalize(label) if label else _normalize(bnid)

            if entity_filter and entity_name not in entity_filter:
                continue

            img_abs = self.root / img_rel if img_rel else None

            manifest.add(EntityImage(
                entity_id=entity_name,
                source="visualsem",
                source_id=bnid or wnid,
                url="",
                local_path=str(img_abs) if img_abs and img_abs.is_file() else None,
                media_type=_guess_media_type(img_rel),
                metadata={"wnid": wnid, "bnid": bnid},
            ))

        logger.info(
            "VisualSem: loaded %d images for %d entities",
            manifest.image_count(),
            manifest.entity_count(),
        )
        return manifest


# ---------------------------------------------------------------
# BabelNet image stub
# ---------------------------------------------------------------

class BabelNetImageHarvester:
    """Harvest images from BabelNet REST API (v9).

    Requires a BabelNet API key. Lower priority than Wikidata/VisualSem
    since BabelNet has rate limits and requires registration.
    """

    _API_BASE = "https://babelnet.io/v9"

    def __init__(self, api_key: str, delay: float = 1.0):
        self.api_key = api_key
        self.delay = delay

    def harvest_synsets(
        self,
        synset_ids: Dict[str, str],
    ) -> ImageManifest:
        """Query BabelNet for images of the given synset IDs.

        Args:
            synset_ids: Mapping ``{entity_name: "bn:xxxxx"}``.
        """
        try:
            import requests
        except ImportError as exc:
            raise ImportError(
                "Install 'requests' for BabelNet image harvesting: "
                "pip install requests"
            ) from exc

        manifest = ImageManifest()

        for entity_name, bnid in synset_ids.items():
            clean_id = bnid.replace("bn:", "bn%3A")
            url = (
                f"{self._API_BASE}/getSynset"
                f"?id={clean_id}&targetLang=EN&key={self.api_key}"
            )
            try:
                resp = requests.get(url, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                logger.warning("BabelNet query for %s failed: %s", bnid, exc)
                time.sleep(self.delay)
                continue

            for img_data in data.get("images", []):
                img_url = img_data.get("thumbUrl") or img_data.get("url", "")
                if not img_url:
                    continue
                manifest.add(EntityImage(
                    entity_id=entity_name,
                    source="babelnet",
                    source_id=bnid,
                    url=img_url,
                    media_type=_guess_media_type(img_url),
                    metadata={"babelnet_source": img_data.get("source", "")},
                ))

            time.sleep(self.delay)

        logger.info(
            "BabelNet: harvested %d images for %d entities",
            manifest.image_count(),
            manifest.entity_count(),
        )
        return manifest


# ---------------------------------------------------------------
# Download helper
# ---------------------------------------------------------------

def download_images(
    manifest: ImageManifest,
    output_dir: Path,
    max_per_entity: int = 3,
    timeout: int = 30,
) -> int:
    """Download images referenced in a manifest to local disk.

    Skips entries that are already downloaded. Updates ``local_path``
    in-place on each EntityImage.

    Returns the number of newly downloaded images.
    """
    try:
        import requests
    except ImportError as exc:
        raise ImportError(
            "Install 'requests' for image downloads: pip install requests"
        ) from exc

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    downloaded = 0

    for entity_key, images in manifest.entities.items():
        count = 0
        for img in images:
            if count >= max_per_entity:
                break
            if img.is_downloaded():
                count += 1
                continue
            if not img.url:
                continue

            ext = _url_extension(img.url)
            filename = f"{entity_key}_{img.source}_{_short_hash(img.url)}{ext}"
            dest = output_dir / img.source / filename
            dest.parent.mkdir(parents=True, exist_ok=True)

            try:
                resp = requests.get(img.url, timeout=timeout, stream=True)
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                img.local_path = str(dest)
                downloaded += 1
                count += 1
            except Exception as exc:
                logger.warning("Download failed for %s: %s", img.url, exc)

    logger.info("Downloaded %d new images to %s", downloaded, output_dir)
    return downloaded


# ---------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------

def _commons_thumb_url(full_url: str, width: int = 640) -> Optional[str]:
    """Convert a Wikimedia Commons file URL to a thumbnail URL."""
    if "Special:FilePath/" not in full_url:
        return None
    filename = full_url.rsplit("Special:FilePath/", 1)[-1]
    filename = unquote(filename).replace(" ", "_")
    md5 = hashlib.md5(filename.encode()).hexdigest()
    return (
        f"https://upload.wikimedia.org/wikipedia/commons/thumb/"
        f"{md5[0]}/{md5[0:2]}/{filename}/{width}px-{filename}"
    )


def _guess_media_type(path_or_url: str) -> str:
    lower = path_or_url.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".gif"):
        return "image/gif"
    if lower.endswith(".webp"):
        return "image/webp"
    if lower.endswith(".svg"):
        return "image/svg+xml"
    return "image/jpeg"


def _url_extension(url: str) -> str:
    for ext in (".png", ".gif", ".webp", ".svg"):
        if ext in url.lower():
            return ext
    return ".jpg"


def _short_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def _extract_qids_from_theory(theory: Theory) -> Dict[str, str]:
    """Try to find Wikidata QIDs stored in rule metadata."""
    qid_map: Dict[str, str] = {}
    qid_re = re.compile(r"Q\d+")

    for rule in theory.rules:
        meta = rule.metadata
        if not meta:
            continue
        for key in ("domain_class", "qid", "wikidata_id", "source_id"):
            val = meta.get(key, "")
            if val and qid_re.fullmatch(str(val)):
                head_pred = rule.head.split("(")[0].lstrip("~")
                qid_map[_normalize(head_pred)] = str(val)
    return qid_map
