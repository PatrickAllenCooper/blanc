#!/bin/bash
#SBATCH --job-name=defab_eval_ft
#SBATCH --output=logs/eval_ft_%j_%x.out
#SBATCH --error=logs/eval_ft_%j_%x.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=80G
#SBATCH --partition=aa100
#SBATCH --gres=gpu:1

# DeFAb Phase B5: Evaluate a fine-tuned checkpoint on the test split
#
# Runs the standard DeFAb evaluation pipeline on a LoRA or merged
# checkpoint, writing results to experiments/results/ in the same
# format as base model evaluation so compare_results.py can produce
# the Table 3 (tab:ft_main) comparisons.
#
# Environment variables:
#   CHECKPOINT    Path to LoRA adapter or merged checkpoint (REQUIRED)
#   BASE_MODEL    Base model HuggingFace ID                (REQUIRED)
#   SPLIT         train | val | test | all  (default: test)
#   MODALITIES    Space-separated            (default: "M4 M2")
#   STRATEGIES    Space-separated            (default: "direct")
#   RESULTS_DIR   Output root dir            (default: experiments/results)
#   RUN_LABEL     Appended to result filename (default: checkpoint basename)
#
# Usage:
#   sbatch --export=ALL,CHECKPOINT=/path/to/checkpoint,BASE_MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ \
#          hpc/slurm_eval_finetuned.sh
#
# Author: Patrick Cooper

set -euo pipefail

: "${CHECKPOINT:?ERROR: CHECKPOINT must be set (path to fine-tuned model)}"
: "${BASE_MODEL:?ERROR: BASE_MODEL must be set (HuggingFace ID of base model)}"

echo "======================================================================="
echo "DeFAb Fine-Tuned Model Evaluation (Phase B5)"
echo "======================================================================="
echo "Job ID      : $SLURM_JOB_ID"
echo "Node        : $SLURM_NODELIST"
echo "GPUs        : $SLURM_GPUS_ON_NODE"
echo "Start       : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
SPLIT="${SPLIT:-test}"
MODALITIES="${MODALITIES:-M4 M2}"
STRATEGIES="${STRATEGIES:-direct}"
RESULTS_DIR="${RESULTS_DIR:-experiments/results}"
RUN_LABEL="${RUN_LABEL:-$(basename $CHECKPOINT)}"

echo "Checkpoint  : $CHECKPOINT"
echo "Base model  : $BASE_MODEL"
echo "Split       : $SPLIT"
echo "Modalities  : $MODALITIES"
echo "Strategies  : $STRATEGIES"
echo "Results dir : $RESULTS_DIR"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
module purge
module load anaconda
conda activate defab-train

PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:$PYTHONPATH"
export HF_HOME="${HF_HOME:-/scratch/alpine/$USER/hf_cache}"
export TRANSFORMERS_CACHE="$HF_HOME"

mkdir -p logs "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Evaluate
# ---------------------------------------------------------------------------
echo "Running evaluation..."

python experiments/finetuning/evaluate_finetuned.py \
    --checkpoint "$CHECKPOINT" \
    --base-model "$BASE_MODEL" \
    --split "$SPLIT" \
    --modalities $MODALITIES \
    --strategies $STRATEGIES \
    --results-dir "$RESULTS_DIR" \
    --run-label "$RUN_LABEL"

EXIT_CODE=$?

echo ""
echo "======================================================================="
echo "Fine-Tuned Evaluation Complete (exit $EXIT_CODE)"
echo "End: $(date)"
echo ""
echo "Next: python experiments/generate_paper_tables.py --results-dir $RESULTS_DIR"
echo "======================================================================="

exit $EXIT_CODE
