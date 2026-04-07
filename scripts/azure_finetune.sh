#!/usr/bin/env bash
# =============================================================================
# azure_finetune.sh -- DeFAb fine-tuning orchestrator for Azure dual-A100 VM
#
# Targets: Azure NC_A100_v4 (2x A100 80 GB) or equivalent
#
# Runs all four fine-tuning methods from the paper on all three base models:
#   Methods : SFT, DPO (standard + margin), GRPO, RLHF/VITL
#   Models  : Qwen2.5-72B-AWQ, Qwen2.5-32B-AWQ, DeepSeek-R1-Distill-70B-AWQ
#
# Usage:
#   bash scripts/azure_finetune.sh [--model MODEL] [--method METHOD]
#                                  [--skip-setup] [--skip-data]
#
# Options:
#   --model MODEL   Run only this model slug (qwen72, qwen32, deepseek)
#   --method METHOD Run only this method (sft, dpo, grpo, rlhf)
#   --skip-setup    Skip conda/pip installation (use if env already built)
#   --skip-data     Skip data preparation (use if data already exists)
#
# Author: Patrick Cooper
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
HF_TOKEN="${HF_TOKEN:-}"            # set HF_TOKEN env var for private dataset
HF_REPO="PatrickAllenCooper/DeFAb"

HF_HOME="${HF_HOME:-/tmp/hf_cache}"
RESULTS_BASE="${REPO_DIR}/results/finetune"
DATA_DIR="${REPO_DIR}/experiments/finetuning/data"
INSTANCES_DIR="${REPO_DIR}/instances"
SPLITS_FILE="${INSTANCES_DIR}/splits.json"
DS_CONFIG="${REPO_DIR}/experiments/finetuning/ds_config_zero2.json"
VLLM_PORT="${VLLM_PORT:-8200}"

# Batch size adaptation for 2 GPUs (maintain ~effective batch 32 to keep fast)
PER_DEVICE_BS=2
GRAD_ACCUM=8   # effective batch = 2 GPUs * 2 * 8 = 32

N_GPU=2

MODEL_FILTER=""
METHOD_FILTER=""
DO_SETUP=true
DO_DATA=true

# Parse args
while [[ $# -gt 0 ]]; do
    case "$1" in
        --model)    MODEL_FILTER="$2"; shift 2 ;;
        --method)   METHOD_FILTER="$2"; shift 2 ;;
        --skip-setup) DO_SETUP=false; shift ;;
        --skip-data)  DO_DATA=false; shift ;;
        *) echo "Unknown arg: $1"; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Model matrix
# ---------------------------------------------------------------------------

declare -A MODEL_IDS=(
    [qwen72]="Qwen/Qwen2.5-72B-Instruct-AWQ"
    [qwen32]="Qwen/Qwen2.5-32B-Instruct-AWQ"
    [deepseek]="casperhansen/deepseek-r1-distill-llama-70b-awq"
)
MODELS=("qwen72" "qwen32" "deepseek")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log() { echo "[$(date '+%H:%M:%S')] $*"; }
log_section() {
    echo ""
    echo "============================================================"
    echo "  $*"
    echo "============================================================"
    echo ""
}

run_if() {
    local filter="$1"; local current="$2"; shift 2
    if [[ -z "$filter" || "$filter" == "$current" ]]; then
        "$@"
    else
        log "Skipping $current (filter=$filter)"
    fi
}

wait_for_server() {
    local url="$1"
    log "Waiting for server at $url ..."
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
# Phase 0: Environment setup
# ---------------------------------------------------------------------------

setup_env() {
    log_section "Phase 0: Environment Setup"
    cd "$REPO_DIR"

    log "Installing Python dependencies..."
    pip install -q --upgrade pip
    pip install -q \
        "torch>=2.2.0" \
        "transformers>=4.45.0" \
        "trl>=0.11.0" \
        "peft>=0.12.0" \
        "bitsandbytes>=0.43.0" \
        "deepspeed>=0.15.0" \
        "accelerate>=0.32.0" \
        "datasets>=2.20.0" \
        "huggingface_hub>=0.24.0" \
        "vllm>=0.5.0" \
        "sentencepiece" \
        "scipy" \
        "numpy" \
        "tensorboard"

    log "Installing DeFAb package..."
    pip install -q -e .

    log "Setup complete."
}

# ---------------------------------------------------------------------------
# Phase 1: Download DeFAb dataset from HuggingFace
# ---------------------------------------------------------------------------

download_dataset() {
    log_section "Phase 1: Download DeFAb Dataset"
    cd "$REPO_DIR"

    log "Downloading instances from $HF_REPO ..."
    python -u -c "
from huggingface_hub import snapshot_download
import os

token = os.environ.get('HF_TOKEN') or None
snapshot_download(
    repo_id='${HF_REPO}',
    repo_type='dataset',
    local_dir='${REPO_DIR}/instances_hf',
    allow_patterns=['instances/**'],
    token=token,
)
print('Download complete.')
"

    log "Copying instance files to instances/ ..."
    mkdir -p "${INSTANCES_DIR}/tier0" "${INSTANCES_DIR}/tier1" "${INSTANCES_DIR}/tier2"

    # Tier 0
    for f in biology_dev_instances legal_dev_instances materials_dev_instances level3_instances; do
        src="${REPO_DIR}/instances_hf/instances/tier0/${f}.json"
        dst_name="${f##*/}"
        [[ -f "$src" ]] && cp "$src" "${INSTANCES_DIR}/${dst_name}.json" && log "  Copied ${dst_name}.json"
    done

    # Tier 1
    for domain in biology chemistry everyday legal materials; do
        src="${REPO_DIR}/instances_hf/instances/tier1/${domain}/instances.json"
        [[ -f "$src" ]] && mkdir -p "${INSTANCES_DIR}/tier1/${domain}" && cp "$src" "${INSTANCES_DIR}/tier1/${domain}/instances.json" && log "  Copied tier1/${domain}/instances.json"
    done

    log "Dataset ready at ${INSTANCES_DIR}"
}

# ---------------------------------------------------------------------------
# Phase 2: Prepare training data (SFT + preferences)
# ---------------------------------------------------------------------------

prepare_data() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"

    log_section "Phase 2: Data Preparation for $model_slug"
    cd "$REPO_DIR"

    mkdir -p "$DATA_DIR"

    # --- SFT data (gold demonstrations) ---
    log "Preparing SFT data..."
    python experiments/finetuning/prepare_sft_data.py \
        --instances-dir "$INSTANCES_DIR" \
        --domains biology legal materials \
        --modalities M4 M2 \
        --strategies direct \
        --output-dir "$DATA_DIR" \
        --splits-file "$SPLITS_FILE" \
        --seed 42

    log "SFT data: $(wc -l < ${DATA_DIR}/sft_train.jsonl) train, $(wc -l < ${DATA_DIR}/sft_val.jsonl) val examples"

    # --- Preference data (sampled responses + verifier scoring) ---
    pref_file="${DATA_DIR}/preferences_${model_slug}.jsonl"
    if [[ -f "$pref_file" ]]; then
        log "Preference file already exists: $pref_file (skipping sampling)"
        return 0
    fi

    log "Starting vLLM server on GPU 0 for response sampling..."
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

    wait_for_server "http://localhost:${VLLM_PORT}" || { kill $VLLM_PID 2>/dev/null; exit 1; }
    export CUDA_VISIBLE_DEVICES=0,1  # restore

    log "Sampling 16 responses per instance..."
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

    log "Stopping vLLM server..."
    kill $VLLM_PID 2>/dev/null || true
    wait $VLLM_PID 2>/dev/null || true
    unset VLLM_PID

    pref_count=$(wc -l < "$pref_file" 2>/dev/null || echo 0)
    log "Preference data: $pref_count pairs in $pref_file"
}

# ---------------------------------------------------------------------------
# Phase 3A: Supervised Fine-Tuning
# ---------------------------------------------------------------------------

run_sft() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/sft/${model_slug}"
    mkdir -p "$out_dir"

    log_section "SFT: $model_slug"
    cd "$REPO_DIR"

    torchrun \
        --nproc_per_node=$N_GPU \
        --master_port 29500 \
        experiments/finetuning/train_sft.py \
        --base-model          "$model_id" \
        --use-4bit \
        --lora-rank           64 \
        --lora-alpha          128 \
        --lora-dropout        0.05 \
        --lora-init           default \
        --curriculum          joint \
        --learning-rate       2e-5 \
        --num-epochs          3 \
        --per-device-batch-size "$PER_DEVICE_BS" \
        --grad-accum-steps    "$GRAD_ACCUM" \
        --warmup-steps        100 \
        --max-seq-length      1024 \
        --data-dir            "$DATA_DIR" \
        --output-dir          "$out_dir" \
        --logging-dir         "${out_dir}/logs" \
        --save-steps          200 \
        --eval-steps          200 \
        --seed                42 \
        --deepspeed-config    "$DS_CONFIG" \
        2>&1 | tee "${out_dir}/train.log"

    log "SFT complete: $out_dir"
}

# ---------------------------------------------------------------------------
# Phase 3B: DPO (standard + margin-weighted)
# ---------------------------------------------------------------------------

run_dpo() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    cd "$REPO_DIR"

    for variant in standard margin; do
        local out_dir="${RESULTS_BASE}/dpo_${variant}/${model_slug}"
        mkdir -p "$out_dir"

        log_section "DPO ($variant): $model_slug"

        torchrun \
            --nproc_per_node=$N_GPU \
            --master_port 29501 \
            experiments/finetuning/train_dpo.py \
            --base-model          "$model_id" \
            --use-4bit \
            --lora-rank           64 \
            --lora-alpha          128 \
            --lora-dropout        0.05 \
            --lora-init           default \
            --dpo-variant         "$variant" \
            --beta                0.1 \
            --margin-delta        2.0 \
            --curriculum          joint \
            --learning-rate       5e-6 \
            --num-epochs          3 \
            --per-device-batch-size "$PER_DEVICE_BS" \
            --grad-accum-steps    "$GRAD_ACCUM" \
            --warmup-steps        100 \
            --max-length          1024 \
            --max-prompt-length   512 \
            --data-dir            "$DATA_DIR" \
            --output-dir          "$out_dir" \
            --logging-dir         "${out_dir}/logs" \
            --save-steps          200 \
            --eval-steps          200 \
            --seed                42 \
            --deepspeed-config    "$DS_CONFIG" \
            2>&1 | tee "${out_dir}/train.log"

        log "DPO ($variant) complete: $out_dir"
    done
}

# ---------------------------------------------------------------------------
# Phase 3C: GRPO (verifier reward, no preference data needed)
# ---------------------------------------------------------------------------

run_grpo() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/grpo/${model_slug}"
    mkdir -p "$out_dir"

    log_section "GRPO: $model_slug"
    cd "$REPO_DIR"

    # GRPO with --use-vllm: GPU 0 serves vLLM, GPU 1 trains.
    # torchrun handles multi-GPU policy update; vLLM is spawned internally.
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
        --save-steps            100 \
        --seed                  42 \
        --deepspeed-config      "$DS_CONFIG" \
        2>&1 | tee "${out_dir}/train.log"

    log "GRPO complete: $out_dir"
}

# ---------------------------------------------------------------------------
# Phase 3D: RLHF / VITL (PPO with exact verifier)
# ---------------------------------------------------------------------------

run_rlhf() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/rlhf_vitl/${model_slug}"
    mkdir -p "$out_dir"

    log_section "RLHF/VITL: $model_slug"
    cd "$REPO_DIR"

    # PPOTrainer does not support multi-GPU / DeepSpeed in current TRL.
    # Runs on GPU 0 only with 4-bit to fit in 80GB.
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
        2>&1 | tee "${out_dir}/train.log"

    log "RLHF/VITL complete: $out_dir"
}

# ---------------------------------------------------------------------------
# Phase 4: Evaluation
# ---------------------------------------------------------------------------

run_eval() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    cd "$REPO_DIR"

    log_section "Phase 4: Evaluation for $model_slug"

    local eval_dir="${RESULTS_BASE}/eval/${model_slug}"
    mkdir -p "$eval_dir"

    for method_dir in \
        "${RESULTS_BASE}/sft/${model_slug}" \
        "${RESULTS_BASE}/dpo_standard/${model_slug}" \
        "${RESULTS_BASE}/dpo_margin/${model_slug}" \
        "${RESULTS_BASE}/grpo/${model_slug}" \
        "${RESULTS_BASE}/rlhf_vitl/${model_slug}"; do

        [[ -d "$method_dir" ]] || continue
        local method_name
        method_name=$(basename "$(dirname "$method_dir")")

        log "Evaluating $method_name/$model_slug ..."
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

    log "Evaluation complete: $eval_dir"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    log_section "DeFAb Fine-Tuning on Azure Dual-A100"
    log "Repo    : $REPO_DIR"
    log "Results : $RESULTS_BASE"
    log "GPUs    : $N_GPU"
    log "HF repo : $HF_REPO"
    [[ -n "$MODEL_FILTER" ]] && log "Model filter : $MODEL_FILTER"
    [[ -n "$METHOD_FILTER" ]] && log "Method filter: $METHOD_FILTER"

    mkdir -p "$RESULTS_BASE" "$DATA_DIR" "$INSTANCES_DIR"

    # Phase 0: Setup
    if $DO_SETUP; then
        setup_env
    fi

    # Phase 1: Download dataset
    if $DO_DATA; then
        download_dataset
    fi

    # Main loop over models
    for model_slug in "${MODELS[@]}"; do
        if [[ -n "$MODEL_FILTER" && "$MODEL_FILTER" != "$model_slug" ]]; then
            continue
        fi

        model_id="${MODEL_IDS[$model_slug]}"
        log_section "MODEL: $model_slug ($model_id)"

        # Phase 2: Data prep (per-model because preferences require the model)
        if $DO_DATA; then
            prepare_data "$model_slug"
        fi

        # Phase 3: Training
        run_if "$METHOD_FILTER" "sft"   run_sft   "$model_slug"
        run_if "$METHOD_FILTER" "dpo"   run_dpo   "$model_slug"
        run_if "$METHOD_FILTER" "grpo"  run_grpo  "$model_slug"
        run_if "$METHOD_FILTER" "rlhf"  run_rlhf  "$model_slug"

        # Phase 4: Evaluation
        run_eval "$model_slug"
    done

    log_section "ALL RUNS COMPLETE"
    log "Results: $RESULTS_BASE"
    find "$RESULTS_BASE/eval" -name "*.json" 2>/dev/null | while read -r f; do
        echo "  $f"
    done
}

main "$@"
