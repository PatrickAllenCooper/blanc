#!/bin/bash
#SBATCH --job-name=defab_sc2_ground
#SBATCH --output=logs/sc2_ground_%j.out
#SBATCH --error=logs/sc2_ground_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=64G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb SC2 Live Grounding (E2)
#
# CPU-only job: records N games with ScriptedPolicy vs built-in AI, then
# converts the trace files to DeFAb instances.
# Mirrors slurm_gen_go.sh shape.
#
# Environment variables:
#   GAMES         Number of grounding games (default: 200)
#   DIFFICULTY    Built-in AI difficulty (default: Random)
#   TRACE_DIR     Trace output directory (default: $SCRATCH/sc2_traces)
#   INSTANCES_OUT Output JSON path (default: $SCRATCH/sc2live_instances.json)
#
# Submit:
#   sbatch --export=ALL,GAMES=200 hpc/slurm_sc2_grounding.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb SC2 Live Grounding (E2 instance generation)"
echo "======================================================================="
echo "Job ID    : $SLURM_JOB_ID"
echo "Node      : $SLURM_NODELIST"
echo "CPUs      : $SLURM_CPUS_PER_TASK"
echo "Start     : $(date)"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAMES="${GAMES:-200}"
DIFFICULTY="${DIFFICULTY:-Random}"
TRACE_DIR="${TRACE_DIR:-${SCRATCH}/sc2_traces}"
INSTANCES_OUT="${INSTANCES_OUT:-${SCRATCH}/sc2live_instances.json}"

echo "Games      : ${GAMES}"
echo "Difficulty : ${DIFFICULTY}"
echo "Trace dir  : ${TRACE_DIR}"
echo "Output     : ${INSTANCES_OUT}"
echo "======================================================================="

if [ -z "${SC2PATH:-}" ]; then
    echo "ERROR: SC2PATH not set. Run scripts/install_sc2_linux_headless.sh first."
    exit 1
fi
echo "SC2PATH    : ${SC2PATH}"

if [ -f "${HOME}/projects/defab/venv/bin/activate" ]; then
    source "${HOME}/projects/defab/venv/bin/activate"
elif [ -f "${HOME}/.venv/bin/activate" ]; then
    source "${HOME}/.venv/bin/activate"
fi

cd "${REPO_DIR}"
mkdir -p "${TRACE_DIR}"
mkdir -p "$(dirname "${INSTANCES_OUT}")"
mkdir -p logs/

echo "=== Phase 1: Record game traces ==="
python scripts/sc2live_extract_traces.py \
    --games "${GAMES}" \
    --difficulty "${DIFFICULTY}" \
    --map random \
    --output "${TRACE_DIR}" \
    --verbose

echo "=== Phase 2: Generate DeFAb instances ==="
python scripts/generate_sc2live_instances.py \
    --trace-dir "${TRACE_DIR}" \
    --output "${INSTANCES_OUT}" \
    --max-frames 10000 \
    --max-instances 20

EXIT_CODE=$?

echo "======================================================================="
echo "Grounding complete (exit ${EXIT_CODE})"
echo "Instances : ${INSTANCES_OUT}"
echo "End       : $(date)"
echo "======================================================================="

exit ${EXIT_CODE}
