#!/bin/bash
#SBATCH --job-name=defab_go
#SBATCH --output=logs/go_gen_%j.out
#SBATCH --error=logs/go_gen_%j.err
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# Gene Ontology: re-extract with fixed extractor then generate instances.
# The fixed extractor adds body predicates to annotation rules, enabling
# derivation chains that the instance generation pipeline requires.
#
# Usage: sbatch hpc/slurm_gen_go.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb Gene Ontology Generation"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "CPUs   : $SLURM_CPUS_PER_TASK"
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

mkdir -p logs data/extracted/gene_ontology instances/multitier/gene_ontology

echo ""
echo "Step 1: Re-extract GO with fixed extractor..."
python scripts/extract_all_tiers.py --sources go

echo ""
echo "Step 2: Generate instances..."
python -u -c "
import pickle, json
from pathlib import Path
from scripts.generate_tier1_instances import generate_domain

with open('data/extracted/gene_ontology/theory.pkl', 'rb') as f:
    theory = pickle.load(f)
print(f'GO theory: {len(theory.rules)} rules, {len(theory.facts)} facts')

instances = generate_domain('gene_ontology', theory)
out = Path('instances/multitier/gene_ontology')
out.mkdir(parents=True, exist_ok=True)
with open(out / 'instances.json', 'w') as f:
    json.dump(instances, f)

l1 = sum(1 for x in instances if x['level'] == 1)
l2 = sum(1 for x in instances if x['level'] == 2)
l3 = sum(1 for x in instances if x['level'] == 3)
print(f'Generated {len(instances)} instances (L1={l1}, L2={l2}, L3={l3})')
"

echo ""
echo "======================================================================="
echo "Done: $(date)"
echo "======================================================================="
