"""Analyze ROE compliance experiment results across all four frontier models.

Reads the .jsonl outputs of scripts/run_roe_compliance_experiment.py and emits
a per-model x per-mode table reporting verifier compliance, correct abstain
rate, and reprompt budget usage.
"""
from __future__ import annotations
import json
from pathlib import Path
from collections import defaultdict


DATA_DIR = Path("data/roe_compliance")


def safe(s: str) -> str:
    return (s or "").encode("ascii", "replace").decode("ascii")


def load_records(prefix: str) -> list[dict]:
    files = sorted(DATA_DIR.glob(f"{prefix}_quiz_*.jsonl"), key=lambda p: p.stat().st_mtime)
    if not files:
        return []
    latest = files[-1]
    with open(latest, "r", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def per_mode_stats(rs: list[dict]) -> dict[str, dict]:
    by_mode: dict[str, list[dict]] = defaultdict(list)
    for r in rs:
        by_mode[r.get("mode", "?")].append(r)
    out: dict[str, dict] = {}
    for mode, items in sorted(by_mode.items()):
        n = len(items)
        if n == 0:
            continue
        correct_abstain = sum(1 for r in items if r.get("gold", {}).get("correct_abstain", False))
        any_orders = sum(1 for r in items if len(r.get("orders_admitted", [])) > 0)
        order_count = sum(len(r.get("orders_admitted", [])) for r in items)
        violations = sum(
            sum(1 for v in r.get("verdicts", []) if not v.get("compliant", True))
            for r in items
        )
        reprompts = sum(r.get("reprompts", 0) for r in items)
        compliance_rate = (1.0 - violations / order_count) if order_count else None
        out[mode] = {
            "n": n,
            "correct_abstain": correct_abstain,
            "scenarios_with_orders": any_orders,
            "total_orders": order_count,
            "violations": violations,
            "reprompts": reprompts,
            "verifier_compliance": compliance_rate,
        }
    return out


def main() -> int:
    models = [
        ("foundry-gpt", "GPT-5.2-chat"),
        ("foundry-claude", "Claude Sonnet 4.6"),
        ("foundry-deepseek", "DeepSeek-R1"),
        ("foundry-kimi", "Kimi-K2.5"),
    ]

    print(f"{'Model':<20} {'Mode':<5} {'CA':<6} {'Orders':<8} {'Viol':<5} {'Comp':<7} {'Rprmpts':<8}")
    print("-" * 70)
    for prefix, label in models:
        rs = load_records(prefix)
        if not rs:
            print(f"{label:<20} (no data found)")
            continue
        stats = per_mode_stats(rs)
        for mode, s in stats.items():
            comp = f"{s['verifier_compliance'] * 100:.0f}%" if s['verifier_compliance'] is not None else "N/A"
            print(f"{label:<20} {mode:<5} {s['correct_abstain']}/{s['n']:<3} "
                  f"{s['total_orders']:<8} {s['violations']:<5} {comp:<7} {s['reprompts']:<8}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
