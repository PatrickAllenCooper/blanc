#!/bin/bash
#SBATCH --job-name=defab_ft_analysis
#SBATCH --output=logs/ft_analysis_%j.out
#SBATCH --error=logs/ft_analysis_%j.err
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --partition=amilan
#SBATCH --qos=normal

# DeFAb Phase B6: Fine-Tuning Analysis Pipeline (Paper Section 6.7-6.8)
#
# Runs all fine-tuning analysis scripts after checkpoint evaluation completes.
# Generates Tables 4-6 and tests Conjectures 1-6.
#
# No GPU required -- all analysis is over cached evaluation results.
#
# Scripts executed (in order):
#   1. generate_ft_tables.py            -- LaTeX Tables 4-6
#   2. analyze_ft_lift.py               -- Conjecture 1: L3 lift
#   3. analyze_error_shift.py           -- Conjecture 2: E1/E2 -> E4/E5 shift
#   4. analyze_level_transfer.py        -- Conjecture 3: L1/L2 -> L3 transfer
#   5. analyze_margin_effect.py         -- Conjecture 4: margin DPO > standard
#   6. analyze_parameter_sparsity.py    -- Conjecture 5: GRPO sparsity
#   7. analyze_curriculum.py            -- Curriculum comparison
#   8. analyze_novel_resolutions.py     -- Novel correct resolutions
#   9. analyze_scaling_projections.py   -- Log-linear scaling curves
#  10. analyze_reward_fidelity.py       -- Spearman rho(R_phi, verifier)
#  11. analyze_reward_overoptimization.py -- Reward hacking diagnostic
#
# Optional overrides (via --export or env):
#   RESULTS_DIR       Path to fine-tuned evaluation results (default: experiments/results)
#   BASE_RESULTS_DIR  Path to base model results for comparison (default: experiments/results)
#   OUTPUT_DIR        Path for LaTeX table output (default: paper/tables)
#
# Usage:
#   sbatch hpc/slurm_ft_analysis.sh
#   sbatch --export=ALL,RESULTS_DIR=experiments/results/finetuned hpc/slurm_ft_analysis.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb Phase B6: Fine-Tuning Analysis"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RESULTS_DIR="${RESULTS_DIR:-experiments/results}"
BASE_RESULTS_DIR="${BASE_RESULTS_DIR:-experiments/results}"
OUTPUT_DIR="${OUTPUT_DIR:-paper/tables}"

echo "Results dir      : $RESULTS_DIR"
echo "Base results dir : $BASE_RESULTS_DIR"
echo "Output dir       : $OUTPUT_DIR"
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

mkdir -p logs "$OUTPUT_DIR"

PASS=0
FAIL=0

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
# 1. Generate LaTeX Tables 4-6
# ---------------------------------------------------------------------------
run_script "Generate FT Tables 4-6" \
    python experiments/finetuning/generate_ft_tables.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR" \
        --output-dir "$OUTPUT_DIR"

# ---------------------------------------------------------------------------
# 2. Conjecture 1: L3 lift
# ---------------------------------------------------------------------------
run_script "Conjecture 1: L3 Lift (analyze_ft_lift)" \
    python experiments/finetuning/analyze_ft_lift.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR"

# ---------------------------------------------------------------------------
# 3. Conjecture 2: Error shift E1/E2 -> E4/E5
# ---------------------------------------------------------------------------
run_script "Conjecture 2: Error Shift (analyze_error_shift)" \
    python experiments/finetuning/analyze_error_shift.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR"

# ---------------------------------------------------------------------------
# 4. Conjecture 3: Level transfer
# ---------------------------------------------------------------------------
run_script "Conjecture 3: Level Transfer (analyze_level_transfer)" \
    python experiments/finetuning/analyze_level_transfer.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR"

# ---------------------------------------------------------------------------
# 5. Conjecture 4: Margin DPO > standard
# ---------------------------------------------------------------------------
run_script "Conjecture 4: Margin Effect (analyze_margin_effect)" \
    python experiments/finetuning/analyze_margin_effect.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR"

# ---------------------------------------------------------------------------
# 6. Conjecture 5: GRPO sparsity
# ---------------------------------------------------------------------------
run_script "Conjecture 5: Parameter Sparsity (analyze_parameter_sparsity)" \
    python experiments/finetuning/analyze_parameter_sparsity.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 7. Curriculum comparison
# ---------------------------------------------------------------------------
run_script "Curriculum Comparison (analyze_curriculum)" \
    python experiments/finetuning/analyze_curriculum.py \
        --results-dir "$RESULTS_DIR" \
        --base-results-dir "$BASE_RESULTS_DIR"

# ---------------------------------------------------------------------------
# 8. Novel correct resolutions
# ---------------------------------------------------------------------------
run_script "Novel Resolutions (analyze_novel_resolutions)" \
    python experiments/finetuning/analyze_novel_resolutions.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 9. Scaling projections
# ---------------------------------------------------------------------------
run_script "Scaling Projections (analyze_scaling_projections)" \
    python experiments/finetuning/analyze_scaling_projections.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 10. Reward fidelity
# ---------------------------------------------------------------------------
run_script "Reward Fidelity (analyze_reward_fidelity)" \
    python experiments/finetuning/analyze_reward_fidelity.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# 11. Reward overoptimization
# ---------------------------------------------------------------------------
run_script "Reward Overoptimization (analyze_reward_overoptimization)" \
    python experiments/finetuning/analyze_reward_overoptimization.py \
        --results-dir "$RESULTS_DIR"

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "======================================================================="
echo "Fine-Tuning Analysis Complete"
echo "======================================================================="
echo "End      : $(date)"
echo "Passed   : $PASS"
echo "Failed   : $FAIL"
echo ""
echo "Tables written to: $OUTPUT_DIR/"
echo "  table4_ft_main.tex"
echo "  table5_ft_curriculum.tex"
echo "  table6_ft_error.tex"

if [ $FAIL -gt 0 ]; then
    echo ""
    echo "WARNING: $FAIL script(s) failed. Check log for details."
    exit 1
fi

exit 0
