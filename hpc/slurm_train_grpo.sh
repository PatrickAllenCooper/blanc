#!/bin/bash
#SBATCH --job-name=defab_grpo
#SBATCH --output=logs/grpo_%j_%x.out
#SBATCH --error=logs/grpo_%j_%x.err
#SBATCH --time=36:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --partition=aa100
#SBATCH --qos=normal
#SBATCH --gres=gpu:4

# DeFAb Phase B-GRPO: RLVR via Group Relative Policy Optimization
#
# Trains a LoRA adapter using GRPO with the DeFAb verifier as a verifiable
# reward signal.  GRPO normalizes advantages within groups of completions,
# producing sparse gradient signal compared to DPO's dense updates.
#
# Environment variables:
#   BASE_MODEL        HuggingFace model ID  (default: Qwen/Qwen2.5-72B-Instruct-AWQ)
#   CURRICULUM        joint | weighted      (default: joint)
#   LORA_INIT         default | spectral    (default: default)
#   NUM_GENERATIONS   Group size G          (default: 8)
#   BETA              KL penalty coeff      (default: 0.04)
#   OUTPUT_DIR        Checkpoint dir        (auto-set)
#
# Submit:
#   sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" \
#          hpc/slurm_train_grpo.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb GRPO/RLVR Training (Phase B-GRPO)"
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
CURRICULUM="${CURRICULUM:-joint}"
LORA_INIT="${LORA_INIT:-default}"
LORA_RANK="${LORA_RANK:-64}"
LORA_ALPHA="${LORA_ALPHA:-128}"
NUM_GENERATIONS="${NUM_GENERATIONS:-8}"
BETA="${BETA:-0.04}"
LEARNING_RATE="${LEARNING_RATE:-5e-7}"
NUM_EPOCHS="${NUM_EPOCHS:-3}"
PER_DEVICE_BATCH="${PER_DEVICE_BATCH:-2}"
GRAD_ACCUM="${GRAD_ACCUM:-4}"
WARMUP_STEPS="${WARMUP_STEPS:-50}"
TEMPERATURE="${TEMPERATURE:-0.7}"
INSTANCES_DIR="${INSTANCES_DIR:-instances}"

MODEL_SLUG=$(echo "$BASE_MODEL" | tr '/' '_' | tr ':' '_')
INIT_SUFFIX=$([ "$LORA_INIT" = "default" ] && echo "" || echo "_${LORA_INIT}")
OUTPUT_DIR="${OUTPUT_DIR:-experiments/finetuning/checkpoints/grpo_${CURRICULUM}_${MODEL_SLUG}${INIT_SUFFIX}}"

echo "Base model        : $BASE_MODEL"
echo "Curriculum        : $CURRICULUM"
echo "LoRA init         : $LORA_INIT"
echo "Num generations G : $NUM_GENERATIONS"
echo "Beta (KL)         : $BETA"
echo "Learning rate     : $LEARNING_RATE"
echo "Output dir        : $OUTPUT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
conda activate defab-train

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:${PYTHONPATH:-}"
export HF_HOME="${HF_HOME:-/scratch/alpine/$USER/hf_cache}"
export TRANSFORMERS_CACHE="$HF_HOME"

mkdir -p logs "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Multi-GPU setup
# ---------------------------------------------------------------------------
NPROC=$(echo "$SLURM_GPUS_ON_NODE" | tr ',' '\n' | wc -l)
echo "Using $NPROC GPUs"

# ---------------------------------------------------------------------------
# GRPO training
# ---------------------------------------------------------------------------
echo ""
echo "Starting GRPO training..."

torchrun \
    --nproc_per_node="$NPROC" \
    --master_port=29500 \
    experiments/finetuning/train_grpo.py \
    --base-model "$BASE_MODEL" \
    --curriculum "$CURRICULUM" \
    --lora-init "$LORA_INIT" \
    --lora-rank "$LORA_RANK" \
    --lora-alpha "$LORA_ALPHA" \
    --num-generations "$NUM_GENERATIONS" \
    --beta "$BETA" \
    --learning-rate "$LEARNING_RATE" \
    --num-epochs "$NUM_EPOCHS" \
    --per-device-batch-size "$PER_DEVICE_BATCH" \
    --grad-accum-steps "$GRAD_ACCUM" \
    --warmup-steps "$WARMUP_STEPS" \
    --temperature "$TEMPERATURE" \
    --instances-dir "$INSTANCES_DIR" \
    --output-dir "$OUTPUT_DIR" \
    --deepspeed-config experiments/finetuning/ds_config_zero2.json

EXIT_CODE=$?

echo ""
echo "======================================================================="
echo "GRPO Training Complete (exit $EXIT_CODE)"
echo "End     : $(date)"
echo "Output  : $OUTPUT_DIR/final"
echo ""
echo "Next:   sbatch --export=ALL,CHECKPOINT=$OUTPUT_DIR/final,BASE_MODEL=$BASE_MODEL hpc/slurm_eval_finetuned.sh"
echo "======================================================================="

exit $EXIT_CODE
