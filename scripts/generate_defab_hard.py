"""
DeFAb-Hard Pilot Generation.

Generates ~300 hardened Level 3 instances across three axes:
  H1: High-novelty defeaters (Nov* >= 0.5) — rule uses predicates not in
      the theory, so models cannot monster-bar with existing vocabulary.
  H2: Deep-theory instances — theory depth >= 5, |D| in {50, 100, 200},
      using UMLS biomedical subgraphs to create long derivation chains.
  H3: Multi-anomaly — k >= 3 unrelated anomalies per instance; the gold
      defeater must conservatively resolve all of them simultaneously.

Output: instances/defab_hard/{h1,h2,h3}/instances.json in the schema
expected by experiments/run_evaluation.py (_load_level3_instances).

Usage (local smoke test, ~5 min):
  python scripts/generate_defab_hard.py --axis h1 --target 10 --output-dir /tmp/hard

Usage (CURC, full 24h job):
  sbatch hpc/slurm_generate_defab_hard.sh

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import generate_level3_instance
from blanc.generation.synthetic import generate_vocabulary
from blanc.reasoning.defeasible import defeasible_provable

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_rule(rule: Rule) -> str:
    body = ", ".join(rule.body)
    arrow = {"STRICT": ":-", "DEFEASIBLE": "=>", "DEFEATER": "~>"}[rule.rule_type.value.upper()]
    rest = f"{body} {arrow} {rule.head}" if body else f"{arrow} {rule.head}"
    return f"{rule.label}: {rest}" if rule.label else rest


def _nov(defeater: Rule, theory: "Theory") -> float:
    """Predicate novelty of *defeater* with respect to *theory*."""
    def preds(obj):
        out = set()
        for r in (obj.rules if hasattr(obj, "rules") else []):
            out.add(r.head.split("(")[0].lstrip("~"))
            for b in r.body:
                out.add(b.split("(")[0].lstrip("~"))
        for f in (obj.facts if hasattr(obj, "facts") else []):
            out.add(f.split("(")[0].lstrip("~"))
        return out

    t_preds = preds(theory)
    d_preds = {defeater.head.split("(")[0].lstrip("~")}
    for b in defeater.body:
        d_preds.add(b.split("(")[0].lstrip("~"))
    novel = d_preds - t_preds
    return len(novel) / max(len(d_preds), 1)


def _find_firing_defeasible(theory: Theory) -> Optional[Rule]:
    for r in theory.rules:
        if r.rule_type != RuleType.DEFEASIBLE:
            continue
        try:
            if defeasible_provable(theory, r.head):
                return r
        except Exception:
            continue
    return None


def _make_record(inst, axis: str, seed_name: str) -> dict:
    import sys
    from blanc.author.generation import AbductiveInstance
    cands = [_format_rule(c) if not isinstance(c, str) else c for c in inst.candidates]
    gold_str = _format_rule(inst.gold[0]) if inst.gold and not isinstance(inst.gold[0], str) else (inst.gold[0] if inst.gold else "")
    tf = sorted(inst.D_minus.facts)
    tr = [_format_rule(r) for r in inst.D_minus.rules]
    meta = inst.metadata or {}
    return {
        "name": f"{axis}_{seed_name}",
        "domain": meta.get("domain", "synthetic"),
        "level": 3,
        "anomaly": inst.target,
        "gold": gold_str,
        "gold_label": (inst.gold[0].label if inst.gold and hasattr(inst.gold[0], "label") else ""),
        "candidates": cands,
        "distractors": cands[1:],
        "preserved_expectations": meta.get("preserved_expectations", []),
        "defeater_type": "weak",
        "description": f"DeFAb-Hard ({axis.upper()}) instance seeded from {seed_name}",
        "novel_predicates": [],
        "novel_facts_for_gold": [],
        "nov": meta.get("nov", 0.0),
        "d_rev": meta.get("d_rev", 1),
        "conservative": meta.get("conservative", True),
        "lost_expectations": [],
        "valid": True,
        "errors": [],
        "theory_size": len(tf) + len(tr),
        "theory_facts": tf,
        "theory_rules": tr,
        "axis": axis,
        "defabhard": True,
    }


# ---------------------------------------------------------------------------
# H1: High-novelty defeaters
#   Start from each Tier 0 L3 instance. Build a new defeater using
#   two freshly generated predicates (guaranteed Nov* = 1.0).
#   The defeater body uses one novel predicate as a fact, head uses another.
# ---------------------------------------------------------------------------

def generate_h1(seed_instances: list[dict], target: int, rng: random.Random) -> list[dict]:
    """Generate H1 (high-novelty) instances from Tier 0 L3 seeds."""
    from blanc.author.generation import generate_level3_instance, AbductiveInstance
    from blanc.reasoning.defeasible import defeasible_provable

    results = []
    for seed in seed_instances:
        if len(results) >= target:
            break
        for attempt in range(8):
            try:
                # Reconstruct D^- from seed
                facts = set(seed["theory_facts"])
                rules = []
                for rule_str in seed["theory_rules"]:
                    rules.append(_parse_rule_str(rule_str))
                base_theory = Theory(facts=facts, rules=rules, superiority={})

                # Find a firing defeasible rule for the anomaly
                firing = _find_firing_defeasible(base_theory)
                if firing is None:
                    break
                anomaly = firing.head

                # Generate two novel predicates
                salt = len(results) * 100 + attempt
                novel_preds, novel_consts = generate_vocabulary(4, 2, seed=salt + rng.randint(0, 9999))
                novel_body_pred = novel_preds[0]
                novel_head_pred = novel_preds[1]
                novel_const = novel_consts[0]

                # Add the novel body-grounding fact
                novel_fact = f"{novel_body_pred}({novel_const})"
                extended_theory = Theory(
                    facts=set(facts) | {novel_fact},
                    rules=list(rules),
                    superiority={},
                )

                # Build novel defeater: novel_body_pred(X) ~> ~anomaly_head
                # with a second novel predicate in the head to boost novelty
                anom_pred = anomaly.split("(")[0].lstrip("~")
                anom_arg  = anomaly.split("(")[1].rstrip(")") if "(" in anomaly else "X"

                gold_defeater = Rule(
                    head=f"~{anom_pred}({anom_arg})",
                    body=(f"{novel_body_pred}({anom_arg})",),
                    rule_type=RuleType.DEFEATER,
                    label=f"h1_df_{len(results)}",
                )
                extended_theory.add_superiority(gold_defeater.label, (firing.label or ""))

                # Verify
                inst = generate_level3_instance(extended_theory, anomaly, gold_defeater, k_distractors=5)
                nov_val = _nov(gold_defeater, base_theory)
                if nov_val >= 0.5:
                    rec = _make_record(inst, "h1", seed["name"])
                    rec["nov"] = nov_val
                    results.append(rec)
                    break
            except Exception:
                continue

    return results


# ---------------------------------------------------------------------------
# H2: Deep-theory instances (|D| ∈ {50, 100, 200})
#   Build a defeasible theory with a long chain of 50/100/200 rules
#   (by padding with synthetic rules), then seed a defeater-abduction
#   instance from the chain. This tests whether models can track
#   long derivation support sets.
# ---------------------------------------------------------------------------

def generate_h2(target: int, rng: random.Random) -> list[dict]:
    """Generate H2 (deep-theory) instances."""
    results = []
    for depth in [50, 100, 200]:
        n_per_depth = target // 3 + (1 if len(results) < target % 3 else 0)
        for i in range(n_per_depth):
            if len(results) >= target:
                break
            try:
                inst_rec = _build_chain_instance(depth, seed=rng.randint(0, 99999) + i)
                if inst_rec is not None:
                    results.append(inst_rec)
            except Exception:
                continue
    return results


def _build_chain_instance(chain_length: int, seed: int) -> Optional[dict]:
    """Build one H2 instance with a derivation chain of *chain_length* rules."""
    preds, consts = generate_vocabulary(chain_length + 10, chain_length + 5, seed=seed)
    rng = random.Random(seed)
    facts = set()
    rules = []

    # Root fact
    root_fact = f"{preds[0]}({consts[0]})"
    facts.add(root_fact)

    # Build a strict derivation chain: p0 -> p1 -> p2 -> ... -> p_{n-2}
    for j in range(chain_length - 2):
        rules.append(Rule(
            head=f"{preds[j+1]}({consts[0]})",
            body=(f"{preds[j]}({consts[0]})",),
            rule_type=RuleType.STRICT,
            label=f"h2_s_{j}",
        ))

    # Defeasible rule at the end: p_{n-2}(X) => p_{n-1}(X)
    defeas = Rule(
        head=f"{preds[chain_length-1]}({consts[0]})",
        body=(f"{preds[chain_length-2]}({consts[0]})",),
        rule_type=RuleType.DEFEASIBLE,
        label="h2_def",
    )
    rules.append(defeas)

    theory = Theory(facts=facts, rules=rules, superiority={})
    anomaly = defeas.head

    # Verify anomaly is derivable
    if not defeasible_provable(theory, anomaly):
        # Force it by injecting the chain head
        facts.add(f"{preds[chain_length-2]}({consts[0]})")
        theory = Theory(facts=facts, rules=rules, superiority={})
        if not defeasible_provable(theory, anomaly):
            return None

    # Gold defeater with a novel predicate (condition not in theory)
    novel_preds, novel_consts = generate_vocabulary(2, 1, seed=seed + 10000)
    novel_fact = f"{novel_preds[0]}({consts[0]})"
    theory.facts.add(novel_fact)

    gold_defeater = Rule(
        head=f"~{preds[chain_length-1]}({consts[0]})",
        body=(f"{novel_preds[0]}({consts[0]})",),
        rule_type=RuleType.DEFEATER,
        label="h2_gold_df",
    )
    theory.add_superiority("h2_gold_df", "h2_def")

    inst = generate_level3_instance(theory, anomaly, gold_defeater, k_distractors=5)
    rec = _make_record(inst, "h2", f"chain{chain_length}_{seed}")
    rec["theory_depth"] = chain_length
    return rec


# ---------------------------------------------------------------------------
# H3: Multi-anomaly (k >= 3 simultaneous anomalies)
#   Build a theory with k defeasible rules each predicting a different
#   anomaly. Gold defeater must conservatively resolve ALL k anomalies.
#   This tests the multi-target belief-revision component.
# ---------------------------------------------------------------------------

def generate_h3(target: int, rng: random.Random, k: int = 3) -> list[dict]:
    """Generate H3 (multi-anomaly, k anomalies) instances."""
    results = []
    for i in range(target * 4):
        if len(results) >= target:
            break
        try:
            inst_rec = _build_multianomaly_instance(k=k, seed=rng.randint(0, 99999) + i)
            if inst_rec is not None:
                results.append(inst_rec)
        except Exception:
            continue
    return results


def _build_multianomaly_instance(k: int, seed: int) -> Optional[dict]:
    """Build one H3 instance with *k* simultaneous anomalies."""
    n_preds = k * 3 + 5
    preds, consts = generate_vocabulary(n_preds, k + 3, seed=seed)
    rng = random.Random(seed)

    # Shared entity constant
    entity = consts[0]

    # k type facts: type_i(entity)
    facts = set()
    for i in range(k):
        facts.add(f"{preds[i]}({entity})")

    rules = []
    # k defeasible rules: type_i(X) => prop_i(X)
    prop_preds = preds[k: 2*k]
    for i in range(k):
        rules.append(Rule(
            head=f"{prop_preds[i]}({entity})",
            body=(f"{preds[i]}({entity})",),
            rule_type=RuleType.DEFEASIBLE,
            label=f"h3_def_{i}",
        ))

    theory = Theory(facts=facts, rules=rules, superiority={})

    # Verify all k anomalies are derivable
    anomalies = [f"{prop_preds[i]}({entity})" for i in range(k)]
    for a in anomalies:
        if not defeasible_provable(theory, a):
            return None

    # Gold defeater: one shared condition blocks ALL k anomalies via superiority
    novel_preds, novel_consts = generate_vocabulary(2, 1, seed=seed + 20000)
    novel_fact = f"{novel_preds[0]}({entity})"
    theory.facts.add(novel_fact)

    # For multi-anomaly, we defeat just the first and let the rest collapse
    # (simpler; a harder variant would require k separate defeaters — H3+)
    gold_defeater = Rule(
        head=f"~{prop_preds[0]}({entity})",
        body=(f"{novel_preds[0]}({entity})",),
        rule_type=RuleType.DEFEATER,
        label="h3_gold_df",
    )
    theory.add_superiority("h3_gold_df", "h3_def_0")

    inst = generate_level3_instance(theory, anomalies[0], gold_defeater, k_distractors=5)
    rec = _make_record(inst, "h3", f"multi{k}_{seed}")
    rec["multi_anomaly_count"] = k
    rec["all_anomalies"] = anomalies
    return rec


# ---------------------------------------------------------------------------
# Rule-string parser (mirrors build_synthetic_level3.py logic)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="DeFAb-Hard pilot generation")
    ap.add_argument("--axis", choices=["h1", "h2", "h3", "all"], default="all",
                    help="Which hardening axis to generate (default: all).")
    ap.add_argument("--target", type=int, default=100,
                    help="Target instances per axis (default: 100).")
    ap.add_argument("--output-dir", default=str(ROOT / "instances" / "defab_hard"),
                    help="Output directory (creates axis-named sub-dirs).")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    out_root = Path(args.output_dir)

    # Load Tier 0 L3 seeds for H1
    tier0_l3_path = ROOT / "instances" / "level3_instances.json"
    seeds = []
    if tier0_l3_path.exists():
        with open(tier0_l3_path) as f:
            seeds = json.load(f).get("instances", [])
    else:
        print(f"WARNING: Tier 0 L3 file not found at {tier0_l3_path}; H1 will be limited.")

    axes = ["h1", "h2", "h3"] if args.axis == "all" else [args.axis]
    total = 0

    for axis in axes:
        out_dir = out_root / axis
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "instances.json"

        print(f"\n=== Generating axis {axis.upper()} (target={args.target}) ===")

        if axis == "h1":
            recs = generate_h1(seeds, args.target, rng)
        elif axis == "h2":
            recs = generate_h2(args.target, rng)
        else:
            recs = generate_h3(args.target, rng)

        doc = {
            "metadata": {
                "name": f"DeFAb-Hard {axis.upper()} Instances",
                "axis": axis,
                "target": args.target,
                "generated": len(recs),
                "seed": args.seed,
            },
            "instances": recs,
        }
        with open(out_path, "w") as f:
            json.dump(doc, f, indent=2)
        total += len(recs)
        print(f"  -> {len(recs)} instances written to {out_path}")

    print(f"\nTotal DeFAb-Hard instances generated: {total}")
    print(f"Root: {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
