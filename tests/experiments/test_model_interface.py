"""
Unit tests for model interface layer.

Tests:
- ModelResponse dataclass
- RateLimiter
- ModelInterface base class
- MockModelInterface
- CURCInterface (mocked OpenAI client)
- Factory function

Author: Patrick Cooper
Date: 2026-02-13
"""

import pytest
import time
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add experiments to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "experiments"))

from model_interface import (
    ModelResponse,
    RateLimiter,
    ModelInterface,
    MockModelInterface,
    CURCInterface,
    FoundryGPT52Interface,
    FoundryKimiInterface,
    FoundryClaudeInterface,
    create_model_interface,
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


def _make_curc_completion(text: str = "test response", prompt_tokens: int = 5, completion_tokens: int = 2):
    """Build a minimal mock openai.ChatCompletion response for CURCInterface."""
    choice = MagicMock()
    choice.message.content = text
    choice.finish_reason = "stop"

    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


class TestCURCInterface:
    """Test CURCInterface against a mocked vLLM / OpenAI-compatible server."""

    def _make_interface(self, model: str = "Qwen/Qwen2.5-72B-Instruct-AWQ") -> CURCInterface:
        return CURCInterface(
            base_url="http://localhost:8000",
            model=model,
            rpm=6000,  # no rate-limiting delay in tests
        )

    def test_init_defaults(self):
        iface = self._make_interface()
        assert iface.model_name == "Qwen/Qwen2.5-72B-Instruct-AWQ"
        assert iface._base_url == "http://localhost:8000"
        assert iface._api_key == "not-needed"

    def test_init_trailing_slash_stripped(self):
        iface = CURCInterface(base_url="http://localhost:8000/", model="some/model")
        assert iface._base_url == "http://localhost:8000"

    def test_cost_properties_are_zero(self):
        iface = self._make_interface()
        assert iface.cost_per_1k_input == 0.0
        assert iface.cost_per_1k_output == 0.0

    @patch("model_interface.CURCInterface._get_client")
    def test_query_returns_model_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_curc_completion(
            text="test output", prompt_tokens=10, completion_tokens=3
        )

        iface = self._make_interface()
        resp = iface.query("Say 'test'", max_tokens=20)

        assert isinstance(resp, ModelResponse)
        assert resp.text == "test output"
        assert resp.model == "Qwen/Qwen2.5-72B-Instruct-AWQ"
        assert resp.tokens_input == 10
        assert resp.tokens_output == 3
        assert resp.cost == 0.0
        assert resp.latency >= 0.0
        assert resp.metadata["provider"] == "curc_vllm"

    @patch("model_interface.CURCInterface._get_client")
    def test_query_updates_statistics(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_curc_completion()

        iface = self._make_interface()
        iface.query("prompt 1")
        iface.query("prompt 2")

        stats = iface.statistics
        assert stats["total_queries"] == 2
        assert stats["total_cost"] == 0.0

    @patch("model_interface.CURCInterface._get_client")
    def test_query_passes_temperature_and_max_tokens(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_curc_completion()

        iface = self._make_interface()
        iface.query("prompt", temperature=0.7, max_tokens=128)

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["temperature"] == 0.7
        assert call_kwargs["max_tokens"] == 128

    @patch("model_interface.CURCInterface._get_client")
    def test_query_serialises_to_dict(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.return_value = _make_curc_completion(text="hello")

        iface = self._make_interface()
        resp = iface.query("hi")
        d = resp.to_dict()

        assert d["text"] == "hello"
        assert d["cost"] == 0.0
        assert "provider" in d["metadata"]

    @patch("model_interface.CURCInterface._get_client")
    def test_query_propagates_server_error(self, mock_get_client):
        """If the vLLM server returns an error, CURCInterface should propagate it."""
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.chat.completions.create.side_effect = RuntimeError("connection refused")

        iface = CURCInterface(
            base_url="http://localhost:8000",
            model="some/model",
            rpm=6000,
        )
        # tenacity will retry 5 times; patch stop condition to fail fast
        with pytest.raises(RuntimeError, match="connection refused"):
            iface.query("prompt")


def _make_openai_completion(text: str = "test", prompt_tokens: int = 5, completion_tokens: int = 2):
    """Build a minimal mock openai.ChatCompletion for Foundry GPT/Kimi tests."""
    choice = MagicMock()
    choice.message.content = text
    choice.finish_reason = "stop"
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens
    completion = MagicMock()
    completion.choices = [choice]
    completion.usage = usage
    return completion


def _make_anthropic_message(text: str = "test", input_tokens: int = 5, output_tokens: int = 2):
    """Build a minimal mock Anthropic Messages response for Foundry Claude tests."""
    content_block = MagicMock()
    content_block.text = text
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    message = MagicMock()
    message.content = [content_block]
    message.usage = usage
    message.stop_reason = "end_turn"
    return message


class TestFoundryGPT52Interface:
    """Test FoundryGPT52Interface against a mocked AzureOpenAI client."""

    FAKE_KEY = "fake-foundry-key"

    def _make_interface(self, reasoning_effort: str = "none") -> FoundryGPT52Interface:
        with patch("model_interface.FoundryGPT52Interface.__init__", lambda self, **kw: None):
            iface = FoundryGPT52Interface.__new__(FoundryGPT52Interface)
            iface.model_name        = FoundryGPT52Interface.FOUNDRY_DEPLOYMENT
            iface._deployment       = FoundryGPT52Interface.FOUNDRY_DEPLOYMENT
            iface._reasoning_effort = reasoning_effort
            iface._total_cost       = 0.0
            iface._total_tokens_input  = 0
            iface._total_tokens_output = 0
            iface._query_count      = 0
            iface.rate_limiter      = RateLimiter(rpm=6000, tpm=10_000_000)
            iface._client           = MagicMock()
            return iface

    def test_cost_properties(self):
        iface = self._make_interface()
        assert iface.cost_per_1k_input > 0
        assert iface.cost_per_1k_output > 0

    def test_query_returns_model_response(self):
        iface = self._make_interface()
        iface._client.chat.completions.create.return_value = _make_openai_completion(
            text="gpt52 answer", prompt_tokens=8, completion_tokens=3
        )
        resp = iface.query("Say 'test'", max_tokens=20)

        assert isinstance(resp, ModelResponse)
        assert resp.text == "gpt52 answer"
        assert resp.tokens_input == 8
        assert resp.tokens_output == 3
        assert resp.cost > 0.0
        assert resp.metadata["provider"] == "foundry-gpt"

    def test_query_uses_max_completion_tokens(self):
        """GPT-5.2 requires max_completion_tokens, not max_tokens."""
        iface = self._make_interface()
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        iface.query("prompt", max_tokens=128)
        call_kwargs = iface._client.chat.completions.create.call_args.kwargs
        assert "max_completion_tokens" in call_kwargs
        assert call_kwargs["max_completion_tokens"] == 128
        assert "max_tokens" not in call_kwargs

    def test_query_does_not_pass_temperature(self):
        """GPT-5.2 rejects temperature; the interface must omit it."""
        iface = self._make_interface()
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        iface.query("prompt", temperature=0.0, max_tokens=16)
        call_kwargs = iface._client.chat.completions.create.call_args.kwargs
        assert "temperature" not in call_kwargs, (
            "temperature was forwarded to GPT-5.2 but the model does not accept it"
        )

    def test_query_passes_reasoning_effort(self):
        """reasoning_effort must be forwarded to suppress internal CoT."""
        iface = self._make_interface()
        iface._reasoning_effort = "none"
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        iface.query("prompt", max_tokens=16)
        call_kwargs = iface._client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("reasoning_effort") == "none"

    def test_reasoning_effort_in_metadata(self):
        iface = self._make_interface()
        iface._reasoning_effort = "none"
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        resp = iface.query("prompt", max_tokens=16)
        assert resp.metadata["reasoning_effort"] == "none"

    def test_factory_creates_foundry_gpt(self):
        with patch("model_interface.FoundryGPT52Interface.__init__", return_value=None):
            iface = create_model_interface("foundry-gpt", api_key="k")
            assert isinstance(iface, FoundryGPT52Interface)

    def test_factory_foundry_gpt_requires_key(self):
        with pytest.raises(ValueError, match="foundry-gpt requires api_key"):
            create_model_interface("foundry-gpt")


class TestFoundryKimiInterface:
    """Test FoundryKimiInterface against a mocked OpenAI client."""

    def _make_interface(self, reasoning_effort: str = "low") -> FoundryKimiInterface:
        with patch("model_interface.FoundryKimiInterface.__init__", lambda self, **kw: None):
            iface = FoundryKimiInterface.__new__(FoundryKimiInterface)
            iface.model_name        = FoundryKimiInterface.FOUNDRY_DEPLOYMENT
            iface._reasoning_effort = reasoning_effort
            iface._total_cost       = 0.0
            iface._total_tokens_input  = 0
            iface._total_tokens_output = 0
            iface._query_count      = 0
            iface.rate_limiter      = RateLimiter(rpm=6000, tpm=10_000_000)
            iface._client           = MagicMock()
            return iface

    def test_cost_properties(self):
        iface = self._make_interface()
        assert iface.cost_per_1k_input > 0
        assert iface.cost_per_1k_output > 0

    def test_query_returns_model_response(self):
        iface = self._make_interface()
        iface._client.chat.completions.create.return_value = _make_openai_completion(
            text="kimi answer", prompt_tokens=6, completion_tokens=2
        )
        resp = iface.query("Say 'test'", max_tokens=20)

        assert isinstance(resp, ModelResponse)
        assert resp.text == "kimi answer"
        assert resp.metadata["provider"] == "foundry-kimi"

    def test_query_uses_max_tokens_not_max_completion_tokens(self):
        iface = self._make_interface()
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        iface.query("prompt", max_tokens=64)
        call_kwargs = iface._client.chat.completions.create.call_args.kwargs
        assert "max_tokens" in call_kwargs
        assert call_kwargs["max_tokens"] == 64

    def test_query_passes_reasoning_effort_via_extra_body(self):
        """Kimi requires reasoning_effort in extra_body to produce visible text."""
        iface = self._make_interface()
        iface._reasoning_effort = "low"
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        iface.query("prompt", max_tokens=64)
        call_kwargs = iface._client.chat.completions.create.call_args.kwargs
        assert call_kwargs.get("extra_body") == {"reasoning_effort": "low"}

    def test_reasoning_effort_in_metadata(self):
        iface = self._make_interface()
        iface._reasoning_effort = "low"
        iface._client.chat.completions.create.return_value = _make_openai_completion()

        resp = iface.query("prompt", max_tokens=16)
        assert resp.metadata["reasoning_effort"] == "low"

    def test_factory_creates_foundry_kimi(self):
        with patch("model_interface.FoundryKimiInterface.__init__", return_value=None):
            iface = create_model_interface("foundry-kimi", api_key="k")
            assert isinstance(iface, FoundryKimiInterface)

    def test_factory_foundry_kimi_requires_key(self):
        with pytest.raises(ValueError, match="foundry-kimi requires api_key"):
            create_model_interface("foundry-kimi")


class TestFoundryClaudeInterface:
    """Test FoundryClaudeInterface against a mocked AnthropicFoundry client."""

    def _make_interface(self) -> FoundryClaudeInterface:
        with patch("model_interface.FoundryClaudeInterface.__init__", lambda self, **kw: None):
            iface = FoundryClaudeInterface.__new__(FoundryClaudeInterface)
            iface.model_name = FoundryClaudeInterface.FOUNDRY_DEPLOYMENT
            iface._total_cost = 0.0
            iface._total_tokens_input = 0
            iface._total_tokens_output = 0
            iface._query_count = 0
            iface.rate_limiter = RateLimiter(rpm=6000, tpm=10_000_000)
            iface._client = MagicMock()
            return iface

    def test_cost_properties(self):
        iface = self._make_interface()
        assert iface.cost_per_1k_input > 0
        assert iface.cost_per_1k_output > 0

    def test_query_returns_model_response(self):
        iface = self._make_interface()
        iface._client.messages.create.return_value = _make_anthropic_message(
            text="claude answer", input_tokens=7, output_tokens=3
        )
        resp = iface.query("Say 'test'", max_tokens=20)

        assert isinstance(resp, ModelResponse)
        assert resp.text == "claude answer"
        assert resp.tokens_input == 7
        assert resp.tokens_output == 3
        assert resp.cost > 0.0
        assert resp.metadata["provider"] == "foundry-claude"
        assert resp.metadata["stop_reason"] == "end_turn"

    def test_query_updates_statistics(self):
        iface = self._make_interface()
        iface._client.messages.create.return_value = _make_anthropic_message()

        iface.query("p1")
        iface.query("p2")
        stats = iface.statistics
        assert stats["total_queries"] == 2
        assert stats["total_cost"] > 0.0

    def test_factory_creates_foundry_claude(self):
        with patch("model_interface.FoundryClaudeInterface.__init__", return_value=None):
            iface = create_model_interface("foundry-claude", api_key="k")
            assert isinstance(iface, FoundryClaudeInterface)

    def test_factory_foundry_claude_requires_key(self):
        with pytest.raises(ValueError, match="foundry-claude requires api_key"):
            create_model_interface("foundry-claude")


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
    
    def test_create_curc_interface(self):
        """Test creating CURCInterface via factory."""
        iface = create_model_interface(
            "curc",
            base_url="http://localhost:8000",
            model="Qwen/Qwen2.5-72B-Instruct-AWQ",
        )
        assert isinstance(iface, CURCInterface)
        assert iface._base_url == "http://localhost:8000"
        assert iface.model_name == "Qwen/Qwen2.5-72B-Instruct-AWQ"

    def test_create_curc_interface_default_model(self):
        """Factory should use the recommended 72B model when none specified."""
        iface = create_model_interface("curc", base_url="http://localhost:8000")
        assert isinstance(iface, CURCInterface)
        assert "Qwen2.5-72B" in iface.model_name

    def test_create_curc_interface_custom_model(self):
        """Factory should accept alternate CURC models."""
        iface = create_model_interface(
            "curc",
            base_url="http://localhost:9999",
            model="hugging-quants/Meta-Llama-3.3-70B-Instruct-AWQ-INT4",
        )
        assert "Llama-3.3-70B" in iface.model_name

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
