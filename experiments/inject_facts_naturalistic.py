"""
Phase 4A: Matched fact-injection ablation for Δ_synth interpretation.

The paper's synthetic contamination control applied a "fact-injection" repair
to synthetic L3 instances (when the generated theory's defeater body did not
ground against the existing facts). This means the synthetic instances differ
from naturalistic ones not only in vocabulary but also in effective theory
composition — the fact-injection adds an additional grounding fact that does
not appear in the corresponding naturalistic instance.

This script applies IDENTICAL fact-injection to the 35 naturalistic Tier 0 L3
instances, producing "injection-matched naturalistic" instances. By comparing:

  Acc(naturalistic original)       vs  Acc(naturalistic injected)
  Acc(synthetic original)          vs  Acc(synthetic injected)

we can compute a cleaner Δ_synth that isolates vocabulary-level contamination
from the surface-composition artifact introduced by fact injection.

True contamination gap = Acc(nat-injected) - Acc(syn-injected)
Fact-injection artifact = Acc(nat-original) - Acc(nat-injected)

Output: instances/naturalistic_injected/level3_instances.json
(same schema as instances/level3_instances.json; drop-in replacement for eval)

Usage:
  python experiments/inject_facts_naturalistic.py
  # Then re-run: python experiments/run_evaluation.py --provider foundry-deepseek \
  #   --modalities M4 --strategies direct cot --include-level3 --level3-limit 35 \
  #   --instances-dir instances/naturalistic_injected \
  #   --results-dir experiments/results/nat_injected_$(date +%Y%m%d)

Author: Patrick Cooper
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.reasoning.defeasible import defeasible_provable


def _parse_rule_str(rule_str: str) -> Rule:
    s = rule_str.strip()
    if ":" in s:
        label, rest = s.split(":", 1)
        label, rest = label.strip(), rest.strip()
    else:
        label, rest = None, s
    if "~>" in rest:
        body_part, head_part = rest.split("~>", 1)
        rule_type = RuleType.DEFEATER
    elif "=>" in rest:
        body_part, head_part = rest.split("=>", 1)
        rule_type = RuleType.DEFEASIBLE
    elif ":-" in rest:
        body_part, head_part = rest.split(":-", 1)
        rule_type = RuleType.STRICT
    else:
        return Rule(head=rest.strip(), body=(), rule_type=RuleType.STRICT, label=label)
    body_atoms = tuple(b.strip() for b in body_part.split(",") if b.strip())
    return Rule(head=head_part.strip(), body=body_atoms, rule_type=rule_type, label=label)


def _reconstruct_theory(inst: dict) -> Theory:
    facts = set(inst.get("theory_facts", []))
    rules = [_parse_rule_str(r) for r in inst.get("theory_rules", [])]
    return Theory(facts=facts, rules=rules, superiority={})


def _parse_gold_rule(gold_str: str) -> Optional[Rule]:
    try:
        return _parse_rule_str(gold_str)
    except Exception:
        return None


def _inject_gold_body_facts(inst: dict) -> dict:
    """Apply fact injection to one naturalistic L3 instance.

    If the gold rule's body atoms are already grounded by the theory's facts
    (i.e., the instance is "self-contained"), no injection is needed and the
    instance is returned unchanged.

    Otherwise, we inject grounding facts for the gold rule's body atoms
    using the subject from the anomaly literal, exactly as done by
    experiments/build_synthetic_level3.py for synthetic instances.
    """
    gold_str = inst.get("gold", "")
    anomaly = inst.get("anomaly", "")
    gold_rule = _parse_gold_rule(gold_str)
    if gold_rule is None or not anomaly:
        return inst  # cannot inject; return unchanged

    # Extract subject from anomaly literal
    if "(" not in anomaly:
        return inst
    subject = anomaly.split("(")[1].rstrip(")")

    theory = _reconstruct_theory(inst)

    # Check if gold body already grounds
    injected_facts = []
    for body_atom in gold_rule.body:
        # Substitute variable X with subject
        grounded = body_atom
        for ch in "XYZABCDEFGHIJKLMNOPQRSTUVW":
            grounded = grounded.replace(f"({ch})", f"({subject})")
            grounded = grounded.replace(f", {ch})", f", {subject})")
            grounded = grounded.replace(f"({ch},", f"({subject},")
        if grounded not in theory.facts:
            injected_facts.append(grounded)

    if not injected_facts:
        # Already grounded — mark as injection-not-needed (no change)
        out = dict(inst)
        out["injection_applied"] = False
        out["injected_facts"] = []
        return out

    # Apply injection
    out = dict(inst)
    new_facts = list(inst.get("theory_facts", [])) + injected_facts
    out["theory_facts"] = new_facts
    out["theory_size"] = len(new_facts) + len(inst.get("theory_rules", []))
    out["injection_applied"] = True
    out["injected_facts"] = injected_facts
    return out


def main() -> int:
    src = ROOT / "instances" / "level3_instances.json"
    if not src.exists():
        print(f"ERROR: {src} not found.")
        return 1

    with open(src) as f:
        data = json.load(f)

    instances = data.get("instances", [])
    print(f"Processing {len(instances)} naturalistic L3 instances...")

    injected = []
    n_modified = 0
    for inst in instances:
        out = _inject_gold_body_facts(inst)
        if out.get("injection_applied", False):
            n_modified += 1
        injected.append(out)

    print(f"Injection applied:     {n_modified}/{len(instances)}")
    print(f"Already grounded:      {len(instances) - n_modified}/{len(instances)}")

    out_dir = ROOT / "instances" / "naturalistic_injected"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "level3_instances.json"

    out_doc = {
        "metadata": {
            "name": "DeFAb Tier 0 L3 Instances (Fact-Injection-Matched)",
            "source": str(src),
            "total": len(injected),
            "injection_applied": n_modified,
            "description": (
                "Naturalistic Tier 0 L3 instances with the same fact-injection "
                "treatment applied to synthetic instances (build_synthetic_level3.py). "
                "Used for the matched Delta_synth ablation (Phase 4A)."
            ),
        },
        "instances": injected,
    }
    with open(out_path, "w") as f:
        json.dump(out_doc, f, indent=2)
    print(f"\nWrote {out_path}")
    print(
        "\nNext: re-evaluate all four frontier models on this directory:\n"
        "  python experiments/run_evaluation.py "
        "--provider foundry-deepseek --modalities M4 --strategies direct cot "
        "--include-level3 --level3-limit 35 "
        "--instances-dir instances/naturalistic_injected "
        "--results-dir experiments/results/nat_injected_YYYYMMDD"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
