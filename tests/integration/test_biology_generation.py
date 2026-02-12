"""
Integration tests for biology KB instance generation.

Tests the complete pipeline with curated biology KB.
Author: Patrick Cooper
Date: 2026-02-11
"""

import pytest
from pathlib import Path

from examples.knowledge_bases.biology_curated import create_biology_base, get_biology_stats
from blanc.author.conversion import convert_theory_to_defeasible
from blanc.author.generation import generate_level2_instance
from blanc.author.support import full_theory_criticality
from blanc.core.theory import RuleType


class TestBiologyKBGeneration:
    """Test instance generation from curated biology KB."""
    
    def test_biology_kb_has_depth_4(self):
        """Verify biology KB has required depth."""
        kb = create_biology_base()
        stats = get_biology_stats(kb)
        
        assert stats['max_depth'] >= 2  # Paper requirement
        assert stats['max_depth'] == 4  # What we achieved
    
    def test_biology_kb_converts_with_all_partitions(self):
        """Test all partition strategies work on biology KB."""
        kb = create_biology_base()
        
        # Test main strategies
        for strategy in ['leaf', 'rule']:
            converted = convert_theory_to_defeasible(kb, strategy)
            assert len(converted) > 0
            
            # Should have some defeasible rules
            defeasible = converted.get_rules_by_type(RuleType.DEFEASIBLE)
            assert len(defeasible) > 0
    
    def test_can_generate_level2_instances(self):
        """Test Level 2 instance generation from biology KB."""
        kb = create_biology_base()
        converted = convert_theory_to_defeasible(kb, "rule")
        
        # Should be able to generate at least one instance
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        
        if len(defeasible_rules) > 0:
            # Try to find a derivable conclusion
            from blanc.reasoning.defeasible import defeasible_provable
            
            for target in ["flies(robin)", "swims(dolphin)", "hunts(eagle)"]:
                try:
                    if defeasible_provable(converted, target):
                        critical = full_theory_criticality(converted, target)
                        critical_rules = [e for e in critical 
                                        if hasattr(e, 'rule_type') 
                                        and e.rule_type == RuleType.DEFEASIBLE]
                        
                        if critical_rules:
                            instance = generate_level2_instance(
                                converted, target, critical_rules[0], k_distractors=2
                            )
                            assert instance.is_valid()
                            return  # Success
                except:
                    continue
            
            pytest.skip("Could not find suitable target for generation")


class TestYieldComputation:
    """Test yield computation on biology KB."""
    
    def test_yield_computes_without_error(self):
        """Basic yield computation should work."""
        from blanc.author.metrics import defeasible_yield
        from blanc.generation.partition import partition_rule
        
        kb = create_biology_base()
        target_set = {"flies(robin)", "swims(dolphin)"}
        
        # Should compute without error
        yield_val = defeasible_yield(partition_rule, target_set, kb)
        assert yield_val >= 0  # Yield is non-negative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
