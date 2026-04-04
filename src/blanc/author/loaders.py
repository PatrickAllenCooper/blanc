"""
Instance loaders for DeFAb -- shared between symbolic_baseline.py,
prepare_preference_data.py, and other experiment scripts.

Provides load_instances_from_json() which reads both Level 2 and Level 3
instance files and returns a list of AbductiveInstance objects with the same
field layout as run_evaluation.py.

Author: Patrick Cooper
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from blanc.author.generation import AbductiveInstance
from blanc.core.theory import Theory, Rule, RuleType


# ---------------------------------------------------------------------------
# Internal helpers (mirrors run_evaluation.py logic)
# ---------------------------------------------------------------------------

def _build_placeholder_theory(item: dict) -> Theory:
    meta = item.get("metadata", {})
    facts = meta.get("facts", [])
    rules_raw = meta.get("rules", [])
    rules = []
    for r in rules_raw:
        if isinstance(r, dict):
            rules.append(Rule(
                head=r.get("head", ""),
                body=tuple(r.get("body", [])),
                rule_type=RuleType(r.get("rule_type", "defeasible")),
                label=r.get("label"),
            ))
    return Theory(facts=set(facts), rules=rules, superiority={})


def _reconstruct_theory_from_level3(item: dict) -> Theory:
    facts = list(item.get("theory_facts", []))
    rules: list[Rule] = []

    for rule_str in item.get("theory_rules", []):
        if ":" in rule_str:
            label, rest = rule_str.split(":", 1)
            label, rest = label.strip(), rest.strip()
        else:
            label, rest = None, rule_str.strip()

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
            rules.append(Rule(head=rest.strip(), body=(), rule_type=RuleType.STRICT, label=label))
            continue

        body_atoms = tuple(b.strip() for b in body_part.split(",") if b.strip())
        rules.append(Rule(head=head_part.strip(), body=body_atoms, rule_type=rule_type, label=label))

    return Theory(facts=set(facts), rules=rules, superiority={})


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def load_level2_instances(
    domain: str,
    instances_dir: Path,
    limit: Optional[int] = None,
) -> list[AbductiveInstance]:
    """Load Level 2 (rule abduction) instances for *domain* from JSON."""
    path = instances_dir / f"{domain}_dev_instances.json"
    if not path.exists():
        return []

    with open(path) as f:
        data = json.load(f)

    raw = data["instances"]
    if limit is not None:
        raw = raw[:limit]

    instances = []
    for i, item in enumerate(raw):
        D_minus = _build_placeholder_theory(item)
        inst = AbductiveInstance(
            D_minus=D_minus,
            target=item.get("target", ""),
            candidates=item.get("candidates", []),
            gold=item.get("gold", []),
            level=item.get("level", 2),
            metadata=item.get("metadata", {}),
        )
        inst.id = item.get("metadata", {}).get("instance_id", f"{domain}-l2-{i+1:04d}")
        instances.append(inst)

    return instances


def load_level3_instances(
    instances_dir: Path,
    limit: Optional[int] = None,
) -> list[AbductiveInstance]:
    """Load Level 3 (defeater abduction) instances from level3_instances.json."""
    path = instances_dir / "level3_instances.json"
    if not path.exists():
        return []

    with open(path) as f:
        data = json.load(f)

    raw = data["instances"]
    if limit is not None:
        raw = raw[:limit]

    instances = []
    for item in raw:
        D_minus = _reconstruct_theory_from_level3(item)
        inst = AbductiveInstance(
            D_minus=D_minus,
            target=item["anomaly"],
            candidates=item["candidates"],
            gold=[item["gold"]],
            level=3,
            metadata={
                "domain":       item.get("domain", ""),
                "nov":          item.get("nov", 0.0),
                "d_rev":        item.get("d_rev", 1),
                "conservative": item.get("conservative", True),
            },
        )
        inst.id = f"l3-{item['name']}"
        instances.append(inst)

    return instances


def load_instances_from_json(
    instances_dir: Path | str,
    domains: Optional[list[str]] = None,
    include_level3: bool = True,
    level2_limit: Optional[int] = None,
    level3_limit: Optional[int] = None,
) -> list[AbductiveInstance]:
    """
    Load all DeFAb instances from *instances_dir*.

    Parameters
    ----------
    instances_dir   : directory containing *_dev_instances.json and
                      level3_instances.json files.
    domains         : list of domain names; defaults to
                      ["biology", "legal", "materials"].
    include_level3  : whether to include Level 3 instances.
    level2_limit    : per-domain limit for Level 2 instances.
    level3_limit    : total limit for Level 3 instances.
    """
    instances_dir = Path(instances_dir)
    if domains is None:
        domains = ["biology", "legal", "materials"]

    instances: list[AbductiveInstance] = []

    for domain in domains:
        instances.extend(load_level2_instances(domain, instances_dir, level2_limit))

    if include_level3:
        instances.extend(load_level3_instances(instances_dir, level3_limit))

    return instances
