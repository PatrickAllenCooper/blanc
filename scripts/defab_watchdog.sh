#!/usr/bin/env bash
# =============================================================================
# defab_watchdog.sh -- stall detector for the defab_finetune service
#
# Symptom it targets: the orchestrator is "active (running)" per systemd, but
# the current training step has produced no new log output for N minutes.
# That usually means a hang in tokenizer download, bitsandbytes kernel
# compilation, deadlocked NCCL collective, or a CUDA OOM that failed to
# unwind. Restarting the service gets us past it because our orchestrator
# resumes from the last on-disk checkpoint.
#
# Strategy:
#   - Every $WATCH_INTERVAL seconds, find the most recently modified train.log
#     under $RESULTS_BASE.
#   - If the newest train.log is older than $STALL_SECONDS and the service is
#     active, restart the service (which triggers our SIGTERM handler -> clean
#     stop -> fresh boot -> state reconcile -> resume).
#   - If no train.log exists at all, we are in setup/download and skip.
#
# Defaults are conservative: 15-minute stall threshold, 2-minute poll.
#
# Env vars:
#   RESULTS_BASE     (default /data/defab_results)
#   WATCH_INTERVAL   (default 120)
#   STALL_SECONDS    (default 900)
#   MAX_RESTARTS     (default 6 per boot -- guards against restart loops)
#
# Author: Patrick Cooper
# =============================================================================

set -u

RESULTS_BASE="${RESULTS_BASE:-/data/defab_results}"
WATCH_INTERVAL="${WATCH_INTERVAL:-120}"
STALL_SECONDS="${STALL_SECONDS:-900}"
MAX_RESTARTS="${MAX_RESTARTS:-6}"
SERVICE="${SERVICE:-defab_finetune.service}"
STATE_DIR="${RESULTS_BASE}/.watchdog"

mkdir -p "$STATE_DIR"
RESTART_COUNTER="${STATE_DIR}/restarts_this_boot"

log() { echo "[watchdog $(date '+%Y-%m-%d %H:%M:%S')] $*"; }

# Reset restart counter on this boot.
boot_id="$(cat /proc/sys/kernel/random/boot_id 2>/dev/null || echo unknown)"
if [[ ! -f "${STATE_DIR}/boot_id" ]] || \
   [[ "$(cat "${STATE_DIR}/boot_id")" != "$boot_id" ]]; then
    echo "$boot_id" > "${STATE_DIR}/boot_id"
    echo 0 > "$RESTART_COUNTER"
fi

latest_log_mtime() {
    # Newest train.log anywhere in $RESULTS_BASE; echoes unix timestamp or empty.
    local newest
    newest="$(find "$RESULTS_BASE" -name train.log -type f \
        -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | awk '{print $1}')"
    [[ -z "$newest" ]] && { echo ""; return; }
    printf '%.0f\n' "$newest"
}

service_active() {
    systemctl is-active --quiet "$SERVICE"
}

restart_count() {
    cat "$RESTART_COUNTER" 2>/dev/null || echo 0
}

bump_restart_count() {
    local n
    n="$(restart_count)"
    echo $(( n + 1 )) > "$RESTART_COUNTER"
}

log "started (interval=${WATCH_INTERVAL}s, stall=${STALL_SECONDS}s, max=${MAX_RESTARTS}/boot)"

while true; do
    sleep "$WATCH_INTERVAL"

    if ! service_active; then
        continue
    fi

    mtime="$(latest_log_mtime)"
    if [[ -z "$mtime" ]]; then
        # No train.log yet -- we are in setup/download/eval, no stall signal.
        continue
    fi

    now="$(date +%s)"
    age=$(( now - mtime ))

    if (( age < STALL_SECONDS )); then
        continue
    fi

    count="$(restart_count)"
    if (( count >= MAX_RESTARTS )); then
        log "STALL detected (age=${age}s) but restart cap ${MAX_RESTARTS} reached; \
leaving alone. Manual intervention required."
        continue
    fi

    log "STALL detected: newest train.log is ${age}s old (threshold ${STALL_SECONDS}s). \
Restart ${count}/${MAX_RESTARTS}. Restarting ${SERVICE}."
    bump_restart_count
    systemctl restart "$SERVICE" || log "systemctl restart failed"
    # Give the service time to recover before we evaluate again.
    sleep 120
done
