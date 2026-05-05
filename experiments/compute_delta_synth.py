"""Compute Delta_synth for each model from synthetic L3 results."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NAT = {
    "foundry-claude":   16.4,
    "foundry-gpt":      47.5,
    "foundry-deepseek": 65.0,
    "foundry-kimi":     14.2,
}
LABEL = {
    "foundry-claude":   "Claude Sonnet 4.6",
    "foundry-gpt":      "GPT-5.2-chat",
    "foundry-deepseek": "DeepSeek-R1",
    "foundry-kimi":     "Kimi-K2.5",
}

results_dir = ROOT / "experiments" / "results" / "synthetic_l3_20260505"

print(f"{'Model':<22} {'Synth Acc':>10} {'Nat Acc':>10} {'Delta_synth':>12}  {'D1':>4} {'FAILED':>7} {'N':>4}")
print("-" * 85)

deltas = []
for prov, label in LABEL.items():
    path = results_dir / f"results_{prov}.json"
    if not path.exists():
        print(f"{label:<22} MISSING")
        continue
    with open(path) as f:
        d = json.load(f)
    s = d["summary"]
    syn = float(s["accuracy"]) * 100.0
    n   = int(s["total_evaluations"])
    dist = s["decoder_distribution"]
    correct = sum(v for k, v in dist.items() if k.startswith("D") and k[1:].isdigit())
    failed = dist.get("FAILED", 0)
    delta = NAT[prov] - syn
    deltas.append((label, syn, NAT[prov], delta, correct, failed, n))
    print(f"{label:<22} {syn:>9.2f}% {NAT[prov]:>9.1f}% {delta:>+11.2f}pp  {correct:>4} {failed:>7} {n:>4}")

print("-" * 85)
if deltas:
    mean_delta = sum(d[3] for d in deltas) / len(deltas)
    print(f"{'Mean Delta_synth':<22} {'':>10} {'':>10} {mean_delta:>+11.2f}pp")
    syn_best = max(d[1] for d in deltas)
    nat_best = max(d[2] for d in deltas)
    print()
    print(f"Best-model nat L3:    {nat_best:.1f}%")
    print(f"Best-model synth L3:  {syn_best:.1f}%")
    print(f"Best-model Delta:     {nat_best - syn_best:+.1f}pp")
