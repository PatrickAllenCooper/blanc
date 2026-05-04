#!/bin/bash
#SBATCH --job-name=defab_debate
#SBATCH --output=logs/debate_%j.out
#SBATCH --error=logs/debate_%j.err
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --partition=amilan

# DeFAb Adversarial Defeasible Debate Experiments (Paper Section 7)
#
# Runs the debate protocol across knowledge bases using MCTS-guided
# proponent and opponent agents. Produces debate_results.json consumed
# by analyze_debate.py to generate Tables 7-9.
#
# No GPU required -- all reasoning is symbolic (MCTS over derivation space).
#
# Optional overrides (via --export or env):
#   DEBATE_KBS        Space-separated KB list (default: "all")
#   DEBATE_ROUNDS     Number of debate rounds  (default: 3)
#   MCTS_ITERATIONS   MCTS iterations per turn (default: 200)
#   EXPLORE_CONSTANT  UCB1 exploration constant (default: 1.414)
#   DISTRACTORS       Number of distractor hypotheses (default: 5)
#   DISTRACTOR_STRATEGY  "random", "syntactic", or "adversarial" (default: "syntactic")
#   SEED              Random seed (default: 42)
#
# Usage:
#   sbatch hpc/slurm_debate.sh
#   sbatch --export=ALL,DEBATE_ROUNDS=5,MCTS_ITERATIONS=500 hpc/slurm_debate.sh
#
# Author: Anonymous Authors

set -euo pipefail

echo "======================================================================="
echo "DeFAb Adversarial Defeasible Debate"
echo "======================================================================="
echo "Job ID   : $SLURM_JOB_ID"
echo "Node     : $SLURM_NODELIST"
echo "CPUs     : $SLURM_CPUS_PER_TASK"
echo "Start    : $(date)"
echo ""

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DEBATE_KBS="${DEBATE_KBS:-all}"
DEBATE_ROUNDS="${DEBATE_ROUNDS:-3}"
MCTS_ITERATIONS="${MCTS_ITERATIONS:-200}"
EXPLORE_CONSTANT="${EXPLORE_CONSTANT:-1.414}"
DISTRACTORS="${DISTRACTORS:-5}"
DISTRACTOR_STRATEGY="${DISTRACTOR_STRATEGY:-syntactic}"
SEED="${SEED:-42}"

echo "KBs              : $DEBATE_KBS"
echo "Rounds           : $DEBATE_ROUNDS"
echo "MCTS iterations  : $MCTS_ITERATIONS"
echo "Explore constant : $EXPLORE_CONSTANT"
echo "Distractors      : $DISTRACTORS"
echo "Strategy         : $DISTRACTOR_STRATEGY"
echo "Seed             : $SEED"
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

mkdir -p logs experiments/results

# ---------------------------------------------------------------------------
# Run debate experiments
# ---------------------------------------------------------------------------
echo ""
echo "Running debate experiments..."
echo ""

python experiments/debate/run_debate.py \
    --kb "$DEBATE_KBS" \
    --rounds "$DEBATE_ROUNDS" \
    --mcts-iterations "$MCTS_ITERATIONS" \
    --explore-constant "$EXPLORE_CONSTANT" \
    --distractors "$DISTRACTORS" \
    --distractor-strategy "$DISTRACTOR_STRATEGY" \
    --seed "$SEED"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ] && [ -f "experiments/results/debate_results.json" ]; then
    echo ""
    echo "Running debate analysis and generating Tables 7-9..."
    python experiments/debate/analyze_debate.py \
        --results-file experiments/results/debate_results.json \
        --output-dir paper/tables \
        2>&1 || echo "  (analyze_debate.py: non-fatal, skipping)"
fi

echo ""
echo "======================================================================="
echo "Debate Experiments Complete"
echo "======================================================================="
echo "End       : $(date)"
echo "Exit code : $EXIT_CODE"
echo "Results   : experiments/results/debate_results.json"
echo "Tables    : paper/tables/table7_debate_robustness.tex"
echo "            paper/tables/table8_debate_grounding_creativity.tex"
echo "            paper/tables/table9_debate_winners.tex"

exit $EXIT_CODE
