"""
Partition Sensitivity Analysis -- paper Section 4.3.5.

Tests whether different KB partitioning strategies produce statistically
distinguishable difficulty distributions.

Current data uses a single partition strategy (rule ablation + syntactic
distractors).  This analysis therefore stratifies by theory size quartile
as a proxy for partition complexity and tests whether the difficulty
distribution varies across strata.  The full multi-family comparison
(P1-P6 from Section 4.3.5) will be reported once per-family generation
is run at production scale on CURC.

Statistical tests used:
  - Mann-Whitney U (two-sample, non-parametric)
  - Kruskal-Wallis H (k-sample extension)
  - Bonferroni correction for multiple comparisons

Author: Patrick Cooper
Date: 2026-02-18
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Load and group
# ---------------------------------------------------------------------------

def load_grouped_instances(instance_files: list) -> dict[str, list[dict]]:
    """
    Load Level 2 instances and group them by theory-size quartile.

    Returns dict with keys 'Q1', 'Q2', 'Q3', 'Q4'.
    """
    instances = []
    for fp in instance_files:
        fp = Path(fp)
        if not fp.exists():
            continue
        with open(fp) as f:
            data = json.load(f)
        for inst in data.get("instances", []):
            if inst.get("level", 2) == 2:
                instances.append(inst)

    if not instances:
        return {}

    sizes = sorted(inst.get("theory_size", 0) for inst in instances)
    n = len(sizes)
    q1 = sizes[n // 4]
    q2 = sizes[n // 2]
    q3 = sizes[3 * n // 4]

    groups: dict = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for inst in instances:
        sz = inst.get("theory_size", 0)
        if sz <= q1:
            groups["Q1"].append(inst)
        elif sz <= q2:
            groups["Q2"].append(inst)
        elif sz <= q3:
            groups["Q3"].append(inst)
        else:
            groups["Q4"].append(inst)

    return groups


def _extract_metric(inst: dict, metric: str) -> float:
    """Extract a numerical metric from an instance dict."""
    if metric == "n_candidates":
        return inst.get("num_candidates") or len(inst.get("candidates", []))
    if metric == "n_gold":
        g = inst.get("gold", [])
        return inst.get("num_gold") or (len(g) if isinstance(g, list) else 1)
    if metric == "theory_size":
        return inst.get("theory_size", 0)
    return 0.0


# ---------------------------------------------------------------------------
# Statistical tests (pure Python, no scipy dependency)
# ---------------------------------------------------------------------------

def mann_whitney_u(x: list, y: list) -> tuple[float, float]:
    """
    Compute two-sided Mann-Whitney U statistic and approximate p-value.

    Uses normal approximation (valid for n1, n2 >= 10).
    Returns (U, p_value).
    """
    import math

    n1, n2 = len(x), len(y)
    if n1 == 0 or n2 == 0:
        return float("nan"), 1.0

    # Rank all values together
    all_vals = sorted((v, 0) for v in x) + sorted((v, 1) for v in y)
    all_vals_sorted = sorted(all_vals, key=lambda t: t[0])

    ranks = [0.0] * (n1 + n2)
    i = 0
    while i < len(all_vals_sorted):
        j = i
        # Find ties
        while j < len(all_vals_sorted) and all_vals_sorted[j][0] == all_vals_sorted[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2  # 1-indexed average
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Sum of ranks for group x (group 0)
    rank_x_sum = sum(ranks[k] for k in range(len(all_vals_sorted)) if all_vals_sorted[k][1] == 0)
    U1 = rank_x_sum - n1 * (n1 + 1) / 2
    U2 = n1 * n2 - U1
    U = min(U1, U2)

    # Normal approximation
    mu_U = n1 * n2 / 2
    sigma_U = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (U - mu_U) / sigma_U if sigma_U > 0 else 0.0

    # Two-tailed p-value using erf approximation
    p = 2 * (1 - _normal_cdf(abs(z)))
    return U, p


def kruskal_wallis_h(groups: list[list]) -> tuple[float, float]:
    """
    Kruskal-Wallis H test for k groups.  Returns (H, p_value).
    Chi-squared approximation with k-1 degrees of freedom.
    """
    import math

    k = len(groups)
    all_vals = []
    group_ids = []
    for gid, g in enumerate(groups):
        for v in g:
            all_vals.append(v)
            group_ids.append(gid)

    n = len(all_vals)
    if n == 0:
        return float("nan"), 1.0

    sorted_indices = sorted(range(n), key=lambda i: all_vals[i])
    ranks = [0.0] * n
    i = 0
    while i < len(sorted_indices):
        j = i
        val = all_vals[sorted_indices[i]]
        while j < n and all_vals[sorted_indices[j]] == val:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k_idx in range(i, j):
            ranks[sorted_indices[k_idx]] = avg_rank
        i = j

    group_rank_sums = defaultdict(float)
    group_sizes = defaultdict(int)
    for idx, gid in enumerate(group_ids):
        group_rank_sums[gid] += ranks[idx]
        group_sizes[gid] += 1

    H = 12 / (n * (n + 1)) * sum(
        group_rank_sums[gid] ** 2 / group_sizes[gid]
        for gid in range(len(groups))
    ) - 3 * (n + 1)

    df = len(groups) - 1
    p = 1 - _chi2_cdf(H, df)
    return H, p


def _normal_cdf(z: float) -> float:
    """Standard normal CDF using erf."""
    import math
    return (1 + math.erf(z / math.sqrt(2))) / 2


def _chi2_cdf(x: float, df: int) -> float:
    """Approximate chi-squared CDF (df >= 1)."""
    import math
    # Use incomplete gamma function via series expansion
    if x <= 0:
        return 0.0
    k = df / 2
    try:
        return _regularized_gamma(k, x / 2)
    except Exception:
        return 0.0


def _regularized_gamma(a: float, x: float, max_iter: int = 200) -> float:
    """Regularized lower incomplete gamma function P(a, x) via series."""
    import math
    if x <= 0:
        return 0.0
    if x < a + 1:
        # Series representation
        term = 1.0 / a
        result = term
        for n in range(1, max_iter):
            term *= x / (a + n)
            result += term
            if abs(term) < 1e-12 * abs(result):
                break
        return result * math.exp(-x + a * math.log(x) - math.lgamma(a))
    else:
        # Continued fraction
        return 1 - _reg_gamma_cf(a, x)


def _reg_gamma_cf(a: float, x: float, max_iter: int = 200) -> float:
    """Upper regularized gamma via continued fraction (Lentz method)."""
    import math
    FPMIN = 1e-30
    b = x + 1 - a
    c = 1 / FPMIN
    d = 1 / b
    h = d
    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-10:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


# ---------------------------------------------------------------------------
# Main analysis
# ---------------------------------------------------------------------------

def analyze_partition_sensitivity(
    groups: dict[str, list[dict]],
    metric: str = "n_candidates",
    alpha: float = 0.05,
) -> dict:
    """
    Run Mann-Whitney pairwise tests and Kruskal-Wallis across quartile groups.

    Returns dict with test statistics and conclusions.
    """
    if not groups:
        return {"error": "No instances loaded."}

    group_vals = {
        name: [_extract_metric(inst, metric) for inst in insts]
        for name, insts in groups.items()
    }

    group_names = [n for n in ("Q1", "Q2", "Q3", "Q4") if n in group_vals]

    print(f"\nMetric: {metric}")
    print(f"{'Group':<6} {'n':>5} {'mean':>8} {'std':>8} {'min':>5} {'max':>5}")
    print("-" * 40)
    for name in group_names:
        vals = group_vals[name]
        if not vals:
            continue
        n = len(vals)
        mean = sum(vals) / n
        std = (sum((v - mean) ** 2 for v in vals) / n) ** 0.5
        print(f"{name:<6} {n:>5} {mean:>8.2f} {std:>8.2f} {min(vals):>5} {max(vals):>5}")

    # Kruskal-Wallis
    all_groups_vals = [group_vals[n] for n in group_names if group_vals[n]]
    H, p_kw = kruskal_wallis_h(all_groups_vals)
    print(f"\nKruskal-Wallis H={H:.3f}, p={p_kw:.4f} ({'significant' if p_kw < alpha else 'not significant'} at alpha={alpha})")

    # Pairwise Mann-Whitney (Bonferroni)
    pairs = [(g1, g2) for i, g1 in enumerate(group_names) for g2 in group_names[i+1:]]
    n_pairs = len(pairs)
    bonferroni = alpha / n_pairs if n_pairs > 0 else alpha

    pairwise: list = []
    for g1, g2 in pairs:
        U, p = mann_whitney_u(group_vals[g1], group_vals[g2])
        sig = p < bonferroni
        pairwise.append({"groups": (g1, g2), "U": U, "p": p, "significant": sig})
        print(f"  MW {g1} vs {g2}: U={U:.1f}, p={p:.4f}  {'*' if sig else ''}")

    any_sig = any(r["significant"] for r in pairwise)

    return {
        "metric": metric,
        "group_sizes": {n: len(group_vals[n]) for n in group_names},
        "kruskal_wallis": {"H": H, "p": p_kw, "significant": p_kw < alpha},
        "pairwise": pairwise,
        "conclusion": (
            f"Theory-size quartiles produce distinguishable {metric} distributions."
            if any_sig
            else f"No significant difference in {metric} across theory-size quartiles "
                 f"(partition strategy is robust)."
        ),
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Partition sensitivity analysis (Section 4.3.5)")
    parser.add_argument("--instances-dir", default=str(ROOT / "instances"))
    parser.add_argument("--save-dir", default=str(ROOT / "experiments" / "results"))
    args = parser.parse_args()

    instances_dir = Path(args.instances_dir)
    files = [
        instances_dir / "biology_dev_instances.json",
        instances_dir / "legal_dev_instances.json",
        instances_dir / "materials_dev_instances.json",
    ]

    print("=" * 70)
    print("Section 4.3.5: Partition Sensitivity Analysis")
    print("=" * 70)
    print()
    print("Note: Current instances use a single partition strategy (rule ablation")
    print("+ syntactic distractors).  Stratification is by theory-size quartile.")
    print("Multi-family analysis (P1-P6) will be added at production scale.")

    groups = load_grouped_instances([str(f) for f in files])
    if not groups:
        print("No instances found.")
        return 1

    total = sum(len(v) for v in groups.values())
    print(f"\nInstances loaded: {total}")
    for q, insts in groups.items():
        sizes = [inst.get("theory_size", 0) for inst in insts]
        mean_sz = sum(sizes) / len(sizes) if sizes else 0
        print(f"  {q}: n={len(insts)}, mean theory_size={mean_sz:.1f}")

    results: dict = {}
    for metric in ("n_candidates", "theory_size"):
        print()
        res = analyze_partition_sensitivity(groups, metric=metric)
        results[metric] = res

    print()
    print("Conclusions:")
    for metric, res in results.items():
        print(f"  [{metric}] {res.get('conclusion', '')}")

    Path(args.save_dir).mkdir(parents=True, exist_ok=True)
    out = Path(args.save_dir) / "partition_sensitivity.json"
    def _sanitize(obj):
        if isinstance(obj, float) and (obj != obj):  # NaN check
            return None
        return obj

    def _clean(d):
        if isinstance(d, dict):
            return {k: _clean(v) for k, v in d.items()}
        if isinstance(d, list):
            return [_clean(v) for v in d]
        return _sanitize(d)

    with open(out, "w") as f:
        json.dump(_clean(results), f, indent=2, default=str)
    print(f"\nResults saved to: {out}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
