#!/usr/bin/env python3
"""
Analyze image coverage for M5-eligible instances.

Loads an ImageManifest and existing DeFAb instances, then reports
per-domain coverage ratios, entity availability, and the number of
instances eligible for M5 evaluation at various coverage thresholds.

Usage:
    python scripts/analyze_image_coverage.py \
        --manifest data/images/manifest.json \
        --instances instances/biology_dev_instances.json

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from blanc.codec.image_manifest import ImageManifest, _extract_entity_names
from blanc.codec.m5_encoder import groundability_score
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze image coverage for DeFAb M5 modality."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        required=True,
        help="Path to ImageManifest JSON.",
    )
    parser.add_argument(
        "--instances",
        type=Path,
        nargs="+",
        required=True,
        help="Path(s) to instance JSON files.",
    )
    parser.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[0.0, 0.25, 0.5, 0.75, 1.0],
        help="Coverage thresholds to report eligible counts.",
    )

    args = parser.parse_args()

    manifest = ImageManifest.load(args.manifest)
    logger.info(
        "Manifest: %d entities, %d images (%d downloaded)",
        manifest.entity_count(),
        manifest.image_count(),
        manifest.downloaded_count(),
    )

    all_instances: list[AbductiveInstance] = []
    for path in args.instances:
        loaded = _load_instances(path)
        logger.info("Loaded %d instances from %s", len(loaded), path)
        all_instances.extend(loaded)

    if not all_instances:
        logger.warning("No instances loaded.")
        return

    scores = [groundability_score(inst, manifest) for inst in all_instances]

    print("\n=== Image Coverage Analysis ===\n")
    print(f"Total instances: {len(all_instances)}")
    print(f"Manifest entities: {manifest.entity_count()}")
    print(f"Manifest images: {manifest.image_count()}")
    print()

    print("--- Eligible instances by threshold ---")
    for t in args.thresholds:
        eligible = sum(1 for s in scores if s >= t)
        print(f"  coverage >= {t:.0%}: {eligible}/{len(all_instances)} ({eligible/len(all_instances):.1%})")
    print()

    all_entities: set[str] = set()
    covered_entities: set[str] = set()
    for inst in all_instances:
        ents = _extract_entity_names(inst.D_minus)
        all_entities.update(ents)
        for e in ents:
            if manifest.has_image(e):
                covered_entities.add(e)

    print(f"--- Entity coverage ---")
    print(f"  Unique entities across all instances: {len(all_entities)}")
    print(f"  Entities with images: {len(covered_entities)}")
    if all_entities:
        print(f"  Entity coverage: {len(covered_entities)/len(all_entities):.1%}")

    missing = sorted(all_entities - covered_entities)
    if missing:
        print(f"\n  Top missing entities (first 20):")
        for e in missing[:20]:
            print(f"    - {e}")
    print()


def _load_instances(path: Path) -> list[AbductiveInstance]:
    """Load instances from a JSON file (supports both L2 and L3 formats)."""
    raw = json.loads(path.read_text(encoding="utf-8"))

    items = raw if isinstance(raw, list) else raw.get("instances", [raw])
    instances: list[AbductiveInstance] = []

    for item in items:
        theory = Theory()
        for fact in item.get("metadata", {}).get("facts", []):
            theory.add_fact(fact)
        for rule_str in item.get("metadata", {}).get("rules", []):
            theory.add_rule(_parse_rule_str(rule_str))

        for fact in item.get("theory_facts", []):
            theory.add_fact(fact)
        for rule_dict in item.get("theory_rules", []):
            if isinstance(rule_dict, dict):
                theory.add_rule(Rule(
                    head=rule_dict.get("head", ""),
                    body=tuple(rule_dict.get("body", [])),
                    rule_type=RuleType(rule_dict.get("rule_type", "defeasible")),
                    label=rule_dict.get("label"),
                ))
            elif isinstance(rule_dict, str):
                theory.add_rule(_parse_rule_str(rule_dict))

        target = item.get("target", item.get("anomaly", ""))
        candidates = item.get("candidates", [])
        gold = item.get("gold", [])
        level = item.get("level", 2)

        inst = AbductiveInstance(
            D_minus=theory,
            target=target,
            candidates=candidates,
            gold=gold if isinstance(gold, list) else [gold],
            level=level,
        )
        inst.id = item.get("id", item.get("name", "unknown"))
        instances.append(inst)

    return instances


def _parse_rule_str(s: str) -> Rule:
    """Minimal rule string parser for loading JSON instances."""
    s = s.strip().rstrip(".")
    if ":-" in s:
        head, body_str = s.split(":-", 1)
        body = tuple(b.strip() for b in body_str.split(",") if b.strip())
        rt = RuleType.DEFEASIBLE
        if "% defeater" in s:
            rt = RuleType.DEFEATER
        elif "% defeasible" not in s:
            rt = RuleType.STRICT
        return Rule(head=head.strip(), body=body, rule_type=rt)
    return Rule(head=s, body=(), rule_type=RuleType.FACT)


if __name__ == "__main__":
    main()
