#!/bin/bash
# DeFAb M5 Evaluation -- Submit All Jobs
#
# Submits M5 evaluation jobs for all four VLMs:
#   1. Foundry API (amilan, no GPU): GPT-5.2-chat + Claude Sonnet 4.6
#   2. CURC vLLM (aa100, 2x GPU): Qwen2.5-VL-72B-Instruct-AWQ
#   3. CURC vLLM (aa100, 1x GPU): Qwen2.5-VL-7B-Instruct (scaling comparator)
#
# Prerequisites:
#   1. ImageManifest at data/images/manifest.json (persistent, under /projects/)
#      and downloaded images at /scratch/alpine/$USER/defab_images/
#      (run: sbatch hpc/slurm_prepare_m5_images.sh)
#   2. FOUNDRY_API_KEY exported for Foundry jobs
#   3. vllm-env conda environment for CURC jobs
#
# Storage:
#   Images        -> /scratch/alpine/$USER/defab_images/ (re-downloadable)
#   Manifest      -> data/images/manifest.json (persistent in /projects/)
#   Results/cache -> experiments/results/, experiments/cache/ (persistent in /projects/)
#
# Usage (from repo root on CURC login node):
#   export FOUNDRY_API_KEY=<key>
#   bash hpc/slurm_evaluate_m5_all.sh
#
# Author: Patrick Cooper

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJ_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJ_DIR"

MANIFEST="${MANIFEST:-data/images/manifest.json}"

if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: ImageManifest not found at $MANIFEST"
    echo "Run first: sbatch hpc/slurm_prepare_m5_images.sh"
    exit 1
fi

echo "======================================================================="
echo "DeFAb M5 Evaluation -- Submitting All Jobs"
echo "======================================================================="
echo "Manifest: $MANIFEST"
echo ""

# ---------------------------------------------------------------------------
# 1. Foundry API (GPT-5.2 + Claude, no GPU, amilan partition)
# ---------------------------------------------------------------------------
echo "--- Foundry (GPT-5.2 + Claude) ---"
JOB_FOUNDRY=$(sbatch --parsable \
    --export=ALL,MANIFEST="$MANIFEST" \
    hpc/slurm_evaluate_m5_foundry.sh)
echo "  Submitted job $JOB_FOUNDRY (foundry-gpt + foundry-claude)"

# ---------------------------------------------------------------------------
# 2. CURC vLLM: Qwen2.5-VL-72B (2x A100, tensor parallel 2)
# ---------------------------------------------------------------------------
echo "--- CURC: Qwen2.5-VL-72B-Instruct-AWQ (2x A100) ---"
JOB_72B=$(sbatch --parsable \
    --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-VL-72B-Instruct-AWQ,MANIFEST="$MANIFEST" \
    hpc/slurm_evaluate_m5_curc.sh)
echo "  Submitted job $JOB_72B (Qwen2.5-VL-72B, 2x A100)"

# ---------------------------------------------------------------------------
# 3. CURC vLLM: Qwen2.5-VL-7B (1x A100, scaling comparator)
# ---------------------------------------------------------------------------
echo "--- CURC: Qwen2.5-VL-7B-Instruct (1x A100) ---"
JOB_7B=$(sbatch --parsable \
    --gres=gpu:1 \
    --export=ALL,VLLM_MODEL=Qwen/Qwen2.5-VL-7B-Instruct,MANIFEST="$MANIFEST" \
    hpc/slurm_evaluate_m5_curc.sh)
echo "  Submitted job $JOB_7B (Qwen2.5-VL-7B, 1x A100)"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "All M5 jobs submitted:"
echo "  Foundry  : $JOB_FOUNDRY"
echo "  VL-72B   : $JOB_72B"
echo "  VL-7B    : $JOB_7B"
echo ""
echo "Monitor: squeue -u \$USER"
echo "======================================================================="
