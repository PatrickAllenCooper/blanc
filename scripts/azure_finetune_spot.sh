#!/usr/bin/env bash
# =============================================================================
# azure_finetune_spot.sh -- Spot-VM-resilient DeFAb fine-tuning orchestrator
#
# Designed for Azure Spot VMs with automatic deallocation/reallocation.
# On every boot the script is invoked by systemd, reads a state file to
# determine what was completed, and resumes from the last successful step.
#
# Deallocation safety:
#   - Each training step saves checkpoints every 50 steps (every ~5 min)
#   - HuggingFace Trainer resumes from the latest checkpoint automatically
#   - A JSON state file records every completed step
#   - A trap on SIGTERM (Azure gives 30s before deallocation) saves state
#     and stops vLLM servers cleanly
#
# First-time setup on a fresh Azure VM:
#   1. Install this script:
#        sudo install -m 755 scripts/azure_finetune_spot.sh /usr/local/bin/defab_finetune
#   2. Install the systemd service:
#        sudo cp scripts/defab_finetune.service /etc/systemd/system/
#        sudo systemctl enable defab_finetune
#        sudo systemctl start defab_finetune
#   3. Monitor:
#        journalctl -u defab_finetune -f
#
# Author: Patrick Cooper
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration -- edit these or set as environment variables
# ---------------------------------------------------------------------------

REPO_DIR="${REPO_DIR:-/home/azureuser/blanc}"
HF_TOKEN="${HF_TOKEN:-}"            # set via /etc/defab/secrets or export HF_TOKEN=...
HF_REPO="PatrickAllenCooper/DeFAb"
HF_HOME="${HF_HOME:-/data/hf_cache}"

RESULTS_BASE="${RESULTS_BASE:-/data/defab_results}"
DATA_DIR="${REPO_DIR}/experiments/finetuning/data"
INSTANCES_DIR="${REPO_DIR}/instances"
SPLITS_FILE="${INSTANCES_DIR}/splits.json"
DS_CONFIG="${REPO_DIR}/experiments/finetuning/ds_config_zero2.json"
VLLM_PORT="${VLLM_PORT:-8200}"

# Checkpoint frequency: save every N steps (~5 min at typical throughput)
SAVE_STEPS=50
EVAL_STEPS=100

# Batch config for 2x A100
PER_DEVICE_BS=2
GRAD_ACCUM=8
N_GPU=2

# State file tracks what has been completed across reboots
STATE_FILE="${RESULTS_BASE}/.finetune_state.json"

# Log file (appended on every boot)
LOG_FILE="${RESULTS_BASE}/run.log"

# ---------------------------------------------------------------------------
# Model matrix
# ---------------------------------------------------------------------------

declare -A MODEL_IDS=(
    [qwen72]="Qwen/Qwen2.5-72B-Instruct"
    [qwen32]="Qwen/Qwen2.5-32B-Instruct"
    [deepseek]="deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
)
MODELS=("qwen72" "qwen32" "deepseek")
METHODS=("sft" "dpo_standard" "dpo_margin" "grpo" "rlhf_vitl")

# PID of any vLLM server we start (for cleanup on SIGTERM)
VLLM_PID=""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

mkdir -p "$RESULTS_BASE"
exec > >(tee -a "$LOG_FILE") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
log_section() {
    echo ""
    echo "============================================================"
    echo "  $*"
    echo "============================================================"
    echo ""
}

# ---------------------------------------------------------------------------
# SIGTERM handler -- Azure gives 30 seconds before deallocation
# ---------------------------------------------------------------------------

on_sigterm() {
    log "SIGTERM received (Azure spot eviction). Saving state and shutting down..."
    if [[ -n "$VLLM_PID" ]]; then
        kill "$VLLM_PID" 2>/dev/null || true
        wait "$VLLM_PID" 2>/dev/null || true
        log "vLLM server stopped."
    fi
    log "State saved at: $STATE_FILE"
    log "Training will resume on next boot."
    exit 0
}
trap on_sigterm SIGTERM SIGINT

# ---------------------------------------------------------------------------
# State file helpers
# State file format:
#   { "completed": ["setup", "download", "data_qwen72", "sft_qwen72", ...] }
# ---------------------------------------------------------------------------

state_init() {
    if [[ ! -f "$STATE_FILE" ]]; then
        echo '{"completed":[]}' > "$STATE_FILE"
        log "Initialized state file: $STATE_FILE"
    fi
}

state_is_done() {
    local key="$1"
    python3 -c "
import json, sys
state = json.load(open('${STATE_FILE}'))
sys.exit(0 if '${key}' in state['completed'] else 1)
" 2>/dev/null
}

state_mark_done() {
    local key="$1"
    python3 -c "
import json
state = json.load(open('${STATE_FILE}'))
if '${key}' not in state['completed']:
    state['completed'].append('${key}')
json.dump(state, open('${STATE_FILE}', 'w'), indent=2)
"
    log "State: marked '$key' as complete."
}

# Run a step only if not already completed
run_step() {
    local key="$1"; shift
    if state_is_done "$key"; then
        log "Skipping '$key' (already complete)"
        return 0
    fi
    log "Running step: $key"
    "$@"
    state_mark_done "$key"
}

# Find latest HuggingFace Trainer checkpoint in a directory
latest_checkpoint() {
    local dir="$1"
    # Trainer saves checkpoints as checkpoint-N; return the highest
    local ckpt
    ckpt=$(ls -d "${dir}/checkpoint-"* 2>/dev/null | sort -t- -k2 -n | tail -1 || echo "")
    echo "$ckpt"
}

# ---------------------------------------------------------------------------
# Wait for vLLM server to be ready
# ---------------------------------------------------------------------------

wait_for_server() {
    local url="$1"
    log "Waiting for vLLM server at $url ..."
    for i in $(seq 1 300); do
        if curl -sf "${url}/health" >/dev/null 2>&1; then
            log "Server ready after ${i}s"
            return 0
        fi
        sleep 1
    done
    log "ERROR: server did not become ready within 300s"
    return 1
}

# ---------------------------------------------------------------------------
# Phase 0: Environment setup (runs once, then skipped)
# ---------------------------------------------------------------------------

do_setup() {
    log_section "Phase 0: Environment Setup"
    cd "$REPO_DIR"

    log "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q \
        "torch==2.5.1+cu121" \
        "torchvision==0.20.1+cu121" \
        "torchaudio==2.5.1+cu121" \
        --index-url https://download.pytorch.org/whl/cu121
    pip install -q \
        "transformers==4.47.0" \
        "trl==0.12.0" \
        "peft==0.14.0" \
        "bitsandbytes==0.45.0" \
        "deepspeed==0.15.4" \
        "accelerate==1.2.1" \
        "datasets==3.2.0" \
        "huggingface_hub==0.27.0" \
        "vllm==0.6.6" \
        "sentencepiece" \
        "scipy" \
        "numpy<2" \
        "tensorboard" \
        "tenacity" \
        "anthropic" \
        "openai"

    pip install -q -e .
    log "Setup complete."
}

# ---------------------------------------------------------------------------
# Phase 1: Download DeFAb dataset (runs once, then skipped)
# ---------------------------------------------------------------------------

do_download() {
    log_section "Phase 1: Download DeFAb Dataset"
    cd "$REPO_DIR"

    export HF_TOKEN
    python -u -c "
from huggingface_hub import snapshot_download
import os
snapshot_download(
    repo_id='${HF_REPO}',
    repo_type='dataset',
    local_dir='${REPO_DIR}/instances_hf',
    allow_patterns=['instances/**'],
    token=os.environ.get('HF_TOKEN'),
)
print('Download complete.')
"

    mkdir -p "${INSTANCES_DIR}/tier0" "${INSTANCES_DIR}/tier1"
    for f in biology_dev_instances legal_dev_instances materials_dev_instances level3_instances; do
        src="${REPO_DIR}/instances_hf/instances/tier0/${f}.json"
        [[ -f "$src" ]] && cp "$src" "${INSTANCES_DIR}/${f}.json"
    done
    for domain in biology chemistry everyday legal materials; do
        src="${REPO_DIR}/instances_hf/instances/tier1/${domain}/instances.json"
        [[ -f "$src" ]] && mkdir -p "${INSTANCES_DIR}/tier1/${domain}" && cp "$src" "${INSTANCES_DIR}/tier1/${domain}/instances.json"
    done
    log "Dataset ready at ${INSTANCES_DIR}"
}

# ---------------------------------------------------------------------------
# Phase 2: Data preparation (per model, runs once each, then skipped)
# ---------------------------------------------------------------------------

do_prepare_data() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"

    log_section "Phase 2: Data Prep for $model_slug"
    cd "$REPO_DIR"
    mkdir -p "$DATA_DIR"

    # SFT gold data
    if [[ ! -f "${DATA_DIR}/sft_train.jsonl" ]]; then
        python experiments/finetuning/prepare_sft_data.py \
            --instances-dir "$INSTANCES_DIR" \
            --domains biology legal materials \
            --modalities M4 M2 \
            --strategies direct \
            --output-dir "$DATA_DIR" \
            --splits-file "$SPLITS_FILE" \
            --seed 42
    else
        log "SFT data already exists, skipping."
    fi

    # Preference data (requires vLLM)
    pref_file="${DATA_DIR}/preferences_${model_slug}.jsonl"
    if [[ -f "$pref_file" ]]; then
        log "Preference file already exists: $pref_file"
        return 0
    fi

    log "Starting vLLM server for preference sampling..."
    export CUDA_VISIBLE_DEVICES=0
    python -m vllm.entrypoints.openai.api_server \
        --model "$model_id" \
        --port "$VLLM_PORT" \
        --dtype auto \
        --max-model-len 4096 \
        --gpu-memory-utilization 0.90 \
        --enforce-eager \
        2>&1 | tee "${RESULTS_BASE}/vllm_${model_slug}_sample.log" &
    VLLM_PID=$!

    wait_for_server "http://localhost:${VLLM_PORT}" || {
        kill $VLLM_PID 2>/dev/null; VLLM_PID=""; exit 1
    }
    export CUDA_VISIBLE_DEVICES=0,1

    python experiments/finetuning/prepare_preference_data.py \
        --provider curc \
        --base-url "http://localhost:${VLLM_PORT}" \
        --model-name "$model_id" \
        --num-samples 16 \
        --temperature 0.7 \
        --min-margin 0.25 \
        --instances-dir "$INSTANCES_DIR" \
        --domains biology legal materials \
        --modalities M4 \
        --strategies direct \
        --output-dir "$DATA_DIR" \
        --splits-file "$SPLITS_FILE" \
        --seed 42

    kill $VLLM_PID 2>/dev/null || true
    wait $VLLM_PID 2>/dev/null || true
    VLLM_PID=""

    log "Preference data ready: $(wc -l < "$pref_file") pairs"
}

# ---------------------------------------------------------------------------
# Phase 3: Training -- each method with checkpoint resume
# ---------------------------------------------------------------------------

do_sft() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/sft/${model_slug}"
    mkdir -p "$out_dir"

    # Find latest checkpoint for resume
    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    if [[ -n "$ckpt" ]]; then
        log "Resuming SFT from checkpoint: $ckpt"
        resume_arg="--resume-from-checkpoint $ckpt"
    fi

    log_section "SFT: $model_slug"
    cd "$REPO_DIR"

    torchrun \
        --nproc_per_node=$N_GPU \
        --master_port 29500 \
        experiments/finetuning/train_sft.py \
        --base-model            "$model_id" \
        --use-4bit \
        --lora-rank             64 \
        --lora-alpha            128 \
        --lora-dropout          0.05 \
        --lora-init             default \
        --curriculum            joint \
        --learning-rate         2e-5 \
        --num-epochs            3 \
        --per-device-batch-size "$PER_DEVICE_BS" \
        --grad-accum-steps      "$GRAD_ACCUM" \
        --warmup-steps          100 \
        --max-seq-length        1024 \
        --data-dir              "$DATA_DIR" \
        --output-dir            "$out_dir" \
        --logging-dir           "${out_dir}/logs" \
        --save-steps            "$SAVE_STEPS" \
        --eval-steps            "$EVAL_STEPS" \
        --seed                  42 \
        --deepspeed-config      "$DS_CONFIG" \
        ${resume_arg} \
        2>&1 | tee -a "${out_dir}/train.log"
}

do_dpo() {
    local model_slug="$1"
    local variant="$2"   # standard or margin
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/dpo_${variant}/${model_slug}"
    mkdir -p "$out_dir"

    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && resume_arg="--resume-from-checkpoint $ckpt" && log "Resuming DPO from: $ckpt"

    log_section "DPO ($variant): $model_slug"
    cd "$REPO_DIR"

    torchrun \
        --nproc_per_node=$N_GPU \
        --master_port 29501 \
        experiments/finetuning/train_dpo.py \
        --base-model            "$model_id" \
        --use-4bit \
        --lora-rank             64 \
        --lora-alpha            128 \
        --lora-dropout          0.05 \
        --lora-init             default \
        --dpo-variant           "$variant" \
        --beta                  0.1 \
        --margin-delta          2.0 \
        --curriculum            joint \
        --learning-rate         5e-6 \
        --num-epochs            3 \
        --per-device-batch-size "$PER_DEVICE_BS" \
        --grad-accum-steps      "$GRAD_ACCUM" \
        --warmup-steps          100 \
        --max-length            1024 \
        --max-prompt-length     512 \
        --data-dir              "$DATA_DIR" \
        --output-dir            "$out_dir" \
        --logging-dir           "${out_dir}/logs" \
        --save-steps            "$SAVE_STEPS" \
        --eval-steps            "$EVAL_STEPS" \
        --seed                  42 \
        --deepspeed-config      "$DS_CONFIG" \
        ${resume_arg} \
        2>&1 | tee -a "${out_dir}/train.log"
}

do_grpo() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/grpo/${model_slug}"
    mkdir -p "$out_dir"

    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && resume_arg="--resume-from-checkpoint $ckpt" && log "Resuming GRPO from: $ckpt"

    log_section "GRPO: $model_slug"
    cd "$REPO_DIR"

    torchrun \
        --nproc_per_node=$N_GPU \
        --master_port 29502 \
        experiments/finetuning/train_grpo.py \
        --base-model            "$model_id" \
        --use-4bit \
        --lora-rank             64 \
        --lora-alpha            128 \
        --lora-dropout          0.05 \
        --lora-init             default \
        --num-generations       8 \
        --max-completion-length 512 \
        --learning-rate         5e-7 \
        --num-epochs            3 \
        --per-device-batch-size "$PER_DEVICE_BS" \
        --grad-accum-steps      4 \
        --warmup-steps          50 \
        --beta                  0.04 \
        --temperature           0.7 \
        --epsilon               0.2 \
        --scale-rewards         batch \
        --use-vllm \
        --modality              M4 \
        --strategy              direct \
        --curriculum            joint \
        --instances-dir         "$INSTANCES_DIR" \
        --splits-file           "$SPLITS_FILE" \
        --output-dir            "$out_dir" \
        --logging-dir           "${out_dir}/logs" \
        --save-steps            "$SAVE_STEPS" \
        --seed                  42 \
        --deepspeed-config      "$DS_CONFIG" \
        ${resume_arg} \
        2>&1 | tee -a "${out_dir}/train.log"
}

do_rlhf() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/rlhf_vitl/${model_slug}"
    mkdir -p "$out_dir"

    # PPO does not support standard resume_from_checkpoint;
    # we pass the checkpoint dir and the trainer loads from it if present
    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && log "RLHF/VITL: latest checkpoint found at $ckpt (PPO will attempt resume)"

    log_section "RLHF/VITL: $model_slug"
    cd "$REPO_DIR"

    CUDA_VISIBLE_DEVICES=0 python \
        experiments/finetuning/train_rlhf_vitl.py \
        --mode                vitl \
        --base-model          "$model_id" \
        --use-4bit \
        --lora-rank           64 \
        --lora-alpha          128 \
        --lora-dropout        0.05 \
        --lora-init           default \
        --kl-coeff            0.05 \
        --ppo-epochs          3 \
        --batch-size          16 \
        --mini-batch-size     8 \
        --learning-rate       1e-6 \
        --max-new-tokens      512 \
        --curriculum          joint \
        --data-dir            "$DATA_DIR" \
        --instances-dir       "$INSTANCES_DIR" \
        --output-dir          "$out_dir" \
        --seed                42 \
        2>&1 | tee -a "${out_dir}/train.log"
}

# ---------------------------------------------------------------------------
# Phase 4: Evaluation
# ---------------------------------------------------------------------------

do_eval() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local eval_dir="${RESULTS_BASE}/eval/${model_slug}"
    mkdir -p "$eval_dir"

    log_section "Evaluation: $model_slug"
    cd "$REPO_DIR"

    for method_dir in \
        "${RESULTS_BASE}/sft/${model_slug}" \
        "${RESULTS_BASE}/dpo_standard/${model_slug}" \
        "${RESULTS_BASE}/dpo_margin/${model_slug}" \
        "${RESULTS_BASE}/grpo/${model_slug}" \
        "${RESULTS_BASE}/rlhf_vitl/${model_slug}"; do

        [[ -d "$method_dir" ]] || continue
        local method_name
        method_name=$(basename "$(dirname "$method_dir")")

        python experiments/finetuning/evaluate_finetuned.py \
            --checkpoint      "$method_dir" \
            --base-model      "$model_id" \
            --use-4bit \
            --split           test \
            --instances-dir   "$INSTANCES_DIR" \
            --splits-file     "$SPLITS_FILE" \
            --data-dir        "$DATA_DIR" \
            --modalities      M4 M2 \
            --strategies      direct cot \
            --results-dir     "$eval_dir" \
            --run-label       "${method_name}_${model_slug}" \
            2>&1 | tee "${eval_dir}/${method_name}.log"
    done
}

# ---------------------------------------------------------------------------
# Main -- resumes from last completed step on every boot
# ---------------------------------------------------------------------------

main() {
    state_init

    log_section "DeFAb Spot-Resilient Fine-Tuning"
    log "State file : $STATE_FILE"
    log "Results    : $RESULTS_BASE"
    log "Repo       : $REPO_DIR"
    log "Booting at : $(date)"

    # Show what is done so far
    log "Completed steps so far:"
    python3 -c "
import json
state = json.load(open('${STATE_FILE}'))
for s in state['completed']:
    print(f'  [done] {s}')
if not state['completed']:
    print('  (none yet -- fresh start)')
"

    echo ""

    # Phase 0 + 1: one-time setup and data download
    run_step "setup"    do_setup
    run_step "download" do_download

    # Per-model loop
    for model_slug in "${MODELS[@]}"; do

        # Phase 2: data prep (per model)
        run_step "data_${model_slug}" do_prepare_data "$model_slug"

        # Phase 3: training (each method tracked separately)
        run_step "sft_${model_slug}"          do_sft    "$model_slug"
        run_step "dpo_standard_${model_slug}" do_dpo    "$model_slug" standard
        run_step "dpo_margin_${model_slug}"   do_dpo    "$model_slug" margin
        run_step "grpo_${model_slug}"         do_grpo   "$model_slug"
        run_step "rlhf_vitl_${model_slug}"    do_rlhf   "$model_slug"

        # Phase 4: evaluation
        run_step "eval_${model_slug}"         do_eval   "$model_slug"
    done

    log_section "ALL STEPS COMPLETE"
    state_mark_done "all_done"
    log "Final state saved to $STATE_FILE"
}

main "$@"
