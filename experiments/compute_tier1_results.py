"""Summarize Tier 1 L2 results across the four-model panel."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "results" / "tier1_l2_20260505"

LABEL = {
    "foundry-deepseek": "DeepSeek-R1",
    "foundry-gpt":      "GPT-5.2-chat",
    "foundry-claude":   "Claude Sonnet 4.6",
    "foundry-kimi":     "Kimi-K2.5",
}

# Tier 0 L2 numbers from paper Table 1 (direct + cot averaged)
TIER0_L2 = {
    "foundry-deepseek": (73.7 + 71.4) / 2,
    "foundry-gpt":      (78.5 + 47.5) / 2,
    "foundry-claude":   (79.3 + 52.3) / 2,
    "foundry-kimi":     (71.9 + 70.4) / 2,
}

print(f"{'Model':<22} {'Tier 1 L2':>10} {'Tier 0 L2':>10} {'Delta':>10}  {'D1+D3':>6} {'FAILED':>7} {'N':>4}")
print("-" * 80)
for prov, label in LABEL.items():
    p = RESULTS / f"results_{prov}.json"
    if not p.exists():
        print(f"{label:<22} MISSING")
        continue
    with open(p) as f:
        d = json.load(f)
    s = d["summary"]
    t1 = float(s["accuracy"]) * 100
    n = int(s["total_evaluations"])
    dist = s["decoder_distribution"]
    correct = sum(v for k, v in dist.items() if k.startswith("D") and k[1:].isdigit())
    failed = dist.get("FAILED", 0)
    delta = t1 - TIER0_L2[prov]
    print(f"{label:<22} {t1:>9.2f}% {TIER0_L2[prov]:>9.2f}% {delta:>+9.2f}pp  {correct:>6} {failed:>7} {n:>4}")
