"""
Verify and repair the DeFAb fine-tuning state file against on-disk artifacts.

The Azure-Spot orchestrator maintains a state file at
    $RESULTS_BASE/.finetune_state.json
with the shape
    {"completed": ["setup", "download", "data_qwen72", "sft_qwen72", ...]}

Previous orchestrator runs marked steps `done` as soon as the launching bash
pipeline exited 0. In practice, training/eval processes can exit 0 without
producing a usable artifact (early exit, silent OOM before the first
checkpoint, wrong out-dir, etc.). The result is a state file that lies:
subsequent boots skip those steps, so work is never redone, and downstream
consumers see phantom completions.

This script is the ground-truth arbiter. For every step key in the state
file it inspects the filesystem and removes any entry whose expected
artifact is absent or empty. The corrected state is written atomically.

Run this:
  - Unconditionally at the start of every boot (the orchestrator invokes it).
  - Manually when you want to audit what truly completed:
        python scripts/verify_and_repair_state.py \
            --state /data/defab_results/.finetune_state.json \
            --results-base /data/defab_results \
            --report

Exit codes:
  0 -- state matches disk (no changes needed or repair succeeded)
  2 -- state file missing or malformed

Author: Patrick Cooper
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable


MODELS = ("qwen72", "qwen32", "deepseek")


def _nonempty_dir(p: Path) -> bool:
    return p.is_dir() and any(p.iterdir())


def _hf_cache_has_shards(cache_hub_dir: Path, min_gb: int = 20) -> bool:
    """HF snapshot_download places shards under hub/models--<org>--<name>/snapshots/.
    We treat a cache that is at least `min_gb` total as evidence that at
    least one model's weights are present. This is a heuristic -- the
    orchestrator's predownload step is idempotent, so a false negative only
    costs us a re-check (hash matches, nothing redownloaded)."""
    if not cache_hub_dir.is_dir():
        return False
    total = 0
    threshold = min_gb * (1024 ** 3)
    for root, _dirs, files in os.walk(cache_hub_dir):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                continue
            if total >= threshold:
                return True
    return False


def _has_lora_final(method_dir: Path) -> bool:
    """A LoRA run is truly complete only if `final/` has adapter weights."""
    final = method_dir / "final"
    if not final.is_dir():
        return False
    # Adapter weights land under one of these names depending on PEFT version.
    candidates = (
        "adapter_model.safetensors",
        "adapter_model.bin",
        "pytorch_model.bin",
        "model.safetensors",
    )
    return any((final / n).exists() for n in candidates)


def _has_eval_summary(eval_dir: Path) -> bool:
    """Evaluation is done when at least one method produced a non-empty summary."""
    if not eval_dir.is_dir():
        return False
    for sub in eval_dir.rglob("summary.json"):
        try:
            if sub.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def _has_prepared_data(data_dir: Path, model_slug: str) -> bool:
    """SFT uses a shared file; preference data is per model."""
    pref = data_dir / f"preferences_{model_slug}.jsonl"
    sft_train = data_dir / "sft_train.jsonl"
    if not sft_train.exists() or sft_train.stat().st_size == 0:
        return False
    if not pref.exists() or pref.stat().st_size == 0:
        return False
    return True


def _build_checks(
    results_base: Path,
    data_dir: Path,
    instances_dir: Path,
) -> dict[str, Callable[[], bool]]:
    checks: dict[str, Callable[[], bool]] = {}

    checks["setup"] = lambda: True  # Package install is implicit once Python runs.
    checks["download"] = lambda: (instances_dir / "tier0").is_dir() and any(
        (instances_dir / "tier0").glob("*.json")
    )

    for slug in MODELS:
        checks[f"data_{slug}"] = lambda s=slug: _has_prepared_data(data_dir, s)
        checks[f"sft_{slug}"] = lambda s=slug: _has_lora_final(
            results_base / "sft" / s
        )
        checks[f"dpo_standard_{slug}"] = lambda s=slug: _has_lora_final(
            results_base / "dpo_standard" / s
        )
        checks[f"dpo_margin_{slug}"] = lambda s=slug: _has_lora_final(
            results_base / "dpo_margin" / s
        )
        checks[f"grpo_{slug}"] = lambda s=slug: _has_lora_final(
            results_base / "grpo" / s
        )
        checks[f"rlhf_vitl_{slug}"] = lambda s=slug: _has_lora_final(
            results_base / "rlhf_vitl" / s
        )
        checks[f"eval_{slug}"] = lambda s=slug: _has_eval_summary(
            results_base / "eval" / s
        )
        checks[f"predownload_{slug}"] = lambda s=slug: _hf_cache_has_shards(
            Path(os.environ.get("HF_HOME", "/data/hf_cache")) / "hub",
            min_gb=20,
        )

    checks["all_done"] = lambda: all(
        _has_eval_summary(results_base / "eval" / s) for s in MODELS
    )

    return checks


def _atomic_write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", required=True, help="Path to .finetune_state.json")
    p.add_argument(
        "--results-base", required=True, help="Base results directory"
    )
    p.add_argument(
        "--data-dir",
        default=None,
        help="Fine-tuning data dir (default: <repo>/experiments/finetuning/data)",
    )
    p.add_argument(
        "--instances-dir",
        default=None,
        help="Instances dir (default: <repo>/instances)",
    )
    p.add_argument(
        "--repo-dir",
        default=os.environ.get("REPO_DIR", "/home/azureuser/blanc"),
    )
    p.add_argument(
        "--report",
        action="store_true",
        help="Print per-step verification without rewriting the state file.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change but do not write.",
    )
    args = p.parse_args()

    state_path = Path(args.state)
    results_base = Path(args.results_base)
    repo_dir = Path(args.repo_dir)
    data_dir = (
        Path(args.data_dir)
        if args.data_dir
        else repo_dir / "experiments" / "finetuning" / "data"
    )
    instances_dir = (
        Path(args.instances_dir) if args.instances_dir else repo_dir / "instances"
    )

    if not state_path.exists():
        print(f"State file does not exist at {state_path}; nothing to repair.")
        _atomic_write_json(state_path, {"completed": []})
        return 0

    try:
        state = json.loads(state_path.read_text())
    except json.JSONDecodeError as exc:
        print(f"ERROR: state file is malformed ({exc}). Resetting to empty.")
        _atomic_write_json(state_path, {"completed": []})
        return 2

    completed = list(state.get("completed", []))
    checks = _build_checks(results_base, data_dir, instances_dir)

    verified: list[str] = []
    removed: list[str] = []
    unknown: list[str] = []

    for key in completed:
        check = checks.get(key)
        if check is None:
            unknown.append(key)
            continue
        try:
            ok = bool(check())
        except Exception as exc:  # noqa: BLE001
            print(f"  [warn] {key}: check raised {exc!r}; treating as missing.")
            ok = False
        if ok:
            verified.append(key)
        else:
            removed.append(key)

    print("State reconciliation report")
    print(f"  state file   : {state_path}")
    print(f"  results base : {results_base}")
    print(f"  verified     : {len(verified)} / {len(completed)} entries")
    for k in verified:
        print(f"    [ok]      {k}")
    for k in removed:
        print(f"    [PHANTOM] {k}  (artifact missing, removing)")
    for k in unknown:
        print(f"    [unknown] {k}  (no verifier; leaving as-is)")

    if args.report:
        return 0

    new_completed = verified + unknown  # keep unknown rather than drop blindly
    if new_completed == completed:
        print("State already matches disk; no write needed.")
        return 0

    if args.dry_run:
        print(f"--dry-run: would write {len(new_completed)} entries.")
        return 0

    new_state = dict(state)
    new_state["completed"] = new_completed
    _atomic_write_json(state_path, new_state)
    print(f"Wrote reconciled state with {len(new_completed)} entries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
