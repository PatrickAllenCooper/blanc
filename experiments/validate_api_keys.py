"""
Validate API keys before running evaluations.

Tests each API key with a minimal query to ensure:
- Key is valid
- API is accessible
- Model is available
- Cost tracking works

Usage:
    python validate_api_keys.py

Author: Patrick Cooper
Date: 2026-02-13
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
import os

sys.path.insert(0, str(Path(__file__).parent))

from model_interface import (
    create_model_interface,
    FoundryGPT52Interface,
    FoundryKimiInterface,
    FoundryClaudeInterface,
    FoundryDeepSeekInterface,
)


def _ok(label: str, value: str) -> None:
    print(f"  OK  {label}: {value}")


def _fail(label: str, err: Exception) -> None:
    print(f"  FAIL {label}: {err}")


def test_openai(api_key: str) -> bool:
    """Test OpenAI API key."""
    print("\nTesting OpenAI (GPT-4o)...")
    try:
        interface = create_model_interface("openai", api_key=api_key, model="gpt-4o")
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_anthropic(api_key: str) -> bool:
    """Test Anthropic API key."""
    print("\nTesting Anthropic (Claude 3.5 Sonnet)...")
    try:
        interface = create_model_interface("anthropic", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_google(api_key: str) -> bool:
    """Test Google API key."""
    print("\nTesting Google (Gemini 1.5 Pro)...")
    try:
        interface = create_model_interface("google", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_azure(endpoint: str, api_key: str, deployment: str, api_version: str) -> bool:
    """Test Azure OpenAI endpoint."""
    print(f"\nTesting Azure OpenAI (deployment: {deployment})...")
    try:
        interface = create_model_interface(
            "azure",
            endpoint=endpoint,
            api_key=api_key,
            deployment_name=deployment,
            api_version=api_version,
        )
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_curc(base_url: str, model: str) -> bool:
    """
    Test CURC LLM Hoster vLLM endpoint (OpenAI-compatible API).

    The server must already be running (launched via the CURC LLM Hoster
    project) and the SSH tunnel must be open if accessing from a local machine.
    """
    print(f"\nTesting CURC vLLM ({base_url}, model: {model})...")
    try:
        interface = create_model_interface("curc", base_url=base_url, model=model)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Latency", f"{response.latency:.2f}s")
        _ok("Cost",    "$0.00 (cluster compute)")
        return True
    except Exception as e:
        _fail("Error", e)
        print("  INFO Ensure the vLLM server is running on Alpine and the")
        print("       SSH tunnel is open. See CURC LLM Hoster QUICKSTART.md.")
        return False


def test_foundry_gpt(api_key: str) -> bool:
    """Test Azure AI Foundry GPT-5.2-chat endpoint."""
    print(f"\nTesting Foundry GPT-5.2-chat ({FoundryGPT52Interface.FOUNDRY_ENDPOINT})...")
    try:
        interface = create_model_interface("foundry-gpt", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_foundry_kimi(api_key: str) -> bool:
    """Test Azure AI Foundry Kimi-K2.5 endpoint."""
    print(f"\nTesting Foundry Kimi-K2.5 ({FoundryKimiInterface.FOUNDRY_BASE_URL})...")
    try:
        interface = create_model_interface("foundry-kimi", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_foundry_deepseek(api_key: str) -> bool:
    """Test Azure AI Foundry DeepSeek-R1 endpoint."""
    print(f"\nTesting Foundry DeepSeek-R1 ({FoundryDeepSeekInterface.FOUNDRY_BASE_URL})...")
    try:
        interface = create_model_interface("foundry-deepseek", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=512)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        if response.metadata.get("thinking"):
            _ok("Thinking", f"{len(response.metadata['thinking'])} chars stripped")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_foundry_claude(api_key: str) -> bool:
    """Test Azure AI Foundry claude-sonnet-4-6 endpoint."""
    print(f"\nTesting Foundry claude-sonnet-4-6 ({FoundryClaudeInterface.FOUNDRY_ENDPOINT})...")
    try:
        interface = create_model_interface("foundry-claude", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Tokens",  f"{response.tokens_input} in, {response.tokens_output} out")
        _ok("Cost",    f"${response.cost:.6f}")
        _ok("Latency", f"{response.latency:.2f}s")
        return True
    except Exception as e:
        _fail("Error", e)
        return False


def test_ollama() -> bool:
    """Test Ollama (local, optional)."""
    print("\nTesting Ollama (optional - local models)...")
    try:
        interface = create_model_interface("ollama", model="llama3:8b")
        print(f"  INFO Querying {interface.model_name} (may take 10-30s)...")
        response = interface.query("Say 'test'", max_tokens=10)
        _ok("Model",   response.model)
        _ok("Response", response.text[:50])
        _ok("Latency", f"{response.latency:.2f}s")
        _ok("Cost",    "$0.00 (local model)")
        return True
    except Exception as e:
        print(f"  INFO Ollama not available: {e}")
        print("  INFO Optional - install from https://ollama.com")
        return False


def main() -> int:
    """Validate all API keys."""
    print("=" * 70)
    print("API KEY VALIDATION")
    print("=" * 70)

    env_file = Path(".env")
    if not env_file.exists():
        print("\nERROR .env file not found!")
        print("   Steps: cp .env.template .env  then add your keys")
        return 1

    load_dotenv()

    openai_key    = os.getenv("OPENAI_API_KEY", "")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
    google_key    = os.getenv("GOOGLE_API_KEY", "")

    azure_endpoint   = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_key        = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    azure_version    = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview")

    curc_base_url = os.getenv("CURC_VLLM_BASE_URL", "http://localhost:8000")
    curc_model    = os.getenv("CURC_VLLM_MODEL", "Qwen/Qwen2.5-72B-Instruct-AWQ")

    foundry_key = os.getenv("FOUNDRY_API_KEY", "")

    results: dict[str, bool] = {}

    if openai_key and openai_key != "sk-...":
        results["openai"] = test_openai(openai_key)
    else:
        print("\nINFO  OpenAI API key not set in .env")
        results["openai"] = False

    if anthropic_key and anthropic_key != "sk-ant-...":
        results["anthropic"] = test_anthropic(anthropic_key)
    else:
        print("\nINFO  Anthropic API key not set in .env")
        results["anthropic"] = False

    if google_key and google_key != "...":
        results["google"] = test_google(google_key)
    else:
        print("\nINFO  Google API key not set in .env (optional)")
        results["google"] = False

    if azure_endpoint and azure_key and azure_endpoint not in ("https://your-resource.openai.azure.com/", ""):
        results["azure"] = test_azure(azure_endpoint, azure_key, azure_deployment, azure_version)
    else:
        print("\nINFO  Azure OpenAI credentials not set in .env (optional)")
        results["azure"] = False

    results["curc"] = test_curc(curc_base_url, curc_model)

    if foundry_key:
        results["foundry-gpt"]      = test_foundry_gpt(foundry_key)
        results["foundry-kimi"]     = test_foundry_kimi(foundry_key)
        results["foundry-claude"]   = test_foundry_claude(foundry_key)
        results["foundry-deepseek"] = test_foundry_deepseek(foundry_key)
    else:
        print("\nINFO  FOUNDRY_API_KEY not set in .env - skipping Foundry tests")
        results["foundry-gpt"]    = False
        results["foundry-kimi"]   = False
        results["foundry-claude"] = False

    results["ollama"] = test_ollama()

    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    for service, success in results.items():
        status = "OK  " if success else "FAIL"
        print(f"  {status}  {service}")

    required_working = any(
        results.get(p)
        for p in ("openai", "azure", "anthropic", "curc",
                  "foundry-gpt", "foundry-kimi", "foundry-claude", "foundry-deepseek")
    )

    print()
    if required_working:
        print("READY FOR PILOT EVALUATION")
        if any(results.get(p) for p in ("foundry-gpt", "foundry-kimi", "foundry-claude")):
            print("  Foundry (SLURM) : sbatch hpc/slurm_evaluate_foundry.sh")
            print("  Foundry (local) : .\\hpc\\run_local.ps1 foundry")
        if results.get("curc"):
            print("  CURC (SLURM)    : sbatch hpc/slurm_evaluate_curc_vllm.sh")
    else:
        print("NO REQUIRED APIs WORKING")
        print("  Need at least one of: OpenAI, Azure, Anthropic, CURC, or Foundry")

    print("=" * 70)
    return 0 if required_working else 1


if __name__ == "__main__":
    sys.exit(main())
