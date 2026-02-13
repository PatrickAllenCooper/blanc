"""
Unit tests for model interface layer.

Tests:
- ModelResponse dataclass
- RateLimiter
- ModelInterface base class
- MockModelInterface
- Factory function

Author: Patrick Cooper
Date: 2026-02-13
"""

import pytest
import time
import sys
from pathlib import Path

# Add experiments to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiments"))

from model_interface import (
    ModelResponse,
    RateLimiter,
    ModelInterface,
    MockModelInterface,
    create_model_interface
)


class TestModelResponse:
    """Test ModelResponse dataclass."""
    
    def test_create_response(self):
        """Test creating a model response."""
        response = ModelResponse(
            text="Test response",
            model="gpt-4o",
            tokens_input=10,
            tokens_output=20,
            cost=0.001,
            latency=0.5
        )
        
        assert response.text == "Test response"
        assert response.model == "gpt-4o"
        assert response.tokens_input == 10
        assert response.tokens_output == 20
        assert response.cost == 0.001
        assert response.latency == 0.5
        assert response.timestamp is not None
    
    def test_to_dict(self):
        """Test converting response to dictionary."""
        response = ModelResponse(
            text="Test",
            model="test-model",
            tokens_input=5,
            tokens_output=10,
            cost=0.001,
            latency=0.1
        )
        
        data = response.to_dict()
        
        assert isinstance(data, dict)
        assert data['text'] == "Test"
        assert data['model'] == "test-model"
        assert data['tokens_input'] == 5
        assert data['tokens_output'] == 10
        assert data['cost'] == 0.001
        assert data['latency'] == 0.1
    
    def test_from_dict(self):
        """Test creating response from dictionary."""
        data = {
            'text': 'Test',
            'model': 'test-model',
            'tokens_input': 5,
            'tokens_output': 10,
            'cost': 0.001,
            'latency': 0.1,
            'timestamp': '2026-02-13T12:00:00',
            'metadata': {'key': 'value'}
        }
        
        response = ModelResponse.from_dict(data)
        
        assert response.text == 'Test'
        assert response.model == 'test-model'
        assert response.metadata == {'key': 'value'}


class TestRateLimiter:
    """Test RateLimiter utility."""
    
    def test_create_rate_limiter(self):
        """Test creating a rate limiter."""
        limiter = RateLimiter(rpm=60, tpm=10000)
        
        assert limiter.rpm == 60
        assert limiter.tpm == 10000
        assert limiter.min_delay == 1.0  # 60/60 = 1 second
    
    def test_wait_if_needed_enforces_min_delay(self):
        """Test that minimum delay is enforced."""
        limiter = RateLimiter(rpm=60, tpm=100000)
        
        start = time.time()
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        elapsed = time.time() - start
        
        # Should have waited at least 1 second between calls
        assert elapsed >= 0.9  # Allow small margin
    
    def test_wait_if_needed_cleans_old_entries(self):
        """Test that old entries are cleaned up."""
        limiter = RateLimiter(rpm=60, tpm=10000)
        
        # Add some entries
        limiter.wait_if_needed()
        
        # Verify entries were added
        assert len(limiter.request_times) > 0
        assert len(limiter.token_usage) > 0


class TestMockModelInterface:
    """Test MockModelInterface."""
    
    def test_create_mock_model(self):
        """Test creating mock model."""
        mock = MockModelInterface("test-model")
        
        assert mock.model_name == "test-model"
        assert mock._query_count == 0
        assert mock._total_cost == 0.0
    
    def test_query_with_canned_responses(self):
        """Test querying with pre-set responses."""
        mock = MockModelInterface("test-model")
        mock.set_responses(["Response 1", "Response 2"])
        
        response1 = mock.query("Prompt 1")
        assert response1.text == "Response 1"
        
        response2 = mock.query("Prompt 2")
        assert response2.text == "Response 2"
    
    def test_query_without_canned_responses(self):
        """Test querying without pre-set responses (echo mode)."""
        mock = MockModelInterface("test-model")
        
        response = mock.query("Test prompt")
        
        assert "Test prompt" in response.text
        assert response.model == "test-model"
    
    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        mock = MockModelInterface("test-model")
        
        mock.query("Prompt 1")
        mock.query("Prompt 2")
        
        stats = mock.statistics
        
        assert stats['total_queries'] == 2
        assert stats['model'] == "test-model"
        assert stats['total_cost'] == 0.0  # Mock has no cost
    
    def test_cost_properties(self):
        """Test cost properties."""
        mock = MockModelInterface("test-model")
        
        assert mock.cost_per_1k_input == 0.0
        assert mock.cost_per_1k_output == 0.0


class TestCreateModelInterface:
    """Test factory function."""
    
    def test_create_mock_interface(self):
        """Test creating mock interface via factory."""
        interface = create_model_interface('mock', model='test-model')
        
        assert isinstance(interface, MockModelInterface)
        assert interface.model_name == 'test-model'
    
    def test_create_openai_requires_api_key(self):
        """Test that OpenAI requires API key."""
        with pytest.raises(ValueError, match="OpenAI requires api_key"):
            create_model_interface('openai')
    
    def test_create_anthropic_requires_api_key(self):
        """Test that Anthropic requires API key."""
        with pytest.raises(ValueError, match="Anthropic requires api_key"):
            create_model_interface('anthropic')
    
    def test_create_google_requires_api_key(self):
        """Test that Google requires API key."""
        with pytest.raises(ValueError, match="Google requires api_key"):
            create_model_interface('google')
    
    def test_unknown_provider_raises_error(self):
        """Test that unknown provider raises error."""
        with pytest.raises(ValueError, match="Unknown provider"):
            create_model_interface('unknown-provider')
    
    def test_provider_case_insensitive(self):
        """Test that provider name is case-insensitive."""
        interface = create_model_interface('MOCK', model='test')
        
        assert isinstance(interface, MockModelInterface)


class TestBatchQuery:
    """Test batch querying."""
    
    def test_batch_query_default_implementation(self):
        """Test default batch query implementation (sequential)."""
        mock = MockModelInterface("test-model")
        mock.set_responses(["Response 1", "Response 2", "Response 3"])
        
        prompts = ["Prompt 1", "Prompt 2", "Prompt 3"]
        responses = mock.batch_query(prompts)
        
        assert len(responses) == 3
        assert responses[0].text == "Response 1"
        assert responses[1].text == "Response 2"
        assert responses[2].text == "Response 3"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
