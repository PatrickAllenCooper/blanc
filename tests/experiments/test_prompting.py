"""
Unit tests for prompting infrastructure.

Tests:
- Prompt rendering for all modalities
- Direct vs CoT strategies
- Batch rendering
- Template formatting

Author: Patrick Cooper
Date: 2026-02-13
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiments"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from prompting import (
    render_prompt,
    batch_render_prompts,
    RenderedPrompt,
    DIRECT_PROMPT_TEMPLATE,
    COT_PROMPT_TEMPLATE
)
from blanc.core.theory import Theory, Rule, RuleType
from blanc.author.generation import AbductiveInstance


@pytest.fixture
def simple_instance():
    """Create a simple test instance."""
    theory = Theory()
    theory.add_rule(Rule("bird(tweety)", (), RuleType.FACT, "f1"))
    theory.add_rule(Rule("flies(X)", ("bird(X)",), RuleType.DEFEASIBLE, "r1"))
    
    instance = AbductiveInstance(
        D_minus=theory,
        target="flies(tweety)",
        candidates=["bird(tweety)", "penguin(tweety)", "injured(tweety)"],
        gold=["bird(tweety)"],
        level=1
    )
    instance.id = "test-001"
    
    return instance


class TestRenderPrompt:
    """Test prompt rendering."""
    
    def test_render_m4_direct(self, simple_instance):
        """Test rendering M4 with direct strategy."""
        rendered = render_prompt(simple_instance, 'M4', 'direct')
        
        assert isinstance(rendered, RenderedPrompt)
        assert rendered.modality == 'M4'
        assert rendered.strategy == 'direct'
        assert rendered.instance_id == 'test-001'
        assert len(rendered.prompt) > 0
        
        # Should contain key elements
        assert "bird(tweety)" in rendered.prompt
        assert "flies(tweety)" in rendered.prompt
        assert "Theory" in rendered.prompt
    
    def test_render_m4_cot(self, simple_instance):
        """Test rendering M4 with Chain-of-Thought."""
        rendered = render_prompt(simple_instance, 'M4', 'cot')
        
        assert rendered.strategy == 'cot'
        assert "step-by-step" in rendered.prompt.lower()
        assert "step 1" in rendered.prompt.lower() or "final answer" in rendered.prompt.lower()
    
    def test_render_m2_direct(self, simple_instance):
        """Test rendering M2 semi-formal."""
        rendered = render_prompt(simple_instance, 'M2', 'direct')
        
        assert rendered.modality == 'M2'
        # M2 should use semi-formal notation
        assert len(rendered.prompt) > 0
    
    def test_render_invalid_modality_raises_error(self, simple_instance):
        """Test that invalid modality raises error."""
        with pytest.raises(ValueError, match="Unknown modality"):
            render_prompt(simple_instance, 'M5', 'direct')
    
    def test_render_invalid_strategy_raises_error(self, simple_instance):
        """Test that invalid strategy raises error."""
        with pytest.raises(ValueError, match="Unknown strategy"):
            render_prompt(simple_instance, 'M4', 'invalid')
    
    def test_modality_case_insensitive(self, simple_instance):
        """Test that modality is case-insensitive."""
        rendered = render_prompt(simple_instance, 'm4', 'direct')
        
        assert rendered.modality == 'M4'
    
    def test_strategy_case_insensitive(self, simple_instance):
        """Test that strategy is case-insensitive."""
        rendered = render_prompt(simple_instance, 'M4', 'DIRECT')
        
        assert rendered.strategy == 'direct'


class TestRenderedPrompt:
    """Test RenderedPrompt dataclass."""
    
    def test_rendered_prompt_str(self, simple_instance):
        """Test that RenderedPrompt can be converted to string."""
        rendered = render_prompt(simple_instance, 'M4', 'direct')
        
        prompt_str = str(rendered)
        
        assert isinstance(prompt_str, str)
        assert len(prompt_str) > 0
    
    def test_rendered_prompt_metadata(self, simple_instance):
        """Test that metadata is populated."""
        rendered = render_prompt(simple_instance, 'M4', 'direct', domain='biology')
        
        assert rendered.metadata is not None
        assert rendered.metadata['domain'] == 'biology'
        assert rendered.metadata['level'] == 1
        assert rendered.metadata['num_candidates'] == 3


class TestBatchRendering:
    """Test batch rendering."""
    
    def test_batch_render_prompts(self, simple_instance):
        """Test batch rendering multiple instances."""
        instances = [simple_instance, simple_instance, simple_instance]
        
        rendered_list = batch_render_prompts(instances, 'M4', 'direct')
        
        assert len(rendered_list) == 3
        assert all(isinstance(r, RenderedPrompt) for r in rendered_list)
        assert all(r.modality == 'M4' for r in rendered_list)
    
    def test_batch_render_empty_list(self):
        """Test batch rendering with empty list."""
        rendered_list = batch_render_prompts([], 'M4', 'direct')
        
        assert len(rendered_list) == 0


class TestPromptTemplates:
    """Test prompt templates."""
    
    def test_direct_template_structure(self):
        """Test direct prompt template structure."""
        assert "{theory_section}" in DIRECT_PROMPT_TEMPLATE
        assert "{target_section}" in DIRECT_PROMPT_TEMPLATE
        assert "{candidates_section}" in DIRECT_PROMPT_TEMPLATE
    
    def test_cot_template_structure(self):
        """Test CoT prompt template structure."""
        assert "{theory_section}" in COT_PROMPT_TEMPLATE
        assert "{target_section}" in COT_PROMPT_TEMPLATE
        assert "{candidates_section}" in COT_PROMPT_TEMPLATE
        assert "step-by-step" in COT_PROMPT_TEMPLATE.lower()


class TestModalitySpecificRendering:
    """Test modality-specific rendering."""
    
    def test_all_modalities_render(self, simple_instance):
        """Test that all modalities can be rendered."""
        for modality in ['M1', 'M2', 'M3', 'M4']:
            rendered = render_prompt(simple_instance, modality, 'direct')
            
            assert rendered.modality == modality
            assert len(rendered.prompt) > 0
    
    def test_all_strategies_render(self, simple_instance):
        """Test that all strategies can be rendered."""
        for strategy in ['direct', 'cot']:
            rendered = render_prompt(simple_instance, 'M4', strategy)
            
            assert rendered.strategy == strategy
            assert len(rendered.prompt) > 0


class TestCandidateFormatting:
    """Test candidate hypothesis formatting."""
    
    def test_candidates_numbered(self, simple_instance):
        """Test that candidates are numbered in prompt."""
        rendered = render_prompt(simple_instance, 'M4', 'direct')
        
        # Should have numbered candidates
        assert "1." in rendered.prompt
        assert "2." in rendered.prompt
        assert "3." in rendered.prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
