#!/bin/bash
#
# DeFAb Phase B5: Submit evaluation jobs for all fine-tuned checkpoints.
#
# Scans experiments/finetuning/checkpoints/ for completed final/ directories,
# reads the base_model.txt written by train_dpo.py / train_rlhf_vitl.py, and
# submits one slurm_eval_finetuned.sh job per checkpoint.
#
# Prerequisites:
#   - All training jobs (B2/B3) must have completed and written a final/ dir.
#   - Each final/ dir must contain base_model.txt (written by training scripts).
#   - instances/splits.json must exist (written by prepare_preference_data.py).
#
# Usage:
#   bash hpc/submit_eval_finetuned_all.sh [--dry-run] [--checkpoints-dir DIR]
#
# Author: Anonymous Authors

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
DRY_RUN=false
CHECKPOINTS_DIR="${CHECKPOINTS_DIR:-experiments/finetuning/checkpoints}"
MODALITIES="${MODALITIES:-M4 M2}"
STRATEGIES="${STRATEGIES:-direct}"

for arg in "$@"; do
    case $arg in
        --dry-run)         DRY_RUN=true ;;
        --checkpoints-dir) CHECKPOINTS_DIR="$2"; shift ;;
    esac
done

echo "======================================================================="
echo "DeFAb Phase B5: Submit All Checkpoint Evaluations"
echo "======================================================================="
echo "Checkpoints dir : $CHECKPOINTS_DIR"
echo "Dry run         : $DRY_RUN"
echo ""

# ---------------------------------------------------------------------------
# Discover checkpoints
# ---------------------------------------------------------------------------
submitted=0
skipped=0
errors=0

if [ ! -d "$CHECKPOINTS_DIR" ]; then
    echo "ERROR: Checkpoints directory not found: $CHECKPOINTS_DIR"
    echo "Run training jobs first (bash hpc/slurm_train_all.sh)."
    exit 1
fi

for FINAL_DIR in "$CHECKPOINTS_DIR"/*/final; do
    if [ ! -d "$FINAL_DIR" ]; then
        continue
    fi

    RUN_DIR="$( dirname "$FINAL_DIR" )"
    RUN_NAME="$( basename "$RUN_DIR" )"

    # Read base model from base_model.txt written by training scripts
    BASE_MODEL_FILE="$FINAL_DIR/base_model.txt"
    if [ ! -f "$BASE_MODEL_FILE" ]; then
        BASE_MODEL_FILE="$RUN_DIR/base_model.txt"
    fi

    if [ ! -f "$BASE_MODEL_FILE" ]; then
        echo "  SKIP $RUN_NAME: no base_model.txt found (training may have crashed)"
        (( skipped++ )) || true
        continue
    fi

    BASE_MODEL="$( cat "$BASE_MODEL_FILE" | tr -d '[:space:]' )"
    if [ -z "$BASE_MODEL" ]; then
        echo "  SKIP $RUN_NAME: base_model.txt is empty"
        (( skipped++ )) || true
        continue
    fi

    # Skip if results already exist for this checkpoint
    RESULTS_PATTERN="experiments/results/finetuned_final_*"
    if ls $RESULTS_PATTERN 2>/dev/null | grep -q "$RUN_NAME"; then
        echo "  SKIP $RUN_NAME: results already exist"
        (( skipped++ )) || true
        continue
    fi

    JOB_NAME="eval_ft_${RUN_NAME}"
    echo "  Submitting: $JOB_NAME"
    echo "    Checkpoint : $FINAL_DIR"
    echo "    Base model : $BASE_MODEL"

    if [ "$DRY_RUN" = "true" ]; then
        echo "    [DRY RUN -- not submitted]"
    else
        sbatch \
            --job-name="$JOB_NAME" \
            --export=ALL,CHECKPOINT="$FINAL_DIR",BASE_MODEL="$BASE_MODEL",MODALITIES="$MODALITIES",STRATEGIES="$STRATEGIES" \
            hpc/slurm_eval_finetuned.sh
        (( submitted++ )) || true
    fi
    echo ""
done

echo "======================================================================="
echo "Summary: $submitted submitted, $skipped skipped, $errors errors"
if [ "$DRY_RUN" = "true" ]; then
    echo "(Dry run -- no jobs were actually submitted)"
fi
echo ""
echo "Monitor with:  squeue -u \$USER"
echo "After completion, run B6 analysis scripts:"
echo "  python experiments/finetuning/generate_ft_tables.py --results-dir experiments/results/"
echo "  python experiments/finetuning/analyze_ft_lift.py    --results-dir experiments/results/"
echo "======================================================================="
