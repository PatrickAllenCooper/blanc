"""
Statistical analysis of generated instances.

Implements Section 4.3 of paper: Dataset Statistics.

Author: Patrick Cooper
Date: 2026-02-12
"""

import sys
from pathlib import Path
import json
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))


def analyze_instances(instance_files):
    """
    Analyze generated instances for Section 4.3.
    
    Args:
        instance_files: List of JSON instance files
    
    Returns:
        Dictionary of statistics
    """
    
    print("=" * 70)
    print("Instance Dataset Analysis (Section 4.3)")
    print("=" * 70)
    
    all_instances = []
    by_domain = defaultdict(list)
    by_partition = defaultdict(list)
    by_level = defaultdict(list)
    
    # Load all instances
    for filepath in instance_files:
        if not Path(filepath).exists():
            print(f"[SKIP] {filepath} - not found")
            continue
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        domain = data['metadata']['domain']
        instances = data['instances']
        
        print(f"\nLoaded {filepath}:")
        print(f"  Domain: {domain}")
        print(f"  Instances: {len(instances)}")
        
        all_instances.extend(instances)
        
        for inst in instances:
            by_domain[domain].append(inst)
            by_level[inst.get('level', 2)].append(inst)
            # Get partition from metadata if available
            partition = inst.get('metadata', {}).get('partition', 'unknown')
            by_partition[partition].append(inst)
    
    # === SECTION 4.3.1: Volume and Balance ===
    print("\n" + "=" * 70)
    print("4.3.1 Volume and Balance")
    print("=" * 70)
    
    print(f"\nTotal instances: {len(all_instances)}")
    
    print(f"\nBy domain:")
    for domain, insts in sorted(by_domain.items()):
        print(f"  {domain}: {len(insts)}")
    
    print(f"\nBy level:")
    for level, insts in sorted(by_level.items()):
        print(f"  Level {level}: {len(insts)}")
    
    print(f"\nBy partition:")
    for partition, insts in sorted(by_partition.items()):
        if partition != 'unknown':
            print(f"  {partition}: {len(insts)}")
    
    # === SECTION 4.3.2: Structural Difficulty (Basic) ===
    print("\n" + "=" * 70)
    print("4.3.2 Structural Difficulty Distributions (Basic)")
    print("=" * 70)
    
    print(f"\nSample instance structure:")
    if all_instances:
        sample = all_instances[0]
        print(f"  Target: {sample.get('target', 'N/A')}")
        print(f"  Level: {sample.get('level', 'N/A')}")
        print(f"  Gold hypotheses: {len(sample.get('gold', []))}")
        print(f"  Candidates: {len(sample.get('candidates', []))}")
    
    # === Summary Statistics ===
    stats = {
        'total_instances': len(all_instances),
        'by_domain': {k: len(v) for k, v in by_domain.items()},
        'by_level': {k: len(v) for k, v in by_level.items()},
        'by_partition': {k: len(v) for k, v in by_partition.items()},
    }
    
    return stats


def main():
    """Analyze development instances."""
    
    instance_files = [
        'biology_dev_instances.json',
        'legal_dev_instances.json',
        'materials_dev_instances.json',
    ]
    
    stats = analyze_instances(instance_files)
    
    # Save statistics
    with open('instance_statistics.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print("\n" + "=" * 70)
    print("Analysis Complete")
    print("=" * 70)
    print(f"\nStatistics saved to: instance_statistics.json")
    print(f"\nReady for Week 4 (full statistical analysis)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
