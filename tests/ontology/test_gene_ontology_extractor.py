"""
Tests for Gene Ontology extractor.

Covers OBO ontology parsing (terms, is_a, obsolete filtering), GAF
annotation parsing (positive and NOT-qualified), evidence code filtering,
gzipped GAF support, theory generation with strict/defeasible/defeater
rule types, and taxonomy output.

Author: Anonymous Authors
"""

from __future__ import annotations

import gzip
import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.ontology.gene_ontology_extractor import (
    GeneOntologyExtractor,
    extract_from_gene_ontology,
)


# ── Synthetic Data Helpers ────────────────────────────────────────

MINIMAL_OBO = """\
format-version: 1.2
ontology: go

[Term]
id: GO:0008150
name: biological_process
namespace: biological_process

[Term]
id: GO:0009987
name: cellular process
namespace: biological_process
is_a: GO:0008150 ! biological_process

[Term]
id: GO:0006915
name: apoptotic process
namespace: biological_process
is_a: GO:0009987 ! cellular process

[Term]
id: GO:0000001
name: obsolete term
namespace: biological_process
is_obsolete: true
"""

OBO_MULTI_PARENT = """\
format-version: 1.2

[Term]
id: GO:0000010
name: root_a
namespace: biological_process

[Term]
id: GO:0000020
name: root_b
namespace: molecular_function

[Term]
id: GO:0000030
name: multi_parent_child
namespace: biological_process
is_a: GO:0000010 ! root_a
is_a: GO:0000020 ! root_b
"""


def _write_obo(tmp_path: Path, content: str, name: str = "test.obo") -> Path:
    obo_path = tmp_path / name
    obo_path.write_text(content, encoding="utf-8")
    return obo_path


def _make_gaf_line(
    gene: str,
    go_id: str,
    qualifier: str = "",
    evidence: str = "IDA",
) -> str:
    cols = [
        "UniProtKB",     # 0  DB
        "P12345",        # 1  DB Object ID
        gene,            # 2  DB Object Symbol
        qualifier,       # 3  Qualifier
        go_id,           # 4  GO ID
        "PMID:1234",     # 5  DB:Reference
        evidence,        # 6  Evidence Code
        "",              # 7  With/From
        "P",             # 8  Aspect
        "Some protein",  # 9  DB Object Name
        "",              # 10 DB Object Synonym
        "protein",       # 11 DB Object Type
        "taxon:9606",    # 12 Taxon
        "20200101",      # 13 Date
        "UniProt",       # 14 Assigned By
    ]
    return "\t".join(cols)


def _write_gaf(
    tmp_path: Path,
    lines: list[str],
    name: str = "test.gaf",
    compress: bool = False,
) -> Path:
    content = "!header comment\n" + "\n".join(lines) + "\n"
    if compress:
        gaf_path = tmp_path / (name + ".gz")
        with gzip.open(gaf_path, "wt", encoding="utf-8") as fh:
            fh.write(content)
    else:
        gaf_path = tmp_path / name
        gaf_path.write_text(content, encoding="utf-8")
    return gaf_path


# ── Init ──────────────────────────────────────────────────────────


class TestGeneOntologyInit:

    def test_missing_obo_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            GeneOntologyExtractor(tmp_path / "nonexistent.obo")

    def test_default_gaf_paths_empty(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        assert ext.gaf_paths == []


# ── OBO Parsing ───────────────────────────────────────────────────


class TestOBOParsing:

    def test_terms_loaded(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert "GO:0008150" in ext.terms
        assert "GO:0009987" in ext.terms
        assert "GO:0006915" in ext.terms
        assert ext.terms["GO:0009987"]["name"] == "cellular process"

    def test_obsolete_term_skipped(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert "GO:0000001" not in ext.terms

    def test_isa_edges(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert ("GO:0009987", "GO:0008150") in ext.isa_edges
        assert ("GO:0006915", "GO:0009987") in ext.isa_edges

    def test_multiple_isa_parents(self, tmp_path):
        obo = _write_obo(tmp_path, OBO_MULTI_PARENT)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        parents = [p for c, p in ext.isa_edges if c == "GO:0000030"]
        assert "GO:0000010" in parents
        assert "GO:0000020" in parents

    def test_term_count_excludes_obsolete(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert len(ext.terms) == 3

    def test_namespace_stored(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert ext.terms["GO:0008150"]["namespace"] == "biological_process"


# ── GAF Parsing ───────────────────────────────────────────────────


class TestGAFParsing:

    def test_positive_annotation(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.positive_annotations) == 1
        assert ext.positive_annotations[0][0] == "TP53"
        assert ext.positive_annotations[0][1] == "GO:0006915"

    def test_negative_annotation(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("BRCA1", "GO:0006915", qualifier="NOT")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 1
        assert ext.negative_annotations[0][0] == "BRCA1"

    def test_not_qualifier_case_insensitive(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("GENE1", "GO:0006915", qualifier="not")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 1

    def test_comment_lines_skipped(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.positive_annotations) == 1

    def test_gaf_missing_file_raises(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        with pytest.raises(FileNotFoundError):
            ext.load_annotations(tmp_path / "nonexistent.gaf")


# ── Gzipped GAF ───────────────────────────────────────────────────


class TestGzippedGAF:

    def test_gzipped_gaf_parsed(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("TP53", "GO:0006915"),
            _make_gaf_line("BRCA1", "GO:0009987", qualifier="NOT"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines, compress=True)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.positive_annotations) == 1
        assert len(ext.negative_annotations) == 1


# ── Evidence Code Filtering ──────────────────────────────────────


class TestEvidenceCodeFiltering:

    def test_nd_evidence_excluded_for_negative(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("GENE1", "GO:0006915", qualifier="NOT", evidence="ND"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 0

    def test_iea_evidence_excluded_for_negative(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("GENE1", "GO:0006915", qualifier="NOT", evidence="IEA"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 0

    def test_nd_evidence_kept_for_positive(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("GENE1", "GO:0006915", evidence="ND"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.positive_annotations) == 1

    def test_ida_evidence_kept_for_negative(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("GENE1", "GO:0006915", qualifier="NOT", evidence="IDA"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 1

    def test_mixed_evidence_filtering(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("G1", "GO:0006915", qualifier="NOT", evidence="IDA"),
            _make_gaf_line("G2", "GO:0006915", qualifier="NOT", evidence="ND"),
            _make_gaf_line("G3", "GO:0006915", qualifier="NOT", evidence="IEA"),
            _make_gaf_line("G4", "GO:0006915", qualifier="NOT", evidence="TAS"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        assert len(ext.negative_annotations) == 2
        genes = {a[0] for a in ext.negative_annotations}
        assert genes == {"G1", "G4"}


# ── Full Extraction Pipeline ─────────────────────────────────────


class TestExtractPipeline:

    def test_extract_loads_ontology_if_not_loaded(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.extract()
        assert len(ext.terms) > 0

    def test_extract_loads_configured_gaf(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo, gaf_paths=[gaf_path])
        ext.extract()
        assert len(ext.positive_annotations) == 1


# ── Theory Conversion ────────────────────────────────────────────


class TestGOToTheory:

    def test_isa_produces_strict_rule(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        theory = ext.to_theory()
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 2
        heads = {r.head for r in strict}
        assert "isa(go_0009987, go_0008150)" in heads
        assert "isa(go_0006915, go_0009987)" in heads

    def test_positive_annotation_produces_defeasible(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915", evidence="IDA")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible) == 1
        assert "has_function(tp53, go_0006915)" == defeasible[0].head

    def test_negative_annotation_produces_defeater(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("BRCA1", "GO:0006915", qualifier="NOT")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        theory = ext.to_theory()
        defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
        assert len(defeaters) == 1
        assert "~has_function(brca1, go_0006915)" == defeaters[0].head

    def test_metadata_source(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        theory = ext.to_theory()
        for rule in theory.rules:
            assert rule.metadata.get("source") == "GeneOntology"

    def test_metadata_evidence_on_annotations(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915", evidence="IDA")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        assert defeasible[0].metadata["evidence"] == "IDA"

    def test_duplicate_annotations_not_repeated(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("TP53", "GO:0006915", evidence="IDA"),
            _make_gaf_line("TP53", "GO:0006915", evidence="TAS"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        theory = ext.to_theory()
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        tp53_rules = [r for r in defeasible
                      if "tp53" in r.head and "go_0006915" in r.head]
        assert len(tp53_rules) == 1

    def test_mixed_theory(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [
            _make_gaf_line("TP53", "GO:0006915"),
            _make_gaf_line("BRCA1", "GO:0009987", qualifier="NOT"),
        ]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        ext.load_annotations(gaf_path)
        theory = ext.to_theory()
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 2
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1
        assert len(theory.get_rules_by_type(RuleType.DEFEATER)) == 1


# ── Taxonomy ──────────────────────────────────────────────────────


class TestGOGetTaxonomy:

    def test_taxonomy_structure(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        tax = ext.get_taxonomy()
        assert "GO:0008150" in tax.get("GO:0009987", set())
        assert "GO:0009987" in tax.get("GO:0006915", set())
        assert "GO:0008150" not in tax

    def test_multiple_parents_taxonomy(self, tmp_path):
        obo = _write_obo(tmp_path, OBO_MULTI_PARENT)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        tax = ext.get_taxonomy()
        parents = tax.get("GO:0000030", set())
        assert "GO:0000010" in parents
        assert "GO:0000020" in parents


# ── Normalization Helpers ─────────────────────────────────────────


class TestGONormalization:

    def test_go_id_normalization(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        assert ext._normalize_go_id("GO:0008150") == "go_0008150"

    def test_name_normalization(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        assert ext._normalize_name("TP53") == "tp53"
        assert ext._normalize_name("alpha-beta") == "alpha_beta"
        assert ext._normalize_name("Cell Cycle") == "cell_cycle"

    def test_term_label_known(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert ext._term_label("GO:0008150") == "biological_process"

    def test_term_label_unknown_returns_id(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        ext = GeneOntologyExtractor(obo)
        ext.load_ontology()
        assert ext._term_label("GO:9999999") == "GO:9999999"


# ── Convenience Function ─────────────────────────────────────────


class TestExtractFromGeneOntology:

    def test_missing_obo_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_from_gene_ontology(tmp_path / "nonexistent.obo")

    def test_obo_only_roundtrip(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        theory = extract_from_gene_ontology(obo)
        strict = theory.get_rules_by_type(RuleType.STRICT)
        assert len(strict) == 2

    def test_with_gaf_roundtrip(self, tmp_path):
        obo = _write_obo(tmp_path, MINIMAL_OBO)
        gaf_lines = [_make_gaf_line("TP53", "GO:0006915")]
        gaf_path = _write_gaf(tmp_path, gaf_lines)
        theory = extract_from_gene_ontology(obo, gaf_paths=[gaf_path])
        assert len(theory.get_rules_by_type(RuleType.STRICT)) == 2
        assert len(theory.get_rules_by_type(RuleType.DEFEASIBLE)) == 1
