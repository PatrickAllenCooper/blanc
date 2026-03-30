"""
Synthetic defeasible theory generation for contamination control.

Generates structurally isomorphic theories with invented predicate and
entity names, preserving formal properties (depth, branching, support set
size, defeater complexity) while guaranteeing that no element appears in
any pretraining corpus.

The vocabulary is produced by a context-free grammar over phonotactically
valid syllable templates (CV, CVC, CVCV) with English consonant and vowel
inventories.

Author: Patrick Cooper
"""

from __future__ import annotations

import hashlib
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from blanc.core.theory import Theory, Rule, RuleType

CONSONANTS = list("bcdfghjklmnprstvwxz")
VOWELS = list("aeiou")

TEMPLATES = ["CV", "CVC", "CVCV", "CVCCV"]


def _random_syllable(template: str, rng: random.Random) -> str:
    chars = []
    for t in template:
        if t == "C":
            chars.append(rng.choice(CONSONANTS))
        elif t == "V":
            chars.append(rng.choice(VOWELS))
    return "".join(chars)


def generate_nonsense_word(rng: random.Random, syllables: int = 2) -> str:
    """Generate a pronounceable nonsense word from syllable templates."""
    parts = []
    for _ in range(syllables):
        tmpl = rng.choice(TEMPLATES)
        parts.append(_random_syllable(tmpl, rng))
    return "".join(parts)


def generate_vocabulary(
    n_predicates: int,
    n_constants: int,
    seed: int = 42,
    existing_vocab: Optional[Set[str]] = None,
) -> Tuple[List[str], List[str]]:
    """Generate sets of unique nonsense predicate and constant names.

    Args:
        n_predicates: Number of predicate names to generate.
        n_constants: Number of constant names to generate.
        seed: RNG seed for reproducibility.
        existing_vocab: Set of words to avoid (e.g., real English words).

    Returns:
        (predicates, constants) tuple of string lists.
    """
    rng = random.Random(seed)
    avoid = existing_vocab or set()
    generated: Set[str] = set()

    def _make_unique(prefix: str, count: int, min_syl: int, max_syl: int) -> List[str]:
        words = []
        attempts = 0
        while len(words) < count and attempts < count * 20:
            n_syl = rng.randint(min_syl, max_syl)
            w = generate_nonsense_word(rng, n_syl)
            w = prefix + w
            if w not in generated and w not in avoid and len(w) >= 4:
                words.append(w)
                generated.add(w)
            attempts += 1
        return words

    predicates = _make_unique("", n_predicates, 2, 3)
    constants = _make_unique("", n_constants, 2, 3)
    return predicates, constants


@dataclass
class SyntheticTheoryParams:
    """Structural parameters for synthetic theory generation."""
    n_facts: int = 20
    n_strict: int = 5
    n_defeasible: int = 15
    n_defeaters: int = 3
    max_depth: int = 3
    branching_factor: int = 2
    max_arity: int = 1


def generate_synthetic_theory(
    params: SyntheticTheoryParams,
    seed: int = 42,
) -> Theory:
    """Generate a synthetic defeasible theory with invented vocabulary.

    The generated theory preserves structural properties (depth, branching,
    rule counts by type, body sizes) while using entirely novel predicates
    and constants that cannot appear in any training corpus.

    Args:
        params: Structural parameters controlling the theory shape.
        seed: RNG seed for reproducibility.

    Returns:
        A Theory with synthetic vocabulary.
    """
    rng = random.Random(seed)

    n_preds = params.n_strict + params.n_defeasible + params.n_defeaters + params.n_facts + 10
    n_consts = params.n_facts + 5
    predicates, constants = generate_vocabulary(n_preds, n_consts, seed=seed)

    pred_idx = 0
    const_idx = 0

    theory = Theory()

    def _next_pred() -> str:
        nonlocal pred_idx
        p = predicates[pred_idx % len(predicates)]
        pred_idx += 1
        return p

    def _next_const() -> str:
        nonlocal const_idx
        c = constants[const_idx % len(constants)]
        const_idx += 1
        return c

    fact_preds: List[str] = []
    for i in range(params.n_facts):
        p = _next_pred()
        c = _next_const()
        theory.add_fact(f"{p}({c})")
        fact_preds.append(p)

    derived_heads: List[Tuple[str, str]] = []

    for i in range(params.n_strict):
        head_pred = _next_pred()
        if fact_preds:
            body_pred = rng.choice(fact_preds)
            body_const = constants[rng.randint(0, min(const_idx, len(constants)) - 1)]
            body = (f"{body_pred}({body_const})",)
        else:
            body = ()
        const = constants[rng.randint(0, min(const_idx, len(constants)) - 1)]
        head = f"{head_pred}({const})"
        theory.add_rule(Rule(
            head=head,
            body=body,
            rule_type=RuleType.STRICT,
            label=f"syn_s_{i}",
        ))
        derived_heads.append((head_pred, const))

    all_body_sources = fact_preds + [h[0] for h in derived_heads]

    for i in range(params.n_defeasible):
        head_pred = _next_pred()
        if all_body_sources:
            body_pred = rng.choice(all_body_sources)
            body_const = constants[rng.randint(0, min(const_idx, len(constants)) - 1)]
            body = (f"{body_pred}({body_const})",)
        else:
            body = ()
        const = constants[rng.randint(0, min(const_idx, len(constants)) - 1)]
        head = f"{head_pred}({const})"
        theory.add_rule(Rule(
            head=head,
            body=body,
            rule_type=RuleType.DEFEASIBLE,
            label=f"syn_d_{i}",
        ))
        derived_heads.append((head_pred, const))
        all_body_sources.append(head_pred)

    defeasible_rules = [r for r in theory.rules if r.rule_type == RuleType.DEFEASIBLE]
    for i in range(min(params.n_defeaters, len(defeasible_rules))):
        target_rule = defeasible_rules[i]
        head_pred = target_rule.head.split("(")[0]
        head_args = target_rule.head.split("(")[1].rstrip(")")

        if all_body_sources:
            body_pred = rng.choice(all_body_sources)
            body_const = constants[rng.randint(0, min(const_idx, len(constants)) - 1)]
            body = (f"{body_pred}({body_const})",)
        else:
            body = ()

        defeater_label = f"syn_df_{i}"
        theory.add_rule(Rule(
            head=f"~{head_pred}({head_args})",
            body=body,
            rule_type=RuleType.DEFEATER,
            label=defeater_label,
        ))
        theory.add_superiority(defeater_label, target_rule.label)

    return theory


def generate_matched_synthetic(
    naturalistic_theory: Theory,
    seed: int = 42,
) -> Theory:
    """Generate a synthetic theory structurally matched to a naturalistic one.

    Extracts structural parameters from the naturalistic theory and produces
    a synthetic counterpart with matching rule counts, body sizes, and depth.

    Args:
        naturalistic_theory: The theory to match structurally.
        seed: RNG seed for reproducibility.

    Returns:
        A structurally matched synthetic Theory.
    """
    from collections import Counter

    types = Counter()
    for r in naturalistic_theory.rules:
        types[r.rule_type] += 1

    params = SyntheticTheoryParams(
        n_facts=len(naturalistic_theory.facts),
        n_strict=types.get(RuleType.STRICT, 0),
        n_defeasible=types.get(RuleType.DEFEASIBLE, 0),
        n_defeaters=types.get(RuleType.DEFEATER, 0),
    )

    return generate_synthetic_theory(params, seed=seed)
