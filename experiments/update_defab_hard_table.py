"""Print a LaTeX-ready DeFAb-Hard accuracy table from the latest evaluation files.

Reads experiments/results/defab_hard_eval_20260511/results_foundry-*.json and
prints the per-axis x per-strategy accuracies in the format used by
tab:defabhard_results in paper/full_paper.tex.

Run after DeepSeek-R1 and Kimi-K2.5 evaluations complete to refresh the table.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict


RESULTS_DIR = Path("experiments/results/defab_hard_eval_20260511")
INSTANCES_DIR = Path("instances/defab_hard")

DISPLAY_NAMES = {
    "deepseek": "DeepSeek-R1",
    "gpt": "GPT-5.2-chat",
    "claude": "Claude Sonnet~4.6",
    "kimi": "Kimi-K2.5",
}
ORDER = ["gpt", "claude", "deepseek", "kimi"]


def load_axis_ids() -> dict[str, set[str]]:
    out: dict[str, set[str]] = {"h1": set(), "h2": set(), "h3": set()}
    for axis in out:
        with open(INSTANCES_DIR / axis / "instances.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        for inst in data["instances"]:
            out[axis].add(f"{axis}-{inst['name']}")
    return out


def parse_model(file: Path, axis_ids: dict[str, set[str]]) -> dict | None:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)
    evals = data.get("evaluations", [])
    if not evals:
        return None
    bucket: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for r in evals:
        iid = r.get("instance_id", "")
        for axis, ids in axis_ids.items():
            if iid in ids:
                strategy = r.get("strategy", "?")
                correct = bool(r.get("metrics", {}).get("correct", False))
                bucket[(axis, strategy)].append(correct)
                break
    if not bucket:
        return None
    out = {}
    for axis in ("h1", "h2", "h3"):
        for strategy in ("direct", "cot"):
            evals_subset = bucket.get((axis, strategy), [])
            n = len(evals_subset)
            out[f"{axis}_{strategy}"] = {
                "n": n,
                "acc": (sum(evals_subset) / n) if n else None,
            }
    pooled_total = sum(s["n"] for s in out.values())
    pooled_correct = sum(
        sum(bucket.get((a, s), []))
        for a in ("h1", "h2", "h3")
        for s in ("direct", "cot")
    )
    out["pooled"] = {
        "n": pooled_total,
        "acc": (pooled_correct / pooled_total) if pooled_total else None,
    }
    return out


def fmt(cell: dict | None) -> str:
    if cell is None or cell["n"] == 0 or cell["acc"] is None:
        return "---"
    pct = cell["acc"] * 100
    return f"{pct:.1f}\\%"


def main() -> int:
    axis_ids = load_axis_ids()
    panels: dict[str, dict | None] = {}
    for short in ORDER:
        f = RESULTS_DIR / f"results_foundry-{short}.json"
        if f.exists():
            panels[short] = parse_model(f, axis_ids)
        else:
            panels[short] = None

    print("\\begin{tabular}{@{}lcccccc@{}}")
    print("\\toprule")
    print("\\textbf{Model} & H1 dir. & H1 CoT & H2 dir. & H2 CoT & H3 dir. & H3 CoT \\\\")
    print("\\midrule")
    for short in ORDER:
        name = DISPLAY_NAMES[short]
        p = panels[short]
        if p is None:
            print(f"{name:<22} & \\multicolumn{{6}}{{c}}{{\\textit{{in progress}}}} \\\\")
            continue
        cells = [
            fmt(p["h1_direct"]), fmt(p["h1_cot"]),
            fmt(p["h2_direct"]), fmt(p["h2_cot"]),
            fmt(p["h3_direct"]), fmt(p["h3_cot"]),
        ]
        print(f"{name:<22} & " + " & ".join(c for c in cells) + " \\\\")
    print("\\midrule")
    for short in ORDER:
        p = panels[short]
        if p is None:
            continue
        pooled = p["pooled"]
        if pooled["acc"] is None:
            continue
        print(f"Pooled ({DISPLAY_NAMES[short]}) & "
              f"\\multicolumn{{6}}{{c}}{{${pooled['acc']*100:.1f}\\%$ across "
              f"$n={pooled['n']}$ evaluations}} \\\\")
    print("\\bottomrule")
    print("\\end{tabular}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
