#!/bin/bash
#SBATCH --job-name=defab_eval_foundry
#SBATCH --output=logs/eval_foundry_%j.out
#SBATCH --error=logs/eval_foundry_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=amilan

# DeFAb Evaluation via Azure AI Foundry
#
# Runs the full evaluation pipeline sequentially against all four
# Foundry-hosted models:
#   - gpt-5.2-chat      (250,000 TPM / 2,500 RPM)
#   - Kimi-K2.5         (250,000 TPM /   250 RPM)
#   - claude-sonnet-4-6 (250,000 TPM /   250 RPM)
#   - DeepSeek-R1       (5,000,000 TPM / 5,000 RPM)
#
# All three models share a single API key (FOUNDRY_API_KEY).
# Jobs are I/O-bound (API calls); 4 CPUs and no GPU are needed.
#
# Required environment variable (set in ~/.bashrc or via sbatch --export):
#   FOUNDRY_API_KEY - shared API key for LLM-Defeasible-Foundry
#
# Usage:
#   sbatch hpc/slurm_evaluate_foundry.sh
#   sbatch --export=ALL,INSTANCE_LIMIT=100 hpc/slurm_evaluate_foundry.sh
#
# Optional overrides (via --export or env):
#   INSTANCE_LIMIT    Max instances per domain per model (default: 50)
#   LEVEL3_LIMIT      Max Level 3 instances per model   (default: 33)
#   MODALITIES        Space-separated list               (default: "M4 M2 M1 M3")
#   STRATEGIES        Space-separated list               (default: "direct cot")
#   INCLUDE_LEVEL3    "true" to include Level 3          (default: true)
#   SKIP_GPT          "true" to skip gpt-5.2-chat        (default: false)
#   SKIP_KIMI         "true" to skip Kimi-K2.5           (default: false)
#   SKIP_CLAUDE       "true" to skip claude-sonnet-4-6   (default: false)
#   SKIP_DEEPSEEK     "true" to skip DeepSeek-R1         (default: false)
#
# Author: Patrick Cooper
# Date: 2026-02-19

set -euo pipefail

echo "======================================================================="
echo "DeFAb Azure AI Foundry Evaluation"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "CPUs     : $SLURM_CPUS_PER_TASK"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Validate credentials
# ---------------------------------------------------------------------------
: "${FOUNDRY_API_KEY:?ERROR: FOUNDRY_API_KEY is not set. Export it before submitting.}"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
INSTANCE_LIMIT="${INSTANCE_LIMIT:-50}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-33}"
MODALITIES="${MODALITIES:-M4 M2 M1 M3}"
STRATEGIES="${STRATEGIES:-direct cot}"
INCLUDE_LEVEL3="${INCLUDE_LEVEL3:-true}"
SKIP_GPT="${SKIP_GPT:-false}"
SKIP_KIMI="${SKIP_KIMI:-false}"
SKIP_CLAUDE="${SKIP_CLAUDE:-false}"
SKIP_DEEPSEEK="${SKIP_DEEPSEEK:-false}"

echo "Instance limit : $INSTANCE_LIMIT per domain"
echo "Level 3 limit  : $LEVEL3_LIMIT"
echo "Modalities     : $MODALITIES"
echo "Strategies     : $STRATEGIES"
echo "Include Level 3: $INCLUDE_LEVEL3"
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
# Shared helpers
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

LEVEL3_ARGS=""
if [ "$INCLUDE_LEVEL3" = "true" ]; then
    LEVEL3_ARGS="--include-level3 --level3-limit $LEVEL3_LIMIT"
fi

run_model() {
    local PROVIDER="$1"
    local LABEL="$2"
    local RESULTS_DIR="experiments/results/foundry_${LABEL}_${TIMESTAMP}"
    local CACHE_DIR="experiments/cache/foundry_${LABEL}"
    local CHECKPOINT="$RESULTS_DIR/checkpoint.json"

    echo ""
    echo "-----------------------------------------------------------------------"
    echo "Running: $PROVIDER  ($LABEL)"
    echo "Results: $RESULTS_DIR"
    echo "-----------------------------------------------------------------------"

    mkdir -p "$RESULTS_DIR" "$CACHE_DIR"

    python experiments/run_evaluation.py \
        --provider       "$PROVIDER" \
        --api-key        "$FOUNDRY_API_KEY" \
        --modalities     $MODALITIES \
        --strategies     $STRATEGIES \
        --instance-limit "$INSTANCE_LIMIT" \
        --results-dir    "$RESULTS_DIR" \
        --cache-dir      "$CACHE_DIR" \
        --checkpoint     "$CHECKPOINT" \
        $LEVEL3_ARGS

    local EXIT_CODE=$?

    if [ $EXIT_CODE -eq 0 ] && [ -d "$RESULTS_DIR" ]; then
        python experiments/analyze_results.py \
            --results-dir "$RESULTS_DIR" \
            --save "$RESULTS_DIR/summary.json" \
            2>/dev/null || echo "  (analyze_results.py: non-fatal, skipping)"
    fi

    echo "  Exit code: $EXIT_CODE"
    return $EXIT_CODE
}

# ---------------------------------------------------------------------------
# Run all three models
# ---------------------------------------------------------------------------
OVERALL_EXIT=0

if [ "$SKIP_GPT" != "true" ]; then
    run_model "foundry-gpt"    "gpt52" || OVERALL_EXIT=$?
else
    echo "Skipping gpt-5.2-chat (SKIP_GPT=true)"
fi

if [ "$SKIP_KIMI" != "true" ]; then
    run_model "foundry-kimi"   "kimi"  || OVERALL_EXIT=$?
else
    echo "Skipping Kimi-K2.5 (SKIP_KIMI=true)"
fi

if [ "$SKIP_CLAUDE" != "true" ]; then
    run_model "foundry-claude" "claude" || OVERALL_EXIT=$?
else
    echo "Skipping claude-sonnet-4-6 (SKIP_CLAUDE=true)"
fi

if [ "$SKIP_DEEPSEEK" != "true" ]; then
    run_model "foundry-deepseek" "deepseek" || OVERALL_EXIT=$?
else
    echo "Skipping DeepSeek-R1 (SKIP_DEEPSEEK=true)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "All Foundry Evaluations Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Exit code: $OVERALL_EXIT"
echo ""
echo "Results saved under: experiments/results/foundry_*_${TIMESTAMP}/"
echo ""
echo "Next steps:"
echo "  python experiments/generate_paper_tables.py --results-dir experiments/results/"
echo "  python experiments/novelty_analysis.py      --results-dir experiments/results/"
echo "  python experiments/error_taxonomy.py        --results-dir experiments/results/"

exit $OVERALL_EXIT
