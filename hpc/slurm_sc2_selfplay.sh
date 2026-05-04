#!/bin/bash
#SBATCH --job-name=defab_sc2_selfplay
#SBATCH --output=logs/sc2_selfplay_%j.out
#SBATCH --error=logs/sc2_selfplay_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb SC2 Live Self-Play (E4)
#
# Runs N parallel LLM-vs-LLM SC2 games and emits GRPO rollout records.
# Each game uses DeFAbBot with LLMPolicy on the headless SC2 Linux binary.
#
# Environment variables:
#   PROVIDER_A         Model provider for bot A (default: foundry-deepseek)
#   PROVIDER_B         Model provider for bot B (default: foundry-gpt)
#   GAMES              Number of self-play games (default: 16)
#   MAP                SC2 map name (default: Simple64)
#   TRACE_DIR          Output directory for trace files (default: $SCRATCH/sc2_traces)
#   ROLLOUT_FILE       Output .jsonl for GRPO rollouts (default: $SCRATCH/sc2_rollouts.jsonl)
#
# Submit:
#   sbatch --export=ALL,GAMES=32,PROVIDER_A=foundry-deepseek hpc/slurm_sc2_selfplay.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb SC2 Live Self-Play (E4 GRPO rollout generation)"
echo "======================================================================="
echo "Job ID    : $SLURM_JOB_ID"
echo "Node      : $SLURM_NODELIST"
echo "CPUs      : $SLURM_CPUS_PER_TASK"
echo "Start     : $(date)"

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROVIDER_A="${PROVIDER_A:-foundry-deepseek}"
PROVIDER_B="${PROVIDER_B:-foundry-gpt}"
GAMES="${GAMES:-16}"
MAP="${MAP:-Simple64}"
TRACE_DIR="${TRACE_DIR:-${SCRATCH}/sc2_traces}"
ROLLOUT_FILE="${ROLLOUT_FILE:-${SCRATCH}/sc2_rollouts.jsonl}"

echo "Provider A : ${PROVIDER_A}"
echo "Provider B : ${PROVIDER_B}"
echo "Games      : ${GAMES}"
echo "Map        : ${MAP}"
echo "Trace dir  : ${TRACE_DIR}"
echo "Rollout    : ${ROLLOUT_FILE}"
echo "======================================================================="

# Verify SC2 is installed
if [ -z "${SC2PATH:-}" ]; then
    echo "ERROR: SC2PATH not set. Run scripts/install_sc2_linux_headless.sh first."
    exit 1
fi
if [ ! -d "${SC2PATH}" ]; then
    echo "ERROR: SC2PATH=${SC2PATH} does not exist."
    exit 1
fi
echo "SC2PATH    : ${SC2PATH}"

# Activate virtual environment
if [ -f "${HOME}/projects/defab/venv/bin/activate" ]; then
    source "${HOME}/projects/defab/venv/bin/activate"
elif [ -f "${HOME}/.venv/bin/activate" ]; then
    source "${HOME}/.venv/bin/activate"
fi

cd "${REPO_DIR}"
echo "Working dir: $(pwd)"

mkdir -p "${TRACE_DIR}"
mkdir -p "$(dirname "${ROLLOUT_FILE}")"
mkdir -p logs/

echo "Starting self-play: ${GAMES} games..."

python scripts/run_sc2_selfplay.py \
    --games "${GAMES}" \
    --provider "${PROVIDER_A}" \
    --provider-b "${PROVIDER_B}" \
    --map "${MAP}" \
    --trace-dir "${TRACE_DIR}" \
    --output "${ROLLOUT_FILE}" \
    --verbose

EXIT_CODE=$?

echo "======================================================================="
echo "Self-play complete (exit ${EXIT_CODE})"
echo "Rollouts: ${ROLLOUT_FILE}"
echo "Traces  : ${TRACE_DIR}"
echo "End     : $(date)"
echo "======================================================================="

exit ${EXIT_CODE}
