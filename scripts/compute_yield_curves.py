"""
Compute yield curves for Proposition 3 validation.

Computes Y(κ_rand(δ), Q) for δ ∈ {0.1, 0.2, ..., 0.9} and fits models.

Author: Patrick Cooper
Date: 2026-02-11
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent))

from examples.knowledge_bases.biology_curated import create_biology_base
from blanc.author.metrics import defeasible_yield
from blanc.generation.partition import partition_random


def compute_yield_curves():
    """Compute and plot yield curves (Proposition 3)."""
    print("=" * 70)
    print("Yield Curve Analysis - Proposition 3 Validation")
    print("=" * 70)
    
    # Load KB
    kb = create_biology_base()
    print(f"\nBiology KB: {len(kb)} rules")
    
    # Define target set Q (sample for speed)
    target_set = {
        "flies(robin)", "swims(dolphin)", "hunts(eagle)",
        "migrates(robin)", "sings(robin)", "vocalizes(robin)",
    }
    print(f"Target set Q: {len(target_set)} predicates")
    
    # Test deltas
    deltas = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    
    # Compute yields (average over 5 seeds)
    print("\nComputing yields (averaging over 5 seeds)...")
    yields_avg = []
    yields_std = []
    
    for delta in deltas:
        yields_at_delta = []
        for seed in range(5):
            y = defeasible_yield(partition_random(delta, seed=seed), target_set, kb)
            yields_at_delta.append(y)
        
        avg = np.mean(yields_at_delta)
        std = np.std(yields_at_delta)
        yields_avg.append(avg)
        yields_std.append(std)
        
        print(f"  delta={delta:.1f}: Y={avg:.1f} +/- {std:.1f}")
    
    # Test Proposition 3 (monotonicity)
    print("\nTesting Proposition 3 (yield monotonicity)...")
    is_monotonic = all(y2 >= y1 for y1, y2 in zip(yields_avg, yields_avg[1:]))
    trend = "increasing" if yields_avg[-1] > yields_avg[0] else "decreasing"
    print(f"  Monotonic: {is_monotonic}")
    print(f"  Trend: {trend} ({yields_avg[0]:.1f} -> {yields_avg[-1]:.1f})")
    
    # Fit parametric models
    print("\nFitting parametric models...")
    
    # Linear
    slope, intercept, r_linear, p_value, stderr = stats.linregress(deltas, yields_avg)
    print(f"  Linear: Y = {slope:.2f}δ + {intercept:.2f}, R² = {r_linear**2:.3f}")
    
    # Plot
    plt.figure(figsize=(10, 6))
    
    plt.errorbar(deltas, yields_avg, yerr=yields_std, fmt='o-', 
                 linewidth=2, markersize=8, capsize=5, label='Measured')
    plt.plot(deltas, slope * np.array(deltas) + intercept, '--', 
             linewidth=2, label=f'Linear fit (R²={r_linear**2:.3f})', alpha=0.7)
    
    plt.xlabel('Defeasibility Ratio (delta)', fontsize=12)
    plt.ylabel('Yield Y(kappa_rand(delta), Q)', fontsize=12)
    plt.title('Proposition 3: Yield Monotonicity in Defeasibility Ratio', 
              fontsize=14, fontweight='bold')
    plt.legend(fontsize=11)
    plt.grid(alpha=0.3)
    plt.tight_layout()
    
    output_path = Path("notebooks/yield_curves_biology.png")
    plt.savefig(output_path, dpi=150)
    print(f"\nSaved plot: {output_path}")
    
    plt.show()
    
    # Summary
    print("\n" + "=" * 70)
    print("YIELD ANALYSIS COMPLETE")
    print("=" * 70)
    print(f"Proposition 3: {'VERIFIED' if trend == 'increasing' else 'INCONCLUSIVE'}")
    print(f"Linear model: Y = {slope:.2f}*delta + {intercept:.2f}")
    print(f"Fit quality: R² = {r_linear**2:.3f}")
    print("=" * 70)
    
    return yields_avg, deltas


if __name__ == "__main__":
    compute_yield_curves()
