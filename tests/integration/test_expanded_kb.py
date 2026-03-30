"""
End-to-end integration tests for the expanded KB pipeline.

Tests the full flow: extract -> combine -> validate -> report,
using synthetic data (no raw data downloads required).

Author: Patrick Cooper
"""

import gzip
import json
import tempfile
from pathlib import Path

import pytest

from blanc.core.theory import Theory, Rule, RuleType
from blanc.ontology.domain_profiles import BIOLOGY, LEGAL, MATERIALS
from blanc.ontology.cross_ontology import (
    combine_taxonomy_properties,
    build_cross_ontology_theory,
)
from blanc.ontology.rule_validator import (
    validate_theory,
    deduplicate_theory,
    save_report,
)


class TestCrossOntologyToValidation:
    """End-to-end: taxonomy + properties -> combined theory -> validation."""

    def _biology_taxonomy(self):
        return {
            "penguin": {"bird"},
            "sparrow": {"bird"},
            "eagle": {"bird"},
            "bird": {"animal"},
            "whale": {"mammal"},
            "dolphin": {"mammal"},
            "dog": {"mammal"},
            "mammal": {"animal"},
            "salmon": {"fish"},
            "fish": {"animal"},
            "animal": set(),
        }

    def _biology_properties(self):
        return {
            "bird": [
                ("CapableOf", "fly"),
                ("HasProperty", "feathers"),
                ("CapableOf", "sing"),
            ],
            "penguin": [
                ("NotCapableOf", "fly"),
                ("CapableOf", "swim"),
            ],
            "mammal": [
                ("CapableOf", "walk"),
                ("HasProperty", "fur"),
            ],
            "whale": [
                ("NotCapableOf", "walk"),
                ("CapableOf", "swim"),
            ],
            "fish": [
                ("CapableOf", "swim"),
                ("HasProperty", "scales"),
            ],
            "animal": [
                ("CapableOf", "move"),
                ("CapableOf", "eat"),
            ],
            "eagle": [
                ("CapableOf", "hunt"),
            ],
        }

    def test_full_pipeline_produces_healthy_theory(self):
        theory, stats = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
            profile=BIOLOGY,
        )
        report = validate_theory(theory)

        assert report.is_healthy
        assert report.defeasible_rules > 0
        assert report.defeaters > 0
        assert report.strict_rules > 0

    def test_full_pipeline_stats_match(self):
        theory, stats = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
            profile=BIOLOGY,
        )
        report = validate_theory(theory)

        assert report.total_rules == stats.total_rules
        assert report.strict_rules == stats.strict_rules
        assert report.defeaters == stats.defeaters

    def test_inherited_properties_propagate(self):
        theory, stats = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
            profile=BIOLOGY,
        )
        defeasible = theory.get_rules_by_type(RuleType.DEFEASIBLE)
        inherited = [
            r for r in defeasible
            if r.label and "inh" in r.label
        ]
        assert len(inherited) > 0
        assert stats.defeasible_inherited > 0

    def test_defeaters_contradict_defaults(self):
        theory, _ = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
            profile=BIOLOGY,
        )
        report = validate_theory(theory)
        assert report.contradiction_count > 0

    def test_save_and_load_report(self):
        theory, _ = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
        )
        report = validate_theory(theory)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            save_report(report, path)
            with open(path) as f:
                data = json.load(f)

            assert data["total_rules"] == report.total_rules
            assert data["is_healthy"] == report.is_healthy

    def test_deduplicate_idempotent(self):
        theory, _ = combine_taxonomy_properties(
            self._biology_taxonomy(),
            self._biology_properties(),
        )
        clean = deduplicate_theory(theory)
        report = validate_theory(clean)
        assert report.duplicate_count == 0


class TestConceptNetToValidation:
    """End-to-end: ConceptNet sample -> theory -> validation."""

    def test_conceptnet_extraction_validates(self):
        from blanc.ontology.conceptnet_extractor import ConceptNetExtractor

        lines = [
            self._edge("CapableOf", "bird", "fly", 8.0),
            self._edge("IsA", "penguin", "bird", 9.0),
            self._edge("NotCapableOf", "penguin", "fly", 7.0),
            self._edge("HasProperty", "bird", "feathers", 6.0),
            self._edge("Causes", "bird", "noise", 5.0),
            self._edge("UsedFor", "bird", "pet", 4.0),
        ]
        path = self._write(lines)
        try:
            ext = ConceptNetExtractor(path, weight_threshold=2.0, profile=BIOLOGY)
            ext.extract()
            theory = ext.to_theory()
            report = validate_theory(theory)

            assert report.defeasible_rules >= 4
            assert report.defeaters >= 1
            assert report.total_facts >= 1
        finally:
            path.unlink()

    def _edge(self, rel, start, end, weight):
        meta = json.dumps({"weight": weight})
        return (
            f"/a/[/r/{rel}]/[/c/en/{start}]/[/c/en/{end}]/\t"
            f"/r/{rel}\t/c/en/{start}\t/c/en/{end}\t{meta}"
        )

    def _write(self, lines):
        f = tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv.gz", delete=False
        )
        with gzip.open(f.name, "wt", encoding="utf-8") as gz:
            for line in lines:
                gz.write(line + "\n")
        return Path(f.name)


class TestComposedKBValidation:
    """Validate the fully composed domain KBs."""

    def test_biology_kb_validates_healthy(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        theory = create_biology_kb(include_instances=False)
        clean = deduplicate_theory(theory)
        report = validate_theory(clean)
        assert report.is_healthy
        assert report.defeasible_rules >= 150
        assert report.defeaters >= 70
        assert report.strict_rules >= 900
        assert report.superiority_count >= 20
        assert report.multi_body_rules >= 25

    def test_legal_kb_validates_healthy(self):
        from examples.knowledge_bases.legal_kb import create_legal_kb
        theory = create_legal_kb(include_instances=False)
        report = validate_theory(theory)
        assert report.is_healthy
        assert report.defeasible_rules >= 90
        assert report.defeaters >= 55
        assert report.superiority_count >= 10
        assert report.multi_body_rules >= 15

    def test_materials_kb_validates_healthy(self):
        from examples.knowledge_bases.materials_kb import create_materials_kb
        theory = create_materials_kb(include_instances=False)
        report = validate_theory(theory)
        assert report.is_healthy
        assert report.defeasible_rules >= 90
        assert report.defeaters >= 55
        assert report.superiority_count >= 10
        assert report.multi_body_rules >= 15

    def test_combined_rule_count_exceeds_3000(self):
        from examples.knowledge_bases.biology_kb import create_biology_kb
        from examples.knowledge_bases.legal_kb import create_legal_kb
        from examples.knowledge_bases.materials_kb import create_materials_kb

        bio = create_biology_kb(include_instances=False)
        legal = create_legal_kb(include_instances=False)
        mat = create_materials_kb(include_instances=False)

        total = len(bio.rules) + len(legal.rules) + len(mat.rules)
        assert total >= 3000
