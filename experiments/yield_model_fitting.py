"""
Yield Model Fitting - Section 4.3.4 Enhancement

Fit parametric models to yield curves and perform statistical tests.

Author: Patrick Cooper
Date: 2026-02-12
"""

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit
import matplotlib.pyplot as plt
from pathlib import Path


def linear_model(x, a, b):
    """Linear model: y = ax + b"""
    return a * x + b


def logistic_model(x, L, k, x0):
    """Logistic model: y = L / (1 + exp(-k(x - x0)))"""
    return L / (1 + np.exp(-k * (x - x0)))


def power_law_model(x, a, b):
    """Power law model: y = a * x^b"""
    return a * np.power(x, b)


def fit_yield_models(deltas, yields):
    """
    Fit parametric models to yield curve.
    
    Args:
        deltas: Array of defeasibility ratios
        yields: Array of corresponding yields
    
    Returns:
        Dictionary with fitted models and statistics
    """
    
    results = {}
    
    # Linear fit
    try:
        slope, intercept, r_linear, p_value, stderr = stats.linregress(deltas, yields)
        results['linear'] = {
            'slope': float(slope),
            'intercept': float(intercept),
            'r_squared': float(r_linear**2),
            'p_value': float(p_value),
            'model': f'Y = {slope:.2f}*delta + {intercept:.2f}'
        }
        print(f"Linear: Y = {slope:.2f}*delta + {intercept:.2f}, R^2 = {r_linear**2:.3f}")
    except Exception as e:
        print(f"Linear fit failed: {e}")
        results['linear'] = None
    
    # Logistic fit (if monotonic trend)
    try:
        # Initial guess for logistic parameters
        L_guess = max(yields)
        k_guess = 1.0
        x0_guess = np.mean(deltas)
        
        popt, _ = curve_fit(logistic_model, deltas, yields, 
                           p0=[L_guess, k_guess, x0_guess],
                           maxfev=5000)
        
        # Compute R^2
        y_pred = logistic_model(np.array(deltas), *popt)
        ss_res = np.sum((yields - y_pred)**2)
        ss_tot = np.sum((yields - np.mean(yields))**2)
        r2_logistic = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        results['logistic'] = {
            'L': float(popt[0]),
            'k': float(popt[1]),
            'x0': float(popt[2]),
            'r_squared': float(r2_logistic),
            'model': f'Logistic(L={popt[0]:.2f}, k={popt[1]:.2f}, x0={popt[2]:.2f})'
        }
        print(f"Logistic: L={popt[0]:.2f}, k={popt[1]:.2f}, x0={popt[2]:.2f}, R^2 = {r2_logistic:.3f}")
    except Exception as e:
        print(f"Logistic fit failed (may not be appropriate): {e}")
        results['logistic'] = None
    
    # Power law fit (if positive values)
    try:
        if all(y > 0 for y in yields) and all(x > 0 for x in deltas):
            popt, _ = curve_fit(power_law_model, deltas, yields,
                               p0=[1.0, 1.0], maxfev=5000)
            
            # Compute R^2
            y_pred = power_law_model(np.array(deltas), *popt)
            ss_res = np.sum((yields - y_pred)**2)
            ss_tot = np.sum((yields - np.mean(yields))**2)
            r2_power = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            results['power_law'] = {
                'a': float(popt[0]),
                'b': float(popt[1]),
                'r_squared': float(r2_power),
                'model': f'Y = {popt[0]:.2f} * delta^{popt[1]:.2f}'
            }
            print(f"Power law: Y = {popt[0]:.2f} * delta^{popt[1]:.2f}, R^2 = {r2_power:.3f}")
        else:
            results['power_law'] = None
    except Exception as e:
        print(f"Power law fit failed: {e}")
        results['power_law'] = None
    
    # Test for monotonicity
    is_monotonic = all(y2 >= y1 for y1, y2 in zip(yields[:-1], yields[1:]))
    monotonic_direction = "increasing" if yields[-1] > yields[0] else "decreasing"
    
    results['monotonicity'] = {
        'is_monotonic': is_monotonic,
        'direction': monotonic_direction,
        'start': float(yields[0]),
        'end': float(yields[-1])
    }
    
    print(f"\nMonotonicity: {is_monotonic} ({monotonic_direction})")
    
    return results


def analyze_yield_curves():
    """Analyze yield curves from Week 3 data."""
    
    print("=" * 70)
    print("Yield Model Fitting - Section 4.3.4")
    print("=" * 70)
    
    # Sample yield data from Week 3 results
    # (In production, would load from actual yield computation)
    
    print("\nBiology KB:")
    bio_deltas = [0.1, 0.3, 0.5, 0.7, 0.9]
    bio_yields = [3.7, 4.3, 5.0, 5.3, 3.3]
    bio_results = fit_yield_models(bio_deltas, bio_yields)
    
    print("\nLegal KB:")
    legal_deltas = [0.1, 0.3, 0.5, 0.7, 0.9]
    legal_yields = [8.0, 8.0, 8.3, 9.0, 9.0]
    legal_results = fit_yield_models(legal_deltas, legal_yields)
    
    print("\nMaterials KB:")
    mat_deltas = [0.1, 0.3, 0.5, 0.7, 0.9]
    mat_yields = [5.3, 5.0, 6.0, 5.0, 5.0]
    mat_results = fit_yield_models(mat_deltas, mat_yields)
    
    # Save results
    import json
    Path('results').mkdir(exist_ok=True)
    
    all_results = {
        'biology': bio_results,
        'legal': legal_results,
        'materials': mat_results
    }
    
    with open('results/yield_model_fitting.json', 'w') as f:
        json.dump(all_results, f, indent=2)
    
    print(f"\n{'=' * 70}")
    print("Yield model fitting complete")
    print("=" * 70)
    print("Results saved to: results/yield_model_fitting.json")
    
    return all_results


if __name__ == "__main__":
    analyze_yield_curves()
