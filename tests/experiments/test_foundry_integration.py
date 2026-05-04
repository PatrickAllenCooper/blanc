"""
Integration tests for Azure AI Foundry endpoints.

These tests make real HTTP calls to the deployed models and are therefore:
  - Skipped automatically when FOUNDRY_API_KEY is not set in the environment.
  - Excluded from the default pytest run; run explicitly with:
      pytest -m integration tests/experiments/test_foundry_integration.py -v

Each test verifies that the endpoint is reachable and responds with token
counts.  GPT-5.2 and Kimi-K2.5 may consume internal "reasoning" tokens
before producing visible text, so assertions are written to accommodate both
behaviours:
  - tokens_input  > 0  (request was received and tokenised)
  - tokens_output > 0  (model produced output of some kind)
  - latency       > 0  (a real network round-trip occurred)
  - response serialises to dict without error

For text-content assertions a token budget of 512 is used so reasoning
models have headroom to emit a visible reply.

Run the full Foundry connectivity check (human-readable) with:
    python experiments/validate_api_keys.py

Author: Anonymous Authors
Date: 2026-02-19
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "experiments"))

from model_interface import (
    ModelResponse,
    create_model_interface,
    FoundryGPT52Interface,
    FoundryKimiInterface,
    FoundryClaudeInterface,
)

# ---------------------------------------------------------------------------
# Load .env once at module level so skipif has access to FOUNDRY_API_KEY.
# ---------------------------------------------------------------------------
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

_FOUNDRY_KEY = os.getenv("FOUNDRY_API_KEY", "")
_NEEDS_KEY   = pytest.mark.skipif(
    not _FOUNDRY_KEY,
    reason="FOUNDRY_API_KEY not set - skipping live Foundry tests",
)

# Minimal prompt that all three models handle with very few tokens.
_PING_PROMPT     = "Say: test"
# Token budget large enough for reasoning models to emit visible text.
_PING_MAX_TOKENS = 512


def _assert_connectivity(resp: ModelResponse, provider_tag: str) -> None:
    """
    Assert that the endpoint responded to a real request.

    With reasoning_effort controls in place, all three Foundry models should
    produce a clean 'stop' finish (not 'length') and return non-empty text.
    """
    assert resp.tokens_input  > 0,   f"{provider_tag}: tokens_input == 0 (no request sent?)"
    assert resp.tokens_output > 0,   f"{provider_tag}: tokens_output == 0 (no generation?)"
    assert resp.latency        > 0,   f"{provider_tag}: latency == 0 (no network call?)"
    assert resp.cost           >= 0,  f"{provider_tag}: cost < 0"
    assert isinstance(resp.text, str), f"{provider_tag}: response.text is not a str"
    assert resp.metadata.get("provider") == provider_tag, (
        f"{provider_tag}: wrong provider tag in metadata"
    )
    assert "reasoning_effort" in resp.metadata or provider_tag == "foundry-claude", (
        f"{provider_tag}: reasoning_effort missing from metadata"
    )
    # Must serialise without raising.
    d = resp.to_dict()
    assert d["tokens_input"] == resp.tokens_input


def _assert_has_text(resp: ModelResponse, provider_tag: str) -> None:
    """Assert that the response contains non-empty visible text."""
    assert len(resp.text.strip()) > 0, (
        f"{provider_tag}: response.text is empty - "
        f"finish_reason={resp.metadata.get('finish_reason')}, "
        f"tokens_out={resp.tokens_output}"
    )


# ---------------------------------------------------------------------------
# GPT-5.2-chat
# ---------------------------------------------------------------------------

@pytest.mark.integration
@_NEEDS_KEY
class TestFoundryGPT52Live:
    """Live connectivity tests for the gpt-5.2-chat Foundry deployment."""

    def test_ping_endpoint_responds(self):
        """Endpoint is reachable and produces token output."""
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_connectivity(resp, "foundry-gpt")

    def test_ping_returns_text_with_sufficient_budget(self):
        """With 512 tokens budget, GPT-5.2 should emit visible text."""
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_has_text(resp, "foundry-gpt")

    def test_model_name_matches_deployment(self):
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY)
        assert iface.model_name == FoundryGPT52Interface.FOUNDRY_DEPLOYMENT

    def test_temperature_silently_omitted(self):
        """temperature=0.0 must not cause a 400 error; interface omits it."""
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, temperature=0.0, max_tokens=_PING_MAX_TOKENS)
        _assert_connectivity(resp, "foundry-gpt")

    def test_reasoning_effort_none_produces_clean_stop(self):
        """reasoning_effort='none' should give finish_reason='stop', not 'length'."""
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY,
                                       reasoning_effort="none")
        resp = iface.query(_PING_PROMPT, max_tokens=32)
        assert resp.metadata.get("finish_reason") == "stop", (
            f"Expected 'stop' but got '{resp.metadata.get('finish_reason')}' "
            f"- reasoning may be consuming tokens"
        )
        assert resp.metadata.get("reasoning_effort") == "none"

    def test_statistics_accumulate(self):
        iface = create_model_interface("foundry-gpt", api_key=_FOUNDRY_KEY)
        iface.query(_PING_PROMPT, max_tokens=64)
        iface.query(_PING_PROMPT, max_tokens=64)
        stats = iface.statistics
        assert stats["total_queries"] == 2
        assert stats["total_tokens_input"]  > 0
        assert stats["total_tokens_output"] > 0


# ---------------------------------------------------------------------------
# Kimi-K2.5
# ---------------------------------------------------------------------------

@pytest.mark.integration
@_NEEDS_KEY
class TestFoundryKimiLive:
    """Live connectivity tests for the Kimi-K2.5 Foundry deployment."""

    def test_ping_endpoint_responds(self):
        """Endpoint is reachable and produces token output."""
        iface = create_model_interface("foundry-kimi", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_connectivity(resp, "foundry-kimi")

    def test_ping_returns_text_with_sufficient_budget(self):
        """With 512 tokens budget, Kimi should emit visible text."""
        iface = create_model_interface("foundry-kimi", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_has_text(resp, "foundry-kimi")

    def test_model_name_matches_deployment(self):
        iface = create_model_interface("foundry-kimi", api_key=_FOUNDRY_KEY)
        assert iface.model_name == FoundryKimiInterface.FOUNDRY_DEPLOYMENT

    def test_reasoning_effort_low_produces_clean_stop(self):
        """reasoning_effort='low' should give finish_reason='stop'."""
        iface = create_model_interface("foundry-kimi", api_key=_FOUNDRY_KEY,
                                       reasoning_effort="low")
        resp = iface.query(_PING_PROMPT, max_tokens=128)
        assert resp.metadata.get("finish_reason") == "stop", (
            f"Expected 'stop' but got '{resp.metadata.get('finish_reason')}'"
        )
        assert resp.metadata.get("reasoning_effort") == "low"

    def test_statistics_accumulate(self):
        iface = create_model_interface("foundry-kimi", api_key=_FOUNDRY_KEY)
        iface.query(_PING_PROMPT, max_tokens=64)
        iface.query(_PING_PROMPT, max_tokens=64)
        stats = iface.statistics
        assert stats["total_queries"] == 2
        assert stats["total_tokens_input"] > 0


# ---------------------------------------------------------------------------
# Claude Sonnet 4.6
# ---------------------------------------------------------------------------

@pytest.mark.integration
@_NEEDS_KEY
class TestFoundryClaudeLive:
    """Live connectivity tests for the claude-sonnet-4-6 Foundry deployment."""

    def test_ping_endpoint_responds(self):
        iface = create_model_interface("foundry-claude", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_connectivity(resp, "foundry-claude")

    def test_ping_returns_text(self):
        iface = create_model_interface("foundry-claude", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_has_text(resp, "foundry-claude")

    def test_model_name_matches_deployment(self):
        iface = create_model_interface("foundry-claude", api_key=_FOUNDRY_KEY)
        assert iface.model_name == FoundryClaudeInterface.FOUNDRY_DEPLOYMENT

    def test_stop_reason_in_metadata(self):
        iface = create_model_interface("foundry-claude", api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        assert "stop_reason" in resp.metadata
        assert resp.metadata["stop_reason"] is not None

    def test_statistics_accumulate(self):
        iface = create_model_interface("foundry-claude", api_key=_FOUNDRY_KEY)
        iface.query(_PING_PROMPT, max_tokens=64)
        iface.query(_PING_PROMPT, max_tokens=64)
        stats = iface.statistics
        assert stats["total_queries"] == 2
        assert stats["total_cost"] > 0.0


# ---------------------------------------------------------------------------
# Cross-provider connectivity sweep
# ---------------------------------------------------------------------------

@pytest.mark.integration
@_NEEDS_KEY
class TestFoundryAllModelsReachable:
    """Confirm all three Foundry endpoints are live."""

    @pytest.mark.parametrize("provider", ["foundry-gpt", "foundry-kimi", "foundry-claude"])
    def test_each_provider_reachable(self, provider: str):
        """Endpoint responds with measurable token output for each model."""
        iface = create_model_interface(provider, api_key=_FOUNDRY_KEY)
        resp = iface.query(_PING_PROMPT, max_tokens=_PING_MAX_TOKENS)
        _assert_connectivity(resp, provider)
