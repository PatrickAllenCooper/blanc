"""
End-to-end pipeline dry run using MockModelInterface.

Exercises the complete evaluation pipeline -- prompt rendering, response
caching, cascading decoder, and metric aggregation -- without incurring API
costs.  Runs against:

  - 5 synthetic Level 2 (rule abduction) instances built directly from the
    avian-biology defeasible theory.
  - 10 Level 3 (defeater abduction) instances loaded from instances/level3_instances.json.

Expected output: no unhandled exceptions; summary statistics printed to stdout.

Author: Anonymous Authors
Date: 2026-02-18
"""

import json
import sys
from pathlib import Path

# Allow importing from src/ and experiments/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance
from model_interface import MockModelInterface
from evaluation_pipeline import EvaluationPipeline


# ---------------------------------------------------------------------------
# Instance factories
# ---------------------------------------------------------------------------

def _make_level2_instances() -> list[AbductiveInstance]:
    """Build five minimal Level 2 (rule abduction) instances."""
    base_facts = ["bird(tweety)", "bird(donald)", "bird(opus)", "penguin(opus)"]

    r_flies   = Rule(head="flies(X)",        body=("bird(X)",),    rule_type=RuleType.DEFEASIBLE, label="r_flies")
    r_feathers= Rule(head="has_feathers(X)", body=("bird(X)",),    rule_type=RuleType.DEFEASIBLE, label="r_feathers")
    r_warm    = Rule(head="warm_blooded(X)", body=("bird(X)",),    rule_type=RuleType.DEFEASIBLE, label="r_warm")
    r_lays    = Rule(head="lays_eggs(X)",    body=("bird(X)",),    rule_type=RuleType.DEFEASIBLE, label="r_lays")
    r_sings   = Rule(head="sings(X)",        body=("bird(X)",),    rule_type=RuleType.DEFEASIBLE, label="r_sings")
    d_penguin = Rule(head="~flies(X)",       body=("penguin(X)",), rule_type=RuleType.DEFEATER,   label="d_penguin")

    full_theory = Theory(
        facts=base_facts,
        rules=[r_flies, r_feathers, r_warm, r_lays, r_sings, d_penguin],
        superiority=[("d_penguin", "r_flies")],
    )

    # For each ablated rule, build an instance
    targets_and_rules = [
        ("flies(tweety)",        r_flies,    "r_flies"),
        ("has_feathers(tweety)", r_feathers, "r_feathers"),
        ("warm_blooded(tweety)", r_warm,     "r_warm"),
        ("lays_eggs(donald)",    r_lays,     "r_lays"),
        ("sings(donald)",        r_sings,    "r_sings"),
    ]

    distractor_candidates = [
        "r_flies: bird(X) => flies(X)",
        "r_feathers: bird(X) => has_feathers(X)",
        "r_warm: bird(X) => warm_blooded(X)",
        "r_lays: bird(X) => lays_eggs(X)",
        "r_sings: bird(X) => sings(X)",
        "r_wrong: animal(X) => flies(X)",
    ]

    instances = []
    for i, (target, gold_rule, gold_label) in enumerate(targets_and_rules):
        # Ablate the gold rule from the theory
        ablated_rules = [r for r in full_theory.rules if r.label != gold_rule.label]
        D_minus = Theory(
            facts=full_theory.facts,
            rules=ablated_rules,
            superiority=full_theory.superiority,
        )

        gold_str = f"{gold_label}: bird(X) => {gold_rule.head}"
        candidates = [gold_str] + [c for c in distractor_candidates if c != gold_str][:5]

        inst = AbductiveInstance(
            D_minus=D_minus,
            target=target,
            candidates=candidates,
            gold=[gold_str],
            level=2,
            metadata={"ablated": gold_label, "domain": "biology"},
        )
        inst.id = f"dry-bio-l2-{i+1:03d}"
        instances.append(inst)

    return instances


def _make_level3_instances(path: Path, limit: int = 10) -> list[AbductiveInstance]:
    """
    Load Level 3 instances from the JSON file and convert each to
    AbductiveInstance.  The Theory is reconstructed from the stored
    theory_facts / theory_rules fields using a simple text parser.
    """
    if not path.exists():
        print(f"Warning: {path} not found -- skipping Level 3 instances.")
        return []

    with open(path) as f:
        data = json.load(f)

    instances = []
    for item in data["instances"][:limit]:
        D_minus = _reconstruct_theory(item)

        inst = AbductiveInstance(
            D_minus=D_minus,
            target=item["anomaly"],
            candidates=item["candidates"],
            gold=[item["gold"]],
            level=3,
            metadata={
                "domain":          item.get("domain", ""),
                "nov":             item.get("nov", 0.0),
                "d_rev":           item.get("d_rev", 1),
                "conservative":    item.get("conservative", True),
                "defeater_type":   item.get("defeater_type", ""),
                "description":     item.get("description", ""),
            },
        )
        inst.id = f"dry-l3-{item['name']}"
        instances.append(inst)

    return instances


def _reconstruct_theory(item: dict) -> Theory:
    """
    Reconstruct a Theory from the 'theory_facts' and 'theory_rules' lists
    stored in the Level 3 JSON.

    Rule strings are in the format:
        label: body1(X), body2(X) => head(X)      (strict)
        label: body1(X), body2(X) => head(X)      (defeasible -- we default to DEFEASIBLE)
        label: body1(X) ~> ~head(X)               (defeater)

    Because the JSON stores the human-readable variant, we do a best-effort
    parse rather than a full grammar.
    """
    facts = list(item.get("theory_facts", []))
    rules: list[Rule] = []

    for rule_str in item.get("theory_rules", []):
        # Split label from body+head
        if ":" in rule_str:
            label, rest = rule_str.split(":", 1)
            label = label.strip()
            rest = rest.strip()
        else:
            label = None
            rest = rule_str.strip()

        if "~>" in rest:
            # Defeater: "body(X) ~> ~head(X)"
            body_part, head_part = rest.split("~>", 1)
            rule_type = RuleType.DEFEATER
        elif "=>" in rest:
            body_part, head_part = rest.split("=>", 1)
            rule_type = RuleType.DEFEASIBLE
        elif ":-" in rest:
            body_part, head_part = rest.split(":-", 1)
            rule_type = RuleType.STRICT
        else:
            # Unrecognised format -- store as strict fact-rule
            rules.append(Rule(head=rest.strip(), body=(), rule_type=RuleType.STRICT, label=label))
            continue

        body_atoms = tuple(b.strip() for b in body_part.split(",") if b.strip())
        head_atom  = head_part.strip()
        rules.append(Rule(head=head_atom, body=body_atoms, rule_type=rule_type, label=label))

    return Theory(facts=facts, rules=rules, superiority=[])


# ---------------------------------------------------------------------------
# Mock response generation
# ---------------------------------------------------------------------------

def _make_mock_responses(instances: list[AbductiveInstance]) -> list[str]:
    """
    Return one mock response string per instance (in all modality x strategy
    combinations).  We return the gold answer for ~50% of instances so that
    the accuracy summary shows a non-trivial spread.
    """
    responses = []
    for i, inst in enumerate(instances):
        # Alternate correct / incorrect to give a realistic mix
        if i % 2 == 0:
            responses.append(inst.gold[0])
        else:
            # Return a plausible distractor (first non-gold candidate)
            distractor = next(
                (c for c in inst.candidates if c not in inst.gold),
                inst.candidates[0],
            )
            responses.append(distractor)
    return responses


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 70)
    print("PIPELINE DRY RUN -- MockModelInterface")
    print("=" * 70)

    # Build instance sets
    l2_instances = _make_level2_instances()
    l3_instances = _make_level3_instances(
        ROOT / "instances" / "level3_instances.json", limit=10
    )
    all_instances = l2_instances + l3_instances

    print(f"Level 2 instances: {len(l2_instances)}")
    print(f"Level 3 instances: {len(l3_instances)}")
    print(f"Total:             {len(all_instances)}")
    print()

    # Configure mock model: one response per (instance x modality x strategy)
    modalities = ["M4"]
    strategies = ["direct"]
    n_responses_needed = len(all_instances) * len(modalities) * len(strategies)

    # We cycle through gold/distractor responses enough times
    base_responses = _make_mock_responses(all_instances)
    # Repeat for each (modality x strategy) combination
    mock_responses = base_responses * (len(modalities) * len(strategies))
    mock_responses = mock_responses[:n_responses_needed]  # Trim to exact count

    mock = MockModelInterface("mock-gpt4o")
    mock.set_responses(mock_responses)

    # Disable caching for the dry run (fresh tmp directory)
    cache_dir = str(ROOT / "experiments" / "cache" / "dry_run_tmp")
    results_dir = str(ROOT / "experiments" / "results" / "dry_run")

    pipeline = EvaluationPipeline(
        instances=all_instances,
        models={"mock-gpt4o": mock},
        modalities=modalities,
        strategies=strategies,
        cache_dir=cache_dir,
        results_dir=results_dir,
    )

    # Run
    results = pipeline.run()

    # Report
    print()
    print("=" * 70)
    print("DRY RUN RESULTS")
    print("=" * 70)
    summary = results.summary
    for k, v in summary.items():
        if isinstance(v, float):
            print(f"  {k:<40} {v:.4f}")
        else:
            print(f"  {k:<40} {v}")

    # Per-level breakdown
    print()
    print("Per-Level Breakdown:")
    level_counts = {2: {"total": 0, "correct": 0}, 3: {"total": 0, "correct": 0}}
    for ev in results.evaluations:
        iid = ev.instance_id
        lvl = 3 if iid.startswith("dry-l3") else 2
        level_counts[lvl]["total"] += 1
        if ev.metrics.correct:
            level_counts[lvl]["correct"] += 1

    for lvl, counts in level_counts.items():
        acc = counts["correct"] / counts["total"] if counts["total"] else 0.0
        print(f"  Level {lvl}: {counts['correct']}/{counts['total']} correct ({acc:.1%})")

    # Confirm all pipeline components exercised
    decoder_stages = set(ev.metrics.decoder_stage for ev in results.evaluations)
    print()
    print(f"Decoder stages reached: {sorted(decoder_stages)}")
    print()
    print("Dry run complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
