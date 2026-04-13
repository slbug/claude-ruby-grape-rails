"""Shared helpers for locating provider-scoped behavioral trigger results.

Behavioral routing results live under ``lab/eval/triggers/results/{provider}/``.
Multiple tools read or write that path (behavioral_scorer, dimensions/behavioral,
eval_sensitivity, neighbor_regression) and each one needs the same provider
allowlist to avoid path traversal via env vars and to stay consistent with
the writer. Keep that logic in one place.

Each consumer still exposes its own module-level ``RESULTS_DIR`` binding so
tests can patch it directly — the helpers here just produce the canonical
Path from a validated provider name.
"""

from __future__ import annotations

import os
from pathlib import Path

from .trigger_scorer import TRIGGERS_DIR


RESULTS_BASE: Path = TRIGGERS_DIR / "results"

DEFAULT_PROVIDER: str = "apfel"
SUPPORTED_PROVIDERS: frozenset[str] = frozenset({"apfel", "haiku"})
PROVIDER_ENV_VAR: str = "RUBY_PLUGIN_EVAL_PROVIDER"


def resolve_provider(name: str | None = None) -> str:
    """Return a supported provider name, falling back to DEFAULT_PROVIDER.

    When ``name`` is None, reads from the ``RUBY_PLUGIN_EVAL_PROVIDER`` env
    var. Any value outside SUPPORTED_PROVIDERS (typo, path-traversal attempt,
    empty string, etc.) falls through to the default so unsanitized input
    can't point results I/O outside RESULTS_BASE.
    """
    if name is None:
        name = os.environ.get(PROVIDER_ENV_VAR, DEFAULT_PROVIDER)
    if name in SUPPORTED_PROVIDERS:
        return name
    return DEFAULT_PROVIDER


def results_dir(provider: str | None = None) -> Path:
    """Return the provider-scoped results directory (``RESULTS_BASE/{provider}``)."""
    return RESULTS_BASE / resolve_provider(provider)
