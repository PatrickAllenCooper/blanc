"""
Results Analysis -- paper Section 5.

Processes raw evaluation output (produced by run_evaluation.py /
EvaluationPipeline) and computes the per-model, per-modality,
per-domain, and per-level breakdowns required for Section 5 tables.

Usage:
    python experiments/analyze_results.py --results-dir experiments/results
    python experiments/analyze_results.py --results-file experiments/results/results_azure.json

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


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_results(path: Path) -> list[dict]:
    """Load evaluations from a single results JSON or a directory of them."""
    evaluations = []
    if path.is_dir():
        files = list(path.glob("*.json"))
        if not files:
            print(f"Warning: no JSON files found in {path}")
        for f in files:
            evaluations.extend(_load_file(f))
    else:
        evaluations.extend(_load_file(path))
    return evaluations


def _load_file(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    # Two formats: {"evaluations": [...], "summary": {...}} or raw list
    if isinstance(data, list):
        return data
    return data.get("evaluations", [])


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def accuracy_by(evaluations: list[dict], *keys: str) -> dict:
    """
    Compute accuracy broken down by the specified keys.

    Keys may be any combination of: 'model', 'modality', 'strategy',
    'level', 'domain'.
    """
    buckets: dict = defaultdict(lambda: {"correct": 0, "total": 0})

    for ev in evaluations:
        metrics = ev.get("metrics", {})
        bucket_key = tuple(
            _extract(ev, k) for k in keys
        )
        buckets[bucket_key]["total"] += 1
        if metrics.get("correct", False):
            buckets[bucket_key]["correct"] += 1

    result = {}
    for key, counts in sorted(buckets.items()):
        n = counts["total"]
        result[key] = {
            "correct": counts["correct"],
            "total": n,
            "accuracy": counts["correct"] / n if n > 0 else 0.0,
        }
    return result


def _extract(ev: dict, key: str) -> str:
    """Extract a dimension value from an evaluation record."""
    if key == "model":
        return ev.get("model", "unknown")
    if key == "modality":
        return ev.get("modality", "unknown")
    if key == "strategy":
        return ev.get("strategy", "unknown")
    if key == "level":
        iid = ev.get("instance_id", "")
        if "l3" in iid.lower() or "-l3-" in iid:
            return "3"
        return "2"
    if key == "domain":
        iid = ev.get("instance_id", "")
        for d in ("biology", "legal", "materials"):
            if d in iid.lower():
                return d
        return "unknown"
    return ev.get(key, "unknown")


def decoder_distribution(evaluations: list[dict]) -> dict:
    """Count evaluations per decoder stage (D1/D2/D3/FAILED)."""
    counts: dict = defaultdict(int)
    for ev in evaluations:
        stage = ev.get("metrics", {}).get("decoder_stage", "FAILED")
        counts[stage] += 1
    return dict(counts)


def rendering_robust_accuracy(evaluations: list[dict]) -> dict:
    """
    Compute rendering-robust accuracy (Definition def:robustacc, paper.tex):
        Acc_robust(M) = (1/N) sum_i min_j Pr_M[h in H*_i | rho^(j)_enc(I_i)]

    In practice (with one run per modality): for each (model, instance), take the
    minimum accuracy across the four modalities and average over instances.

    Returns per-model robust accuracy.
    """
    from collections import defaultdict

    # Group evaluations by (model, instance_id, modality)
    # For each (model, instance_id) we need accuracy per modality.
    by_model_inst_mod: dict = defaultdict(lambda: defaultdict(dict))
    for ev in evaluations:
        model = ev.get("model", "unknown")
        iid = ev.get("instance_id", "")
        modality = ev.get("modality", "unknown")
        correct = int(ev.get("metrics", {}).get("correct", False))
        by_model_inst_mod[model][iid][modality] = correct

    modalities = {"M1", "M2", "M3", "M4"}
    result = {}
    for model, instances in by_model_inst_mod.items():
        per_instance_min = []
        for iid, mod_scores in instances.items():
            available = {m: mod_scores[m] for m in modalities if m in mod_scores}
            if not available:
                continue
            per_instance_min.append(min(available.values()))
        if per_instance_min:
            result[model] = {
                "robust_accuracy": sum(per_instance_min) / len(per_instance_min),
                "n_instances": len(per_instance_min),
                "n_modalities_avg": sum(
                    len(mod_scores) for mod_scores in instances.values()
                ) / len(instances),
            }
    return result


def cot_lift(evaluations: list[dict]) -> dict:
    """
    Compute delta_CoT = Acc_CoT - Acc_direct per (model, level).

    Requires evaluations with strategy='direct' and strategy='cot'.
    """
    from collections import defaultdict

    by_model_level_strategy: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for ev in evaluations:
        model = ev.get("model", "unknown")
        level = _extract(ev, "level")
        strategy = ev.get("strategy", "direct")
        correct = int(ev.get("metrics", {}).get("correct", False))
        by_model_level_strategy[model][level][strategy].append(correct)

    result = {}
    for model, levels in by_model_level_strategy.items():
        result[model] = {}
        for level, strategies in levels.items():
            direct = strategies.get("direct", [])
            cot = strategies.get("cot", [])
            if not direct or not cot:
                continue
            acc_direct = sum(direct) / len(direct)
            acc_cot = sum(cot) / len(cot)
            result[model][level] = {
                "acc_direct": acc_direct,
                "acc_cot": acc_cot,
                "delta_cot": acc_cot - acc_direct,
                "n_direct": len(direct),
                "n_cot": len(cot),
            }
    return result


def graded_score_summary(evaluations: list[dict]) -> dict:
    """
    Aggregate graded partial credit scores (Section 4.6) for Level 3 evaluations.

    Returns mean graded score per model and overall distribution.
    """
    from collections import defaultdict

    l3 = [ev for ev in evaluations
          if ev.get("metrics", {}).get("graded_score") is not None]
    if not l3:
        return {}

    by_model: dict = defaultdict(list)
    for ev in l3:
        score = ev["metrics"]["graded_score"]
        model = ev.get("model", "unknown")
        by_model[model].append(score)

    all_scores = [ev["metrics"]["graded_score"] for ev in l3]
    distribution: dict = {0.0: 0, 0.25: 0, 0.5: 0, 0.75: 0, 1.0: 0}
    for s in all_scores:
        if s in distribution:
            distribution[s] += 1

    return {
        "n": len(l3),
        "mean_graded_score": sum(all_scores) / len(all_scores),
        "score_distribution": distribution,
        "by_model": {
            model: {
                "mean": sum(scores) / len(scores),
                "n": len(scores),
            }
            for model, scores in by_model.items()
        },
    }


def level3_metrics_summary(evaluations: list[dict]) -> dict:
    """
    Aggregate Level 3 formal metrics across all evaluations.

    Returns means and distributions for: resolves_anomaly, is_conservative,
    nov, d_rev, parse_success, error_class.
    """
    l3 = [ev for ev in evaluations if _extract(ev, "level") == "3"]
    if not l3:
        return {}

    metrics_lists: dict = defaultdict(list)
    error_counts: dict = defaultdict(int)

    for ev in l3:
        m = ev.get("metrics", {})
        for field in ("resolves_anomaly", "is_conservative", "nov", "d_rev", "parse_success"):
            val = m.get(field)
            if val is not None:
                metrics_lists[field].append(val)
        ec = m.get("error_class") or "unknown"
        error_counts[ec] += 1

    summary: dict = {"n": len(l3)}
    for field, vals in metrics_lists.items():
        if vals:
            if isinstance(vals[0], bool):
                summary[field + "_rate"] = sum(vals) / len(vals)
            else:
                summary[field + "_mean"] = sum(vals) / len(vals)
                summary[field + "_nonzero"] = sum(1 for v in vals if v and v > 0)
    summary["error_distribution"] = dict(error_counts)
    return summary


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def print_summary(evaluations: list[dict]) -> None:
    total = len(evaluations)
    correct = sum(1 for ev in evaluations if ev.get("metrics", {}).get("correct", False))

    print(f"Total evaluations : {total}")
    print(f"Overall accuracy  : {correct / total:.1%}  ({correct}/{total})")
    print()

    # By level
    print("Accuracy by Level:")
    for key, d in accuracy_by(evaluations, "level").items():
        print(f"  Level {key[0]}: {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
    print()

    # By model
    print("Accuracy by Model:")
    for key, d in accuracy_by(evaluations, "model").items():
        print(f"  {key[0]:<30} {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
    print()

    # By modality
    print("Accuracy by Modality:")
    for key, d in accuracy_by(evaluations, "modality").items():
        print(f"  {key[0]:<8} {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
    print()

    # By domain
    print("Accuracy by Domain:")
    for key, d in accuracy_by(evaluations, "domain").items():
        print(f"  {key[0]:<12} {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
    print()

    # By strategy
    print("Accuracy by Strategy:")
    for key, d in accuracy_by(evaluations, "strategy").items():
        print(f"  {key[0]:<10} {d['accuracy']:.1%}  ({d['correct']}/{d['total']})")
    print()

    # Decoder distribution
    print("Decoder Stage Distribution:")
    for stage, count in sorted(decoder_distribution(evaluations).items()):
        print(f"  {stage:<8} {count:>6}  ({count/total:.1%})")
    print()

    # Rendering-robust accuracy (headline metric, Definition robustacc)
    robust = rendering_robust_accuracy(evaluations)
    if robust:
        print("Rendering-Robust Accuracy (worst-case over modalities -- headline metric):")
        for model, d in sorted(robust.items()):
            print(f"  {model:<30} {d['robust_accuracy']:.1%}  (n_inst={d['n_instances']}, "
                  f"avg modalities={d['n_modalities_avg']:.1f})")
        print()

    # Graded score (Level 3)
    graded = graded_score_summary(evaluations)
    if graded:
        print(f"Level 3 Graded Scores (Section 4.6, n={graded['n']}):")
        print(f"  Mean graded score: {graded['mean_graded_score']:.3f}")
        print("  Score distribution:")
        for score, count in sorted(graded["score_distribution"].items()):
            print(f"    {score:.2f}: {count:>5}  ({count/graded['n']:.1%})")
        print()

    # CoT lift
    cot = cot_lift(evaluations)
    if cot:
        print("CoT Lift (delta_CoT = Acc_CoT - Acc_direct):")
        for model, levels in sorted(cot.items()):
            for level, d in sorted(levels.items()):
                print(f"  {model:<30} Level {level}: direct={d['acc_direct']:.1%}  "
                      f"CoT={d['acc_cot']:.1%}  delta={d['delta_cot']:+.1%}")
        print()

    # Level 3 formal metrics
    l3_summary = level3_metrics_summary(evaluations)
    if l3_summary:
        print(f"Level 3 Formal Metrics (n={l3_summary['n']}):")
        for k, v in l3_summary.items():
            if k in ("n", "error_distribution"):
                continue
            if isinstance(v, float):
                print(f"  {k:<35} {v:.3f}")
            else:
                print(f"  {k:<35} {v}")
        print("  Error distribution:")
        for cls, count in sorted(l3_summary.get("error_distribution", {}).items()):
            pct = count / l3_summary["n"]
            print(f"    {cls:<35} {count:>5}  ({pct:.1%})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze DeFAb evaluation results")
    parser.add_argument("--results-dir", default=str(ROOT / "experiments" / "results"))
    parser.add_argument("--results-file", default=None,
                        help="Single results file (overrides --results-dir)")
    parser.add_argument("--save", default=None,
                        help="Save aggregated metrics to this JSON file")
    args = parser.parse_args()

    path = Path(args.results_file) if args.results_file else Path(args.results_dir)

    if not path.exists():
        print(f"Error: {path} does not exist.")
        return 1

    evaluations = load_results(path)
    if not evaluations:
        print("No evaluations found.")
        return 1

    print("=" * 70)
    print("DeFAb Results Analysis -- Section 5")
    print("=" * 70)
    print()

    print_summary(evaluations)

    if args.save:
        aggregated = {
            "total": len(evaluations),
            "by_level":    accuracy_by(evaluations, "level"),
            "by_model":    accuracy_by(evaluations, "model"),
            "by_modality": accuracy_by(evaluations, "modality"),
            "by_domain":   accuracy_by(evaluations, "domain"),
            "by_strategy": accuracy_by(evaluations, "strategy"),
            "by_model_modality": accuracy_by(evaluations, "model", "modality"),
            "by_model_level":    accuracy_by(evaluations, "model", "level"),
            "decoder_distribution": decoder_distribution(evaluations),
            "rendering_robust_accuracy": rendering_robust_accuracy(evaluations),
            "cot_lift": cot_lift(evaluations),
            "graded_score_summary": graded_score_summary(evaluations),
            "level3_metrics": level3_metrics_summary(evaluations),
        }
        # Convert tuple keys to strings for JSON serialization
        def _fix_keys(d: dict) -> dict:
            return {" x ".join(k) if isinstance(k, tuple) else k: v
                    for k, v in d.items()}
        aggregated = {k: _fix_keys(v) if isinstance(v, dict) else v
                      for k, v in aggregated.items()}

        with open(args.save, "w") as f:
            json.dump(aggregated, f, indent=2, default=str)
        print(f"\nAggregated metrics saved to: {args.save}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
