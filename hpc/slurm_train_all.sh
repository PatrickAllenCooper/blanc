#!/bin/bash
#
# DeFAb Phase B: Submit the full fine-tuning training matrix.
#
# This script submits all DPO and RLHF training jobs for the three open-source
# models across all variants and curricula.
#
# Training matrix (12 DPO + 6 RLHF = 18 total jobs):
#
#   Model                               DPO variants         Curricula
#   -----------------------------------------------------------------------
#   Qwen/Qwen2.5-72B-Instruct-AWQ      standard, margin     joint, weighted
#   Qwen/Qwen2.5-32B-Instruct-AWQ      standard, margin     joint, weighted
#   deepseek-r1-distill-llama-70b-awq   standard, margin     joint, weighted
#
#   RLHF (VITL + standard):
#   Qwen-72B: vitl, reward-model
#   Qwen-32B: vitl
#   DS-R1-70B: vitl
#
# Prerequisite: slurm_sample_responses.sh must have completed for each model.
#
# Usage:
#   bash hpc/slurm_train_all.sh [--dpo-only] [--rlhf-only] [--model MODEL]
#
# Author: Patrick Cooper

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
DPO_ONLY=false
RLHF_ONLY=false
MODEL_FILTER=""

for arg in "$@"; do
    case $arg in
        --dpo-only)  DPO_ONLY=true  ;;
        --rlhf-only) RLHF_ONLY=true ;;
        --model)     MODEL_FILTER="$2"; shift ;;
    esac
done

# ---------------------------------------------------------------------------
# Model list
# ---------------------------------------------------------------------------
declare -a MODELS=(
    "Qwen/Qwen2.5-72B-Instruct-AWQ"
    "Qwen/Qwen2.5-32B-Instruct-AWQ"
    "casperhansen/deepseek-r1-distill-llama-70b-awq"
)

declare -a DPO_VARIANTS=("standard" "margin")
declare -a CURRICULA=("joint" "weighted")

# ---------------------------------------------------------------------------
# Submit DPO jobs
# ---------------------------------------------------------------------------
if [ "$RLHF_ONLY" != "true" ]; then
    echo "Submitting DPO training jobs..."
    for MODEL in "${MODELS[@]}"; do
        if [ -n "$MODEL_FILTER" ] && [[ "$MODEL" != *"$MODEL_FILTER"* ]]; then
            continue
        fi
        for VARIANT in "${DPO_VARIANTS[@]}"; do
            for CURRICULUM in "${CURRICULA[@]}"; do
                JOB_NAME="dpo_${VARIANT}_${CURRICULUM}_$(echo $MODEL | tr '/' '_' | tr ':' '_')"
                echo "  Submitting: $JOB_NAME"
                sbatch \
                    --job-name="$JOB_NAME" \
                    --export=ALL,BASE_MODEL="$MODEL",DPO_VARIANT="$VARIANT",CURRICULUM="$CURRICULUM" \
                    hpc/slurm_train_dpo.sh
            done
        done
    done
fi

# ---------------------------------------------------------------------------
# Submit RLHF jobs (VITL for all models; standard RM for Qwen-72B only)
# ---------------------------------------------------------------------------
if [ "$DPO_ONLY" != "true" ]; then
    echo ""
    echo "Submitting RLHF training jobs..."
    for MODEL in "${MODELS[@]}"; do
        if [ -n "$MODEL_FILTER" ] && [[ "$MODEL" != *"$MODEL_FILTER"* ]]; then
            continue
        fi
        # VITL for all three
        JOB_NAME="rlhf_vitl_$(echo $MODEL | tr '/' '_' | tr ':' '_')"
        echo "  Submitting: $JOB_NAME (VITL)"
        sbatch \
            --job-name="$JOB_NAME" \
            --export=ALL,BASE_MODEL="$MODEL",RLHF_MODE="vitl",CURRICULUM="joint" \
            hpc/slurm_train_rlhf.sh
    done

    # Standard RM only for Qwen-72B (most capable base, controls for RM quality)
    JOB_NAME="rlhf_rm_qwen72b"
    echo "  Submitting: $JOB_NAME (standard reward model)"
    sbatch \
        --job-name="$JOB_NAME" \
        --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",RLHF_MODE="reward-model",CURRICULUM="joint" \
        hpc/slurm_train_rlhf.sh
fi

echo ""
echo "All jobs submitted.  Monitor with:"
echo "  squeue -u $USER"
echo ""
echo "After completion, evaluate fine-tuned checkpoints:"
echo "  bash hpc/submit_eval_finetuned_all.sh"
