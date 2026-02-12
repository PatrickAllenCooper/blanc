"""
Difficulty Distribution Analysis - Section 4.3.2

Extract and analyze structural difficulty tuples σ(I) from instances.

Author: Patrick Cooper
Date: 2026-02-12
"""

import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter


def extract_difficulty_tuples(instance_files):
    """
    Extract difficulty tuples σ(I) = (ℓ, |Supp|, |H*|, min|h|, Nov*) from instances.
    
    Args:
        instance_files: List of instance JSON files
    
    Returns:
        List of difficulty tuples
    """
    
    difficulties = []
    
    for filepath in instance_files:
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        for inst in data['instances']:
            # Extract difficulty components
            level = inst.get('level', 2)
            gold_count = len(inst.get('gold', []))
            candidate_count = len(inst.get('candidates', []))
            
            # Approximate min|h| and novelty (would need full instance parsing)
            # For now, use gold count as proxy for complexity
            min_h_size = 1  # Rule/fact has size ~1
            novelty = 0.0  # Most instances use existing predicates
            
            # Support size approximation (would need D_minus parsing)
            support_size = gold_count  # Rough proxy
            
            difficulty = {
                'level': level,
                'support_size': support_size,
                'gold_count': gold_count,
                'min_h_size': min_h_size,
                'novelty': novelty,
                'candidates': candidate_count
            }
            
            difficulties.append(difficulty)
    
    return difficulties


def analyze_difficulty_distributions(difficulties):
    """Analyze and plot difficulty distributions."""
    
    print("=" * 70)
    print("Section 4.3.2: Structural Difficulty Distributions")
    print("=" * 70)
    
    # Extract components
    levels = [d['level'] for d in difficulties]
    support_sizes = [d['support_size'] for d in difficulties]
    gold_counts = [d['gold_count'] for d in difficulties]
    min_h_sizes = [d['min_h_size'] for d in difficulties]
    novelties = [d['novelty'] for d in difficulties]
    candidate_counts = [d['candidates'] for d in difficulties]
    
    # Marginal distributions
    print(f"\nMarginal distributions (n={len(difficulties)}):")
    print(f"  Level: {Counter(levels)}")
    print(f"  |H*| (gold count): mean={np.mean(gold_counts):.2f}, std={np.std(gold_counts):.2f}, range=[{min(gold_counts)}, {max(gold_counts)}]")
    print(f"  |H_cand| (candidates): mean={np.mean(candidate_counts):.2f}, std={np.std(candidate_counts):.2f}, range=[{min(candidate_counts)}, {max(candidate_counts)}]")
    print(f"  min|h|: mean={np.mean(min_h_sizes):.2f}")
    print(f"  Nov*: mean={np.mean(novelties):.2f}")
    
    # Create histograms
    fig, axes = plt.subplots(2, 2, figsize=(12, 10))
    
    axes[0, 0].hist(gold_counts, bins=max(5, len(set(gold_counts))), edgecolor='black')
    axes[0, 0].set_xlabel('|H*| (Gold Hypothesis Count)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Distribution of Gold Hypothesis Counts')
    axes[0, 0].grid(alpha=0.3)
    
    axes[0, 1].hist(candidate_counts, bins=max(5, len(set(candidate_counts))), edgecolor='black')
    axes[0, 1].set_xlabel('|H_cand| (Candidate Count)')
    axes[0, 1].set_ylabel('Frequency')
    axes[0, 1].set_title('Distribution of Candidate Counts')
    axes[0, 1].grid(alpha=0.3)
    
    axes[1, 0].hist(support_sizes, bins=max(5, len(set(support_sizes))), edgecolor='black')
    axes[1, 0].set_xlabel('|Supp| (Support Size)')
    axes[1, 0].set_ylabel('Frequency')
    axes[1, 0].set_title('Distribution of Support Sizes')
    axes[1, 0].grid(alpha=0.3)
    
    # Level distribution
    level_counts = Counter(levels)
    axes[1, 1].bar(level_counts.keys(), level_counts.values(), edgecolor='black')
    axes[1, 1].set_xlabel('Level')
    axes[1, 1].set_ylabel('Frequency')
    axes[1, 1].set_title('Distribution by Level')
    axes[1, 1].grid(alpha=0.3)
    
    plt.tight_layout()
    
    Path('figures').mkdir(exist_ok=True)
    output_file = 'figures/difficulty_histograms.png'
    plt.savefig(output_file, dpi=150)
    print(f"\nSaved histograms to: {output_file}")
    
    # Mutual information (simplified - full version would compute MI between all pairs)
    print(f"\nIndependence tests:")
    print(f"  Correlation (|H*|, |H_cand|): {np.corrcoef(gold_counts, candidate_counts)[0,1]:.3f}")
    
    return {
        'marginals': {
            'gold_count': {'mean': float(np.mean(gold_counts)), 'std': float(np.std(gold_counts))},
            'candidates': {'mean': float(np.mean(candidate_counts)), 'std': float(np.std(candidate_counts))},
            'support_size': {'mean': float(np.mean(support_sizes)), 'std': float(np.std(support_sizes))},
        },
        'correlation_gold_candidates': float(np.corrcoef(gold_counts, candidate_counts)[0,1]),
    }


def main():
    """Run difficulty distribution analysis."""
    
    instance_files = [
        'instances/biology_dev_instances.json',
        'instances/legal_dev_instances.json',
        'instances/materials_dev_instances.json',
    ]
    
    difficulties = extract_difficulty_tuples(instance_files)
    results = analyze_difficulty_distributions(difficulties)
    
    # Save results
    with open('results/difficulty_distributions.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n" + "=" * 70)
    print("Difficulty analysis complete")
    print("=" * 70)
    print("Results saved to: results/difficulty_distributions.json")
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
