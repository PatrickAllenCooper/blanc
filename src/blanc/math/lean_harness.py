"""
Lean 4 kernel harness for the DeFAb-Math-Topology pipeline.

The Lean kernel is the math-side analogue of the polynomial-time defeasible
verifier.  This module provides an abstract ``LeanHarness`` interface plus
two concrete backends:

    MockLeanHarness         -- deterministic in-memory backend used by tests
                               and the M0 single-example demo; carries an
                               explicit table of (theorem, defeater) -> status
                               so the topology / dropper / scorer can be
                               exercised end-to-end with no Lean install.

    SubprocessLeanHarness   -- shells out to a real Lean 4 binary if one is
                               on PATH and a project file is supplied.  Used
                               by M1 onwards; not required for tests.

A future ``LeanInteractHarness`` / ``LeanDojoHarness`` can drop in alongside
these by satisfying ``LeanHarness``.

The harness deliberately exposes a single coarse operation:

    check(theorem, defeater) -> LeanResult

This is the only signal the rest of the pipeline (scorer, GRPO reward, novelty
filter) consumes, so the choice of underlying backend is transparent above
this line.

Author: Patrick Cooper
"""

from __future__ import annotations

import shutil
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from blanc.math.types import Defeater, LeanResult, LeanStatus, MathTheorem


class LeanHarnessError(RuntimeError):
    """Raised when the harness itself fails (not when Lean rejects a goal)."""


# ---------------------------------------------------------------------------
# Abstract interface
# ---------------------------------------------------------------------------


class LeanHarness(ABC):
    """Abstract Lean 4 kernel adapter.

    Subclasses must implement :py:meth:`check`.  Implementations are expected
    to be stateless across calls; any caching belongs in the scorer layer.
    """

    @abstractmethod
    def check(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...] = (),
        timeout_ms: int = 5_000,
    ) -> LeanResult:
        """Ask Lean: does ``defeater`` discharge the theorem with ``masked_hypotheses`` removed?

        Args:
            theorem:           The parent theorem.
            defeater:          The candidate defeater (Lean expression).
            masked_hypotheses: Names of hypotheses removed from the parent.
                The defeater is intended to plug this gap.
            timeout_ms:        Soft per-call wall-clock budget.  Backends may
                approximate.
        """

    def healthy(self) -> bool:
        """Cheap probe; default implementation tries an empty goal."""
        try:
            self.check(
                MathTheorem(
                    identifier="_probe",
                    statement="True",
                    hypotheses=(),
                ),
                Defeater(lean_expr="trivial", provenance="probe"),
            )
            return True
        except Exception:
            return False


# ---------------------------------------------------------------------------
# Mock backend (default for tests and the M0 demo)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _MockKey:
    """Hashable lookup key for the mock harness response table."""

    theorem_id: str
    masked: tuple[str, ...]
    defeater_canonical: str


@dataclass
class MockLeanHarness(LeanHarness):
    """Deterministic in-memory Lean kernel stub.

    Carries an explicit response table keyed by
    ``(theorem.identifier, sorted(masked_hypotheses), normalised(defeater))``.
    Anything not in the table returns ``LeanStatus.UNKNOWN`` -- the scorer
    treats that as a non-acceptance, never as an accidental acceptance.
    """

    responses: dict[_MockKey, LeanResult] = field(default_factory=dict)
    default_status: LeanStatus = LeanStatus.UNKNOWN
    elapsed_ms_per_call: int = 1

    @staticmethod
    def _normalise(expr: str) -> str:
        return " ".join(expr.split()).strip()

    def register(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...],
        status: LeanStatus,
        message: str = "",
        proof_term: Optional[str] = None,
    ) -> None:
        """Pre-load a Lean verdict for one (theorem, defeater, mask) triple."""
        key = _MockKey(
            theorem_id=theorem.identifier,
            masked=tuple(sorted(masked_hypotheses)),
            defeater_canonical=self._normalise(defeater.lean_expr),
        )
        self.responses[key] = LeanResult(
            status=status,
            elapsed_ms=self.elapsed_ms_per_call,
            message=message,
            proof_term=proof_term,
        )

    def check(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...] = (),
        timeout_ms: int = 5_000,
    ) -> LeanResult:
        key = _MockKey(
            theorem_id=theorem.identifier,
            masked=tuple(sorted(masked_hypotheses)),
            defeater_canonical=self._normalise(defeater.lean_expr),
        )
        if key in self.responses:
            return self.responses[key]
        return LeanResult(
            status=self.default_status,
            elapsed_ms=self.elapsed_ms_per_call,
            message="no registered response in MockLeanHarness",
        )


# ---------------------------------------------------------------------------
# Subprocess backend (real Lean if installed)
# ---------------------------------------------------------------------------


@dataclass
class SubprocessLeanHarness(LeanHarness):
    """Talks to a real Lean 4 binary over a one-shot subprocess call.

    Each :py:meth:`check` writes a self-contained ``.lean`` file containing
    the parent theorem (with ``masked_hypotheses`` removed and ``defeater``
    re-introduced), then runs ``lean --run`` (or just ``lean``) and parses
    success / failure from the exit code and stderr.

    This is the simplest possible real-Lean backend; it is intentionally
    slow (whole-file recompile per call).  Production runs (M1 onwards)
    should swap in a long-lived LeanInteract / Pantograph backend.

    Args:
        lean_binary: Path to ``lean`` executable.  If None, looks on PATH.
        project_dir: Lean project root (must contain a ``lakefile.lean``
            or ``lean-toolchain``).  If None, the harness skips project
            context and relies on Lean's stdlib only -- which means Mathlib
            symbols will not resolve.  For tests this is fine.
        scratch_dir: Where to write the per-call ``.lean`` files.  If None,
            a temp directory under ``project_dir / "_blanc_scratch"`` is used.
    """

    lean_binary: Optional[str] = None
    project_dir: Optional[Path] = None
    scratch_dir: Optional[Path] = None
    extra_imports: tuple[str, ...] = ("Mathlib.Topology.Basic",)

    def __post_init__(self) -> None:
        binary = self.lean_binary or shutil.which("lean")
        if binary is None:
            raise LeanHarnessError(
                "no `lean` binary on PATH and no lean_binary supplied; "
                "use MockLeanHarness for tests, or install Lean 4 + elan."
            )
        self._binary: str = binary
        if self.scratch_dir is None:
            base = self.project_dir or Path.cwd()
            self.scratch_dir = base / "_blanc_scratch"
        self.scratch_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_id(s: str) -> str:
        return "".join(c if c.isalnum() else "_" for c in s)

    def _render_lean_file(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...],
    ) -> str:
        kept = [h for h in theorem.hypotheses if h.name not in masked_hypotheses]
        binders = " ".join(f"({h.name} : {h.lean_expr})" for h in kept)
        defeater_name = "h_defeater"
        if binders:
            binders = f"{binders} ({defeater_name} : {defeater.lean_expr})"
        else:
            binders = f"({defeater_name} : {defeater.lean_expr})"
        imports = "\n".join(f"import {m}" for m in self.extra_imports)
        thm_id = self._safe_id(theorem.identifier)
        return (
            f"{imports}\n"
            f"open Classical\n"
            f"theorem _blanc_check_{thm_id} {binders} : {theorem.statement} := by\n"
            f"  sorry\n"
        )

    def check(
        self,
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...] = (),
        timeout_ms: int = 5_000,
    ) -> LeanResult:
        assert self.scratch_dir is not None
        path = self.scratch_dir / f"check_{self._safe_id(theorem.identifier)}.lean"
        path.write_text(self._render_lean_file(theorem, defeater, masked_hypotheses))
        start = time.monotonic()
        try:
            cwd = self.project_dir or Path.cwd()
            proc = subprocess.run(
                [self._binary, str(path)],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_ms / 1000.0,
            )
        except subprocess.TimeoutExpired:
            elapsed = int((time.monotonic() - start) * 1000)
            return LeanResult(
                status=LeanStatus.TIMEOUT,
                elapsed_ms=elapsed,
                message=f"lean exceeded {timeout_ms}ms",
            )
        elapsed = int((time.monotonic() - start) * 1000)
        if proc.returncode == 0 and "error" not in proc.stderr.lower():
            return LeanResult(
                status=LeanStatus.PROVED,
                elapsed_ms=elapsed,
                message=proc.stdout[:500],
            )
        if "sorry" in proc.stderr.lower() or proc.returncode != 0:
            return LeanResult(
                status=LeanStatus.ERROR,
                elapsed_ms=elapsed,
                message=proc.stderr[:1000],
            )
        return LeanResult(
            status=LeanStatus.UNKNOWN,
            elapsed_ms=elapsed,
            message=proc.stderr[:1000],
        )


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def available_harness(prefer_real: bool = False) -> LeanHarness:
    """Return whichever backend is usable in this environment.

    Tests and CI never call this with ``prefer_real=True``; M1+ scripts do.
    """
    if prefer_real and shutil.which("lean") is not None:
        return SubprocessLeanHarness()
    return MockLeanHarness()
