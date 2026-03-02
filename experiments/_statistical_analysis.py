"""
Comprehensive statistical analysis of DeFAb evaluation results.

Computes:
  1. Per-domain accuracy with Wilson 95% CIs
  2. Per-modality accuracy per model
  3. Model comparison significance (McNemar's test, instance-level)
  4. CoT vs direct paired significance (McNemar's test)
  5. Sample size adequacy assessment

Author: Patrick Cooper
"""
import json, math, sys, collections, itertools
from pathlib import Path
from scipy.stats import chi2_contingency
import numpy as np

CANONICAL = {
    "GPT-5.2":     "experiments/results/foundry_gpt52_20260228_174111/results_foundry-gpt.json",
    "Claude":      "experiments/results/foundry_claude_20260228_174111/results_foundry-claude.json",
    "DeepSeek-R1": "experiments/results/foundry_deepseek_20260228_174111/results_foundry-deepseek.json",
    "Kimi-K2.5":   "experiments/results/foundry_kimi_20260228_174111/results_foundry-kimi.json",
}


def load(path):
    raw = json.load(open(path))
    return raw["evaluations"] if isinstance(raw, dict) and "evaluations" in raw else raw


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0, 0.0)
    p = k / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = (z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)


def infer_domain(instance_id: str) -> str:
    """Extract domain from instance_id when domain field is None (L2 records)."""
    iid = (instance_id or "").lower()
    if "biology" in iid or "bio" in iid:
        return "biology"
    if "legal" in iid or "law" in iid or "lkif" in iid:
        return "legal"
    if "materials" in iid or "mat" in iid:
        return "materials"
    return "unknown"


def get_domain(e):
    d = e.get("domain")
    if d and d != "unknown":
        return d
    return infer_domain(e.get("instance_id", ""))


def mcnemar_test(results_a, results_b):
    """
    McNemar's test on paired binary outcomes.
    results_a, results_b: dicts of instance_key -> bool
    Returns (chi2, p_value, b, c) where b=A-correct/B-wrong, c=A-wrong/B-correct.
    """
    keys = set(results_a) & set(results_b)
    b = sum(1 for k in keys if results_a[k] and not results_b[k])
    c = sum(1 for k in keys if not results_a[k] and results_b[k])
    n = b + c
    if n == 0:
        return 0.0, 1.0, b, c
    # With continuity correction (Yates)
    chi2 = (abs(b - c) - 1) ** 2 / (b + c) if (b + c) > 0 else 0.0
    from scipy.stats import chi2 as chi2_dist
    p = 1 - chi2_dist.cdf(chi2, df=1)
    return chi2, p, b, c


# ── Load all data ──────────────────────────────────────────────────────────
all_evals = {label: load(path) for label, path in CANONICAL.items()}


# ── 1. Domain breakdown ────────────────────────────────────────────────────
print("=" * 80)
print("1. ACCURACY BY DOMAIN AND LEVEL  (instance-level, all modalities pooled)")
print("   Wilson 95% confidence intervals")
print("=" * 80)

DOMAINS = ["biology", "legal", "materials"]
LEVELS  = [2, 3]

for level in LEVELS:
    print(f"\nLevel {level}:")
    header = f"  {'Model':<14}" + "".join(f"  {d[:3].capitalize():>18}" for d in DOMAINS)
    print(header)
    print("  " + "-" * (len(header) - 2))
    for label, evals in all_evals.items():
        row = f"  {label:<14}"
        for dom in DOMAINS:
            subset = [e for e in evals
                      if e.get("level") == level and get_domain(e) == dom]
            k = sum(1 for e in subset if e.get("metrics", {}).get("correct"))
            n = len(subset)
            p, lo, hi = wilson_ci(k, n)
            row += f"  {p*100:4.0f}% [{lo*100:.0f}–{hi*100:.0f}%] n={n:4d}"
        print(row)

# ── 2. Per-modality breakdown ──────────────────────────────────────────────
print("\n\n" + "=" * 80)
print("2. ACCURACY BY MODALITY  (all levels pooled, direct + CoT)")
print("=" * 80)

MODALITIES = ["M1", "M2", "M3", "M4"]
header = f"  {'Model':<14}" + "".join(f"  {m:>14}" for m in MODALITIES)
print("\n" + header)
print("  " + "-" * (len(header) - 2))
for label, evals in all_evals.items():
    row = f"  {label:<14}"
    for mod in MODALITIES:
        subset = [e for e in evals if e.get("modality") == mod]
        k = sum(1 for e in subset if e.get("metrics", {}).get("correct"))
        n = len(subset)
        p, lo, hi = wilson_ci(k, n)
        row += f"  {p*100:4.0f}% [{lo*100:.0f}–{hi*100:.0f}%]"
    print(row)

# ── 3. Model comparison: McNemar's tests on L3 instances ──────────────────
print("\n\n" + "=" * 80)
print("3. MODEL COMPARISON: McNemar's tests on Level 3 (instance × modality pairs)")
print("   Null: no difference in error rates between models")
print("=" * 80)

def l3_results(evals, strategy=None):
    """Return dict of (instance_id, modality, strategy) -> bool for L3."""
    d = {}
    for e in evals:
        if e.get("level") != 3:
            continue
        if strategy and e.get("strategy") != strategy:
            continue
        key = (e.get("instance_id"), e.get("modality"), e.get("strategy"))
        d[key] = bool(e.get("metrics", {}).get("correct"))
    return d

model_names = list(all_evals.keys())
l3_res = {label: l3_results(evals) for label, evals in all_evals.items()}

print(f"\n  {'Comparison':<30}  {'chi2':>6}  {'p':>8}  {'A-only':>7}  {'B-only':>7}  {'sig':>5}")
print("  " + "-" * 72)
for a, b in itertools.combinations(model_names, 2):
    chi2, p, bc, cb = mcnemar_test(l3_res[a], l3_res[b])
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    print(f"  {a} vs {b:<18}  {chi2:6.2f}  {p:8.4f}  {bc:7d}  {cb:7d}  {sig:>5}")

# ── 4. CoT vs direct: McNemar's tests per model at L3 ─────────────────────
print("\n\n" + "=" * 80)
print("4. CoT vs DIRECT: McNemar's tests per model at Level 3")
print("   Positive A-only means direct-correct/CoT-wrong; B-only = CoT-correct/direct-wrong")
print("=" * 80)

print(f"\n  {'Model':<14}  {'chi2':>6}  {'p':>8}  {'dir-only':>9}  {'cot-only':>9}  {'sig':>5}  Effect")
print("  " + "-" * 75)
for label, evals in all_evals.items():
    l3_dir = {(e.get("instance_id"), e.get("modality")): bool(e.get("metrics",{}).get("correct"))
              for e in evals if e.get("level")==3 and e.get("strategy")=="direct"}
    l3_cot = {(e.get("instance_id"), e.get("modality")): bool(e.get("metrics",{}).get("correct"))
              for e in evals if e.get("level")==3 and e.get("strategy")=="cot"}
    chi2, p, b, c = mcnemar_test(l3_dir, l3_cot)
    sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else "ns"))
    direction = "CoT>" if c > b else ("Dir>" if b > c else "equal")
    print(f"  {label:<14}  {chi2:6.2f}  {p:8.4f}  {b:9d}  {c:9d}  {sig:>5}  {direction}")

# ── 5. Sample size adequacy ────────────────────────────────────────────────
print("\n\n" + "=" * 80)
print("5. SAMPLE SIZE ADEQUACY")
print("=" * 80)
lines = [
    "Level 2 (374 instances x 4 modalities x 2 strategies = 2,992 evaluations/model):",
    "  Unique instances: 374  [ADEQUATE for 95% CIs +/-5pp near 50% accuracy]",
    "  Per-domain: Biology 114, Legal 116, Materials 144",
    "  Wilson CI half-width at 80% accuracy: +/-4pp (bio), +/-4pp (leg), +/-3pp (mat)",
    "  McNemar model comparisons: 374 x 4 = 1,496 paired obs  [ADEQUATE]",
    "",
    "Level 3 (35 instances x 4 modalities x 2 strategies = 280 evaluations/model):",
    "  Unique instances: 35  [MARGINAL -- wide CIs, ~+/-15-17pp at 50% accuracy]",
    "  Per-domain: Biology 16, Legal 10, Materials 9",
    "  Wilson CI half-width at 50% accuracy: +/-25pp (bio), +/-31pp (leg), +/-33pp (mat)",
    "  Per-domain L3 comparisons have LOW POWER -- treat as descriptive only",
    "  McNemar model comparisons: 35 x 4 = 140 paired obs  [MARGINAL, ~15pp MDD at 80% power]",
    "",
    "RECOMMENDATIONS:",
    "  (a) Report per-domain L3 as descriptive only; wide CIs preclude inference",
    "  (b) Report aggregate L3 model comparisons with McNemar p-values",
    "  (c) Add Wilson 95% CIs to all accuracy figures in Tables 1-2",
    "  (d) Primary L3 claims must be over all 35 instances, not per-domain",
    "  (e) Expanding L3 set to 100+ instances enables proper domain-level inference",
]
for line in lines:
    print(line)
