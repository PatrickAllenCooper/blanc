#!/bin/bash
#SBATCH --job-name=defab_generate
#SBATCH --output=logs/generate_%j.out
#SBATCH --error=logs/generate_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64
#SBATCH --mem=128G
#SBATCH --partition=amilan

# DeFAb Instance Generation on CURC Alpine
# Generates instances from expert-curated KBs using parallel processing
#
# Author: Patrick Cooper
# Date: 2026-02-12

echo "======================================================================="
echo "DeFAb Instance Generation - CURC Alpine HPC"
echo "======================================================================="
echo "Job ID: $SLURM_JOB_ID"
echo "Node: $SLURM_NODELIST"
echo "CPUs: $SLURM_CPUS_PER_TASK"
echo "Memory: $SLURM_MEM_PER_NODE MB"
echo "Start: $(date)"
echo ""

# Load modules
module purge
module load anaconda
module load python/3.11

# Activate environment (create if doesn't exist)
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python -m venv venv
fi

source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Download expert KBs if not present
if [ ! -d "data/yago" ]; then
    echo "Downloading expert KBs..."
    python scripts/download_yago.py
    python scripts/download_wordnet.py
    python scripts/download_lkif.py
    python scripts/download_matonto.py
fi

# Run parallel instance generation
echo ""
echo "Starting parallel instance generation..."
echo "CPUs available: $SLURM_CPUS_PER_TASK"
echo ""

# Set number of workers to match allocated CPUs
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK

# Run generation script
python scripts/generate_instances_parallel.py

# Check results
echo ""
echo "======================================================================="
echo "Generation Complete"
echo "======================================================================="
echo "End: $(date)"
echo ""

# List generated files
if [ -f "biology_expert_instances_parallel.json" ]; then
    INSTANCES=$(python -c "import json; d=json.load(open('biology_expert_instances_parallel.json')); print(len(d['instances']))")
    echo "Biology instances: $INSTANCES"
fi

if [ -f "legal_expert_instances_parallel.json" ]; then
    INSTANCES=$(python -c "import json; d=json.load(open('legal_expert_instances_parallel.json')); print(len(d['instances']))")
    echo "Legal instances: $INSTANCES"
fi

if [ -f "materials_expert_instances_parallel.json" ]; then
    INSTANCES=$(python -c "import json; d=json.load(open('materials_expert_instances_parallel.json')); print(len(d['instances']))")
    echo "Materials instances: $INSTANCES"
fi

echo ""
echo "Job complete. Results saved to JSON files."
