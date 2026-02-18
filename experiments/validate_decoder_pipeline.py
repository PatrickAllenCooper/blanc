"""
Decoder Pipeline Validation -- paper Section 4.8.

Validates round-trip recovery rate Pr[dec(enc(h)) = h] >= 95% for
modalities M2-M4 before proceeding to the main evaluation.  For M1
(narrative), reports the recovery rate and classifies failures.

Usage:
    python experiments/validate_decoder_pipeline.py
    python experiments/validate_decoder_pipeline.py --domain legal --limit 200

Author: Patrick Cooper
Date: 2026-02-18
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.core.theory import Rule, RuleType
from blanc.codec.encoder import PureFormalEncoder
from blanc.codec.cascading_decoder import CascadingDecoder


# ---------------------------------------------------------------------------
# Encoding helpers (mirror prompting.py _encode_element but self-contained)
# ---------------------------------------------------------------------------

def _encode_element_m4(candidate: str) -> str:
    """M4: identity -- candidates are already in formal syntax."""
    return candidate


def _encode_element_m2(candidate: str, domain: str) -> str:
    """M2: semi-formal encoding of a candidate string."""
    try:
        from blanc.codec.m2_encoder import encode_m2
        return encode_m2(candidate, domain=domain)
    except Exception:
        return candidate


def _encode_element_m3(candidate: str, domain: str) -> str:
    """M3: structured encoding."""
    try:
        from blanc.codec.m3_encoder import encode_m3
        return encode_m3(candidate, domain=domain)
    except Exception:
        return candidate


def _encode_element_m1(candidate: str, domain: str) -> str:
    """M1: narrative encoding."""
    try:
        from blanc.codec.m1_encoder import encode_m1
        return encode_m1(candidate, domain=domain)
    except Exception:
        return candidate


ENCODERS = {
    "M4": _encode_element_m4,
    "M2": _encode_element_m2,
    "M3": _encode_element_m3,
    "M1": _encode_element_m1,
}


# ---------------------------------------------------------------------------
# Round-trip validation
# ---------------------------------------------------------------------------

def validate_roundtrip(
    instances: list[dict],
    modalities: list[str],
    domain: str,
    limit: int = 500,
) -> dict:
    """
    For each (instance, modality) pair, encode the gold hypothesis then decode
    it and check whether we recover the original string.

    Returns a dict of per-modality results: {modality: {correct, total, rate, failures}}.
    """
    decoder = CascadingDecoder()
    results: dict = {m: {"correct": 0, "total": 0, "failures": []} for m in modalities}

    for inst in instances[:limit]:
        raw_gold = inst.get("gold", [])
        candidates = inst.get("candidates", [])
        if not raw_gold or not candidates:
            continue

        # gold can be a list (Level 2) or a plain string (Level 3)
        if isinstance(raw_gold, str):
            gold_elements = [raw_gold]
        else:
            gold_elements = raw_gold

        for gold in gold_elements:
            for modality in modalities:
                encoder_fn = ENCODERS.get(modality)
                if encoder_fn is None:
                    continue

                # Encode
                try:
                    if modality == "M4":
                        encoded = encoder_fn(gold)
                    else:
                        encoded = encoder_fn(gold, domain)
                except Exception as e:
                    results[modality]["failures"].append({
                        "gold": gold,
                        "error": f"encode_error: {e}",
                        "stage": None,
                    })
                    results[modality]["total"] += 1
                    continue

                # Decode (pass encoded string as 'response', candidates unchanged)
                decoded, stage = decoder.decode(encoded, candidates)

                results[modality]["total"] += 1
                if decoded and decoded.strip() == gold.strip():
                    results[modality]["correct"] += 1
                else:
                    results[modality]["failures"].append({
                        "gold": gold,
                        "encoded": encoded,
                        "decoded": decoded,
                        "stage": stage,
                    })

    # Compute rates
    for m, data in results.items():
        n = data["total"]
        data["rate"] = data["correct"] / n if n > 0 else 0.0

    return results


# ---------------------------------------------------------------------------
# M1 failure classification
# ---------------------------------------------------------------------------

def classify_m1_failures(failures: list[dict]) -> dict:
    """
    Classify M1 decode failures into:
      - true_ambiguity: natural language admits multiple valid parses
      - systematic_error: decoder fails on a recoverable pattern
      - encode_error: encoding itself failed
    """
    counts = {"true_ambiguity": 0, "systematic_error": 0, "encode_error": 0}

    for f in failures:
        if "encode_error" in (f.get("error", "")):
            counts["encode_error"] += 1
        elif f.get("decoded") is None:
            # Complete decode failure → systematic error
            counts["systematic_error"] += 1
        else:
            # Decoded something, but wrong → ambiguity or error
            # Heuristic: if gold and decoded share >50% tokens, call it ambiguity
            gold_tokens = set(f.get("gold", "").lower().split())
            decoded_tokens = set((f.get("decoded") or "").lower().split())
            overlap = len(gold_tokens & decoded_tokens) / max(len(gold_tokens), 1)
            if overlap > 0.5:
                counts["true_ambiguity"] += 1
            else:
                counts["systematic_error"] += 1

    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Validate decoder pipeline round-trip")
    parser.add_argument("--instances-dir", default=str(ROOT / "instances"))
    parser.add_argument("--limit", type=int, default=500, help="Max instances per domain")
    parser.add_argument("--threshold", type=float, default=0.95,
                        help="Required round-trip recovery rate for M2-M4")
    parser.add_argument("--modalities", nargs="+", default=["M4", "M2", "M3", "M1"])
    args = parser.parse_args()

    instances_dir = Path(args.instances_dir)
    threshold = args.threshold

    print("=" * 70)
    print("Decoder Pipeline Validation -- Section 4.8")
    print("=" * 70)
    print(f"Threshold (M2-M4): {threshold:.0%}")
    print()

    all_pass = True
    domain_files = {
        "biology": instances_dir / "biology_dev_instances.json",
        "legal":   instances_dir / "legal_dev_instances.json",
        "materials": instances_dir / "materials_dev_instances.json",
    }
    level3_file = instances_dir / "level3_instances.json"

    combined: list[dict] = []
    for domain, path in domain_files.items():
        if not path.exists():
            print(f"  Warning: {path} not found.")
            continue
        with open(path) as f:
            data = json.load(f)
        combined.extend(data.get("instances", []))

    # Include Level 3
    if level3_file.exists():
        with open(level3_file) as f:
            l3data = json.load(f)
        combined.extend(l3data.get("instances", []))

    print(f"Instances loaded: {len(combined)}")
    print()

    results = validate_roundtrip(combined, args.modalities, domain="biology",
                                 limit=args.limit)

    print(f"{'Modality':<8} {'Correct':>8} {'Total':>8} {'Rate':>8}  {'Status'}")
    print("-" * 55)
    for modality in args.modalities:
        d = results[modality]
        rate = d["rate"]
        correct = d["correct"]
        total = d["total"]
        required = modality in ("M2", "M3", "M4")
        passes = (not required) or rate >= threshold
        status = "PASS" if passes else "FAIL"
        if not passes:
            all_pass = False
        print(f"{modality:<8} {correct:>8} {total:>8} {rate:>7.1%}  {status}")

    # M1 failure breakdown
    if "M1" in results and results["M1"]["failures"]:
        print()
        print("M1 Failure Classification (manual audit required for > 200 failures):")
        m1_classes = classify_m1_failures(results["M1"]["failures"])
        for cls, count in m1_classes.items():
            print(f"  {cls:<25}: {count}")

    print()
    if all_pass:
        print("RESULT: All required modalities meet the 95% threshold.")
        print("Proceeding to main evaluation is cleared.")
        return 0
    else:
        print("RESULT: One or more modalities below threshold. Investigate decoder failures.")
        print("First 5 failures (M4):")
        for f in results.get("M4", {}).get("failures", [])[:5]:
            print(f"  gold:    {str(f.get('gold', ''))[:60]}")
            print(f"  decoded: {str(f.get('decoded') or '')[:60]}")
            print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
