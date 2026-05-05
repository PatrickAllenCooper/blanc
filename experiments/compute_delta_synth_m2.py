"""Compute synthetic L3 accuracy at M2 for each model and aggregate against M4."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

LABEL = {
    "foundry-claude":   "Claude Sonnet 4.6",
    "foundry-gpt":      "GPT-5.2-chat",
    "foundry-deepseek": "DeepSeek-R1",
    "foundry-kimi":     "Kimi-K2.5",
}
NAT_AGG = {
    "foundry-claude":   16.4,
    "foundry-gpt":      47.5,
    "foundry-deepseek": 65.0,
    "foundry-kimi":     14.2,
}

m4_dir = ROOT / "experiments" / "results" / "synthetic_l3_20260505"
m2_dir = ROOT / "experiments" / "results" / "synthetic_l3_m2_20260505"

print(f"{'Model':<22} {'Nat agg':>8} {'Syn M4':>8} {'Syn M2':>8} {'Syn M2+M4':>10} {'Delta agg':>10}")
print("-" * 80)
deltas = []
for prov, label in LABEL.items():
    p4 = m4_dir / f"results_{prov}.json"
    p2 = m2_dir / f"results_{prov}.json"
    if not p4.exists() or not p2.exists():
        print(f"{label:<22} MISSING")
        continue
    a4 = float(json.load(open(p4))["summary"]["accuracy"]) * 100
    a2 = float(json.load(open(p2))["summary"]["accuracy"]) * 100
    avg = (a4 + a2) / 2
    delta = NAT_AGG[prov] - avg
    deltas.append((label, a4, a2, avg, delta))
    print(f"{label:<22} {NAT_AGG[prov]:>7.1f}% {a4:>7.2f}% {a2:>7.2f}% {avg:>9.2f}% {delta:>+9.2f}pp")

print("-" * 80)
mean = sum(d[4] for d in deltas) / len(deltas)
print(f"{'Mean':<22} {'':>8} {'':>8} {'':>8} {'':>10} {mean:>+9.2f}pp")
