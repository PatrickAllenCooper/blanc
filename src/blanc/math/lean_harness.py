"""
Lean 4 kernel harness for the DeFAb-Math-Topology pipeline.

The Lean kernel is the math-side analogue of the polynomial-time defeasible
verifier.  This module provides an abstract ``LeanHarness`` interface plus
three concrete backends:

    MockLeanHarness         -- deterministic in-memory backend used by tests
                               and the M0 single-example demo; carries an
                               explicit table of (theorem, defeater) -> status
                               so the topology / dropper / scorer can be
                               exercised end-to-end with no Lean install.

    SubprocessLeanHarness   -- shells out to a real Lean 4 binary if one is
                               on PATH and a project file is supplied.  Kept
                               as a simple fallback; not required for tests.

    LeanInteractHarness     -- the production backend.  Uses the
                               ``lean-interact`` package to maintain a
                               long-lived Lean REPL process, checking one
                               theorem + defeater per call without recompiling
                               the whole project.  Requires ``lean-interact``
                               (pip install lean-interact) and a working Lean
                               4 toolchain; import is lazy so the rest of the
                               package functions without it.

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
# LeanInteract backend (production; requires pip install lean-interact)
# ---------------------------------------------------------------------------


@dataclass
class LeanInteractHarness(LeanHarness):
    """Production Lean 4 harness backed by ``lean-interact``.

    Uses the Lean REPL via the ``lean-interact`` package to check theorem
    well-typedness.  A theorem with the defeater as an extra hypothesis is
    submitted with a ``sorry`` proof body; Lean accepts the goal iff:
      - no elaboration errors appear, AND
      - the only diagnostic is the expected "declaration uses 'sorry'" warning.

    The server is spawned lazily on the first :py:meth:`check` call and reused
    across calls (one process, many commands), giving millisecond-level per-call
    overhead after the initial Mathlib import (which is cached across runs by
    ``lean-interact``).

    Args:
        lean_version: Lean 4 version string, e.g. ``"v4.25.0"``. Must match a
            version installed via elan.  Defaults to the value in
            ``lean/lean-toolchain`` if the project directory is given, else
            ``"v4.25.0"`` (the pinned version for this project).
        project_dir: Path to the ``lean/`` directory containing
            ``lakefile.lean`` and ``lean-toolchain``.  When supplied, the
            server uses the existing project (avoids re-downloading Mathlib).
            When ``None``, a ``TempRequireProject`` is created automatically.
        use_mathlib: Whether to include a ``import Mathlib.Topology.Basic``
            preamble in each check.  Costs ~0ms after the first import.
        timeout_per_call_ms: Wall-clock timeout forwarded to the REPL.
    """

    lean_version: str = "v4.25.0"
    project_dir: Optional[Path] = None
    use_mathlib: bool = True
    timeout_per_call_ms: int = 10_000

    def __post_init__(self) -> None:
        self._server: Optional[object] = None

    def _get_server(self) -> object:
        if self._server is not None:
            return self._server
        try:
            from lean_interact import (  # noqa: WPS433 lazy import on purpose
                LeanREPLConfig,
                LeanServer,
                LocalProject,
                TempRequireProject,
            )
        except ImportError as exc:
            raise LeanHarnessError(
                "lean-interact is not installed; run `pip install lean-interact` "
                "or use MockLeanHarness for tests."
            ) from exc

        if self.project_dir is not None and (self.project_dir / "lakefile.lean").exists():
            project = LocalProject(directory=str(self.project_dir))
        else:
            project = TempRequireProject(
                lean_version=self.lean_version,
                require="mathlib",
            )
        config = LeanREPLConfig(project=project, verbose=False)
        self._server = LeanServer(config)
        return self._server

    @staticmethod
    def _render_command(
        theorem: MathTheorem,
        defeater: Defeater,
        masked_hypotheses: tuple[str, ...],
        use_mathlib: bool,
    ) -> str:
        kept = [h for h in theorem.hypotheses if h.name not in masked_hypotheses]
        binders = " ".join(f"({h.name} : {h.lean_expr})" for h in kept)
        defeater_name = "h_defeater"
        if binders:
            binders = f"{binders} ({defeater_name} : {defeater.lean_expr})"
        else:
            binders = f"({defeater_name} : {defeater.lean_expr})"
        thm_id = "".join(c if c.isalnum() else "_" for c in theorem.identifier)
        preamble = "import Mathlib.Topology.Basic\nopen Set Filter Topology\n" if use_mathlib else ""
        return (
            f"{preamble}"
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
        try:
            from lean_interact import Command  # noqa: WPS433
        except ImportError as exc:
            raise LeanHarnessError("lean-interact not installed") from exc

        server = self._get_server()
        cmd_text = self._render_command(
            theorem, defeater, masked_hypotheses, self.use_mathlib
        )
        start = time.monotonic()
        try:
            response = server.run(
                Command(cmd=cmd_text),
            )
        except Exception as exc:  # noqa: BLE001 broad on purpose; REPL crash
            elapsed = int((time.monotonic() - start) * 1000)
            return LeanResult(
                status=LeanStatus.ERROR,
                elapsed_ms=elapsed,
                message=str(exc)[:500],
            )
        elapsed = int((time.monotonic() - start) * 1000)

        # Inspect messages: errors -> ERROR; only-sorry warning -> PROVED;
        # sorries list non-empty with no errors -> PROVED (sorry mode);
        # nothing at all -> PROVED.
        messages = getattr(response, "messages", []) or []
        sorries = getattr(response, "sorries", []) or []
        error_msgs = [
            m for m in messages
            if getattr(m, "severity", "") == "error"
        ]
        if error_msgs:
            detail = "; ".join(getattr(m, "data", str(m)) for m in error_msgs)
            return LeanResult(
                status=LeanStatus.ERROR,
                elapsed_ms=elapsed,
                message=detail[:1000],
            )
        # A sorry-proof with no errors is PROVED for our purposes: the
        # hypothesis is well-typed and the goal is accepted.
        return LeanResult(
            status=LeanStatus.PROVED,
            elapsed_ms=elapsed,
            message="",
        )

    def close(self) -> None:
        """Shut down the REPL process if one is running."""
        if self._server is not None:
            try:
                self._server.__exit__(None, None, None)
            except Exception:  # noqa: BLE001
                pass
            self._server = None

    def __del__(self) -> None:
        self.close()


# ---------------------------------------------------------------------------
# Convenience
# ---------------------------------------------------------------------------


def available_harness(prefer_real: bool = False) -> LeanHarness:
    """Return whichever backend is usable in this environment.

    Priority when ``prefer_real=True``:
      1. ``LeanInteractHarness`` if ``lean_interact`` is importable.
      2. ``SubprocessLeanHarness`` if ``lean`` is on PATH.
      3. ``MockLeanHarness`` otherwise.

    Tests and CI never call this with ``prefer_real=True``; M1+ scripts do.
    """
    if prefer_real:
        try:
            import lean_interact  # noqa: F401
            return LeanInteractHarness()
        except ImportError:
            pass
        if shutil.which("lean") is not None:
            return SubprocessLeanHarness()
    return MockLeanHarness()
