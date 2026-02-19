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
)


def test_openai(api_key: str) -> bool:
    """Test OpenAI API key."""
    print("\nTesting OpenAI (GPT-4o)...")
    
    try:
        interface = create_model_interface('openai', api_key=api_key, model='gpt-4o')
        response = interface.query("Say 'test'", max_tokens=10)
        
        print(f"  ✓ Model: {response.model}")
        print(f"  ✓ Response: {response.text[:50]}")
        print(f"  ✓ Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  ✓ Cost: ${response.cost:.6f}")
        print(f"  ✓ Latency: {response.latency:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_anthropic(api_key: str) -> bool:
    """Test Anthropic API key."""
    print("\nTesting Anthropic (Claude 3.5 Sonnet)...")
    
    try:
        interface = create_model_interface('anthropic', api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        
        print(f"  ✓ Model: {response.model}")
        print(f"  ✓ Response: {response.text[:50]}")
        print(f"  ✓ Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  ✓ Cost: ${response.cost:.6f}")
        print(f"  ✓ Latency: {response.latency:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def test_google(api_key: str) -> bool:
    """Test Google API key."""
    print("\nTesting Google (Gemini 1.5 Pro)...")
    
    try:
        interface = create_model_interface('google', api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)
        
        print(f"  ✓ Model: {response.model}")
        print(f"  ✓ Response: {response.text[:50]}")
        print(f"  ✓ Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  ✓ Cost: ${response.cost:.6f}")
        print(f"  ✓ Latency: {response.latency:.2f}s")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
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

        print(f"  OK Model: {response.model}")
        print(f"  OK Response: {response.text[:50]}")
        print(f"  OK Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  OK Cost: ${response.cost:.6f}")
        print(f"  OK Latency: {response.latency:.2f}s")

        return True

    except Exception as e:
        print(f"  FAIL Error: {e}")
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

        print(f"  OK Model: {response.model}")
        print(f"  OK Response: {response.text[:50]}")
        print(f"  OK Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  OK Latency: {response.latency:.2f}s")
        print(f"  OK Cost: $0.00 (cluster compute)")

        return True

    except Exception as e:
        print(f"  FAIL Error: {e}")
        print(f"  INFO Ensure the vLLM server is running on Alpine and the")
        print(f"       SSH tunnel is open. See CURC LLM Hoster QUICKSTART.md.")
        return False


def test_foundry_gpt(api_key: str) -> bool:
    """Test Azure AI Foundry GPT-5.2-chat endpoint."""
    print(f"\nTesting Foundry GPT-5.2-chat ({FoundryGPT52Interface.FOUNDRY_ENDPOINT})...")

    try:
        interface = create_model_interface("foundry-gpt", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)

        print(f"  OK Model: {response.model}")
        print(f"  OK Response: {response.text[:50]}")
        print(f"  OK Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  OK Cost: ${response.cost:.6f}")
        print(f"  OK Latency: {response.latency:.2f}s")

        return True

    except Exception as e:
        print(f"  FAIL Error: {e}")
        return False


def test_foundry_kimi(api_key: str) -> bool:
    """Test Azure AI Foundry Kimi-K2.5 endpoint."""
    print(f"\nTesting Foundry Kimi-K2.5 ({FoundryKimiInterface.FOUNDRY_BASE_URL})...")

    try:
        interface = create_model_interface("foundry-kimi", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)

        print(f"  OK Model: {response.model}")
        print(f"  OK Response: {response.text[:50]}")
        print(f"  OK Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  OK Cost: ${response.cost:.6f}")
        print(f"  OK Latency: {response.latency:.2f}s")

        return True

    except Exception as e:
        print(f"  FAIL Error: {e}")
        return False


def test_foundry_claude(api_key: str) -> bool:
    """Test Azure AI Foundry claude-sonnet-4-6 endpoint."""
    print(f"\nTesting Foundry claude-sonnet-4-6 ({FoundryClaudeInterface.FOUNDRY_ENDPOINT})...")

    try:
        interface = create_model_interface("foundry-claude", api_key=api_key)
        response = interface.query("Say 'test'", max_tokens=10)

        print(f"  OK Model: {response.model}")
        print(f"  OK Response: {response.text[:50]}")
        print(f"  OK Tokens: {response.tokens_input} in, {response.tokens_output} out")
        print(f"  OK Cost: ${response.cost:.6f}")
        print(f"  OK Latency: {response.latency:.2f}s")

        return True

    except Exception as e:
        print(f"  FAIL Error: {e}")
        return False


def test_ollama() -> bool:
    """Test Ollama (local)."""
    print("\nTesting Ollama (optional - local models)...")
    
    try:
        # Try with smallest model first
        interface = create_model_interface('ollama', model='llama3:8b')
        
        print(f"  ℹ Attempting to query {interface.model_name}...")
        print(f"  ℹ This may take 10-30 seconds for first query...")
        
        response = interface.query("Say 'test'", max_tokens=10)
        
        print(f"  ✓ Model: {response.model}")
        print(f"  ✓ Response: {response.text[:50]}")
        print(f"  ✓ Latency: {response.latency:.2f}s")
        print(f"  ✓ Cost: $0.00 (local model)")
        
        return True
        
    except Exception as e:
        print(f"  ℹ Ollama not available: {e}")
        print(f"  ℹ This is optional - install from https://ollama.ai/")
        return False


def main():
    """Validate all API keys."""
    print("=" * 70)
    print("API KEY VALIDATION")
    print("=" * 70)
    
    # Load environment
    env_file = Path(".env")
    
    if not env_file.exists():
        print("\n❌ .env file not found!")
        print("   Please create .env from .env.template and add your API keys")
        print("\n   Steps:")
        print("   1. cp .env.template .env")
        print("   2. Edit .env and add your API keys")
        print("   3. Run this script again")
        return 1
    
    load_dotenv()
    
    # Get keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    google_key = os.getenv('GOOGLE_API_KEY')

    # Azure credentials
    azure_endpoint   = os.getenv('AZURE_OPENAI_ENDPOINT', '')
    azure_key        = os.getenv('AZURE_OPENAI_API_KEY', '')
    azure_deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o')
    azure_version    = os.getenv('AZURE_OPENAI_API_VERSION', '2024-08-01-preview')

    # CURC vLLM credentials
    curc_base_url = os.getenv('CURC_VLLM_BASE_URL', 'http://localhost:8000')
    curc_model    = os.getenv('CURC_VLLM_MODEL', 'Qwen/Qwen2.5-72B-Instruct-AWQ')

    # Azure AI Foundry credentials (shared key for all three models)
    foundry_key = os.getenv('FOUNDRY_API_KEY', '')

    # Track results
    results = {}
    
    # Test OpenAI
    if openai_key and openai_key != 'sk-...':
        results['openai'] = test_openai(openai_key)
    else:
        print("\n⚠️  OpenAI API key not set in .env")
        results['openai'] = False
    
    # Test Anthropic
    if anthropic_key and anthropic_key != 'sk-ant-...':
        results['anthropic'] = test_anthropic(anthropic_key)
    else:
        print("\n⚠️  Anthropic API key not set in .env")
        results['anthropic'] = False
    
    # Test Google (optional)
    if google_key and google_key != '...':
        results['google'] = test_google(google_key)
    else:
        print("\n⚠️  Google API key not set in .env (optional)")
        results['google'] = False
    
    # Test Azure OpenAI
    if azure_endpoint and azure_key and azure_endpoint not in ('https://your-resource.openai.azure.com/', ''):
        results['azure'] = test_azure(azure_endpoint, azure_key, azure_deployment, azure_version)
    else:
        print("\nINFO  Azure OpenAI credentials not set in .env (optional)")
        results['azure'] = False

    # Test CURC vLLM (optional -- requires vLLM server running + SSH tunnel)
    results['curc'] = test_curc(curc_base_url, curc_model)

    # Test Azure AI Foundry models
    if foundry_key:
        results['foundry-gpt']    = test_foundry_gpt(foundry_key)
        results['foundry-kimi']   = test_foundry_kimi(foundry_key)
        results['foundry-claude'] = test_foundry_claude(foundry_key)
    else:
        print("\nINFO  FOUNDRY_API_KEY not set in .env - skipping Foundry tests")
        results['foundry-gpt']    = False
        results['foundry-kimi']   = False
        results['foundry-claude'] = False

    # Test Ollama (optional)
    results['ollama'] = test_ollama()
    
    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)
    
    for service, success in results.items():
        status = "OK" if success else "FAIL"
        print(f"  {status}  {service.title()}")
    
    required_working = (
        results.get('openai', False)
        or results.get('azure', False)
        or results.get('anthropic', False)
        or results.get('curc', False)
        or results.get('foundry-gpt', False)
        or results.get('foundry-kimi', False)
        or results.get('foundry-claude', False)
    )

    if required_working:
        print("\nREADY FOR PILOT EVALUATION")
        if any(results.get(p) for p in ('foundry-gpt', 'foundry-kimi', 'foundry-claude')):
            print("   Foundry run: sbatch hpc/slurm_evaluate_foundry.sh")
            print("   Local run  : .\\hpc\\run_local.ps1 foundry-gpt")
        if results.get('curc'):
            print("   CURC run   : sbatch hpc/slurm_evaluate_curc_vllm.sh")
    else:
        print("\nREQUIRED APIs not working")
        print("   Need at least one of: OpenAI, Azure OpenAI, Anthropic, or CURC vLLM")
        print("   Optional: Google, Ollama")
    
    print("\n" + "=" * 70)
    
    return 0 if required_working else 1


if __name__ == "__main__":
    sys.exit(main())
