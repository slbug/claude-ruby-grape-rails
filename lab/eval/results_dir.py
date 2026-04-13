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

import logging
import os
from pathlib import Path

from .trigger_scorer import TRIGGERS_DIR


_log = logging.getLogger("results_dir")


RESULTS_BASE: Path = TRIGGERS_DIR / "results"

DEFAULT_PROVIDER: str = "apfel"
SUPPORTED_PROVIDERS: frozenset[str] = frozenset({"apfel", "haiku"})
PROVIDER_ENV_VAR: str = "RUBY_PLUGIN_EVAL_PROVIDER"


# Track invalid env-var values so we warn only once per unique bad value,
# not on every resolve_provider() call.
_warned_invalid_env: set[str] = set()


def resolve_provider(name: str | None = None) -> str:
    """Return a supported provider name, falling back to DEFAULT_PROVIDER.

    When ``name`` is None, reads from the ``RUBY_PLUGIN_EVAL_PROVIDER`` env
    var. Any value outside SUPPORTED_PROVIDERS (typo, path-traversal attempt,
    empty string, etc.) falls through to the default so unsanitized input
    can't point results I/O outside RESULTS_BASE.

    An invalid non-empty env-var value emits a one-time warning (per value)
    so typos like ``RUBY_PLUGIN_EVAL_PROVIDER=haik`` don't silently route to
    the default and desync reader/writer caches.
    """
    env_value: str | None = None
    if name is None:
        env_value = os.environ.get(PROVIDER_ENV_VAR)
        name = env_value if env_value is not None else DEFAULT_PROVIDER
    if name in SUPPORTED_PROVIDERS:
        return name
    # Invalid: warn once if it came from the env var (not from a programmatic
    # caller passing a bad string — those are the caller's responsibility).
    if env_value is not None and env_value and env_value not in _warned_invalid_env:
        _warned_invalid_env.add(env_value)
        _log.warning(
            "%s=%r is not a supported provider (%s); falling back to %r.",
            PROVIDER_ENV_VAR,
            env_value,
            ", ".join(sorted(SUPPORTED_PROVIDERS)),
            DEFAULT_PROVIDER,
        )
    return DEFAULT_PROVIDER


def results_dir(provider: str | None = None) -> Path:
    """Return the provider-scoped results directory (``RESULTS_BASE/{provider}``)."""
    return RESULTS_BASE / resolve_provider(provider)
