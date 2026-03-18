"""
Tests for SUMO ontology extractor.

Covers KIF tokenization, S-expression parsing, relation extraction
(subclass, instance, domain, contraryAttribute, disjoint), theory
generation with correct rule types, and taxonomy output.

Author: Patrick Cooper
"""

from __future__ import annotations

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.sumo_extractor import (
    SumoExtractor,
    _tokenize_kif,
    _parse_sexpr,
    parse_kif,
    _normalize,
    extract_from_sumo,
)


# ── KIF Tokenizer ────────────────────────────────────────────────


class TestTokenizeKif:

    def test_simple_expr(self):
        tokens = _tokenize_kif("(subclass Dog Animal)")
        assert tokens == ["(", "subclass", "Dog", "Animal", ")"]

    def test_nested_parens(self):
        tokens = _tokenize_kif("(=> (instance ?X Dog) (instance ?X Animal))")
        assert "(" in tokens
        assert tokens.count("(") == 3
        assert tokens.count(")") == 3

    def test_comment_stripped(self):
        text = "; this is a comment\n(subclass Cat Animal)"
        tokens = _tokenize_kif(text)
        assert ";" not in tokens
        assert "comment" not in tokens
        assert tokens == ["(", "subclass", "Cat", "Animal", ")"]

    def test_quoted_string(self):
        tokens = _tokenize_kif('(documentation Dog "A domesticated canine")')
        assert '"A domesticated canine"' in tokens

    def test_escaped_quote_in_string(self):
        tokens = _tokenize_kif(r'(doc "says \"hello\"")')
        assert any('"' in t and "hello" in t for t in tokens)

    def test_empty_input(self):
        assert _tokenize_kif("") == []
        assert _tokenize_kif("   \n\t  ") == []

    def test_whitespace_variants(self):
        tokens = _tokenize_kif("(subclass\tDog\r\nAnimal)")
        assert tokens == ["(", "subclass", "Dog", "Animal", ")"]


# ── S-expression Parser ──────────────────────────────────────────


class TestParseSexpr:

    def test_atom(self):
        val, pos = _parse_sexpr(["foo"], 0)
        assert val == "foo"
        assert pos == 1

    def test_flat_list(self):
        tokens = ["(", "subclass", "Dog", "Animal", ")"]
        val, pos = _parse_sexpr(tokens, 0)
        assert val == ["subclass", "Dog", "Animal"]
        assert pos == 5

    def test_nested_list(self):
        tokens = ["(", "=>", "(", "a", "b", ")", "(", "c", "d", ")", ")"]
        val, _ = _parse_sexpr(tokens, 0)
        assert val == ["=>", ["a", "b"], ["c", "d"]]

    def test_end_of_tokens_raises(self):
        with pytest.raises(ValueError, match="end of tokens"):
            _parse_sexpr([], 0)

    def test_unexpected_close_raises(self):
        with pytest.raises(ValueError, match="closing parenthesis"):
            _parse_sexpr([")"], 0)


# ── Full KIF Parse ────────────────────────────────────────────────


class TestParseKif:

    def test_multiple_top_level(self):
        text = "(subclass Dog Animal)\n(subclass Cat Animal)"
        exprs = parse_kif(text)
        assert len(exprs) == 2
        assert exprs[0] == ["subclass", "Dog", "Animal"]
        assert exprs[1] == ["subclass", "Cat", "Animal"]

    def test_mixed_with_comments(self):
        text = """\
; SUMO concepts
(subclass Dog Animal)
; another comment
(instance Fido Dog)
"""
        exprs = parse_kif(text)
        assert len(exprs) == 2

    def test_stray_close_paren_skipped(self):
        text = ")(subclass A B)"
        exprs = parse_kif(text)
        assert len(exprs) == 1
        assert exprs[0] == ["subclass", "A", "B"]


# ── Normalize ─────────────────────────────────────────────────────


class TestNormalize:

    def test_lowercase(self):
        assert _normalize("Dog") == "dog"

    def test_space_and_hyphen(self):
        assert _normalize("Cell-Division Process") == "cell_division_process"

    def test_leading_digit(self):
        assert _normalize("3DObject") == "c_3dobject"

    def test_variable_passthrough(self):
        assert _normalize("?X") == "?X"
        assert _normalize("@ROW") == "@ROW"


# ── SumoExtractor Init ───────────────────────────────────────────


class TestSumoExtractorInit:

    def test_missing_dir_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            SumoExtractor(tmp_path / "nonexistent")

    def test_no_kif_files_raises(self, tmp_path):
        ext = SumoExtractor(tmp_path)
        with pytest.raises(FileNotFoundError, match="No .kif"):
            ext.load()

    def test_extract_before_load_raises(self, tmp_path):
        (tmp_path / "test.kif").write_text("(subclass A B)")
        ext = SumoExtractor(tmp_path)
        with pytest.raises(ValueError, match="load"):
            ext.extract()


# ── Relation Extraction ──────────────────────────────────────────


def _make_extractor(tmp_path: Path, kif_content: str) -> SumoExtractor:
    (tmp_path / "test.kif").write_text(kif_content, encoding="utf-8")
    ext = SumoExtractor(tmp_path)
    ext.load()
    ext.extract()
    return ext


class TestSubclassExtraction:

    def test_ground_subclass_extracted(self, tmp_path):
        ext = _make_extractor(tmp_path, "(subclass Dog Animal)")
        assert ("Dog", "Animal") in ext.subclass_pairs

    def test_variable_subclass_skipped(self, tmp_path):
        ext = _make_extractor(tmp_path, "(subclass ?X Entity)")
        assert len(ext.subclass_pairs) == 0

    def test_multiple_subclass(self, tmp_path):
        kif = "(subclass Dog Animal)\n(subclass Cat Animal)\n(subclass Poodle Dog)"
        ext = _make_extractor(tmp_path, kif)
        assert len(ext.subclass_pairs) == 3


class TestInstanceExtraction:

    def test_ground_instance(self, tmp_path):
        ext = _make_extractor(tmp_path, "(instance Fido Dog)")
        assert ("Fido", "Dog") in ext.instance_pairs

    def test_variable_instance_skipped(self, tmp_path):
        ext = _make_extractor(tmp_path, "(instance ?X Dog)")
        assert len(ext.instance_pairs) == 0


class TestDomainExtraction:

    def test_domain_triple(self, tmp_path):
        ext = _make_extractor(tmp_path, "(domain employs 1 Organization)")
        assert ("employs", 1, "Organization") in ext.domain_triples

    def test_domain_variable_skipped(self, tmp_path):
        ext = _make_extractor(tmp_path, "(domain ?R 1 ?C)")
        assert len(ext.domain_triples) == 0

    def test_domain_non_integer_arg_skipped(self, tmp_path):
        ext = _make_extractor(tmp_path, "(domain employs foo Organization)")
        assert len(ext.domain_triples) == 0


class TestContraryExtraction:

    def test_binary_contrary(self, tmp_path):
        ext = _make_extractor(tmp_path, "(contraryAttribute Wet Dry)")
        assert ("Wet", "Dry") in ext.contrary_pairs

    def test_ternary_contrary_generates_pairs(self, tmp_path):
        ext = _make_extractor(tmp_path, "(contraryAttribute Hot Warm Cold)")
        pairs = ext.contrary_pairs
        assert ("Hot", "Warm") in pairs
        assert ("Hot", "Cold") in pairs
        assert ("Warm", "Cold") in pairs
        assert len(pairs) == 3


class TestDisjointExtraction:

    def test_disjoint_pair(self, tmp_path):
        ext = _make_extractor(tmp_path, "(disjoint Abstract Physical)")
        assert ("Abstract", "Physical") in ext.disjoint_pairs


# ── Theory Conversion ────────────────────────────────────────────


class TestSumoToTheory:

    def test_subclass_produces_strict_rule(self, tmp_path):
        ext = _make_extractor(tmp_path, "(subclass Dog Animal)")
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1
        assert strict[0].head == "isa(dog, animal)"

    def test_instance_produces_fact(self, tmp_path):
        ext = _make_extractor(tmp_path, "(instance Fido Dog)")
        theory = ext.to_theory()
        assert "instance(fido, dog)" in theory.facts

    def test_domain_produces_defeasible_rule(self, tmp_path):
        ext = _make_extractor(tmp_path, "(domain employs 1 Organization)")
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert "domain_constraint" in defeasible[0].head

    def test_contrary_produces_defeater_pair(self, tmp_path):
        ext = _make_extractor(tmp_path, "(contraryAttribute Wet Dry)")
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) == 2
        heads = {d.head for d in defeaters}
        assert "~dry(X)" in heads
        assert "~wet(X)" in heads

    def test_disjoint_produces_defeater_pair(self, tmp_path):
        ext = _make_extractor(tmp_path, "(disjoint Abstract Physical)")
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) == 2
        heads = {d.head for d in defeaters}
        assert "~isa(X, physical)" in heads
        assert "~isa(X, abstract)" in heads

    def test_metadata_source_is_sumo(self, tmp_path):
        ext = _make_extractor(tmp_path, "(subclass Dog Animal)")
        theory = ext.to_theory()
        for rule in theory.rules:
            if rule.metadata:
                assert rule.metadata["source"] == "SUMO"

    def test_duplicate_subclass_not_repeated(self, tmp_path):
        kif = "(subclass Dog Animal)\n(subclass Dog Animal)"
        ext = _make_extractor(tmp_path, kif)
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 1

    def test_mixed_relations_theory(self, tmp_path):
        kif = "\n".join([
            "(subclass Dog Animal)",
            "(instance Fido Dog)",
            "(domain employs 1 Organization)",
            "(contraryAttribute Wet Dry)",
            "(disjoint Abstract Physical)",
        ])
        ext = _make_extractor(tmp_path, kif)
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEATER)) == 4
        assert "instance(fido, dog)" in theory.facts


# ── Taxonomy ──────────────────────────────────────────────────────


class TestSumoGetTaxonomy:

    def test_taxonomy_structure(self, tmp_path):
        kif = "(subclass Dog Animal)\n(subclass Cat Animal)\n(subclass Poodle Dog)"
        ext = _make_extractor(tmp_path, kif)
        tax = ext.get_taxonomy()
        assert tax["Dog"] == {"Animal"}
        assert tax["Cat"] == {"Animal"}
        assert tax["Poodle"] == {"Dog"}
        assert "Animal" not in tax

    def test_taxonomy_multiple_parents(self, tmp_path):
        kif = "(subclass Bat Mammal)\n(subclass Bat FlyingAnimal)"
        ext = _make_extractor(tmp_path, kif)
        tax = ext.get_taxonomy()
        assert tax["Bat"] == {"Mammal", "FlyingAnimal"}


# ── Convenience Function ─────────────────────────────────────────


class TestExtractFromSumo:

    def test_convenience_function_missing_dir(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_sumo(tmp_path / "nonexistent")

    def test_convenience_function_roundtrip(self, tmp_path):
        (tmp_path / "test.kif").write_text(
            "(subclass Dog Animal)\n(instance Fido Dog)"
        )
        theory = extract_from_sumo(tmp_path)
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 1
        assert "instance(fido, dog)" in theory.facts
