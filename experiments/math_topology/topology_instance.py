"""
DeFAb-Math-Topology benchmark instance schema.

Math-side counterpart of :class:`blanc.author.generation.AbductiveInstance`.
Each ``TopologyInstance`` is one (theorem, level, ablation) row of the
DeFAb-Math-Topology benchmark.

    Level 1 -- Missing-lemma / fact completion.  One non-critical
        hypothesis is masked and the model must propose it back.
        Lean-checked: parent theorem with restored hypothesis must elaborate.

    Level 2 -- Theorem-statement abduction.  The full statement is masked;
        the model is given hypotheses + a one-line natural-language hint
        and must propose the conclusion.

    Level 3 -- Counterexample-with-conservativity.  A critical hypothesis
        is masked and the model must propose a strictly weaker defeater
        (matched by :class:`blanc.math.NoveltyFilter`).

Author: Patrick Cooper
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

from blanc.math.types import Hypothesis, MathTheorem


@dataclass(frozen=True)
class TopologyInstance:
    """One benchmark row.

    Attributes:
        instance_id: Stable ID of the form ``L{level}.{theorem_id}.{mask_tag}``.
        level: 1, 2, or 3.
        theorem_identifier: Source theorem identifier in the corpus.
        theorem_statement: The full statement (always present, used for
            Lean checking; for L2 the prompt withholds it from the model).
        hypotheses: All hypotheses on the parent theorem.
        masked_hypotheses: Names of hypotheses removed from the model's
            prompt.  Empty for L2 (the *statement* is masked there, not
            hypotheses).
        gold: For L1, the dropped hypothesis expression(s); for L2, the
            statement; for L3, all Lean-acceptable defeaters known at
            generation time (typically the dropped hypothesis itself plus
            any harvested counterexample-driven refinement).
        prompt: Natural-language prompt suitable for the model_interface.
        metadata: Free-form provenance, source path, etc.
    """

    instance_id: str
    level: int
    theorem_identifier: str
    theorem_statement: str
    hypotheses: tuple[Hypothesis, ...]
    masked_hypotheses: tuple[str, ...]
    gold: tuple[str, ...]
    prompt: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "instance_id":         self.instance_id,
            "level":               self.level,
            "theorem_identifier":  self.theorem_identifier,
            "theorem_statement":   self.theorem_statement,
            "hypotheses":          [asdict(h) for h in self.hypotheses],
            "masked_hypotheses":   list(self.masked_hypotheses),
            "gold":                list(self.gold),
            "prompt":              self.prompt,
            "metadata":            self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TopologyInstance":
        return cls(
            instance_id=data["instance_id"],
            level=data["level"],
            theorem_identifier=data["theorem_identifier"],
            theorem_statement=data["theorem_statement"],
            hypotheses=tuple(Hypothesis(**h) for h in data["hypotheses"]),
            masked_hypotheses=tuple(data["masked_hypotheses"]),
            gold=tuple(data["gold"]),
            prompt=data["prompt"],
            metadata=dict(data.get("metadata", {})),
        )


def write_jsonl(instances: Iterable[TopologyInstance], path: Path) -> int:
    """Write instances as JSONL.  Returns the number of rows written."""
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for inst in instances:
            f.write(json.dumps(inst.to_dict()))
            f.write("\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[TopologyInstance]:
    out: list[TopologyInstance] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(TopologyInstance.from_dict(json.loads(line)))
    return out


def reconstruct_theorem(inst: TopologyInstance) -> MathTheorem:
    """Rebuild the parent ``MathTheorem`` from an instance.  Useful for
    feeding the harness / scorer downstream of a saved benchmark."""
    return MathTheorem(
        identifier=inst.theorem_identifier,
        statement=inst.theorem_statement,
        hypotheses=inst.hypotheses,
        natural_language=inst.metadata.get("natural_language", ""),
        source_path=inst.metadata.get("source_path"),
    )
