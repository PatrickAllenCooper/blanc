#!/bin/bash
#
# Phase 0 Quick-Start: CURC environment setup + smoke test.
#
# Run this ONCE after SSH-ing to CURC:
#   ssh paco0228@login.rc.colorado.edu
#   cd /projects/paco0228/blanc
#   bash hpc/phase0_curc_quickstart.sh
#
# What it does:
#   1. git pull to sync with main
#   2. Sets up the defab-train conda env (idempotent)
#   3. Runs a 5-step SFT smoke test on Qwen-0.5B (login node, no GPU needed)
#   4. Runs prepare_sft_data.py on Tier 0 only
#   5. Prints next steps
#
# Author: Patrick Cooper

set -euo pipefail

PROJ_DIR="/projects/paco0228/blanc"
cd "$PROJ_DIR"

echo "======================================================="
echo "DeFAb Phase 0 Quick-Start"
echo "Start: $(date)"
echo "======================================================="

# 1. Pull latest
echo ""
echo "[1/5] Pulling latest from origin/main..."
git pull origin main
echo "Current commit: $(git log --oneline -1)"

# 2. Setup conda env (idempotent)
echo ""
echo "[2/5] Setting up defab-train conda environment..."
bash hpc/setup_curc_env.sh

# Activate
if ! command -v conda &>/dev/null; then
    module load anaconda 2>/dev/null || true
fi
eval "$(conda shell.bash hook)"
conda activate defab-train

export PYTHONPATH="$PROJ_DIR/src:${PYTHONPATH:-}"
export HF_HOME="/scratch/alpine/paco0228/hf_cache"
export TRANSFORMERS_CACHE="$HF_HOME"
mkdir -p "$HF_HOME" logs experiments/finetuning/data experiments/finetuning/checkpoints

# 3. SFT smoke test (login node, CPU only, no real GPU needed for 5 steps)
echo ""
echo "[3/5] Running SFT smoke test (Qwen-0.5B, 5 steps, CPU only)..."
timeout 300 python experiments/finetuning/train_sft.py \
    --base-model "Qwen/Qwen2.5-0.5B-Instruct" \
    --max-steps 5 \
    --output-dir /tmp/sft_smoke_$$ \
    --data-dir experiments/finetuning/data \
    --per-device-batch-size 1 \
    --grad-accum-steps 1 \
    --no-cuda 2>&1 | tail -5 \
    && echo "  SFT smoke test PASSED" \
    || echo "  SFT smoke test FAILED (check if train_sft.py has --no-cuda support; use --max-steps 5 on atesting GPU instead)"

# 4. Prepare Tier 0 SFT data
echo ""
echo "[4/5] Preparing Tier 0 SFT training data..."
python experiments/finetuning/prepare_sft_data.py \
    --modalities M4 M2 \
    --strategies direct cot \
    --output-dir experiments/finetuning/data \
    --instances-dir instances
echo "  SFT data written to experiments/finetuning/data/"
ls -lh experiments/finetuning/data/*.jsonl 2>/dev/null || true

# 5. Print next steps
echo ""
echo "======================================================="
echo "Phase 0 COMPLETE: $(date)"
echo "======================================================="
echo ""
echo "Next steps — submit these SLURM jobs:"
echo ""
echo "  # 1A: DeFAb-Hard generation (CPU, ~24h)"
echo "  sbatch hpc/slurm_generate_defab_hard.sh"
echo ""
echo "  # 1C: Constrained-output decoder ablation (run locally or via Foundry):"
echo "  python experiments/run_evaluation.py --provider foundry-deepseek \\"
echo "    --modalities M4 --strategies direct cot --include-level3 --level3-limit 35 \\"
echo "    --constrained --instances-dir instances \\"
echo "    --results-dir experiments/results/constrained_l3_$(date +%Y%m%d)"
echo ""
echo "  # 2A: SFT on Qwen-32B-AWQ (4 GPUs, 12h)"
echo "  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ',CURRICULUM='joint' \\"
echo "    hpc/slurm_train_sft.sh"
echo ""
echo "  # 2B: DPO standard on Qwen-32B-AWQ"
echo "  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ',DPO_VARIANT='standard',CURRICULUM='joint' \\"
echo "    hpc/slurm_train_dpo.sh"
echo ""
echo "  # 2C: DPO margin-weighted"
echo "  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ',DPO_VARIANT='margin',GAMMA='2.0' \\"
echo "    hpc/slurm_train_dpo.sh"
echo ""
echo "  # 2D: GRPO on L3-only"
echo "  sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ',CURRICULUM='l3_only' \\"
echo "    hpc/slurm_train_grpo.sh"
echo ""
echo "  # 3B: Tier 2/3 evaluation (Foundry, ~2h)"
echo "  python experiments/run_evaluation.py --provider foundry-gpt \\"
echo "    --modalities M4 --strategies direct --instances-dir instances/tier2_sample \\"
echo "    --results-dir experiments/results/tier2_$(date +%Y%m%d)"
echo ""
echo "  # 4A: Matched fact-injection ablation (must run first):"
echo "  python experiments/inject_facts_naturalistic.py"
echo "  # Then re-eval on instances/naturalistic_injected/"
echo ""
echo "  # 4B: DEFREASING comparison:"
echo "  git clone https://github.com/elizaallaway/defreasing data/defreasing"
echo "  python experiments/run_defreasing_comparison.py --defreasing-dir data/defreasing"
echo ""
echo "  # 4C: Human baseline (run interactively on your local machine):"
echo "  python experiments/run_human_baseline.py --solver-id YOUR_NAME"
echo ""
echo "Monitor jobs:  squeue -u paco0228"
echo "Check GPU util: seff <JOBID>"
echo "======================================================="
