"""
Regression tests for ``scripts/defab_finetune.service`` and
``scripts/defab_watchdog.service`` to prevent known-bad systemd patterns from
re-entering the orchestration units.

Concrete bug we are guarding against (observed 2026-04-20 on Azure):

    ExecStop=/bin/kill -SIGTERM $MAINPID

When the orchestrator's own SIGTERM handler beats systemd to a graceful exit
(which is exactly what happens during an Azure Spot preemption: the IMDS
poller signals the orchestrator, which exits 0), MAINPID has already cleared.
``kill`` is then invoked with no positional argument, prints its usage to
stderr, and exits 1.  systemd records this as a unit failure, which then
fires ``Restart=on-failure`` on a VM that Azure is about to deallocate --
wasting restart-budget from StartLimitBurst and producing alarming
"FAILURE" status output for what was actually a clean shutdown.

The fix is to drop ``ExecStop`` entirely; systemd already SIGTERMs MainPID
itself thanks to ``KillSignal=SIGTERM`` and propagates to the cgroup via
``KillMode=mixed``.

These tests also enforce the broader hardening contract documented in
``hpc/AZURE_FINETUNE.md``: spot-resilient services MUST set ``KillMode``,
``KillSignal``, ``TimeoutStopSec``, ``Restart``, and have a sane PATH so
conda-installed binaries (``python``, ``torchrun``) resolve from systemd.

Author: Patrick Cooper
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = ROOT / "scripts"

FINETUNE_UNIT = SCRIPTS / "defab_finetune.service"
WATCHDOG_UNIT = SCRIPTS / "defab_watchdog.service"


def _read(path: Path) -> str:
    assert path.exists(), f"Missing systemd unit: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Anti-pattern: ExecStop using $MAINPID
# ---------------------------------------------------------------------------

def test_finetune_unit_does_not_use_execstop_kill_mainpid() -> None:
    """The exact bug we observed on Apr 20 -- spot preemption misclassified
    as a failure because ExecStop=/bin/kill ran after MAINPID cleared.

    This pattern only makes sense for services that do NOT have their own
    signal handlers. Our orchestrator catches SIGTERM itself, so any
    redundant ExecStop will race with the orchestrator's own exit and fail."""
    src = _read(FINETUNE_UNIT)
    offending = re.findall(
        r"^\s*ExecStop\s*=.*\$MAINPID", src, flags=re.MULTILINE
    )
    assert not offending, (
        "defab_finetune.service must not declare ExecStop=...$MAINPID. "
        "systemd already SIGTERMs MainPID via KillSignal=SIGTERM. The "
        "redundant kill races our own signal handler, and on graceful spot "
        "preemption (orchestrator already exited 0) it fires `kill` with "
        "no argument -> exit 1 -> false 'Failed' status -> wasted restart "
        "budget on a dying VM. Found offending lines:\n"
        + "\n".join(offending)
    )


# ---------------------------------------------------------------------------
# Required directives for spot-VM resilience
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("directive,expected", [
    ("KillMode", "mixed"),
    ("KillSignal", "SIGTERM"),
    ("Restart", "on-failure"),
])
def test_finetune_unit_has_required_directive(directive: str, expected: str) -> None:
    src = _read(FINETUNE_UNIT)
    pattern = rf"^\s*{re.escape(directive)}\s*=\s*{re.escape(expected)}\s*$"
    matches = re.findall(pattern, src, flags=re.MULTILINE)
    assert matches, (
        f"defab_finetune.service is missing required directive "
        f"'{directive}={expected}'. This breaks spot-VM resilience -- see "
        f"hpc/AZURE_FINETUNE.md for the rationale."
    )


def test_finetune_unit_has_reasonable_stop_timeout() -> None:
    """Azure gives a Spot VM ~30s after ScheduledEvents notice. We need
    enough headroom to flush a checkpoint and the state file. Anything less
    than 30s risks a SIGKILL mid-fsync; anything over 90s and systemd will
    fight the kernel's eviction timer."""
    src = _read(FINETUNE_UNIT)
    match = re.search(r"^\s*TimeoutStopSec\s*=\s*(\d+)", src, flags=re.MULTILINE)
    assert match, "defab_finetune.service must set TimeoutStopSec"
    seconds = int(match.group(1))
    assert 30 <= seconds <= 90, (
        f"TimeoutStopSec={seconds}s is outside the safe range [30, 90]. "
        "Azure spot eviction window is ~30s; less than that means SIGKILL "
        "before checkpoint flush, more than 90s fights the kernel."
    )


def test_finetune_unit_has_conda_path_environment() -> None:
    """systemd strips the login shell PATH. Without an explicit Environment=
    PATH= directive, `python` and `torchrun` fail to resolve and the
    orchestrator dies on the first download step (observed Apr 16)."""
    src = _read(FINETUNE_UNIT)
    pattern = re.compile(
        r'^\s*Environment\s*=\s*"?PATH=[^"\n]*miniconda3/envs/[^/]+/bin',
        flags=re.MULTILINE,
    )
    assert pattern.search(src), (
        "defab_finetune.service must set Environment=\"PATH=...miniconda3/"
        "envs/<env>/bin:...\" so torchrun/python resolve under systemd. "
        "See hpc/AZURE_FINETUNE.md."
    )


def test_finetune_unit_has_oom_score_protection() -> None:
    """The orchestrator must outlive its own training children when the
    OOM killer triggers, so it can mark the failed step and restart cleanly."""
    src = _read(FINETUNE_UNIT)
    match = re.search(r"^\s*OOMScoreAdjust\s*=\s*(-?\d+)", src, flags=re.MULTILINE)
    assert match, "defab_finetune.service must set OOMScoreAdjust"
    score = int(match.group(1))
    assert score < 0, (
        f"OOMScoreAdjust={score} should be negative (more negative => less "
        "likely to be OOM-killed). The orchestrator must survive its "
        "training children to record the failure."
    )


def test_finetune_unit_has_start_limit_protection() -> None:
    """If a bug puts us in a tight crash loop we want systemd to give up
    rather than burn restart cycles forever."""
    src = _read(FINETUNE_UNIT)
    burst = re.search(r"^\s*StartLimitBurst\s*=\s*(\d+)", src, flags=re.MULTILINE)
    interval = re.search(
        r"^\s*StartLimitIntervalSec\s*=\s*(\d+)", src, flags=re.MULTILINE
    )
    assert burst, "defab_finetune.service must set StartLimitBurst"
    assert interval, "defab_finetune.service must set StartLimitIntervalSec"
    assert int(burst.group(1)) <= 20, (
        "StartLimitBurst > 20 is too permissive for a long-running training "
        "service; a real bug would loop indefinitely without ever surfacing."
    )


# ---------------------------------------------------------------------------
# Watchdog unit safety
# ---------------------------------------------------------------------------

def test_watchdog_unit_present_and_uses_root() -> None:
    """The watchdog detects stalled training and restarts the main service.
    It needs root privileges to issue `systemctl restart` against another
    unit, and must not itself depend on the main service for ordering
    (otherwise a stalled orchestrator can deadlock the watchdog)."""
    src = _read(WATCHDOG_UNIT)
    assert re.search(r"^\s*User\s*=\s*root", src, flags=re.MULTILINE), (
        "defab_watchdog.service must run as root to restart defab_finetune."
    )
