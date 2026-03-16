"""
Rule validation framework for DeFAb knowledge bases.

Validates that a Theory meets the formal requirements defined in
paper.tex: derivation depth, deduplication, consistency, anomaly
structure, and coverage statistics.

Author: Patrick Cooper
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType


@dataclass
class ValidationReport:
    """Results of a full KB validation pass."""

    total_rules: int = 0
    total_facts: int = 0
    strict_rules: int = 0
    defeasible_rules: int = 0
    defeaters: int = 0
    fact_rules: int = 0

    duplicate_count: int = 0
    duplicates: List[str] = field(default_factory=list)

    contradiction_count: int = 0
    contradictions: List[Tuple[str, str]] = field(default_factory=list)

    max_depth: int = 0
    depth_histogram: Dict[int, int] = field(default_factory=dict)
    rules_at_depth_lt2: int = 0

    predicate_count: int = 0
    predicates: Set[str] = field(default_factory=set)
    domain_coverage: Dict[str, int] = field(default_factory=dict)

    anomaly_pairs: int = 0

    @property
    def is_healthy(self) -> bool:
        return (
            self.defeasible_rules > 0
            and self.defeaters > 0
            and self.duplicate_count == 0
        )

    def to_dict(self) -> dict:
        return {
            "total_rules": self.total_rules,
            "total_facts": self.total_facts,
            "strict_rules": self.strict_rules,
            "defeasible_rules": self.defeasible_rules,
            "defeaters": self.defeaters,
            "fact_rules": self.fact_rules,
            "duplicate_count": self.duplicate_count,
            "contradiction_count": self.contradiction_count,
            "max_depth": self.max_depth,
            "depth_histogram": self.depth_histogram,
            "rules_at_depth_lt2": self.rules_at_depth_lt2,
            "predicate_count": self.predicate_count,
            "domain_coverage": self.domain_coverage,
            "anomaly_pairs": self.anomaly_pairs,
            "is_healthy": self.is_healthy,
        }

    def summary(self) -> str:
        lines = [
            "=== KB Validation Report ===",
            f"Rules:       {self.total_rules}  "
            f"(strict={self.strict_rules}, defeasible={self.defeasible_rules}, "
            f"defeaters={self.defeaters}, facts={self.fact_rules})",
            f"Facts:       {self.total_facts}",
            f"Predicates:  {self.predicate_count}",
            f"Max depth:   {self.max_depth}",
            f"Duplicates:  {self.duplicate_count}",
            f"Contradictions (intended): {self.contradiction_count}",
            f"Anomaly pairs:            {self.anomaly_pairs}",
            f"Healthy:     {self.is_healthy}",
        ]
        if self.domain_coverage:
            lines.append("Domain coverage:")
            for domain, count in sorted(self.domain_coverage.items()):
                lines.append(f"  {domain}: {count} rules")
        return "\n".join(lines)


def _extract_predicate(head: str) -> str:
    """Extract the predicate name from a rule head like 'flies(X)'."""
    if "(" in head:
        return head.split("(")[0].lstrip("~")
    return head.lstrip("~")


def _rule_signature(rule: Rule) -> tuple:
    """Canonical signature for deduplication."""
    return (rule.head, rule.body, rule.rule_type)


def validate_theory(theory: Theory) -> ValidationReport:
    """Run all validation checks on a Theory and return a report."""
    report = ValidationReport()

    report.total_rules = len(theory.rules)
    report.total_facts = len(theory.facts)

    # ── Type counts ──────────────────────────────────────────────

    for rule in theory.rules:
        if rule.rule_type == RuleType.STRICT:
            report.strict_rules += 1
        elif rule.rule_type == RuleType.DEFEASIBLE:
            report.defeasible_rules += 1
        elif rule.rule_type == RuleType.DEFEATER:
            report.defeaters += 1
        elif rule.rule_type == RuleType.FACT:
            report.fact_rules += 1

    # ── Deduplication ────────────────────────────────────────────

    seen: Dict[tuple, str] = {}
    for rule in theory.rules:
        sig = _rule_signature(rule)
        if sig in seen:
            report.duplicate_count += 1
            report.duplicates.append(
                f"{rule.label} duplicates {seen[sig]}"
            )
        else:
            seen[sig] = rule.label or str(rule)

    # ── Predicate coverage ───────────────────────────────────────

    preds: Set[str] = set()
    for rule in theory.rules:
        preds.add(_extract_predicate(rule.head))
    report.predicates = preds
    report.predicate_count = len(preds)

    # ── Domain coverage (from metadata) ──────────────────────────

    domain_counts: Dict[str, int] = defaultdict(int)
    for rule in theory.rules:
        if rule.metadata and "domain" in rule.metadata:
            domain_counts[rule.metadata["domain"]] += 1
        elif rule.label:
            if rule.label.startswith("bio_"):
                domain_counts["biology"] += 1
            elif rule.label.startswith("legal_"):
                domain_counts["legal"] += 1
            elif rule.label.startswith("mat_"):
                domain_counts["materials"] += 1
    report.domain_coverage = dict(domain_counts)

    # ── Contradiction detection (intended defeater pairs) ────────

    defeasible_heads: Set[str] = set()
    defeater_heads: Set[str] = set()
    for rule in theory.rules:
        if rule.rule_type == RuleType.DEFEASIBLE:
            defeasible_heads.add(rule.head)
        elif rule.rule_type == RuleType.DEFEATER:
            defeater_heads.add(rule.head)

    for dh in defeater_heads:
        bare = dh.lstrip("~")
        negated = f"~{bare}" if not dh.startswith("~") else bare
        positive = bare if dh.startswith("~") else dh
        pos_pattern = positive
        if pos_pattern in defeasible_heads or any(
            p.startswith(bare.split("(")[0] + "(") for p in defeasible_heads
        ):
            report.contradiction_count += 1
            report.contradictions.append((positive, dh))

    # ── Anomaly pairs (defeater that contradicts an inherited default) ─

    report.anomaly_pairs = report.contradiction_count

    # ── Depth estimation ─────────────────────────────────────────

    head_to_bodies: Dict[str, List[tuple]] = defaultdict(list)
    for rule in theory.rules:
        if rule.body:
            head_to_bodies[rule.head].append(rule.body)

    depths: Dict[str, int] = {}
    for fact in theory.facts:
        depths[fact] = 0

    for rule in theory.rules:
        if rule.is_fact or (rule.rule_type == RuleType.FACT):
            depths[rule.head] = 0

    changed = True
    max_iterations = 50
    iteration = 0
    while changed and iteration < max_iterations:
        changed = False
        iteration += 1
        for rule in theory.rules:
            if not rule.body:
                continue
            body_depth = 0
            all_resolved = True
            for lit in rule.body:
                if lit in depths:
                    body_depth = max(body_depth, depths[lit])
                else:
                    all_resolved = False
                    break
            if all_resolved:
                new_depth = body_depth + 1
                if rule.head not in depths or depths[rule.head] < new_depth:
                    depths[rule.head] = new_depth
                    changed = True

    if depths:
        report.max_depth = max(depths.values())
    histogram: Dict[int, int] = defaultdict(int)
    for d in depths.values():
        histogram[d] += 1
    report.depth_histogram = dict(histogram)

    report.rules_at_depth_lt2 = sum(
        count for depth, count in histogram.items() if depth < 2
    )

    return report


def deduplicate_theory(theory: Theory) -> Theory:
    """Return a copy of the theory with duplicate rules removed."""
    clean = Theory()
    clean.facts = set(theory.facts)
    clean.superiority = dict(theory.superiority)
    clean.metadata = dict(theory.metadata)

    seen: Set[tuple] = set()
    for rule in theory.rules:
        sig = _rule_signature(rule)
        if sig not in seen:
            clean.rules.append(rule)
            seen.add(sig)

    return clean


def save_report(report: ValidationReport, path: Path) -> None:
    """Save a validation report to JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(report.to_dict(), f, indent=2)
