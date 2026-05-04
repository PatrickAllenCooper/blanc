#!/bin/bash
#SBATCH --job-name=defab_analysis
#SBATCH --output=logs/analysis_%j.out
#SBATCH --error=logs/analysis_%j.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=amilan

# DeFAb Phase A4: Full Analysis Pipeline (Paper Section 5)
#
# Runs all analysis scripts after base evaluation completes.
# Generates Tables 1-3, statistical tests, and Section 5 diagnostics.
#
# No GPU required -- all analysis is over cached evaluation results.
#
# Scripts executed (in order):
#   1. symbolic_baseline.py          -- symbolic solver ceiling (L2=100%, L3=100%)
#   2. validate_decoder_pipeline.py  -- M2-M4 round-trip validation
#   3. analyze_results.py            -- primary accuracy tables
#   4. generate_paper_tables.py      -- LaTeX Tables 1-3
#   5. error_taxonomy.py             -- E1-E5 error distribution
#   6. novelty_analysis.py           -- Level 3 novelty analysis
#   7. conservativity_analysis.py    -- conservativity diagnostics
#   8. scaling_analysis.py           -- theory size scaling
#   9. difficulty_analysis.py        -- structural difficulty distributions
#  10. partition_sensitivity.py      -- partition function sensitivity
#  11. statistics.py                 -- dataset statistics (Section 4.3)
#
# Optional overrides (via --export or env):
#   RESULTS_DIR       Path to evaluation results (default: experiments/results)
#   OUTPUT_DIR        Path for LaTeX table output (default: paper/tables)
#   SKIP_SYMBOLIC     "true" to skip symbolic baseline (default: false)
#   SKIP_DECODER      "true" to skip decoder validation (default: false)
#
# Usage:
#   sbatch hpc/slurm_analysis.sh
#   sbatch --export=ALL,RESULTS_DIR=experiments/results/foundry_gpt52_20260228 hpc/slurm_analysis.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb Phase A4: Full Analysis Pipeline"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESULTS_DIR="${RESULTS_DIR:-experiments/results}"
OUTPUT_DIR="${OUTPUT_DIR:-paper/tables}"
SKIP_SYMBOLIC="${SKIP_SYMBOLIC:-false}"
SKIP_DECODER="${SKIP_DECODER:-false}"

echo "Results dir  : $RESULTS_DIR"
echo "Output dir   : $OUTPUT_DIR"
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

export PYTHONPATH="${PROJ_DIR}/src:${PROJ_DIR}/experiments:${PROJ_DIR}/examples:${PYTHONPATH:-}"

mkdir -p logs "$OUTPUT_DIR" experiments/results

PASS=0
FAIL=0
SKIP=0

run_script() {
    local NAME="$1"
    shift
    echo ""
    echo "--- $NAME ---"
    if "$@" 2>&1; then
        echo "  OK"
        (( PASS++ )) || true
    else
        echo "  FAILED (non-fatal, continuing)"
        (( FAIL++ )) || true
    fi
}

# ---------------------------------------------------------------------------
# 1. Symbolic baseline
# ---------------------------------------------------------------------------
if [ "$SKIP_SYMBOLIC" != "true" ]; then
    run_script "Symbolic Baseline (Level 2)" \
        python experiments/symbolic_baseline.py --level 2 \
            --save experiments/results/symbolic_l2.json

    run_script "Symbolic Baseline (Level 3)" \
        python experiments/symbolic_baseline.py --level 3 \
            --save experiments/results/symbolic_l3.json
else
    echo "Skipping symbolic baseline (SKIP_SYMBOLIC=true)"
    (( SKIP += 2 )) || true
fi

# ---------------------------------------------------------------------------
# 2. Decoder validation
# ---------------------------------------------------------------------------
if [ "$SKIP_DECODER" != "true" ]; then
    run_script "Decoder Pipeline Validation" \
        python experiments/validate_decoder_pipeline.py
else
    echo "Skipping decoder validation (SKIP_DECODER=true)"
    (( SKIP++ )) || true
fi

# ---------------------------------------------------------------------------
# 3. Primary analysis
# ---------------------------------------------------------------------------
run_script "Analyze Results" \
    python experiments/analyze_results.py \
        --results-dir "$RESULTS_DIR" \
        --save "$RESULTS_DIR/summary.json"

# ---------------------------------------------------------------------------
# 4. Generate paper tables (Tables 1-3)
# ---------------------------------------------------------------------------
run_script "Generate Paper Tables 1-3" \
    python experiments/generate_paper_tables.py \
        --results-dir "$RESULTS_DIR" \
        --output-dir "$OUTPUT_DIR" \
        --canonical

# ---------------------------------------------------------------------------
# 5. Error taxonomy
# ---------------------------------------------------------------------------
run_script "Error Taxonomy" \
    python experiments/error_taxonomy.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 6. Novelty analysis
# ---------------------------------------------------------------------------
run_script "Novelty Analysis" \
    python experiments/novelty_analysis.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 7. Conservativity analysis
# ---------------------------------------------------------------------------
run_script "Conservativity Analysis" \
    python experiments/conservativity_analysis.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 8. Scaling analysis
# ---------------------------------------------------------------------------
run_script "Scaling Analysis" \
    python experiments/scaling_analysis.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 9. Difficulty analysis
# ---------------------------------------------------------------------------
run_script "Difficulty Analysis" \
    python experiments/difficulty_analysis.py \
        --save-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 10. Partition sensitivity
# ---------------------------------------------------------------------------
run_script "Partition Sensitivity" \
    python experiments/partition_sensitivity.py \
        --save-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 11. Dataset statistics
# ---------------------------------------------------------------------------
run_script "Dataset Statistics" \
    python experiments/statistics.py

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Analysis Pipeline Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Passed   : $PASS"
echo "Failed   : $FAIL"
echo "Skipped  : $SKIP"
echo ""
echo "Tables written to: $OUTPUT_DIR/"
echo "Summaries written to: $RESULTS_DIR/"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "WARNING: $FAIL script(s) failed. Check log for details."
    exit 1
fi

exit 0
