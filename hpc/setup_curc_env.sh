#!/bin/bash
#
# DeFAb CURC Environment Setup
#
# Run this ONCE on CURC to set up the defab-train conda environment
# for fine-tuning experiments. Run from an interactive session or login node.
#
# Prerequisites:
#   - CURC account with access to aa100 partition
#   - blanc repo cloned to /projects/paco0228/blanc
#
# Usage:
#   bash hpc/setup_curc_env.sh
#
# Author: Patrick Cooper

set -euo pipefail

echo "======================================================================="
echo "DeFAb CURC Environment Setup"
echo "======================================================================="
echo ""

PROJ_DIR="/projects/paco0228/blanc"

# ---------------------------------------------------------------------------
# 1. Verify project directory
# ---------------------------------------------------------------------------
if [ ! -d "$PROJ_DIR" ]; then
    echo "Cloning blanc repo..."
    cd /projects/paco0228
    git clone git@github.com:PatrickAllenCooper/blanc.git
else
    echo "Project directory exists: $PROJ_DIR"
    cd "$PROJ_DIR"
    echo "Pulling latest changes..."
    git pull
fi

cd "$PROJ_DIR"
echo "Current commit: $(git log --oneline -1)"
echo ""

# ---------------------------------------------------------------------------
# 2. Set up HuggingFace cache
# ---------------------------------------------------------------------------
export HF_HOME="/scratch/alpine/paco0228/hf_cache"
export TRANSFORMERS_CACHE="$HF_HOME"
mkdir -p "$HF_HOME"
echo "HF cache: $HF_HOME"
echo ""

# ---------------------------------------------------------------------------
# 3. Create defab-train conda environment
# ---------------------------------------------------------------------------
module purge
module load anaconda

if conda env list | grep -q "defab-train"; then
    echo "defab-train environment already exists."
    echo "To recreate: conda env remove -n defab-train && bash hpc/setup_curc_env.sh"
else
    echo "Creating defab-train conda environment..."
    conda create -n defab-train python=3.11 -y

    echo "Installing PyTorch with CUDA 12.1..."
    conda run -n defab-train pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

    echo "Installing training dependencies..."
    conda run -n defab-train pip install \
        transformers \
        accelerate \
        peft \
        trl \
        datasets \
        bitsandbytes \
        deepspeed

    echo "Installing additional dependencies..."
    conda run -n defab-train pip install \
        scipy \
        numpy \
        tqdm \
        python-dotenv \
        tenacity \
        lark \
        python-Levenshtein

    echo "Installing blanc in editable mode..."
    conda run -n defab-train pip install -e "$PROJ_DIR"

    echo ""
    echo "defab-train environment created successfully."
fi

# ---------------------------------------------------------------------------
# 4. Verify the vllm-env exists (for B1 response sampling)
# ---------------------------------------------------------------------------
echo ""
if [ -d "/projects/paco0228/software/anaconda/envs/vllm-env" ]; then
    echo "vllm-env found at /projects/paco0228/software/anaconda/envs/vllm-env"
else
    echo "WARNING: vllm-env not found. It is needed for B1 response sampling."
    echo "If it exists elsewhere, update hpc/slurm_sample_responses.sh accordingly."
fi

# ---------------------------------------------------------------------------
# 5. Create required directories
# ---------------------------------------------------------------------------
mkdir -p "$PROJ_DIR/logs"
mkdir -p "$PROJ_DIR/experiments/finetuning/data"
mkdir -p "$PROJ_DIR/experiments/finetuning/checkpoints"
mkdir -p "$PROJ_DIR/experiments/results"
echo ""
echo "Directories created."

# ---------------------------------------------------------------------------
# 6. Quick GPU verification
# ---------------------------------------------------------------------------
echo ""
echo "Verifying defab-train environment..."
conda activate defab-train
python -c "
import torch
print(f'PyTorch:      {torch.__version__}')
print(f'CUDA avail:   {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU count:    {torch.cuda.device_count()}')
    for i in range(torch.cuda.device_count()):
        print(f'  GPU {i}: {torch.cuda.get_device_name(i)}')

import transformers, peft, trl, datasets, deepspeed
print(f'transformers: {transformers.__version__}')
print(f'peft:         {peft.__version__}')
print(f'trl:          {trl.__version__}')
print(f'datasets:     {datasets.__version__}')
print(f'deepspeed:    {deepspeed.__version__}')
print('All imports OK.')
"

echo ""
echo "======================================================================="
echo "Setup complete."
echo ""
echo "Next steps:"
echo "  1. Submit initial experiment:"
echo "     cd $PROJ_DIR && bash hpc/initial_experiment.sh"
echo ""
echo "  2. Or submit individual jobs:"
echo "     sbatch --export=ALL,VLLM_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ' hpc/slurm_sample_responses.sh"
echo "     sbatch --export=ALL,BASE_MODEL='Qwen/Qwen2.5-32B-Instruct-AWQ' hpc/slurm_train_dpo.sh"
echo "======================================================================="
