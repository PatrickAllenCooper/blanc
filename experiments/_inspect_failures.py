"""Temporary diagnostic script: inspect L3 decoder failures for DeepSeek and Kimi CoT."""
import json, sys

def inspect(path, label, level=3, strategy=None, n=4):
    with open(path) as f:
        raw = json.load(f)
    data = raw["evaluations"] if isinstance(raw, dict) and "evaluations" in raw else raw
    records = [r for r in data if r.get("level") == level]
    if strategy:
        records = [r for r in records if r.get("strategy") == strategy]
    print(f"\n{'='*70}")
    print(f"{label}  |  level={level}  strategy={strategy or 'all'}  (n={len(records)} total, showing {n})")
    print('='*70)
    for r in records[:n]:
        raw = str(r.get("raw_response") or r.get("response") or "")
        decoded = r.get("decoded_hypothesis") or r.get("decoded") or ""
        print(f"  modality={r.get('modality')}  strategy={r.get('strategy')}  correct={r.get('is_correct')}  stage={r.get('decoder_stage')}  error={r.get('error_type')}")
        print(f"  raw (first 400): {repr(raw[:400])}")
        print(f"  decoded: {repr(str(decoded)[:200])}")
        print()

inspect("experiments/results/foundry_deepseek_20260225_161735/results_foundry-deepseek.json",
        "DeepSeek-R1  L3 all modalities", level=3)

inspect("experiments/results/foundry_kimi_20260225_161735/results_foundry-kimi.json",
        "Kimi-K2.5  L2 CoT", level=2, strategy="cot")

inspect("experiments/results/foundry_kimi_20260225_161735/results_foundry-kimi.json",
        "Kimi-K2.5  L2 direct (sanity check)", level=2, strategy="direct", n=2)
