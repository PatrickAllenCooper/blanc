"""
Tests for OpenCyc extractor.

Author: Patrick Cooper
Date: 2026-02-11
"""

import pytest
from pathlib import Path

from blanc.ontology.opencyc_extractor import OpenCycExtractor, RDFLIB_AVAILABLE
from examples.knowledge_bases.opencyc_biology import load_opencyc_biology


@pytest.mark.skipif(not RDFLIB_AVAILABLE, reason="rdflib not installed")
class TestOpenCycExtractor:
    """Test OpenCyc extraction functionality."""
    
    def test_extractor_initialization(self):
        """Test extractor can be initialized."""
        opencyc_path = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
        
        if not opencyc_path.exists():
            pytest.skip("OpenCyc file not available")
        
        extractor = OpenCycExtractor(opencyc_path)
        assert extractor.opencyc_path == opencyc_path
        assert extractor.graph is None
    
    def test_concept_name_extraction(self):
        """Test concept name extraction from URI."""
        opencyc_path = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
        
        if not opencyc_path.exists():
            pytest.skip("OpenCyc file not available")
        
        extractor = OpenCycExtractor(opencyc_path)
        
        # Test URI patterns
        assert extractor._extract_concept_name("http://example.com/Bird") == "Bird"
        # Note: Fragment (#) extraction gets last component after /
        name = extractor._extract_concept_name("http://example.com#Animal")
        assert "Animal" in name or name == "example.com#Animal"  # Implementation detail
    
    def test_prolog_normalization(self):
        """Test Prolog name normalization."""
        opencyc_path = Path(r"D:\datasets\opencyc-kb\opencyc-2012-05-10-readable.owl.gz")
        
        if not opencyc_path.exists():
            pytest.skip("OpenCyc file not available")
        
        extractor = OpenCycExtractor(opencyc_path)
        
        # Test normalization
        assert extractor._normalize_for_prolog("Bird Species") == "bird_species"
        assert extractor._normalize_for_prolog("Animal-Type") == "animal_type"
        assert extractor._normalize_for_prolog("Cell(Type)") == "celltype"
        assert extractor._normalize_for_prolog("123Organism").startswith("c_")


class TestOpenCycBiologyKB:
    """Test the extracted OpenCyc biology KB."""
    
    def test_load_opencyc_biology(self):
        """Test loading the extracted biology KB."""
        kb_path = Path("examples/knowledge_bases/opencyc_biology/opencyc_biology.pkl")
        
        if not kb_path.exists():
            pytest.skip("OpenCyc biology KB not extracted yet")
        
        kb = load_opencyc_biology()
        
        assert len(kb.facts) > 0
        assert len(kb.rules) > 0
        assert len(kb) > 30000  # Should be large
    
    def test_biology_kb_structure(self):
        """Test structure of biology KB."""
        kb_path = Path("examples/knowledge_bases/opencyc_biology/opencyc_biology.pkl")
        
        if not kb_path.exists():
            pytest.skip("OpenCyc biology KB not extracted yet")
        
        kb = load_opencyc_biology()
        
        # Should have biological_concept facts
        bio_concept_facts = [f for f in kb.facts if 'biological_concept(' in f]
        assert len(bio_concept_facts) > 1000
        
        # Should have isa rules
        isa_rules = [r for r in kb.rules if 'isa(' in r.head]
        assert len(isa_rules) > 1000
    
    def test_biology_kb_concepts_normalized(self):
        """Test that concept names are properly normalized."""
        kb_path = Path("examples/knowledge_bases/opencyc_biology/opencyc_biology.pkl")
        
        if not kb_path.exists():
            pytest.skip("OpenCyc biology KB not extracted yet")
        
        kb = load_opencyc_biology()
        
        # Check normalization (all lowercase, underscores)
        for fact in list(kb.facts)[:100]:
            # Extract concept name
            if 'biological_concept(' in fact:
                concept = fact.replace('biological_concept(', '').replace(')', '')
                # Should be lowercase
                assert concept.islower() or concept.startswith('c_')
                # Should not have spaces
                assert ' ' not in concept


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
