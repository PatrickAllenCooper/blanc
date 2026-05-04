#!/usr/bin/env bash
# Submit SLURM evaluation jobs for all three DeFAb open-source models.
#
# Each model gets its own independent SLURM job (no dependency chain) so
# all three can run in parallel if the partition has enough A100 nodes.
# Each job starts its own vLLM server, runs the evaluation, and shuts the
# server down — no inter-job coordination required.
#
# Models and GPU budgets (all fit on a single A100 80 GB):
#
#   DeepSeek-R1-Distill-Llama-70B-AWQ  ~35 GB   reasoning comparator
#   Qwen 2.5 72B Instruct AWQ          ~36 GB   general-instruction comparator
#   Qwen 2.5 32B Instruct AWQ          ~16 GB   within-family scaling
#
# Usage (from repo root on an Alpine login node):
#   bash hpc/slurm_evaluate_curc_all.sh
#
#   Override scale:
#   INSTANCE_LIMIT=120 LEVEL3_LIMIT=35 bash hpc/slurm_evaluate_curc_all.sh
#
# Author: Anonymous Authors
# Date: 2026-02-19

set -euo pipefail

INSTANCE_LIMIT="${INSTANCE_LIMIT:-50}"
LEVEL3_LIMIT="${LEVEL3_LIMIT:-33}"
MODALITIES="${MODALITIES:-M4 M2 M1 M3}"
STRATEGIES="${STRATEGIES:-direct cot}"

echo "======================================================================="
echo "DeFAb CURC Open-Source Evaluation — submitting 3 SLURM jobs"
echo "======================================================================="
echo "Instance limit : $INSTANCE_LIMIT per domain"
echo "Level 3 limit  : $LEVEL3_LIMIT"
echo "Modalities     : $MODALITIES"
echo "Strategies     : $STRATEGIES"
echo ""

# ---------------------------------------------------------------------------
# 1. DeepSeek-R1-Distill-Llama-70B (reasoning model)
# ---------------------------------------------------------------------------
JID1=$(sbatch --parsable \
    --export=ALL,\
VLLM_MODEL=casperhansen/deepseek-r1-distill-llama-70b-awq,\
INSTANCE_LIMIT=${INSTANCE_LIMIT},\
LEVEL3_LIMIT=${LEVEL3_LIMIT},\
MODALITIES="${MODALITIES}",\
STRATEGIES="${STRATEGIES}" \
    hpc/slurm_evaluate_curc_vllm.sh)
echo "Submitted DeepSeek-R1-Distill-70B  (job $JID1)"

# ---------------------------------------------------------------------------
# 2. Qwen 2.5 72B (general-instruction model)
# ---------------------------------------------------------------------------
JID2=$(sbatch --parsable \
    --export=ALL,\
VLLM_MODEL=Qwen/Qwen2.5-72B-Instruct-AWQ,\
INSTANCE_LIMIT=${INSTANCE_LIMIT},\
LEVEL3_LIMIT=${LEVEL3_LIMIT},\
MODALITIES="${MODALITIES}",\
STRATEGIES="${STRATEGIES}" \
    hpc/slurm_evaluate_curc_vllm.sh)
echo "Submitted Qwen 2.5 72B             (job $JID2)"

# ---------------------------------------------------------------------------
# 3. Qwen 2.5 32B (within-family scaling)
# ---------------------------------------------------------------------------
JID3=$(sbatch --parsable \
    --export=ALL,\
VLLM_MODEL=Qwen/Qwen2.5-32B-Instruct-AWQ,\
INSTANCE_LIMIT=${INSTANCE_LIMIT},\
LEVEL3_LIMIT=${LEVEL3_LIMIT},\
MODALITIES="${MODALITIES}",\
STRATEGIES="${STRATEGIES}" \
    hpc/slurm_evaluate_curc_vllm.sh)
echo "Submitted Qwen 2.5 32B             (job $JID3)"

echo ""
echo "All three jobs submitted.  Monitor with:"
echo "  squeue -u \$USER"
echo "  tail -f logs/eval_curc_${JID1}.out   # DeepSeek-R1"
echo "  tail -f logs/eval_curc_${JID2}.out   # Qwen 72B"
echo "  tail -f logs/eval_curc_${JID3}.out   # Qwen 32B"
echo ""
echo "Once all complete, run analysis:"
echo "  python experiments/analyze_results.py --results-dir experiments/results/"
echo "  python experiments/generate_paper_tables.py --results-dir experiments/results/"
