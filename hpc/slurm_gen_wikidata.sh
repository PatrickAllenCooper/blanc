#!/bin/bash
#SBATCH --job-name=defab_wikidata
#SBATCH --output=logs/wikidata_gen_%j.out
#SBATCH --error=logs/wikidata_gen_%j.err
#SBATCH --time=08:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# Wikidata: re-extract with fixed extractor then generate instances.
# The fixed extractor produces facts using isa/has_property predicates
# that match rule body patterns, enabling derivation chains.
# Critical source: 11,557 P2303 defeaters for Level 3 instances.
#
# Usage: sbatch hpc/slurm_gen_wikidata.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb Wikidata Generation"
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

mkdir -p logs data/extracted/wikidata instances/multitier/wikidata

echo ""
echo "Step 1: Re-extract Wikidata with fixed extractor..."
python scripts/extract_all_tiers.py --sources wikidata

echo ""
echo "Step 2: Generate instances..."
python -u -c "
import pickle, json
from pathlib import Path
from scripts.generate_tier1_instances import generate_domain

with open('data/extracted/wikidata/theory.pkl', 'rb') as f:
    theory = pickle.load(f)
print(f'Wikidata theory: {len(theory.rules)} rules, {len(theory.facts)} facts')

instances = generate_domain('wikidata', theory)
out = Path('instances/multitier/wikidata')
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
