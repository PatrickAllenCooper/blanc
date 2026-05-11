#!/bin/bash
#SBATCH --job-name=defab_m5_images
#SBATCH --output=logs/m5_images_%j.out
#SBATCH --error=logs/m5_images_%j.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb M5 Image Preparation
#
# Harvests entity images from Wikidata P18 (and optionally VisualSem /
# BabelNet) and downloads thumbnails to scratch storage.  Produces a
# consolidated ImageManifest at data/images/manifest.json (in the
# persistent /projects/ directory).
#
# Storage strategy:
#   - Images (bulk data)  -> /scratch/alpine/$USER/defab_images/
#     Scratch has 10 TB quota; images can be re-downloaded if purged.
#   - Manifest (metadata) -> data/images/manifest.json (under /projects/)
#     Persists across scratch purges; contains URLs for re-download.
#
# This is a prerequisite for any M5 evaluation job.
#
# Usage:
#   sbatch hpc/slurm_prepare_m5_images.sh
#
# Environment variables (all optional):
#   QID_MAP           Path to entity-name -> Q-ID mapping JSON
#                     (default: data/qid_map.json)
#   THUMB_WIDTH       Thumbnail width in pixels (default: 640)
#   IMAGE_DIR         Download directory (default: /scratch/alpine/$USER/defab_images)
#   MANIFEST_DIR      Manifest output directory (default: data/images, under /projects/)
#   SOURCES           Space-separated list of sources (default: wikidata)
#   VISUALSEM_DIR     Path to VisualSem download (required if sources
#                     includes "visualsem")
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb M5 Image Preparation"
echo "======================================================================="
echo "Job ID : $SLURM_JOB_ID"
echo "Node   : $SLURM_NODELIST"
echo "Start  : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
QID_MAP="${QID_MAP:-data/qid_map.json}"
THUMB_WIDTH="${THUMB_WIDTH:-640}"
IMAGE_DIR="${IMAGE_DIR:-/scratch/alpine/$USER/defab_images}"
MANIFEST_DIR="${MANIFEST_DIR:-data/images}"
SOURCES="${SOURCES:-wikidata}"
VISUALSEM_DIR="${VISUALSEM_DIR:-}"

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || module load Anaconda3 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"

module load python/3.11 2>/dev/null || true

if [ -n "${SLURM_SUBMIT_DIR:-}" ]; then
    PROJ_DIR="$SLURM_SUBMIT_DIR"
else
    PROJ_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
fi
cd "$PROJ_DIR"

if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
else
    python3 -m venv venv
    source venv/bin/activate
fi

pip install -q -e ".[vision]" 2>/dev/null || pip install -q -r requirements.txt

mkdir -p logs "$IMAGE_DIR" "$MANIFEST_DIR"

echo "Sources      : $SOURCES"
echo "QID map      : $QID_MAP"
echo "Thumb width  : $THUMB_WIDTH"
echo "Image dir    : $IMAGE_DIR (scratch -- re-downloadable)"
echo "Manifest dir : $MANIFEST_DIR (projects -- persistent)"
echo ""

# ---------------------------------------------------------------------------
# Build source arguments
# ---------------------------------------------------------------------------
SOURCE_ARGS="--sources $SOURCES"
EXTRA_ARGS=""

if [ -f "$QID_MAP" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --qid-map $QID_MAP"
else
    echo "WARNING: QID map not found at $QID_MAP"
    echo "Wikidata harvest will be skipped unless a QID map is provided."
fi

if [[ "$SOURCES" == *"visualsem"* ]] && [ -n "$VISUALSEM_DIR" ]; then
    EXTRA_ARGS="$EXTRA_ARGS --visualsem-dir $VISUALSEM_DIR"
fi

# ---------------------------------------------------------------------------
# Run image harvesting and download
# ---------------------------------------------------------------------------
MANIFEST_PATH="$MANIFEST_DIR/manifest.json"

echo "Starting image harvesting..."
python scripts/download_entity_images.py \
    $SOURCE_ARGS \
    --output-dir "$IMAGE_DIR" \
    --manifest   "$MANIFEST_PATH" \
    --thumb-width "$THUMB_WIDTH" \
    --max-per-entity 3 \
    $EXTRA_ARGS

echo ""
echo "======================================================================="
echo "Image Preparation Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Manifest : $MANIFEST_PATH (persistent)"
echo "Images   : $IMAGE_DIR (scratch)"

if [ -f "$MANIFEST_PATH" ]; then
    python3 -c "
import json
with open('$MANIFEST_PATH') as f:
    d = json.load(f)
ents = d.get('entities', {})
imgs = sum(len(v) for v in ents.values())
print(f'  Entities : {len(ents)}')
print(f'  Images   : {imgs}')
" 2>/dev/null || true
fi
