"""
Phase B6: Novel Correct Resolution Analysis (Section 6.8).

Measures the fraction of correct fine-tuned model responses that are not in the
gold hypothesis set -- i.e., genuinely novel valid defeaters discovered through
fine-tuning that were not constructed by the Author algorithm.

A correct response is counted as "novel" if:
  - It is decoded successfully (D1/D2/D3)
  - The DeFAb verifier accepts it (graded_score >= 0.75 or correct=True)
  - It does not match any gold hypothesis (case-insensitive exact match after
    normalization)

High novel resolution rate indicates that fine-tuning has generalized beyond
the training distribution -- the model has learned to construct new valid
defeaters, not merely memorized gold answers.

Usage:
  python experiments/finetuning/analyze_novel_resolutions.py \\
      --results-dir experiments/results/ \\
      --instances-dir instances/

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))


def _load_result_file(path: Path) -> tuple[list[dict], dict]:
    with open(path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, {}
    return data.get("evaluations", []), data.get("metadata", {})


def _load_all_results(results_dir: Path) -> list[tuple[list[dict], dict]]:
    results = []
    for path in sorted(results_dir.rglob("*.json")):
        try:
            evals, meta = _load_result_file(path)
            if evals:
                results.append((evals, meta))
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def _is_finetuned(meta: dict) -> bool:
    return "checkpoint" in meta


def _load_training_config(checkpoint: str) -> dict:
    cfg_path = Path(checkpoint).parent / "training_config.json"
    if not cfg_path.exists():
        cfg_path = Path(checkpoint) / "training_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            return json.load(f)
    return {}


def _model_short(base_model: str) -> str:
    if "72b" in base_model.lower():
        return "Qwen-72B"
    if "32b" in base_model.lower():
        return "Qwen-32B"
    if "deepseek" in base_model.lower() or "r1" in base_model.lower():
        return "DS-R1-70B"
    return base_model.split("/")[-1][:15]


def _level(ev: dict) -> int:
    iid = ev.get("instance_id", "")
    if "l3" in iid.lower() or "-l3-" in iid:
        return 3
    return ev.get("level", 2)


def _normalize(text: str) -> str:
    return " ".join(text.strip().lower().split())


def main() -> int:
    p = argparse.ArgumentParser(description="Novel resolution analysis (Section 6.8).")
    p.add_argument("--results-dir",  default="experiments/results")
    p.add_argument("--instances-dir", default="instances")
    args = p.parse_args()

    results_dir   = ROOT / args.results_dir
    instances_dir = ROOT / args.instances_dir

    # --- Load gold hypothesis sets from instances ---
    gold_by_id: dict[str, set[str]] = {}
    try:
        from blanc.author.loaders import load_instances_from_json
        instances = load_instances_from_json(instances_dir, include_level3=True)
        for inst in instances:
            golds = getattr(inst, "gold", [])
            gold_by_id[inst.id] = {_normalize(str(g)) for g in (golds or [])}
        print(f"Loaded gold sets for {len(gold_by_id)} instances.")
    except Exception as e:
        print(f"Warning: could not load instances ({e}). "
              "Novel resolution detection will use response metadata only.")

    all_results = _load_all_results(results_dir)
    ft_results  = [(e, m) for e, m in all_results if _is_finetuned(m)]

    if not ft_results:
        print("No fine-tuned results found. Run Phase B5 evaluations first.")
        return 1

    print("\n" + "=" * 72)
    print("Novel Correct Resolution Analysis (Section 6.8)")
    print("=" * 72)
    print(f"{'Model':<14} {'Level':<7} {'Correct':>8} {'Novel':>8} {'Novel%':>8}")
    print("-" * 72)

    for evals, meta in sorted(ft_results, key=lambda x: x[1].get("checkpoint", "")):
        cfg   = _load_training_config(meta.get("checkpoint", ""))
        model = _model_short(meta.get("base_model", cfg.get("base_model", "?")))

        for level in [2, 3]:
            level_evals = [e for e in evals if _level(e) == level]
            correct_evals = [e for e in level_evals
                             if e.get("metrics", {}).get("correct", False)]
            if not correct_evals:
                continue

            novel_count = 0
            for ev in correct_evals:
                iid      = ev.get("instance_id", "")
                decoded  = ev.get("metrics", {}).get("decoded_response", None)
                if decoded and iid in gold_by_id:
                    norm = _normalize(str(decoded))
                    if norm not in gold_by_id[iid]:
                        novel_count += 1
                elif ev.get("metrics", {}).get("novel", False):
                    # Fallback: use novel flag if present
                    novel_count += 1

            n_correct   = len(correct_evals)
            novel_frac  = novel_count / n_correct if n_correct else float("nan")
            novel_str   = f"{novel_frac:.1%}" if n_correct else "---"
            print(f"  {model:<12} L{level}     {n_correct:>8} {novel_count:>8} {novel_str:>8}")

    print("""
Notes:
  Novel resolutions demonstrate that the fine-tuned model generalizes beyond
  the gold set and can construct new valid defeaters. High novel% at L3 is
  evidence that the model has internalized the rationality constraints of
  defeasible belief revision, not merely memorized training examples.
""")
    return 0


if __name__ == "__main__":
    sys.exit(main())
