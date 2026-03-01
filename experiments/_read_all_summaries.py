"""Print all result summaries in experiments/results/."""
import json, os

base = "experiments/results"
dirs = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))

for d in dirs:
    summary_path = os.path.join(base, d, "summary.json")
    if not os.path.exists(summary_path):
        continue
    data = json.load(open(summary_path))
    lvl2 = data.get("by_level", {}).get("2", {})
    lvl3 = data.get("by_level", {}).get("3", {})
    models = data.get("by_model", {})
    model  = list(models.keys())[0] if models else d
    rr_map = data.get("rendering_robust_accuracy", {})
    rr_val = list(rr_map.values())[0]["robust_accuracy"] if rr_map else None
    cot    = data.get("cot_lift", {})
    cot_l2 = cot.get(model, {}).get("2", {})
    cot_l3 = cot.get(model, {}).get("3", {})
    graded = data.get("graded_score_summary", {})
    decoder = data.get("decoder_distribution", {})
    l3m    = data.get("level3_metrics", {})

    print(f"{'='*70}")
    print(f"DIR   : {d}")
    print(f"Model : {model}")
    print(f"L2    : {lvl2.get('accuracy',0)*100:.1f}%  ({lvl2.get('correct',0)}/{lvl2.get('total',0)})")
    print(f"L3    : {lvl3.get('accuracy',0)*100:.1f}%  ({lvl3.get('correct',0)}/{lvl3.get('total',0)})")
    if rr_val is not None:
        print(f"Rend-robust : {rr_val*100:.1f}%")
    if cot_l2:
        print(f"CoT lift L2 : {cot_l2.get('delta_cot',0)*100:+.1f}pp  (direct={cot_l2.get('acc_direct',0)*100:.1f}%  cot={cot_l2.get('acc_cot',0)*100:.1f}%)")
    if cot_l3:
        print(f"CoT lift L3 : {cot_l3.get('delta_cot',0)*100:+.1f}pp  (direct={cot_l3.get('acc_direct',0)*100:.1f}%  cot={cot_l3.get('acc_cot',0)*100:.1f}%)")
    if graded:
        print(f"L3 graded   : {graded.get('mean_graded_score',0):.4f}  (n={graded.get('n',0)})")
        dist = graded.get("score_distribution", {})
        print(f"  dist: 0.0={dist.get('0.0',0)}  0.25={dist.get('0.25',0)}  0.5={dist.get('0.5',0)}  0.75={dist.get('0.75',0)}  1.0={dist.get('1.0',0)}")
    if decoder:
        total_dec = sum(decoder.values())
        fail = decoder.get("FAILED", 0)
        print(f"Decoder: D1={decoder.get('D1',0)} D2={decoder.get('D2',0)} D3={decoder.get('D3',0)} FAILED={fail} ({fail/total_dec*100:.0f}%)")
    if l3m:
        err = l3m.get("error_distribution", {})
        print(f"L3 errors   : E1={err.get('E1_decoder_failure',0)}  E2={err.get('E2_derivation_failure',0)}  E4={err.get('E4_conservativity_violation',0)}  E5={err.get('E5_strength_shortfall',0)}  correct={err.get('correct',0)}")
    print()
