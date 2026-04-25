"""Shared logging helpers for lab/eval tools.

``emit_info(msg)`` writes a timestamped informational message to stderr in a
way that works both under the CLI (where ``logging.basicConfig`` has raised
the root level to INFO) and under programmatic callers (tests,
neighbor_regression, etc.) that leave the root logger at WARNING.

``verbose_lock`` serializes multi-line verbose output blocks across worker
threads so per-call log groups stay contiguous in stderr output.

Used by:

- ``behavioral_scorer.py`` (skill-routing eval)
- ``epistemic_suite.py`` (epistemic posture eval)

Prefer these helpers over direct ``print(..., file=sys.stderr)`` or module-
local clones to keep stderr formatting consistent across the suite.
"""


import logging
import sys
import threading

_log = logging.getLogger("eval")

#: Lock used to serialize multi-line verbose output across worker threads.
verbose_lock: threading.Lock = threading.Lock()


def emit_info(msg: str) -> None:
    """Emit an informational message that must reach the user.

    When ``logging.basicConfig`` has enabled INFO (the CLI main()), routes
    through the logger so the timestamp/format stays consistent with the
    rest of the eval suite. When INFO is disabled (programmatic callers,
    tests), falls back to direct ``print(..., file=sys.stderr, flush=True)``
    so progress messages are never silently dropped.
    """
    if _log.isEnabledFor(logging.INFO):
        _log.info(msg)
    else:
        print(msg, file=sys.stderr, flush=True)
