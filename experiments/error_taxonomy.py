"""
Error Taxonomy -- paper Section 5.

Classifies prediction failures into five error classes:

  E1 - Correct (no error)
  E2 - Non-conservative: resolves anomaly but too broad (breaks other expectations)
  E3 - Does not resolve: wrong head or condition, anomaly persists
  E4 - Parse failure: response is syntactically unparseable as a defeater rule
  E5 - Wrong but conservative: some other valid-looking rule that doesn't match gold

For Level 2 (rule abduction), only E1 and a simplified E3/E4 apply.

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

ERROR_LABELS = {
    # Paper Section 4.8 taxonomy (all codes are errors; 'correct' = no error)
    "correct":                      "Correct",
    "E1_decoder_failure":           "E1 Decoder failure (unparseable output)",
    "E2_derivation_failure":        "E2 Derivation failure (anomaly persists)",
    "E3_minimality_violation":      "E3 Minimality violation (over-specified)",
    "E4_conservativity_violation":  "E4 Conservativity violation (breaks expectations)",
    "E5_strength_shortfall":        "E5 Strength shortfall (weaker than gold)",
    # Level 2 simplified codes
    "E1_correct":                   "Correct (Level 2)",
    "E3_no_resolve":                "E2/E3 Does not restore derivability (Level 2)",
    "E4_parse_failure":             "E1 Decoder failure (Level 2)",
    "unknown":                      "Unknown",
}


def _is_level3(ev: dict) -> bool:
    iid = ev.get("instance_id", "")
    return "l3" in iid.lower() or "-l3-" in iid


def _classify_level2(ev: dict) -> str:
    """
    Simplified error classification for Level 2 (no formal metrics available).

    Uses paper E1-E5 labels:
      E1_decoder_failure  -- decoder completely failed (FAILED stage)
      E2_derivation_failure -- decoded hypothesis does not restore derivability
      correct             -- correct response
    """
    m = ev.get("metrics", {})
    if m.get("correct", False):
        return "correct"
    stage = m.get("decoder_stage", "FAILED")
    if stage == "FAILED":
        return "E1_decoder_failure"
    return "E2_derivation_failure"


def build_error_taxonomy(evaluations: list[dict]) -> dict:
    """
    Build error taxonomy over all evaluations.

    Returns per-level, per-model, per-modality breakdown of error classes.
    """
    by_level: dict = defaultdict(lambda: defaultdict(int))
    by_model: dict = defaultdict(lambda: defaultdict(int))
    by_modality: dict = defaultdict(lambda: defaultdict(int))
    overall: dict = defaultdict(int)

    for ev in evaluations:
        m = ev.get("metrics", {})
        level = "3" if _is_level3(ev) else "2"
        model = ev.get("model", "unknown")
        modality = ev.get("modality", "unknown")

        if level == "3":
            error_class = m.get("error_class") or "unknown"
        else:
            error_class = _classify_level2(ev)

        by_level[level][error_class] += 1
        by_model[model][error_class] += 1
        by_modality[modality][error_class] += 1
        overall[error_class] += 1

    return {
        "overall": dict(overall),
        "by_level": {k: dict(v) for k, v in by_level.items()},
        "by_model": {k: dict(v) for k, v in by_model.items()},
        "by_modality": {k: dict(v) for k, v in by_modality.items()},
    }


def print_error_report(evaluations: list[dict]) -> None:
    print("=" * 70)
    print("Error Taxonomy -- Section 5")
    print("=" * 70)
    print()

    taxonomy = build_error_taxonomy(evaluations)
    total = sum(taxonomy["overall"].values())

    print("Overall Error Distribution:")
    for code, label in ERROR_LABELS.items():
        count = taxonomy["overall"].get(code, 0)
        print(f"  {label:<40} {count:>5}  ({count/total:.1%})")
    print()

    print("Error Distribution by Level:")
    for level in sorted(taxonomy["by_level"]):
        lvl_counts = taxonomy["by_level"][level]
        lvl_total = sum(lvl_counts.values())
        print(f"  Level {level} (n={lvl_total}):")
        for code, label in ERROR_LABELS.items():
            count = lvl_counts.get(code, 0)
            if count:
                print(f"    {label:<40} {count:>5}  ({count/lvl_total:.1%})")
    print()

    print("Error Distribution by Model:")
    for model, model_counts in sorted(taxonomy["by_model"].items()):
        model_total = sum(model_counts.values())
        correct = model_counts.get("E1_correct", 0)
        print(f"  {model:<35} acc={correct/model_total:.1%}  (n={model_total})")
        for code in ("E2_non_conservative", "E3_no_resolve", "E4_parse_failure", "E5_wrong_but_conservative"):
            count = model_counts.get(code, 0)
            if count:
                print(f"    {ERROR_LABELS[code]:<40} {count:>4}  ({count/model_total:.1%})")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--results-file", default=None)
    parser.add_argument("--save", default=None)
    args = parser.parse_args()

    path = Path(args.results_file) if args.results_file else Path(args.results_dir)
    evaluations = []
    if path.is_dir():
        for f in path.glob("*.json"):
            d = json.load(open(f))
            evaluations.extend(d.get("evaluations", []) if isinstance(d, dict) else d)
    else:
        d = json.load(open(path))
        evaluations = d.get("evaluations", []) if isinstance(d, dict) else d

    if not evaluations:
        print("No evaluations found.")
        sys.exit(1)

    print_error_report(evaluations)

    if args.save:
        taxonomy = build_error_taxonomy(evaluations)
        with open(args.save, "w") as f:
            json.dump(taxonomy, f, indent=2)
        print(f"\nTaxonomy saved to: {args.save}")
