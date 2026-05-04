#!/usr/bin/env python3
"""
Download entity images for M5 visual grounding.

Orchestrates image harvesting from Wikidata P18, VisualSem, and
(optionally) BabelNet, then downloads thumbnails and produces a
consolidated ImageManifest at data/images/manifest.json.

Usage:
    python scripts/download_entity_images.py --sources wikidata
    python scripts/download_entity_images.py --sources wikidata visualsem \
        --visualsem-dir /path/to/visualsem
    python scripts/download_entity_images.py --qid-map data/qid_map.json

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from blanc.codec.image_manifest import ImageManifest
from blanc.ontology.image_harvester import (
    BabelNetImageHarvester,
    VisualSemBridge,
    WikidataImageHarvester,
    download_images,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download entity images for DeFAb M5 modality."
    )
    parser.add_argument(
        "--sources",
        nargs="+",
        choices=["wikidata", "visualsem", "babelnet"],
        default=["wikidata"],
        help="Image sources to harvest from (default: wikidata).",
    )
    parser.add_argument(
        "--qid-map",
        type=Path,
        default=None,
        help="JSON file mapping entity names to Wikidata Q-IDs.",
    )
    parser.add_argument(
        "--visualsem-dir",
        type=Path,
        default=None,
        help="Path to VisualSem download directory.",
    )
    parser.add_argument(
        "--babelnet-key",
        type=str,
        default=None,
        help="BabelNet API key (required if source includes babelnet).",
    )
    parser.add_argument(
        "--babelnet-synsets",
        type=Path,
        default=None,
        help="JSON mapping entity names to BabelNet synset IDs.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=project_root / "data" / "images",
        help="Directory to download images into.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=None,
        help="Output manifest path (default: <output-dir>/manifest.json).",
    )
    parser.add_argument(
        "--existing-manifest",
        type=Path,
        default=None,
        help="Existing manifest to merge into (incremental updates).",
    )
    parser.add_argument(
        "--thumb-width",
        type=int,
        default=640,
        help="Thumbnail width in pixels for Wikidata images.",
    )
    parser.add_argument(
        "--max-per-entity",
        type=int,
        default=3,
        help="Maximum images to download per entity.",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Harvest image URLs without downloading files.",
    )

    args = parser.parse_args()
    manifest_path = args.manifest or (args.output_dir / "manifest.json")

    manifest = ImageManifest()
    if args.existing_manifest and args.existing_manifest.is_file():
        logger.info("Loading existing manifest from %s", args.existing_manifest)
        manifest = ImageManifest.load(args.existing_manifest)

    # -- Wikidata --
    if "wikidata" in args.sources:
        qid_map = _load_qid_map(args.qid_map)
        if qid_map:
            harvester = WikidataImageHarvester(thumb_width=args.thumb_width)
            qid_to_entity = {v: k for k, v in qid_map.items()}
            wd_manifest = harvester.harvest_by_qids(qid_to_entity)
            manifest.merge(wd_manifest)
            logger.info(
                "Wikidata: %d entities, %d images",
                wd_manifest.entity_count(),
                wd_manifest.image_count(),
            )
        else:
            logger.warning(
                "No QID map provided (--qid-map). Skipping Wikidata harvest."
            )

    # -- VisualSem --
    if "visualsem" in args.sources:
        if args.visualsem_dir and args.visualsem_dir.is_dir():
            bridge = VisualSemBridge(args.visualsem_dir)
            vs_manifest = bridge.build_manifest()
            manifest.merge(vs_manifest)
            logger.info(
                "VisualSem: %d entities, %d images",
                vs_manifest.entity_count(),
                vs_manifest.image_count(),
            )
        else:
            logger.warning(
                "VisualSem directory not found or not provided. "
                "Use --visualsem-dir."
            )

    # -- BabelNet --
    if "babelnet" in args.sources:
        if args.babelnet_key and args.babelnet_synsets:
            synset_map = json.loads(
                args.babelnet_synsets.read_text(encoding="utf-8")
            )
            bn_harvester = BabelNetImageHarvester(api_key=args.babelnet_key)
            bn_manifest = bn_harvester.harvest_synsets(synset_map)
            manifest.merge(bn_manifest)
            logger.info(
                "BabelNet: %d entities, %d images",
                bn_manifest.entity_count(),
                bn_manifest.image_count(),
            )
        else:
            logger.warning(
                "BabelNet requires --babelnet-key and --babelnet-synsets."
            )

    # -- Download --
    if not args.skip_download:
        count = download_images(
            manifest,
            args.output_dir,
            max_per_entity=args.max_per_entity,
        )
        logger.info("Downloaded %d new images.", count)

    # -- Save --
    manifest.save(manifest_path)
    logger.info("Manifest saved to %s", manifest_path)
    logger.info(
        "Total: %d entities, %d images (%d downloaded)",
        manifest.entity_count(),
        manifest.image_count(),
        manifest.downloaded_count(),
    )


def _load_qid_map(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
