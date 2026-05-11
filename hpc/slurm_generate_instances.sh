#!/bin/bash
#SBATCH --job-name=defab_generate
#SBATCH --output=logs/generate_%j.out
#SBATCH --error=logs/generate_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=64G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb Instance Generation on CURC Alpine
#
# Generates Level 2 and Level 3 instances from expert-curated KBs
# (Biology, Legal, Materials) using all 13 partition strategies.
#
# Output files (written to project root):
#   biology_instances_expert.json
#   legal_instances_expert.json
#   materials_instances_expert.json
#
# Level 3 instances are generated separately via generate_level3_instances.py.
#
# Usage:
#   sbatch hpc/slurm_generate_instances.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb Instance Generation - CURC Alpine HPC"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "CPUs   : $SLURM_CPUS_PER_TASK"
echo "Memory : ${SLURM_MEM_PER_NODE:-unknown} MB"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Environment setup
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
module load python/3.11

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

export PYTHONPATH="${PROJ_DIR}/src:${PROJ_DIR}/examples:${PYTHONPATH:-}"

mkdir -p logs

# ---------------------------------------------------------------------------
# Download expert KBs if not present
# ---------------------------------------------------------------------------
if [ ! -d "data/yago" ] || [ ! -d "data/wordnet" ]; then
    echo "Downloading expert KBs..."
    python scripts/download_yago.py      2>&1 || echo "  YAGO download skipped"
    python scripts/download_wordnet.py   2>&1 || echo "  WordNet download skipped"
    python scripts/download_matonto.py   2>&1 || echo "  MatOnto download skipped"
fi

# ---------------------------------------------------------------------------
# Generate Level 2 instances (all 3 domains, 13 partition strategies)
# ---------------------------------------------------------------------------
echo ""
echo "Starting Level 2 instance generation..."
python scripts/generate_all_instances.py
L2_EXIT=$?

# ---------------------------------------------------------------------------
# Generate Level 3 instances
# ---------------------------------------------------------------------------
echo ""
echo "Starting Level 3 instance generation..."
python scripts/generate_level3_instances.py
L3_EXIT=$?

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Generation Complete"
echo "======================================================================="
echo "End : $(date)"
echo ""

for DOMAIN in biology legal materials; do
    FILE="${DOMAIN}_instances_expert.json"
    if [ -f "$FILE" ]; then
        COUNT=$(python -c "import json; d=json.load(open('$FILE')); print(len(d['instances']))" 2>/dev/null || echo "?")
        echo "${DOMAIN^} L2 instances: $COUNT"
    else
        echo "${DOMAIN^} L2 instances: FILE NOT FOUND"
    fi
done

echo ""
echo "L2 generation exit code: $L2_EXIT"
echo "L3 generation exit code: $L3_EXIT"

if [ $L2_EXIT -ne 0 ] || [ $L3_EXIT -ne 0 ]; then
    exit 1
fi

exit 0
