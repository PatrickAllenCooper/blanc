#!/bin/bash
#
# DeFAb Initial Fine-Tuning Experiment
#
# Submits the minimal B1 -> B2 -> B5 pipeline for a single model
# (Qwen-32B by default) to validate the fine-tuning infrastructure
# end-to-end before committing to the full training matrix.
#
# Pipeline:
#   B1: Sample 8 responses/instance (reduced from 16) via vLLM, build preference pairs
#   B2: DPO training (standard + joint curriculum) on 2xA100
#   B5: Evaluate the fine-tuned checkpoint on the test split
#
# Each stage submits a SLURM job with a dependency on the previous stage,
# so the full pipeline runs unattended. Monitor with:
#   squeue -u $USER
#   tail -f logs/sample_*.out logs/dpo_*.out logs/eval_ft_*.out
#
# Expected wall time:
#   B1: ~2-3h (Qwen-32B, 8 samples, ~286 train instances)
#   B2: ~8-12h (2xA100, 3 epochs DPO)
#   B5: ~1-2h (1xA100, ~61 test instances)
#   Total: ~12-17h wall time (mostly in queue + training)
#
# Usage:
#   cd /projects/paco0228/blanc
#   bash hpc/initial_experiment.sh [--model MODEL] [--dry-run]
#
# Author: Anonymous Authors

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( dirname "$SCRIPT_DIR" )"
cd "$PROJ_DIR"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_MODEL="${MODEL:-Qwen/Qwen2.5-32B-Instruct-AWQ}"
DRY_RUN=false
NUM_SAMPLES=8       # reduced from 16 for faster initial run
NUM_EPOCHS=3
DPO_VARIANT="standard"
CURRICULUM="joint"

for arg in "$@"; do
    case $arg in
        --model)    BASE_MODEL="$2"; shift ;;
        --dry-run)  DRY_RUN=true ;;
    esac
done

MODEL_SLUG=$(echo "$BASE_MODEL" | tr '/' '_' | tr ':' '_')
CKPT_DIR="experiments/finetuning/checkpoints/initial_dpo_${DPO_VARIANT}_${CURRICULUM}_${MODEL_SLUG}"

echo "======================================================================="
echo "DeFAb Initial Fine-Tuning Experiment"
echo "======================================================================="
echo "Model       : $BASE_MODEL"
echo "Variant     : $DPO_VARIANT"
echo "Curriculum  : $CURRICULUM"
echo "Num samples : $NUM_SAMPLES"
echo "Num epochs  : $NUM_EPOCHS"
echo "Checkpoint  : $CKPT_DIR"
echo "Dry run     : $DRY_RUN"
echo ""

# Verify we're on CURC
if [ ! -d "/scratch/alpine" ]; then
    echo "ERROR: This script must be run on CURC Alpine."
    echo "SSH in: ssh paco0228@login.rc.colorado.edu"
    exit 1
fi

# Verify repo is up to date
echo "Current commit: $(git log --oneline -1)"
echo ""

mkdir -p logs experiments/finetuning/data experiments/finetuning/checkpoints experiments/results

# ---------------------------------------------------------------------------
# Stage 1 (B1): Response Sampling
# ---------------------------------------------------------------------------
echo "--- Stage 1: Response Sampling (B1) ---"
echo "Submitting slurm_sample_responses.sh..."

if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY RUN] sbatch --export=ALL,VLLM_MODEL=$BASE_MODEL,NUM_SAMPLES=$NUM_SAMPLES hpc/slurm_sample_responses.sh"
    B1_JOBID="DRY_RUN_B1"
else
    B1_JOBID=$(sbatch --parsable \
        --export=ALL,VLLM_MODEL="$BASE_MODEL",NUM_SAMPLES="$NUM_SAMPLES" \
        hpc/slurm_sample_responses.sh)
    echo "B1 job submitted: $B1_JOBID"
fi
echo ""

# ---------------------------------------------------------------------------
# Stage 2 (B2): DPO Training (depends on B1)
# ---------------------------------------------------------------------------
echo "--- Stage 2: DPO Training (B2) ---"
echo "Will run after B1 completes..."

# Qwen-32B fits on 2xA100 for LoRA training
GPU_COUNT=2
if echo "$BASE_MODEL" | grep -qi "72b\|70b"; then
    GPU_COUNT=4
fi

if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY RUN] sbatch --dependency=afterok:$B1_JOBID --gres=gpu:$GPU_COUNT ..."
    B2_JOBID="DRY_RUN_B2"
else
    B2_JOBID=$(sbatch --parsable \
        --dependency=afterok:$B1_JOBID \
        --job-name="initial_dpo_${MODEL_SLUG}" \
        --gres=gpu:$GPU_COUNT \
        --export=ALL,BASE_MODEL="$BASE_MODEL",DPO_VARIANT="$DPO_VARIANT",CURRICULUM="$CURRICULUM",NUM_EPOCHS="$NUM_EPOCHS",OUTPUT_DIR="$CKPT_DIR" \
        hpc/slurm_train_dpo.sh)
    echo "B2 job submitted: $B2_JOBID (depends on B1=$B1_JOBID)"
fi
echo ""

# ---------------------------------------------------------------------------
# Stage 3 (B5): Evaluate Fine-Tuned Checkpoint (depends on B2)
# ---------------------------------------------------------------------------
echo "--- Stage 3: Evaluation (B5) ---"
echo "Will run after B2 completes..."

CHECKPOINT_PATH="${CKPT_DIR}/final"

if [ "$DRY_RUN" = "true" ]; then
    echo "[DRY RUN] sbatch --dependency=afterok:$B2_JOBID --export=ALL,CHECKPOINT=$CHECKPOINT_PATH,BASE_MODEL=$BASE_MODEL ..."
    B5_JOBID="DRY_RUN_B5"
else
    B5_JOBID=$(sbatch --parsable \
        --dependency=afterok:$B2_JOBID \
        --job-name="initial_eval_${MODEL_SLUG}" \
        --export=ALL,CHECKPOINT="$CHECKPOINT_PATH",BASE_MODEL="$BASE_MODEL",MODALITIES="M4 M2",STRATEGIES="direct" \
        hpc/slurm_eval_finetuned.sh)
    echo "B5 job submitted: $B5_JOBID (depends on B2=$B2_JOBID)"
fi
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "======================================================================="
echo "Initial Experiment Pipeline Submitted"
echo "======================================================================="
echo ""
echo "Job chain: B1($B1_JOBID) -> B2($B2_JOBID) -> B5($B5_JOBID)"
echo ""
echo "Monitor:"
echo "  squeue -u \$USER"
echo "  # B1 log:"
echo "  tail -f logs/sample_${B1_JOBID}_*.out 2>/dev/null || echo 'B1 not started yet'"
echo "  # B2 log:"
echo "  tail -f logs/dpo_${B2_JOBID}_*.out 2>/dev/null || echo 'B2 not started yet'"
echo "  # B5 log:"
echo "  tail -f logs/eval_ft_${B5_JOBID}_*.out 2>/dev/null || echo 'B5 not started yet'"
echo ""
echo "Results will be in:"
echo "  Preference data : experiments/finetuning/data/preferences_${MODEL_SLUG}.jsonl"
echo "  Checkpoint       : ${CKPT_DIR}/final/"
echo "  Evaluation       : experiments/results/"
echo ""
echo "Expected wall time: ~12-17 hours (including queue wait)"
echo "======================================================================="
