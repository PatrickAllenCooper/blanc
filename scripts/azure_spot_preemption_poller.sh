#!/usr/bin/env bash
# =============================================================================
# azure_spot_preemption_poller.sh -- proactive Azure Spot eviction detector
#
# Azure Spot VMs receive a 30-second notice before eviction. The notice is
# delivered in two ways:
#   1. SIGTERM to PID 1 (handled by systemd, which propagates to the unit).
#   2. A "Preempt" event on the Azure Instance Metadata Service (IMDS) at
#        http://169.254.169.254/metadata/scheduledevents?api-version=2020-07-01
#      which typically surfaces 30s before SIGTERM.
#
# Polling IMDS is strictly earlier and more reliable than waiting for the OS
# signal. When we detect a Preempt event affecting this VM, we touch a
# sentinel file and send SIGTERM to the orchestrator so its trap runs while
# we still have disk and network.
#
# This script is spawned as a background child of the orchestrator. It exits
# automatically when the orchestrator's PID disappears.
#
# Env vars:
#   DEFAB_ORCH_PID   -- PID of the orchestrator to signal (required)
#   DEFAB_SENTINEL   -- path to touch on imminent preemption (optional)
#   DEFAB_POLL_SEC   -- poll interval in seconds (default 5)
#
# Author: Patrick Cooper
# =============================================================================

set -u

ORCH_PID="${DEFAB_ORCH_PID:?DEFAB_ORCH_PID must be set}"
SENTINEL="${DEFAB_SENTINEL:-/data/defab_results/.preemption_imminent}"
POLL_SEC="${DEFAB_POLL_SEC:-5}"

IMDS_URL="http://169.254.169.254/metadata/scheduledevents?api-version=2020-07-01"
IMDS_HEADER="Metadata:true"

log() { echo "[preempt-poller $(date '+%H:%M:%S')] $*" >&2; }

# Exit silently if curl or jq are missing -- we prefer degraded operation
# (pure SIGTERM fallback) over crashing the orchestrator.
command -v curl >/dev/null 2>&1 || { log "curl not found; poller exits."; exit 0; }

# Warm up: first GET may be slow as IMDS establishes the subscription.
curl -s -H "$IMDS_HEADER" --max-time 5 "$IMDS_URL" >/dev/null 2>&1 || true

log "started (orchestrator pid=$ORCH_PID, interval=${POLL_SEC}s)"

while kill -0 "$ORCH_PID" 2>/dev/null; do
    # The IMDS response is JSON of the form:
    #   {"DocumentIncarnation":N,"Events":[{"EventId":"...","EventType":"Preempt","ResourceType":"VirtualMachine","Resources":["<vm-name>"],"EventStatus":"Scheduled","NotBefore":"..."}]}
    # "Preempt" is the eviction; we also alarm on "Freeze" and "Reboot" since
    # they frequently precede a forced restart on Spot.
    payload="$(curl -s -H "$IMDS_HEADER" --max-time 5 "$IMDS_URL" || true)"

    if [[ -n "$payload" ]]; then
        # Pass payload via env var so it can contain any quoting.
        urgent="$(IMDS_PAYLOAD="$payload" python3 - <<'PY' 2>/dev/null || true
import json, os, sys
try:
    data = json.loads(os.environ.get("IMDS_PAYLOAD", ""))
except Exception:
    sys.exit(0)
urgent_types = {"Preempt", "Freeze", "Reboot", "Redeploy", "Terminate"}
hits = [
    ev for ev in data.get("Events", [])
    if ev.get("EventType") in urgent_types
]
if hits:
    types = ",".join(sorted({ev["EventType"] for ev in hits}))
    print(types)
PY
        )"

        if [[ -n "$urgent" ]]; then
            log "IMDS reports urgent event(s): $urgent -- signaling orchestrator."
            mkdir -p "$(dirname "$SENTINEL")" 2>/dev/null || true
            printf 'imminent=%s\ndetected_at=%s\n' \
                "$urgent" "$(date -Iseconds)" > "$SENTINEL" 2>/dev/null || true
            kill -SIGTERM "$ORCH_PID" 2>/dev/null || true
            sleep 2
            exit 0
        fi
    fi

    sleep "$POLL_SEC"
done

log "orchestrator pid $ORCH_PID is gone; poller exits."
