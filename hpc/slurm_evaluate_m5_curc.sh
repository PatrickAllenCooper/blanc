#!/bin/bash
#SBATCH --job-name=defab_m5_curc
#SBATCH --output=logs/m5_curc_%j.out
#SBATCH --error=logs/m5_curc_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --partition=aa100
#SBATCH --qos=normal
#SBATCH --gres=gpu:2

# DeFAb M5 Evaluation via CURC vLLM (Open-Source VLMs)
#
# Evaluates M5 visual grounding using open-source vision-language models
# served via vLLM on CURC Alpine A100 GPUs.
#
# Default model: Qwen2.5-VL-72B-Instruct-AWQ (requires 2x A100 80GB,
# tensor parallel 2).  For the 7B scaling comparator, override VLLM_MODEL
# and request 1 GPU via --gres=gpu:1.
#
# Prerequisites:
#   1. ImageManifest at data/images/manifest.json
#      (run: sbatch hpc/slurm_prepare_m5_images.sh)
#   2. vllm-env conda environment (CURC LLM Hoster setup)
#
# Usage:
#   sbatch hpc/slurm_evaluate_m5_curc.sh
#   sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct \
#          --gres=gpu:1 hpc/slurm_evaluate_m5_curc.sh
#
# Environment variables (all optional):
#   VLLM_MODEL      HuggingFace model ID (default: Qwen/Qwen2.5-VL-72B-Instruct-AWQ)
#   VLLM_PORT       Port for vLLM server (default: 8100)
#   HF_HOME         HuggingFace cache (default: /scratch/alpine/$USER/hf_cache)
#   MANIFEST        Path to ImageManifest JSON (default: data/images/manifest.json)
#   M5_VARIANT      "replace" or "supplement" (default: replace)
#   INSTANCE_LIMIT  Max instances per domain (default: 50)
#   INCLUDE_LEVEL3  "true" or "false" (default: true)
#   LEVEL3_LIMIT    Max Level 3 instances (default: 33)
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb M5 Evaluation via CURC vLLM (VLM)"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "GPUs   : ${SLURM_GPUS_ON_NODE:-$(echo $SLURM_GRES | grep -oP 'gpu:\K[0-9]+' || echo 2)}"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VLLM_MODEL="${VLLM_MODEL:-Qwen/Qwen2.5-VL-72B-Instruct-AWQ}"
VLLM_PORT="${VLLM_PORT:-8100}"
HF_HOME="${HF_HOME:-/scratch/alpine/$USER/hf_cache}"
MANIFEST="${MANIFEST:-data/images/manifest.json}"
M5_VARIANT="${M5_VARIANT:-replace}"
INSTANCE_LIMIT="${INSTANCE_LIMIT:-50}"
INCLUDE_LEVEL3="${INCLUDE_LEVEL3:-true}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-33}"

VLLM_BASE_URL="http://localhost:${VLLM_PORT}"
VLLM_READY_URL="${VLLM_BASE_URL}/health"

echo "Model      : $VLLM_MODEL"
echo "vLLM port  : $VLLM_PORT"
echo "HF cache   : $HF_HOME"
echo "Manifest   : $MANIFEST"
echo "M5 variant : $M5_VARIANT"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

conda activate vllm-env 2>/dev/null || {
    echo "WARNING: 'vllm-env' not found. Falling back to base + pip install."
    conda activate base
    pip install -q vllm openai tenacity
}

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

pip install -q -r requirements.txt

mkdir -p logs

export HF_HOME
export TRANSFORMERS_CACHE="$HF_HOME"

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: ImageManifest not found at $MANIFEST"
    echo "Run: sbatch hpc/slurm_prepare_m5_images.sh"
    exit 1
fi

# ---------------------------------------------------------------------------
# GPU status
# ---------------------------------------------------------------------------
echo "GPU status:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null \
    || echo "  (nvidia-smi not available)"
echo ""

# ---------------------------------------------------------------------------
# Start vLLM server (multimodal-capable)
# ---------------------------------------------------------------------------
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l || echo 2)
TP_SIZE="${GPU_COUNT:-2}"

echo "Starting vLLM server (tensor_parallel_size=${TP_SIZE}, multimodal)..."
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL" \
    --port  "$VLLM_PORT" \
    --tensor-parallel-size "$TP_SIZE" \
    --dtype auto \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --enforce-eager \
    --trust-remote-code \
    2>&1 | tee "logs/vllm_m5_${SLURM_JOB_ID}.log" &

VLLM_PID=$!
echo "vLLM PID: $VLLM_PID"

# ---------------------------------------------------------------------------
# Wait for vLLM to be ready (up to 30 min for large VLM download/load)
# ---------------------------------------------------------------------------
echo "Waiting for vLLM server (timeout 1800s)..."
for i in $(seq 1 1800); do
    if curl -sf "${VLLM_READY_URL}" > /dev/null 2>&1; then
        echo "vLLM server ready after ${i}s"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "ERROR: vLLM server died. Check logs/vllm_m5_${SLURM_JOB_ID}.log"
        exit 1
    fi
    if [ $i -eq 1800 ]; then
        echo "ERROR: vLLM server not ready within 1800s."
        kill $VLLM_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

REGISTERED_MODELS=$(curl -sf "${VLLM_BASE_URL}/v1/models" 2>/dev/null | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])" 2>/dev/null \
    || echo "(could not query model list)")
echo "Registered models: $REGISTERED_MODELS"
echo ""

# ---------------------------------------------------------------------------
# Run M5 evaluation
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODEL_SLUG=$(echo "$VLLM_MODEL" | tr '/:' '_')
RESULTS_DIR="experiments/results/m5_curc_${MODEL_SLUG}_${M5_VARIANT}_${TIMESTAMP}"
CACHE_DIR="experiments/cache/m5_curc_${MODEL_SLUG}"
CHECKPOINT="$RESULTS_DIR/checkpoint.json"

mkdir -p "$RESULTS_DIR" "$CACHE_DIR"

echo "Results : $RESULTS_DIR"
echo "Cache   : $CACHE_DIR"
echo ""

LEVEL3_FLAG=""
if [ "$INCLUDE_LEVEL3" = "true" ]; then
    LEVEL3_FLAG="--include-level3 --level3-limit $LEVEL3_LIMIT"
fi

echo "Starting M5 evaluation..."
python experiments/run_evaluation.py \
    --provider      curc \
    --model         "$VLLM_MODEL" \
    --curc-base-url "$VLLM_BASE_URL" \
    --modalities    M5 \
    --manifest      "$MANIFEST" \
    --m5-variant    "$M5_VARIANT" \
    --strategies    direct \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir   "$RESULTS_DIR" \
    --cache-dir     "$CACHE_DIR" \
    --checkpoint    "$CHECKPOINT" \
    $LEVEL3_FLAG

EVAL_EXIT=$?

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "Stopping vLLM server (PID $VLLM_PID)..."
kill $VLLM_PID 2>/dev/null || true
wait $VLLM_PID 2>/dev/null || true

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "M5 CURC Evaluation Complete"
echo "======================================================================="
echo "End       : $(date)"
echo "Exit code : $EVAL_EXIT"
echo "Model     : $VLLM_MODEL"
echo "Variant   : $M5_VARIANT"
echo "Results   : $RESULTS_DIR"

exit $EVAL_EXIT
