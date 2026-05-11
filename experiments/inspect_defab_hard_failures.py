"""Inspect failure modes of frontier models on DeFAb-Hard.

For each completed model, prints a sample of incorrect responses to understand
why the model is failing on the hard axes (predicate novelty, deep chain,
multi-anomaly).
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict


RESULTS_DIR = Path("experiments/results/defab_hard_eval_20260511")


def load_hard_ids() -> dict[str, set[str]]:
    axis_to_ids: dict[str, set[str]] = {"h1": set(), "h2": set(), "h3": set()}
    for axis in axis_to_ids:
        path = Path("instances/defab_hard") / axis / "instances.json"
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for inst in data["instances"]:
            axis_to_ids[axis].add(f"{axis}-{inst['name']}")
    return axis_to_ids


def _safe(s: str) -> str:
    return s.encode("ascii", "replace").decode("ascii")


def inspect(file: Path, axis_ids: dict[str, set[str]], max_per_axis_strategy: int = 2) -> None:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    evals = data["evaluations"]

    by_bucket: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in evals:
        iid = r.get("instance_id", "")
        for axis, ids in axis_ids.items():
            if iid in ids:
                by_bucket[(axis, r.get("strategy", "?"))].append(r)
                break

    for (axis, strategy), rs in sorted(by_bucket.items()):
        wrong = [r for r in rs if not r.get("metrics", {}).get("correct", False)]
        if not wrong:
            continue
        print(f"\n--- {axis.upper()} {strategy} -- {len(wrong)}/{len(rs)} wrong --")
        sample_count = min(max_per_axis_strategy, len(wrong))
        for r in wrong[:sample_count]:
            iid = r.get("instance_id", "?")
            decoded = r.get("decoded_hypothesis", "?")
            decoded_str = _safe(str(decoded))[:120] if decoded else "(empty)"
            metrics = r.get("metrics", {})
            decoder = metrics.get("decoder_used", metrics.get("decoder", "?"))
            raw = _safe(r.get("raw_response", "") or "")[:200].replace("\n", " ")
            print(f"  {iid}")
            print(f"    decoder: {decoder}, decoded: {decoded_str}")
            print(f"    raw: {raw}...")


def main() -> int:
    axis_ids = load_hard_ids()
    for model_file in sorted(RESULTS_DIR.glob("results_foundry-*.json")):
        model = model_file.stem.replace("results_foundry-", "")
        print(f"\n{'='*70}\n{model.upper()}\n{'='*70}")
        inspect(model_file, axis_ids, max_per_axis_strategy=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
