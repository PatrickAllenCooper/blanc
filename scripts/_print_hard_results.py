import json, glob

print("DeFAb-Hard-ROE (4 chain/multi-condition L3 seeds)")
print("=" * 60)
print(f"{'Model':<24} {'Direct':>8} {'CoT':>8} {'Combined':>10}")
print("-" * 54)

paper_order = ["foundry-nano","foundry-deepseek","foundry-gpt","foundry-claude","foundry-kimi"]
names = {
    "foundry-nano":     "GPT-5.4-nano",
    "foundry-deepseek": "DeepSeek-R1",
    "foundry-gpt":      "GPT-5.2-chat",
    "foundry-claude":   "Claude S. 4.6",
    "foundry-kimi":     "Kimi-K2.5",
}

best_per_model = {}  # provider -> best result file (lowest cache rate = most recent fresh run)
for f in sorted(glob.glob("data/rts_hard_results/rts_*.json")):
    with open(f) as fh:
        d = json.load(fh)
    prov = d.get("provider", "?")
    cache = d.get("summary", {}).get("cache_hit_rate", 1.0)
    strats = d.get("strategies", [])
    if "direct" in strats and "cot" in strats:  # combined run
        if prov not in best_per_model or cache < best_per_model[prov][1]:
            best_per_model[prov] = (d, cache)

for prov in paper_order:
    if prov not in best_per_model:
        if prov == "foundry-nano":
            # nano has separate direct-only run; check both
            pass
        print(f"  {names.get(prov, prov):<22} {'--':>8} {'--':>8} {'--':>10}")
        continue

    d = best_per_model[prov][0]
    evals = d.get("evaluations", [])

    direct_correct = sum(1 for e in evals if e.get("strategy") == "direct" and e.get("correct"))
    direct_total   = sum(1 for e in evals if e.get("strategy") == "direct")
    cot_correct    = sum(1 for e in evals if e.get("strategy") == "cot" and e.get("correct"))
    cot_total      = sum(1 for e in evals if e.get("strategy") == "cot")
    all_acc = d.get("summary", {}).get("accuracy")

    def pct(c, t): return f"{c/t*100:.0f}%" if t else "--"
    print(f"  {names.get(prov, prov):<22} "
          f"{pct(direct_correct, direct_total):>8} "
          f"{pct(cot_correct, cot_total):>8} "
          f"{f'{all_acc*100:.0f}%' if all_acc is not None else '--':>10}")

print()
print("Easy seeds (6 instances, M4 CoT) for comparison:")
print(f"  {'GPT-5.4-nano':<22} {'100%':>8}")
print(f"  {'DeepSeek-R1':<22} {'83%':>8}")
print(f"  {'GPT-5.2-chat':<22} {'100%':>8}")
print(f"  {'Claude S. 4.6':<22} {'0%':>8}")
print(f"  {'Kimi-K2.5':<22} {'33%':>8}")
