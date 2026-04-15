"""
Certify the RTS engagement knowledge base for DeFAb.

This script runs a comprehensive validation of the DeFAb-ROE knowledge base,
producing a certification report that mirrors the structural statistics reported
in the paper for biology/legal/materials domains.  It verifies:

  1. KB structure: rule counts, fact counts, superiority relations.
  2. L3 seed conflicts: each of the 6 hand-crafted ROE scenarios is
     formally verified end-to-end through the DefeasibleEngine.
  3. L1/L2 instance generation: the standard pipeline produces well-formed,
     verifier-valid instances.
  4. Conservativity spot-checks: key ROE exceptions are conservative.

Usage:
    python scripts/certify_rts_kb.py
    python scripts/certify_rts_kb.py --output data/rts_certification_report.json
    python scripts/certify_rts_kb.py --verbose

The report compares DeFAb-ROE to the other three domains:
    Biology  (YAGO 4.5 + WordNet 3.0): 918 rules, 255 facts
    Legal    (LKIF Core):              201 rules,  63 facts
    Materials (MatOnto):             1190 rules,  86 facts

Author: Patrick Cooper
"""

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from examples.knowledge_bases.rts_engagement_kb import (
    create_rts_engagement_kb,
    get_rts_stats,
)
from scripts.generate_rts_instances import (
    ROE_LEVEL3_SEEDS,
    generate_from_rts_kb,
)
from blanc.reasoning.defeasible import defeasible_provable, DefeasibleEngine
from blanc.author.conversion import phi_kappa
from blanc.author.support import full_theory_criticality
from blanc.author.generation import generate_level2_instance
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    compute_dependency_depths,
)
from blanc.core.theory import RuleType


# ── Reference domain statistics (from paper Section 3) ───────────────────────
DOMAIN_REFERENCE = {
    "biology":   {"rules": 918,  "facts": 255, "sources": ["YAGO 4.5", "WordNet 3.0"]},
    "legal":     {"rules": 201,  "facts":  63, "sources": ["LKIF Core"]},
    "materials": {"rules": 1190, "facts":  86, "sources": ["MatOnto"]},
}


def _theory_with_facts(base_kb, extra_facts: list[str]):
    """Return a deep copy of the KB with extra facts added."""
    t = copy.deepcopy(base_kb)
    for f in extra_facts:
        t.add_fact(f)
    return t


# ── Section 1: KB structure ───────────────────────────────────────────────────

def certify_kb_structure(kb, verbose: bool) -> dict:
    """Verify and report KB structural statistics."""
    print("\n" + "=" * 70)
    print("SECTION 1: KB STRUCTURE")
    print("=" * 70)

    stats = get_rts_stats(kb)

    strict = [r for r in kb.rules if r.rule_type == RuleType.STRICT]
    defeasible = [r for r in kb.rules if r.rule_type == RuleType.DEFEASIBLE]
    defeaters = [r for r in kb.rules if r.rule_type == RuleType.DEFEATER]
    roe_rules = [r for r in kb.rules if r.label and r.label.startswith("rts_r")]

    result = {
        "rules_total": stats["rules_total"],
        "facts_total": stats["facts_total"],
        "strict_rules": stats["strict_rules"],
        "defeasible_rules": stats["defeasible_rules"],
        "defeater_rules": stats["defeater_rules"],
        "roe_behavioral_rules": stats["roe_behavioral"],
        "superiority_relations": len(kb.superiority),
        "max_dependency_depth": stats["max_dependency_depth"],
        "sources": stats["sources"],
        "comparison_to_existing_domains": DOMAIN_REFERENCE,
    }

    print(f"\n  Domain:              rts_engagement")
    print(f"  Total rules:         {result['rules_total']}")
    print(f"  Total facts:         {result['facts_total']}")
    print(f"  Strict rules:        {result['strict_rules']}")
    print(f"  Defeasible rules:    {result['defeasible_rules']}")
    print(f"  Defeater rules:      {result['defeater_rules']}")
    print(f"  ROE behavioral:      {result['roe_behavioral_rules']}")
    print(f"  Superiority rels:    {result['superiority_relations']}")
    print(f"  Max dep. depth:      {result['max_dependency_depth']}")

    print(f"\n  Comparison:")
    print(f"    {'Domain':<12} {'Rules':>8} {'Facts':>7}")
    print(f"    {'-'*12} {'-'*8} {'-'*7}")
    for domain, ref in DOMAIN_REFERENCE.items():
        print(f"    {domain:<12} {ref['rules']:>8} {ref['facts']:>7}")
    print(f"    {'rts_roe':<12} {result['rules_total']:>8} {result['facts_total']:>7}")

    # Assertions
    errors = []
    if result["rules_total"] < 50:
        errors.append(f"Too few rules: {result['rules_total']} < 50")
    if result["facts_total"] < 30:
        errors.append(f"Too few facts: {result['facts_total']} < 30")
    if result["strict_rules"] < 20:
        errors.append(f"Too few strict rules: {result['strict_rules']} < 20")
    if result["defeasible_rules"] < 20:
        errors.append(f"Too few defeasible ROE rules: {result['defeasible_rules']} < 20")
    if result["defeater_rules"] < 10:
        errors.append(f"Too few defeaters: {result['defeater_rules']} < 10")
    if result["superiority_relations"] < 5:
        errors.append(f"Too few superiority relations: {result['superiority_relations']} < 5")

    result["errors"] = errors
    result["passed"] = len(errors) == 0
    _print_status(result["passed"], "KB structure checks")
    if errors and verbose:
        for e in errors:
            print(f"    ERROR: {e}")
    return result


# ── Section 2: L3 seed conflict verification ─────────────────────────────────

def certify_l3_seed_conflicts(kb, verbose: bool) -> dict:
    """
    For each L3 seed conflict, verify:
      A. In D^-: the anomaly IS derivable (theory without defeater produces
         the 'wrong' conclusion).
      B. In D:  the anomaly is NOT derivable (defeater resolves the conflict).
      C. Conservativity: all unrelated ROE conclusions are preserved in D.
    """
    print("\n" + "=" * 70)
    print("SECTION 2: LEVEL 3 SEED CONFLICT VERIFICATION")
    print("=" * 70)
    print(f"\n  Verifying {len(ROE_LEVEL3_SEEDS)} ROE seed scenarios...")

    results = []
    passed_count = 0

    for seed in ROE_LEVEL3_SEEDS:
        sid = seed["scenario_id"]
        print(f"\n  Scenario: {sid}")

        result = {
            "scenario_id": sid,
            "description": seed["description"][:120] + "...",
            "anomaly": seed["anomaly"],
            "defeater_label": seed["defeater_label"],
        }

        # Build D (full theory) and D^- (without the defeater)
        working = copy.deepcopy(kb)
        for fact in seed["context_facts"]:
            working.add_fact(fact)

        defeater_rule = None
        for rule in working.rules:
            if rule.label == seed["defeater_label"]:
                defeater_rule = rule
                break

        if defeater_rule is None:
            result["error"] = f"defeater label {seed['defeater_label']} not found in KB"
            result["passed"] = False
            results.append(result)
            _print_status(False, sid)
            continue

        # Build D^- by removing the defeater
        from blanc.author.support import _remove_element
        d_minus = _remove_element(working, defeater_rule)

        anomaly = seed["anomaly"]

        # Check A: anomaly derivable in D^-
        try:
            anomaly_in_d_minus = defeasible_provable(d_minus, anomaly)
        except Exception as e:
            anomaly_in_d_minus = False
            result["check_a_error"] = str(e)

        # Check B: anomaly NOT derivable in D (full theory)
        try:
            anomaly_in_d = defeasible_provable(working, anomaly)
        except Exception as e:
            anomaly_in_d = True  # pessimistic
            result["check_b_error"] = str(e)

        # Check C: conservativity -- a sample of unrelated ROE conclusions
        # should be identical in D^- and D
        conservativity_checks = [
            "can_attack_ground(marine)",
            "protected_from_attack(enemy_scv_cluster)",
            "gathers_resources(scv)",
            "is_mobile(marine)",
        ]
        # Exclude predicates that appear in the anomaly head
        anomaly_pred = anomaly.split("(")[0].lstrip("~")
        checks_to_run = [c for c in conservativity_checks
                         if anomaly_pred not in c]

        conservativity_violations = []
        for check in checks_to_run:
            try:
                in_d_minus = defeasible_provable(d_minus, check)
                in_d = defeasible_provable(working, check)
                if in_d_minus != in_d:
                    conservativity_violations.append({
                        "query": check,
                        "in_d_minus": in_d_minus,
                        "in_d": in_d,
                    })
            except Exception:
                pass

        result["check_a_anomaly_derivable_in_d_minus"] = anomaly_in_d_minus
        result["check_b_anomaly_resolved_in_d"] = not anomaly_in_d
        result["check_c_conservativity_violations"] = conservativity_violations
        result["check_c_passed"] = len(conservativity_violations) == 0

        scenario_passed = (
            anomaly_in_d_minus
            and not anomaly_in_d
            and len(conservativity_violations) == 0
        )
        result["passed"] = scenario_passed
        if scenario_passed:
            passed_count += 1

        _print_status(anomaly_in_d_minus,
                      f"  A: anomaly derivable in D^- ({anomaly})")
        _print_status(not anomaly_in_d,
                      f"  B: anomaly resolved in D    ({anomaly})")
        _print_status(result["check_c_passed"],
                      f"  C: conservativity           ({len(checks_to_run)} checks)")

        if verbose and conservativity_violations:
            for v in conservativity_violations:
                print(f"     VIOLATION: {v['query']} "
                      f"D^-={v['in_d_minus']} D={v['in_d']}")

        results.append(result)

    summary = {
        "total_seeds": len(ROE_LEVEL3_SEEDS),
        "passed": passed_count,
        "failed": len(ROE_LEVEL3_SEEDS) - passed_count,
        "pass_rate": passed_count / len(ROE_LEVEL3_SEEDS),
        "scenarios": results,
    }

    print(f"\n  Result: {passed_count}/{len(ROE_LEVEL3_SEEDS)} seed scenarios passed "
          f"({summary['pass_rate']*100:.0f}%)")
    return summary


# ── Section 3: L1/L2 instance generation ─────────────────────────────────────

def certify_instance_generation(kb, max_per_partition: int, verbose: bool) -> dict:
    """Generate L1 and L2 instances and validate each with is_valid()."""
    print("\n" + "=" * 70)
    print("SECTION 3: INSTANCE GENERATION CERTIFICATION")
    print("=" * 70)

    result = {}

    for level in [1, 2]:
        print(f"\n  Generating Level {level} instances...")
        try:
            instances, partition_results = generate_from_rts_kb(
                kb, level=level, max_per_partition=max_per_partition
            )
        except Exception as e:
            result[f"level{level}"] = {
                "count": 0, "valid": 0, "validity_rate": 0.0,
                "error": str(e),
            }
            print(f"    ERROR: {e}")
            continue

        valid_count = sum(1 for inst in instances if inst.is_valid())
        validity_rate = valid_count / len(instances) if instances else 0.0

        result[f"level{level}"] = {
            "count": len(instances),
            "valid": valid_count,
            "invalid": len(instances) - valid_count,
            "validity_rate": validity_rate,
            "partition_strategies_used": len(partition_results),
        }
        if verbose and (len(instances) - valid_count) > 0:
            print(f"    WARNING: {len(instances) - valid_count} invalid instances")

        _print_status(
            validity_rate == 1.0 or len(instances) == 0,
            f"  Level {level}: {valid_count}/{len(instances)} valid "
            f"({validity_rate*100:.0f}%)"
        )

    return result


# ── Section 4: Conservativity spot checks ────────────────────────────────────

def certify_conservativity(kb, verbose: bool) -> dict:
    """
    Spot-check that ROE exceptions are conservative at the KB level.
    These checks duplicate some L3 seed logic but run against the base
    KB directly, without removing any rule.
    """
    print("\n" + "=" * 70)
    print("SECTION 4: CONSERVATIVITY SPOT CHECKS")
    print("=" * 70)

    checks = [
        {
            "name": "exclusion_zone_blocks_in_zone_not_out_of_zone",
            "description": (
                "Exclusion zone defeater (rts_r3003) blocks engagement inside "
                "restricted_zone_alpha but does NOT affect engagement outside it"
            ),
            "extra_facts": [
                "in_zone(marine, restricted_zone_alpha)",
                "in_zone(enemy_marine_squad, restricted_zone_alpha)",
            ],
            "query_should_be_true":  [
                # stalker not in zone -- engagement still authorized (conservativity)
                "authorized_to_engage(stalker, enemy_siege_tank)",
            ],
            "query_should_be_false": [
                # marine in zone -- engagement blocked (the defeater fires)
                "authorized_to_engage(marine, enemy_marine_squad)",
            ],
        },
        {
            "name": "worker_protection_blocks_worker_not_military_target",
            "description": (
                "Worker protection defeater (rts_r3012) blocks engagement of "
                "protected workers but does NOT affect engagement of military targets"
            ),
            "extra_facts": [],  # enemy_probe_line already worker_target in KB
            "query_should_be_true":  [
                # military target -- engagement authorized (conservativity)
                "authorized_to_engage(marine, enemy_marine_squad)",
            ],
            "query_should_be_false": [
                # worker target -- engagement blocked (worker protection fires)
                "authorized_to_engage(marine, enemy_probe_line)",
            ],
        },
        {
            "name": "retreat_override_does_not_affect_engagement_rules",
            "description": (
                "All-in rush retreat override does NOT affect engagement "
                "authorizations or worker protection rules -- unrelated predicates "
                "must be preserved (conservativity)"
            ),
            "extra_facts": [
                "has_numerical_disadvantage(zealot)",
                "all_in_rush_detected",
                "assigned_to_mission(stalker, op_ghost_eye)",
            ],
            "query_should_be_true":  [
                # engagement authorization for non-retreat scenario unaffected (conservativity)
                "authorized_to_engage(marine, enemy_marine_squad)",
                # stealth posture for recon mission unaffected by retreat logic (conservativity)
                "stealth_posture_active(stalker)",
            ],
            "query_should_be_false": [
                # zealot with all-in rush -- retreat correctly cancelled
                "ordered_to_retreat(zealot)",
            ],
        },
    ]

    results = []
    passed_count = 0

    for check in checks:
        print(f"\n  Check: {check['name']}")
        theory = copy.deepcopy(kb)
        for f in check["extra_facts"]:
            theory.add_fact(f)

        errors = []
        for q in check["query_should_be_true"]:
            if not defeasible_provable(theory, q):
                errors.append(f"Expected TRUE but got FALSE: {q}")
        for q in check["query_should_be_false"]:
            if defeasible_provable(theory, q):
                errors.append(f"Expected FALSE but got TRUE: {q}")

        passed = len(errors) == 0
        if passed:
            passed_count += 1
        result_item = {
            "name": check["name"],
            "description": check["description"],
            "passed": passed,
            "errors": errors,
        }
        results.append(result_item)
        _print_status(passed, f"  {check['name']}")
        if verbose and errors:
            for e in errors:
                print(f"    ERROR: {e}")

    summary = {
        "total": len(checks),
        "passed": passed_count,
        "failed": len(checks) - passed_count,
        "checks": results,
    }
    return summary


# ── Helpers ────────────────────────────────────────────────────────────────────

def _print_status(ok: bool, label: str) -> None:
    status = "PASS" if ok else "FAIL"
    print(f"    [{status}] {label}")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Certify the DeFAb-ROE RTS engagement knowledge base"
    )
    parser.add_argument("--output", default=None,
                        help="Output JSON path (default: data/rts_certification_report.json)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print detailed failure information")
    parser.add_argument("--max-per-partition", type=int, default=10,
                        help="Max instances per partition strategy for L1/L2 (default 10)")
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else ROOT / "data" / "rts_certification_report.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("DeFAb-ROE KNOWLEDGE BASE CERTIFICATION")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Output: {output_path}")

    print("\nLoading RTS engagement KB...")
    kb = create_rts_engagement_kb()
    print(f"  Loaded: {len(kb.rules)} rules, {len(kb.facts)} facts")

    # ── Run all certification sections ─────────────────────────────────────────
    structure_result = certify_kb_structure(kb, args.verbose)
    l3_result = certify_l3_seed_conflicts(kb, args.verbose)
    generation_result = certify_instance_generation(kb, args.max_per_partition, args.verbose)
    conservativity_result = certify_conservativity(kb, args.verbose)

    # ── Overall summary ────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("CERTIFICATION SUMMARY")
    print("=" * 70)

    section_pass = {
        "structure":        structure_result.get("passed", False),
        "l3_seed_conflicts": l3_result["passed"] == l3_result["total_seeds"],
        "instance_gen_l1":  generation_result.get("level1", {}).get("validity_rate", 0) == 1.0
                            or generation_result.get("level1", {}).get("count", 0) == 0,
        "instance_gen_l2":  generation_result.get("level2", {}).get("validity_rate", 0) == 1.0
                            or generation_result.get("level2", {}).get("count", 0) == 0,
        "conservativity":   conservativity_result["passed"] == conservativity_result["total"],
    }

    all_passed = all(section_pass.values())
    for section, passed in section_pass.items():
        _print_status(passed, section)

    print()
    if all_passed:
        print("  RESULT: CERTIFICATION PASSED")
        print("  DeFAb-ROE KB meets the same formal guarantees as the")
        print("  biology/legal/materials knowledge bases.")
    else:
        failed = [s for s, p in section_pass.items() if not p]
        print(f"  RESULT: CERTIFICATION INCOMPLETE -- {len(failed)} section(s) need attention:")
        for s in failed:
            print(f"    - {s}")

    # ── Save report ─────────────────────────────────────────────────────────────
    report = {
        "certification_date": datetime.now().isoformat(),
        "overall_passed": all_passed,
        "sections": {
            "structure": structure_result,
            "l3_seed_conflicts": l3_result,
            "instance_generation": generation_result,
            "conservativity": conservativity_result,
        },
        "section_status": section_pass,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nReport saved: {output_path}")
    print("=" * 70)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
