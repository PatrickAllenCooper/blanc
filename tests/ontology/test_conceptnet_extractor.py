"""
Comprehensive tests for ConceptNet5 extractor.

Tests all extraction logic to achieve >90% coverage.
Author: Patrick Cooper
Date: 2026-02-11
"""

import pytest
from pathlib import Path
import tempfile
import gzip
import json

from blanc.ontology.conceptnet_extractor import (
    ConceptNetExtractor,
    extract_biology_from_conceptnet,
)
from blanc.core.theory import RuleType


class TestConceptNetExtractor:
    """Test ConceptNet5 extraction functionality."""
    
    def test_extractor_initialization(self):
        """Test extractor can be initialized."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if not cn_path.exists():
            pytest.skip("ConceptNet5 file not available")
        
        extractor = ConceptNetExtractor(cn_path, weight_threshold=2.0)
        assert extractor.conceptnet_path == cn_path
        assert extractor.weight_threshold == 2.0
        assert extractor.edges == []
        assert extractor.biological_edges == []
    
    def test_extract_concept_from_uri(self):
        """Test concept extraction from ConceptNet URI."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if not cn_path.exists():
            pytest.skip("ConceptNet5 file not available")
        
        extractor = ConceptNetExtractor(cn_path)
        
        # Test various URI formats
        assert extractor._extract_concept("/c/en/bird") == "bird"
        assert extractor._extract_concept("/c/en/bird/n") == "bird"
        assert extractor._extract_concept("/c/en/fly") == "fly"
    
    def test_extract_relation_from_uri(self):
        """Test relation extraction from URI."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if not cn_path.exists():
            pytest.skip("ConceptNet5 file not available")
        
        extractor = ConceptNetExtractor(cn_path)
        
        # Test relation URIs
        assert extractor._extract_relation("/r/CapableOf") == "CapableOf"
        assert extractor._extract_relation("/r/IsA") == "IsA"
        assert extractor._extract_relation("/r/NotCapableOf") == "NotCapableOf"
        assert extractor._extract_relation("/r/HasProperty") == "HasProperty"
    
    def test_normalization(self):
        """Test Prolog normalization."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if not cn_path.exists():
            pytest.skip("ConceptNet5 file not available")
        
        extractor = ConceptNetExtractor(cn_path)
        
        # Test normalization
        assert extractor._normalize("Bird Species") == "bird_species"
        assert extractor._normalize("Can-Fly") == "can_fly"
        assert extractor._normalize("Has Property") == "has_property"
        assert extractor._normalize("Bird123") == "bird123"
    
    def test_action_to_predicate(self):
        """Test action conversion to predicate."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if not cn_path.exists():
            pytest.skip("ConceptNet5 file not available")
        
        extractor = ConceptNetExtractor(cn_path)
        
        # Actions should be normalized
        assert extractor._action_to_predicate("fly") == "fly"
        assert extractor._action_to_predicate("swim fast") == "swim_fast"


class TestConceptNetExtractionOnSample:
    """Test extraction on sample ConceptNet data."""
    
    def test_extract_from_sample_data(self):
        """Test extraction with sample ConceptNet edges."""
        # Create sample ConceptNet data
        sample_data = [
            # High-weight biological edge (should be extracted)
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.3, "dataset": "/d/conceptnet/4/en"}),
            
            # IsA edge
            "/a/[/r/IsA]/[/c/en/penguin]/[/c/en/bird]/\t/r/IsA\t/c/en/penguin\t/c/en/bird\t"
            + json.dumps({"weight": 9.1}),
            
            # NotCapableOf (exception)
            "/a/[/r/NotCapableOf]/[/c/en/penguin]/[/c/en/fly]/\t/r/NotCapableOf\t/c/en/penguin\t/c/en/fly\t"
            + json.dumps({"weight": 7.2}),
            
            # Low weight (should be filtered)
            "/a/[/r/CapableOf]/[/c/en/rock]/[/c/en/fly]/\t/r/CapableOf\t/c/en/rock\t/c/en/fly\t"
            + json.dumps({"weight": 0.5}),
            
            # Non-English (should be filtered)
            "/a/[/r/CapableOf]/[/c/fr/oiseau]/[/c/fr/voler]/\t/r/CapableOf\t/c/fr/oiseau\t/c/fr/voler\t"
            + json.dumps({"weight": 5.0}),
        ]
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            # Extract
            extractor = ConceptNetExtractor(temp_path, weight_threshold=2.0)
            extractor.extract_biology(max_edges=10)
            
            # Should have 3 biological edges (bird fly, penguin bird, penguin ~fly)
            assert len(extractor.biological_edges) == 3
            
            # Check relations
            relations = [e['relation'] for e in extractor.biological_edges]
            assert 'CapableOf' in relations
            assert 'IsA' in relations
            assert 'NotCapableOf' in relations
            
        finally:
            # Cleanup
            temp_path.unlink()
    
    def test_conversion_to_theory(self):
        """Test conversion of edges to Theory object."""
        # Create sample data
        sample_data = [
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.3}),
            
            "/a/[/r/IsA]/[/c/en/penguin]/[/c/en/bird]/\t/r/IsA\t/c/en/penguin\t/c/en/bird\t"
            + json.dumps({"weight": 9.1}),
            
            "/a/[/r/NotCapableOf]/[/c/en/penguin]/[/c/en/fly]/\t/r/NotCapableOf\t/c/en/penguin\t/c/en/fly\t"
            + json.dumps({"weight": 7.2}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            # Extract and convert
            extractor = ConceptNetExtractor(temp_path, weight_threshold=2.0)
            extractor.extract_biology()
            theory = extractor.to_theory()
            
            # Should have facts (IsA)
            assert len(theory.facts) > 0
            assert "isa(penguin, bird)" in theory.facts
            
            # Should have defeasible rules (CapableOf)
            defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(defeasible_rules) > 0
            
            # Should have defeaters (NotCapableOf)
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) > 0
            
        finally:
            temp_path.unlink()
    
    def test_weight_filtering(self):
        """Test that weight threshold filters correctly."""
        sample_data = [
            # High weight (should pass)
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.0}),
            
            # Low weight (should be filtered)
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/teleport]/\t/r/CapableOf\t/c/en/bird\t/c/en/teleport\t"
            + json.dumps({"weight": 0.1}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            # Extract with threshold 2.0
            extractor = ConceptNetExtractor(temp_path, weight_threshold=2.0)
            extractor.extract_biology()
            
            # Should only have high-weight edge
            assert len(extractor.biological_edges) == 1
            assert extractor.biological_edges[0]['weight'] >= 2.0
            
        finally:
            temp_path.unlink()
    
    def test_malformed_line_handling(self):
        """Test that malformed lines are skipped gracefully."""
        sample_data = [
            # Good line
            "/a/[/r/IsA]/[/c/en/bird]/[/c/en/animal]/\t/r/IsA\t/c/en/bird\t/c/en/animal\t"
            + json.dumps({"weight": 5.0}),
            
            # Malformed (missing tabs)
            "malformed line without tabs",
            
            # Invalid JSON
            "/a/test\t/r/IsA\t/c/en/bird\t/c/en/animal\t{invalid json}",
            
            # Another good line
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 3.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            # Should not crash on malformed lines
            extractor = ConceptNetExtractor(temp_path, weight_threshold=2.0)
            extractor.extract_biology()
            
            # Should have extracted 2 good lines
            assert len(extractor.biological_edges) == 2
            
        finally:
            temp_path.unlink()


class TestConceptNetRuleTypes:
    """Test different ConceptNet relation types convert correctly."""
    
    def test_isa_creates_facts(self):
        """IsA relations should create facts."""
        sample_data = [
            "/a/[/r/IsA]/[/c/en/sparrow]/[/c/en/bird]/\t/r/IsA\t/c/en/sparrow\t/c/en/bird\t"
            + json.dumps({"weight": 9.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            theory = extractor.to_theory()
            
            # Should have isa fact
            assert "isa(sparrow, bird)" in theory.facts
            
        finally:
            temp_path.unlink()
    
    def test_capableof_creates_defeasible_rules(self):
        """CapableOf relations should create defeasible rules."""
        sample_data = [
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            theory = extractor.to_theory()
            
            # Should have defeasible rule
            defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(defeasible_rules) > 0
            
            # Check structure
            rule = defeasible_rules[0]
            assert "fly" in rule.head
            assert rule.rule_type == RuleType.DEFEASIBLE
            
        finally:
            temp_path.unlink()
    
    def test_notcapableof_creates_defeaters(self):
        """NotCapableOf relations should create defeater rules."""
        sample_data = [
            "/a/[/r/NotCapableOf]/[/c/en/penguin]/[/c/en/fly]/\t/r/NotCapableOf\t/c/en/penguin\t/c/en/fly\t"
            + json.dumps({"weight": 7.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            theory = extractor.to_theory()
            
            # Should have defeater
            defeaters = theory.get_rules_by_type(RuleType.DEFEATER)
            assert len(defeaters) > 0
            
            # Check structure
            defeater = defeaters[0]
            assert "~" in defeater.head or "fly" in defeater.head
            assert defeater.rule_type == RuleType.DEFEATER
            
        finally:
            temp_path.unlink()
    
    def test_hasproperty_creates_rules(self):
        """HasProperty relations should create defeasible rules."""
        sample_data = [
            "/a/[/r/HasProperty]/[/c/en/bird]/[/c/en/feathers]/\t/r/HasProperty\t/c/en/bird\t/c/en/feathers\t"
            + json.dumps({"weight": 6.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            theory = extractor.to_theory()
            
            # Should have has_property rule
            defeasible_rules = theory.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(defeasible_rules) > 0
            
            # Check for has_ prefix
            rule = defeasible_rules[0]
            assert "has_" in rule.head or "feather" in rule.head
            
        finally:
            temp_path.unlink()


class TestConceptNetBiologyKeywords:
    """Test biological keyword filtering."""
    
    def test_bird_keyword_matches(self):
        """Edges with 'bird' should be extracted."""
        sample_data = [
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            
            assert len(extractor.biological_edges) == 1
            
        finally:
            temp_path.unlink()
    
    def test_non_biological_filtered(self):
        """Non-biological edges should be filtered."""
        sample_data = [
            # Biological
            "/a/[/r/CapableOf]/[/c/en/bird]/[/c/en/fly]/\t/r/CapableOf\t/c/en/bird\t/c/en/fly\t"
            + json.dumps({"weight": 8.0}),
            
            # Non-biological (should be filtered)
            "/a/[/r/CapableOf]/[/c/en/car]/[/c/en/drive]/\t/r/CapableOf\t/c/en/car\t/c/en/drive\t"
            + json.dumps({"weight": 9.0}),
        ]
        
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv.gz', delete=False) as f:
            with gzip.open(f.name, 'wt', encoding='utf-8') as gz:
                for line in sample_data:
                    gz.write(line + '\n')
            temp_path = Path(f.name)
        
        try:
            extractor = ConceptNetExtractor(temp_path)
            extractor.extract_biology()
            
            # Should only have biological edge
            assert len(extractor.biological_edges) == 1
            assert 'bird' in extractor.biological_edges[0]['start']
            
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
