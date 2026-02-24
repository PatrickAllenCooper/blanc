#!/bin/bash
#SBATCH --job-name=defab_dpo
#SBATCH --output=logs/dpo_%j_%x.out
#SBATCH --error=logs/dpo_%j_%x.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --partition=aa100
#SBATCH --gres=gpu:4

# DeFAb Phase B2: DPO Training
#
# Trains a LoRA adapter on DeFAb preference data via DPO (Section 6.3).
# Supports standard DPO (Equation 9) and margin-weighted DPO (Equation 10).
#
# Environment variables:
#   BASE_MODEL    HuggingFace model ID     (default: Qwen/Qwen2.5-72B-Instruct-AWQ)
#   DPO_VARIANT   standard | margin        (default: standard)
#   CURRICULUM    joint | sequential | weighted  (default: joint)
#   GAMMA         Margin delta             (default: 2.0)
#   OUTPUT_DIR    Checkpoint dir           (auto-set from model + variant)
#
# Training matrix (12 jobs):
#   Models:    Qwen-72B, Qwen-32B, DS-R1-70B
#   Variants:  standard, margin
#   Curricula: joint, weighted
#
# Submit all 12 jobs:
#   bash hpc/slurm_train_all.sh
#
# Or submit a single job:
#   sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",DPO_VARIANT="standard",CURRICULUM="joint" \
#          hpc/slurm_train_dpo.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb DPO Training (Phase B2)"
echo "======================================================================="
echo "Job ID    : $SLURM_JOB_ID"
echo "Node      : $SLURM_NODELIST"
echo "GPUs      : $SLURM_GPUS_ON_NODE"
echo "Start     : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_MODEL="${BASE_MODEL:-Qwen/Qwen2.5-72B-Instruct-AWQ}"
DPO_VARIANT="${DPO_VARIANT:-standard}"
CURRICULUM="${CURRICULUM:-joint}"
GAMMA="${GAMMA:-2.0}"
LORA_RANK="${LORA_RANK:-64}"
LORA_ALPHA="${LORA_ALPHA:-128}"
BETA="${BETA:-0.1}"
LEARNING_RATE="${LEARNING_RATE:-5e-6}"
NUM_EPOCHS="${NUM_EPOCHS:-3}"
PER_DEVICE_BATCH="${PER_DEVICE_BATCH:-2}"
GRAD_ACCUM="${GRAD_ACCUM:-8}"
WARMUP_STEPS="${WARMUP_STEPS:-100}"
DATA_DIR="${DATA_DIR:-experiments/finetuning/data}"

MODEL_SLUG=$(echo "$BASE_MODEL" | tr '/' '_' | tr ':' '_')
OUTPUT_DIR="${OUTPUT_DIR:-experiments/finetuning/checkpoints/dpo_${DPO_VARIANT}_${CURRICULUM}_${MODEL_SLUG}}"

echo "Base model     : $BASE_MODEL"
echo "DPO variant    : $DPO_VARIANT"
echo "Curriculum     : $CURRICULUM"
echo "Beta           : $BETA"
echo "Learning rate  : $LEARNING_RATE"
echo "Output dir     : $OUTPUT_DIR"
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

mkdir -p logs "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Multi-GPU setup
# ---------------------------------------------------------------------------
NPROC=$(echo "$SLURM_GPUS_ON_NODE" | tr ',' '\n' | wc -l)
echo "Using $NPROC GPUs"

# ---------------------------------------------------------------------------
# DPO training
# ---------------------------------------------------------------------------
echo ""
echo "Starting DPO training..."

torchrun \
    --nproc_per_node="$NPROC" \
    --master_port=29500 \
    experiments/finetuning/train_dpo.py \
    --base-model "$BASE_MODEL" \
    --dpo-variant "$DPO_VARIANT" \
    --curriculum "$CURRICULUM" \
    --margin-delta "$GAMMA" \
    --beta "$BETA" \
    --lora-rank "$LORA_RANK" \
    --lora-alpha "$LORA_ALPHA" \
    --learning-rate "$LEARNING_RATE" \
    --num-epochs "$NUM_EPOCHS" \
    --per-device-batch-size "$PER_DEVICE_BATCH" \
    --grad-accum-steps "$GRAD_ACCUM" \
    --warmup-steps "$WARMUP_STEPS" \
    --data-dir "$DATA_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --deepspeed-config experiments/finetuning/ds_config_zero2.json

EXIT_CODE=$?

echo ""
echo "======================================================================="
echo "DPO Training Complete (exit $EXIT_CODE)"
echo "End     : $(date)"
echo "Output  : $OUTPUT_DIR/final"
echo ""
echo "Next:   sbatch --export=ALL,CHECKPOINT=$OUTPUT_DIR/final,BASE_MODEL=$BASE_MODEL hpc/slurm_eval_finetuned.sh"
echo "======================================================================="

exit $EXIT_CODE
