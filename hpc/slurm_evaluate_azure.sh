#!/bin/bash
#SBATCH --job-name=defab_eval_azure
#SBATCH --output=logs/eval_azure_%j.out
#SBATCH --error=logs/eval_azure_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=amilan

# DeFAb LLM Evaluation via Azure OpenAI
#
# Runs the full evaluation pipeline against the Azure-hosted GPT-4o
# deployment.  API calls are I/O-bound so only 4 CPUs are needed; the
# job is almost entirely waiting on network round-trips.
#
# Required environment variables (set in ~/.bashrc or passed via sbatch --export):
#   AZURE_OPENAI_ENDPOINT    - https://<resource>.openai.azure.com
#   AZURE_OPENAI_API_KEY     - Azure resource key
#   AZURE_DEPLOYMENT_NAME    - deployment name in Azure AI Studio (e.g. gpt-4o)
#   AZURE_API_VERSION        - REST API version (default: 2024-08-01-preview)
#
# Usage:
#   sbatch hpc/slurm_evaluate_azure.sh
#   sbatch --export=ALL,AZURE_OPENAI_ENDPOINT=https://... hpc/slurm_evaluate_azure.sh
#
# Optional sbatch overrides:
#   --time, --mem, --partition
#
# Author: Patrick Cooper
# Date: 2026-02-18

set -euo pipefail

echo "======================================================================="
echo "DeFAb Azure OpenAI Evaluation"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "CPUs     : $SLURM_CPUS_PER_TASK"
echo "Memory   : ${SLURM_MEM_PER_NODE:-unset} MB"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Validate credentials
# ---------------------------------------------------------------------------
: "${AZURE_OPENAI_ENDPOINT:?ERROR: AZURE_OPENAI_ENDPOINT is not set}"
: "${AZURE_OPENAI_API_KEY:?ERROR: AZURE_OPENAI_API_KEY is not set}"
: "${AZURE_DEPLOYMENT_NAME:?ERROR: AZURE_DEPLOYMENT_NAME is not set}"
AZURE_API_VERSION="${AZURE_API_VERSION:-2024-08-01-preview}"

echo "Endpoint   : $AZURE_OPENAI_ENDPOINT"
echo "Deployment : $AZURE_DEPLOYMENT_NAME"
echo "API version: $AZURE_API_VERSION"
echo ""

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
module purge
module load anaconda
module load python/3.11

PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

mkdir -p logs

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESULTS_DIR="experiments/results/azure_$(date +%Y%m%d_%H%M%S)"
CACHE_DIR="experiments/cache/azure"
CHECKPOINT="$RESULTS_DIR/checkpoint.json"

# Evaluation parameters
MODALITIES="M4 M2"          # Start with formal + semi-formal
STRATEGIES="direct cot"     # Direct + chain-of-thought
INSTANCE_LIMIT=50            # Instances per domain in this run (increase for full eval)

mkdir -p "$RESULTS_DIR" "$CACHE_DIR"

echo "Results directory : $RESULTS_DIR"
echo "Cache directory   : $CACHE_DIR"
echo "Modalities        : $MODALITIES"
echo "Strategies        : $STRATEGIES"
echo "Instance limit    : $INSTANCE_LIMIT per domain"
echo ""

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
echo "Starting evaluation..."
python experiments/run_evaluation.py \
    --provider    azure \
    --endpoint    "$AZURE_OPENAI_ENDPOINT" \
    --api-key     "$AZURE_OPENAI_API_KEY" \
    --deployment  "$AZURE_DEPLOYMENT_NAME" \
    --api-version "$AZURE_API_VERSION" \
    --modalities  $MODALITIES \
    --strategies  $STRATEGIES \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir "$RESULTS_DIR" \
    --cache-dir   "$CACHE_DIR" \
    --checkpoint  "$CHECKPOINT" \
    --include-level3

EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Post-processing
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Evaluation Complete"
echo "======================================================================="
echo "End: $(date)"
echo "Exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 0 ] && [ -d "$RESULTS_DIR" ]; then
    echo "Results summary:"
    python -c "
import json, glob, sys
files = glob.glob('$RESULTS_DIR/*.json')
for f in sorted(files):
    try:
        d = json.load(open(f))
        summary = d.get('summary', {})
        if summary:
            acc = summary.get('accuracy', 'n/a')
            total = summary.get('total_evaluations', 'n/a')
            print(f'  {f}: accuracy={acc:.3f}, n={total}')
    except Exception as e:
        print(f'  {f}: could not parse ({e})')
" 2>/dev/null || true
fi

echo ""
echo "Job complete. Results saved to: $RESULTS_DIR"
exit $EXIT_CODE
