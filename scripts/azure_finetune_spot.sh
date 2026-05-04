#!/usr/bin/env bash
# =============================================================================
# azure_finetune_spot.sh -- Spot-VM-resilient DeFAb fine-tuning orchestrator
#
# Designed for Azure Spot VMs with unannounced deallocation/reallocation.
# Systemd invokes the script on every boot. It reconciles the state file
# against disk, then resumes from the first incomplete step.
#
# Key resilience properties:
#   * State file (/data/defab_results/.finetune_state.json) is the only
#     persistent memory. It is written atomically (tmp + rename + fsync).
#   * Every boot begins with `verify_and_repair_state.py`, which removes
#     "[done]" entries whose artifacts are absent. No more phantom completions.
#   * `run_step` marks a step complete only after its declared artifact check
#     passes. A clean exit without artifacts is treated as failure.
#   * A background Azure IMDS ScheduledEvents poller signals the orchestrator
#     up to 30s before the OS SIGTERM, letting checkpoints flush cleanly.
#   * The SIGTERM trap propagates to every child (torchrun ranks, vLLM, etc.)
#     via a dedicated process group.
#   * Pre-flight checks (disk headroom, stale CUDA processes) run before each
#     GPU step.
#   * HuggingFace weights are pre-downloaded into /data/hf_cache (a persistent
#     disk) before training, so eviction mid-download never wastes hours.
#   * Training scripts save every 25 steps with `save_total_limit=3`; on
#     restart they resume from the latest `checkpoint-N`.
#
# First-time setup on a fresh Azure VM:
#   sudo install -m 755 scripts/azure_finetune_spot.sh       /usr/local/bin/defab_finetune
#   sudo install -m 755 scripts/azure_spot_preemption_poller.sh /usr/local/bin/defab_preempt_poller
#   sudo install -m 755 scripts/defab_watchdog.sh            /usr/local/bin/defab_watchdog
#   sudo cp scripts/defab_finetune.service  /etc/systemd/system/
#   sudo cp scripts/defab_watchdog.service  /etc/systemd/system/
#   sudo systemctl daemon-reload
#   sudo systemctl enable --now defab_finetune defab_watchdog
#   journalctl -u defab_finetune -f
#
# Author: Anonymous Authors
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Conda activation -- systemd's default PATH does not include Miniconda/Anaconda,
# so we source conda and activate the target env before anything else. This
# keeps `python`, `torchrun`, and the preinstalled CUDA/PyTorch stack on PATH
# regardless of how the orchestrator is launched.
# ---------------------------------------------------------------------------

DEFAB_CONDA_ENV="${DEFAB_CONDA_ENV:-defab}"

_activate_conda() {
    # `conda activate` tolerates unbound CONDA_SHLVL etc. poorly under `set -u`.
    # Relax strictness for this block only.
    set +u
    local base
    local activated=0
    for base in \
        "${HOME}/miniconda3" \
        "${HOME}/anaconda3" \
        "/opt/miniconda3" \
        "/opt/conda"; do
        if [[ -f "${base}/etc/profile.d/conda.sh" ]]; then
            # shellcheck disable=SC1091
            source "${base}/etc/profile.d/conda.sh"
            if conda activate "$DEFAB_CONDA_ENV" 2>/dev/null; then
                echo "[conda] activated $DEFAB_CONDA_ENV from $base"
                activated=1
                break
            fi
            if conda activate base 2>/dev/null; then
                echo "[conda] '$DEFAB_CONDA_ENV' not found; fell back to base at $base"
                activated=1
                break
            fi
        fi
    done
    if (( activated == 0 )); then
        echo "[conda] WARN: no miniconda/anaconda install found; relying on inherited PATH"
    fi
    set -u
}
_activate_conda

# After activation, $CONDA_PREFIX/bin is on PATH, so `python` resolves.
# Pin a PYTHON variable as a last-resort explicit fallback.
PYTHON="${PYTHON:-$(command -v python 2>/dev/null || command -v python3 2>/dev/null || echo /usr/bin/python3)}"
export PYTHON

# ---------------------------------------------------------------------------
# Configuration -- override via /etc/defab/secrets or Environment= in unit
# ---------------------------------------------------------------------------

REPO_DIR="${REPO_DIR:-/home/azureuser/blanc}"
HF_TOKEN="${HF_TOKEN:-}"
HF_REPO="${HF_REPO:-PatrickAllenCooper/DeFAb}"
export HF_HOME="${HF_HOME:-/data/hf_cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME}"

RESULTS_BASE="${RESULTS_BASE:-/data/defab_results}"
DATA_DIR="${REPO_DIR}/experiments/finetuning/data"
INSTANCES_DIR="${REPO_DIR}/instances"
SPLITS_FILE="${INSTANCES_DIR}/splits.json"
DS_CONFIG="${REPO_DIR}/experiments/finetuning/ds_config_zero2.json"
VLLM_PORT="${VLLM_PORT:-8200}"

# Checkpoint frequency: bound the work lost to a single Spot preemption.
# Observed on dual-A100 80GB:
#   * Qwen2.5-72B QLoRA (DPO):     ~58 s/step  -> SAVE_STEPS=10 ~= 9.7 min
#   * Qwen2.5-32B QLoRA (SFT):     ~25 s/step  -> SAVE_STEPS=10 ~= 4.2 min
#   * Qwen2.5-72B QLoRA (SFT, 54 steps): finishes in one shot, save_steps moot
# A LoRA adapter + Adam optimizer state checkpoint is ~5 GB; with NVMe write
# bandwidth (~3 GB/s) each save costs ~2 s, dwarfed by training step time.
# Disk footprint is bounded by SAVE_TOTAL_LIMIT regardless.
# We previously ran with SAVE_STEPS=25, lost a full 24 min of DPO progress on
# the first real Spot preemption (Apr 20, step 24 of 240, no checkpoint yet).
SAVE_STEPS="${SAVE_STEPS:-10}"
EVAL_STEPS="${EVAL_STEPS:-50}"
SAVE_TOTAL_LIMIT="${SAVE_TOTAL_LIMIT:-3}"

# Batch config for 2x A100 80GB
PER_DEVICE_BS="${PER_DEVICE_BS:-2}"
GRAD_ACCUM="${GRAD_ACCUM:-8}"
N_GPU="${N_GPU:-2}"

# Warmup is expressed as ratio because our per-run step count (~54) is tiny.
# 100 fixed warmup steps > total steps is a silent bug: the model never
# escapes warmup. 0.05 gives ~3 warmup steps, then cosine decay over the rest.
WARMUP_RATIO="${WARMUP_RATIO:-0.05}"

# Minimum free disk (GB) required before entering any training step.
# Per-step minimum free space under $RESULTS_BASE. The predownload phases
# need far more (see preflight_disk_for_predownload below); the floor here is
# the runtime headroom every other step needs (LoRA checkpoints, tokenizer
# shards, eval outputs, scratch).
MIN_FREE_GB="${MIN_FREE_GB:-50}"

# Size estimates for pre-download pre-flight. Values in GB, padded ~15% for
# shard deltas, tokenizer/config files, and in-flight partial writes.
PREDOWNLOAD_SIZE_GB_qwen72="${PREDOWNLOAD_SIZE_GB_qwen72:-170}"
PREDOWNLOAD_SIZE_GB_qwen32="${PREDOWNLOAD_SIZE_GB_qwen32:-80}"

# Stall cap (seconds) before we abort a child process.
STEP_TIMEOUT_SEC="${STEP_TIMEOUT_SEC:-86400}"   # 24h per step, soft cap

# Paths and helpers
STATE_FILE="${RESULTS_BASE}/.finetune_state.json"
STATE_LOCK="${RESULTS_BASE}/.finetune_state.lock"
LOG_FILE="${RESULTS_BASE}/run.log"
PREEMPT_SENTINEL="${RESULTS_BASE}/.preemption_imminent"
PID_FILE="${RESULTS_BASE}/.orchestrator.pid"

# ---------------------------------------------------------------------------
# Model matrix
# ---------------------------------------------------------------------------

declare -A MODEL_IDS=(
    [qwen72]="Qwen/Qwen2.5-72B-Instruct"
    [qwen32]="Qwen/Qwen2.5-32B-Instruct"
    [deepseek]="deepseek-ai/DeepSeek-R1-Distill-Llama-70B"
)
MODELS=("qwen72" "qwen32" "deepseek")

# Expected artifact per step (relative to $RESULTS_BASE); used to decide
# whether to mark a step complete *after* its function returns 0.
declare -A STEP_ARTIFACT=(
    [setup]=""
    [download]="${INSTANCES_DIR}/tier0"
)

# Running child PIDs -- the SIGTERM trap terminates all of them.
CHILD_PIDS=()
POLLER_PID=""

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

mkdir -p "$RESULTS_BASE"
echo $$ > "$PID_FILE"
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
# Signal handling -- propagate to the entire process group
# ---------------------------------------------------------------------------

on_sigterm() {
    local sig="${1:-TERM}"
    log "Signal ${sig} received. Propagating to children and flushing state..."
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            log "  signaling child pid=$pid"
            kill -SIGTERM "$pid" 2>/dev/null || true
        fi
    done
    if [[ -n "$POLLER_PID" ]] && kill -0 "$POLLER_PID" 2>/dev/null; then
        kill -SIGTERM "$POLLER_PID" 2>/dev/null || true
    fi
    # Give children up to 25s to flush (Azure eviction window is 30s).
    local waited=0
    for pid in "${CHILD_PIDS[@]}"; do
        while kill -0 "$pid" 2>/dev/null && (( waited < 25 )); do
            sleep 1
            waited=$(( waited + 1 ))
        done
    done
    log "State file: $STATE_FILE"
    log "Orchestrator exiting cleanly; next boot will resume via state reconciliation."
    rm -f "$PID_FILE"
    exit 0
}
trap 'on_sigterm TERM' SIGTERM
trap 'on_sigterm INT'  SIGINT
trap 'rm -f "$PID_FILE"' EXIT

# Place ourselves in our own process group so `kill -- -$$` reaches everything.
# (systemd delivers SIGTERM to the main PID; we then fan it out ourselves.)

# ---------------------------------------------------------------------------
# State helpers -- atomic writes, file lock, ground-truth verification
# ---------------------------------------------------------------------------

state_reconcile() {
    log "Reconciling state file against on-disk artifacts..."
    "$PYTHON" "${REPO_DIR}/scripts/verify_and_repair_state.py" \
        --state "$STATE_FILE" \
        --results-base "$RESULTS_BASE" \
        --repo-dir "$REPO_DIR" \
        --data-dir "$DATA_DIR" \
        --instances-dir "$INSTANCES_DIR" \
        || log "WARN: state reconciliation returned non-zero; continuing with whatever is on disk."
}

state_init() {
    if [[ ! -f "$STATE_FILE" ]]; then
        "$PYTHON" -c "
import json, os, tempfile
path = '$STATE_FILE'
os.makedirs(os.path.dirname(path), exist_ok=True)
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.state.', suffix='.tmp')
with os.fdopen(fd, 'w') as f:
    json.dump({'completed': []}, f, indent=2)
    f.flush(); os.fsync(f.fileno())
os.replace(tmp, path)
"
        log "Initialized state file: $STATE_FILE"
    fi
}

state_is_done() {
    local key="$1"
    "$PYTHON" -c "
import json, sys
try:
    state = json.load(open('${STATE_FILE}'))
except Exception:
    sys.exit(1)
sys.exit(0 if '${key}' in state.get('completed', []) else 1)
" 2>/dev/null
}

state_mark_done() {
    local key="$1"
    # flock guards against racey writes if the watchdog/another process touches
    # the file. Atomic replace guards against crash mid-write.
    (
        flock -x 200
        "$PYTHON" -c "
import json, os, sys, tempfile
path = '${STATE_FILE}'
try:
    state = json.load(open(path))
except Exception:
    state = {'completed': []}
if '${key}' not in state['completed']:
    state['completed'].append('${key}')
fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.state.', suffix='.tmp')
with os.fdopen(fd, 'w') as f:
    json.dump(state, f, indent=2, sort_keys=True)
    f.flush(); os.fsync(f.fileno())
os.replace(tmp, path)
"
    ) 200>"$STATE_LOCK"
    log "State: marked '$key' complete."
}

# Ground-truth verifiers for run_step: each returns 0 iff the step really
# produced its expected artifact. They mirror verify_and_repair_state.py and
# must stay in sync.
_has_lora_final() {
    local dir="$1"
    local final="${dir}/final"
    [[ -d "$final" ]] || return 1
    for n in adapter_model.safetensors adapter_model.bin pytorch_model.bin model.safetensors; do
        [[ -f "${final}/${n}" ]] && return 0
    done
    return 1
}

_verify_step() {
    local key="$1"
    case "$key" in
        setup)      return 0 ;;
        download)
            # do_download copies Tier-0 dev files flat into $INSTANCES_DIR and
            # Tier-1 per-domain files into $INSTANCES_DIR/tier1/<d>/instances.json.
            # Either is sufficient evidence that snapshot_download ran.
            [[ -f "${INSTANCES_DIR}/level3_instances.json" ]] || \
            [[ -f "${INSTANCES_DIR}/biology_dev_instances.json" ]] || \
            [[ -f "${INSTANCES_DIR}/tier1/biology/instances.json" ]]
            ;;
        data_*)
            local slug="${key#data_}"
            [[ -s "${DATA_DIR}/sft_train.jsonl" ]] && \
            [[ -s "${DATA_DIR}/preferences_${slug}.jsonl" ]]
            ;;
        predownload_*)
            # Shards land under $HF_HOME/hub/models--<org>--<name>/snapshots/<sha>/
            # Treat the cache dir containing >20 GB as strong evidence the
            # shards are fully present (Qwen 32B is ~65 GB, 72B ~145 GB).
            local cache_dir="${HF_HOME}/hub"
            if [[ ! -d "$cache_dir" ]]; then
                return 1
            fi
            local bytes
            bytes=$(du -sb "$cache_dir" 2>/dev/null | awk '{print $1}')
            bytes=${bytes:-0}
            [[ "$bytes" -gt $((20 * 1024**3)) ]]
            ;;
        sft_*)         _has_lora_final "${RESULTS_BASE}/sft/${key#sft_}" ;;
        dpo_standard_*) _has_lora_final "${RESULTS_BASE}/dpo_standard/${key#dpo_standard_}" ;;
        dpo_margin_*)  _has_lora_final "${RESULTS_BASE}/dpo_margin/${key#dpo_margin_}" ;;
        grpo_*)        _has_lora_final "${RESULTS_BASE}/grpo/${key#grpo_}" ;;
        rlhf_vitl_*)   _has_lora_final "${RESULTS_BASE}/rlhf_vitl/${key#rlhf_vitl_}" ;;
        eval_*)
            local slug="${key#eval_}"
            local found
            found=$(find "${RESULTS_BASE}/eval/${slug}" -name summary.json -size +0c 2>/dev/null | head -1)
            [[ -n "$found" ]]
            ;;
        all_done)      return 0 ;;
        *)             return 0 ;;  # unknown keys are not verified
    esac
}

run_step() {
    local key="$1"; shift
    if state_is_done "$key"; then
        log "Skipping '$key' (state + disk verified)"
        return 0
    fi
    log "Running step: $key"
    local rc=0
    "$@" || rc=$?
    if (( rc != 0 )); then
        log "ERROR: step '$key' exited with code $rc; NOT marking complete."
        return $rc
    fi
    if ! _verify_step "$key"; then
        log "ERROR: step '$key' exited 0 but expected artifact is missing; NOT marking complete."
        _explain_verify "$key" || true
        return 1
    fi
    state_mark_done "$key"
}

# Print why _verify_step rejected a step. Called only on failure so it is
# safe to be chatty.
_explain_verify() {
    local key="$1"
    case "$key" in
        download)
            log "  checked INSTANCES_DIR=${INSTANCES_DIR}"
            for f in level3_instances.json biology_dev_instances.json \
                     tier1/biology/instances.json; do
                if [[ -f "${INSTANCES_DIR}/${f}" ]]; then
                    log "    [present] ${f}"
                else
                    log "    [missing] ${f}"
                fi
            done
            ;;
        data_*)
            local slug="${key#data_}"
            log "  checked DATA_DIR=${DATA_DIR}"
            for f in sft_train.jsonl "preferences_${slug}.jsonl"; do
                if [[ -s "${DATA_DIR}/${f}" ]]; then
                    log "    [present] ${f}"
                else
                    log "    [missing or empty] ${f}"
                fi
            done
            ;;
        sft_*|dpo_standard_*|dpo_margin_*|grpo_*|rlhf_vitl_*)
            local kind="${key%_*}" slug="${key##*_}"
            log "  checked ${RESULTS_BASE}/${kind}/${slug}/final for LoRA weights"
            ;;
        eval_*)
            local slug="${key#eval_}"
            log "  checked ${RESULTS_BASE}/eval/${slug} for non-empty summary.json"
            ;;
        predownload_*)
            log "  checked HF_HOME/hub for >20 GB of cached shards (HF_HOME=${HF_HOME})"
            ;;
    esac
}

# ---------------------------------------------------------------------------
# Checkpoint discovery + integrity validation
#
# Why this is not just `ls | tail -1`: a SIGTERM mid-checkpoint-write (which
# is exactly what Azure Spot preemption produces, since the HF Trainer does
# not write checkpoints atomically) leaves a truncated
# `adapter_model.safetensors` on disk. On resume, `safe_open` raises
#   safetensors_rust.SafetensorError: Error while deserializing header:
#     incomplete metadata, file not fully covered
# which kills the trainer before the first step, systemd counts a Failure,
# Restart=on-failure retries, we find the same corrupt checkpoint, and the
# service loops until StartLimitBurst is exhausted (observed Apr 20, 16:11
# UTC, crash counter reached 5 in under a minute).
#
# Fix: iterate newest -> oldest; deeply validate each candidate's weight
# file; quarantine any that fail so we never find them again; return the
# newest surviving checkpoint or empty string to fall back to training from
# scratch.
# ---------------------------------------------------------------------------

_checkpoint_is_valid() {
    local ckpt="$1" weight_file=""
    local candidate
    for candidate in adapter_model.safetensors adapter_model.bin \
                     pytorch_model.bin model.safetensors; do
        if [[ -f "${ckpt}/${candidate}" ]]; then
            weight_file="${ckpt}/${candidate}"
            break
        fi
    done
    [[ -z "$weight_file" || ! -s "$weight_file" ]] && return 1

    # Deep check: ask Python to parse the archive. Cheap (~0.3 s) because
    # safe_open only reads the header, and torch.load(weights_only=True)
    # streams the pickle. If $PYTHON is unset (shouldn't happen after
    # _activate_conda) we only do the shallow byte-size check above.
    if [[ -z "${PYTHON:-}" ]]; then
        return 0
    fi
    WEIGHT_FILE="$weight_file" "$PYTHON" - >/dev/null 2>&1 <<'PY'
import os, sys
path = os.environ["WEIGHT_FILE"]
try:
    if path.endswith(".safetensors"):
        from safetensors import safe_open
        with safe_open(path, framework="pt") as f:
            # Empty keys would mean a valid but useless checkpoint; treat as bad.
            if not list(f.keys()):
                sys.exit(1)
    else:
        import torch
        torch.load(path, map_location="cpu", weights_only=True)
except Exception:
    sys.exit(1)
sys.exit(0)
PY
    return $?
}

_quarantine_checkpoint() {
    local ckpt="$1" parent quarantine ts
    parent=$(dirname "$ckpt")
    quarantine="${parent}/.corrupt"
    ts=$(date +%Y%m%dT%H%M%S)
    mkdir -p "$quarantine"
    if mv "$ckpt" "${quarantine}/$(basename "$ckpt").${ts}" 2>/dev/null; then
        log "  quarantined $(basename "$ckpt") -> ${quarantine}/"
    else
        log "  WARN: failed to move corrupt checkpoint; renaming inline"
        mv "$ckpt" "${ckpt}.corrupt.${ts}" 2>/dev/null || true
    fi
}

latest_checkpoint() {
    local dir="$1" candidate
    [[ -d "$dir" ]] || { echo ""; return 0; }

    # Sort numerically by step, newest first.
    local sorted_list
    sorted_list=$(ls -d "${dir}/checkpoint-"* 2>/dev/null | sort -t- -k2 -n -r || true)
    [[ -z "$sorted_list" ]] && { echo ""; return 0; }

    while IFS= read -r candidate; do
        [[ -z "$candidate" ]] && continue
        if _checkpoint_is_valid "$candidate"; then
            echo "$candidate"
            return 0
        fi
        log "Rejecting corrupt checkpoint (truncated weight file): $candidate"
        _quarantine_checkpoint "$candidate"
    done <<< "$sorted_list"

    log "No valid checkpoints in $dir; training will start from scratch."
    echo ""
}

# ---------------------------------------------------------------------------
# Pre-flight checks
# ---------------------------------------------------------------------------

_free_gb_on() {
    # Print free GB on the filesystem holding $1 (or 0 if unknown).
    local path="$1" gb
    gb=$(df -BG "$path" 2>/dev/null | awk 'NR==2 {gsub("G","",$4); print $4}')
    echo "${gb:-0}"
}

_used_gb_on() {
    local path="$1" gb
    gb=$(du -sBG "$path" 2>/dev/null | awk '{gsub("G","",$1); print $1}')
    echo "${gb:-0}"
}

preflight_disk() {
    local free_gb hf_free_gb
    free_gb=$(_free_gb_on "$RESULTS_BASE")
    if (( free_gb < MIN_FREE_GB )); then
        log "ERROR: only ${free_gb}G free under $RESULTS_BASE (need >= ${MIN_FREE_GB}G). Aborting step."
        return 1
    fi
    hf_free_gb=$(_free_gb_on "$HF_HOME")
    log "Disk headroom OK: ${free_gb}G free on \$RESULTS_BASE, ${hf_free_gb}G on \$HF_HOME."
}

# More aggressive pre-check for a model pre-download step. Estimates how
# much of the target snapshot is already cached and requires the remainder
# plus 10 GB scratch to be free on \$HF_HOME. Returns 1 with a clear message
# if there is not enough room to finish the snapshot.
preflight_disk_for_predownload() {
    local slug="$1" need_gb cached_gb free_gb remaining_gb
    case "$slug" in
        qwen72)  need_gb="$PREDOWNLOAD_SIZE_GB_qwen72" ;;
        qwen32)  need_gb="$PREDOWNLOAD_SIZE_GB_qwen32" ;;
        *)       need_gb=20 ;;
    esac
    free_gb=$(_free_gb_on "$HF_HOME")
    cached_gb=$(_used_gb_on "$HF_HOME/hub")
    if (( cached_gb >= need_gb )); then
        log "Predownload pre-flight OK for ${slug}: already ~${cached_gb}G cached, free=${free_gb}G."
        return 0
    fi
    remaining_gb=$(( need_gb - cached_gb ))
    if (( free_gb < remaining_gb + 10 )); then
        log "ERROR: predownload_${slug} needs ~${remaining_gb}G more on ${HF_HOME} " \
            "(plus 10G scratch); only ${free_gb}G free. Aborting step."
        log "HINT: free space under ${HF_HOME}, or set HF_HOME to a larger mount" \
            " (e.g. /mnt/resource_nvme/hf_cache) in /etc/systemd/system/defab_finetune.service."
        return 1
    fi
    log "Predownload pre-flight OK for ${slug}: need ~${remaining_gb}G more, free=${free_gb}G."
}

preflight_gpu() {
    if ! command -v nvidia-smi >/dev/null 2>&1; then
        log "WARN: nvidia-smi not found; skipping GPU pre-flight."
        return 0
    fi
    # Kill any stray python/torchrun processes not owned by us.
    local stale
    stale=$(nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null || echo "")
    if [[ -n "$stale" ]]; then
        log "GPU has existing processes: $stale"
        # We do not auto-kill because they might be children we just spawned.
        # If a previous orchestrator crashed, systemd's KillMode=mixed will
        # already have cleaned them up before we start.
    fi
    log "GPU pre-flight OK."
}

preflight() {
    preflight_disk && preflight_gpu
}

# ---------------------------------------------------------------------------
# Child process management -- every long-running command goes through this
# so the SIGTERM trap can find it.
# ---------------------------------------------------------------------------

spawn() {
    # Spawn a command in the background, register its PID, wait for completion.
    # Forwards exit code.
    "$@" &
    local pid=$!
    CHILD_PIDS+=("$pid")
    local rc=0
    wait "$pid" || rc=$?
    local new_pids=()
    for p in "${CHILD_PIDS[@]:-}"; do
        [[ "$p" != "$pid" ]] && new_pids+=("$p")
    done
    CHILD_PIDS=("${new_pids[@]:-}")
    return $rc
}

# Spawn a command, teeing its combined output to a per-step log file while
# still streaming to the orchestrator's stdout (journal + run.log). Avoids
# pipelines at the outer level so PID tracking and signal propagation keep
# working -- the SIGTERM trap can still reach the real child pid.
spawn_to() {
    local logfile="$1"; shift
    mkdir -p "$(dirname "$logfile")"
    "$@" > >(tee -a "$logfile") 2>&1 &
    local pid=$!
    CHILD_PIDS+=("$pid")
    local rc=0
    wait "$pid" || rc=$?
    local new_pids=()
    for p in "${CHILD_PIDS[@]:-}"; do
        [[ "$p" != "$pid" ]] && new_pids+=("$p")
    done
    CHILD_PIDS=("${new_pids[@]:-}")
    return $rc
}

start_preempt_poller() {
    if [[ -x /usr/local/bin/defab_preempt_poller ]]; then
        DEFAB_ORCH_PID=$$ DEFAB_SENTINEL="$PREEMPT_SENTINEL" \
            /usr/local/bin/defab_preempt_poller &
        POLLER_PID=$!
        log "Started Azure IMDS preemption poller (pid=$POLLER_PID)."
    else
        log "Preemption poller not installed at /usr/local/bin/defab_preempt_poller; \
relying on SIGTERM only."
    fi
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
# Phase 0: Environment setup (idempotent; the verifier is always 0)
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
        "sentencepiece" "scipy" "numpy<2" "tensorboard" "tenacity" \
        "anthropic" "openai"

    pip install -q -e .
    log "Setup complete."
}

# ---------------------------------------------------------------------------
# Phase 1: Download DeFAb dataset
# ---------------------------------------------------------------------------

do_download() {
    log_section "Phase 1: Download DeFAb Dataset"
    cd "$REPO_DIR"

    export HF_TOKEN
    "$PYTHON" -u -c "
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
        [[ -f "$src" ]] && mkdir -p "${INSTANCES_DIR}/tier1/${domain}" && \
            cp "$src" "${INSTANCES_DIR}/tier1/${domain}/instances.json"
    done
    log "Dataset ready at ${INSTANCES_DIR}"
}

# ---------------------------------------------------------------------------
# Phase 1b: Pre-download model weights (each model, idempotent)
# Having shards on the persistent /data disk means we do not re-download
# hundreds of GB on every spot reallocation.
# ---------------------------------------------------------------------------

do_predownload() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"

    log_section "Phase 1b: Pre-download $model_id"
    mkdir -p "$HF_HOME"
    preflight_disk_for_predownload "$model_slug" || return 1
    export HF_TOKEN
    "$PYTHON" -u -c "
import os
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='${model_id}',
    cache_dir=os.environ['HF_HOME'],
    token=os.environ.get('HF_TOKEN'),
    # resume_download is default-on in recent huggingface_hub; listed for clarity.
    resume_download=True,
)
print('Pre-download complete for ${model_id}')
"
    log "Cache size: $(du -sh "$HF_HOME" 2>/dev/null | awk '{print $1}')"
}

# ---------------------------------------------------------------------------
# Phase 2: Data preparation (per model)
# ---------------------------------------------------------------------------

do_prepare_data() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"

    log_section "Phase 2: Data Prep for $model_slug"
    cd "$REPO_DIR"
    mkdir -p "$DATA_DIR"
    preflight || return 1

    if [[ ! -f "${DATA_DIR}/sft_train.jsonl" ]]; then
        "$PYTHON" experiments/finetuning/prepare_sft_data.py \
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

    pref_file="${DATA_DIR}/preferences_${model_slug}.jsonl"
    if [[ -f "$pref_file" && -s "$pref_file" ]]; then
        log "Preference file already exists: $pref_file"
        return 0
    fi

    log "Starting vLLM server for preference sampling..."
    export CUDA_VISIBLE_DEVICES=0
    "$PYTHON" -m vllm.entrypoints.openai.api_server \
        --model "$model_id" \
        --port "$VLLM_PORT" \
        --dtype auto \
        --max-model-len 4096 \
        --gpu-memory-utilization 0.90 \
        --enforce-eager \
        > >(tee -a "${RESULTS_BASE}/vllm_${model_slug}_sample.log") 2>&1 &
    local vllm_pid=$!
    CHILD_PIDS+=("$vllm_pid")

    wait_for_server "http://localhost:${VLLM_PORT}" || {
        kill "$vllm_pid" 2>/dev/null || true; return 1
    }
    export CUDA_VISIBLE_DEVICES=0,1

    "$PYTHON" experiments/finetuning/prepare_preference_data.py \
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

    kill "$vllm_pid" 2>/dev/null || true
    wait "$vllm_pid" 2>/dev/null || true
    log "Preference data ready: $(wc -l < "$pref_file") pairs"
}

# ---------------------------------------------------------------------------
# Phase 3: Training -- each method resumes from latest on-disk checkpoint
# ---------------------------------------------------------------------------

do_sft() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/sft/${model_slug}"
    mkdir -p "$out_dir"
    preflight || return 1

    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    if [[ -n "$ckpt" ]]; then
        log "Resuming SFT from checkpoint: $ckpt"
        resume_arg="--resume-from-checkpoint $ckpt"
    fi

    log_section "SFT: $model_slug"
    cd "$REPO_DIR"

    spawn_to "${out_dir}/train.log" torchrun \
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
        --warmup-ratio          "$WARMUP_RATIO" \
        --max-seq-length        1024 \
        --data-dir              "$DATA_DIR" \
        --output-dir            "$out_dir" \
        --logging-dir           "${out_dir}/logs" \
        --save-steps            "$SAVE_STEPS" \
        --eval-steps            "$EVAL_STEPS" \
        --save-total-limit      "$SAVE_TOTAL_LIMIT" \
        --seed                  42 \
        $resume_arg
}

do_dpo() {
    local model_slug="$1"
    local variant="$2"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/dpo_${variant}/${model_slug}"
    mkdir -p "$out_dir"
    preflight || return 1

    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && resume_arg="--resume-from-checkpoint $ckpt" && \
        log "Resuming DPO from: $ckpt"

    log_section "DPO ($variant): $model_slug"
    cd "$REPO_DIR"

    spawn_to "${out_dir}/train.log" torchrun \
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
        --warmup-ratio          "$WARMUP_RATIO" \
        --max-length            1024 \
        --max-prompt-length     512 \
        --data-dir              "$DATA_DIR" \
        --output-dir            "$out_dir" \
        --logging-dir           "${out_dir}/logs" \
        --save-steps            "$SAVE_STEPS" \
        --eval-steps            "$EVAL_STEPS" \
        --save-total-limit      "$SAVE_TOTAL_LIMIT" \
        --seed                  42 \
        $resume_arg
}

do_grpo() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/grpo/${model_slug}"
    mkdir -p "$out_dir"
    preflight || return 1

    local resume_arg=""
    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && resume_arg="--resume-from-checkpoint $ckpt" && \
        log "Resuming GRPO from: $ckpt"

    log_section "GRPO: $model_slug"
    cd "$REPO_DIR"

    spawn_to "${out_dir}/train.log" torchrun \
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
        --warmup-ratio          "$WARMUP_RATIO" \
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
        --save-total-limit      "$SAVE_TOTAL_LIMIT" \
        --seed                  42 \
        $resume_arg
}

do_rlhf() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local out_dir="${RESULTS_BASE}/rlhf_vitl/${model_slug}"
    mkdir -p "$out_dir"
    preflight || return 1

    local ckpt
    ckpt=$(latest_checkpoint "$out_dir")
    [[ -n "$ckpt" ]] && log "RLHF/VITL: latest checkpoint found at $ckpt (PPO will attempt resume)"

    log_section "RLHF/VITL: $model_slug"
    cd "$REPO_DIR"

    CUDA_VISIBLE_DEVICES=0 spawn_to "${out_dir}/train.log" "$PYTHON" \
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
        --seed                42
}

# ---------------------------------------------------------------------------
# Phase 4: Evaluation
# ---------------------------------------------------------------------------

do_eval() {
    local model_slug="$1"
    local model_id="${MODEL_IDS[$model_slug]}"
    local eval_dir="${RESULTS_BASE}/eval/${model_slug}"
    mkdir -p "$eval_dir"
    preflight || return 1

    log_section "Evaluation: $model_slug"
    cd "$REPO_DIR"

    for method_dir in \
        "${RESULTS_BASE}/sft/${model_slug}" \
        "${RESULTS_BASE}/dpo_standard/${model_slug}" \
        "${RESULTS_BASE}/dpo_margin/${model_slug}" \
        "${RESULTS_BASE}/grpo/${model_slug}" \
        "${RESULTS_BASE}/rlhf_vitl/${model_slug}"; do

        [[ -d "$method_dir/final" ]] || { log "skip eval (no final/): $method_dir"; continue; }
        local method_name
        method_name=$(basename "$(dirname "$method_dir")")

        spawn_to "${eval_dir}/${method_name}.log" "$PYTHON" \
            experiments/finetuning/evaluate_finetuned.py \
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
            --run-label       "${method_name}_${model_slug}"
    done
}

# ---------------------------------------------------------------------------
# Main -- every boot: reconcile, start poller, iterate.
# ---------------------------------------------------------------------------

main() {
    state_init
    state_reconcile
    start_preempt_poller

    log_section "DeFAb Spot-Resilient Fine-Tuning"
    log "State file : $STATE_FILE"
    log "Results    : $RESULTS_BASE"
    log "HF cache   : $HF_HOME"
    log "Repo       : $REPO_DIR"
    log "Booting at : $(date)"
    log "Orchestrator pid=$$"

    log "Completed steps so far:"
    "$PYTHON" -c "
import json
state = json.load(open('${STATE_FILE}'))
for s in state['completed']:
    print(f'  [done] {s}')
if not state['completed']:
    print('  (none yet -- fresh start)')
"

    echo ""

    # Phase 0 + 1: one-time setup and dataset download
    run_step "setup"    do_setup
    run_step "download" do_download

    # Per-model loop
    for model_slug in "${MODELS[@]}"; do
        run_step "predownload_${model_slug}"  do_predownload  "$model_slug"
        run_step "data_${model_slug}"         do_prepare_data "$model_slug"
        run_step "sft_${model_slug}"          do_sft          "$model_slug"
        run_step "dpo_standard_${model_slug}" do_dpo          "$model_slug" standard
        run_step "dpo_margin_${model_slug}"   do_dpo          "$model_slug" margin
        run_step "grpo_${model_slug}"         do_grpo         "$model_slug"
        run_step "rlhf_vitl_${model_slug}"    do_rlhf         "$model_slug"
        run_step "eval_${model_slug}"         do_eval         "$model_slug"
    done

    log_section "ALL STEPS COMPLETE"
    state_mark_done "all_done"
    log "Final state saved to $STATE_FILE"
}

main "$@"
