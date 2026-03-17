"""
SUMO (Suggested Upper Merged Ontology) extraction for defeasible knowledge bases.

Parses SUO-KIF format (.kif) files from the SUMO ontology
(https://github.com/ontologyportal/sumo) and extracts taxonomic relations,
type constraints, and mutual-exclusion defeaters.

Primary source files: Merge.kif, Mid-level-ontology.kif.

Author: Patrick Cooper
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from blanc.core.theory import Theory, Rule, RuleType


def _tokenize_kif(text: str) -> List[str]:
    """Tokenize a KIF string into parentheses, quoted strings, and atoms."""
    tokens: List[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch in " \t\r\n":
            i += 1
        elif ch == ";":
            while i < n and text[i] != "\n":
                i += 1
        elif ch in "()" :
            tokens.append(ch)
            i += 1
        elif ch == '"':
            j = i + 1
            while j < n and text[j] != '"':
                if text[j] == "\\":
                    j += 1
                j += 1
            tokens.append(text[i : j + 1])
            i = j + 1
        else:
            j = i
            while j < n and text[j] not in " \t\r\n();\"":
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def _parse_sexpr(tokens: List[str], pos: int) -> Tuple[object, int]:
    """Parse one S-expression from *tokens* starting at *pos*.

    Returns (parsed_value, next_position).  Lists become Python lists;
    atoms remain as strings.
    """
    if pos >= len(tokens):
        raise ValueError("Unexpected end of tokens")

    tok = tokens[pos]

    if tok == "(":
        result: List[object] = []
        pos += 1
        while pos < len(tokens) and tokens[pos] != ")":
            child, pos = _parse_sexpr(tokens, pos)
            result.append(child)
        if pos < len(tokens):
            pos += 1  # skip closing paren
        return result, pos

    if tok == ")":
        raise ValueError("Unexpected closing parenthesis")

    return tok, pos + 1


def parse_kif(text: str) -> List[object]:
    """Parse all top-level S-expressions in a KIF source string."""
    tokens = _tokenize_kif(text)
    exprs: List[object] = []
    pos = 0
    while pos < len(tokens):
        if tokens[pos] == ")":
            pos += 1
            continue
        expr, pos = _parse_sexpr(tokens, pos)
        exprs.append(expr)
    return exprs


def _normalize(name: str) -> str:
    """Normalize a SUMO concept name for use in logic programs."""
    if name.startswith("?") or name.startswith("@"):
        return name
    name = name.lower().replace(" ", "_").replace("-", "_")
    name = "".join(c for c in name if c.isalnum() or c == "_")
    if name and not name[0].isalpha():
        name = "c_" + name
    return name


class SumoExtractor:
    """Extract defeasible knowledge from the SUMO ontology.

    SUMO ships as a collection of .kif files written in SUO-KIF, a
    Lisp-like S-expression language.  The extractor reads every .kif
    file under *sumo_dir*, parses the S-expressions, and maps selected
    relation types to strict rules, defeasible rules, and defeaters.

    Mapping:
        (subclass ?X ?Y)         -> strict taxonomic rule
        (instance ?X ?Y)         -> ground fact
        (domain ?REL ?N ?CLASS)  -> defeasible type constraint
        (contraryAttribute A B)  -> defeater (mutual exclusion)
        (disjoint ?X ?Y)         -> defeater (disjoint classes)
    """

    _SOURCE = "SUMO"

    def __init__(self, sumo_dir: Path):
        if not sumo_dir.is_dir():
            raise FileNotFoundError(f"SUMO directory not found: {sumo_dir}")

        self.sumo_dir = sumo_dir
        self._exprs: List[object] = []

        self.subclass_pairs: List[Tuple[str, str]] = []
        self.instance_pairs: List[Tuple[str, str]] = []
        self.domain_triples: List[Tuple[str, int, str]] = []
        self.contrary_pairs: List[Tuple[str, str]] = []
        self.disjoint_pairs: List[Tuple[str, str]] = []

    # ── Loading ───────────────────────────────────────────────────

    def load(self) -> None:
        """Read and parse all .kif files under *sumo_dir*."""
        kif_files = sorted(self.sumo_dir.glob("*.kif"))
        if not kif_files:
            raise FileNotFoundError(
                f"No .kif files found in {self.sumo_dir}"
            )

        all_exprs: List[object] = []
        for path in kif_files:
            text = path.read_text(encoding="utf-8", errors="replace")
            all_exprs.extend(parse_kif(text))

        self._exprs = all_exprs

    # ── Extraction ────────────────────────────────────────────────

    def extract(self) -> None:
        """Walk parsed S-expressions and populate relation lists."""
        if not self._exprs:
            raise ValueError("Must call load() first")

        for expr in self._exprs:
            if not isinstance(expr, list) or len(expr) < 3:
                continue

            rel = expr[0]

            if rel == "subclass" and len(expr) == 3:
                child, parent = str(expr[1]), str(expr[2])
                if not child.startswith("?") and not parent.startswith("?"):
                    self.subclass_pairs.append((child, parent))

            elif rel == "instance" and len(expr) == 3:
                inst, cls = str(expr[1]), str(expr[2])
                if not inst.startswith("?") and not cls.startswith("?"):
                    self.instance_pairs.append((inst, cls))

            elif rel == "domain" and len(expr) == 4:
                relation = str(expr[1])
                try:
                    arg_pos = int(expr[2])
                except (ValueError, TypeError):
                    continue
                cls = str(expr[3])
                if not relation.startswith("?") and not cls.startswith("?"):
                    self.domain_triples.append((relation, arg_pos, cls))

            elif rel == "contraryAttribute" and len(expr) >= 3:
                attrs = [str(a) for a in expr[1:] if not str(a).startswith("?")]
                for i, a in enumerate(attrs):
                    for b in attrs[i + 1 :]:
                        self.contrary_pairs.append((a, b))

            elif rel == "disjoint" and len(expr) == 3:
                cls_a, cls_b = str(expr[1]), str(expr[2])
                if not cls_a.startswith("?") and not cls_b.startswith("?"):
                    self.disjoint_pairs.append((cls_a, cls_b))

    # ── Conversion ────────────────────────────────────────────────

    def to_theory(self) -> Theory:
        """Build a ``Theory`` from the extracted SUMO relations.

        Returns:
            Theory containing strict taxonomy, defeasible type constraints,
            ground instance facts, and mutual-exclusion defeaters.
        """
        theory = Theory()
        added: Set[tuple] = set()

        for child, parent in self.subclass_pairs:
            cn, pn = _normalize(child), _normalize(parent)
            key = ("subclass", cn, pn)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"isa({cn}, {pn})",
                    body=(),
                    rule_type=RuleType.STRICT,
                    label=f"tax_{cn}_{pn}",
                    metadata={"source": self._SOURCE, "relation": "subclass"},
                ))
                added.add(key)

        for inst, cls in self.instance_pairs:
            in_norm, cn = _normalize(inst), _normalize(cls)
            fact = f"instance({in_norm}, {cn})"
            if fact not in theory.facts:
                theory.add_fact(fact)

        for relation, arg_pos, cls in self.domain_triples:
            rn, cn = _normalize(relation), _normalize(cls)
            key = ("domain", rn, arg_pos, cn)
            if key not in added:
                theory.add_rule(Rule(
                    head=f"domain_constraint({rn}, {cn})",
                    body=(f"arg{arg_pos}({rn}, X)", f"isa(X, {cn})"),
                    rule_type=RuleType.DEFEASIBLE,
                    label=f"dom_{rn}_{arg_pos}_{cn}",
                    metadata={"source": self._SOURCE, "relation": "domain",
                              "arg_position": arg_pos},
                ))
                added.add(key)

        for a, b in self.contrary_pairs:
            an, bn = _normalize(a), _normalize(b)
            key = ("contrary", an, bn)
            rev = ("contrary", bn, an)
            if key not in added and rev not in added:
                theory.add_rule(Rule(
                    head=f"~{bn}(X)",
                    body=(f"{an}(X)",),
                    rule_type=RuleType.DEFEATER,
                    label=f"contrary_{an}_{bn}",
                    metadata={"source": self._SOURCE,
                              "relation": "contraryAttribute"},
                ))
                theory.add_rule(Rule(
                    head=f"~{an}(X)",
                    body=(f"{bn}(X)",),
                    rule_type=RuleType.DEFEATER,
                    label=f"contrary_{bn}_{an}",
                    metadata={"source": self._SOURCE,
                              "relation": "contraryAttribute"},
                ))
                added.add(key)

        for cls_a, cls_b in self.disjoint_pairs:
            an, bn = _normalize(cls_a), _normalize(cls_b)
            key = ("disjoint", an, bn)
            rev = ("disjoint", bn, an)
            if key not in added and rev not in added:
                theory.add_rule(Rule(
                    head=f"~isa(X, {bn})",
                    body=(f"isa(X, {an})",),
                    rule_type=RuleType.DEFEATER,
                    label=f"disjoint_{an}_{bn}",
                    metadata={"source": self._SOURCE, "relation": "disjoint"},
                ))
                theory.add_rule(Rule(
                    head=f"~isa(X, {an})",
                    body=(f"isa(X, {bn})",),
                    rule_type=RuleType.DEFEATER,
                    label=f"disjoint_{bn}_{an}",
                    metadata={"source": self._SOURCE, "relation": "disjoint"},
                ))
                added.add(key)

        return theory

    def get_taxonomy(self) -> Dict[str, Set[str]]:
        """Return concept -> {parents} mapping for the cross-ontology combiner."""
        taxonomy: Dict[str, Set[str]] = defaultdict(set)
        for child, parent in self.subclass_pairs:
            taxonomy[child].add(parent)
        return dict(taxonomy)


# ── Convenience function ──────────────────────────────────────────

def extract_from_sumo(
    sumo_dir: Optional[Path] = None,
) -> Theory:
    """Extract a defeasible theory from the SUMO ontology.

    Args:
        sumo_dir: Directory containing SUMO .kif files.
                  Defaults to ``data/sumo/`` relative to the project root.

    Returns:
        Theory with taxonomic, constraint, and exclusion rules.
    """
    if sumo_dir is None:
        sumo_dir = (
            Path(__file__).parent.parent.parent.parent
            / "data"
            / "sumo"
        )

    extractor = SumoExtractor(sumo_dir)
    extractor.load()
    extractor.extract()
    return extractor.to_theory()
