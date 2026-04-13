"""Behavioral trigger evaluation.

Tests whether Claude routes user prompts to the correct skill by sending all
skill descriptions + one test prompt to the active provider (apfel on-device
by default, haiku via the Claude API as an alternative).

Usage:
    python3 -m lab.eval.behavioral_scorer --skill plan          # Test one skill
    python3 -m lab.eval.behavioral_scorer --all                  # Test all skills with triggers
    python3 -m lab.eval.behavioral_scorer --all --cache          # Cache-only (no API calls)
    python3 -m lab.eval.behavioral_scorer --all --summary        # Summary only
    python3 -m lab.eval.behavioral_scorer --all --workers 4      # Parallel (~3-4x speedup)
    python3 -m lab.eval.behavioral_scorer --skill plan --rotations 5  # Order-bias control
    python3 -m lab.eval.behavioral_scorer --skill plan --samples 3    # pass@k robustness

Cost: Uses --bare mode (~$0.006/call avg, varies by skill complexity).
Full 51-skill run (621 prompts): ~$3.70 single-shot, ~$19 with rotations 5, ~$11 with samples 3.
"""

from __future__ import annotations

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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from .results_dir import (
    SUPPORTED_PROVIDERS,
    resolve_provider,
    results_dir,
)
from .trigger_scorer import load_all_descriptions, load_trigger_file, TRIGGERS_DIR

log = logging.getLogger("behavioral_scorer")


# Active provider — CLI --provider flag wins, RUBY_PLUGIN_EVAL_PROVIDER env var
# is the fallback, DEFAULT_PROVIDER is last resort. Resolving through
# resolve_provider() keeps the writer in lockstep with readers
# (dimensions/behavioral.py, eval_sensitivity.py) that also honor the env var.
_provider: str = resolve_provider(None)


# Canonical results directory used for all cache I/O.
#
# Provider-scoped so callers importing/patching RESULTS_DIR (neighbor_regression,
# tests) read and write to the same location that score_skill writes to. Kept
# in sync with _provider by main() when the CLI --provider flag changes it.
RESULTS_DIR = results_dir(_provider)


def _results_dir() -> Path:
    """Return the active results directory used for cache I/O."""
    return RESULTS_DIR

# Resolved settings path — defaults to bare_settings.json, replaced by
# _resolve_settings() at startup when a temp auth settings file is needed.
_resolved_settings_path: str = str(TRIGGERS_DIR.parent / "bare_settings.json")

_ROUTING_SYSTEM_PROMPT = (
    "You are a skill router. Given a list of skills and a user message, "
    "reply with ONLY the skill name(s) that should be loaded, one per line. "
    "If none, reply with the single word 'none'. List at most 3, ordered by relevance. "
    "NEVER add explanations, code examples, or commentary. Output ONLY skill names or 'none'."
)


_RESOLVED_TOKEN_ENV = "_RUBY_PLUGIN_RESOLVED_TOKEN"


def _resolve_settings() -> str:
    """Resolve auth settings for bare mode.

    If bare_settings.json uses apiKeyHelper, extract the token once and write
    a temp settings file whose apiKeyHelper reads from an env var instead of
    hitting the keychain. This avoids concurrent keychain access with --workers > 1.

    Sets the token as an env var so all worker subprocesses inherit it.
    Returns the path to use with --settings.
    """
    import tempfile

    base_path = TRIGGERS_DIR.parent / "bare_settings.json"
    if not base_path.is_file():
        return str(base_path)

    try:
        settings = json.loads(base_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return str(base_path)

    helper = settings.get("apiKeyHelper")
    if not helper:
        return str(base_path)

    # Run the original helper once to get the token
    try:
        result = subprocess.run(
            ["/bin/sh", "-c", helper],
            capture_output=True, text=True, timeout=10,
        )
        token = result.stdout.strip()
        if not token or result.returncode != 0:
            log.warning("apiKeyHelper failed, falling back to per-call helper")
            return str(base_path)
    except Exception as exc:
        log.warning("apiKeyHelper failed (%s), falling back to per-call helper", exc)
        return str(base_path)

    # Set token in env — inherited by all subprocess workers
    os.environ[_RESOLVED_TOKEN_ENV] = token

    # Write temp settings to OS temp dir (avoids repo pollution on SIGKILL)
    # Use printf to avoid echo mangling tokens starting with -n etc.
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", prefix="bare_resolved_", delete=False,
    )
    settings["apiKeyHelper"] = f'printf %s "${_RESOLVED_TOKEN_ENV}"'
    json.dump(settings, tmp)
    tmp.close()
    return tmp.name


@dataclasses.dataclass(slots=True)
class CallResult:
    """Result from a single provider call."""
    skills: list[str] | None
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    # One of: "budget", "max_turns", "parse_error", "timeout", "context_overflow",
    # "guardrail_blocked", "server_unavailable", "unknown", or None on success.
    error_type: str | None = None


def content_hash(skill_name: str, descriptions: dict[str, str]) -> str:
    """Hash skill description + trigger corpus for cache invalidation."""
    desc = descriptions.get(skill_name, "")
    trigger_data = load_trigger_file(skill_name)
    corpus = json.dumps(trigger_data, sort_keys=True) if trigger_data else ""
    combined = f"{desc}\n---\n{corpus}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


def build_routing_prompt(
    descriptions: dict[str, str],
    user_prompt: str,
    rotation: int = 0,
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
    desc_list = "\n".join(
        f"- {name}: {desc}" for name, desc in items
    )
    return (
        f"Available skills:\n{desc_list}\n\n"
        f'The user says: "{user_prompt}"'
    )


# Global executor reference for signal handler cleanup
_executor: ThreadPoolExecutor | None = None
_executor_lock = threading.Lock()

# Lock for serializing verbose output blocks across threads
_verbose_lock = threading.Lock()


def _emit_info(msg: str) -> None:
    """Emit an informational message that must be visible to the user.

    CLI entry (main()) configures logging.basicConfig so log.info shows; but
    programmatic callers (neighbor_regression, tests) skip main() and leave
    the root logger at WARNING — log.info would drop silently. Falling back
    to stderr when INFO is disabled keeps verbose output reliable regardless
    of entry point.
    """
    if log.isEnabledFor(logging.INFO):
        log.info(msg)
    else:
        print(msg, file=sys.stderr, flush=True)


def run_haiku(prompt: str, verbose: bool = False,
              log_buf: list[str] | None = None) -> CallResult:
    """Ask haiku which skill(s) to route to. Returns CallResult."""

    def _log(msg: str) -> None:
        if log_buf is not None:
            log_buf.append(msg)
        else:
            _emit_info(msg)

    settings_path = _resolved_settings_path
    try:
        result = subprocess.run(
            [
                "claude", "--bare",
                "--settings", settings_path,
                "-p", "-",
                "--model", "haiku",
                "--system-prompt", _ROUTING_SYSTEM_PROMPT,
                "--tools", "",
                "--max-turns", "1",
                "--output-format", "json",
                "--max-budget-usd", "0.10",
                "--no-session-persistence",
            ],
            input=prompt,
            capture_output=True, text=True, timeout=60,
        )
        # Try parsing JSON even on non-zero exit (claude returns JSON with error info)
        error_type = None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            data = None

        if result.returncode != 0 or (data and data.get("is_error")):
            if data:
                subtype = data.get("subtype", "")
                if "budget" in subtype:
                    error_type = "budget"
                elif "max_turns" in subtype:
                    error_type = "max_turns"
                else:
                    error_type = "unknown"
            else:
                error_type = "unknown"
            if verbose:
                _log(f"--- RESPONSE (rc={result.returncode}, error={error_type}) ---")
                _log(result.stdout.strip()[:200] or "(empty)")
                if result.stderr.strip():
                    _log(f"STDERR: {result.stderr.strip()[:200]}")
                _log("--- END RESPONSE ---")
            return CallResult(skills=None, error_type=error_type)

        if data is None:
            if verbose:
                _log("ERROR: could not parse JSON response")
            return CallResult(skills=None, error_type="parse_error")

        text = data.get("result", "")
        cost = data.get("total_cost_usd", 0)
        usage = data.get("usage", {})
        in_tok = (usage.get("input_tokens", 0)
                  + usage.get("cache_creation_input_tokens", 0)
                  + usage.get("cache_read_input_tokens", 0))
        out_tok = usage.get("output_tokens", 0)

        if verbose:
            _log(f"--- RESPONSE (${cost:.4f}, {in_tok}in/{out_tok}out) ---")
            _log(text.strip() or "(empty)")
            _log("--- END RESPONSE ---")

        skills = []
        for line in text.strip().split("\n"):
            line = line.strip().lstrip("-*0123456789.) ").strip()
            if " — " in line:
                line = line.split(" — ")[0].strip()
            if " (" in line:
                line = line.split(" (")[0].strip()
            if " -" in line:
                line = line.split(" -")[0].strip()
            line = line.strip("`").strip()
            if line and line.lower() != "none" and not line.startswith("No "):
                skills.append(line)
        return CallResult(skills=skills, cost=cost, input_tokens=in_tok, output_tokens=out_tok)

    except subprocess.TimeoutExpired:
        if verbose:
            _log("TIMEOUT after 60s")
        return CallResult(skills=None, error_type="timeout")
    except Exception as exc:
        if verbose:
            _log(f"ERROR: {exc}")
        return CallResult(skills=None, error_type="unknown")


_apfel_client = None
_apfel_server_proc = None
_apfel_server_lock = threading.Lock()
_apfel_client_lock = threading.Lock()


def _get_apfel_port() -> int:
    """Parse APFEL_PORT env var, falling back to default on invalid values."""
    default_port = 11434
    raw_port = os.environ.get("APFEL_PORT")
    if raw_port is None:
        return default_port
    try:
        return int(raw_port)
    except ValueError:
        log.warning(
            "Invalid APFEL_PORT %r; falling back to default port %d",
            raw_port,
            default_port,
        )
        return default_port


_APFEL_HOST = os.environ.get("APFEL_HOST", "127.0.0.1")
_APFEL_PORT = _get_apfel_port()


def _normalize_apfel_base_url(url: str) -> str:
    """Normalize APFEL_BASE_URL for urlsplit parsing.

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
            f"Invalid APFEL_BASE_URL {url!r}: could not parse host. "
            f"Expected form: http://host:port/v1"
        )
    return candidate


_APFEL_BASE_URL = _normalize_apfel_base_url(
    os.environ.get("APFEL_BASE_URL", f"http://{_APFEL_HOST}:{_APFEL_PORT}/v1")
)

_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


def _derive_health_url(base_url: str) -> str:
    """Derive an apfel /health URL from an OpenAI-style base URL.

    Strips a trailing /v1 (the OpenAI chat endpoint path) and replaces it with
    /health so the probe hits the same host:port the client will talk to.
    """
    import urllib.parse

    parsed = urllib.parse.urlsplit(base_url)
    path = parsed.path or ""
    if path.endswith("/v1"):
        health_path = path[:-3] + "/health"
    elif path:
        health_path = path.rstrip("/") + "/health"
    else:
        health_path = "/health"
    return urllib.parse.urlunsplit((
        parsed.scheme or "http",
        parsed.netloc,
        health_path,
        "",
        "",
    ))


def _is_loopback_base_url(base_url: str) -> bool:
    """Return True when base_url points at a local apfel we may auto-spawn."""
    import urllib.parse

    host = urllib.parse.urlsplit(base_url).hostname
    return host in _LOOPBACK_HOSTS


def _ensure_apfel_server():
    """Start apfel --serve if not already running, wait for readiness.

    Safe to call from worker threads via _get_apfel_client(): the module-level
    lock keeps the check+spawn atomic so concurrent callers don't race to
    spawn multiple apfel processes on the same port.

    When APFEL_BASE_URL points at a non-loopback host, the user is pointing at
    a remote apfel — health-probe it but do not auto-spawn anything locally.
    """
    global _apfel_server_proc
    import urllib.request
    import urllib.error

    health_url = _derive_health_url(_APFEL_BASE_URL)
    local = _is_loopback_base_url(_APFEL_BASE_URL)

    with _apfel_server_lock:
        if _apfel_server_proc is not None:
            if _apfel_server_proc.poll() is None:
                return
            # Cached handle but process has exited — clear and respawn.
            log.warning("Cached apfel server process exited; restarting.")
            _apfel_server_proc = None

        # Check if already up
        try:
            with urllib.request.urlopen(health_url, timeout=2):
                return  # server already running
        except (urllib.error.URLError, OSError):
            pass

        # Remote APFEL_BASE_URL: the user manages the server elsewhere. Don't
        # try to spawn locally — surface a clear error so they fix config or
        # start their remote apfel.
        if not local:
            raise RuntimeError(
                f"Remote apfel at {health_url} is unreachable. "
                f"Start the remote server, unset APFEL_BASE_URL to auto-spawn "
                f"locally, or pass --provider haiku."
            )

        # Start server — fixed --max-concurrent 16 covers typical worker counts
        # (--workers is capped at 32 but typical runs use 1-10); --permissive
        # reduces guardrail false positives on technical prompts.
        _emit_info("Starting apfel --serve --permissive ...")
        try:
            _apfel_server_proc = subprocess.Popen(
                ["apfel", "--serve", "--max-concurrent", "16", "--permissive"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Failed to start apfel server: 'apfel' was not found on PATH. "
                "Install apfel or pass --provider haiku."
            ) from exc
        atexit.register(_stop_apfel_server)

        # Wait for readiness (up to 10s)
        for _ in range(20):
            try:
                with urllib.request.urlopen(health_url, timeout=1):
                    _emit_info("apfel server ready.")
                    return
            except (urllib.error.URLError, OSError):
                import time
                time.sleep(0.5)
        # Readiness timed out — tear down the half-started process so we don't
        # leak it and so the next _ensure_apfel_server() call can retry.
        _stop_apfel_server()
        raise RuntimeError("apfel --serve failed to start within 10s")


def _stop_apfel_server():
    """Kill apfel server if we started it. Always clears the cached handle."""
    global _apfel_server_proc
    proc = _apfel_server_proc
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
    finally:
        _apfel_server_proc = None


def _get_apfel_client():
    """Lazy-init OpenAI client for apfel server. Auto-starts server if needed.

    Safe for programmatic callers (score_skill, neighbor_regression) that do
    not go through main(): _ensure_apfel_server() short-circuits when the
    server is already running. Client construction is guarded by a dedicated
    lock so workers>1 don't race and leak parallel httpx pools.
    """
    global _apfel_client
    _ensure_apfel_server()
    with _apfel_client_lock:
        if _apfel_client is None:
            try:
                from openai import OpenAI
                import httpx as _httpx
            except ImportError:
                raise RuntimeError(
                    "openai and httpx packages required for apfel provider. "
                    "Install: .venv/bin/pip install openai httpx"
                )
            _apfel_client = OpenAI(
                base_url=_APFEL_BASE_URL,
                api_key="unused",
                timeout=_httpx.Timeout(60.0, connect=5.0),
                max_retries=0,
            )
    return _apfel_client


def run_apfel(prompt: str, verbose: bool = False,
              log_buf: list[str] | None = None) -> CallResult:
    """Ask Apple Foundation Model which skill(s) to route to via apfel server.

    Auto-starts `apfel --serve` if not running. On-device, zero cost, ~4096 token context.
    """
    global _apfel_server_proc

    def _log(msg: str) -> None:
        if log_buf is not None:
            log_buf.append(msg)
        else:
            _emit_info(msg)

    try:
        client = _get_apfel_client()
        # Retry on timeout up to 2 times (Apple FM can get into transient slow states)
        last_exc = None
        resp = None
        for attempt in range(3):
            try:
                resp = client.chat.completions.create(
                    model="apple-foundationmodel",
                    messages=[
                        {"role": "system", "content": _ROUTING_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    extra_body={"x_context_output_reserve": 64},
                )
                break
            except Exception as e:
                msg = str(e).lower()
                if "timed out" in msg or "timeout" in msg:
                    last_exc = e
                    if verbose and attempt < 2:
                        _log(f"--- APFEL TIMEOUT (attempt {attempt+1}/3, retrying) ---")
                    continue
                raise
        if resp is None:
            raise last_exc if last_exc else RuntimeError("apfel call failed without exception")

        text = resp.choices[0].message.content or ""
        usage = resp.usage
        in_tok = usage.prompt_tokens if usage else 0
        out_tok = usage.completion_tokens if usage else 0

        if verbose:
            _log(f"--- APFEL RESPONSE (on-device, $0, {in_tok}in/{out_tok}out) ---")
            _log(text.strip() or "(empty)")
            _log("--- END RESPONSE ---")

        # Strip markdown code fences apfel sometimes wraps output in
        cleaned = text.strip()
        if cleaned.startswith("```"):
            cleaned = "\n".join(
                l for l in cleaned.split("\n")
                if not l.strip().startswith("```")
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
            if line and line.lower() != "none" and not line.startswith("No ") and line not in seen:
                skills.append(line)
                seen.add(line)
        return CallResult(skills=skills, cost=0.0, input_tokens=in_tok, output_tokens=out_tok)

    except Exception as exc:
        exc_str = str(exc)
        error_type = "unknown"
        if "context" in exc_str.lower() or "overflow" in exc_str.lower() or "4096" in exc_str:
            error_type = "context_overflow"
        elif "guardrail" in exc_str.lower() or "safety" in exc_str.lower():
            error_type = "guardrail_blocked"
        elif "timed out" in exc_str.lower() or "timeout" in exc_str.lower():
            error_type = "timeout"
        elif "connection" in exc_str.lower() or "refused" in exc_str.lower():
            error_type = "server_unavailable"
            # Server may have crashed — try to restart for subsequent calls
            if _apfel_server_proc and _apfel_server_proc.poll() is not None:
                _apfel_server_proc = None
                try:
                    _ensure_apfel_server()
                except RuntimeError:
                    pass  # restart failed, will error again on next call
        if verbose:
            _log(f"--- APFEL ERROR ({error_type}) ---")
            _log(exc_str[:300])
            _log("--- END ---")
        return CallResult(skills=None, error_type=error_type)


def _run_provider(prompt: str, verbose: bool = False,
                  log_buf: list[str] | None = None) -> CallResult:
    """Dispatch to active provider."""
    if _provider == "apfel":
        return run_apfel(prompt, verbose=verbose, log_buf=log_buf)
    return run_haiku(prompt, verbose=verbose, log_buf=log_buf)


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


def _check_correct(skill_name: str, chosen: list[str], expected: bool,
                   routing: str | None, valid_skills: list[str]) -> bool:
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
    descriptions: dict[str, str],
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
        log.info(header)

    log_lines: list[str] = []
    if verbose and parallel:
        log_lines.append(header)

    full_prompt = build_routing_prompt(descriptions, prompt, rotation=rotation)
    call_result = _run_provider(full_prompt, verbose=verbose,
                                log_buf=log_lines if parallel else None)
    chosen = call_result.skills

    if chosen is None:
        if verbose:
            error_hint = f" [{call_result.error_type}]" if call_result.error_type else ""
            log_lines.append(f"  -> SKIPPED ({_provider} call failed{error_hint})")
            if parallel:
                with _verbose_lock:
                    for line in log_lines:
                        log.warning(line)
            else:
                log.warning(log_lines[-1])
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
                    log.info(line)
        else:
            log.info(result_line)

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
    descriptions: dict[str, str],
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
        for i, (item, expected, tier, rotation, run_index, pid) in enumerate(flat_items, 1):
            result = _run_single_prompt(
                skill_name, item, i, total, descriptions, expected, tier,
                verbose, parallel=False, rotation=rotation,
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
            for i, (item, expected, tier, rotation, run_index, pid) in enumerate(flat_items, 1):
                future = executor.submit(
                    _run_single_prompt,
                    skill_name, item, i, total, descriptions, expected, tier,
                    verbose, True, rotation,
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
                            log.warning(traceback.format_exc())
                    continue
                ri, pid = meta_per_future[idx]
                _collect(result, ri, pid)
        finally:
            with _executor_lock:
                _executor = None

    if errors and not verbose:
        log.warning("  %d worker failures: %s", len(errors), ", ".join(set(errors)))

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
        return {"accuracy": 0.0, "precision": 1.0, "recall": 1.0, "total": 0, "correct": 0}
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
        "tp": tp, "fp": fp, "fn": fn,
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
    descriptions: dict[str, str],
    use_cache: bool = False,
    verbose: bool = False,
    limit: int = 0,
    workers: int = 1,
    rotations: int = 1,
    samples: int = 1,
) -> tuple[dict, list[CallResult]]:
    """Score trigger accuracy for one skill. Returns (score_dict, call_results)."""
    if rotations > 1 and samples > 1:
        raise ValueError("rotations and samples are mutually exclusive; only one may be > 1")
    cache_path = _results_dir() / _result_filename(skill_name, rotations, samples)

    if use_cache:
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {"skill": skill_name, "error": "corrupted cache file"}, []
            expected_hash = content_hash(skill_name, descriptions)
            if cached.get("content_hash") == expected_hash:
                return cached, []
        return {"skill": skill_name, "error": "no valid cache (stale or missing)"}, []

    triggers = load_trigger_file(skill_name)
    if not triggers:
        return {"skill": skill_name, "error": "no trigger file"}, []

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
    # With N rotations over L skills, stride = L // N. E.g., 5 rotations over 51 skills
    # gives offsets [0, 10, 20, 30, 40] — each skill shifts ~10 positions per rotation.
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
        skill_name, flat_items, descriptions, verbose=verbose, workers=workers,
    )

    if not all_results and total_failures > 0:
        return {"skill": skill_name, "error": f"all {total_failures} {_provider} calls failed"}, all_call_results

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
    fork_results = [r for r in all_results if r.get("routing") == "fork" and r.get("expected") is True]
    lock_results = [r for r in all_results if r.get("routing") == "lock" and r.get("expected") is True]
    fork_metrics = _compute_metrics(fork_results)
    lock_metrics = _compute_metrics(lock_results)

    score_data = {
        "skill": skill_name,
        **overall,
        "failures": total_failures,
        "failure_types": _count_failure_types(all_call_results),
        "provider": _provider,
        "easy_accuracy": easy_metrics["accuracy"],
        "easy_precision": easy_metrics["precision"],
        "easy_recall": easy_metrics["recall"],
        "hard_accuracy": hard_metrics["accuracy"],
        "hard_precision": hard_metrics["precision"],
        "hard_recall": hard_metrics["recall"],
        "fork_accuracy": fork_metrics["accuracy"],
        "lock_accuracy": lock_metrics["accuracy"],
        "tier_counts": {"easy": easy_metrics["total"], "hard": hard_metrics["total"]},
        "routing_counts": {"fork": fork_metrics["total"], "lock": lock_metrics["total"]},
        "content_hash": content_hash(skill_name, descriptions),
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
        order_range = round(max(per_rotation_acc) - min(per_rotation_acc), 4) if per_rotation_acc else 0.0
        # correctness_consistency: all rotations agree on correct/incorrect verdict
        correctness_agree = sum(
            1 for r in all_results
            if r.get("per_rotation_correct") and all(
                c == r["per_rotation_correct"][0] for c in r["per_rotation_correct"]
            )
        )
        # choice_consistency: all rotations return the same skill list
        choice_agree = sum(
            1 for r in all_results
            if r.get("per_rotation_choices") and all(
                c == r["per_rotation_choices"][0] for c in r["per_rotation_choices"]
                if c is not None
            ) and all(c is not None for c in r["per_rotation_choices"])
        )
        total_prompts = len(all_results)
        score_data["rotations"] = rotations
        score_data["per_rotation_accuracy"] = per_rotation_acc
        score_data["order_range"] = order_range
        score_data["order_stddev"] = round(
            (sum((a - sum(per_rotation_acc) / len(per_rotation_acc)) ** 2
                 for a in per_rotation_acc) / len(per_rotation_acc)) ** 0.5, 4
        ) if per_rotation_acc else 0.0
        score_data["order_sensitive"] = order_range > 0.15
        score_data["routing_consistency"] = round(
            choice_agree / total_prompts, 4
        ) if total_prompts else 0.0
        score_data["correctness_consistency"] = round(
            correctness_agree / total_prompts, 4
        ) if total_prompts else 0.0

    # Sample-specific metrics (P3)
    if samples > 1:
        pass_at_k_count = sum(1 for r in all_results if r.get("pass_at_k"))
        consistency_count = sum(1 for r in all_results if r.get("sample_consistency"))
        total_prompts = len(all_results)
        score_data["samples"] = samples
        score_data["pass_at_k"] = round(
            pass_at_k_count / total_prompts, 4
        ) if total_prompts else 0.0
        score_data["sample_consistency"] = round(
            consistency_count / total_prompts, 4
        ) if total_prompts else 0.0
        score_data["inconsistent_routing"] = (
            score_data["pass_at_k"] - score_data["accuracy"] > 0.15
        )

    # Write mode metadata for auditability
    score_data["mode"] = {
        "rotations": rotations,
        "samples": samples,
    }

    _results_dir().mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(score_data, indent=2) + "\n", encoding="utf-8")

    return score_data, all_call_results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test skill trigger accuracy with apfel (default) or haiku"
    )
    parser.add_argument("--skill", help="Test one skill")
    parser.add_argument("--all", action="store_true", help="Test all skills with trigger files")
    parser.add_argument("--cache", action="store_true", help="Cache-only: use cached results, skip stale/missing (no API calls)")
    parser.add_argument("--summary", action="store_true", help="Print summary only")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON")
    parser.add_argument("--verbose", action="store_true", help="Show prompt/response for each API call")
    parser.add_argument("--limit", type=int, default=0, metavar="N",
                        help="Test only first N should_trigger + N should_not_trigger prompts per skill")
    parser.add_argument("--workers", type=int, default=1, metavar="N", choices=range(1, 33),
                        help="Parallel workers for provider calls (default 1, recommended 4)")
    parser.add_argument("--rotations", type=int, default=1, metavar="N", choices=range(1, 16),
                        help="Cyclic rotations for order-bias control (default 1, recommended 5)")
    parser.add_argument("--samples", type=int, default=1, metavar="N", choices=range(1, 8),
                        help="Independent samples for pass@k robustness (default 1, recommended 3)")
    parser.add_argument("--provider", default=resolve_provider(None),
                        choices=sorted(SUPPORTED_PROVIDERS),
                        help=(
                            "Routing provider: apfel (on-device, free) or haiku (API, paid). "
                            "Default: RUBY_PLUGIN_EVAL_PROVIDER env var or apfel."
                        ))
    args = parser.parse_args()

    logging.basicConfig(
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO if args.verbose else logging.WARNING,
        stream=sys.stderr,
    )

    if args.rotations > 1 and args.samples > 1:
        parser.error("--rotations and --samples are mutually exclusive (both > 1)")

    global _provider, RESULTS_DIR
    _provider = resolve_provider(args.provider)
    RESULTS_DIR = results_dir(_provider)

    # Start apfel server before workers (avoids race condition in threads).
    # Skip for --cache (documented as "no API calls" — pure filesystem reads).
    if _provider == "apfel" and not args.cache:
        _ensure_apfel_server()

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
            log.warning("Interrupted — cancelling pending work, waiting for running workers.")
            executor.shutdown(wait=True, cancel_futures=True)
        raise SystemExit(130)

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    # Resolve auth once — avoids concurrent keychain access with --workers > 1
    global _resolved_settings_path
    _resolved_settings_path = _resolve_settings()
    base_settings = str(TRIGGERS_DIR.parent / "bare_settings.json")
    is_temp_settings = _resolved_settings_path != base_settings

    def _cleanup_settings():
        if is_temp_settings:
            try:
                os.unlink(_resolved_settings_path)
            except OSError:
                pass
            os.environ.pop(_RESOLVED_TOKEN_ENV, None)

    atexit.register(_cleanup_settings)

    descriptions = load_all_descriptions()

    # Collect all CallResults for cost aggregation (single-threaded, no lock needed)
    all_call_results: list[CallResult] = []

    if args.skill:
        result, crs = score_skill(args.skill, descriptions, args.cache,
                                  verbose=args.verbose, limit=args.limit,
                                  workers=args.workers,
                                  rotations=args.rotations, samples=args.samples)
        all_call_results.extend(crs)

        if args.summary:
            tier_str = ""
            tc = result.get("tier_counts", {})
            if tc.get("hard", 0) > 0:
                tier_str = (f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                            f"hard: {result.get('hard_accuracy', 0):.0%})")
            extra = ""
            if result.get("rotations", 1) > 1:
                extra = (f" choice={result.get('routing_consistency', 0):.0%}"
                         f" correct={result.get('correctness_consistency', 0):.0%}"
                         f" range={result.get('order_range', 0):.2f}")
                if result.get("order_sensitive"):
                    extra += " ORDER-SENSITIVE"
            if result.get("samples", 1) > 1:
                extra = (f" pass@{result['samples']}={result.get('pass_at_k', 0):.0%}"
                         f" cons={result.get('sample_consistency', 0):.0%}")
                if result.get("inconsistent_routing"):
                    extra += " INCONSISTENT"
            print(f"{args.skill}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                  f"precision={result.get('precision', 0):.0%} "
                  f"recall={result.get('recall', 0):.0%}{extra}")
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
            result, crs = score_skill(name, descriptions, args.cache,
                                      verbose=args.verbose, limit=args.limit,
                                      workers=args.workers,
                                      rotations=args.rotations, samples=args.samples)
            all_call_results.extend(crs)

            if "error" in result:
                log.warning("SKIPPED (%s)", result['error'])
                continue
            all_results[name] = result
            total_accuracy += result.get("accuracy", 0)
            skills_tested += 1
            print(
                f"accuracy={result.get('accuracy', 0):.0%} "
                f"(P={result.get('precision', 0):.0%} "
                f"R={result.get('recall', 0):.0%})",
                file=sys.stderr, flush=True,
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
                    tier_str = (f" (easy: {result.get('easy_accuracy', 0):.0%}, "
                                f"hard: {result.get('hard_accuracy', 0):.0%})")
                extra = ""
                if result.get("rotations", 1) > 1:
                    extra = (f" choice={result.get('routing_consistency', 0):.0%}"
                             f" correct={result.get('correctness_consistency', 0):.0%}"
                             f" range={result.get('order_range', 0):.2f}")
                    if result.get("order_sensitive"):
                        extra += " ORDER-SENSITIVE"
                if result.get("samples", 1) > 1:
                    extra = (f" pass@{result['samples']}={result.get('pass_at_k', 0):.0%}"
                             f" cons={result.get('sample_consistency', 0):.0%}")
                    if result.get("inconsistent_routing"):
                        extra += " INCONSISTENT"
                print(f"  {name}: accuracy={result.get('accuracy', 0):.0%}{tier_str} "
                      f"P={result.get('precision', 0):.0%} "
                      f"R={result.get('recall', 0):.0%}{extra}")
        else:
            aggregate = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
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
            aggregate_suffix = _result_filename("_aggregate", args.rotations, args.samples)
            aggregate_path = _results_dir() / aggregate_suffix
            _results_dir().mkdir(parents=True, exist_ok=True)
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
        cost_lines = ["--- Cost Summary ---", f"  Total API calls: {len(successful)}"]
        if failed:
            cost_lines.append(f"  Failed calls:    {failed}")
        cost_lines.extend([
            f"  Total cost:      ${total_cost:.4f}",
            f"  Max single call: ${max_cost:.4f}",
            f"  Avg per call:    ${avg_cost:.4f}",
            "--------------------",
        ])
        if args.verbose:
            for line in cost_lines:
                log.info(line)
        else:
            for line in cost_lines:
                print(line, file=sys.stderr, flush=True)

    # Temp settings cleanup handled by atexit (also fires on SIGINT/SystemExit)


if __name__ == "__main__":
    main()
