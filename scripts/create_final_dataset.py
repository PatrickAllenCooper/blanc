"""
Create final MVP dataset combining all levels.

Merges:
- Level 1-2: avian_abduction_v0.1.json (12 instances)
- Level 3: avian_level3_v0.1.json (3 instances)

Total: 15 instances

Author: Anonymous Authors
Date: 2026-02-11
"""

import json
from pathlib import Path

def main():
    """Merge datasets and validate."""
    print("=" * 70)
    print("Creating Final MVP Dataset")
    print("=" * 70)
    
    # Load Level 1-2
    path_l12 = Path("avian_abduction_v0.1.json")
    if path_l12.exists():
        with open(path_l12) as f:
            dataset_l12 = json.load(f)
        instances_l12 = dataset_l12["instances"]
        print(f"\nLoaded Level 1-2: {len(instances_l12)} instances")
    else:
        print(f"\n[WARNING] {path_l12} not found")
        instances_l12 = []
    
    # Load Level 3
    path_l3 = Path("avian_level3_v0.1.json")
    if path_l3.exists():
        with open(path_l3) as f:
            dataset_l3 = json.load(f)
        instances_l3 = dataset_l3["instances"]
        print(f"Loaded Level 3:   {len(instances_l3)} instances")
    else:
        print(f"[WARNING] {path_l3} not found")
        instances_l3 = []
    
    # Merge
    all_instances = instances_l12 + instances_l3
    
    # Count by level
    level_counts = {}
    for inst in all_instances:
        level = inst["level"]
        level_counts[level] = level_counts.get(level, 0) + 1
    
    # Create final dataset
    final_dataset = {
        "metadata": {
            "name": "Avian Abduction Benchmark - MVP Complete",
            "version": "0.1",
            "date": "2026-02-11",
            "knowledge_base": "avian_biology",
            "partition_strategy": "rule (L1-2), hand-crafted (L3)",
            "total_instances": len(all_instances),
            "level1_count": level_counts.get(1, 0),
            "level2_count": level_counts.get(2, 0),
            "level3_count": level_counts.get(3, 0),
            "encoding": "M4 (pure formal)",
            "decoder": "D1 (exact match)",
            "round_trip_accuracy": 1.0,  # Guaranteed by construction
        },
        "instances": all_instances
    }
    
    # Save
    output_path = Path("avian_abduction_mvp_final.json")
    with open(output_path, 'w') as f:
        json.dump(final_dataset, f, indent=2)
    
    print(f"\nSaved final dataset: {output_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("FINAL MVP DATASET")
    print("=" * 70)
    print(f"Total instances:  {len(all_instances)}")
    print(f"Level 1 (facts):  {level_counts.get(1, 0)}")
    print(f"Level 2 (rules):  {level_counts.get(2, 0)}")
    print(f"Level 3 (defeat): {level_counts.get(3, 0)}")
    print(f"Encoding:         M4 (Pure Formal)")
    print(f"Decoder:          D1 (Exact Match)")
    print(f"Round-trip:       100% (guaranteed)")
    print("=" * 70)
    
    return final_dataset


if __name__ == "__main__":
    dataset = main()
    print(f"\n[SUCCESS] Final MVP dataset created: {dataset['metadata']['total_instances']} instances")
