"""
Generate Level 3 instances (hand-crafted for MVP).

Level 3 requires working backwards from complete theory with defeaters.

Author: Anonymous Authors
Date: 2026-02-11
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from blanc.author.support import _remove_element
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
    create_avian_biology_full,
)


def check_conservativity(D_base, D_with_defeater, anomaly):
    """
    Check if adding defeater is conservative.
    
    Conservative: Preserves all expectations except the anomaly.
    """
    engine_base = DefeasibleEngine(D_base)
    engine_full = DefeasibleEngine(D_with_defeater)
    
    # Get expectations from base theory
    # For MVP: Check key expectations manually
    
    # Things that SHOULD remain derivable
    preserved_expectations = [
        "bird(tweety)",
        "flies(tweety)",  # Tweety still flies
        "bird(polly)",
        "flies(polly)",  # Polly still flies
    ]
    
    lost_expectations = []
    
    for exp in preserved_expectations:
        if exp == anomaly:
            continue  # Skip the anomaly itself
        
        was_derivable = engine_base.is_defeasibly_provable(exp)
        still_derivable = engine_full.is_defeasibly_provable(exp)
        
        if was_derivable and not still_derivable:
            lost_expectations.append(exp)
    
    return len(lost_expectations) == 0, lost_expectations


def create_penguin_instance():
    """
    Level 3: Penguin defeater.
    
    Anomaly: flies(opus)
    Theory predicts: flies(opus) (via r1: bird(X) => flies(X))
    Observation: ~flies(opus) (penguins don't fly)
    Resolution: d1: ~flies(X) :- penguin(X) with d1 > r1
    """
    # Create base theory (without defeater)
    base = create_avian_biology_base()
    full = create_avian_biology_full()
    
    # D^- is the base theory (without defeaters)
    D_minus = base
    
    # Add bird facts to D_minus
    D_minus.add_fact("bird(opus)")
    D_minus.add_fact("penguin(opus)")
    
    # Add r1 (bird => flies) as defeasible
    D_minus.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    ))
    
    # Verify anomaly: D^- ⊢∂ flies(opus)
    assert defeasible_provable(D_minus, "flies(opus)"), \
        "Base theory should predict flies(opus)"
    
    # The defeater (gold)
    defeater = Rule(
        head="~flies(X)",
        body=("penguin(X)",),
        rule_type=RuleType.DEFEATER,
        label="d1"
    )
    
    # D^full with defeater
    D_full = Theory()
    for fact in D_minus.facts:
        D_full.add_fact(fact)
    for rule in D_minus.rules:
        D_full.add_rule(rule)
    D_full.add_rule(defeater)
    D_full.add_superiority("d1", "r1")
    
    # Verify resolution: D^full ⊬∂ flies(opus)
    assert not defeasible_provable(D_full, "flies(opus)"), \
        "Defeater should block flies(opus)"
    
    # Check conservativity
    is_conservative, lost = check_conservativity(D_minus, D_full, "flies(opus)")
    
    print(f"[Level 3] Penguin defeater:")
    print(f"  Anomaly: flies(opus)")
    print(f"  Defeater: d1 (penguin => ~flies)")
    print(f"  Conservative: {is_conservative}")
    if not is_conservative:
        print(f"  Lost expectations: {lost}")
    
    # Create instance
    instance = AbductiveInstance(
        D_minus=D_minus,
        target="~flies(opus)",  # We want to derive NOT flies
        candidates=[defeater],
        gold=[defeater],
        level=3,
        metadata={
            "anomaly": "flies(opus)",
            "resolution": "d1",
            "conservative": is_conservative,
            "defeater_type": "weak",  # Blocks but doesn't assert opposite
        }
    )
    
    return instance


def create_injury_instance():
    """
    Level 3: Wing injury defeater.
    
    Anomaly: flies(chirpy)
    Observation: ~flies(chirpy) (injured birds don't fly)
    Resolution: d2: ~flies(X) :- wing_injury(X)
    """
    # Similar structure to penguin
    D_minus = Theory()
    D_minus.add_fact("bird(chirpy)")
    D_minus.add_fact("canary(chirpy)")
    D_minus.add_fact("wing_injury(chirpy)")
    D_minus.add_fact("small(chirpy)")
    
    D_minus.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    ))
    
    assert defeasible_provable(D_minus, "flies(chirpy)")
    
    defeater = Rule(
        head="~flies(X)",
        body=("wing_injury(X)",),
        rule_type=RuleType.DEFEATER,
        label="d2"
    )
    
    D_full = Theory()
    for fact in D_minus.facts:
        D_full.add_fact(fact)
    for rule in D_minus.rules:
        D_full.add_rule(rule)
    D_full.add_rule(defeater)
    D_full.add_superiority("d2", "r1")
    
    assert not defeasible_provable(D_full, "flies(chirpy)")
    
    is_conservative, lost = check_conservativity(D_minus, D_full, "flies(chirpy)")
    
    print(f"[Level 3] Wing injury defeater:")
    print(f"  Anomaly: flies(chirpy)")
    print(f"  Defeater: d2 (wing_injury => ~flies)")
    print(f"  Conservative: {is_conservative}")
    
    instance = AbductiveInstance(
        D_minus=D_minus,
        target="~flies(chirpy)",
        candidates=[defeater],
        gold=[defeater],
        level=3,
        metadata={
            "anomaly": "flies(chirpy)",
            "resolution": "d2",
            "conservative": is_conservative,
            "defeater_type": "weak",
        }
    )
    
    return instance


def create_duck_instance():
    """
    Level 3: Duck migration defeater.
    
    Anomaly: migrates(donald)
    Observation: ~migrates(donald) (ducks don't migrate)
    Resolution: d3: ~migrates(X) :- duck(X)
    """
    D_minus = Theory()
    D_minus.add_fact("bird(donald)")
    D_minus.add_fact("duck(donald)")
    D_minus.add_fact("large(donald)")
    
    # r1: bird => flies
    D_minus.add_rule(Rule(
        head="flies(X)",
        body=("bird(X)",),
        rule_type=RuleType.DEFEASIBLE,
        label="r1"
    ))
    
    # r2: bird, flies => migrates
    D_minus.add_rule(Rule(
        head="migrates(X)",
        body=("bird(X)", "flies(X)"),
        rule_type=RuleType.DEFEASIBLE,
        label="r2"
    ))
    
    assert defeasible_provable(D_minus, "migrates(donald)")
    
    defeater = Rule(
        head="~migrates(X)",
        body=("duck(X)",),
        rule_type=RuleType.DEFEATER,
        label="d3"
    )
    
    D_full = Theory()
    for fact in D_minus.facts:
        D_full.add_fact(fact)
    for rule in D_minus.rules:
        D_full.add_rule(rule)
    D_full.add_rule(defeater)
    D_full.add_superiority("d3", "r2")
    
    assert not defeasible_provable(D_full, "migrates(donald)")
    
    is_conservative, lost = check_conservativity(D_minus, D_full, "migrates(donald)")
    
    print(f"[Level 3] Duck migration defeater:")
    print(f"  Anomaly: migrates(donald)")
    print(f"  Defeater: d3 (duck => ~migrates)")
    print(f"  Conservative: {is_conservative}")
    
    instance = AbductiveInstance(
        D_minus=D_minus,
        target="~migrates(donald)",
        candidates=[defeater],
        gold=[defeater],
        level=3,
        metadata={
            "anomaly": "migrates(donald)",
            "resolution": "d3",
            "conservative": is_conservative,
            "defeater_type": "weak",
        }
    )
    
    return instance


def main():
    """Generate Level 3 instances."""
    print("=" * 70)
    print("Level 3 Instance Generation (Hand-Crafted)")
    print("=" * 70)
    
    instances = []
    
    # Generate instances
    print("\n1. Generating Level 3 instances...")
    
    instance1 = create_penguin_instance()
    instances.append(instance1)
    
    instance2 = create_injury_instance()
    instances.append(instance2)
    
    instance3 = create_duck_instance()
    instances.append(instance3)
    
    print(f"\n   Generated: {len(instances)} Level 3 instances")
    
    # Validate
    print("\n2. Validating instances...")
    valid_count = sum(1 for inst in instances if inst.is_valid())
    print(f"   Valid: {valid_count}/{len(instances)}")
    
    # Save
    print("\n3. Saving instances...")
    dataset = {
        "metadata": {
            "name": "Avian Abduction Level 3 v0.1",
            "total_instances": len(instances),
            "level3_count": len(instances),
            "valid_count": valid_count,
            "knowledge_base": "avian_biology",
        },
        "instances": [inst.to_dict() for inst in instances]
    }
    
    output_path = Path("avian_level3_v0.1.json")
    with open(output_path, 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"   Saved to: {output_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Level 3 instances: {len(instances)}")
    print(f"Valid:             {valid_count}/{len(instances)}")
    print("=" * 70)
    
    return instances


if __name__ == "__main__":
    instances = main()
    print(f"\n[SUCCESS] Generated {len(instances)} Level 3 instances")
