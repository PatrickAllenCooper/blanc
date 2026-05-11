#!/bin/bash
#SBATCH --job-name=defab_hard_gen
#SBATCH --output=logs/hard_gen_%j.out
#SBATCH --error=logs/hard_gen_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb-Hard Pilot Generation
# Generates ~100 instances per axis (H1, H2, H3) across 64 CPU cores.
#
# Submit:
#   sbatch hpc/slurm_generate_defab_hard.sh
#
# Override target:
#   sbatch --export=ALL,TARGET=200 hpc/slurm_generate_defab_hard.sh

set -euo pipefail

TARGET="${TARGET:-100}"
SEED="${SEED:-42}"

echo "======================================================="
echo "DeFAb-Hard Pilot Generation"
echo "======================================================="
echo "Job ID  : $SLURM_JOB_ID"
echo "Node    : $SLURM_NODELIST"
echo "CPUs    : $SLURM_CPUS_PER_TASK"
echo "Target  : $TARGET per axis"
echo "Start   : $(date)"
echo ""

if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
conda activate defab-train

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"
export PYTHONPATH="$PROJ_DIR/src:${PYTHONPATH:-}"

mkdir -p logs instances/defab_hard

echo "Generating H1 (high-novelty) instances..."
python scripts/generate_defab_hard.py --axis h1 --target "$TARGET" --seed "$SEED" \
    --output-dir instances/defab_hard

echo "Generating H2 (deep-theory) instances..."
python scripts/generate_defab_hard.py --axis h2 --target "$TARGET" --seed "$((SEED+1))" \
    --output-dir instances/defab_hard

echo "Generating H3 (multi-anomaly) instances..."
python scripts/generate_defab_hard.py --axis h3 --target "$TARGET" --seed "$((SEED+2))" \
    --output-dir instances/defab_hard

echo ""
echo "======================================================="
echo "Generation complete: $(date)"
echo "Output: $PROJ_DIR/instances/defab_hard/"
ls -la instances/defab_hard/*/instances.json 2>/dev/null || true
echo "======================================================="
