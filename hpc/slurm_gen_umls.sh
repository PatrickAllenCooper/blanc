#!/bin/bash
#SBATCH --job-name=defab_umls
#SBATCH --output=logs/umls_gen_%j.out
#SBATCH --error=logs/umls_gen_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=48
#SBATCH --mem=128G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# UMLS 2025AB: subsampled instance generation.
# The full UMLS theory has 29.5M rules -- too large to partition as one
# theory. This script samples connected CUI subgraphs and generates
# instances from each.
#
# Prerequisite: UMLS theory must be extracted and patched with body
# predicates. If data/extracted/umls/theory.pkl does not exist on CURC,
# run scripts/_extract_umls.py first (requires UMLS RRF files).
#
# Usage: sbatch hpc/slurm_gen_umls.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb UMLS Subsampled Generation"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "CPUs   : $SLURM_CPUS_PER_TASK"
echo "Memory : ${SLURM_MEM_PER_NODE:-unknown} MB"
echo "Start  : $(date)"

if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
conda activate defab-train 2>/dev/null || conda activate base

PROJ_DIR="${SLURM_SUBMIT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$PROJ_DIR"
export PYTHONPATH="$PROJ_DIR/src:$PROJ_DIR/examples:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

mkdir -p logs instances/multitier/umls

if [ ! -f "data/extracted/umls/theory.pkl" ]; then
    echo "ERROR: UMLS theory not found at data/extracted/umls/theory.pkl"
    echo "You need to either:"
    echo "  1. Copy theory.pkl from local machine, or"
    echo "  2. Run: python scripts/_extract_umls.py (requires UMLS RRF files)"
    exit 1
fi

echo ""
python -u scripts/_gen_umls_subsampled.py

echo ""
echo "======================================================================="
echo "Done: $(date)"
echo "======================================================================="
