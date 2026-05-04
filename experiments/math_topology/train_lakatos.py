"""
Lakatos training driver (M2).

Thin orchestration wrapper that:

    1. Calls :mod:`prepare_sft_data` to produce the SFT JSONL.
    2. Calls :mod:`prepare_dpo_data` to produce the margin-weighted DPO JSONL.
    3. Optionally invokes ``experiments/finetuning/train_sft.py`` and
       ``experiments/finetuning/train_dpo.py`` over those JSONLs.

Step 3 requires a CUDA install + the existing TRL stack.  When ``--dry-run``
is supplied (default in tests / CI) we stop after step 2 and only verify
the data flow is consistent; the actual training calls are exercised by
the existing ``experiments/finetuning/`` test suite under their own
fixtures.

This split is intentional: the math-side novelty in M2 is the *data*, not
a different training algorithm.  The training algorithm is the same SFT +
margin-weighted DPO recipe used in the main project.

Usage:

    python experiments/math_topology/train_lakatos.py --dry-run

    # Real run (CURC; assumes vLLM not needed for SFT):
    python experiments/math_topology/train_lakatos.py \
        --base-model Qwen/Qwen2.5-7B-Instruct \
        --output-dir experiments/math_topology/checkpoints/lakatos_v0/

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "experiments"))

from math_topology.prepare_dpo_data import build_dpo_records, write_records as write_dpo
from math_topology.prepare_sft_data import build_sft_records, write_records as write_sft


@dataclass
class PreparedArtifacts:
    sft_path:   Path
    dpo_path:   Path
    n_sft:      int
    n_dpo:      int


def prepare_artifacts(data_dir: Path) -> PreparedArtifacts:
    data_dir.mkdir(parents=True, exist_ok=True)
    sft_path = data_dir / "lakatos_sft.jsonl"
    dpo_path = data_dir / "lakatos_dpo.jsonl"
    n_sft = write_sft(build_sft_records(), sft_path)
    n_dpo = write_dpo(build_dpo_records(), dpo_path)
    return PreparedArtifacts(sft_path, dpo_path, n_sft, n_dpo)


def maybe_run_training(
    artifacts: PreparedArtifacts,
    base_model: str | None,
    output_dir: Path | None,
    dry_run: bool,
) -> int:
    if dry_run or base_model is None or output_dir is None:
        return 0
    sft_script = ROOT / "experiments" / "finetuning" / "train_sft.py"
    dpo_script = ROOT / "experiments" / "finetuning" / "train_dpo.py"
    output_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        sys.executable, str(sft_script),
        "--data", str(artifacts.sft_path),
        "--base-model", base_model,
        "--output-dir", str(output_dir / "sft"),
    ], check=True)
    subprocess.run([
        sys.executable, str(dpo_script),
        "--data", str(artifacts.dpo_path),
        "--base-model", str(output_dir / "sft"),
        "--output-dir", str(output_dir / "dpo"),
    ], check=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path,
                        default=ROOT / "experiments" / "math_topology" / "data" / "lakatos")
    parser.add_argument("--base-model", type=str, default=None)
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--no-dry-run", dest="dry_run", action="store_false")
    args = parser.parse_args()

    artifacts = prepare_artifacts(args.data_dir)
    sys.stdout.write(
        f"Lakatos artifacts ready: SFT={artifacts.n_sft} pairs at {artifacts.sft_path}; "
        f"DPO={artifacts.n_dpo} pairs at {artifacts.dpo_path}\n"
    )
    return maybe_run_training(
        artifacts,
        base_model=args.base_model,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    sys.exit(main())
