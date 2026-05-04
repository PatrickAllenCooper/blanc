#!/usr/bin/env bash
# Local evaluation runner for DeFAb.
#
# Equivalent to the SLURM scripts but with no cluster dependencies.
# Reads credentials from .env at the project root.
#
# Supported providers:
#   openai        - GPT-4o via OpenAI API          (requires OPENAI_API_KEY)
#   anthropic     - Claude via Anthropic API        (requires ANTHROPIC_API_KEY)
#   google        - Gemini via Google API           (requires GOOGLE_API_KEY)
#   azure         - GPT-4o via Azure OpenAI         (requires AZURE_OPENAI_* vars)
#   ollama        - Local model via Ollama          (requires Ollama running locally)
#   foundry-gpt      - gpt-5.2-chat via Foundry       (requires FOUNDRY_API_KEY)
#   foundry-kimi     - Kimi-K2.5 via Foundry          (requires FOUNDRY_API_KEY)
#   foundry-claude   - claude-sonnet-4-6 via Foundry  (requires FOUNDRY_API_KEY)
#   foundry-deepseek - DeepSeek-R1 via Foundry        (requires FOUNDRY_API_KEY)
#   foundry          - Run all four Foundry models     (requires FOUNDRY_API_KEY)
#   mock          - Deterministic fake model        (no credentials needed)
#
# Usage:
#   ./hpc/run_local.sh [PROVIDER] [OPTIONS]
#
# Examples:
#   ./hpc/run_local.sh foundry-gpt
#   ./hpc/run_local.sh foundry           # runs all three Foundry models
#   ./hpc/run_local.sh openai
#   ./hpc/run_local.sh anthropic --instance-limit 20 --modalities M4
#   ./hpc/run_local.sh ollama --model llama3:8b
#   ./hpc/run_local.sh mock --instance-limit 5
#   PROVIDER=google ./hpc/run_local.sh
#
# Environment overrides:
#   PROVIDER          Provider to use (positional arg takes precedence)
#   INSTANCE_LIMIT    Instances per domain (default: 20 for quick local runs)
#   MODALITIES        Space-separated list  (default: "M4 M2")
#   STRATEGIES        Space-separated list  (default: "direct cot")
#   INCLUDE_LEVEL3    "true" to include Level 3 (default: true)
#   LEVEL3_LIMIT      Max Level 3 instances  (default: 20)
#   OLLAMA_MODEL      Ollama model tag        (default: llama3:8b)
#   OLLAMA_HOST       Ollama server URL       (default: http://localhost:11434)
#
# Author: Anonymous Authors
# Date: 2026-02-19

set -euo pipefail

# ---------------------------------------------------------------------------
# Locate project root (one level up from hpc/)
# ---------------------------------------------------------------------------
PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
if [ -f "$PROJ_DIR/.env" ]; then
    # Export only KEY=VALUE lines; skip comments and blanks
    set -a
    # shellcheck source=/dev/null
    source <(grep -E '^[A-Z_]+=.+' "$PROJ_DIR/.env")
    set +a
    echo "Loaded credentials from .env"
else
    echo "Note: no .env file found at $PROJ_DIR/.env"
    echo "      Set credentials via environment variables or create .env from .env.template"
fi

# ---------------------------------------------------------------------------
# Provider selection (positional arg > env var > auto-detect)
# ---------------------------------------------------------------------------
PROVIDER="${1:-${PROVIDER:-}}"
shift 2>/dev/null || true   # Consume $1 if present

if [ -z "$PROVIDER" ]; then
    # Auto-detect from available credentials (Foundry preferred when key is set)
    if [ -n "${FOUNDRY_API_KEY:-}" ];    then PROVIDER="foundry"
    elif [ -n "${OPENAI_API_KEY:-}" ];   then PROVIDER="openai"
    elif [ -n "${ANTHROPIC_API_KEY:-}" ]; then PROVIDER="anthropic"
    elif [ -n "${GOOGLE_API_KEY:-}" ];    then PROVIDER="google"
    elif [ -n "${AZURE_OPENAI_API_KEY:-}" ]; then PROVIDER="azure"
    else
        echo "ERROR: No provider specified and no API key found in environment."
        echo "       Set PROVIDER=<name> or add a key to .env."
        echo "       Run with 'mock' for a credential-free dry run."
        exit 1
    fi
    echo "Auto-detected provider: $PROVIDER"
fi

# ---------------------------------------------------------------------------
# 'foundry' meta-provider: run all three models sequentially
# ---------------------------------------------------------------------------
if [ "$PROVIDER" = "foundry" ]; then
    FOUNDRY_KEY="${FOUNDRY_API_KEY:-}"
    if [ -z "$FOUNDRY_KEY" ]; then
        echo "ERROR: FOUNDRY_API_KEY not set."
        exit 1
    fi
    echo "Running all three Foundry models sequentially..."
    OVERALL_EXIT=0
    for SUB_PROVIDER in foundry-gpt foundry-kimi foundry-claude foundry-deepseek; do
        PROVIDER="$SUB_PROVIDER" "$BASH_SOURCE" "$SUB_PROVIDER" "${EXTRA_ARGS[@]+"${EXTRA_ARGS[@]}"}"
        SUB_EXIT=$?
        [ $SUB_EXIT -ne 0 ] && OVERALL_EXIT=$SUB_EXIT
    done
    exit $OVERALL_EXIT
fi

# ---------------------------------------------------------------------------
# Configuration (override via environment variables)
# ---------------------------------------------------------------------------
INSTANCE_LIMIT="${INSTANCE_LIMIT:-20}"
MODALITIES="${MODALITIES:-M4 M2}"
STRATEGIES="${STRATEGIES:-direct cot}"
INCLUDE_LEVEL3="${INCLUDE_LEVEL3:-true}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-20}"
OLLAMA_MODEL="${OLLAMA_MODEL:-llama3:8b}"
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESULTS_DIR="experiments/results/local_${PROVIDER}_${TIMESTAMP}"
CACHE_DIR="experiments/cache/local_${PROVIDER}"
CHECKPOINT="$RESULTS_DIR/checkpoint.json"

mkdir -p "$RESULTS_DIR" "$CACHE_DIR" logs

echo "======================================================================="
echo "DeFAb Local Evaluation"
echo "======================================================================="
echo "Provider      : $PROVIDER"
echo "Instance limit: $INSTANCE_LIMIT per domain"
echo "Modalities    : $MODALITIES"
echo "Strategies    : $STRATEGIES"
echo "Level 3       : $INCLUDE_LEVEL3 (limit: $LEVEL3_LIMIT)"
echo "Results dir   : $RESULTS_DIR"
echo "Started       : $(date)"
echo "======================================================================="
echo ""

# ---------------------------------------------------------------------------
# Build provider-specific arguments
# ---------------------------------------------------------------------------
PROVIDER_ARGS=()

case "$PROVIDER" in
    openai)
        if [ -z "${OPENAI_API_KEY:-}" ]; then
            echo "ERROR: OPENAI_API_KEY not set."
            exit 1
        fi
        PROVIDER_ARGS+=(--api-key "$OPENAI_API_KEY")
        PROVIDER_ARGS+=(--model "${OPENAI_MODEL:-gpt-4o}")
        ;;

    anthropic)
        if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
            echo "ERROR: ANTHROPIC_API_KEY not set."
            exit 1
        fi
        PROVIDER_ARGS+=(--api-key "$ANTHROPIC_API_KEY")
        PROVIDER_ARGS+=(--model "${ANTHROPIC_MODEL:-claude-3-5-sonnet-20241022}")
        ;;

    google)
        if [ -z "${GOOGLE_API_KEY:-}" ]; then
            echo "ERROR: GOOGLE_API_KEY not set."
            exit 1
        fi
        PROVIDER_ARGS+=(--api-key "$GOOGLE_API_KEY")
        PROVIDER_ARGS+=(--model "${GOOGLE_MODEL:-gemini-1.5-pro}")
        ;;

    azure)
        : "${AZURE_OPENAI_API_KEY:?ERROR: AZURE_OPENAI_API_KEY not set}"
        : "${AZURE_OPENAI_ENDPOINT:?ERROR: AZURE_OPENAI_ENDPOINT not set}"
        : "${AZURE_OPENAI_DEPLOYMENT:?ERROR: AZURE_OPENAI_DEPLOYMENT not set}"
        PROVIDER_ARGS+=(--api-key    "$AZURE_OPENAI_API_KEY")
        PROVIDER_ARGS+=(--endpoint   "$AZURE_OPENAI_ENDPOINT")
        PROVIDER_ARGS+=(--deployment "$AZURE_OPENAI_DEPLOYMENT")
        PROVIDER_ARGS+=(--api-version "${AZURE_OPENAI_API_VERSION:-2024-08-01-preview}")
        ;;

    ollama)
        # Check Ollama is running
        if ! curl -sf "${OLLAMA_HOST}/api/tags" > /dev/null 2>&1; then
            echo "ERROR: Ollama server not reachable at $OLLAMA_HOST"
            echo "       Start it with: ollama serve"
            echo "       Then pull your model: ollama pull $OLLAMA_MODEL"
            exit 1
        fi
        PROVIDER_ARGS+=(--model       "$OLLAMA_MODEL")
        PROVIDER_ARGS+=(--ollama-host "$OLLAMA_HOST")
        ;;

    foundry-gpt | foundry-kimi | foundry-claude | foundry-deepseek)
        FOUNDRY_KEY="${FOUNDRY_API_KEY:-}"
        if [ -z "$FOUNDRY_KEY" ]; then
            echo "ERROR: FOUNDRY_API_KEY not set."
            exit 1
        fi
        PROVIDER_ARGS+=(--api-key "$FOUNDRY_KEY")
        ;;

    mock)
        # No credentials required
        ;;

    curc)
        # CURC is accessible locally via SSH tunnel (see .env.template)
        CURC_BASE_URL="${CURC_VLLM_BASE_URL:-http://localhost:8000}"
        CURC_MODEL="${CURC_VLLM_MODEL:-Qwen/Qwen2.5-72B-Instruct-AWQ}"
        if ! curl -sf "${CURC_BASE_URL}/health" > /dev/null 2>&1; then
            echo "ERROR: CURC vLLM server not reachable at $CURC_BASE_URL"
            echo "       Create an SSH tunnel first (see .env.template for instructions)."
            exit 1
        fi
        PROVIDER_ARGS+=(--curc-base-url "$CURC_BASE_URL")
        PROVIDER_ARGS+=(--model         "$CURC_MODEL")
        ;;

    *)
        echo "ERROR: Unknown provider '$PROVIDER'."
        echo "       Valid choices: openai, anthropic, google, azure, ollama, curc, mock"
        exit 1
        ;;
esac

# ---------------------------------------------------------------------------
# Append any extra CLI arguments passed to this script
# ---------------------------------------------------------------------------
EXTRA_ARGS=("$@")

# ---------------------------------------------------------------------------
# Level 3 flag
# ---------------------------------------------------------------------------
LEVEL3_ARGS=()
if [ "$INCLUDE_LEVEL3" = "true" ]; then
    LEVEL3_ARGS=(--include-level3 --level3-limit "$LEVEL3_LIMIT")
fi

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
echo "Starting evaluation..."
python experiments/run_evaluation.py \
    --provider       "$PROVIDER" \
    --modalities     $MODALITIES \
    --strategies     $STRATEGIES \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir    "$RESULTS_DIR" \
    --cache-dir      "$CACHE_DIR" \
    --checkpoint     "$CHECKPOINT" \
    "${PROVIDER_ARGS[@]}" \
    "${LEVEL3_ARGS[@]}" \
    "${EXTRA_ARGS[@]}"

EVAL_EXIT=$?

# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
if [ $EVAL_EXIT -eq 0 ] && [ -d "$RESULTS_DIR" ]; then
    echo ""
    echo "Running analysis..."
    python experiments/analyze_results.py \
        --results-dir "$RESULTS_DIR" \
        --save "$RESULTS_DIR/summary.json" \
        2>/dev/null || echo "  (analyze_results.py: non-fatal error, skipping)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Evaluation Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Exit code: $EVAL_EXIT"
echo "Results  : $RESULTS_DIR"
echo ""

if [ -f "$RESULTS_DIR/summary.json" ]; then
    python3 -c "
import json
with open('$RESULTS_DIR/summary.json') as f:
    s = json.load(f)
overall = s.get('overall', {})
acc     = overall.get('accuracy', 'n/a')
robust  = s.get('rendering_robust_accuracy', 'n/a')
n       = overall.get('total', 'n/a')
print(f'  Overall accuracy          : {acc}')
print(f'  Rendering-robust accuracy : {robust}')
print(f'  Total evaluations         : {n}')
" 2>/dev/null || true
fi

exit $EVAL_EXIT
