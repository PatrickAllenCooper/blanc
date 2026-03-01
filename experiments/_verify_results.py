"""
Verification script: checks remaining truncations, Kimi output format,
Claude CoT L3, and L3 instance count consistency.
"""
import json, os, collections

CANONICAL = {
    "gpt":      "experiments/results/foundry_gpt52_20260225_161735/results_foundry-gpt.json",
    "claude":   "experiments/results/foundry_claude_20260225_161735/results_foundry-claude.json",
    "deepseek": "experiments/results/foundry_deepseek_20260227_070407/results_foundry-deepseek.json",
    "kimi":     "experiments/results/foundry_kimi_20260227_070407/results_foundry-kimi.json",
}

NEW_CACHE = {
    "deepseek": "experiments/cache/foundry_deepseek",
    "kimi":     "experiments/cache/foundry_kimi",
}

def load(path):
    raw = json.load(open(path))
    return raw["evaluations"] if isinstance(raw, dict) and "evaluations" in raw else raw


# ── V1: Remaining truncations in new DeepSeek/Kimi caches ─────────────────
print("=" * 70)
print("V1: Remaining truncations in cache (finish_reason=length, text='')")
print("=" * 70)
for name, cdir in NEW_CACHE.items():
    total = trunc = still_empty = 0
    for f in os.listdir(cdir):
        d = json.load(open(os.path.join(cdir, f)))
        r = d.get("response", {})
        total += 1
        fr = (r.get("metadata") or {}).get("finish_reason", "")
        txt = r.get("text", "")
        if fr == "length":
            trunc += 1
        if txt == "":
            still_empty += 1
    print(f"  {name}: total={total}  finish_reason=length: {trunc} ({trunc/total*100:.1f}%)  empty_text: {still_empty} ({still_empty/total*100:.1f}%)")
print()


# ── V2: Kimi structural output format ─────────────────────────────────────
print("=" * 70)
print("V2: Kimi FAILED responses -- what does the raw output look like?")
print("=" * 70)
kimi_evals = load(CANONICAL["kimi"])
kimi_failed = [e for e in kimi_evals
               if e.get("metrics", {}).get("decoder_stage") == "FAILED"
               and e.get("raw_response", "").strip() != ""]
print(f"  FAILED with non-empty text: {len(kimi_failed)} of {len(kimi_evals)}")
print()
for e in kimi_failed[:4]:
    raw = str(e.get("raw_response", ""))
    print(f"  modality={e.get('modality')} strategy={e.get('strategy')} level={e.get('level')}")
    print(f"  raw (first 300): {repr(raw[:300])}")
    print()


# ── V3: Claude CoT L3 -- why 0.8%? ────────────────────────────────────────
print("=" * 70)
print("V3: Claude CoT L3 -- verify CoT extraction")
print("=" * 70)
claude_evals = load(CANONICAL["claude"])
claude_l3_cot = [e for e in claude_evals if e.get("level") == 3 and e.get("strategy") == "cot"]
claude_l3_cot_correct = [e for e in claude_l3_cot if e.get("metrics", {}).get("correct")]
claude_l3_cot_failed  = [e for e in claude_l3_cot if e.get("metrics", {}).get("decoder_stage") == "FAILED"]
print(f"  Total L3 CoT: {len(claude_l3_cot)}")
print(f"  Correct: {len(claude_l3_cot_correct)} ({len(claude_l3_cot_correct)/len(claude_l3_cot)*100:.1f}%)")
print(f"  FAILED decoder: {len(claude_l3_cot_failed)} ({len(claude_l3_cot_failed)/len(claude_l3_cot)*100:.1f}%)")
print()
print("  Sample FAILED CoT L3 raw outputs:")
for e in claude_l3_cot_failed[:3]:
    raw = str(e.get("raw_response", ""))
    safe = raw[:400].encode("ascii", errors="replace").decode("ascii")
    print(f"    modality={e.get('modality')} | raw (first 400): {repr(safe)}")
    print()
print("  Sample correct CoT L3:")
for e in claude_l3_cot_correct[:2]:
    raw = str(e.get("raw_response", ""))
    safe = raw[:400].encode("ascii", errors="replace").decode("ascii")
    print(f"    modality={e.get('modality')} | raw (first 400): {repr(safe)}")
    print()


# ── V4: L3 instance count reconciliation ──────────────────────────────────
print("=" * 70)
print("V4: L3 instance count")
print("=" * 70)
for name, path in CANONICAL.items():
    evals = load(path)
    l3 = [e for e in evals if e.get("level") == 3]
    ids = set(e.get("instance_id") for e in l3)
    mods = set(e.get("modality") for e in l3)
    strats = set(e.get("strategy") for e in l3)
    print(f"  {name}: {len(l3)} L3 evals | {len(ids)} unique instance IDs | modalities={sorted(mods)} | strategies={sorted(strats)}")
    print(f"    Expected: {len(ids)} instances × {len(mods)} modalities × {len(strats)} strategies = {len(ids)*len(mods)*len(strats)}")
    if len(ids)*len(mods)*len(strats) != len(l3):
        print(f"    WARNING: actual {len(l3)} != expected {len(ids)*len(mods)*len(strats)}")
print()
