#!/bin/bash
#SBATCH --job-name=defab_eval_llama
#SBATCH --output=logs/eval_llama_%j.out
#SBATCH --error=logs/eval_llama_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --partition=aa100
#SBATCH --qos=normal
#SBATCH --gres=gpu:1

# DeFAb Llama 3 Evaluation on CURC Alpine (GPU)
#
# Runs the evaluation pipeline against Meta Llama 3 70B (or 8B) served
# locally via Ollama.  Alpine's aa100 partition provides A100 80 GB GPUs
# which can hold the 70B model in 4-bit quantisation.
#
# Llama 3 70B (Q4):
#   GPU VRAM required:  ~40 GB  (fits 1x A100 80GB)
#   Recommended: aa100 partition (2x or 4x A100 if available)
#
# Llama 3 8B (full precision):
#   GPU VRAM required:  ~16 GB  (fits any modern GPU)
#   Recommended: aa100 or atesting partition
#
# Usage:
#   sbatch hpc/slurm_evaluate_llama.sh
#   sbatch --export=ALL,LLAMA_MODEL=llama3:8b hpc/slurm_evaluate_llama.sh
#
# Environment variables (optional):
#   LLAMA_MODEL    - Ollama model tag (default: llama3:70b)
#   OLLAMA_PORT    - Port for Ollama server (default: 11434)
#
# Author: Anonymous Authors
# Date: 2026-02-18

set -euo pipefail

echo "======================================================================="
echo "DeFAb Llama 3 Evaluation"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "CPUs     : $SLURM_CPUS_PER_TASK"
echo "Memory   : ${SLURM_MEM_PER_NODE:-unset} MB"
echo "GPUs     : ${SLURM_GPUS:-unset}"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
LLAMA_MODEL="${LLAMA_MODEL:-llama3:70b}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

echo "Model    : $LLAMA_MODEL"
echo "Ollama port: $OLLAMA_PORT"
echo ""

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
module load python/3.11
module load cuda/11.8    # Required by Ollama GPU backend

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

mkdir -p logs

# ---------------------------------------------------------------------------
# Start Ollama server on the compute node
# ---------------------------------------------------------------------------
echo "Starting Ollama server on port $OLLAMA_PORT..."
export OLLAMA_HOST="0.0.0.0:$OLLAMA_PORT"
export OLLAMA_MODELS="$PROJ_DIR/.ollama/models"  # Keep models within project dir
mkdir -p "$OLLAMA_MODELS"

# Download Ollama if not present
if ! command -v ollama &> /dev/null; then
    echo "Downloading Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi

# Start server in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama server to be ready
echo "Waiting for Ollama server..."
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
        echo "Ollama server ready after ${i}s"
        break
    fi
    sleep 1
done

# Pull the model if not already cached
echo "Pulling model $LLAMA_MODEL (may take several minutes if not cached)..."
ollama pull "$LLAMA_MODEL"

echo ""
echo "GPU status:"
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader 2>/dev/null || echo "(nvidia-smi not available)"
echo ""

# ---------------------------------------------------------------------------
# Run evaluation
# ---------------------------------------------------------------------------
RESULTS_DIR="experiments/results/llama_$(date +%Y%m%d_%H%M%S)"
CACHE_DIR="experiments/cache/llama"
CHECKPOINT="$RESULTS_DIR/checkpoint.json"

MODALITIES="M4 M2"
STRATEGIES="direct cot"
INSTANCE_LIMIT=50

mkdir -p "$RESULTS_DIR" "$CACHE_DIR"

echo "Results directory : $RESULTS_DIR"
echo "Cache directory   : $CACHE_DIR"
echo "Instance limit    : $INSTANCE_LIMIT per domain"
echo ""

echo "Starting evaluation..."
python experiments/run_evaluation.py \
    --provider      ollama \
    --model         "$LLAMA_MODEL" \
    --ollama-host   "http://localhost:$OLLAMA_PORT" \
    --modalities    $MODALITIES \
    --strategies    $STRATEGIES \
    --instance-limit "$INSTANCE_LIMIT" \
    --results-dir   "$RESULTS_DIR" \
    --cache-dir     "$CACHE_DIR" \
    --checkpoint    "$CHECKPOINT" \
    --include-level3

EXIT_CODE=$?

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
echo ""
echo "Stopping Ollama server (PID $OLLAMA_PID)..."
kill $OLLAMA_PID 2>/dev/null || true
wait $OLLAMA_PID 2>/dev/null || true

# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Evaluation Complete"
echo "======================================================================="
echo "End: $(date)"
echo "Exit code: $EXIT_CODE"
echo ""

if [ $EXIT_CODE -eq 0 ] && [ -d "$RESULTS_DIR" ]; then
    echo "Results summary:"
    python -c "
import json, glob
files = glob.glob('$RESULTS_DIR/*.json')
for f in sorted(files):
    try:
        d = json.load(open(f))
        summary = d.get('summary', {})
        if summary:
            acc = summary.get('accuracy', 'n/a')
            total = summary.get('total_evaluations', 'n/a')
            print(f'  {f}: accuracy={acc:.3f}, n={total}')
    except Exception as e:
        print(f'  {f}: could not parse ({e})')
" 2>/dev/null || true
fi

echo ""
echo "Job complete. Results saved to: $RESULTS_DIR"
exit $EXIT_CODE
