#!/bin/bash
#SBATCH --job-name=defab_m5_foundry
#SBATCH --output=logs/m5_foundry_%j.out
#SBATCH --error=logs/m5_foundry_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=amilan

# DeFAb M5 Evaluation via Azure AI Foundry (Closed-Source VLMs)
#
# Evaluates M5 visual grounding modality using vision-capable closed-source
# models (GPT-5.2-chat and Claude Sonnet 4.6) via the Azure AI Foundry API.
# No GPU required -- this is an API-bound job.
#
# Prerequisites:
#   1. FOUNDRY_API_KEY environment variable set (or pass --api-key)
#   2. ImageManifest at data/images/manifest.json
#      (run: sbatch hpc/slurm_prepare_m5_images.sh)
#
# Usage:
#   sbatch hpc/slurm_evaluate_m5_foundry.sh
#
# Environment variables (all optional):
#   MANIFEST        Path to ImageManifest JSON (default: data/images/manifest.json)
#   M5_VARIANT      "replace" or "supplement" (default: replace)
#   INSTANCE_LIMIT  Max instances per domain (default: 50)
#   INCLUDE_LEVEL3  "true" or "false" (default: true)
#   LEVEL3_LIMIT    Max Level 3 instances (default: 33)
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb M5 Evaluation via Azure AI Foundry"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MANIFEST="${MANIFEST:-data/images/manifest.json}"
M5_VARIANT="${M5_VARIANT:-replace}"
INSTANCE_LIMIT="${INSTANCE_LIMIT:-50}"
INCLUDE_LEVEL3="${INCLUDE_LEVEL3:-true}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-33}"

# ---------------------------------------------------------------------------
# Validate prerequisites
# ---------------------------------------------------------------------------
FOUNDRY_KEY="${FOUNDRY_API_KEY:-}"
if [ -z "$FOUNDRY_KEY" ]; then
    echo "ERROR: FOUNDRY_API_KEY environment variable is not set."
    echo "Export it before submitting: export FOUNDRY_API_KEY=<key>"
    exit 1
fi

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

module load python/3.11 2>/dev/null || true

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -q -e ".[vision]" 2>/dev/null || pip install -q -r requirements.txt

mkdir -p logs

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: ImageManifest not found at $MANIFEST"
    echo "Run: sbatch hpc/slurm_prepare_m5_images.sh"
    exit 1
fi

echo "Manifest   : $MANIFEST"
echo "M5 variant : $M5_VARIANT"
echo "Instances  : $INSTANCE_LIMIT per domain"
echo ""

LEVEL3_FLAG=""
if [ "$INCLUDE_LEVEL3" = "true" ]; then
    LEVEL3_FLAG="--include-level3 --level3-limit $LEVEL3_LIMIT"
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ---------------------------------------------------------------------------
# GPT-5.2-chat (vision-capable)
# ---------------------------------------------------------------------------
echo "--- GPT-5.2-chat (M5-$M5_VARIANT) ---"
RESULTS_GPT="experiments/results/m5_foundry-gpt_${M5_VARIANT}_${TIMESTAMP}"
CACHE_GPT="experiments/cache/m5_foundry-gpt"
mkdir -p "$RESULTS_GPT" "$CACHE_GPT"

python experiments/run_evaluation.py \
    --provider      foundry-gpt \
    --modalities    M5 \
    --manifest      "$MANIFEST" \
    --m5-variant    "$M5_VARIANT" \
    --strategies    direct \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir   "$RESULTS_GPT" \
    --cache-dir     "$CACHE_GPT" \
    --checkpoint    "$RESULTS_GPT/checkpoint.json" \
    $LEVEL3_FLAG \
    && echo "GPT-5.2 M5 evaluation complete." \
    || echo "GPT-5.2 M5 evaluation failed (exit $?)."

echo ""

# ---------------------------------------------------------------------------
# Claude Sonnet 4.6 (vision-capable)
# ---------------------------------------------------------------------------
echo "--- Claude Sonnet 4.6 (M5-$M5_VARIANT) ---"
RESULTS_CLAUDE="experiments/results/m5_foundry-claude_${M5_VARIANT}_${TIMESTAMP}"
CACHE_CLAUDE="experiments/cache/m5_foundry-claude"
mkdir -p "$RESULTS_CLAUDE" "$CACHE_CLAUDE"

python experiments/run_evaluation.py \
    --provider      foundry-claude \
    --modalities    M5 \
    --manifest      "$MANIFEST" \
    --m5-variant    "$M5_VARIANT" \
    --strategies    direct \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir   "$RESULTS_CLAUDE" \
    --cache-dir     "$CACHE_CLAUDE" \
    --checkpoint    "$RESULTS_CLAUDE/checkpoint.json" \
    $LEVEL3_FLAG \
    && echo "Claude M5 evaluation complete." \
    || echo "Claude M5 evaluation failed (exit $?)."

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "M5 Foundry Evaluation Complete"
echo "======================================================================="
echo "End     : $(date)"
echo "GPT-5.2 : $RESULTS_GPT"
echo "Claude  : $RESULTS_CLAUDE"
