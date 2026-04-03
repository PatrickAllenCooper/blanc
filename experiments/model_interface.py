"""
Model interface layer for LLM evaluation.

Provides unified interface for querying multiple foundation models.

Azure AI Foundry (primary platform — preferred over CURC wherever possible):
  gpt-5.2-chat        https://llm-defeasible-foundry.cognitiveservices.azure.com/
  Kimi-K2.5           https://llm-defeasible-foundry.services.ai.azure.com/openai/v1/
  claude-sonnet-4-6   https://llm-defeasible-foundry.services.ai.azure.com/anthropic/
  DeepSeek-R1         https://llm-defeasible-foundry.openai.azure.com/openai/v1/
  All share FOUNDRY_API_KEY.

CURC vLLM (only for models not available on Foundry):
  Qwen 2.5 72B / 32B for within-family scaling comparison.
  Accessed via SSH tunnel: http://localhost:8000/v1

Author: Patrick Cooper
Date: 2026-02-13
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import time
import hashlib
import json
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


@dataclass
class ModelResponse:
    """Standardized response format for all models."""
    
    text: str
    model: str
    tokens_input: int
    tokens_output: int
    cost: float
    latency: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            'text': self.text,
            'model': self.model,
            'tokens_input': self.tokens_input,
            'tokens_output': self.tokens_output,
            'cost': self.cost,
            'latency': self.latency,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'ModelResponse':
        """Create from dictionary."""
        return cls(**data)


class RateLimiter:
    """Simple rate limiter for API calls."""
    
    def __init__(self, rpm: int = 60, tpm: int = 100000):
        """
        Initialize rate limiter.
        
        Args:
            rpm: Requests per minute
            tpm: Tokens per minute
        """
        self.rpm = rpm
        self.tpm = tpm
        self.request_times: List[float] = []
        self.token_usage: List[tuple[float, int]] = []
        self.min_delay = 60.0 / rpm  # Minimum seconds between requests
    
    def wait_if_needed(self, estimated_tokens: int = 1000):
        """Wait if we're exceeding rate limits."""
        current_time = time.time()
        
        # Clean old entries (older than 1 minute)
        cutoff = current_time - 60
        self.request_times = [t for t in self.request_times if t > cutoff]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff]
        
        # Check RPM limit
        if len(self.request_times) >= self.rpm:
            sleep_time = 60 - (current_time - self.request_times[0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Check TPM limit
        recent_tokens = sum(tokens for _, tokens in self.token_usage)
        if recent_tokens + estimated_tokens > self.tpm:
            sleep_time = 60 - (current_time - self.token_usage[0][0])
            if sleep_time > 0:
                time.sleep(sleep_time)
        
        # Enforce minimum delay between requests
        if self.request_times:
            time_since_last = current_time - self.request_times[-1]
            if time_since_last < self.min_delay:
                time.sleep(self.min_delay - time_since_last)
        
        # Record this request
        self.request_times.append(time.time())
        self.token_usage.append((time.time(), estimated_tokens))


class ModelInterface(ABC):
    """Abstract base class for all model interfaces."""
    
    def __init__(self, model_name: str):
        """Initialize model interface."""
        self.model_name = model_name
        self._total_cost = 0.0
        self._total_tokens_input = 0
        self._total_tokens_output = 0
        self._query_count = 0
    
    @abstractmethod
    def query(
        self, 
        prompt: str, 
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """
        Query the model with a prompt.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature (0.0 = greedy)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional model-specific parameters
            
        Returns:
            ModelResponse with text, cost, tokens, etc.
        """
        pass
    
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query the model with text and optional images.

        Default implementation falls back to text-only ``query()`` when
        no images are provided.  Subclasses that support multimodal
        input should override this method with provider-specific logic.

        Args:
            prompt: Text prompt.
            images: List of ``PromptImage`` objects (from M5 encoder).
            temperature: Sampling temperature.
            max_tokens: Maximum tokens to generate.

        Returns:
            ModelResponse.

        Raises:
            NotImplementedError: If *images* is non-empty and the
                subclass has not implemented multimodal support.
        """
        if not images:
            return self.query(
                prompt, temperature=temperature, max_tokens=max_tokens, **kwargs,
            )
        raise NotImplementedError(
            f"{type(self).__name__} does not support multimodal input. "
            "Use a vision-capable model for M5 evaluation."
        )

    def batch_query(
        self,
        prompts: List[str],
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> List[ModelResponse]:
        """
        Query multiple prompts (default: sequential).
        
        Subclasses can override for true batch API support.
        
        Args:
            prompts: List of prompts
            temperature: Sampling temperature
            max_tokens: Maximum tokens per response
            **kwargs: Additional parameters
            
        Returns:
            List of ModelResponse objects
        """
        return [
            self.query(prompt, temperature, max_tokens, **kwargs)
            for prompt in prompts
        ]
    
    @property
    @abstractmethod
    def cost_per_1k_input(self) -> float:
        """Cost per 1K input tokens in USD."""
        pass
    
    @property
    @abstractmethod
    def cost_per_1k_output(self) -> float:
        """Cost per 1K output tokens in USD."""
        pass
    
    def calculate_cost(self, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost for a query."""
        cost_input = (tokens_input / 1000) * self.cost_per_1k_input
        cost_output = (tokens_output / 1000) * self.cost_per_1k_output
        return cost_input + cost_output
    
    def update_stats(self, response: ModelResponse):
        """Update running statistics."""
        self._total_cost += response.cost
        self._total_tokens_input += response.tokens_input
        self._total_tokens_output += response.tokens_output
        self._query_count += 1
    
    @property
    def statistics(self) -> dict:
        """Get usage statistics."""
        return {
            'model': self.model_name,
            'total_queries': self._query_count,
            'total_cost': self._total_cost,
            'total_tokens_input': self._total_tokens_input,
            'total_tokens_output': self._total_tokens_output,
            'avg_cost_per_query': self._total_cost / max(1, self._query_count),
            'avg_tokens_per_query': (self._total_tokens_input + self._total_tokens_output) / max(1, self._query_count)
        }


def _encode_image_base64(img) -> Optional[str]:
    """Read an image file and return its base64 encoding, or None."""
    import base64
    path = img.local_path
    if not path:
        logger.warning("Image for entity %r has no local_path; skipping.", getattr(img, "entity", "?"))
        return None
    if not Path(path).is_file():
        logger.warning("Image file not found: %s (entity %r); skipping.", path, getattr(img, "entity", "?"))
        return None
    return base64.b64encode(Path(path).read_bytes()).decode("ascii")


def _build_openai_multimodal_content(prompt: str, images: List) -> List[Dict[str, Any]]:
    """Build an OpenAI-format content array with text and base64 images.

    Respects ``PromptImage.placement``:
    - ``before_theory``: image block appears before the text block
    - ``inline_fact``: image block appears before the text block
      (correlates with ``[IMAGE:...]`` placeholders inside the text)
    - ``after_theory``: image block appears after the text block
    """
    import base64
    before: List[Dict[str, Any]] = []
    after: List[Dict[str, Any]] = []

    for img in images:
        b64 = _encode_image_base64(img)
        if b64 is None:
            continue
        block = {
            "type": "image_url",
            "image_url": {"url": f"data:{img.media_type};base64,{b64}"},
        }
        placement = getattr(img, "placement", "inline_fact")
        if placement == "after_theory":
            after.append(block)
        else:
            before.append(block)

    return before + [{"type": "text", "text": prompt}] + after


def _build_anthropic_multimodal_content(prompt: str, images: List) -> List[Dict[str, Any]]:
    """Build an Anthropic-format content array with text and base64 images.

    Respects ``PromptImage.placement`` (same ordering as the OpenAI builder).
    """
    import base64
    before: List[Dict[str, Any]] = []
    after: List[Dict[str, Any]] = []

    for img in images:
        b64 = _encode_image_base64(img)
        if b64 is None:
            continue
        block = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": img.media_type,
                "data": b64,
            },
        }
        placement = getattr(img, "placement", "inline_fact")
        if placement == "after_theory":
            after.append(block)
        else:
            before.append(block)

    return before + [{"type": "text", "text": prompt}] + after


class OpenAIInterface(ModelInterface):
    """OpenAI API interface for GPT-4o."""
    
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        """
        Initialize OpenAI interface.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default: gpt-4o)
        """
        super().__init__(model)
        
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai")
        
        self.client = OpenAI(api_key=api_key)
        self.rate_limiter = RateLimiter(rpm=500, tpm=80000)  # Tier 1 limits
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """Query GPT-4o with exponential backoff retry."""
        
        # Rate limiting
        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        
        start_time = time.time()
        
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            latency = time.time() - start_time
            
            text = response.choices[0].message.content or ""
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            cost = self.calculate_cost(tokens_input, tokens_output)
            
            result = ModelResponse(
                text=text,
                model=self.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'model_version': response.model,
                }
            )
            
            self.update_stats(result)
            return result
            
        except Exception as e:
            logger.warning("OpenAI API error: %s", e)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        start_time = time.time()
        content = _build_openai_multimodal_content(prompt, images)

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )
            latency = time.time() - start_time
            text = response.choices[0].message.content or ""
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            cost = self.calculate_cost(tokens_input, tokens_output)
            result = ModelResponse(
                text=text, model=self.model_name,
                tokens_input=tokens_input, tokens_output=tokens_output,
                cost=cost, latency=latency,
                metadata={
                    'finish_reason': response.choices[0].finish_reason,
                    'model_version': response.model,
                    'multimodal': True,
                    'num_images': len(images),
                },
            )
            self.update_stats(result)
            return result
        except Exception as e:
            logger.warning("OpenAI multimodal API error: %s", e)
            raise

    @property
    def cost_per_1k_input(self) -> float:
        """GPT-4o pricing."""
        return 0.0025  # $2.50 per 1M tokens = $0.0025 per 1K
    
    @property
    def cost_per_1k_output(self) -> float:
        """GPT-4o pricing."""
        return 0.01  # $10 per 1M tokens = $0.01 per 1K


class AzureOpenAIInterface(ModelInterface):
    """Azure OpenAI Service interface.

    Wraps the OpenAI SDK's AzureOpenAI client, which shares the same wire
    protocol as the direct OpenAI API but authenticates via an Azure endpoint,
    an API version, and a deployment name rather than a model string.

    Required environment / constructor arguments:
        endpoint:        https://<resource>.openai.azure.com
        api_key:         Azure resource key (or AAD token)
        api_version:     e.g. "2024-08-01-preview"
        deployment_name: the name given when deploying the model in Azure AI Studio
    """

    # Default Azure OpenAI pricing mirrors OpenAI pricing (USD per 1 K tokens).
    # Update when Microsoft revises its rate card.
    _PRICING: Dict[str, Dict[str, float]] = {
        "gpt-4o":       {"input": 0.0025, "output": 0.01},
        "gpt-4o-mini":  {"input": 0.00015, "output": 0.0006},
        "gpt-4":        {"input": 0.03,   "output": 0.06},
        "gpt-35-turbo": {"input": 0.0005, "output": 0.0015},
    }
    _DEFAULT_PRICING = {"input": 0.0025, "output": 0.01}  # Fallback: gpt-4o rates

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str = "2024-08-01-preview",
        model: Optional[str] = None,
        rpm: int = 240,
        tpm: int = 40000,
    ):
        """
        Initialize Azure OpenAI interface.

        Args:
            endpoint:        Azure OpenAI resource endpoint URL.
            api_key:         Azure OpenAI API key.
            deployment_name: Name of the deployed model in Azure AI Studio.
            api_version:     Azure OpenAI REST API version string.
            model:           Human-readable model name used for cost lookup and
                             statistics.  Defaults to deployment_name.
            rpm:             Requests per minute limit (Azure Standard S0 default).
            tpm:             Tokens per minute limit (Azure Standard S0 default).
        """
        super().__init__(model or deployment_name)

        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0")

        self.deployment_name = deployment_name
        self.api_version = api_version
        self.endpoint = endpoint

        self.client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self.rate_limiter = RateLimiter(rpm=rpm, tpm=tpm)

        # Resolve pricing: try exact name, then any key that is a prefix of model_name.
        pricing = self._PRICING.get(self.model_name)
        if pricing is None:
            for key, val in self._PRICING.items():
                if key in self.model_name.lower():
                    pricing = val
                    break
        self._pricing = pricing or self._DEFAULT_PRICING

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query an Azure-hosted model with exponential backoff retry."""

        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)

        start_time = time.time()

        try:
            response = self.client.chat.completions.create(
                model=self.deployment_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            latency = time.time() - start_time

            text = response.choices[0].message.content or ""
            tokens_input = response.usage.prompt_tokens
            tokens_output = response.usage.completion_tokens
            cost = self.calculate_cost(tokens_input, tokens_output)

            result = ModelResponse(
                text=text,
                model=self.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "deployment": self.deployment_name,
                    "api_version": self.api_version,
                    "endpoint": self.endpoint,
                },
            )

            self.update_stats(result)
            return result

        except Exception as e:
            logger.warning("Azure OpenAI API error: %s", e)
            raise

    @property
    def cost_per_1k_input(self) -> float:
        return self._pricing["input"]

    @property
    def cost_per_1k_output(self) -> float:
        return self._pricing["output"]


class AnthropicInterface(ModelInterface):
    """Anthropic API interface for Claude 3.5 Sonnet."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Anthropic interface.
        
        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-5-sonnet-20241022)
        """
        super().__init__(model)
        
        try:
            import anthropic
        except ImportError:
            raise ImportError("anthropic package not installed. Run: pip install anthropic")
        
        self.client = anthropic.Anthropic(api_key=api_key)
        self.rate_limiter = RateLimiter(rpm=50, tpm=40000)  # Tier 1 limits
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """Query Claude 3.5 Sonnet with exponential backoff retry."""
        
        # Rate limiting
        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        
        start_time = time.time()
        
        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )
            
            latency = time.time() - start_time
            
            # Extract response data
            text = response.content[0].text
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens
            cost = self.calculate_cost(tokens_input, tokens_output)
            
            result = ModelResponse(
                text=text,
                model=self.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                metadata={
                    'stop_reason': response.stop_reason,
                    'model_version': response.model,
                }
            )
            
            self.update_stats(result)
            return result
            
        except Exception as e:
            logger.warning("Anthropic API error: %s", e)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        start_time = time.time()
        content = _build_anthropic_multimodal_content(prompt, images)

        try:
            response = self.client.messages.create(
                model=self.model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": content}],
                **kwargs,
            )
            latency = time.time() - start_time
            text = response.content[0].text
            tokens_input = response.usage.input_tokens
            tokens_output = response.usage.output_tokens
            cost = self.calculate_cost(tokens_input, tokens_output)
            result = ModelResponse(
                text=text, model=self.model_name,
                tokens_input=tokens_input, tokens_output=tokens_output,
                cost=cost, latency=latency,
                metadata={
                    'stop_reason': response.stop_reason,
                    'model_version': response.model,
                    'multimodal': True,
                    'num_images': len(images),
                },
            )
            self.update_stats(result)
            return result
        except Exception as e:
            logger.warning("Anthropic multimodal API error: %s", e)
            raise

    @property
    def cost_per_1k_input(self) -> float:
        """Claude 3.5 Sonnet pricing."""
        return 0.003  # $3 per 1M tokens = $0.003 per 1K
    
    @property
    def cost_per_1k_output(self) -> float:
        """Claude 3.5 Sonnet pricing."""
        return 0.015  # $15 per 1M tokens = $0.015 per 1K


class GoogleInterface(ModelInterface):
    """Google AI API interface for Gemini 1.5 Pro."""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        """
        Initialize Google interface.
        
        Args:
            api_key: Google API key
            model: Model name (default: gemini-1.5-pro)
        """
        super().__init__(model)
        
        try:
            import google.generativeai as genai
        except ImportError:
            raise ImportError("google-generativeai package not installed. Run: pip install google-generativeai")
        
        genai.configure(api_key=api_key)
        self.genai_model = genai.GenerativeModel(model)
        self.rate_limiter = RateLimiter(rpm=2, tpm=32000)  # Free tier limits (very restrictive!)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """Query Gemini 1.5 Pro with exponential backoff retry."""
        
        # Rate limiting (very strict for free tier)
        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        
        start_time = time.time()
        
        try:
            generation_config = {
                'temperature': temperature,
                'max_output_tokens': max_tokens,
            }
            
            response = self.genai_model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            latency = time.time() - start_time
            
            # Extract response data
            text = response.text
            
            # Gemini doesn't always provide token counts
            # Use rough estimate if not available
            if hasattr(response, 'usage_metadata'):
                tokens_input = response.usage_metadata.prompt_token_count
                tokens_output = response.usage_metadata.candidates_token_count
            else:
                tokens_input = len(prompt) // 4  # Rough estimate
                tokens_output = len(text) // 4
            
            cost = self.calculate_cost(tokens_input, tokens_output)
            
            result = ModelResponse(
                text=text,
                model=self.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                metadata={
                    'finish_reason': response.candidates[0].finish_reason if response.candidates else None,
                }
            )
            
            self.update_stats(result)
            return result
            
        except Exception as e:
            logger.warning("Google AI API error: %s", e)
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

        import base64
        try:
            from google.generativeai.types import content_types
        except ImportError:
            pass

        self.rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        start_time = time.time()

        before_parts = []
        after_parts = []
        for img in images:
            path = img.local_path
            if path and Path(path).is_file():
                raw = Path(path).read_bytes()
                part = {"mime_type": img.media_type, "data": raw}
                placement = getattr(img, "placement", "inline_fact")
                if placement == "after_theory":
                    after_parts.append(part)
                else:
                    before_parts.append(part)
        parts = before_parts + [prompt] + after_parts

        try:
            generation_config = {
                'temperature': temperature,
                'max_output_tokens': max_tokens,
            }
            response = self.genai_model.generate_content(
                parts, generation_config=generation_config,
            )
            latency = time.time() - start_time
            text = response.text
            if hasattr(response, 'usage_metadata'):
                tokens_input = response.usage_metadata.prompt_token_count
                tokens_output = response.usage_metadata.candidates_token_count
            else:
                tokens_input = len(prompt) // 4
                tokens_output = len(text) // 4
            cost = self.calculate_cost(tokens_input, tokens_output)
            result = ModelResponse(
                text=text, model=self.model_name,
                tokens_input=tokens_input, tokens_output=tokens_output,
                cost=cost, latency=latency,
                metadata={
                    'finish_reason': (response.candidates[0].finish_reason
                                      if response.candidates else None),
                    'multimodal': True, 'num_images': len(images),
                },
            )
            self.update_stats(result)
            return result
        except Exception as e:
            logger.warning("Google AI multimodal error: %s", e)
            raise

    @property
    def cost_per_1k_input(self) -> float:
        """Gemini 1.5 Pro pricing (using current estimate)."""
        return 0.00125  # $1.25 per 1M tokens = $0.00125 per 1K
    
    @property
    def cost_per_1k_output(self) -> float:
        """Gemini 1.5 Pro pricing."""
        return 0.005  # $5 per 1M tokens = $0.005 per 1K


class OllamaInterface(ModelInterface):
    """Local Llama interface via Ollama."""
    
    def __init__(self, model: str = "llama3:70b", host: str = "http://localhost:11434"):
        """
        Initialize Ollama interface.
        
        Args:
            model: Model name (e.g., "llama3:70b" or "llama3:8b")
            host: Ollama server URL (default: http://localhost:11434)
        """
        super().__init__(model)
        self._host = host
        
        # Check if ollama is available
        import subprocess
        try:
            result = subprocess.run(
                ['ollama', 'list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                raise RuntimeError("Ollama is not running. Start it with: ollama serve")
        except FileNotFoundError:
            raise ImportError("Ollama not installed. Install from https://ollama.ai/")
        
        # No rate limiting needed for local models
        self.rate_limiter = None
    
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """Query local Llama model via Ollama."""
        
        import subprocess
        import json as json_module
        
        start_time = time.time()
        
        try:
            # Prepare request
            request_data = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens,
                }
            }
            
            # Call ollama via subprocess
            result = subprocess.run(
                ['ollama', 'run', self.model_name, '--format', 'json'],
                input=prompt,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"Ollama error: {result.stderr}")
            
            latency = time.time() - start_time
            
            # Parse response
            text = result.stdout.strip()
            
            # Estimate tokens (no exact counts from Ollama)
            tokens_input = len(prompt) // 4
            tokens_output = len(text) // 4
            cost = 0.0  # Local model, no cost
            
            response_obj = ModelResponse(
                text=text,
                model=self.model_name,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                metadata={
                    'local': True,
                    'estimated_tokens': True
                }
            )
            
            self.update_stats(response_obj)
            return response_obj
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("Ollama query timed out after 120s")
        except Exception as e:
            logger.warning("Ollama error: %s", e)
            raise
    
    @property
    def cost_per_1k_input(self) -> float:
        """Local model, no cost."""
        return 0.0
    
    @property
    def cost_per_1k_output(self) -> float:
        """Local model, no cost."""
        return 0.0


def _strip_thinking_tokens(text: str) -> tuple[str, str]:
    """
    Strip DeepSeek-R1-style <think>...</think> blocks from a model response.

    Returns (visible_text, thinking_text).  visible_text is what the decoder
    sees; thinking_text is preserved for analysis / metadata logging.

    DeepSeek-R1-Distill models emit all chain-of-thought inside a
    <think>...</think> block, then produce the final answer after </think>.
    Passing the thinking block to the cascading decoder would cause every
    instance to fall through to the expensive D3 semantic parser and still
    likely fail, so stripping is necessary before decoding.
    """
    import re
    think_pattern = re.compile(r"<think>(.*?)</think>\s*", re.DOTALL)
    match = think_pattern.search(text)
    if match:
        thinking = match.group(1).strip()
        visible  = think_pattern.sub("", text).strip()
        return visible, thinking
    return text, ""


class CURCInterface(ModelInterface):
    """
    Interface for CURC-hosted open-source models via vLLM.

    The CURC LLM Hoster (Patrick Cooper, 2026) runs a vLLM inference server
    on Alpine's A100 GPU nodes and exposes an OpenAI-compatible REST API.
    Access is via SSH tunnel (local) or directly from within the cluster:

        http://localhost:8000/v1   (via SSH tunnel on local machine)
        http://<compute-node>:8000/v1  (from within the cluster)

    Chosen open-source models for this evaluation (all fit on one A100 80 GB,
    all available in AWQ 4-bit quantisation):

        casperhansen/deepseek-r1-distill-llama-70b-awq  (~35 GB)
            DeepSeek-R1 reasoning capability distilled into Llama 3 70B.
            Open-source reasoning comparator to GPT-5.2 and Kimi-K2.5.
            Emits <think>...</think> blocks; the interface strips these
            automatically before the response reaches the decoder.

        Qwen/Qwen2.5-72B-Instruct-AWQ                  (~36 GB)
            Top general-instruction open-source model (February 2026).
            Open-source comparator to Claude Sonnet 4.6.

        Qwen/Qwen2.5-32B-Instruct-AWQ                  (~16 GB)
            Within-family scaling comparator (32B vs 72B).
            Fastest of the three; submit with INSTANCE_LIMIT=120.

    Scientific structure (6 models total, 3 Foundry + 3 CURC):

        Reasoning tier   : GPT-5.2-chat (Foundry) · Kimi-K2.5 (Foundry)
                           DeepSeek-R1-Distill-70B (CURC)
        Instruction tier : claude-sonnet-4-6 (Foundry)
                           Qwen 2.5 72B (CURC)
        Scaling tier     : Qwen 2.5 32B (CURC, within-family vs 72B)
    """

    def __init__(
        self,
        base_url: str,
        model: str = "Qwen/Qwen2.5-72B-Instruct-AWQ",
        api_key: str = "not-needed",
        rpm: int = 600,
        timeout: int = 120,
    ):
        """
        Initialize CURC vLLM interface.

        Args:
            base_url:  Base URL of the vLLM server (e.g. http://localhost:8000).
                       The /v1 suffix is appended automatically.
            model:     Hugging Face model ID served by the vLLM instance.
            api_key:   vLLM accepts any non-empty key; defaults to 'not-needed'.
            rpm:       Maximum requests per minute (server-side limit varies by
                       model and node count; 600 is safe for single-user runs).
            timeout:   Per-request timeout in seconds.
        """
        super().__init__(model)
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._rate_limiter = RateLimiter(rpm=rpm, tpm=10_000_000)  # tokens unlimited locally

    def _get_client(self):
        """Return an OpenAI client pointed at the vLLM server."""
        import openai
        return openai.OpenAI(
            base_url=f"{self._base_url}/v1",
            api_key=self._api_key,
            timeout=self._timeout,
        )

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=2, min=5, max=60),
           reraise=True)
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query the CURC vLLM server via the OpenAI chat completions API."""
        self._rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        start = time.time()

        client = self._get_client()
        completion = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency = time.time() - start
        raw_text = completion.choices[0].message.content or ""
        usage    = completion.usage

        # Strip <think>...</think> blocks emitted by DeepSeek-R1-Distill models.
        # The thinking content is preserved in metadata for analysis; only the
        # visible answer reaches the cascading decoder.
        visible_text, thinking_text = _strip_thinking_tokens(raw_text)

        response = ModelResponse(
            text=visible_text,
            model=self.model_name,
            tokens_input=usage.prompt_tokens if usage else len(prompt) // 4,
            tokens_output=usage.completion_tokens if usage else len(raw_text) // 4,
            cost=0.0,  # Cluster compute; no API billing
            latency=latency,
            metadata={
                "provider":      "curc_vllm",
                "base_url":      self._base_url,
                "finish_reason": completion.choices[0].finish_reason,
                "thinking":      thinking_text or None,
            },
        )
        self.update_stats(response)
        return response

    @retry(stop=stop_after_attempt(5),
           wait=wait_exponential(multiplier=2, min=5, max=60),
           reraise=True)
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)

        self._rate_limiter.wait_if_needed(estimated_tokens=len(prompt) // 4 + max_tokens)
        start = time.time()
        content = _build_openai_multimodal_content(prompt, images)
        client = self._get_client()

        completion = client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": content}],
            temperature=temperature,
            max_tokens=max_tokens,
        )

        latency = time.time() - start
        raw_text = completion.choices[0].message.content or ""
        usage = completion.usage
        visible_text, thinking_text = _strip_thinking_tokens(raw_text)

        response = ModelResponse(
            text=visible_text,
            model=self.model_name,
            tokens_input=usage.prompt_tokens if usage else len(prompt) // 4,
            tokens_output=usage.completion_tokens if usage else len(raw_text) // 4,
            cost=0.0,
            latency=latency,
            metadata={
                "provider": "curc_vllm",
                "base_url": self._base_url,
                "finish_reason": completion.choices[0].finish_reason,
                "thinking": thinking_text or None,
                "multimodal": True,
                "num_images": len(images),
            },
        )
        self.update_stats(response)
        return response

    @property
    def cost_per_1k_input(self) -> float:
        return 0.0  # Cluster compute, no API cost

    @property
    def cost_per_1k_output(self) -> float:
        return 0.0


class FoundryGPT52Interface(ModelInterface):
    """
    Azure AI Foundry interface for GPT-5.2-chat.

    GPT-5.2 is a hybrid reasoning model.  It supports a reasoning_effort
    parameter ('none', 'low', 'medium', 'high', 'xhigh').  The default here
    is 'none', which disables internal chain-of-thought and makes the model
    behave like a standard chat completion — essential for token-efficient
    structured-selection tasks in the evaluation pipeline.

    Practical notes (confirmed by live testing 2026-02-19):
      - temperature is not accepted; the interface silently omits it.
      - max_tokens maps to max_completion_tokens.
      - reasoning_effort='none' → clean stop, ~5 tokens for a one-word reply.
      - reasoning_effort='low'  → mild CoT, still very fast.

    Rate limits (Foundry Global Standard, as of 2026-02-19):
        250,000 TPM / 2,500 RPM
    """

    # Pricing per OpenAI public rate card (USD per 1K tokens).
    _COST_PER_1K_INPUT  = 0.00175  # $1.75 per 1M input tokens
    _COST_PER_1K_OUTPUT = 0.014    # $14.00 per 1M output tokens

    FOUNDRY_ENDPOINT    = "https://llm-defeasible-foundry.cognitiveservices.azure.com/"
    FOUNDRY_DEPLOYMENT  = "gpt-5.2-chat"
    FOUNDRY_API_VERSION = "2024-12-01-preview"

    def __init__(
        self,
        api_key: str,
        endpoint: str = FOUNDRY_ENDPOINT,
        deployment: str = FOUNDRY_DEPLOYMENT,
        api_version: str = FOUNDRY_API_VERSION,
        reasoning_effort: str = "none",
        rpm: int = 2500,
        tpm: int = 250_000,
    ):
        super().__init__(deployment)
        try:
            from openai import AzureOpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0")

        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
        self._deployment       = deployment
        self._reasoning_effort = reasoning_effort
        self.rate_limiter      = RateLimiter(rpm=rpm, tpm=tpm)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query GPT-5.2-chat with exponential backoff retry.

        Note: GPT-5.2 is a reasoning model that does not accept a temperature
        parameter (only the API default of 1 is supported).  The temperature
        argument is accepted here for interface compatibility but is not
        forwarded to the API.
        """
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()

        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[{"role": "user", "content": prompt}],
                max_completion_tokens=max_tokens,
                reasoning_effort=self._reasoning_effort,
                # temperature is intentionally omitted: GPT-5.2 rejects it
            )
        except Exception as e:
            logger.warning("Foundry GPT-5.2 API error: %s", e)
            raise

        latency = time.time() - start
        text = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in  = usage.prompt_tokens     if usage else len(prompt) // 4
        tokens_out = usage.completion_tokens if usage else len(text) // 4
        cost = self.calculate_cost(tokens_in, tokens_out)

        result = ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost=cost,
            latency=latency,
            metadata={
                "finish_reason":     response.choices[0].finish_reason,
                "deployment":        self._deployment,
                "provider":          "foundry-gpt",
                "reasoning_effort":  self._reasoning_effort,
            },
        )
        self.update_stats(result)
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()
        content = _build_openai_multimodal_content(prompt, images)
        try:
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[{"role": "user", "content": content}],
                max_completion_tokens=max_tokens,
                reasoning_effort=self._reasoning_effort,
            )
        except Exception as e:
            logger.warning("Foundry GPT-5.2 multimodal error: %s", e)
            raise

        latency = time.time() - start
        text = response.choices[0].message.content or ""
        usage = response.usage
        tokens_in  = usage.prompt_tokens     if usage else len(prompt) // 4
        tokens_out = usage.completion_tokens if usage else len(text) // 4
        cost = self.calculate_cost(tokens_in, tokens_out)
        result = ModelResponse(
            text=text, model=self.model_name,
            tokens_input=tokens_in, tokens_output=tokens_out,
            cost=cost, latency=latency,
            metadata={
                "finish_reason": response.choices[0].finish_reason,
                "deployment": self._deployment,
                "provider": "foundry-gpt",
                "multimodal": True, "num_images": len(images),
            },
        )
        self.update_stats(result)
        return result

    @property
    def cost_per_1k_input(self) -> float:
        return self._COST_PER_1K_INPUT

    @property
    def cost_per_1k_output(self) -> float:
        return self._COST_PER_1K_OUTPUT


class FoundryKimiInterface(ModelInterface):
    """
    Azure AI Foundry interface for Kimi-K2.5.

    Kimi-K2.5 (Moonshot AI) is a hybrid reasoning model served via an
    OpenAI-compatible endpoint on Azure AI Foundry.  It supports a
    reasoning_effort parameter passed via extra_body; supported values are
    'low', 'medium', and 'high' ('none' and 'minimal' are rejected by the
    endpoint).  The default is 'low', which minimises chain-of-thought
    while still producing visible text output.

    Practical notes (confirmed by live testing 2026-02-19):
      - Without reasoning_effort, the model consumes all tokens on internal
        reasoning and returns None content.
      - reasoning_effort='low' → clean stop, ~25 tokens for a one-word reply.
      - temperature IS accepted (unlike GPT-5.2).

    Rate limits (Foundry Global Standard, as of 2026-02-19):
        250,000 TPM / 250 RPM
    """

    _COST_PER_1K_INPUT  = 0.0014  # USD per 1K tokens (Moonshot estimate)
    _COST_PER_1K_OUTPUT = 0.0028

    FOUNDRY_BASE_URL   = "https://llm-defeasible-foundry.services.ai.azure.com/openai/v1/"
    FOUNDRY_DEPLOYMENT = "Kimi-K2.5"

    def __init__(
        self,
        api_key: str,
        base_url: str = FOUNDRY_BASE_URL,
        model: str = FOUNDRY_DEPLOYMENT,
        reasoning_effort: str = "low",
        rpm: int = 250,
        tpm: int = 250_000,
    ):
        super().__init__(model)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0")

        self._client           = OpenAI(base_url=base_url, api_key=api_key)
        self._reasoning_effort = reasoning_effort
        self.rate_limiter      = RateLimiter(rpm=rpm, tpm=tpm)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query Kimi-K2.5 with exponential backoff retry.

        reasoning_effort is passed via extra_body (supported: 'low', 'medium',
        'high').  Without it the model allocates all completion tokens to
        internal chain-of-thought and returns no visible text.
        """
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()

        try:
            completion = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                extra_body={"reasoning_effort": self._reasoning_effort},
            )
        except Exception as e:
            logger.warning("Foundry Kimi API error: %s", e)
            raise

        latency = time.time() - start
        text = completion.choices[0].message.content or ""
        usage = completion.usage
        tokens_in  = usage.prompt_tokens     if usage else len(prompt) // 4
        tokens_out = usage.completion_tokens if usage else len(text) // 4
        cost = self.calculate_cost(tokens_in, tokens_out)

        result = ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost=cost,
            latency=latency,
            metadata={
                "finish_reason":    completion.choices[0].finish_reason,
                "provider":         "foundry-kimi",
                "reasoning_effort": self._reasoning_effort,
            },
        )
        self.update_stats(result)
        return result

    @property
    def cost_per_1k_input(self) -> float:
        return self._COST_PER_1K_INPUT

    @property
    def cost_per_1k_output(self) -> float:
        return self._COST_PER_1K_OUTPUT


class FoundryClaudeInterface(ModelInterface):
    """
    Azure AI Foundry interface for Claude Sonnet 4.6.

    Uses the AnthropicFoundry client (anthropic>=0.40) which wraps the
    standard Anthropic Messages API against the Foundry-managed endpoint.

    Rate limits (Foundry Global Standard, as of 2026-02-19):
        250,000 TPM / 250 RPM
    """

    _COST_PER_1K_INPUT  = 0.003   # Claude Sonnet pricing (USD per 1K)
    _COST_PER_1K_OUTPUT = 0.015

    FOUNDRY_ENDPOINT   = "https://llm-defeasible-foundry.services.ai.azure.com/anthropic/"
    FOUNDRY_DEPLOYMENT = "claude-sonnet-4-6"

    def __init__(
        self,
        api_key: str,
        endpoint: str = FOUNDRY_ENDPOINT,
        model: str = FOUNDRY_DEPLOYMENT,
        rpm: int = 250,
        tpm: int = 250_000,
    ):
        super().__init__(model)
        try:
            from anthropic import AnthropicFoundry
        except ImportError:
            raise ImportError(
                "anthropic package not installed or too old for AnthropicFoundry. "
                "Run: pip install 'anthropic>=0.40'"
            )

        self._client = AnthropicFoundry(api_key=api_key, base_url=endpoint)
        self.rate_limiter = RateLimiter(rpm=rpm, tpm=tpm)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Query claude-sonnet-4-6 via AnthropicFoundry with exponential backoff."""
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()

        try:
            response = self._client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning("Foundry Claude API error: %s", e)
            raise

        latency = time.time() - start
        text = response.content[0].text
        tokens_in  = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost = self.calculate_cost(tokens_in, tokens_out)

        result = ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=tokens_in,
            tokens_output=tokens_out,
            cost=cost,
            latency=latency,
            metadata={
                "stop_reason": response.stop_reason,
                "provider": "foundry-claude",
            },
        )
        self.update_stats(result)
        return result

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        if not images:
            return self.query(prompt, temperature=temperature, max_tokens=max_tokens, **kwargs)
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()
        content = _build_anthropic_multimodal_content(prompt, images)
        try:
            response = self._client.messages.create(
                model=self.model_name,
                messages=[{"role": "user", "content": content}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning("Foundry Claude multimodal error: %s", e)
            raise
        latency = time.time() - start
        text = response.content[0].text
        tokens_in  = response.usage.input_tokens
        tokens_out = response.usage.output_tokens
        cost = self.calculate_cost(tokens_in, tokens_out)
        result = ModelResponse(
            text=text, model=self.model_name,
            tokens_input=tokens_in, tokens_output=tokens_out,
            cost=cost, latency=latency,
            metadata={
                "stop_reason": response.stop_reason,
                "provider": "foundry-claude",
                "multimodal": True, "num_images": len(images),
            },
        )
        self.update_stats(result)
        return result

    @property
    def cost_per_1k_input(self) -> float:
        return self._COST_PER_1K_INPUT

    @property
    def cost_per_1k_output(self) -> float:
        return self._COST_PER_1K_OUTPUT


class FoundryDeepSeekInterface(ModelInterface):
    """
    Azure AI Foundry interface for DeepSeek-R1.

    DeepSeek-R1 is available as a Direct-from-Azure Foundry Model (Global
    Standard), accessed via the Azure OpenAI v1 endpoint using the standard
    openai.OpenAI client with a custom base_url.  It emits chain-of-thought
    reasoning inside <think>...</think> tags; these are stripped before the
    cascading decoder sees the response, with thinking content preserved in
    metadata["thinking"] for secondary analysis.

    Rate limits (Foundry Direct, as of 2026-02-19):
        5,000,000 TPM / 5,000 RPM  — substantially higher than other Foundry models.

    Endpoint pattern:
        https://llm-defeasible-foundry.openai.azure.com/openai/v1/
    Deployment name in the Foundry portal (set at deploy time, e.g. "DeepSeek-R1").
    """

    _COST_PER_1K_INPUT  = 0.00135   # DeepSeek-R1 Azure pricing (USD per 1K tokens)
    _COST_PER_1K_OUTPUT = 0.0054

    # Endpoint confirmed from Foundry portal (2026-02-25).
    # Note: uses services.ai.azure.com (same subdomain as Kimi/Claude),
    # NOT openai.azure.com which was the pre-deployment placeholder.
    # Rate limit: 250 RPM / 250K TPM (Global Standard, same as Kimi/Claude).
    FOUNDRY_BASE_URL   = "https://llm-defeasible-foundry.services.ai.azure.com/openai/v1/"
    FOUNDRY_DEPLOYMENT = "DeepSeek-R1"

    def __init__(
        self,
        api_key: str,
        base_url: str = FOUNDRY_BASE_URL,
        model: str = FOUNDRY_DEPLOYMENT,
        rpm: int = 250,
        tpm: int = 250_000,
    ):
        super().__init__(model)
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError("openai package not installed. Run: pip install openai>=1.0")

        self._client      = OpenAI(base_url=base_url, api_key=api_key)
        self.rate_limiter = RateLimiter(rpm=rpm, tpm=tpm)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True,
    )
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        **kwargs,
    ) -> ModelResponse:
        """Query DeepSeek-R1 via Foundry with thinking-token stripping.

        max_tokens defaults to 1024 (not 512) because DeepSeek-R1 consumes
        some tokens on internal chain-of-thought before emitting the visible
        answer.  Increasing the budget ensures the answer is not truncated.
        """
        self.rate_limiter.wait_if_needed(len(prompt) // 4 + max_tokens)
        start = time.time()

        try:
            completion = self._client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            logger.warning("Foundry DeepSeek API error: %s", e)
            raise

        latency  = time.time() - start
        raw_text = completion.choices[0].message.content or ""
        usage    = completion.usage

        visible_text, thinking_text = _strip_thinking_tokens(raw_text)

        result = ModelResponse(
            text=visible_text,
            model=self.model_name,
            tokens_input=usage.prompt_tokens     if usage else len(prompt) // 4,
            tokens_output=usage.completion_tokens if usage else len(raw_text) // 4,
            cost=self.calculate_cost(
                usage.prompt_tokens if usage else len(prompt) // 4,
                usage.completion_tokens if usage else len(raw_text) // 4,
            ),
            latency=latency,
            metadata={
                "finish_reason": completion.choices[0].finish_reason,
                "provider":      "foundry-deepseek",
                "thinking":      thinking_text or None,
            },
        )
        self.update_stats(result)
        return result

    @property
    def cost_per_1k_input(self) -> float:
        return self._COST_PER_1K_INPUT

    @property
    def cost_per_1k_output(self) -> float:
        return self._COST_PER_1K_OUTPUT


class MockModelInterface(ModelInterface):
    """Mock model for testing without API calls."""
    
    def __init__(self, model_name: str = "mock-model"):
        """Initialize mock model."""
        super().__init__(model_name)
        self.responses = []
    
    def set_responses(self, responses: List[str]):
        """Set canned responses for testing."""
        self.responses = responses
    
    def query(
        self,
        prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs
    ) -> ModelResponse:
        """Return mock response."""
        
        # Use first response if available, else echo prompt
        if self.responses:
            text = self.responses.pop(0)
        else:
            text = f"Mock response to: {prompt[:50]}..."
        
        tokens_input = len(prompt) // 4  # Rough estimate
        tokens_output = len(text) // 4
        
        result = ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=0.0,
            latency=0.001,
            metadata={'mock': True}
        )
        
        self.update_stats(result)
        return result

    def query_multimodal(
        self,
        prompt: str,
        images: Optional[List] = None,
        temperature: float = 0.0,
        max_tokens: int = 512,
        **kwargs,
    ) -> ModelResponse:
        """Mock multimodal query -- records image metadata, returns canned response."""
        if self.responses:
            text = self.responses.pop(0)
        else:
            text = f"Mock response to: {prompt[:50]}..."

        tokens_input = len(prompt) // 4
        tokens_output = len(text) // 4

        result = ModelResponse(
            text=text,
            model=self.model_name,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            cost=0.0,
            latency=0.001,
            metadata={
                'mock': True,
                'multimodal': bool(images),
                'num_images': len(images) if images else 0,
                'image_entities': [img.entity for img in images] if images else [],
            },
        )
        self.update_stats(result)
        return result

    @property
    def cost_per_1k_input(self) -> float:
        return 0.0
    
    @property
    def cost_per_1k_output(self) -> float:
        return 0.0


def create_model_interface(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs
) -> ModelInterface:
    """
    Factory function to create model interfaces.

    Args:
        provider: One of 'openai', 'azure', 'anthropic', 'google', 'curc',
                  'ollama', 'foundry-gpt', 'foundry-kimi', 'foundry-claude', 'mock'
        api_key: API key (if required)
        model: Specific model name (optional)
        **kwargs: Additional provider-specific arguments.
            For 'azure': endpoint (str, required), deployment_name (str, required),
                         api_version (str, optional), rpm (int), tpm (int).
            For 'foundry-gpt': endpoint (str, optional) - defaults to Foundry endpoint.
            For 'foundry-kimi': base_url (str, optional) - defaults to Foundry endpoint.
            For 'foundry-claude': endpoint (str, optional) - defaults to Foundry endpoint.

    Returns:
        ModelInterface instance
    """
    provider = provider.lower()

    if provider == 'openai':
        if not api_key:
            raise ValueError("OpenAI requires api_key")
        model = model or "gpt-4o"
        return OpenAIInterface(api_key=api_key, model=model)

    elif provider == 'azure':
        endpoint = kwargs.pop('endpoint', None)
        deployment_name = kwargs.pop('deployment_name', None)
        if not api_key:
            raise ValueError("Azure OpenAI requires api_key")
        if not endpoint:
            raise ValueError("Azure OpenAI requires endpoint")
        if not deployment_name:
            raise ValueError("Azure OpenAI requires deployment_name")
        return AzureOpenAIInterface(
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=deployment_name,
            model=model,
            **kwargs,
        )

    elif provider == 'anthropic':
        if not api_key:
            raise ValueError("Anthropic requires api_key")
        model = model or "claude-3-5-sonnet-20241022"
        return AnthropicInterface(api_key=api_key, model=model)

    elif provider == 'google':
        if not api_key:
            raise ValueError("Google requires api_key")
        model = model or "gemini-1.5-pro"
        return GoogleInterface(api_key=api_key, model=model)

    elif provider == 'curc':
        base_url = kwargs.pop('base_url', None) or 'http://localhost:8000'
        model = model or "Qwen/Qwen2.5-72B-Instruct-AWQ"
        return CURCInterface(base_url=base_url, model=model, **kwargs)

    elif provider == 'ollama':
        model = model or "llama3:8b"
        return OllamaInterface(model=model, host=kwargs.get("host", "http://localhost:11434"))

    elif provider == 'foundry-gpt':
        if not api_key:
            raise ValueError("foundry-gpt requires api_key (FOUNDRY_API_KEY)")
        endpoint         = kwargs.pop('endpoint', FoundryGPT52Interface.FOUNDRY_ENDPOINT)
        deployment       = model or kwargs.pop('deployment', FoundryGPT52Interface.FOUNDRY_DEPLOYMENT)
        api_version      = kwargs.pop('api_version', FoundryGPT52Interface.FOUNDRY_API_VERSION)
        reasoning_effort = kwargs.pop('reasoning_effort', 'none')
        return FoundryGPT52Interface(
            api_key=api_key,
            endpoint=endpoint,
            deployment=deployment,
            api_version=api_version,
            reasoning_effort=reasoning_effort,
            **kwargs,
        )

    elif provider == 'foundry-kimi':
        if not api_key:
            raise ValueError("foundry-kimi requires api_key (FOUNDRY_API_KEY)")
        base_url         = kwargs.pop('base_url', FoundryKimiInterface.FOUNDRY_BASE_URL)
        model            = model or FoundryKimiInterface.FOUNDRY_DEPLOYMENT
        reasoning_effort = kwargs.pop('reasoning_effort', 'low')
        return FoundryKimiInterface(
            api_key=api_key, base_url=base_url, model=model,
            reasoning_effort=reasoning_effort, **kwargs,
        )

    elif provider == 'foundry-claude':
        if not api_key:
            raise ValueError("foundry-claude requires api_key (FOUNDRY_API_KEY)")
        endpoint = kwargs.pop('endpoint', FoundryClaudeInterface.FOUNDRY_ENDPOINT)
        model = model or FoundryClaudeInterface.FOUNDRY_DEPLOYMENT
        return FoundryClaudeInterface(api_key=api_key, endpoint=endpoint, model=model, **kwargs)

    elif provider == 'foundry-deepseek':
        if not api_key:
            raise ValueError("foundry-deepseek requires api_key (FOUNDRY_API_KEY)")
        base_url = kwargs.pop('base_url', FoundryDeepSeekInterface.FOUNDRY_BASE_URL)
        model    = model or FoundryDeepSeekInterface.FOUNDRY_DEPLOYMENT
        return FoundryDeepSeekInterface(api_key=api_key, base_url=base_url, model=model, **kwargs)

    elif provider == 'mock':
        model = model or "mock-model"
        return MockModelInterface(model_name=model)

    else:
        raise ValueError(
            f"Unknown provider: {provider}. "
            "Available: openai, azure, curc, anthropic, google, ollama, "
            "foundry-gpt, foundry-kimi, foundry-claude, mock"
        )


if __name__ == "__main__":
    # Quick test
    print("Model Interface Module")
    print("=" * 50)
    
    # Test mock model
    mock = MockModelInterface("test-model")
    mock.set_responses(["This is a test response"])
    
    response = mock.query("Test prompt")
    print(f"\nMock Response:")
    print(f"  Text: {response.text}")
    print(f"  Tokens: {response.tokens_input} in, {response.tokens_output} out")
    print(f"  Cost: ${response.cost:.4f}")
    
    print(f"\nStatistics:")
    for key, value in mock.statistics.items():
        print(f"  {key}: {value}")
    
    print("\n✅ Base interface module working!")
