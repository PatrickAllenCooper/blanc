"""
Compatibility shim for the TRL/transformers signature drift in ``Trainer.log``.

Symptom we are protecting against, observed on Azure 2x A100 with Qwen2.5-72B
4-bit + LoRA + DDP after the QLoRA grad-checkpointing fix landed:

    File "transformers/trainer.py", line 3043, in _maybe_log_save_evaluate
        self.log(logs, start_time)
    TypeError: DPOTrainer.log() takes 2 positional arguments but 3 were given

Cause: ``transformers >= 4.43`` adds ``start_time`` as a positional argument
to ``Trainer.log`` so it can compute throughput metrics.  TRL trainers that
override ``log`` were written against the old ``Trainer.log(self, logs)``
signature and have not yet been updated.  The mismatch surfaces the very
first time a training loop hits its ``logging_steps`` interval.

The pragmatic fix without forcing a TRL upgrade (which would cascade through
``DPOConfig`` / ``GRPOConfig`` API changes): monkey-patch the affected TRL
trainer classes so their ``log`` method silently absorbs and forwards any
extra positional / keyword arguments to whatever the original ``log``
expected.

This module is import-only.  Importing it once -- ideally at the top of any
script that instantiates ``DPOTrainer``, ``RewardTrainer`` or ``GRPOTrainer``
-- patches every relevant class in place.  Re-importing is idempotent.

Author: Anonymous Authors
"""

from __future__ import annotations

import inspect
import logging

LOGGER = logging.getLogger(__name__)

_PATCHED_FLAG = "_defab_log_compat_patched"


def _wrap_log(cls) -> None:
    """Replace ``cls.log`` with a wrapper that tolerates extra positional /
    keyword arguments while preserving the underlying behaviour."""
    if cls is None or getattr(cls, _PATCHED_FLAG, False):
        return

    original_log = cls.__dict__.get("log")
    if original_log is None:
        # Class does not override log itself; transformers.Trainer.log already
        # accepts the new signature, so nothing to do.
        setattr(cls, _PATCHED_FLAG, True)
        return

    try:
        sig = inspect.signature(original_log)
        params = list(sig.parameters.values())
    except (TypeError, ValueError):
        params = []

    accepts_var_args = any(
        p.kind is inspect.Parameter.VAR_POSITIONAL for p in params
    )
    accepts_var_kwargs = any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in params
    )
    positional_count = sum(
        1
        for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
    )

    if accepts_var_args and accepts_var_kwargs:
        # Already tolerant; nothing to do.
        setattr(cls, _PATCHED_FLAG, True)
        return

    def patched_log(self, logs, *args, **kwargs):
        # Drop arguments the wrapped log does not accept rather than crashing.
        if accepts_var_args or positional_count > 2:
            return original_log(self, logs, *args, **kwargs)
        return original_log(self, logs)

    patched_log.__name__ = original_log.__name__
    patched_log.__qualname__ = original_log.__qualname__
    patched_log.__doc__ = original_log.__doc__
    patched_log.__wrapped__ = original_log

    setattr(cls, "log", patched_log)
    setattr(cls, _PATCHED_FLAG, True)
    LOGGER.debug("Patched %s.log for transformers>=4.43 compatibility", cls.__name__)


def patch_all() -> None:
    """Patch every TRL trainer class we use that overrides ``log``."""
    candidates = []

    try:
        from trl import DPOTrainer
        candidates.append(DPOTrainer)
    except ImportError:
        pass

    try:
        from trl import GRPOTrainer
        candidates.append(GRPOTrainer)
    except ImportError:
        pass

    try:
        from trl import RewardTrainer
        candidates.append(RewardTrainer)
    except ImportError:
        pass

    try:
        from trl import SFTTrainer
        candidates.append(SFTTrainer)
    except ImportError:
        pass

    for cls in candidates:
        _wrap_log(cls)


patch_all()
