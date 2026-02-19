"""Quick diagnostic: inspect model response text for decoder failure analysis."""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent

files = {
    "gpt52":  ROOT / "experiments/results/pilot_foundry_gpt/results_foundry-gpt.json",
    "claude": ROOT / "experiments/results/pilot_foundry_claude/results_foundry-claude.json",
    "kimi":   ROOT / "experiments/results/pilot_foundry_kimi/results_foundry-kimi.json",
}

for model, fpath in files.items():
    if not fpath.exists():
        print(f"=== {model}: file not found ===\n")
        continue

    with open(fpath) as f:
        data = json.load(f)

    evals  = data.get("evaluations", [])
    summary = data.get("summary", {})

    failed        = [e for e in evals if e.get("metrics", {}).get("decoder_stage") == "FAILED"]
    correct       = [e for e in evals if e.get("metrics", {}).get("correct") is True]
    decoded_wrong = [e for e in evals if e.get("metrics", {}).get("decoder_stage") != "FAILED"
                     and not e.get("metrics", {}).get("correct")]

    print(f"=== {model} ===")
    print(f"  total={len(evals)}  correct={len(correct)}  "
          f"failed_decoder={len(failed)}  decoded_wrong={len(decoded_wrong)}")
    print(f"  summary accuracy={summary.get('accuracy', 'n/a')}")
    print(f"  summary decoder={summary.get('decoder_distribution', 'n/a')}")

    print("\n  -- FAILED decoder examples --")
    for e in failed[:3]:
        raw  = e.get("raw_response", "")
        gold = e.get("metrics", {}).get("gold", "")
        print(f"    instance : {e.get('instance_id')}  modality={e.get('modality')}  strategy={e.get('strategy')}")
        print(f"    raw_resp : {repr(raw[:300])}")
        print()

    print("  -- CORRECT examples --")
    for e in correct[:2]:
        raw  = e.get("raw_response", "")
        dec  = e.get("decoded_hypothesis", "")
        print(f"    instance : {e.get('instance_id')}  stage={e.get('metrics',{}).get('decoder_stage')}")
        print(f"    raw_resp : {repr(raw[:200])}")
        print(f"    decoded  : {repr(dec[:100])}")
        print()

    print("  -- DECODED but WRONG examples --")
    for e in decoded_wrong[:2]:
        raw  = e.get("raw_response", "")
        dec  = e.get("decoded_hypothesis", "")
        print(f"    instance : {e.get('instance_id')}  stage={e.get('metrics',{}).get('decoder_stage')}")
        print(f"    raw_resp : {repr(raw[:200])}")
        print(f"    decoded  : {repr(dec[:100])}")
        print()

    print()
