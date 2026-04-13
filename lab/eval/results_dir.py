"""Single source of truth for provider-scoped behavioral trigger results.

Behavioral routing results live under ``lab/eval/triggers/results/{provider}/``.
This module owns the active provider state so all tools
(behavioral_scorer, dimensions/behavioral, eval_sensitivity,
neighbor_regression) read and write the same directory without coordinating
their own module-level bindings.

Public API:

- ``active_results_dir()`` / ``get_active_provider()`` — getters used by
  every reader and writer.
- ``set_active_provider(name)`` — CLI entry points call this to honor their
  ``--provider`` flag (or env var via ``resolve_provider(None)``).
- ``resolve_provider(name)`` — pure allowlist validation (used indirectly
  via the getter/setter; exposed for the argparse default).

``results_dir(provider)`` is retained as a pure helper that composes a path
from an explicit provider name without touching the active state.
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


# Active provider — the single source of truth for which results directory
# all behavioral eval tools read from and write to. Initialized from the env
# var at import; CLI entry points flip it via set_active_provider().
_active_provider: str = resolve_provider(None)


def get_active_provider() -> str:
    """Return the currently active provider name."""
    return _active_provider


def active_results_dir() -> Path:
    """Return the active provider-scoped results directory.

    All behavioral eval tools read/write through this getter so CLI flag
    and env var stay in lockstep across the module graph.
    """
    return RESULTS_BASE / _active_provider


def set_active_provider(name: str | None) -> str:
    """Switch the active provider for subsequent reads/writes.

    Validates through ``resolve_provider`` (invalid values fall back to the
    default with a one-time warning). Returns the resolved name. Thread
    safety: expected to be called from a single CLI main() before worker
    threads spawn; not safe to flip under concurrency.
    """
    global _active_provider
    _active_provider = resolve_provider(name)
    return _active_provider
