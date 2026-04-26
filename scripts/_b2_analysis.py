import json, glob, sys

# Examine every B2 tick: was the gate ever triggered?
print("B2 enforcement analysis: was the gate ever triggered?")
print("=" * 60)

for f in sorted(glob.glob('data/comprehensive_sc2_run_*/artifacts/quiz_*/*.jsonl') +
                glob.glob('data/roe_panel_*/artifacts/*/quiz/*.jsonl')):
    recs = [json.loads(l) for l in open(f) if l.strip()]
    b2 = [r for r in recs if r.get('mode') == 'B2']
    if not b2:
        continue
    reprompted = sum(1 for r in b2 if r.get('reprompts', 0) > 0)
    violations = sum(1 for r in b2 for v in r.get('verdicts', []) if not v.get('compliant', True))
    correct = sum(1 for r in b2 if r.get('gold', {}).get('correct_abstain', True))
    provider = f.replace('\\', '/').split('quiz_')[-1].split('/')[0]
    print(f"  {provider:<30} B2={len(b2)}  reprompts={reprompted}  verifier_violations={violations}  correct_abstain={correct}/{len(b2)}")
