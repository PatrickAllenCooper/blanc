"""
GRPO dataset assembly for M3.

Consumes the per-challenge ``groups.jsonl`` produced by
:mod:`at_scale_dropping` and produces a JSONL whose rows are the GRPO
training units: a prompt, K candidate completions, and per-completion
rewards / advantages.

Why a separate module: the at-scale driver is also useful as a pure
data-collection step for analysis; GRPO requires only the
prompt + samples + rewards triple.  Keeping them separate means the
sampling pass and the GRPO step are independently re-runnable.

The output is shaped to match the input expected by the existing
``experiments/finetuning/train_grpo.py`` driver in this repo.

Author: Anonymous Authors
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class GRPOUnit:
    prompt:        str
    completions:   tuple[str, ...]
    rewards:       tuple[float, ...]
    advantages:    tuple[float, ...]
    theorem_id:    str
    masked:        tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        out = asdict(self)
        # tuples -> lists for JSON friendliness
        out["completions"] = list(self.completions)
        out["rewards"] = list(self.rewards)
        out["advantages"] = list(self.advantages)
        out["masked"] = list(self.masked)
        return out


def assemble(groups_jsonl: Path) -> list[GRPOUnit]:
    units: list[GRPOUnit] = []
    for line in groups_jsonl.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        completions = tuple(s["response"] for s in obj["samples"])
        rewards = tuple(float(s["reward"]) for s in obj["samples"])
        advantages = tuple(float(a) for a in obj.get("advantages", []))
        if len(advantages) != len(completions):
            advantages = _recompute_advantages(rewards)
        units.append(GRPOUnit(
            prompt=obj["prompt"],
            completions=completions,
            rewards=rewards,
            advantages=advantages,
            theorem_id=obj["theorem"],
            masked=tuple(obj["masked"]),
        ))
    return units


def _recompute_advantages(rewards: tuple[float, ...]) -> tuple[float, ...]:
    if not rewards:
        return ()
    mean = sum(rewards) / len(rewards)
    var = sum((r - mean) ** 2 for r in rewards) / len(rewards)
    std = (var ** 0.5) or 1.0
    return tuple((r - mean) / std for r in rewards)


def write_units(units: list[GRPOUnit], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for u in units:
            f.write(json.dumps(u.to_dict()))
            f.write("\n")
    return len(units)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--groups", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    units = assemble(args.groups)
    n = write_units(units, args.output)
    sys.stdout.write(f"Wrote {n} GRPO units to {args.output}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
