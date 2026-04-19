"""Single source of truth for behavioral trigger result locations.

Behavioral routing results live under ``lab/eval/triggers/results/{namespace}/``.
For haiku and apfel providers, the namespace is the provider name. For
Ollama, the namespace is model-derived
(``gemma4:26b-a4b-it-q8_0`` -> ``gemma4-26b-a4b-it-q8_0``) so cache
comparisons stay model-specific while the CLI provider remains ``ollama``.
This module owns the active provider state so all tools
(behavioral_scorer, dimensions/behavioral, eval_sensitivity,
neighbor_regression) read and write the same directory without coordinating
their own module-level bindings.

Public API:

- ``active_results_dir()`` / ``get_active_provider()`` /
  ``get_active_cache_namespace()`` — getters used by every reader and writer.
- ``set_active_provider(name)`` — CLI entry points call this to honor their
  ``--provider`` flag (or env var via ``resolve_provider(None)``).
- ``resolve_provider(name)`` — pure allowlist validation (used indirectly
  via the getter/setter; exposed for the argparse default).

``results_dir(provider, model)`` is retained as a pure helper that composes a
path from an explicit provider/model pair without touching the active state.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
import re

from .trigger_scorer import TRIGGERS_DIR


_log = logging.getLogger("results_dir")


RESULTS_BASE: Path = TRIGGERS_DIR / "results"

DEFAULT_PROVIDER: str = "ollama"
SUPPORTED_PROVIDERS: frozenset[str] = frozenset({"ollama", "apfel", "haiku"})
PROVIDER_ENV_VAR: str = "RUBY_PLUGIN_EVAL_PROVIDER"
OLLAMA_MODEL_ENV_VAR: str = "RUBY_PLUGIN_EVAL_OLLAMA_MODEL"
DEFAULT_OLLAMA_MODEL: str = "gemma4:26b-a4b-it-q8_0"


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


def resolve_ollama_model(model: str | None = None) -> str:
    """Return the active Ollama model tag for routing evals."""
    if model is None:
        model = os.environ.get(OLLAMA_MODEL_ENV_VAR)
    model = (model or DEFAULT_OLLAMA_MODEL).strip()
    return model or DEFAULT_OLLAMA_MODEL


def model_cache_namespace(model: str | None = None) -> str:
    """Return a safe cache namespace derived from an Ollama model tag.

    Examples:
    - ``gemma4:26b-a4b-it-q8_0`` -> ``gemma4-26b-a4b-it-q8_0``
    - ``gemma4:latest`` -> ``gemma4``
    - ``qwen3:8b`` -> ``qwen3-8b``
    - ``qwen3:14b`` -> ``qwen3-14b``
    - ``library/gemma4:latest`` -> ``gemma4``
    """
    model_name = resolve_ollama_model(model)
    leaf = model_name.rsplit("/", 1)[-1].strip()
    if ":" in leaf:
        base, tag = leaf.split(":", 1)
        raw_namespace = base if tag == "latest" else f"{base}-{tag}"
    else:
        raw_namespace = leaf
    namespace = re.sub(r"[^A-Za-z0-9._-]+", "-", raw_namespace).strip(".-_")
    return namespace or "ollama"


def cache_namespace(provider: str | None = None, model: str | None = None) -> str:
    """Return the result-cache namespace for a provider/model pair."""
    resolved = resolve_provider(provider)
    if resolved == "ollama":
        return model_cache_namespace(model)
    return resolved


def results_dir(provider: str | None = None, model: str | None = None) -> Path:
    """Return the result directory for an explicit provider/model pair."""
    return RESULTS_BASE / cache_namespace(provider, model)


# Active provider — the single source of truth for which results directory
# all behavioral eval tools read from and write to. Initialized from the env
# var at import; CLI entry points flip it via set_active_provider().
_active_provider: str = resolve_provider(None)


def get_active_provider() -> str:
    """Return the currently active provider name."""
    return _active_provider


def get_active_cache_namespace() -> str:
    """Return the currently active result-cache namespace."""
    return cache_namespace(_active_provider)


def active_results_dir() -> Path:
    """Return the active result-cache directory.

    All behavioral eval tools read/write through this getter so CLI flag
    and env var stay in lockstep across the module graph.
    """
    return RESULTS_BASE / get_active_cache_namespace()


def set_active_provider(name: str | None) -> str:
    """Switch the active provider for subsequent reads/writes.

    Validates through ``resolve_provider``. Invalid values fall back to the
    default provider; one-time warnings are only emitted for invalid values
    read from ``RUBY_PLUGIN_EVAL_PROVIDER`` (explicit bad names passed by a
    programmatic caller are silently defaulted — that's a caller bug, not a
    user config bug). Returns the resolved name. Thread safety: expected to
    be called from a single CLI main() before worker threads spawn; not safe
    to flip under concurrency.
    """
    global _active_provider
    _active_provider = resolve_provider(name)
    return _active_provider
