"""
Phase 4A: Analyze matched fact-injection ablation results.

Computes the cleaner contamination-gap interpretation:
  True_Delta_synth = Acc(nat-injected) - Acc(syn-injected)
  Injection_artifact = Acc(nat-original) - Acc(nat-injected)

Author: Patrick Cooper
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "experiments" / "results" / "nat_injected_20260511"

# Baseline numbers from paper Table 4 + synthetic ablation
BASELINE = {
    "deepseek": {"direct": 37.1, "cot": 92.9, "best": 65.0, "synth": 52.9},
    "gpt":      {"direct":  7.9, "cot": 87.1, "best": 47.5, "synth": 30.9},
    "claude":   {"direct": 23.6, "cot":  9.3, "best": 16.4, "synth":  2.1},
    "kimi":     {"direct":  0.8, "cot": 27.6, "best": 14.2, "synth":  2.9},
}


def parse_provider(provider: str) -> dict | None:
    path = RESULTS_DIR / f"results_foundry-{provider}.json"
    if not path.exists():
        return None
    with open(path) as f:
        d = json.load(f)
    evals = d.get("evaluations", [])
    l3 = [e for e in evals if e.get("level") == 3]
    direct = [e for e in l3 if e.get("strategy") == "direct"]
    cot = [e for e in l3 if e.get("strategy") == "cot"]
    if not direct or not cot:
        return None

    def acc(es):
        return sum(1 for e in es if e.get("metrics", {}).get("correct", False)) / len(es) * 100

    return {
        "direct": acc(direct),
        "cot": acc(cot),
        "best": (acc(direct) + acc(cot)) / 2,
        "n_direct": len(direct),
        "n_cot": len(cot),
    }


def main() -> int:
    print("Phase 4A: Matched Fact-Injection Ablation (Tier 0 L3)")
    print("=" * 80)
    print(f"{'Model':<11} {'Nat-orig':>9} {'Nat-inj':>9} {'Syn-inj':>9} "
          f"{'Old D':>8} {'True D':>8} {'Artifact':>9}")
    print("-" * 80)

    for p in ["deepseek", "gpt", "claude", "kimi"]:
        result = parse_provider(p)
        if result is None:
            print(f"{p:<11} (results pending)")
            continue
        nat_orig = BASELINE[p]["best"]
        syn = BASELINE[p]["synth"]
        nat_inj = result["best"]
        old_delta = nat_orig - syn
        new_delta = nat_inj - syn
        artifact = nat_orig - nat_inj
        print(f"{p:<11} {nat_orig:>7.1f}%  {nat_inj:>7.1f}%  {syn:>7.1f}%  "
              f"{old_delta:>+6.1f}pp  {new_delta:>+6.1f}pp  {artifact:>+6.1f}pp")

    print()
    print("Interpretation:")
    print("  Old D     = uncorrected Delta_synth = Acc(nat-orig) - Acc(syn-injected)")
    print("  True D    = matched Delta_synth     = Acc(nat-inj)  - Acc(syn-injected)")
    print("  Artifact  = injection effect        = Acc(nat-orig) - Acc(nat-inj)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
