"""Shared auth-settings helpers for lab/eval tools that shell out to
``claude --bare``.

``resolve_settings_path()`` runs the keychain-based ``apiKeyHelper`` from
``lab/eval/bare_settings.json`` exactly once, caches the resulting OAuth
token in the ``_RUBY_PLUGIN_RESOLVED_TOKEN`` env var, and writes a temp
settings file whose helper reads from the env var instead of hitting the
keychain. Needed because ``security find-generic-password`` under
concurrent workers triggers auth prompts / failures.

Used by:

- ``behavioral_scorer.py`` (skill-routing eval)
- ``epistemic_suite.py`` (epistemic posture eval)

Callers pass the returned path via ``claude --bare --settings <path>``.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from .trigger_scorer import TRIGGERS_DIR

_log = logging.getLogger("eval_auth")

#: Canonical settings file shipped in the repo. Contains the original
#: ``apiKeyHelper`` that hits the macOS keychain.
BARE_SETTINGS_PATH: Path = TRIGGERS_DIR.parent / "bare_settings.json"

#: Env var used by the temp settings file's ``apiKeyHelper`` to read the
#: already-extracted OAuth token (so concurrent workers don't re-hit the
#: keychain).
RESOLVED_TOKEN_ENV: str = "_RUBY_PLUGIN_RESOLVED_TOKEN"


def resolve_settings_path() -> tuple[str, bool]:
    """Return ``(settings_path, is_temp)`` for ``claude --bare --settings``.

    Extracts the OAuth token from the keychain helper once, stores it in
    ``RESOLVED_TOKEN_ENV`` so subprocess workers inherit it, and writes a
    temp settings file whose helper reads from the env var. Subsequent
    ``claude --bare`` invocations under the same process reuse the temp
    path without touching the keychain.

    Falls back to the canonical settings path when:

    - ``bare_settings.json`` is missing or malformed
    - ``bare_settings.json`` has no ``apiKeyHelper`` (plain static token)
    - The helper itself fails (empty output, non-zero exit, exception)

    Callers should register ``cleanup_settings(path, is_temp)`` via
    ``atexit`` to remove the temp file on process exit.
    """
    if not BARE_SETTINGS_PATH.is_file():
        return str(BARE_SETTINGS_PATH), False

    try:
        settings = json.loads(BARE_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return str(BARE_SETTINGS_PATH), False

    helper = settings.get("apiKeyHelper")
    if not helper:
        return str(BARE_SETTINGS_PATH), False

    try:
        result = subprocess.run(
            ["/bin/sh", "-c", helper],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        token = result.stdout.strip()
        if not token or result.returncode != 0:
            _log.warning("apiKeyHelper failed, falling back to per-call helper")
            return str(BARE_SETTINGS_PATH), False
    except Exception as exc:
        _log.warning(
            "apiKeyHelper failed (%s), falling back to per-call helper", exc
        )
        return str(BARE_SETTINGS_PATH), False

    os.environ[RESOLVED_TOKEN_ENV] = token

    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".json",
        prefix="bare_resolved_",
        delete=False,
    )
    settings["apiKeyHelper"] = f'printf %s "${RESOLVED_TOKEN_ENV}"'
    json.dump(settings, tmp)
    tmp.close()
    return tmp.name, True


def cleanup_settings(path: str, is_temp: bool) -> None:
    """Remove the temp settings file and clear the env-var token.

    Safe to call multiple times. ``is_temp=False`` is a no-op.
    """
    if not is_temp:
        return
    try:
        os.unlink(path)
    except OSError:
        pass
    os.environ.pop(RESOLVED_TOKEN_ENV, None)
