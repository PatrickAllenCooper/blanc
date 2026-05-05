"""
Build evaluation-ready Level 3 instances from the structurally-matched
synthetic theories at instances/synthetic/synthetic_instances.json.

Each input synthetic record contains a complete Theory (facts + rules,
including a single DEFEATER), but the defeater's target literal is rarely
derivable from the theory minus the defeater (D^-) because the synthetic
generator chose body constants independently of the facts.

This script repairs each synthetic theory so it admits a valid Level 3
instance. The repair selects an anomaly literal H by walking the defeasible
rules in the theory and finding the first one whose body is satisfiable
in D^- (the rule fires); then it constructs a fresh DEFEATER `~H :- G`
where G is any existing literal in the theory different from the body of
the firing rule. Anomaly = H, gold_defeater = the new defeater. The result
is a valid Level 3 instance (anomaly derivable in D^-, blocked when the
defeater is reinstated, conservativity preserved by construction).

The structural footprint (predicate vocabulary, fact / rule counts,
defeasible-rule counts, depth) is identical to the input synthetic
theory, so the contamination-control property of "no overlap with
pretraining vocabulary" is preserved.

Output is written to instances/synthetic/level3_instances.json in the
schema expected by experiments/run_evaluation.py (_load_level3_instances).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import generate_level3_instance
from blanc.reasoning.defeasible import defeasible_provable


def _format_rule(rule: Rule) -> str:
    label = rule.label or ""
    body = ", ".join(rule.body)
    if rule.rule_type == RuleType.STRICT:
        arrow = ":-"
    elif rule.rule_type == RuleType.DEFEASIBLE:
        arrow = "=>"
    elif rule.rule_type == RuleType.DEFEATER:
        arrow = "~>"
    else:
        arrow = "?"
    rest = f"{body} {arrow} {rule.head}" if body else f"{arrow} {rule.head}"
    return f"{label}: {rest}" if label else rest


def _reconstruct_theory(record: dict, drop_defeaters: bool = False) -> Theory:
    facts = list(record["theory"]["facts"])
    rules: list[Rule] = []
    for r in record["theory"]["rules"]:
        rt = RuleType(r["rule_type"].lower())
        if drop_defeaters and rt == RuleType.DEFEATER:
            continue
        rules.append(Rule(
            head=r["head"],
            body=tuple(r["body"]),
            rule_type=rt,
            label=r.get("label"),
        ))
    return Theory(facts=set(facts), rules=rules, superiority={})


def _find_firing_defeasible(theory: Theory) -> Rule | None:
    """Return the first DEFEASIBLE rule in `theory` whose head is derivable."""
    for r in theory.rules:
        if r.rule_type != RuleType.DEFEASIBLE:
            continue
        try:
            if defeasible_provable(theory, r.head):
                return r
        except Exception:
            continue
    return None


def _convert(record: dict) -> dict | None:
    base = _reconstruct_theory(record, drop_defeaters=True)
    firing = _find_firing_defeasible(base)
    if firing is None:
        defeasible_rules = [r for r in base.rules if r.rule_type == RuleType.DEFEASIBLE]
        if not defeasible_rules:
            return {"_error": "no defeasible rules at all", "name": record["id"]}
        first_def = defeasible_rules[0]
        for body_atom in first_def.body:
            base.facts.add(body_atom)
        firing = _find_firing_defeasible(base)
        if firing is None:
            return {"_error": "rule still does not fire after fact injection", "name": record["id"]}

    anomaly = firing.head
    facts = sorted(base.facts)
    if not facts:
        return {"_error": "theory has no facts", "name": record["id"]}
    body_atom = next((f for f in facts if f not in firing.body), facts[0])

    new_defeater = Rule(
        head=f"~{anomaly}",
        body=(body_atom,),
        rule_type=RuleType.DEFEATER,
        label=f"syn_df_{record['id']}",
    )

    repaired = Theory(
        facts=set(base.facts),
        rules=list(base.rules) + [new_defeater],
        superiority={},
    )
    if firing.label and new_defeater.label:
        repaired.add_superiority(new_defeater.label, firing.label)

    try:
        inst = generate_level3_instance(repaired, anomaly, new_defeater, k_distractors=5)
    except ValueError as exc:
        return {"_error": str(exc), "name": record["id"]}

    candidates_str = [_format_rule(c) for c in inst.candidates]
    gold_str = _format_rule(new_defeater)
    theory_facts = sorted(inst.D_minus.facts)
    theory_rules = [_format_rule(r) for r in inst.D_minus.rules]

    return {
        "name": record["id"],
        "domain": "synthetic",
        "level": 3,
        "anomaly": anomaly,
        "gold": gold_str,
        "gold_label": new_defeater.label,
        "candidates": candidates_str,
        "distractors": candidates_str[1:],
        "preserved_expectations": inst.metadata.get("preserved_expectations", []),
        "defeater_type": "weak",
        "description": (
            f"Synthetic L3 instance structurally matched to "
            f"{record.get('matched_to', 'unknown')}. Anomaly chosen as the head "
            f"of the first firing defeasible rule; gold defeater synthesized to "
            f"block it under condition {body_atom}."
        ),
        "novel_predicates": [],
        "novel_facts_for_gold": [],
        "nov": inst.metadata.get("nov", 0.0),
        "d_rev": inst.metadata.get("d_rev", 1),
        "conservative": inst.metadata.get("conservative", True),
        "lost_expectations": [],
        "valid": True,
        "errors": [],
        "theory_size": len(theory_facts) + len(theory_rules),
        "theory_facts": theory_facts,
        "theory_rules": theory_rules,
        "matched_to": record.get("matched_to"),
        "synthetic": True,
    }


def main() -> int:
    src = ROOT / "instances" / "synthetic" / "synthetic_instances.json"
    if not src.exists():
        print(f"ERROR: {src} not found")
        return 1

    with open(src) as f:
        data = json.load(f)

    l3_inputs = [i for i in data["instances"] if i.get("level") == 3]
    print(f"Loading {len(l3_inputs)} synthetic L3 records...")

    out_records = []
    skipped = []
    for rec in l3_inputs:
        result = _convert(rec)
        if result is None:
            skipped.append((rec["id"], "no DEFEATER rule"))
            continue
        if "_error" in result:
            skipped.append((result["name"], result["_error"]))
            continue
        out_records.append(result)

    print(f"Built {len(out_records)} valid L3 instances; {len(skipped)} skipped.")
    for name, reason in skipped[:10]:
        print(f"  - {name}: {reason}")
    if len(skipped) > 10:
        print(f"  ... and {len(skipped) - 10} more")

    out_path = ROOT / "instances" / "synthetic" / "level3_instances.json"
    out_doc = {
        "metadata": {
            "name": "DeFAb Synthetic Contamination Control L3 Instances",
            "total": len(out_records),
            "matched_to": "Tier 0 Level 3 evaluation instances",
            "generation": "experiments/build_synthetic_level3.py",
        },
        "instances": out_records,
    }
    with open(out_path, "w") as f:
        json.dump(out_doc, f, indent=2)
    print(f"Wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
