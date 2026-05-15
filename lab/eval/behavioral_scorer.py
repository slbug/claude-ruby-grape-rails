"""Behavioral trigger evaluation.

Tests whether an LLM routes user prompts to the correct skill by sending all
skill routing descriptions + one test prompt to the active provider. Ollama
(local Gemma4 by default) is the only provider currently wired. Adding a
new provider is pluggable: extend `results_dir.SUPPORTED_PROVIDERS`, add a
`_PROVIDER_SETTINGS` entry, and add a dispatch branch in `_run_provider`.

Usage:
    python3 -m lab.eval.behavioral_scorer --skill plan          # Test one skill
    python3 -m lab.eval.behavioral_scorer --all                  # Test all skills with triggers
    python3 -m lab.eval.behavioral_scorer --all --cache          # Cache-only (no provider calls)
    python3 -m lab.eval.behavioral_scorer --all --summary        # Summary only
    python3 -m lab.eval.behavioral_scorer --all --workers 4      # Parallel (~3-4x speedup)
    python3 -m lab.eval.behavioral_scorer --skill plan --rotations 5  # Order-bias control
    python3 -m lab.eval.behavioral_scorer --skill plan --samples 3    # pass@k robustness

Cost: Ollama runs locally at $0. Future cloud providers (e.g., Microsoft
Waza) plug into the same dispatch and add their own per-call cost notes.
"""


import argparse
import atexit
import dataclasses
import hashlib
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import traceback
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from . import results_dir as rd
from .results_dir import SUPPORTED_PROVIDERS
from .trigger_scorer import (
    load_all_routing_descriptions,
    load_hidden_skills,
    load_trigger_file,
    routing_descriptions_blob,
    RoutingDescription,
    RoutingDescriptions,
    routing_description_text,
)

log = logging.getLogger("behavioral_scorer")


# Provider and results directory live in lab.eval.results_dir as the single
# source of truth. Readers/writers here call rd.get_active_provider() and
# rd.active_results_dir() at use-sites so CLI --provider flips and env-var
# overrides propagate without per-module synchronization.

_ROUTING_SYSTEM_PROMPT = (
    "You are a skill router. Given a list of skills and a user message, "
    "reply with ONLY the skill name(s) that should be loaded, one per line. "
    "If none, reply with the single word 'none'. List at most 3, ordered by relevance. "
    "NEVER add explanations, code examples, or commentary. Output ONLY skill names or 'none'."
)

ROUTING_PROMPT_VERSION = "description_only_v1"
ROUTING_FIELDS = ("description",)


@dataclasses.dataclass(frozen=True, slots=True)
class ProviderSettings:
    model: str
    prompt_policy: str
    description_limit: int | None = None


# Pluggable provider table. Add a new provider by appending its name to
# `results_dir.SUPPORTED_PROVIDERS`, adding a ProviderSettings entry here,
# and adding a dispatch branch in `_run_provider`.
_PROVIDER_SETTINGS: dict[str, ProviderSettings] = {
    "ollama": ProviderSettings(
        model=rd.DEFAULT_OLLAMA_MODEL,
        prompt_policy="full",
    ),
}


def _provider_settings(provider: str | None = None) -> ProviderSettings:
    """Return active provider settings, resolving dynamic model defaults."""
    provider_name = provider or rd.get_active_provider()
    settings = _PROVIDER_SETTINGS[provider_name]
    if provider_name == "ollama":
        return dataclasses.replace(settings, model=rd.resolve_ollama_model())
    return settings


@dataclasses.dataclass(slots=True)
class CallResult:
    """Result from a single provider call."""

    skills: list[str] | None
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    # Machine-readable error category. Both providers emit the same canonical
    # set: "budget", "max_turns", "parse_error", "timeout", "context_overflow",
    # "guardrail_blocked", "server_unavailable", "dependency_missing",
    # "rate_limited", "unknown", or None on success. Intentionally extensible —
    # new categories may appear; callers should not assume this list is
    # exhaustive and should fall through to a generic bucket.
    error_type: str | None = None


# Alias kept for internal call-sites; canonical definition is in trigger_scorer.
_routing_descriptions_blob = routing_descriptions_blob


_TRIGGER_DATA_UNSET = object()


def content_hash(
    skill_name: str,
    descriptions: RoutingDescriptions,
    descriptions_blob: str | None = None,
    trigger_data=_TRIGGER_DATA_UNSET,
) -> str:
    """Hash routing descriptions + one skill's trigger corpus for cache invalidation."""
    desc_blob = (
        descriptions_blob
        if descriptions_blob is not None
        else _routing_descriptions_blob(descriptions)
    )
    if trigger_data is _TRIGGER_DATA_UNSET:
        trigger_data = load_trigger_file(skill_name)
    corpus = json.dumps(trigger_data, sort_keys=True) if trigger_data else ""
    combined = f"{ROUTING_PROMPT_VERSION}\n{desc_blob}\n---\n{corpus}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def _truncate_for_prompt(text: str, limit: int | None) -> str:
    """Truncate one prompt field to at most limit chars, preserving readability."""
    text = text.strip()
    if limit is None or len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return text[: limit - 3].rstrip() + "..."


def _format_routing_description_for_prompt(
    value: RoutingDescription,
    settings: ProviderSettings,
) -> str:
    """Format one skill's routing text for the active provider prompt policy."""
    if isinstance(value, Mapping):
        desc = str(value.get("description", "")).strip()
        if settings.prompt_policy == "strip_to_size":
            desc = _truncate_for_prompt(desc, settings.description_limit)
        return desc

    text = routing_description_text(value)
    if settings.prompt_policy == "strip_to_size":
        return _truncate_for_prompt(text, settings.description_limit)
    return text


def build_routing_prompt(
    descriptions: RoutingDescriptions,
    user_prompt: str,
    rotation: int = 0,
    prompt_policy: str | None = None,
) -> str:
    """Build the routing prompt for the active provider.

    System-level instructions are in _ROUTING_SYSTEM_PROMPT (passed via --system-prompt).
    This function builds only the user-turn content: skill list + user message.

    rotation: cyclic shift offset for the sorted skill list (0 = default order).
    """
    items = sorted(descriptions.items())
    if rotation and items:
        rotation = rotation % len(items)
        items = items[rotation:] + items[:rotation]
    settings = _provider_settings()
    if prompt_policy is not None and prompt_policy != settings.prompt_policy:
        settings = dataclasses.replace(settings, prompt_policy=prompt_policy)
    desc_list = "\n".join(
        f"- {name}: {_format_routing_description_for_prompt(desc, settings)}"
        for name, desc in items
    )
    return f'Available skills:\n{desc_list}\n\nThe user says: "{user_prompt}"'


def _prompt_limits(settings: ProviderSettings) -> dict[str, int | None]:
    """Return prompt-size limits that affect cache compatibility."""
    return {
        "description": settings.description_limit,
    }


def _cache_profile(settings: ProviderSettings | None = None) -> dict:
    """Return provider/model/prompt metadata that defines cache compatibility."""
    settings = settings or _provider_settings()
    return {
        "provider": rd.get_active_provider(),
        "model": settings.model,
        "cache_namespace": rd.get_active_cache_namespace(),
        "routing_fields": list(ROUTING_FIELDS),
        "routing_prompt_version": ROUTING_PROMPT_VERSION,
        "prompt_policy": settings.prompt_policy,
        "prompt_limits": _prompt_limits(settings),
    }


def _cache_profile_matches(
    cached: dict,
    expected_hash: str,
    settings: ProviderSettings | None = None,
) -> bool:
    """Return True when a cached artifact matches current routing semantics."""
    if cached.get("content_hash") != expected_hash:
        return False
    profile = _cache_profile(settings)
    return all(cached.get(key) == value for key, value in profile.items())


# Global executor reference for signal handler cleanup
_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()

# Shared stderr logging helpers moved to lab/eval/eval_logging.py so
# epistemic_suite (and any future eval tool) can reuse the same verbose-
# output semantics without duplicating the logic. Local underscore-prefixed
# aliases preserve the existing ~16 call sites without churn.
from .eval_logging import emit_info as _emit_info, verbose_lock as _verbose_lock


def _normalize_openai_compatible_base_url(url: str) -> str:
    """Normalize an OpenAI-compatible base URL for urlsplit parsing.

    Users commonly set values like ``127.0.0.1:11434/v1`` or
    ``localhost:11434/v1`` (no scheme). urlsplit mis-parses both — the first
    yields empty netloc, the second treats ``localhost`` as the scheme.
    Prepend ``http://`` when no scheme is present so the rest of the module
    (health-URL derivation, loopback detection) sees a well-formed URL.

    Raises RuntimeError if the result still has no host — clearer than
    producing a mangled ``http:///health`` later.
    """
    import urllib.parse

    candidate = url if "://" in url else f"http://{url}"
    parsed = urllib.parse.urlsplit(candidate)
    if not parsed.hostname:
        raise RuntimeError(
            f"Invalid OpenAI-compatible base URL {url!r}: could not parse host. "
            f"Expected form: http://host:port/v1"
        )
    return candidate


_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


_ollama_client = None
_ollama_server_proc = None
_ollama_stderr_path: str | None = None
_ollama_server_lock = threading.Lock()
_ollama_client_lock = threading.Lock()
_ollama_models_lock = threading.Lock()
_ollama_base_url_cache: str | None = None
_ollama_models_checked: set[str] = set()


def _normalize_ollama_base_url(url: str) -> str:
    """Normalize Ollama's OpenAI-compatible base URL.

    Accepts bare hosts (``127.0.0.1:11434``), root URLs, proxied prefixes,
    and explicit ``/v1`` URLs. OpenAI client calls need the ``/v1`` suffix,
    so any path that lacks it gets it appended.
    """
    import urllib.parse

    try:
        candidate = _normalize_openai_compatible_base_url(url)
    except RuntimeError as exc:
        raise RuntimeError(
            f"Invalid RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL {url!r}: could not "
            "parse host. Expected form: http://host:port/v1"
        ) from exc
    parsed = urllib.parse.urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(
            f"Invalid RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL {url!r}: scheme must "
            "be http or https."
        )
    path = (parsed.path or "").rstrip("/")
    if path in {"", "/"}:
        path = "/v1"
    elif not path.endswith("/v1"):
        path = f"{path}/v1"
    return urllib.parse.urlunsplit(
        (parsed.scheme or "http", parsed.netloc, path, "", "")
    )


def _get_ollama_base_url() -> str:
    """Return the normalized OpenAI-compatible Ollama base URL."""
    global _ollama_base_url_cache
    if _ollama_base_url_cache is None:
        raw = os.environ.get(
            "RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL",
            "http://127.0.0.1:11434/v1",
        )
        _ollama_base_url_cache = _normalize_ollama_base_url(raw)
    return _ollama_base_url_cache


def _derive_health_url(base_url: str) -> str:
    """Derive a /health URL from an OpenAI-style base URL.

    Strips a trailing /v1 (the OpenAI chat endpoint path) and replaces it with
    /health so the probe hits the same host:port the client will talk to.
    Accepts ``/v1``, ``/v1/``, trailing-slash variants, and bare hosts.
    """
    import urllib.parse

    parsed = urllib.parse.urlsplit(base_url)
    # Strip trailing slashes once so /v1/ and /v1 are handled symmetrically.
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/v1"):
        health_path = path[:-3] + "/health"
    elif path:
        health_path = path + "/health"
    else:
        health_path = "/health"
    return urllib.parse.urlunsplit(
        (
            parsed.scheme or "http",
            parsed.netloc,
            health_path,
            "",
            "",
        )
    )


def _is_loopback_base_url(base_url: str) -> bool:
    """Return True when base_url points at a local provider we may auto-spawn."""
    import urllib.parse

    host = urllib.parse.urlsplit(base_url).hostname
    return host in _LOOPBACK_HOSTS


def _derive_ollama_api_url(base_url: str, api_path: str) -> str:
    """Derive an Ollama native API URL from an OpenAI-style base URL."""
    import urllib.parse

    parsed = urllib.parse.urlsplit(base_url)
    path = (parsed.path or "").rstrip("/")
    if path.endswith("/v1"):
        root = path[:-3]
    else:
        root = path if path not in {"", "/"} else ""
    api_path = api_path if api_path.startswith("/") else f"/{api_path}"
    return urllib.parse.urlunsplit(
        (
            parsed.scheme or "http",
            parsed.netloc,
            f"{root}{api_path}",
            "",
            "",
        )
    )


def _stop_ollama_server():
    """Kill Ollama server if this process started it."""
    global _ollama_server_proc, _ollama_stderr_path
    proc = _ollama_server_proc
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
    finally:
        _ollama_server_proc = None
        if _ollama_stderr_path is not None:
            try:
                os.unlink(_ollama_stderr_path)
            except OSError:
                pass
            _ollama_stderr_path = None


def _ensure_ollama_server():
    """Start ``ollama serve`` if the configured local endpoint is not running."""
    global _ollama_server_proc, _ollama_stderr_path
    import tempfile
    import time
    import urllib.parse
    import urllib.request
    import urllib.error

    base_url = _get_ollama_base_url()
    url_parts = urllib.parse.urlsplit(base_url)
    version_url = _derive_ollama_api_url(base_url, "/api/version")
    is_localhost = _is_loopback_base_url(base_url)

    if is_localhost:
        if url_parts.scheme != "http":
            raise RuntimeError(
                f"Unsupported localhost RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL "
                f"scheme {url_parts.scheme!r}. Local Ollama auto-spawn "
                "requires an http URL such as 'http://localhost:11434' or "
                "'http://localhost:11434/v1'. Use a non-loopback HTTPS URL "
                "only for a remote/proxied Ollama service you manage."
            )
        normalized_path = (url_parts.path or "").rstrip("/") or "/"
        if normalized_path not in {"/", "/v1"}:
            raise RuntimeError(
                f"Unsupported localhost RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL path "
                f"prefix {url_parts.path!r}. Local Ollama auto-spawn only works "
                "with a root base URL such as 'http://localhost:11434' or "
                "'http://localhost:11434/v1'."
            )

    with _ollama_server_lock:
        if _ollama_server_proc is not None:
            if _ollama_server_proc.poll() is None:
                return
            log.warning("Cached Ollama server process exited; restarting.")
            _ollama_server_proc = None

        try:
            with urllib.request.urlopen(version_url, timeout=2):
                # Ollama is already running — started externally (Ollama.app
                # GUI, a separate `ollama serve`, or a remote instance). The
                # `OLLAMA_FLASH_ATTENTION=1` + `OLLAMA_KV_CACHE_TYPE=q8_0`
                # env vars the eval suite sets on autostart are SERVER-SIDE:
                # the external process was started without them, and we
                # can't inject them via the API. Evals still work — they
                # just run with whatever KV precision that server was
                # configured with. Warn once so the contributor knows why
                # per-run memory footprint might be higher than expected.
                _emit_info(
                    f"Ollama already running at {version_url} (not spawned "
                    "by this process). OLLAMA_FLASH_ATTENTION, "
                    "OLLAMA_KV_CACHE_TYPE, OLLAMA_NUM_PARALLEL, and "
                    "OLLAMA_MAX_LOADED_MODELS env vars will NOT apply — "
                    "they must be set BEFORE `ollama serve` starts. "
                    "Consequences: KV cache runs at whatever precision the "
                    "external server was started with, and --workers > 1 "
                    "queues at the server instead of running in parallel "
                    "unless the external server was launched with "
                    "OLLAMA_NUM_PARALLEL > 1. To enable both, stop the "
                    "external server first (e.g. kill Ollama.app / "
                    "`killall ollama`) and re-run so this script "
                    "autostarts the daemon with the eval-tuned env."
                )
                return
        except (urllib.error.URLError, OSError):
            pass

        if not is_localhost:
            raise RuntimeError(
                f"Remote Ollama at {version_url} is unreachable. "
                "Start the remote server or unset RUBY_PLUGIN_EVAL_OLLAMA_BASE_URL "
                "to auto-spawn locally."
            )

        ollama_host = url_parts.hostname
        ollama_port = str(url_parts.port) if url_parts.port is not None else "11434"
        if ollama_host is None:
            raise RuntimeError(
                f"Cannot auto-start local Ollama for malformed base URL: "
                f"{base_url!r}."
            )

        stderr_fd, stderr_path = tempfile.mkstemp(
            prefix="ollama-stderr-", suffix=".log"
        )
        _ollama_stderr_path = stderr_path
        env = dict(os.environ)
        env["OLLAMA_HOST"] = f"{ollama_host}:{ollama_port}"
        # Plugin-spawned ollama daemons get flash-attention + quantized KV cache
        # for lower memory pressure during eval. Do not set globally — applies
        # only when behavioral_scorer starts the server itself.
        env.setdefault("OLLAMA_FLASH_ATTENTION", "1")
        env.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
        # Without OLLAMA_NUM_PARALLEL, ollama defaults to single-concurrent
        # request per loaded model — ThreadPoolExecutor workers > 1 queue at
        # the server instead of running in parallel. Default 4 matches modern
        # Ollama; each extra parallel slot adds KV cache overhead so users
        # with tight VRAM can override (e.g. OLLAMA_NUM_PARALLEL=1 for the
        # low-RAM fallback).
        env.setdefault("OLLAMA_NUM_PARALLEL", "4")
        env.setdefault("OLLAMA_MAX_LOADED_MODELS", "1")
        _emit_info(f"Starting ollama serve on {env['OLLAMA_HOST']} ...")
        try:
            _ollama_server_proc = subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=stderr_fd,
                env=env,
            )
        except FileNotFoundError as exc:
            try:
                os.unlink(stderr_path)
            except OSError:
                pass
            _ollama_stderr_path = None
            raise RuntimeError(
                "Failed to start Ollama server: 'ollama' was not found on PATH. "
                "Install Ollama from https://ollama.com."
            ) from exc
        except OSError as exc:
            try:
                os.unlink(stderr_path)
            except OSError:
                pass
            _ollama_stderr_path = None
            raise RuntimeError(
                f"Failed to start Ollama server with 'ollama serve': {exc}. "
                "Check that the ollama binary is executable."
            ) from exc
        finally:
            os.close(stderr_fd)
        atexit.register(_stop_ollama_server)

        def _read_ollama_stderr_tail(limit: int = 1000) -> str:
            try:
                with open(stderr_path, encoding="utf-8", errors="replace") as fh:
                    data = fh.read()
            except OSError:
                return ""
            tail = data[-limit:]
            if len(data) > limit:
                tail = f"...\n{tail}"
            return tail.strip()

        for _ in range(30):
            exit_code = _ollama_server_proc.poll()
            if exit_code is not None:
                stderr_tail = _read_ollama_stderr_tail()
                _stop_ollama_server()
                msg = (
                    f"ollama serve exited with code {exit_code} before "
                    f"becoming ready."
                )
                if stderr_tail:
                    msg += f" stderr tail:\n{stderr_tail}"
                raise RuntimeError(msg)
            try:
                with urllib.request.urlopen(version_url, timeout=1):
                    _emit_info("Ollama server ready.")
                    return
            except (urllib.error.URLError, OSError):
                time.sleep(0.5)

        stderr_tail = _read_ollama_stderr_tail()
        _stop_ollama_server()
        msg = "ollama serve failed to start within 15s"
        if stderr_tail:
            msg += f". stderr tail:\n{stderr_tail}"
        raise RuntimeError(msg)


def _ollama_model_aliases(model: str) -> set[str]:
    """Return equivalent Ollama model names for installed-model checks."""
    raw = model.strip()
    if not raw:
        return set()

    aliases = {raw, raw.rsplit("/", 1)[-1]}
    for name in tuple(aliases):
        if name.endswith(":latest"):
            aliases.add(name[: -len(":latest")])
        elif ":" not in name:
            aliases.add(f"{name}:latest")
    return {alias for alias in aliases if alias}


def _ensure_ollama_model_available() -> None:
    """Verify the configured Ollama model exists; never auto-pull models."""
    import urllib.request
    import urllib.error

    model = rd.resolve_ollama_model()
    with _ollama_models_lock:
        if model in _ollama_models_checked:
            return
        tags_url = _derive_ollama_api_url(_get_ollama_base_url(), "/api/tags")
        try:
            with urllib.request.urlopen(tags_url, timeout=5) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not list Ollama models at {tags_url}: {exc}") from exc
        model_aliases = _ollama_model_aliases(model)
        installed_aliases: set[str] = set()
        for item in payload.get("models", []):
            if not isinstance(item, dict):
                continue
            installed_model = str(item.get("name") or item.get("model") or "")
            installed_aliases.update(_ollama_model_aliases(installed_model))
        if not (model_aliases & installed_aliases):
            raise RuntimeError(
                f"Ollama model {model!r} is not installed. "
                f"Run: ollama pull {model}"
            )
        _ollama_models_checked.add(model)


def _get_ollama_client():
    """Lazy-init OpenAI client for Ollama's OpenAI-compatible endpoint."""
    global _ollama_client
    _ensure_ollama_server()
    _ensure_ollama_model_available()
    with _ollama_client_lock:
        if _ollama_client is None:
            try:
                from openai import OpenAI
                import httpx as _httpx
            except ImportError as exc:
                raise RuntimeError(
                    "openai and httpx packages required for Ollama provider. "
                    "Install: .venv/bin/pip install openai httpx"
                ) from exc
            _ollama_client = OpenAI(
                base_url=_get_ollama_base_url(),
                api_key="ollama",
                timeout=_httpx.Timeout(120.0, connect=5.0),
                max_retries=0,
            )
    return _ollama_client


def ollama_chat(
    system_prompt: str,
    user_prompt: str,
    *,
    max_tokens: int = 256,
    reasoning_effort: str = "none",
    timeout: float | None = None,
) -> str:
    """Single-shot Ollama chat call. Returns raw response text.

    Thin generic helper for callers that need a non-routing prompt
    (e.g. semantic-confusable-pairs generation, future tools). Reuses the
    same client + server lifecycle as run_ollama. Caller picks max_tokens
    + reasoning_effort to fit the task. Raises on transport errors.
    """
    model = rd.resolve_ollama_model()
    client = _get_ollama_client()
    create_kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "extra_body": {"reasoning_effort": reasoning_effort},
    }
    if timeout is not None:
        create_kwargs["timeout"] = timeout
    resp = client.chat.completions.create(**create_kwargs)
    return (resp.choices[0].message.content or "").strip()


def run_ollama(
    prompt: str, verbose: bool = False, log_buf: list[str] | None = None
) -> CallResult:
    """Ask the configured local Ollama model which skill(s) to route to."""

    def _log(msg: str) -> None:
        if log_buf is not None:
            log_buf.append(msg)
        else:
            _emit_info(msg)

    model = rd.resolve_ollama_model()
    try:
        client = _get_ollama_client()
        # reasoning_effort=none disables hidden thinking output on
        # Gemma4 26b+ / other reasoning-capable models. Skill routing is a
        # simple classification task (list up to 3 skill names). Without
        # this, thinking burns the entire max_tokens=64 budget and the
        # returned content is empty.
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
            max_tokens=64,
            extra_body={"reasoning_effort": "none"},
        )
        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        if verbose:
            _log(f"--- OLLAMA RESPONSE ({model}, local, $0, {in_tok}in/{out_tok}out) ---")
            _log(text.strip() or "(empty)")
            _log("--- END RESPONSE ---")

        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                line
                for line in cleaned.split("\n")
                if not line.strip().startswith("```")
            )

        skills = []
        seen: set[str] = set()
        for line in cleaned.strip().split("\n"):
            line = line.strip().lstrip("-*0123456789.) ").strip()
            if " — " in line:
                line = line.split(" — ")[0].strip()
            if " (" in line:
                line = line.split(" (")[0].strip()
            if " -" in line:
                line = line.split(" -")[0].strip()
            line = line.strip("`").strip()
            if (
                line
                and line.lower() != "none"
                and not line.startswith("No ")
                and line not in seen
            ):
                skills.append(line)
                seen.add(line)
        return CallResult(
            skills=skills, cost=0.0, input_tokens=in_tok, output_tokens=out_tok
        )

    except Exception as exc:
        exc_str = str(exc)
        exc_lower = exc_str.lower()
        error_type = "unknown"
        if (
            isinstance(exc, (ModuleNotFoundError, ImportError))
            or "openai and httpx" in exc_lower
            or ("ollama" in exc_lower and "not found on path" in exc_lower)
            or "not installed" in exc_lower
            or "ollama pull" in exc_lower
        ):
            error_type = "dependency_missing"
        elif "remote ollama" in exc_lower and "unreachable" in exc_lower:
            error_type = "server_unavailable"
        elif "context" in exc_lower or "overflow" in exc_lower:
            error_type = "context_overflow"
        elif "timed out" in exc_lower or "timeout" in exc_lower:
            error_type = "timeout"
        elif "rate" in exc_lower and "limit" in exc_lower:
            error_type = "rate_limited"
        elif "connection" in exc_lower or "refused" in exc_lower:
            error_type = "server_unavailable"
        if verbose:
            _log(f"--- OLLAMA ERROR ({error_type}) ---")
            _log(exc_str[:300])
            _log("--- END ---")
        return CallResult(skills=None, error_type=error_type)


def _run_provider(
    prompt: str, verbose: bool = False, log_buf: list[str] | None = None
) -> CallResult:
    """Dispatch to the active provider.

    To add a provider, extend `results_dir.SUPPORTED_PROVIDERS`, add a
    `_PROVIDER_SETTINGS` entry, and add a dispatch branch below that calls
    the provider's run_* helper (which should return a CallResult).
    """
    provider = rd.get_active_provider()
    if provider == "ollama":
        return run_ollama(prompt, verbose=verbose, log_buf=log_buf)
    return CallResult(skills=None, error_type="unknown")


def extract_prompt(item) -> str:
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        return str(item.get("prompt", "")).strip()
    return ""


def _extract_prompt_meta(item) -> dict:
    """Extract prompt text and optional routing metadata from a trigger item."""
    if isinstance(item, str):
        return {"prompt": item.strip(), "routing": None, "valid_skills": []}
    if isinstance(item, dict):
        return {
            "prompt": str(item.get("prompt", "")).strip(),
            "routing": item.get("routing"),
            "valid_skills": item.get("valid_skills", []),
        }
    return {"prompt": "", "routing": None, "valid_skills": []}


def _check_correct(
    skill_name: str,
    chosen: list[str],
    expected: bool,
    routing: str | None,
    valid_skills: list[str],
) -> bool:
    """Single source of truth for per-prompt correctness."""
    if not expected:
        return skill_name not in chosen
    if routing == "fork" and valid_skills:
        return any(s in chosen for s in valid_skills)
    return skill_name in chosen


def _run_single_prompt(
    skill_name: str,
    item,
    index: int,
    total: int,
    descriptions: RoutingDescriptions,
    expected: bool,
    tier: str,
    verbose: bool = False,
    parallel: bool = False,
    rotation: int = 0,
) -> dict | None:
    """Run one prompt item. Returns result dict, {"_failure": True} on provider failure, or None on skip.

    rotation: cyclic shift offset for the skill list (0 = default sorted order).
    """
    meta = _extract_prompt_meta(item)
    prompt = meta["prompt"]
    if not prompt:
        return None
    label = "should_trigger" if expected else "should_not"
    routing = meta["routing"]
    routing_tag = f" [{routing}]" if routing and routing != "lock" else ""
    rot_tag = f" r{rotation}" if rotation else ""
    header = f"  [{skill_name} {label}({tier}){routing_tag}{rot_tag} {index}/{total}] {prompt}"

    if verbose and not parallel:
        _emit_info(header)

    log_lines: list[str] = []
    if verbose and parallel:
        log_lines.append(header)

    full_prompt = build_routing_prompt(descriptions, prompt, rotation=rotation)
    call_result = _run_provider(
        full_prompt, verbose=verbose, log_buf=log_lines if parallel else None
    )
    chosen = call_result.skills

    if chosen is None:
        if verbose:
            error_hint = (
                f" [{call_result.error_type}]" if call_result.error_type else ""
            )
            log_lines.append(
                f"  -> SKIPPED ({rd.get_active_provider()} call failed{error_hint})"
            )
            if parallel:
                with _verbose_lock:
                    for line in log_lines:
                        _emit_info(line)
            else:
                _emit_info(log_lines[-1])
        return {"_failure": True, "_call_result": call_result}

    correct = _check_correct(
        skill_name, chosen, expected, meta["routing"], meta["valid_skills"]
    )
    status = "OK" if correct else ("MISS" if expected else "FALSE_POS")
    result_line = f"  -> chosen={chosen} [{status}]"

    if verbose:
        log_lines.append(result_line)
        if parallel:
            with _verbose_lock:
                for line in log_lines:
                    _emit_info(line)
        else:
            _emit_info(result_line)

    result_entry = {
        "prompt": prompt,
        "expected": expected,
        "chosen": chosen,
        "correct": correct,
        "tier": tier,
        "routing": meta["routing"],
        "_call_result": call_result,
    }
    if call_result.error_type:
        result_entry["error_type"] = call_result.error_type
    return result_entry


def _run_prompt_batch(
    skill_name: str,
    flat_items: list[tuple],
    descriptions: RoutingDescriptions,
    verbose: bool = False,
    workers: int = 1,
) -> tuple[list[dict], int, list[CallResult]]:
    """Run a flat list of (item, expected, tier, rotation, run_index, prompt_id) tuples.

    Returns (results, failure_count, call_results).
    One executor pool for all items — keeps workers saturated across tiers.
    """
    global _executor
    results = []
    failures = 0
    call_results: list[CallResult] = []
    parallel = workers > 1
    total = len(flat_items)

    def _collect(result: dict | None, run_index: int = 0, prompt_id: int = 0) -> None:
        nonlocal failures
        if result is None:
            return
        cr = result.pop("_call_result", None)
        if cr:
            call_results.append(cr)
        if result.get("_failure"):
            failures += 1
        else:
            result["run_index"] = run_index
            result["prompt_id"] = prompt_id
            results.append(result)

    if not parallel:
        for i, (item, expected, tier, rotation, run_index, pid) in enumerate(
            flat_items, 1
        ):
            result = _run_single_prompt(
                skill_name,
                item,
                i,
                total,
                descriptions,
                expected,
                tier,
                verbose,
                parallel=False,
                rotation=rotation,
            )
            _collect(result, run_index, pid)
        return results, failures, call_results

    # Parallel path: one executor for all prompts, collect in submission order
    errors: list[str] = []
    meta_per_future: list[tuple[int, int]] = []  # (run_index, prompt_id)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        with _executor_lock:
            _executor = executor
        try:
            futures = []
            for i, (item, expected, tier, rotation, run_index, pid) in enumerate(
                flat_items, 1
            ):
                future = executor.submit(
                    _run_single_prompt,
                    skill_name,
                    item,
                    i,
                    total,
                    descriptions,
                    expected,
                    tier,
                    verbose,
                    True,
                    rotation,
                )
                futures.append(future)
                meta_per_future.append((run_index, pid))

            for idx, future in enumerate(futures):
                try:
                    result = future.result()
                except Exception as exc:
                    failures += 1
                    errors.append(f"{type(exc).__name__}: {exc}")
                    if verbose:
                        with _verbose_lock:
                            _emit_info(traceback.format_exc())
                    continue
                ri, pid = meta_per_future[idx]
                _collect(result, ri, pid)
        finally:
            with _executor_lock:
                _executor = None

    if errors and not verbose:
        # Non-verbose path: the caller printed "  Testing {name}... " with
        # end=" ", so a timestamped log.warning would interleave mid-line.
        # Start on a fresh line and use plain stderr (matches the SKIPPED
        # branch in main()).
        print(
            f"\n  {len(errors)} worker failures: {', '.join(set(errors))}",
            file=sys.stderr,
            flush=True,
        )

    return results, failures, call_results


def _count_failure_types(call_results: list[CallResult]) -> dict[str, int]:
    """Count failures by error_type from call results."""
    counts: dict[str, int] = {}
    for cr in call_results:
        if cr.skills is None and cr.error_type:
            counts[cr.error_type] = counts.get(cr.error_type, 0) + 1
    return dict(sorted(counts.items()))


def _compute_metrics(results: list[dict]) -> dict:
    """Compute accuracy/precision/recall from a list of result dicts."""
    total = len(results)
    if total == 0:
        return {
            "accuracy": 0.0,
            "precision": 1.0,
            "recall": 1.0,
            "total": 0,
            "correct": 0,
        }
    correct_count = sum(1 for r in results if r["correct"])
    tp = sum(1 for r in results if r["expected"] and r["correct"])
    fp = sum(1 for r in results if not r["expected"] and not r["correct"])
    fn = sum(1 for r in results if r["expected"] and not r["correct"])
    precision = tp / (tp + fp) if (tp + fp) > 0 else 1.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    accuracy = correct_count / total if total > 0 else 0.0
    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "total": total,
        "correct": correct_count,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def _majority_vote(booleans: list[bool]) -> bool:
    """Majority vote on booleans. Strict majority — fail on tie (conservative)."""
    return sum(1 for b in booleans if b) > len(booleans) / 2


def _aggregate_rotations(results: list[dict], num_rotations: int) -> list[dict]:
    """Collapse rotation-expanded results into majority-voted per-prompt results.

    Input: N*R results where each prompt appears R times (one per rotation).
    Output: N results with majority-voted correct, per_rotation_correct, per_rotation_choices.

    Missing rotations (failed calls) are treated as incorrect for majority vote.
    Uses rotation 0's chosen value when present; falls back to first successful
    rotation otherwise (chosen may not reflect the default ordering in that case).
    """
    from collections import defaultdict

    by_prompt: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        by_prompt[r.get("prompt_id", 0)].append(r)

    aggregated = []
    for _pid, group in sorted(by_prompt.items()):
        group.sort(key=lambda x: x.get("run_index", 0))
        # Build per-rotation arrays, padding missing rotations as incorrect
        per_rotation_correct = [False] * num_rotations
        per_rotation_choices: list[list[str] | None] = [None] * num_rotations
        for r in group:
            idx = r.get("run_index", 0)
            if 0 <= idx < num_rotations:
                per_rotation_correct[idx] = r["correct"]
                per_rotation_choices[idx] = r["chosen"]

        voted_correct = _majority_vote(per_rotation_correct)
        rot0 = next((r for r in group if r.get("run_index", 0) == 0), group[0])
        base = dict(rot0)
        base["correct"] = voted_correct
        base["chosen"] = rot0["chosen"]
        base["per_rotation_correct"] = per_rotation_correct
        base["per_rotation_choices"] = per_rotation_choices
        base.pop("run_index", None)
        base.pop("prompt_id", None)
        aggregated.append(base)
    return aggregated


def _aggregate_samples(results: list[dict], num_samples: int) -> list[dict]:
    """Collapse sample-expanded results into per-prompt results with pass@k.

    Output: N results with accuracy from sample 0, pass_at_k, sample_consistency.

    Uses run_index to identify each sample. If sample 0 failed and was dropped,
    correct defaults to False. Missing samples padded as incorrect.
    """
    from collections import defaultdict

    by_prompt: dict[int, list[dict]] = defaultdict(list)
    for r in results:
        by_prompt[r.get("prompt_id", 0)].append(r)

    aggregated = []
    for _pid, group in sorted(by_prompt.items()):
        # Index results by run_index for reliable sample identification
        by_index: dict[int, dict] = {}
        for r in group:
            idx = r.get("run_index", 0)
            by_index[idx] = r

        # Build per-sample array, padding missing samples as incorrect
        per_sample_correct = [
            by_index[i]["correct"] if i in by_index else False
            for i in range(num_samples)
        ]

        # Use sample 0 as canonical; fall back to first available if missing
        sample0 = by_index.get(0)
        if sample0 is not None:
            base = dict(sample0)
        elif group:
            base = dict(group[0])
            base["correct"] = False  # conservative: sample 0 is missing
            base["sample0_missing"] = True
        else:
            continue

        base["pass_at_k"] = any(per_sample_correct)
        base["per_sample_correct"] = per_sample_correct
        base["sample_consistency"] = all(
            c == per_sample_correct[0] for c in per_sample_correct
        )
        base.pop("run_index", None)
        base.pop("prompt_id", None)
        aggregated.append(base)
    return aggregated


def _result_filename(skill_name: str, rotations: int = 1, samples: int = 1) -> str:
    """Compute mode-specific result filename.

    Baseline (rotations=1, samples=1) uses {skill}.json for backward compat.
    Rotations mode uses {skill}_r{N}.json, samples mode uses {skill}_s{N}.json.
    This prevents modes from overwriting each other's cached results.
    """
    if rotations > 1:
        return f"{skill_name}_r{rotations}.json"
    if samples > 1:
        return f"{skill_name}_s{samples}.json"
    return f"{skill_name}.json"


def score_skill(
    skill_name: str,
    descriptions: RoutingDescriptions,
    use_cache: bool = False,
    verbose: bool = False,
    limit: int = 0,
    workers: int = 1,
    rotations: int = 1,
    samples: int = 1,
    descriptions_blob: str | None = None,
) -> tuple[dict, list[CallResult]]:
    """Score trigger accuracy for one skill. Returns (score_dict, call_results)."""
    if rotations > 1 and samples > 1:
        raise ValueError(
            "rotations and samples are mutually exclusive; only one may be > 1"
        )
    cache_path = rd.active_results_dir() / _result_filename(
        skill_name, rotations, samples
    )
    settings = _provider_settings()
    expected_hash: str | None = None

    if use_cache:
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {"skill": skill_name, "error": "corrupted cache file"}, []
            expected_hash = content_hash(skill_name, descriptions, descriptions_blob)
            if _cache_profile_matches(cached, expected_hash, settings):
                return cached, []
        return {"skill": skill_name, "error": "no valid cache (stale or missing)"}, []

    triggers = load_trigger_file(skill_name)
    if not triggers:
        return {"skill": skill_name, "error": "no trigger file"}, []
    if expected_hash is None:
        expected_hash = content_hash(
            skill_name,
            descriptions,
            descriptions_blob,
            trigger_data=triggers,
        )

    easy_trigger = triggers.get("should_trigger", [])
    easy_not = triggers.get("should_not_trigger", [])
    hard_trigger = triggers.get("hard_should_trigger", [])
    hard_not = triggers.get("hard_should_not_trigger", [])

    if limit > 0:
        easy_trigger = easy_trigger[:limit]
        easy_not = easy_not[:limit]
        hard_trigger = hard_trigger[:limit]
        hard_not = hard_not[:limit]

    # Build base prompt list with stable prompt_id for aggregation.
    # prompt_id is a sequential index across all buckets — survives even if
    # identical prompt text appears in different buckets (theoretically possible).
    base_items: list[tuple] = []
    prompt_id = 0
    for items, expected, tier in [
        (easy_trigger, True, "easy"),
        (easy_not, False, "easy"),
        (hard_trigger, True, "hard"),
        (hard_not, False, "hard"),
    ]:
        for item in items:
            base_items.append((item, expected, tier, prompt_id))
            prompt_id += 1

    # Expand for rotations or samples — each produces independent work items.
    # Tuple: (item, expected, tier, rotation, run_index, prompt_id)
    # For rotations: use strided offsets (BiasBusters method) for maximum positional spread.
    # With N rotations over L skills, stride = L // N. E.g., 5 rotations over L skills
    # gives offsets [0, L//5, 2*L//5, ...] — each skill shifts ~L/5 positions per rotation.
    multiplier = max(rotations, samples)
    num_skills = len(descriptions)
    rotation_stride = max(num_skills // rotations, 1) if rotations > 1 else 0
    flat_items: list[tuple] = []
    for rep in range(multiplier):
        run_index = rep if (rotations > 1 or samples > 1) else 0
        rotation = rep * rotation_stride if rotations > 1 else 0
        for item, expected, tier, pid in base_items:
            flat_items.append((item, expected, tier, rotation, run_index, pid))

    all_results, total_failures, all_call_results = _run_prompt_batch(
        skill_name,
        flat_items,
        descriptions,
        verbose=verbose,
        workers=workers,
    )

    if not all_results and total_failures > 0:
        # Surface the failure_types breakdown so the caller (main()'s SKIPPED
        # line, or programmatic consumers) can see at a glance why the run
        # failed without digging into per-call results. Matches the shape
        # attached to successful score_data at line ~1251.
        breakdown = _count_failure_types(all_call_results)
        base_msg = f"all {total_failures} {rd.get_active_provider()} calls failed"
        if breakdown:
            summary = ", ".join(
                f"{et}={n}" for et, n in sorted(
                    breakdown.items(), key=lambda it: (-it[1], it[0])
                )
            )
            error_msg = f"{base_msg} (failure_types: {summary})"
        else:
            error_msg = base_msg
        return {
            "skill": skill_name,
            "error": error_msg,
            "failure_types": breakdown,
            **_cache_profile(settings),
        }, all_call_results

    # Aggregate multi-run results
    if rotations > 1:
        all_results = _aggregate_rotations(all_results, rotations)
    elif samples > 1:
        all_results = _aggregate_samples(all_results, samples)

    # Overall metrics
    overall = _compute_metrics(all_results)

    # Tier-split metrics
    easy_results = [r for r in all_results if r.get("tier") == "easy"]
    hard_results = [r for r in all_results if r.get("tier") == "hard"]
    easy_metrics = _compute_metrics(easy_results)
    hard_metrics = _compute_metrics(hard_results)

    # Fork/lock metrics
    fork_results = [
        r
        for r in all_results
        if r.get("routing") == "fork" and r.get("expected") is True
    ]
    lock_results = [
        r
        for r in all_results
        if r.get("routing") == "lock" and r.get("expected") is True
    ]
    fork_metrics = _compute_metrics(fork_results)
    lock_metrics = _compute_metrics(lock_results)

    score_data = {
        "skill": skill_name,
        **_cache_profile(settings),
        **overall,
        "failures": total_failures,
        "failure_types": _count_failure_types(all_call_results),
        "easy_accuracy": easy_metrics["accuracy"],
        "easy_precision": easy_metrics["precision"],
        "easy_recall": easy_metrics["recall"],
        "hard_accuracy": hard_metrics["accuracy"],
        "hard_precision": hard_metrics["precision"],
        "hard_recall": hard_metrics["recall"],
        "fork_accuracy": fork_metrics["accuracy"],
        "lock_accuracy": lock_metrics["accuracy"],
        "tier_counts": {"easy": easy_metrics["total"], "hard": hard_metrics["total"]},
        "routing_counts": {
            "fork": fork_metrics["total"],
            "lock": lock_metrics["total"],
        },
        "content_hash": expected_hash,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": all_results,
    }

    # Rotation-specific metrics (P1b)
    if rotations > 1:
        per_rotation_acc = []
        for rot in range(rotations):
            rot_correct = []
            for r in all_results:
                prc = r.get("per_rotation_correct", [])
                if rot < len(prc):
                    rot_correct.append(prc[rot])
            if rot_correct:
                per_rotation_acc.append(round(sum(rot_correct) / len(rot_correct), 4))
        order_range = (
            round(max(per_rotation_acc) - min(per_rotation_acc), 4)
            if per_rotation_acc
            else 0.0
        )
        # correctness_consistency: all rotations agree on correct/incorrect verdict
        correctness_agree = sum(
            1
            for r in all_results
            if r.get("per_rotation_correct")
            and all(
                c == r["per_rotation_correct"][0] for c in r["per_rotation_correct"]
            )
        )
        # choice_consistency: all rotations return the same skill list
        choice_agree = sum(
            1
            for r in all_results
            if r.get("per_rotation_choices")
            and all(
                c == r["per_rotation_choices"][0]
                for c in r["per_rotation_choices"]
                if c is not None
            )
            and all(c is not None for c in r["per_rotation_choices"])
        )
        total_prompts = len(all_results)
        score_data["rotations"] = rotations
        score_data["per_rotation_accuracy"] = per_rotation_acc
        score_data["order_range"] = order_range
        score_data["order_stddev"] = (
            round(
                (
                    sum(
                        (a - sum(per_rotation_acc) / len(per_rotation_acc)) ** 2
                        for a in per_rotation_acc
                    )
                    / len(per_rotation_acc)
                )
                ** 0.5,
                4,
            )
            if per_rotation_acc
            else 0.0
        )
        score_data["order_sensitive"] = order_range > 0.15
        score_data["routing_consistency"] = (
            round(choice_agree / total_prompts, 4) if total_prompts else 0.0
        )
        score_data["correctness_consistency"] = (
            round(correctness_agree / total_prompts, 4) if total_prompts else 0.0
        )

    # Sample-specific metrics (P3)
    if samples > 1:
        pass_at_k_count = sum(1 for r in all_results if r.get("pass_at_k"))
        consistency_count = sum(1 for r in all_results if r.get("sample_consistency"))
        total_prompts = len(all_results)
        score_data["samples"] = samples
        score_data["pass_at_k"] = (
            round(pass_at_k_count / total_prompts, 4) if total_prompts else 0.0
        )
        score_data["sample_consistency"] = (
            round(consistency_count / total_prompts, 4) if total_prompts else 0.0
        )
        score_data["inconsistent_routing"] = (
            score_data["pass_at_k"] - score_data["accuracy"] > 0.15
        )

    # Write mode metadata for auditability
    score_data["mode"] = {
        "rotations": rotations,
        "samples": samples,
    }

    rd.active_results_dir().mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(score_data, indent=2) + "\n", encoding="utf-8")

    return score_data, all_call_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test skill trigger accuracy with Ollama Gemma4 (default)"
    )
    parser.add_argument("--skill", help="Test one skill")
    parser.add_argument(
        "--all", action="store_true", help="Test all skills with trigger files"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        help="Cache-only: use cached results, skip stale/missing (no provider calls)",
    )
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show prompt/response for each provider call",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        metavar="N",
        help="Test only first N should_trigger + N should_not_trigger prompts per skill",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        metavar="N",
        choices=range(1, 33),
        help="Parallel workers for provider calls (default 1, recommended 4)",
    )
    parser.add_argument(
        "--rotations",
        type=int,
        default=1,
        metavar="N",
        choices=range(1, 16),
        help="Cyclic rotations for order-bias control (default 1, recommended 5)",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=1,
        metavar="N",
        choices=range(1, 8),
        help="Independent samples for pass@k robustness (default 1, recommended 3)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        choices=sorted(SUPPORTED_PROVIDERS),
        help=(
            "Routing provider. Currently only `ollama` (local Gemma4 by "
            "default) is wired; future providers plug in via "
            "results_dir.SUPPORTED_PROVIDERS + _PROVIDER_SETTINGS + "
            "_run_provider. Default: RUBY_PLUGIN_EVAL_PROVIDER env var or ollama."
        ),
    )
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
    )

    if args.rotations > 1 and args.samples > 1:
        parser.error("--rotations and --samples are mutually exclusive (both > 1)")

    # Resolve provider after parsing so warnings only occur when actually needed
    rd.set_active_provider(args.provider)

    # Start local providers before workers (avoids race conditions in threads).
    # Skip for --cache (documented as "no provider calls" — pure filesystem reads).
    if not args.cache:
        if rd.get_active_provider() == "ollama":
            _ensure_ollama_server()
            _ensure_ollama_model_available()

    # Signal handler: cancel pending futures, wait for running workers.
    # Use non-blocking acquire — signal runs on main thread which may
    # already hold _executor_lock, so blocking would deadlock.
    def _shutdown_handler(signum, frame):
        global _executor
        executor = None
        acquired = _executor_lock.acquire(blocking=False)
        try:
            if acquired:
                executor = _executor
                _executor = None
        finally:
            if acquired:
                _executor_lock.release()
        if executor is not None:
            log.warning(
                "Interrupted — cancelling pending work, waiting for running workers."
            )
            executor.shutdown(wait=True, cancel_futures=True)
        raise SystemExit(130)

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    hidden_skills = load_hidden_skills()
    descriptions = {
        name: desc
        for name, desc in load_all_routing_descriptions().items()
        if name not in hidden_skills
    }
    descriptions_blob = _routing_descriptions_blob(descriptions)

    # Collect all CallResults for cost aggregation (single-threaded, no lock needed)
    all_call_results: list[CallResult] = []

    if args.skill:
        if args.skill in hidden_skills:
            raise SystemExit(
                f"skill {args.skill} is hidden (disable-model-invocation: true); "
                "behavioral routing scoring not applicable"
            )
        result, crs = score_skill(
            args.skill,
            descriptions,
            args.cache,
            verbose=args.verbose,
            limit=args.limit,
            workers=args.workers,
            rotations=args.rotations,
            samples=args.samples,
            descriptions_blob=descriptions_blob,
        )
        all_call_results.extend(crs)

        if args.summary:
            tier_str = ""
            tc = result.get("tier_counts", {})
            if tc.get("hard", 0) > 0:
                tier_str = (
                    f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                    f"hard: {result.get('hard_accuracy', 0):.0%})"
                )
            extra = ""
            if result.get("rotations", 1) > 1:
                extra = (
                    f" choice={result.get('routing_consistency', 0):.0%}"
                    f" correct={result.get('correctness_consistency', 0):.0%}"
                    f" range={result.get('order_range', 0):.2f}"
                )
                if result.get("order_sensitive"):
                    extra += " ORDER-SENSITIVE"
            if result.get("samples", 1) > 1:
                extra = (
                    f" pass@{result['samples']}={result.get('pass_at_k', 0):.0%}"
                    f" cons={result.get('sample_consistency', 0):.0%}"
                )
                if result.get("inconsistent_routing"):
                    extra += " INCONSISTENT"
            print(
                f"{args.skill}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                f"precision={result.get('precision', 0):.0%} "
                f"recall={result.get('recall', 0):.0%}{extra}"
            )
        else:
            print(json.dumps(result, indent=2 if args.pretty else None))

    elif args.all:
        skills_tested = 0
        total_accuracy = 0.0
        all_results = {}

        for name in sorted(descriptions.keys()):
            triggers = load_trigger_file(name)
            if not triggers:
                continue
            if args.verbose:
                log.info("  Testing %s...", name)
            else:
                print(f"  Testing {name}...", end=" ", flush=True, file=sys.stderr)
            result, crs = score_skill(
                name,
                descriptions,
                args.cache,
                verbose=args.verbose,
                limit=args.limit,
                workers=args.workers,
                rotations=args.rotations,
                samples=args.samples,
                descriptions_blob=descriptions_blob,
            )
            all_call_results.extend(crs)

            if "error" in result:
                if args.verbose:
                    log.warning("SKIPPED (%s)", result["error"])
                else:
                    # Non-verbose: "  Testing {name}... " was printed with end=" ",
                    # so finish the line cleanly instead of interleaving a
                    # timestamped log record mid-line.
                    print(f"SKIPPED ({result['error']})", file=sys.stderr, flush=True)
                continue
            all_results[name] = result
            total_accuracy += result.get("accuracy", 0)
            skills_tested += 1
            print(
                f"accuracy={result.get('accuracy', 0):.0%} "
                f"(P={result.get('precision', 0):.0%} "
                f"R={result.get('recall', 0):.0%})",
                file=sys.stderr,
                flush=True,
            )

        avg = total_accuracy / skills_tested if skills_tested else 0
        summary = f"{skills_tested} skills tested, average accuracy: {avg:.0%}"
        if args.verbose:
            log.info(summary)
        else:
            print(summary, file=sys.stderr, flush=True)

        if args.summary:
            for name, result in sorted(all_results.items()):
                tier_str = ""
                tc = result.get("tier_counts", {})
                if tc.get("hard", 0) > 0:
                    tier_str = (
                        f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                        f"hard: {result.get('hard_accuracy', 0):.0%})"
                    )
                extra = ""
                if result.get("rotations", 1) > 1:
                    extra = (
                        f" choice={result.get('routing_consistency', 0):.0%}"
                        f" correct={result.get('correctness_consistency', 0):.0%}"
                        f" range={result.get('order_range', 0):.2f}"
                    )
                    if result.get("order_sensitive"):
                        extra += " ORDER-SENSITIVE"
                if result.get("samples", 1) > 1:
                    extra = (
                        f" pass@{result['samples']}={result.get('pass_at_k', 0):.0%}"
                        f" cons={result.get('sample_consistency', 0):.0%}"
                    )
                    if result.get("inconsistent_routing"):
                        extra += " INCONSISTENT"
                print(
                    f"  {name}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                    f"P={result.get('precision', 0):.0%} "
                    f"R={result.get('recall', 0):.0%}{extra}"
                )
        else:
            settings = _provider_settings()
            aggregate = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                **_cache_profile(settings),
                "mode": {"rotations": args.rotations, "samples": args.samples},
                "skills_tested": skills_tested,
                "average_accuracy": round(avg, 4),
                "per_skill": {
                    k: {
                        "accuracy": v.get("accuracy", 0),
                        "precision": v.get("precision", 0),
                        "recall": v.get("recall", 0),
                    }
                    for k, v in all_results.items()
                },
            }
            aggregate_suffix = _result_filename(
                "_aggregate", args.rotations, args.samples
            )
            aggregate_path = rd.active_results_dir() / aggregate_suffix
            rd.active_results_dir().mkdir(parents=True, exist_ok=True)
            aggregate_path.write_text(
                json.dumps(aggregate, indent=2) + "\n", encoding="utf-8"
            )
            print(json.dumps(aggregate, indent=2 if args.pretty else None))

    else:
        parser.print_help()
        return

    # Cost summary — aggregated from CallResult objects (single-threaded, no lock).
    # Always surface to stderr so non-verbose runs still show it (logger is
    # configured at WARNING by default).
    if all_call_results:
        successful = [cr for cr in all_call_results if cr.skills is not None]
        failed = len(all_call_results) - len(successful)
        total_cost = sum(cr.cost for cr in successful)
        max_cost = max((cr.cost for cr in successful), default=0)
        avg_cost = total_cost / len(successful) if successful else 0
        cost_lines = [
            f"--- Cost Summary ({rd.get_active_provider()}) ---",
            f"  Total successful calls: {len(successful)}",
        ]
        if failed:
            cost_lines.append(f"  Failed calls:    {failed}")
        cost_lines.extend(
            [
                f"  Total cost:      ${total_cost:.4f}",
                f"  Max single call: ${max_cost:.4f}",
                f"  Avg per call:    ${avg_cost:.4f}",
                "--------------------",
            ]
        )
        if args.verbose:
            for line in cost_lines:
                log.info(line)
        else:
            for line in cost_lines:
                print(line, file=sys.stderr, flush=True)

    # Temp settings cleanup handled by atexit (also fires on SIGINT/SystemExit)


if __name__ == "__main__":
    main()
