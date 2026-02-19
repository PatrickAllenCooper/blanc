#!/bin/bash
#SBATCH --job-name=defab_eval_curc
#SBATCH --output=logs/eval_curc_%j.out
#SBATCH --error=logs/eval_curc_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=aa100
#SBATCH --gres=gpu:1

# DeFAb Evaluation via CURC LLM Hoster (vLLM, OpenAI-compatible API)
#
# This script:
#   1. Loads the conda environment (curc-llm) from the CURC LLM Hoster project.
#   2. Starts a vLLM server on the allocated GPU node.
#   3. Waits for the server to be ready.
#   4. Runs the DeFAb evaluation pipeline against the vLLM endpoint.
#   5. Stops the vLLM server.
#
# The vLLM server exposes an OpenAI-compatible REST API at:
#   http://localhost:${VLLM_PORT}/v1
#
# DeFAb open-source evaluation models (all fit on one A100 80 GB, AWQ 4-bit):
#
#   casperhansen/deepseek-r1-distill-llama-70b-awq   (~35 GB)  [DEFAULT]
#     DeepSeek-R1 reasoning distilled into Llama 70B. Open-source reasoning
#     comparator to GPT-5.2-chat and Kimi-K2.5 (Foundry). Emits
#     <think>...</think> blocks; CURCInterface strips these automatically.
#     MIT license.
#
#   Qwen/Qwen2.5-72B-Instruct-AWQ                    (~36 GB)
#     Top general-instruction open-source model (Feb 2026). Open-source
#     comparator to claude-sonnet-4-6 (Foundry). Apache 2.0 license.
#
#   Qwen/Qwen2.5-32B-Instruct-AWQ                    (~16 GB)
#     Within-family scaling comparator (32B vs 72B Qwen). Fastest.
#     Use INSTANCE_LIMIT=120 for full KB coverage. Apache 2.0 license.
#
# Submit all three in one call:
#   bash hpc/slurm_evaluate_curc_all.sh
#
# Submit a single model:
#   sbatch hpc/slurm_evaluate_curc_vllm.sh
#   sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ \
#          hpc/slurm_evaluate_curc_vllm.sh
#   sbatch --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ,INSTANCE_LIMIT=120 \
#          hpc/slurm_evaluate_curc_vllm.sh
#
# Environment variables (all optional):
#   VLLM_MODEL        Hugging Face model ID (default: DeepSeek-R1-Distill 70B)
#   VLLM_PORT         Port for the vLLM server (default: 8100)
#   CURC_HOSTER_DIR   Path to the curc-LLM-hoster repo (default: ~/curc-LLM-hoster)
#   HF_HOME           Hugging Face cache directory (default: /scratch/alpine/$USER/.cache/hf)
#   INSTANCE_LIMIT    Instances per domain per modality (default: 50)
#   MODALITIES        Space-separated list (default: "M4 M2 M1 M3")
#   STRATEGIES        Space-separated list (default: "direct cot")
#   INCLUDE_LEVEL3    Set to "true" to include Level 3 instances (default: true)
#
# Author: Patrick Cooper
# Date: 2026-02-18

set -euo pipefail

echo "======================================================================="
echo "DeFAb Evaluation via CURC LLM Hoster (vLLM)"
echo "======================================================================="
echo "Job ID    : $SLURM_JOB_ID"
echo "Node      : $SLURM_NODELIST"
echo "CPUs      : $SLURM_CPUS_PER_TASK"
echo "GPUs      : ${SLURM_GPUS_ON_NODE:-$(echo $SLURM_GRES | grep -oP 'gpu:\K[0-9]+' || echo 1)}"
echo "Start     : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
VLLM_MODEL="${VLLM_MODEL:-casperhansen/deepseek-r1-distill-llama-70b-awq}"
VLLM_PORT="${VLLM_PORT:-8100}"
CURC_HOSTER_DIR="${CURC_HOSTER_DIR:-$HOME/curc-LLM-hoster}"
HF_HOME="${HF_HOME:-/scratch/alpine/$USER/.cache/hf}"
INSTANCE_LIMIT="${INSTANCE_LIMIT:-50}"
MODALITIES="${MODALITIES:-M4 M2 M1 M3}"
STRATEGIES="${STRATEGIES:-direct cot}"
INCLUDE_LEVEL3="${INCLUDE_LEVEL3:-true}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-33}"

VLLM_BASE_URL="http://localhost:${VLLM_PORT}"
VLLM_READY_URL="${VLLM_BASE_URL}/health"

echo "Model     : $VLLM_MODEL"
echo "vLLM port : $VLLM_PORT"
echo "HF cache  : $HF_HOME"
echo "Modalities: $MODALITIES"
echo "Strategies: $STRATEGIES"
echo ""

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
module purge
module load anaconda

# Activate the curc-llm conda environment (created by CURC LLM Hoster setup)
conda activate curc-llm 2>/dev/null || {
    echo "WARNING: 'curc-llm' conda env not found."
    echo "Run: cd $CURC_HOSTER_DIR && ./scripts/setup_environment.sh"
    echo "Falling back to base conda + pip install..."
    conda activate base
    pip install -q vllm openai tenacity
}

PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$PROJ_DIR"

# Install DeFAb dependencies into whichever env is active
pip install -q -r requirements.txt

mkdir -p logs

export HF_HOME
export TRANSFORMERS_CACHE="$HF_HOME"

# ---------------------------------------------------------------------------
# GPU status
# ---------------------------------------------------------------------------
echo "GPU status:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null \
    || echo "  (nvidia-smi not available)"
echo ""

# ---------------------------------------------------------------------------
# Start vLLM server
# ---------------------------------------------------------------------------
# Tensor parallelism: use all GPUs on the node if more than one is available.
GPU_COUNT=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | wc -l || echo 1)
TP_SIZE="${GPU_COUNT:-1}"

echo "Starting vLLM server (tensor_parallel_size=${TP_SIZE})..."
python -m vllm.entrypoints.openai.api_server \
    --model "$VLLM_MODEL" \
    --port  "$VLLM_PORT" \
    --tensor-parallel-size "$TP_SIZE" \
    --dtype  auto \
    --max-model-len 8192 \
    --gpu-memory-utilization 0.90 \
    --enforce-eager \
    2>&1 | tee "logs/vllm_${SLURM_JOB_ID}.log" &

VLLM_PID=$!
echo "vLLM PID: $VLLM_PID"

# ---------------------------------------------------------------------------
# Wait for vLLM server to be ready (up to 10 minutes for model download/load)
# ---------------------------------------------------------------------------
echo "Waiting for vLLM server to be ready (timeout 600s)..."
for i in $(seq 1 600); do
    if curl -sf "${VLLM_READY_URL}" > /dev/null 2>&1; then
        echo "vLLM server ready after ${i}s"
        break
    fi
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "ERROR: vLLM server process died unexpectedly."
        echo "Check logs/vllm_${SLURM_JOB_ID}.log for details."
        exit 1
    fi
    if [ $i -eq 600 ]; then
        echo "ERROR: vLLM server did not become ready within 600s."
        kill $VLLM_PID 2>/dev/null || true
        exit 1
    fi
    sleep 1
done

# Confirm the model is registered
REGISTERED_MODELS=$(curl -sf "${VLLM_BASE_URL}/v1/models" 2>/dev/null | python3 -c \
    "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data']])" 2>/dev/null \
    || echo "(could not query model list)")
echo "Registered models: $REGISTERED_MODELS"
echo ""

# ---------------------------------------------------------------------------
# Run DeFAb evaluation
# ---------------------------------------------------------------------------
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
MODEL_SLUG=$(echo "$VLLM_MODEL" | tr '/:' '_')
RESULTS_DIR="experiments/results/curc_${MODEL_SLUG}_${TIMESTAMP}"
CACHE_DIR="experiments/cache/curc_${MODEL_SLUG}"
CHECKPOINT="$RESULTS_DIR/checkpoint.json"

mkdir -p "$RESULTS_DIR" "$CACHE_DIR"

echo "Results   : $RESULTS_DIR"
echo "Cache     : $CACHE_DIR"
echo ""

LEVEL3_FLAG=""
if [ "$INCLUDE_LEVEL3" = "true" ]; then
    LEVEL3_FLAG="--include-level3 --level3-limit $LEVEL3_LIMIT"
fi

echo "Starting evaluation..."
python experiments/run_evaluation.py \
    --provider      curc \
    --model         "$VLLM_MODEL" \
    --curc-base-url "$VLLM_BASE_URL" \
    --modalities    $MODALITIES \
    --strategies    $STRATEGIES \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir   "$RESULTS_DIR" \
    --cache-dir     "$CACHE_DIR" \
    --checkpoint    "$CHECKPOINT" \
    $LEVEL3_FLAG

EVAL_EXIT=$?

# ---------------------------------------------------------------------------
# Run analysis on results
# ---------------------------------------------------------------------------
if [ $EVAL_EXIT -eq 0 ] && [ -d "$RESULTS_DIR" ]; then
    echo ""
    echo "Running analysis..."
    python experiments/analyze_results.py \
        --results-dir "$RESULTS_DIR" \
        --save "$RESULTS_DIR/summary.json" \
        2>/dev/null || echo "  (analyze_results.py: non-fatal error)"
fi

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
echo "Evaluation Complete"
echo "======================================================================="
echo "End       : $(date)"
echo "Exit code : $EVAL_EXIT"
echo "Results   : $RESULTS_DIR"
echo ""

if [ -f "$RESULTS_DIR/summary.json" ]; then
    python3 -c "
import json
with open('$RESULTS_DIR/summary.json') as f:
    s = json.load(f)
acc = s.get('overall', {}).get('accuracy', 'n/a')
robust = s.get('rendering_robust_accuracy', 'n/a')
n = s.get('overall', {}).get('total', 'n/a')
print(f'  Overall accuracy         : {acc}')
print(f'  Rendering-robust accuracy: {robust}')
print(f'  Total evaluations        : {n}')
" 2>/dev/null || true
fi

exit $EVAL_EXIT
