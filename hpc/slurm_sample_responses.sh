#!/bin/bash
#SBATCH --job-name=defab_sample
#SBATCH --output=logs/sample_%j_%x.out
#SBATCH --error=logs/sample_%j_%x.err
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --partition=aa100
#SBATCH --qos=normal
#SBATCH --gres=gpu:1

# DeFAb Phase B1: Response Sampling for Preference Data Construction
#
# Starts a vLLM server on the allocated GPU, then runs
# prepare_preference_data.py to sample n=16 responses per training instance.
# The resulting preferences_*.jsonl file is the input for DPO and RLHF.
#
# Environment variables (set via --export or sbatch environment):
#   VLLM_MODEL       HuggingFace model ID (default: Qwen/Qwen2.5-72B-Instruct-AWQ)
#   NUM_SAMPLES      Responses per instance (default: 16)
#   TEMPERATURE      Sampling temperature (default: 0.7)
#   MIN_MARGIN       Minimum score gap for pairs (default: 0.25)
#   VLLM_PORT        Port for vLLM server (default: 8111)
#   OUTPUT_DIR       Destination for JSONL files (default: experiments/finetuning/data)
#
# Submit for each model:
#   sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-72B-Instruct-AWQ" hpc/slurm_sample_responses.sh
#   sbatch --export=ALL,VLLM_MODEL="Qwen/Qwen2.5-32B-Instruct-AWQ" hpc/slurm_sample_responses.sh
#   sbatch --export=ALL,VLLM_MODEL="casperhansen/deepseek-r1-distill-llama-70b-awq" hpc/slurm_sample_responses.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb Response Sampling (Phase B1)"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "GPUs     : $SLURM_GPUS_ON_NODE"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-72B-Instruct-AWQ}"
NUM_SAMPLES="${NUM_SAMPLES:-16}"
TEMPERATURE="${TEMPERATURE:-0.7}"
MIN_MARGIN="${MIN_MARGIN:-0.25}"
VLLM_PORT="${VLLM_PORT:-8111}"
OUTPUT_DIR="${OUTPUT_DIR:-experiments/finetuning/data}"

echo "Model        : $VLLM_MODEL"
echo "Num samples  : $NUM_SAMPLES"
echo "Temperature  : $TEMPERATURE"
echo "Min margin   : $MIN_MARGIN"
echo "Output dir   : $OUTPUT_DIR"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

if [ -d "/projects/paco0228/software/anaconda/envs/vllm-env" ]; then
    conda activate /projects/paco0228/software/anaconda/envs/vllm-env
elif conda env list 2>/dev/null | grep -q "vllm-env"; then
    conda activate vllm-env
else
    echo "ERROR: vllm-env not found."
    exit 1
fi

PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:${PYTHONPATH:-}"
export HF_HOME="${HF_HOME:-/scratch/alpine/$USER/hf_cache}"
export TRANSFORMERS_CACHE="$HF_HOME"

mkdir -p logs "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# Start vLLM server
# ---------------------------------------------------------------------------
echo "Starting vLLM server on port $VLLM_PORT..."

python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL" \
    --host 0.0.0.0 \
    --port "$VLLM_PORT" \
    --dtype bfloat16 \
    --max-model-len 4096 \
    --gpu-memory-utilization 0.90 \
    --max-num-seqs 32 \
    --enforce-eager \
    &
VLLM_PID=$!

echo "vLLM PID: $VLLM_PID"
echo "Waiting for server to be ready..."

for i in $(seq 1 60); do
    if curl -sf "http://localhost:$VLLM_PORT/health" >/dev/null 2>&1; then
        echo "Server ready after ${i}s"
        break
    fi
    sleep 5
done

if ! curl -sf "http://localhost:$VLLM_PORT/health" >/dev/null 2>&1; then
    echo "ERROR: vLLM server did not start in time"
    kill $VLLM_PID 2>/dev/null || true
    exit 1
fi

# ---------------------------------------------------------------------------
# Run preference data construction
# ---------------------------------------------------------------------------
echo ""
echo "Running prepare_preference_data.py..."

python experiments/finetuning/prepare_preference_data.py \
    --provider curc \
    --base-url "http://localhost:$VLLM_PORT" \
    --model-name "$VLLM_MODEL" \
    --num-samples "$NUM_SAMPLES" \
    --temperature "$TEMPERATURE" \
    --min-margin "$MIN_MARGIN" \
    --modalities M4 M2 \
    --strategies direct cot \
    --output-dir "$OUTPUT_DIR"

EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Shutdown vLLM
# ---------------------------------------------------------------------------
echo ""
echo "Shutting down vLLM server..."
kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true

echo ""
echo "======================================================================="
echo "Sampling complete (exit $EXIT_CODE)"
echo "End: $(date)"
echo ""
echo "Output: $OUTPUT_DIR/preferences_$(basename $VLLM_MODEL).jsonl"
echo "Next:   sbatch hpc/slurm_train_dpo.sh"
echo "======================================================================="

exit $EXIT_CODE
