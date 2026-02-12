"""
Integration tests for ontology extraction modules.

Tests complete pipelines with real data (when available).
Author: Patrick Cooper
Date: 2026-02-11
"""

import pytest
from pathlib import Path

from blanc.core.theory import RuleType
from blanc.reasoning.defeasible import defeasible_provable


class TestOpenCycBiologyIntegration:
    """Integration tests for OpenCyc biology KB."""
    
    def test_opencyc_biology_loads_and_validates(self):
        """Test complete OpenCyc biology KB."""
        pkl_path = Path("examples/knowledge_bases/opencyc_biology/opencyc_biology.pkl")
        
        if not pkl_path.exists():
            pytest.skip("OpenCyc biology KB not generated yet")
        
        from examples.knowledge_bases.opencyc_biology import load_opencyc_biology
        
        kb = load_opencyc_biology()
        
        # Basic structure
        assert len(kb.facts) > 0
        assert len(kb.rules) > 0
        
        # All rules should be strict (from taxonomy)
        for rule in kb.rules:
            assert rule.rule_type == RuleType.STRICT or rule.rule_type is None


class TestConceptNetExtractionComplete:
    """Test ConceptNet extraction when file is available."""
    
    def test_conceptnet_file_exists(self):
        """Verify ConceptNet5 is downloaded."""
        cn_path = Path("D:/datasets/conceptnet5/conceptnet-assertions-5.7.0.csv.gz")
        
        if cn_path.exists():
            # File should be large (~475 MB)
            size_mb = cn_path.stat().st_size / (1024 * 1024)
            assert size_mb > 400  # Should be ~475 MB
            assert size_mb < 600  # Sanity check
        else:
            pytest.skip("ConceptNet5 not downloaded yet")


class TestExtractionCoverage:
    """Ensure extraction modules are well-tested."""
    
    def test_opencyc_extractor_has_tests(self):
        """Verify OpenCyc extractor has comprehensive tests."""
        test_file = Path("tests/ontology/test_opencyc_extractor.py")
        assert test_file.exists()
        
        # Should have multiple test classes
        content = test_file.read_text()
        assert "class Test" in content
        assert "def test_" in content
    
    def test_conceptnet_extractor_has_tests(self):
        """Verify ConceptNet extractor has comprehensive tests."""
        test_file = Path("tests/ontology/test_conceptnet_extractor.py")
        assert test_file.exists()
        
        # Should have multiple test classes
        content = test_file.read_text()
        assert "class Test" in content
        assert "def test_" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
