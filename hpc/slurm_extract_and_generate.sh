#!/bin/bash
#SBATCH --job-name=defab_dataset
#SBATCH --output=logs/dataset_%j.out
#SBATCH --error=logs/dataset_%j.err
#SBATCH --time=24:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=32
#SBATCH --mem=128G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb Dataset Generation on CURC Alpine
#
# Runs the full extraction and instance generation pipeline:
#   1. Download source data (SUMO, Gene Ontology, MeSH, FrameNet, ConceptNet, OpenCyc)
#   2. Extract rules from all sources
#   3. Run Tier 1 cross-ontology extraction
#   4. Generate instances from all theories (including large ones like GO)
#
# This job uses the high-memory amilan partition (128 GB) to handle
# the Gene Ontology theory (409K rules) and Tier 1 chemistry domain
# that exceed local machine memory limits.
#
# Usage:
#   sbatch hpc/slurm_extract_and_generate.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb Full Dataset Generation - CURC Alpine"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "CPUs   : $SLURM_CPUS_PER_TASK"
echo "Memory : ${SLURM_MEM_PER_NODE:-unknown} MB"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

if [ -d "/projects/paco0228/software/anaconda/envs/defab-train" ]; then
    conda activate /projects/paco0228/software/anaconda/envs/defab-train
elif conda env list 2>/dev/null | grep -q "defab-train"; then
    conda activate defab-train
else
    echo "WARNING: defab-train env not found, using base"
fi

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

export PYTHONPATH="$PROJ_DIR/src:$PROJ_DIR/examples:${PYTHONPATH:-}"
export PYTHONUNBUFFERED=1

mkdir -p logs data/extracted data/tier1 instances/tier1 instances/multitier

echo "Python: $(python --version)"
echo "Working dir: $(pwd)"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Download source data
# ---------------------------------------------------------------------------
echo "Step 1: Downloading source data..."
echo "-----------------------------------------------------------------------"

python scripts/download_opencyc.py     2>&1 || echo "  OpenCyc download issue (may already exist)"
python scripts/download_conceptnet5.py 2>&1 || echo "  ConceptNet download issue"
python scripts/download_sumo.py        2>&1 || echo "  SUMO download issue"
python scripts/download_gene_ontology.py 2>&1 || echo "  GO download issue"
python scripts/download_mesh.py        2>&1 || echo "  MeSH download issue"
python scripts/download_framenet.py    2>&1 || echo "  FrameNet download issue"

echo ""

# ---------------------------------------------------------------------------
# Step 2: Multi-tier extraction (SUMO, GO, MeSH, FrameNet, Wikidata)
# ---------------------------------------------------------------------------
echo "Step 2: Multi-tier extraction..."
echo "-----------------------------------------------------------------------"

python scripts/extract_all_tiers.py --sources sumo,go,mesh,framenet,wikidata 2>&1

echo ""

# ---------------------------------------------------------------------------
# Step 3: Tier 1 cross-ontology extraction
# ---------------------------------------------------------------------------
echo "Step 3: Tier 1 cross-ontology extraction..."
echo "-----------------------------------------------------------------------"

python scripts/extract_cross_ontology_all.py 2>&1

echo ""

# ---------------------------------------------------------------------------
# Step 4: Generate Tier 1 instances (all 5 domains)
# ---------------------------------------------------------------------------
echo "Step 4: Tier 1 instance generation..."
echo "-----------------------------------------------------------------------"

python scripts/generate_tier1_instances.py 2>&1

echo ""

# ---------------------------------------------------------------------------
# Step 5: Generate multi-tier instances (GO, SUMO, FrameNet, etc.)
# ---------------------------------------------------------------------------
echo "Step 5: Multi-tier instance generation..."
echo "-----------------------------------------------------------------------"

python scripts/generate_multitier_instances.py 2>&1

echo ""

# ---------------------------------------------------------------------------
# Step 6: Package dataset
# ---------------------------------------------------------------------------
echo "Step 6: Packaging dataset..."
echo "-----------------------------------------------------------------------"

python scripts/package_tier1_dataset.py 2>&1

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "======================================================================="
echo "Dataset Generation Complete"
echo "======================================================================="
echo "End: $(date)"
echo ""

echo "Extracted theories:"
for DIR in data/extracted/*/; do
    NAME=$(basename "$DIR")
    if [ -f "$DIR/stats.json" ]; then
        RULES=$(python -c "import json; print(json.load(open('$DIR/stats.json'))['total_rules'])" 2>/dev/null || echo "?")
        DEFEATERS=$(python -c "import json; print(json.load(open('$DIR/stats.json'))['defeaters'])" 2>/dev/null || echo "?")
        echo "  $NAME: $RULES rules ($DEFEATERS defeaters)"
    fi
done

echo ""
echo "Instance files:"
for DIR in instances/tier1/*/; do
    NAME=$(basename "$DIR")
    if [ -f "$DIR/instances.json" ]; then
        COUNT=$(python -c "import json; print(len(json.load(open('$DIR/instances.json'))))" 2>/dev/null || echo "?")
        echo "  tier1/$NAME: $COUNT instances"
    fi
done

for DIR in instances/multitier/*/; do
    NAME=$(basename "$DIR")
    if [ -f "$DIR/instances.json" ]; then
        COUNT=$(python -c "import json; print(len(json.load(open('$DIR/instances.json'))))" 2>/dev/null || echo "?")
        echo "  multitier/$NAME: $COUNT instances"
    fi
done

echo ""
echo "Summary files:"
[ -f "instances/tier1/generation_summary.json" ] && cat instances/tier1/generation_summary.json
[ -f "instances/multitier/generation_summary.json" ] && cat instances/multitier/generation_summary.json

exit 0
