#!/bin/bash
#
# DeFAb Phase B: Submit the full fine-tuning training matrix.
#
# This script submits all DPO and RLHF training jobs for the three open-source
# models across all variants and curricula.
#
# Training matrix (12 DPO + 6 RLHF + 3 SFT + 3 GRPO = 24 total jobs):
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
#   SFT: 3 models x joint curriculum
#   GRPO/RLVR: 3 models x joint curriculum
#
# Prerequisite: slurm_sample_responses.sh must have completed for each model.
# For SFT: prepare_sft_data.py must have been run first.
#
# Usage:
#   bash hpc/slurm_train_all.sh [--dpo-only] [--rlhf-only] [--sft-only] [--grpo-only] [--model MODEL]
#
# Author: Anonymous Authors

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Parse flags
# ---------------------------------------------------------------------------
DPO_ONLY=false
RLHF_ONLY=false
SFT_ONLY=false
GRPO_ONLY=false
MODEL_FILTER=""

for arg in "$@"; do
    case $arg in
        --dpo-only)  DPO_ONLY=true  ;;
        --rlhf-only) RLHF_ONLY=true ;;
        --sft-only)  SFT_ONLY=true  ;;
        --grpo-only) GRPO_ONLY=true ;;
        --model)     MODEL_FILTER="$2"; shift ;;
    esac
done

# If any --*-only flag is set, skip methods that weren't requested
ANY_ONLY=false
if [ "$DPO_ONLY" = "true" ] || [ "$RLHF_ONLY" = "true" ] || [ "$SFT_ONLY" = "true" ] || [ "$GRPO_ONLY" = "true" ]; then
    ANY_ONLY=true
fi

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
if { [ "$ANY_ONLY" != "true" ] || [ "$DPO_ONLY" = "true" ]; }; then
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
if { [ "$ANY_ONLY" != "true" ] || [ "$RLHF_ONLY" = "true" ]; }; then
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

# ---------------------------------------------------------------------------
# Submit SFT jobs (3 models x joint curriculum)
# ---------------------------------------------------------------------------
if { [ "$ANY_ONLY" != "true" ] || [ "$SFT_ONLY" = "true" ]; }; then
    echo ""
    echo "Submitting SFT training jobs..."
    for MODEL in "${MODELS[@]}"; do
        if [ -n "$MODEL_FILTER" ] && [[ "$MODEL" != *"$MODEL_FILTER"* ]]; then
            continue
        fi
        JOB_NAME="sft_joint_$(echo $MODEL | tr '/' '_' | tr ':' '_')"
        echo "  Submitting: $JOB_NAME"
        sbatch \
            --job-name="$JOB_NAME" \
            --export=ALL,BASE_MODEL="$MODEL",CURRICULUM="joint" \
            hpc/slurm_train_sft.sh
    done
fi

# ---------------------------------------------------------------------------
# Submit GRPO/RLVR jobs (3 models x joint curriculum)
# ---------------------------------------------------------------------------
if { [ "$ANY_ONLY" != "true" ] || [ "$GRPO_ONLY" = "true" ]; }; then
    echo ""
    echo "Submitting GRPO/RLVR training jobs..."
    for MODEL in "${MODELS[@]}"; do
        if [ -n "$MODEL_FILTER" ] && [[ "$MODEL" != *"$MODEL_FILTER"* ]]; then
            continue
        fi
        JOB_NAME="grpo_joint_$(echo $MODEL | tr '/' '_' | tr ':' '_')"
        echo "  Submitting: $JOB_NAME (RLVR)"
        sbatch \
            --job-name="$JOB_NAME" \
            --export=ALL,BASE_MODEL="$MODEL",CURRICULUM="joint" \
            hpc/slurm_train_grpo.sh
    done
fi

echo ""
echo "All jobs submitted.  Monitor with:"
echo "  squeue -u $USER"
echo ""
echo "After completion, evaluate fine-tuned checkpoints:"
echo "  bash hpc/submit_eval_finetuned_all.sh"
