"""
Tests for defeasible conversion.

Tests Definition 9 and Proposition 1.
Author: Anonymous Authors
"""

import pytest
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.conversion import phi_kappa, convert_theory_to_defeasible
from blanc.generation.partition import (
    partition_leaf,
    partition_rule,
    partition_random,
    defeasibility_ratio,
)
from blanc.reasoning.defeasible import defeasible_provable, strictly_provable
from examples.knowledge_bases.avian_biology.avian_biology_base import (
    create_avian_biology_base,
)


class TestPhiKappa:
    """Test φ_κ conversion function."""
    
    def test_basic_conversion(self):
        """Basic conversion preserves theory content."""
        source = Theory()
        source.add_fact("bird(tweety)")
        source.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT  # Will be reclassified
        ))
        
        # Convert with κ_rule (facts strict, rules defeasible)
        converted = phi_kappa(source, partition_rule)
        
        # Should have 1 fact, 1 defeasible rule
        assert "bird(tweety)" in converted.facts
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        assert len(defeasible_rules) == 1
        assert defeasible_rules[0].head == "flies(X)"
    
    def test_partition_leaf_conversion(self):
        """Test conversion with κ_leaf (facts defeasible, rules strict)."""
        source = Theory()
        source.add_fact("bird(tweety)")
        source.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",)
        ))
        
        converted = phi_kappa(source, partition_leaf)
        
        # Facts should become defeasible rules with empty body
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        assert any(r.head == "bird(tweety)" and len(r.body) == 0 
                  for r in defeasible_rules)
        
        # Rules should become strict
        strict_rules = converted.get_rules_by_type(RuleType.STRICT)
        assert any(r.head == "flies(X)" for r in strict_rules)
    
    def test_partition_rule_conversion(self):
        """Test conversion with κ_rule (facts strict, rules defeasible)."""
        source = Theory()
        source.add_fact("bird(tweety)")
        source.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",)
        ))
        
        converted = phi_kappa(source, partition_rule)
        
        # Facts should remain strict
        assert "bird(tweety)" in converted.facts
        
        # Rules should become defeasible
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        assert any(r.head == "flies(X)" for r in defeasible_rules)


class TestProposition1:
    """Test Proposition 1: Conservative conversion when κ ≡ s."""
    
    def test_all_strict_preserves_derivability(self):
        """
        Proposition 1 (paper.tex line 743):
        When κ ≡ s (all strict), q ∈ M_Π ⟺ D_κ ⊢Δ q.
        
        The conversion is conservative: strictly derivable conclusions
        are preserved exactly.
        """
        source = Theory()
        source.add_fact("bird(tweety)")
        source.add_rule(Rule(
            head="flies(X)",
            body=("bird(X)",),
            rule_type=RuleType.STRICT
        ))
        source.add_rule(Rule(
            head="migrates(X)",
            body=("flies(X)",),
            rule_type=RuleType.STRICT
        ))
        
        # All-strict partition
        kappa_strict = lambda r: 's'
        converted = phi_kappa(source, kappa_strict)
        
        # All derivable conclusions should be preserved
        # bird(tweety) should be strictly provable
        assert strictly_provable(converted, "bird(tweety)")
        
        # flies(tweety) should be strictly provable
        assert strictly_provable(converted, "flies(tweety)")
        
        # migrates(tweety) should be strictly provable
        assert strictly_provable(converted, "migrates(tweety)")
        
        # Non-derivable should remain non-derivable
        assert not strictly_provable(converted, "swims(tweety)")
    
    def test_all_strict_no_defeasible_rules(self):
        """When κ ≡ s, converted theory should have no defeasible rules."""
        source = Theory()
        source.add_fact("p")
        source.add_rule(Rule(head="q", body=("p",)))
        
        kappa_strict = lambda r: 's'
        converted = phi_kappa(source, kappa_strict)
        
        # No defeasible rules
        assert len(converted.get_rules_by_type(RuleType.DEFEASIBLE)) == 0
        
        # Only strict rules and facts
        assert len(converted.facts) > 0 or len(converted.get_rules_by_type(RuleType.STRICT)) > 0


class TestConversionAvianBiology:
    """Test conversion on Avian Biology KB."""
    
    def test_convert_with_partition_rule(self):
        """Convert Avian Biology with κ_rule."""
        source = create_avian_biology_base()
        converted = convert_theory_to_defeasible(source, "rule")
        
        # Facts should be strict
        assert "bird(tweety)" in converted.facts
        assert "sparrow(tweety)" in converted.facts
        
        # Behavioral rules should be defeasible (r1-r5)
        defeasible_rules = converted.get_rules_by_type(RuleType.DEFEASIBLE)
        labels = {r.label for r in defeasible_rules if r.label}
        
        assert "r1" in labels  # flies(X) :- bird(X)
        assert "r2" in labels  # migrates(X) :- bird(X), flies(X)
        
        # Taxonomic rules are originally STRICT in source, so κ_rule
        # should convert them to DEFEASIBLE (rules become defeasible)
        # This is the behavior of partition_rule - ALL rules become defeasible
        assert "s1" in labels  # bird(X) :- sparrow(X) becomes defeasible
    
    def test_converted_theory_derivations(self):
        """Converted theory should derive same conclusions."""
        source = create_avian_biology_base()
        converted = convert_theory_to_defeasible(source, "rule")
        
        # Should derive same conclusions (defeasibly, not strictly)
        assert defeasible_provable(converted, "bird(tweety)")
        assert defeasible_provable(converted, "flies(tweety)")
        assert defeasible_provable(converted, "migrates(tweety)")
    
    def test_defeasibility_ratio_rule_partition(self):
        """Compute defeasibility ratio for κ_rule."""
        source = create_avian_biology_base()
        
        # Get all rules (including facts as rules)
        all_rules = []
        for fact in source.facts:
            all_rules.append(Rule(head=fact, body=(), rule_type=RuleType.FACT))
        all_rules.extend(source.rules)
        
        ratio = defeasibility_ratio(partition_rule, all_rules)
        
        # Most rules should be defeasible (all non-facts)
        # With Avian Biology: many rules, some facts
        assert 0 < ratio < 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
