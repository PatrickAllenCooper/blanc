"""Parse DeFAb-Hard pilot results for completed Foundry models.

Filters the full L3 evaluation result file down to H1/H2/H3 instances and
reports per-axis and pooled accuracy with decoder distribution.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict


RESULTS_DIR = Path("experiments/results/defab_hard_eval_20260511")
INSTANCES_DIR = Path("instances/defab_hard")


def load_hard_instance_ids() -> dict[str, set[str]]:
    axis_to_ids: dict[str, set[str]] = {"h1": set(), "h2": set(), "h3": set()}
    for axis in ("h1", "h2", "h3"):
        path = INSTANCES_DIR / axis / "instances.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        instances = data["instances"] if isinstance(data, dict) else data
        for inst in instances:
            name = inst.get("name") or inst.get("instance_id") or inst.get("id")
            if name:
                axis_to_ids[axis].add(f"{axis}-{name}")
    return axis_to_ids


def parse_results(file: Path, axis_ids: dict[str, set[str]]) -> dict:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    results = data.get("evaluations", data.get("results", data))
    if isinstance(results, dict):
        results = list(results.values())

    per_axis = {axis: defaultdict(list) for axis in axis_ids}
    for r in results:
        iid = r.get("instance_id", "")
        for axis, ids in axis_ids.items():
            if iid in ids:
                strategy = r.get("strategy", "unknown")
                metrics = r.get("metrics", {})
                correct = bool(metrics.get("correct", r.get("correct", False)))
                decoder = metrics.get("decoder_used", r.get("decoder_used", r.get("decoder", "?")))
                per_axis[axis][strategy].append({"correct": correct, "decoder": decoder})
                break

    summary = {}
    for axis in ("h1", "h2", "h3"):
        for strategy in ("direct", "cot"):
            evals = per_axis[axis].get(strategy, [])
            n = len(evals)
            if n == 0:
                continue
            correct = sum(1 for e in evals if e["correct"])
            failed = sum(1 for e in evals if e["decoder"] == "FAILED")
            summary[f"{axis}_{strategy}"] = {
                "n": n,
                "accuracy": correct / n,
                "decoder_failures": failed,
                "decoder_failure_rate": failed / n if n else 0.0,
            }
    pooled_n = sum(len(per_axis[a].get(s, [])) for a in axis_ids for s in ("direct", "cot"))
    pooled_correct = sum(
        sum(1 for e in per_axis[a].get(s, []) if e["correct"])
        for a in axis_ids for s in ("direct", "cot")
    )
    pooled_failed = sum(
        sum(1 for e in per_axis[a].get(s, []) if e["decoder"] == "FAILED")
        for a in axis_ids for s in ("direct", "cot")
    )
    summary["pooled"] = {
        "n": pooled_n,
        "accuracy": pooled_correct / pooled_n if pooled_n else 0.0,
        "decoder_failures": pooled_failed,
    }
    return summary


def main() -> int:
    axis_ids = load_hard_instance_ids()
    print(f"DeFAb-Hard pilot instance counts: H1={len(axis_ids['h1'])}, H2={len(axis_ids['h2'])}, H3={len(axis_ids['h3'])}")
    print(f"Total: {sum(len(v) for v in axis_ids.values())}\n")

    for model_file in sorted(RESULTS_DIR.glob("results_foundry-*.json")):
        model_name = model_file.stem.replace("results_foundry-", "")
        print(f"=== {model_name.upper()} ===")
        summary = parse_results(model_file, axis_ids)
        print(f"{'Subset':<20} {'N':>6} {'Acc':>8} {'DecFail':>8} {'DecFailRate':>12}")
        print("-" * 60)
        for key, s in summary.items():
            n = s["n"]
            acc = s["accuracy"] * 100
            df = s["decoder_failures"]
            dfr = s.get("decoder_failure_rate", df / n if n else 0.0) * 100
            print(f"{key:<20} {n:>6} {acc:>7.1f}% {df:>8} {dfr:>11.1f}%")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
