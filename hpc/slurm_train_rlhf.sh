#!/bin/bash
#SBATCH --job-name=defab_rlhf
#SBATCH --output=logs/rlhf_%j_%x.out
#SBATCH --error=logs/rlhf_%j_%x.err
#SBATCH --time=36:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --partition=aa100
#SBATCH --gres=gpu:4

# DeFAb Phase B3: RLHF Training (standard reward model or VITL)
#
# Implements Section 6.4 of the paper.
#
# Modes:
#   vitl         -- Uses DeFAb verifier directly as reward signal (Equation 13)
#   reward-model -- Trains Bradley-Terry RM then does PPO (Equation 11-12)
#
# Environment variables:
#   BASE_MODEL    HuggingFace model ID     (default: Qwen/Qwen2.5-72B-Instruct-AWQ)
#   RLHF_MODE     vitl | reward-model      (default: vitl)
#   CURRICULUM    joint | sequential | weighted  (default: joint)
#   KL_COEFF      PPO KL penalty coeff     (default: 0.1)
#   PPO_EPOCHS    Number of PPO epochs     (default: 3)
#
# Submit:
#   # VITL (recommended)
#   sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",RLHF_MODE="vitl" hpc/slurm_train_rlhf.sh
#
#   # Standard RLHF
#   sbatch --export=ALL,BASE_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ",RLHF_MODE="reward-model" hpc/slurm_train_rlhf.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb RLHF Training (Phase B3)"
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
RLHF_MODE="${RLHF_MODE:-vitl}"
CURRICULUM="${CURRICULUM:-joint}"
KL_COEFF="${KL_COEFF:-0.05}"          # paper Section 6.6: beta=0.05
PPO_EPOCHS="${PPO_EPOCHS:-3}"
BATCH_SIZE="${BATCH_SIZE:-16}"
MINI_BATCH_SIZE="${MINI_BATCH_SIZE:-8}"   # paper Section 6.6: mini-batch=8
LEARNING_RATE="${LEARNING_RATE:-1e-6}"    # paper Section 6.6: LR=1e-6
MAX_NEW_TOKENS="${MAX_NEW_TOKENS:-512}"
LORA_RANK="${LORA_RANK:-64}"
LORA_ALPHA="${LORA_ALPHA:-128}"
DATA_DIR="${DATA_DIR:-experiments/finetuning/data}"

MODEL_SLUG=$(echo "$BASE_MODEL" | tr '/' '_' | tr ':' '_')
OUTPUT_DIR="${OUTPUT_DIR:-experiments/finetuning/checkpoints/rlhf_${RLHF_MODE}_${CURRICULUM}_${MODEL_SLUG}}"

echo "Base model     : $BASE_MODEL"
echo "RLHF mode      : $RLHF_MODE"
echo "Curriculum     : $CURRICULUM"
echo "KL coeff       : $KL_COEFF"
echo "PPO epochs     : $PPO_EPOCHS"
echo "Output dir     : $OUTPUT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
conda activate defab-train

PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:$PYTHONPATH"
export HF_HOME="${HF_HOME:-/scratch/alpine/$USER/hf_cache}"
export TRANSFORMERS_CACHE="$HF_HOME"

mkdir -p logs "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# RLHF training
# ---------------------------------------------------------------------------
NPROC=$(echo "$SLURM_GPUS_ON_NODE" | tr ',' '\n' | wc -l)
echo "Using $NPROC GPUs"

echo ""
echo "Starting RLHF ($RLHF_MODE) training..."

torchrun \
    --nproc_per_node="$NPROC" \
    --master_port=29501 \
    experiments/finetuning/train_rlhf_vitl.py \
    --mode "$RLHF_MODE" \
    --base-model "$BASE_MODEL" \
    --curriculum "$CURRICULUM" \
    --kl-coeff "$KL_COEFF" \
    --ppo-epochs "$PPO_EPOCHS" \
    --batch-size "$BATCH_SIZE" \
    --mini-batch-size "$MINI_BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --max-new-tokens "$MAX_NEW_TOKENS" \
    --lora-rank "$LORA_RANK" \
    --lora-alpha "$LORA_ALPHA" \
    --data-dir "$DATA_DIR" \
    --output-dir "$OUTPUT_DIR"

EXIT_CODE=$?

echo ""
echo "======================================================================="
echo "RLHF Training Complete (exit $EXIT_CODE)"
echo "End     : $(date)"
echo "Output  : $OUTPUT_DIR/final"
echo ""
echo "Next:   sbatch --export=ALL,CHECKPOINT=$OUTPUT_DIR/final,BASE_MODEL=$BASE_MODEL hpc/slurm_eval_finetuned.sh"
echo "======================================================================="

exit $EXIT_CODE
