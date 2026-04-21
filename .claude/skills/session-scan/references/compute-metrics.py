#!/usr/bin/env python3
"""
Session Analytics v2 — Compute exploratory metrics from Claude Code sessions.

Reads ccrider message JSON and computes friction scores, fingerprints, plugin
opportunity scores, tool bigrams, and file hotspots.

Usage:
    # Single session from messages JSON file (outputs JSON to stdout)
    python3 compute-metrics.py <messages.json> --session-id ID --project NAME [--provider NAME]

    # Single session directly from ccrider SQLite DB
    python3 compute-metrics.py --from-db SESSION_ID --db PATH [--project NAME] [--provider NAME]

    # Batch mode (appends to metrics.jsonl)
    python3 compute-metrics.py --batch <manifest.json>

    # Trends mode (computes windowed aggregates)
    python3 compute-metrics.py --trends <metrics.jsonl> [--project NAME] [--provider NAME] [--notes PATH]

    # Backfill from v1 extracts
    python3 compute-metrics.py --backfill <extracts-dir/>

For full scans across many sessions prefer the scan-sessions.py orchestrator,
which handles discovery, dedup, ledger append, and triage table in one call.
"""

import json
import math
import os
import re
import shlex
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ─── Friction Score Weights ───────────────────────────────────────────────────

FRICTION_WEIGHTS = {
    "error_tool_ratio": 2.0,
    "retry_loops": 3.0,
    "user_corrections": 2.5,
    "approach_changes": 2.0,
    "context_compactions": 1.5,
    "interrupted_requests": 1.0,
}

# Sigmoid normalization: score = 1 / (1 + e^(-k*(raw - midpoint)))
FRICTION_SIGMOID_K = 3.0
FRICTION_SIGMOID_MIDPOINT = 1.5

# ─── Fingerprint Rules ───────────────────────────────────────────────────────

CORRECTION_PATTERNS = re.compile(
    r"\b(no[,.]?\s|wrong|instead|actually|that'?s not|not what I|"
    r"I meant|I said|please don'?t|stop|undo|revert)\b",
    re.IGNORECASE,
)

FINGERPRINT_KEYWORDS = {
    "bug-fix": re.compile(
        r"\b(fix|bug|broken|error|issue|crash|fail|debug|wrong)\b", re.IGNORECASE
    ),
    "feature": re.compile(
        r"\b(add|implement|build|create|new feature|scaffold)\b", re.IGNORECASE
    ),
    "exploration": re.compile(
        r"\b(explore|understand|how does|what is|explain|look at)\b", re.IGNORECASE
    ),
    "maintenance": re.compile(
        r"\b(deps?|update|upgrade|bump|version|migrate)\b", re.IGNORECASE
    ),
    "review": re.compile(
        r"\b(review|PR|pull request|code review|feedback)\b", re.IGNORECASE
    ),
    "refactoring": re.compile(
        r"\b(refactor|extract|rename|move|reorganize|clean ?up)\b", re.IGNORECASE
    ),
}

# ─── Plugin Opportunity Signals ───────────────────────────────────────────────

PLUGIN_COMMAND_RE = re.compile(r"/(?:(?:rb)|(?:ruby-grape-rails)):[a-z][a-z0-9_-]*")
SKILL_COMMAND_RE = re.compile(
    r"/(?:(?:rb)|(?:ruby-grape-rails)|(?:hotwire)):[a-z][a-z0-9_-]*"
)
SCAFFOLDING_PREFIX_RE = re.compile(r"^\s*Base directory for this skill:")


def sigmoid(raw):
    """Apply sigmoid normalization to raw friction score."""
    return 1.0 / (
        1.0 + math.exp(-FRICTION_SIGMOID_K * (raw - FRICTION_SIGMOID_MIDPOINT))
    )


def normalize_plugin_command(command):
    """Normalize plugin command aliases to canonical short names."""
    if not isinstance(command, str):
        return None
    if command.startswith("/ruby-grape-rails:"):
        return "/rb:" + command.split(":", 1)[1]
    return command


def normalize_plugin_command_name(command):
    """Normalize a plugin command to its bare command name."""
    if not isinstance(command, str):
        return None
    normalized = normalize_plugin_command(command)
    if not normalized:
        return None
    if normalized.startswith("/rb:"):
        return normalized.split(":", 1)[1]
    if normalized.startswith("/"):
        return normalized[1:]
    return normalized


def normalize_project_path(path):
    """Return a stable project path value for persisted metrics."""
    if not path:
        return "unknown"
    return str(path)


def extract_plugin_commands(user_msgs):
    """Extract shipped plugin commands while ignoring contributor analyzers."""
    commands = []
    for text in user_msgs:
        if SCAFFOLDING_PREFIX_RE.match(text):
            continue
        found = PLUGIN_COMMAND_RE.findall(text)
        for command in found:
            if "{" in command or "<" in command:
                continue
            normalized = normalize_plugin_command(command)
            if normalized:
                commands.append(normalized)
    return commands


# ─── Message Parsing ─────────────────────────────────────────────────────────


def parse_messages(data):
    """Parse ccrider message JSON into structured lists.

    Accepts either:
    - A list of message objects (ccrider format)
    - A dict with a 'messages' key containing the list
    """
    if isinstance(data, dict):
        messages = data.get("messages", [])
    elif isinstance(data, list):
        messages = data
    else:
        return []
    return messages


def extract_provider(data, fallback=None):
    """Extract provider label from transcript payload when available."""
    candidates = []
    if isinstance(data, dict):
        candidates.append(data.get("provider"))

        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            candidates.append(metadata.get("provider"))

        session = data.get("session")
        if isinstance(session, dict):
            candidates.append(session.get("provider"))

        source = data.get("source")
        if isinstance(source, dict):
            candidates.append(source.get("provider"))

    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()

    if isinstance(fallback, str) and fallback.strip():
        return fallback.strip()
    return "unknown"


def _get_role(msg):
    """Get message role, supporting both API format (role) and ccrider format (type)."""
    return msg.get("role", msg.get("type", msg.get("message", {}).get("role", "")))


def _get_content(msg):
    """Get message content, supporting both API and ccrider formats."""
    return msg.get("content", msg.get("message", {}).get("content", ""))


def extract_file_paths(tool_input):
    """Extract one or more file paths from a tool input payload."""
    if not isinstance(tool_input, dict):
        return []

    paths = []
    for key in ("file_path", "path"):
        value = tool_input.get(key)
        if isinstance(value, str) and value:
            paths.append(value)

    for key in ("file_paths", "paths"):
        value = tool_input.get(key)
        if isinstance(value, list):
            paths.extend(p for p in value if isinstance(p, str) and p)

    edits = tool_input.get("edits")
    if isinstance(edits, list):
        for edit in edits:
            if isinstance(edit, dict):
                paths.extend(extract_file_paths(edit))

    return paths


# Tool name detection from assistant text (ccrider may not preserve tool_use blocks).
# Restrict this to tool-like syntax so ordinary prose like "ask the Agent" does not
# inflate tool counts.
TOOL_NAME_PATTERN = (
    r"Read|Edit|MultiEdit|Write|Bash|Grep|Glob|Task|Agent|NotebookEdit|"
    r"WebFetch|WebSearch|Skill|AskUserQuestion|ExitPlanMode|KillShell|"
    r"MCPSearch|mcp__[A-Za-z0-9_]+"
)
TOOL_MENTION_RE = re.compile(
    rf"(?:`(?P<backtick>{TOOL_NAME_PATTERN})`|"
    rf"\btool:(?P<prefixed>{TOOL_NAME_PATTERN})\b|"
    rf"\b(?P<call>{TOOL_NAME_PATTERN})\s*\((?P<call_args>[^)]*)\))"
)
SHELL_FENCE_RE = re.compile(r"```(?:bash|sh|zsh|shell)\s*\n(.*?)```", re.DOTALL | re.I)
PROMPT_COMMAND_RE = re.compile(r"^\s*(?:\$|>)\s+(.+?)\s*$")
KNOWN_BASH_PREFIX_RE = re.compile(
    r"^(bundle\s|rails\s|rake\s|git\s|npm\s|python3?\s|cd\s|rm\s)"
)
FAILURE_SIGNAL_RE = re.compile(
    r"\b(error|failed|failure|exception|traceback|command not found|"
    r"permission denied|no such file|syntaxerror|exit code)\b",
    re.IGNORECASE,
)
USER_FAILURE_SIGNAL_RE = re.compile(
    r"(?im)(?:\btraceback\b|\bcommand not found\b|\bpermission denied\b|"
    r"\bno such file(?: or directory)?\b|\bsyntaxerror\b|\bexit code\s+\d+\b|"
    r"^\s*(?:error|failed|failure|exception):|\bi got an error\b|"
    r"\bit failed\b|\bit errored\b)"
)
ASSISTANT_FAILURE_SIGNAL_RE = re.compile(
    r"(?im)(?:\btraceback\b|\bcommand not found\b|\bpermission denied\b|"
    r"\bno such file(?: or directory)?\b|\bsyntaxerror\b|\bexit code\s+\d+\b|"
    r"^\s*(?:error|failed|exception):)"
)


def extract_tool_calls(messages):
    """Extract ordered list of tool calls from messages.

    For API format: extracts structured tool_use blocks.
    For ccrider format: infers tool names from assistant message text patterns.
    """
    return [item["tc"] for item in extract_tool_positions(messages)]


def extract_tool_positions(messages):
    """Extract tool calls with message positions across transcript formats."""
    tools = []
    for i, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue
        content = _get_content(msg)
        role = _get_role(msg)

        # API format: structured content blocks
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tools.append({"msg_index": i, "tc": block})

        # ccrider format: infer tools from assistant text
        elif isinstance(content, str) and role == "assistant":
            inferred_bash_commands = _infer_bash_commands_from_text(content)
            mentioned = []
            for match in TOOL_MENTION_RE.finditer(content):
                name = match.group("backtick") or match.group("prefixed") or match.group("call")
                if match.group("call"):
                    call_args = (match.group("call_args") or "").strip()
                    if call_args and "=" not in call_args and '"' not in call_args and "'" not in call_args:
                        continue
                if name:
                    mentioned.append(name)
            for name in mentioned:
                if name == "Bash" and inferred_bash_commands:
                    continue
                tools.append({"msg_index": i, "tc": {"name": name, "input": {}}})
            for command in inferred_bash_commands:
                tools.append(
                    {
                        "msg_index": i,
                        "tc": {"name": "Bash", "input": {"command": command}},
                    }
                )

    return tools


def extract_user_messages(messages):
    """Extract user message texts."""
    user_msgs = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        role = _get_role(msg)
        if role != "user":
            continue
        content = _get_content(msg)
        if isinstance(content, str):
            if (
                not content.startswith("<system-reminder>")
                and not content.startswith("<local-command-caveat>")
                and not content.startswith("<local-command-stdout>")
                and len(content) > 5
            ):
                user_msgs.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text = block.get("text", "")
                    if not text.startswith("<system-reminder>") and not text.startswith(
                        "<command-name>"
                    ):
                        if len(text) > 5:
                            user_msgs.append(text)
    return user_msgs


def extract_errors(messages):
    """Extract tool errors from messages."""
    errors = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        content = _get_content(msg)
        role = _get_role(msg)

        # API format: structured error blocks
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    if block.get("type") == "tool_result" and block.get("is_error"):
                        err = block.get("content", "")
                        if isinstance(err, str) and len(err) > 5:
                            errors.append(err[:200])

        # ccrider format: detect error patterns in assistant text
        elif isinstance(content, str) and role == "assistant":
            if re.search(r"\b(error|Error|ERROR|failed|Failed|FAILED)\b", content):
                if re.search(
                    r"\b(zeitwerk|rubocop|test|rspec|minitest)\s+(error|fail)",
                    content,
                    re.I,
                ):
                    errors.append(content[:200])
    return errors


def extract_timestamps(messages):
    """Extract timestamps from messages."""
    timestamps = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        ts = msg.get("timestamp")
        if ts:
            timestamps.append(ts)
    return timestamps


def _text_blocks(content):
    """Yield text fragments from either string or block content."""
    if isinstance(content, str):
        yield content
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    text = block.get("text", "")
                    if isinstance(text, str):
                        yield text
                elif block.get("type") == "tool_result":
                    text = block.get("content", "")
                    if isinstance(text, str):
                        yield text


def _normalize_inferred_bash_line(line, allow_bare=False):
    """Normalize a shell-like line extracted from transcript text."""
    if not isinstance(line, str):
        return ""

    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return ""

    prompt_match = PROMPT_COMMAND_RE.match(stripped)
    if prompt_match:
        return prompt_match.group(1).strip()

    if allow_bare and KNOWN_BASH_PREFIX_RE.match(stripped):
        return stripped

    return ""


def _infer_bash_commands_from_text(content):
    """Best-effort extraction of Bash commands from text-only assistant output."""
    commands = []
    seen = set()

    for text in _text_blocks(content):
        if not isinstance(text, str):
            continue

        for match in SHELL_FENCE_RE.finditer(text):
            block = match.group(1)
            for line in block.splitlines():
                command = _normalize_inferred_bash_line(line, allow_bare=True)
                if command and command not in seen:
                    seen.add(command)
                    commands.append(command)

        text_without_fences = SHELL_FENCE_RE.sub("", text)
        for line in text_without_fences.splitlines():
            command = _normalize_inferred_bash_line(line, allow_bare=False)
            if command and command not in seen:
                seen.add(command)
                commands.append(command)

    return commands


def message_has_failure_signal(msg):
    """Detect whether a message contains explicit failure evidence."""
    if not isinstance(msg, dict):
        return False

    role = _get_role(msg)
    content = _get_content(msg)
    tool_result_texts = []

    if isinstance(content, list):
        for block in content:
            if isinstance(block, dict) and block.get("type") == "tool_result":
                if block.get("is_error"):
                    return True
                block_content = block.get("content", "")
                if isinstance(block_content, str):
                    tool_result_texts.append(block_content)

    if role == "assistant":
        for text in tool_result_texts:
            if FAILURE_SIGNAL_RE.search(text):
                return True
        for text in _text_blocks(content):
            if ASSISTANT_FAILURE_SIGNAL_RE.search(text):
                return True
    else:
        for text in _text_blocks(content):
            if USER_FAILURE_SIGNAL_RE.search(text):
                return True
    return False


def normalize_bash_signature(command):
    """Normalize Bash commands for retry-loop detection."""
    if not isinstance(command, str) or not command.strip():
        return ""

    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.strip().split()

    while tokens and re.match(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
        tokens = tokens[1:]

    if len(tokens) >= 2 and tokens[0] in ("bash", "zsh", "sh") and tokens[1] in (
        "-lc",
        "-c",
    ):
        tokens = tokens[2:]
        while tokens and re.match(r"[A-Za-z_][A-Za-z0-9_]*=.*", tokens[0]):
            tokens = tokens[1:]

    if len(tokens) >= 2 and tokens[0] == "bundle" and tokens[1] == "exec":
        tokens = tokens[2:]

    if not tokens:
        return ""

    return " ".join(tokens[:3])


def extract_bash_runs(messages):
    """Extract Bash commands with nearby failure evidence."""
    runs = []
    for index, msg in enumerate(messages):
        if not isinstance(msg, dict):
            continue

        content = _get_content(msg)
        role = _get_role(msg)
        signatures = []

        if isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use" or block.get("name") != "Bash":
                    continue

                command = block.get("input", {}).get("command", "")
                signature = normalize_bash_signature(command)
                if signature:
                    signatures.append(signature)

        if not signatures and role == "assistant":
            for command in _infer_bash_commands_from_text(content):
                signature = normalize_bash_signature(command)
                if signature:
                    signatures.append(signature)

        if not signatures:
            continue

        lookahead = messages[index : index + 4]
        failed = any(message_has_failure_signal(candidate) for candidate in lookahead)
        for signature in signatures:
            runs.append({"signature": signature, "failed": failed})

    return runs


def count_retry_loops(bash_runs):
    """Count repeated failing Bash command loops from normalized run data."""
    retry_loops = 0
    window = []
    for run in bash_runs:
        signature = run["signature"]
        if window and window[-1]["signature"] == signature:
            window.append(run)
        else:
            if len(window) >= 3 and sum(1 for item in window if item["failed"]) >= 2:
                retry_loops += 1
            window = [run]
    if len(window) >= 3 and sum(1 for item in window if item["failed"]) >= 2:
        retry_loops += 1
    return retry_loops


# ─── Metric Computation ──────────────────────────────────────────────────────


def compute_friction(tool_calls, user_msgs, errors, messages):
    """Compute friction score (0.0-1.0) with signal breakdown."""
    tool_count = len(tool_calls)

    # Error-tool ratio
    error_count = len(errors)
    error_tool_ratio = error_count / max(tool_count, 1)

    # Retry loops: same normalized Bash command 3+ times with repeated failure
    # evidence nearby. This deliberately ignores successful scripted repetition.
    bash_runs = extract_bash_runs(messages)
    retry_loops = count_retry_loops(bash_runs)

    # User corrections
    user_corrections = 0
    for text in user_msgs:
        if CORRECTION_PATTERNS.search(text[:500]):
            user_corrections += 1

    # Approach changes: detect tool pattern shifts (edit-heavy -> read-heavy)
    approach_changes = 0
    if len(tool_calls) >= 10:
        chunk_size = max(len(tool_calls) // 4, 5)
        chunks = [
            tool_calls[i : i + chunk_size]
            for i in range(0, len(tool_calls), chunk_size)
        ]
        prev_dominant = None
        for chunk in chunks:
            counts = Counter(tc.get("name", "") for tc in chunk)
            dominant = counts.most_common(1)[0][0] if counts else None
            if prev_dominant and dominant and prev_dominant != dominant:
                approach_changes += 1
            prev_dominant = dominant

    # Context compactions
    context_compactions = 0
    for msg in messages:
        content = _get_content(msg)
        if isinstance(content, str) and "context compaction" in content.lower():
            context_compactions += 1
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    if "context compaction" in block.get("text", "").lower():
                        context_compactions += 1

    # Interrupted requests
    interrupted_requests = 0
    for msg in messages:
        content = _get_content(msg)
        if isinstance(content, str):
            if "[Request interrupted by user]" in content:
                interrupted_requests += 1
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    if "[Request interrupted by user]" in block.get("text", ""):
                        interrupted_requests += 1

    signals = {
        "error_tool_ratio": round(error_tool_ratio, 3),
        "retry_loops": retry_loops,
        "user_corrections": user_corrections,
        "approach_changes": approach_changes,
        "context_compactions": context_compactions,
        "interrupted_requests": interrupted_requests,
    }

    # Weighted sum
    raw = sum(signals[k] * FRICTION_WEIGHTS[k] for k in FRICTION_WEIGHTS)

    score = round(sigmoid(raw), 3)
    return score, signals


def compute_fingerprint(user_msgs, tool_calls, files_edited):
    """Classify session type with confidence."""
    scores = defaultdict(float)

    user_text = " ".join(user_msgs[:10])  # First 10 messages for intent

    for fp_type, pattern in FINGERPRINT_KEYWORDS.items():
        matches = pattern.findall(user_text)
        scores[fp_type] += len(matches) * 2.0

    # Tool profile signals
    tool_names = [tc.get("name", "") for tc in tool_calls]
    tool_counts = Counter(tool_names)
    total = max(len(tool_names), 1)

    read_pct = (
        tool_counts.get("Read", 0)
        + tool_counts.get("Grep", 0)
        + tool_counts.get("Glob", 0)
    ) / total
    edit_pct = (
        tool_counts.get("Edit", 0)
        + tool_counts.get("Write", 0)
        + tool_counts.get("MultiEdit", 0)
        + tool_counts.get("NotebookEdit", 0)
    ) / total
    bash_pct = tool_counts.get("Bash", 0) / total

    if read_pct > 0.5 and edit_pct < 0.1:
        scores["exploration"] += 3.0
    if edit_pct > 0.3:
        scores["feature"] += 2.0
    if bash_pct > 0.3:
        scores["bug-fix"] += 2.0
    if len(files_edited) > 10:
        scores["refactoring"] += 2.0
    if len(files_edited) > 5:
        scores["feature"] += 1.0

    # runtime tooling signals
    tidewave_count = sum(1 for n in tool_names if n.startswith("mcp__tidewave"))
    if tidewave_count > 0:
        scores["bug-fix"] += 1.5

    # Bundle deps signals
    bash_cmds = [
        tc.get("input", {}).get("command", "")
        for tc in tool_calls
        if tc.get("name") == "Bash"
    ]
    deps_cmds = [
        c
        for c in bash_cmds
        if "bundle install" in c or "bundle update" in c or "gem install" in c
    ]
    if deps_cmds:
        scores["maintenance"] += 3.0

    # gh pr signals
    pr_cmds = [c for c in bash_cmds if "gh pr" in c or "gh issue" in c]
    if pr_cmds:
        scores["review"] += 3.0

    if not scores:
        return "unknown", 0.0

    best = max(scores, key=scores.get)
    total_score = sum(scores.values())
    confidence = round(scores[best] / max(total_score, 1), 2)

    return best, confidence


def compute_plugin_opportunity(user_msgs, tool_calls, rb_commands, messages=None):
    """Compute plugin opportunity score (0.0-1.0)."""
    could_use = []
    used_commands = {
        name
        for name in (normalize_plugin_command_name(command) for command in rb_commands)
        if name
    }

    tool_names = [tc.get("name", "") for tc in tool_calls]
    tool_count = len(tool_names)
    bash_cmds = [
        tc.get("input", {}).get("command", "")
        for tc in tool_calls
        if tc.get("name") == "Bash"
    ]

    # Repeated failing Bash runs suggest /rb:investigate.
    retry_loops = count_retry_loops(extract_bash_runs(messages or []))

    if retry_loops > 0 and "investigate" not in used_commands:
        could_use.append("investigate")

    # Many tools without plan suggest /rb:plan
    if tool_count > 50 and "plan" not in used_commands:
        could_use.append("plan")

    # Multiple test runs suggest /rb:verify
    test_runs = sum(
        1
        for c in bash_cmds
        if "bundle exec rspec" in c
        or "bundle exec minitest" in c
        or "bundle exec rails test" in c
        or "rails zeitwerk:check" in c
    )
    if test_runs >= 3 and "verify" not in used_commands:
        could_use.append("verify")

    # PR commands suggest /rb:pr-review
    pr_cmds = sum(1 for c in bash_cmds if "gh pr" in c)
    if pr_cmds >= 2 and "pr-review" not in used_commands:
        could_use.append("pr-review")

    # Many edits without review suggest /rb:review
    edit_count = sum(
        1 for n in tool_names if n in ("Edit", "Write", "MultiEdit", "NotebookEdit")
    )
    if edit_count > 10 and "review" not in used_commands:
        could_use.append("review")

    score = min(len(could_use) * 0.2, 1.0)
    return round(score, 2), could_use


def compute_tool_profile(tool_calls):
    """Compute tool usage percentages."""
    names = [tc.get("name", "") for tc in tool_calls]
    total = max(len(names), 1)
    counts = Counter(names)

    read_count = counts.get("Read", 0) + counts.get("Glob", 0)
    edit_count = (
        counts.get("Edit", 0)
        + counts.get("Write", 0)
        + counts.get("MultiEdit", 0)
        + counts.get("NotebookEdit", 0)
    )
    bash_count = counts.get("Bash", 0)
    grep_count = counts.get("Grep", 0)
    tidewave_count = sum(v for k, v in counts.items() if k.startswith("mcp__tidewave"))
    other_count = (
        total - read_count - edit_count - bash_count - grep_count - tidewave_count
    )

    return {
        "read_pct": round(read_count / total * 100, 1),
        "edit_pct": round(edit_count / total * 100, 1),
        "bash_pct": round(bash_count / total * 100, 1),
        "grep_pct": round(grep_count / total * 100, 1),
        "tidewave_pct": round(tidewave_count / total * 100, 1),
        "other_pct": round(max(other_count, 0) / total * 100, 1),
    }


def compute_tool_bigrams(tool_calls, top_n=15):
    """Extract top tool sequence pairs."""
    names = [tc.get("name", "") for tc in tool_calls]
    bigrams = Counter()
    for i in range(len(names) - 1):
        pair = f"{names[i]}->{names[i + 1]}"
        bigrams[pair] += 1
    return dict(bigrams.most_common(top_n))


def compute_file_hotspots(tool_calls, top_n=10):
    """Count reads/edits per file path."""
    hotspots = defaultdict(lambda: {"reads": 0, "edits": 0})
    for tc in tool_calls:
        name = tc.get("name", "")
        inp = tc.get("input", {})
        file_paths = extract_file_paths(inp)
        if not file_paths:
            continue
        for fp in file_paths:
            if name in ("Read", "Glob"):
                hotspots[fp]["reads"] += 1
            elif name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                hotspots[fp]["edits"] += 1

    ranked = sorted(
        hotspots.items(),
        key=lambda x: x[1]["reads"] + x[1]["edits"],
        reverse=True,
    )[:top_n]

    return [{"path": p, **counts} for p, counts in ranked]


def compute_duration(timestamps):
    """Compute session duration in minutes from timestamps."""
    if len(timestamps) < 2:
        return None
    try:
        first, last = timestamps[0], timestamps[-1]
        if isinstance(first, str) and isinstance(last, str):
            t1 = datetime.fromisoformat(first.replace("Z", "+00:00"))
            t2 = datetime.fromisoformat(last.replace("Z", "+00:00"))
            return round((t2 - t1).total_seconds() / 60, 1)
        elif isinstance(first, (int, float)) and isinstance(last, (int, float)):
            return round((last - first) / 60000, 1)
    except (ValueError, TypeError):
        pass
    return None


def categorize_files(files):
    """Categorize files by type (preserved from v1 extract-session.py)."""
    categories = Counter()
    for fp in files:
        if "_controller.rb" in fp or "/controllers/" in fp:
            categories["controller"] += 1
        elif "_test.rb" in fp or "_spec.rb" in fp:
            categories["test"] += 1
        elif "/migrations/" in fp or "_migration.rb" in fp:
            categories["migration"] += 1
        elif (
            "_worker.rb" in fp or "/workers/" in fp or "_job.rb" in fp or "/jobs/" in fp
        ):
            categories["sidekiq_worker"] += 1
        elif "/models/" in fp or (fp.endswith(".rb") and "/app/" in fp):
            categories["model_or_module"] += 1
        elif fp.endswith(".erb") or fp.endswith(".haml") or fp.endswith(".slim"):
            categories["template"] += 1
        elif "routes.rb" in fp:
            categories["router"] += 1
        elif fp.endswith(".js") or fp.endswith(".ts"):
            categories["javascript"] += 1
        elif fp.endswith(".css"):
            categories["css"] += 1
        else:
            categories["other"] += 1
    return dict(categories)


# ─── Skill Effectiveness ─────────────────────────────────────────────────────


def _locate_skill_invocations(user_msgs, all_messages):
    """Find skill invocations and their position in the message stream.

    Returns list of {skill, msg_index, user_msg_index} for each invocation.
    """
    invocations = []
    user_idx = 0
    for i, msg in enumerate(all_messages):
        if not isinstance(msg, dict):
            continue
        role = _get_role(msg)
        content = _get_content(msg)
        if role != "user":
            continue
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = " ".join(
                b.get("text", "")
                for b in content
                if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            user_idx += 1
            continue

        if SCAFFOLDING_PREFIX_RE.match(text):
            user_idx += 1
            continue

        cmds = SKILL_COMMAND_RE.findall(text)
        for cmd in cmds:
            if "{" in cmd or "<" in cmd:
                continue
            normalized = normalize_plugin_command(cmd)
            invocations.append(
                {
                    "skill": normalized or cmd,
                    "msg_index": i,
                    "user_msg_index": user_idx,
                }
            )
        user_idx += 1
    return invocations


def compute_skill_effectiveness(user_msgs, tool_calls, errors, messages):
    """Compute per-skill effectiveness signals.

    For each skill invocation, measures what happened before and after:
    - Pre/post error rates
    - Post-skill edit count (did the skill lead to action?)
    - Post-skill test runs (did the user verify?)
    - Whether user corrections followed (skill didn't help)
    - Time-to-action (how quickly edits followed)

    Returns dict keyed by skill command name.
    """
    invocations = _locate_skill_invocations(user_msgs, messages)
    if not invocations:
        return {}

    total_msgs = len(messages)
    tool_positions = extract_tool_positions(messages)

    results = {}
    for inv in invocations:
        skill = inv["skill"]
        msg_idx = inv["msg_index"]

        # Collect tools after this skill invocation
        post_tools = [tp for tp in tool_positions if tp["msg_index"] > msg_idx]

        # Window: next 50 tool calls after invocation (or until next skill)
        next_skill_idx = total_msgs
        for other in invocations:
            if other["msg_index"] > msg_idx:
                next_skill_idx = min(next_skill_idx, other["msg_index"])
                break
        window_tools = [tp for tp in post_tools if tp["msg_index"] < next_skill_idx][
            :50
        ]

        # Count post-skill signals
        post_edits = sum(
            1
            for tp in window_tools
            if tp["tc"].get("name") in ("Edit", "Write", "MultiEdit", "NotebookEdit")
        )
        post_reads = sum(
            1 for tp in window_tools if tp["tc"].get("name") in ("Read", "Grep", "Glob")
        )
        # For API-format: check input.command; for ccrider-format: check surrounding text
        post_test_runs = 0
        for tp in window_tools:
            if tp["tc"].get("name") != "Bash":
                continue
            cmd = tp["tc"].get("input", {}).get("command", "")
            if cmd and (
                "bundle exec rspec" in cmd
                or "bundle exec minitest" in cmd
                or "rails test" in cmd
            ):
                post_test_runs += 1
            elif not cmd:
                # ccrider-format: tool input is empty, check assistant text at this position
                mi = tp["msg_index"]
                if mi < len(messages) and isinstance(messages[mi], dict):
                    text = _get_content(messages[mi])
                    if isinstance(text, str) and (
                        "bundle exec rspec" in text
                        or "bundle exec minitest" in text
                        or "rails test" in text
                    ):
                        post_test_runs += 1

        # Post-skill errors (from messages in the window)
        window_msgs = [
            m
            for j, m in enumerate(messages)
            if isinstance(m, dict) and j > msg_idx and j < next_skill_idx
        ]
        post_errors = len(extract_errors(window_msgs))

        # Post-skill user corrections
        post_corrections = 0
        for m in window_msgs:
            content = _get_content(m)
            role = _get_role(m)
            if role == "user" and isinstance(content, str):
                if CORRECTION_PATTERNS.search(content[:500]):
                    post_corrections += 1

        # Led to action: skill resulted in edits or test runs
        led_to_action = post_edits > 0 or post_test_runs > 0

        # Outcome heuristic
        if post_errors == 0 and post_corrections == 0 and led_to_action:
            outcome = "effective"
        elif post_corrections > 0 or post_errors > 3:
            outcome = "friction"
        elif not led_to_action:
            outcome = "no_action"
        else:
            outcome = "mixed"

        # Store per-skill (aggregate if same skill invoked multiple times)
        if skill not in results:
            results[skill] = {
                "invocation_count": 0,
                "total_post_edits": 0,
                "total_post_reads": 0,
                "total_post_test_runs": 0,
                "total_post_errors": 0,
                "total_post_corrections": 0,
                "led_to_action_count": 0,
                "outcomes": [],
            }

        r = results[skill]
        r["invocation_count"] += 1
        r["total_post_edits"] += post_edits
        r["total_post_reads"] += post_reads
        r["total_post_test_runs"] += post_test_runs
        r["total_post_errors"] += post_errors
        r["total_post_corrections"] += post_corrections
        if led_to_action:
            r["led_to_action_count"] += 1
        r["outcomes"].append(outcome)

    # Compute summary metrics per skill
    for skill, r in results.items():
        n = r["invocation_count"]
        r["action_rate"] = round(r["led_to_action_count"] / max(n, 1), 2)
        r["avg_post_errors"] = round(r["total_post_errors"] / max(n, 1), 2)
        r["avg_post_corrections"] = round(r["total_post_corrections"] / max(n, 1), 2)
        # Dominant outcome
        outcome_counts = Counter(r["outcomes"])
        r["dominant_outcome"] = (
            outcome_counts.most_common(1)[0][0] if outcome_counts else "unknown"
        )

    return results


# ─── Main Metric Pipeline ────────────────────────────────────────────────────


def compute_session_metrics(data, session_id, project, date=None, provider=None):
    """Compute all metrics for a single session."""
    messages = parse_messages(data)
    tool_calls = extract_tool_calls(messages)
    user_msgs = extract_user_messages(messages)
    errors = extract_errors(messages)
    timestamps = extract_timestamps(messages)

    # Extract files edited/read
    files_edited = set()
    files_read = set()
    for tc in tool_calls:
        name = tc.get("name", "")
        file_paths = extract_file_paths(tc.get("input", {}))
        if not file_paths:
            continue
        if name in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
            files_edited.update(file_paths)
        elif name == "Read":
            files_read.update(file_paths)

    # Extract shipped plugin commands from user messages.
    # Explicitly ignore contributor-only analyzer commands such as /docs-check
    # or /session-scan by only recognizing shipped plugin prefixes.
    rb_commands = extract_plugin_commands(user_msgs)

    provider_name = extract_provider(data, provider)

    # runtime tooling detection
    tool_names = [tc.get("name", "") for tc in tool_calls]
    tidewave_available = any(n.startswith("mcp__tidewave") for n in tool_names)
    tidewave_used = tidewave_available  # If calls exist, it was used

    friction_score, friction_signals = compute_friction(
        tool_calls, user_msgs, errors, messages
    )
    fingerprint, fp_confidence = compute_fingerprint(
        user_msgs, tool_calls, list(files_edited)
    )
    opportunity_score, could_use = compute_plugin_opportunity(
        user_msgs, tool_calls, [c.replace("/rb:", "") for c in rb_commands], messages
    )
    tool_profile = compute_tool_profile(tool_calls)
    bigrams = compute_tool_bigrams(tool_calls)
    hotspots = compute_file_hotspots(tool_calls)
    duration = compute_duration(timestamps)
    skill_effectiveness = compute_skill_effectiveness(
        user_msgs, tool_calls, errors, messages
    )

    # Tier 2 eligibility
    tier2_reasons = []
    if friction_score > 0.35:
        tier2_reasons.append("friction > 0.35")
    if opportunity_score > 0.5:
        tier2_reasons.append("opportunity > 0.5")
    if rb_commands:
        tier2_reasons.append("plugin commands used")
    if len(user_msgs) > 50:
        tier2_reasons.append("message_count > 50")
    tier2_eligible = len(tier2_reasons) > 0

    return {
        "session_id": session_id,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "project": project,
        "provider": provider_name,
        "date": date
        or (
            timestamps[0][:10]
            if timestamps and isinstance(timestamps[0], str)
            else None
        ),
        "duration_minutes": duration,
        "message_count": len(user_msgs),
        "tool_count": len(tool_calls),
        "fingerprint": fingerprint,
        "fingerprint_confidence": fp_confidence,
        "friction_score": friction_score,
        "friction_signals": friction_signals,
        "plugin_opportunity_score": opportunity_score,
        "plugin_signals": {
            "rb_commands_used": sorted(set(rb_commands)),
            "could_use": could_use,
            "tidewave_available": tidewave_available,
            "tidewave_used": tidewave_used,
        },
        "tool_profile": tool_profile,
        "tool_bigrams": bigrams,
        "file_hotspots": hotspots,
        "file_categories": categorize_files(list(files_edited)),
        "skill_effectiveness": skill_effectiveness,
        "session_chain": {"implemented": False},
        "tier2_eligible": tier2_eligible,
        "tier2_reason": " AND ".join(tier2_reasons) if tier2_reasons else None,
        "tier2_completed": False,
    }


# ─── Backfill from v1 Extracts ───────────────────────────────────────────────


def backfill_from_v1(extract_path):
    """Compute v2 metrics from a v1 extract JSON file.

    v1 extracts have tool_usage, user_messages, rb_commands, errors, etc.
    Some v2 signals (user corrections, approach changes) are approximated.
    """
    with open(extract_path) as f:
        v1 = json.load(f)

    session_id = v1.get(
        "session_id", os.path.basename(extract_path).replace(".json", "")
    )
    project = v1.get("project", "unknown")
    tool_usage = v1.get("tool_usage", {})
    total_tools = sum(tool_usage.values())

    # Approximate friction from available v1 data
    error_count = len(v1.get("errors", []))
    error_tool_ratio = round(error_count / max(total_tools, 1), 3)

    # User corrections approximation from user messages
    user_msgs = v1.get("user_messages", [])
    user_corrections = sum(
        1 for text in user_msgs if CORRECTION_PATTERNS.search(text[:500])
    )

    friction_signals = {
        "error_tool_ratio": error_tool_ratio,
        "retry_loops": 0,  # Can't reliably detect from v1 extracts
        "user_corrections": user_corrections,
        "approach_changes": 0,
        "context_compactions": 0,
        "interrupted_requests": 0,
    }
    raw = sum(friction_signals[k] * FRICTION_WEIGHTS[k] for k in FRICTION_WEIGHTS)
    friction_score = round(sigmoid(raw), 3)

    # Fingerprint from v1 data
    user_text = " ".join(user_msgs[:10])
    scores = defaultdict(float)
    for fp_type, pattern in FINGERPRINT_KEYWORDS.items():
        matches = pattern.findall(user_text)
        scores[fp_type] += len(matches) * 2.0

    # Tool profile from v1 tool_usage
    read_count = tool_usage.get("Read", 0) + tool_usage.get("Glob", 0)
    edit_count = tool_usage.get("Edit", 0) + tool_usage.get("Write", 0)
    bash_count = tool_usage.get("Bash", 0)
    grep_count = tool_usage.get("Grep", 0)
    tidewave_count = sum(
        v for k, v in tool_usage.items() if k.startswith("mcp__tidewave")
    )

    if (
        read_count / max(total_tools, 1) > 0.5
        and edit_count / max(total_tools, 1) < 0.1
    ):
        scores["exploration"] += 3.0
    if edit_count / max(total_tools, 1) > 0.3:
        scores["feature"] += 2.0
    if bash_count / max(total_tools, 1) > 0.3:
        scores["bug-fix"] += 2.0

    best = max(scores, key=scores.get) if scores else "unknown"
    total_score = sum(scores.values())
    fp_confidence = (
        round(scores.get(best, 0) / max(total_score, 1), 2) if scores else 0.0
    )

    # Plugin opportunity from v1 rb_commands
    rb_commands = v1.get("rb_commands", [])
    could_use = []
    if total_tools > 50 and not rb_commands:
        could_use.append("plan")
    rails_cmds = v1.get("rails_commands", [])
    test_runs = sum(
        1
        for c in rails_cmds
        if "bundle exec rspec" in c
        or "bundle exec minitest" in c
        or "rails zeitwerk:check" in c
    )
    if test_runs >= 3:
        could_use.append("verify")

    opportunity_score = min(len(could_use) * 0.2, 1.0)

    other_count = max(
        total_tools
        - read_count
        - edit_count
        - bash_count
        - grep_count
        - tidewave_count,
        0,
    )

    return {
        "session_id": session_id,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "backfilled": True,
        "project": project,
        "provider": v1.get("provider", "unknown"),
        "date": None,
        "duration_minutes": v1.get("duration_minutes"),
        "message_count": v1.get("user_message_count", len(user_msgs)),
        "tool_count": total_tools,
        "fingerprint": best,
        "fingerprint_confidence": fp_confidence,
        "friction_score": friction_score,
        "friction_signals": friction_signals,
        "plugin_opportunity_score": round(opportunity_score, 2),
        "plugin_signals": {
            "rb_commands_used": rb_commands,
            "could_use": could_use,
            "tidewave_available": bool(v1.get("tidewave_usage")),
            "tidewave_used": bool(v1.get("tidewave_usage")),
        },
        "tool_profile": {
            "read_pct": round(read_count / max(total_tools, 1) * 100, 1),
            "edit_pct": round(edit_count / max(total_tools, 1) * 100, 1),
            "bash_pct": round(bash_count / max(total_tools, 1) * 100, 1),
            "grep_pct": round(grep_count / max(total_tools, 1) * 100, 1),
            "tidewave_pct": round(tidewave_count / max(total_tools, 1) * 100, 1),
            "other_pct": round(other_count / max(total_tools, 1) * 100, 1),
        },
        "tool_bigrams": {},
        "file_hotspots": [],
        "file_categories": v1.get("file_categories", {}),
        "skill_effectiveness": {},
        "session_chain": {"implemented": False},
        "tier2_eligible": friction_score > 0.35 or opportunity_score > 0.5,
        "tier2_reason": None,
        "tier2_completed": False,
    }


# ─── Trends Computation ──────────────────────────────────────────────────────


def compute_trends(
    metrics_path, notes_path=None, project_filter=None, provider_filter=None
):
    """Compute windowed aggregates from metrics.jsonl."""

    def load_latest_entries(path):
        deduped_entries = {}
        ordered_entries = []
        with open(path, encoding="utf-8") as f:
            for index, line in enumerate(f):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                session_id = entry.get("session_id")
                if session_id:
                    deduped_entries[session_id] = (index, entry)
                else:
                    ordered_entries.append((index, entry))

        ordered_entries.extend(deduped_entries.values())
        ordered_entries.sort(key=lambda item: item[0])
        return [entry for _, entry in ordered_entries]

    entries = []
    for entry in load_latest_entries(metrics_path):
        if project_filter:
            proj = entry.get("project", "")
            if project_filter.lower() not in proj.lower():
                continue
        if provider_filter and provider_filter.lower() != "all":
            provider_name = str(entry.get("provider", "unknown"))
            if provider_name.lower() != provider_filter.lower():
                continue
        entries.append(entry)

    if not entries:
        return {"error": "No metrics found", "total_sessions": 0}

    now = datetime.now(timezone.utc)
    windows = {
        "7d": now - timedelta(days=7),
        "30d": now - timedelta(days=30),
        "all": datetime(2000, 1, 1, tzinfo=timezone.utc),
    }

    def parse_date(entry):
        d = entry.get("date") or entry.get("scanned_at", "")
        if not d:
            return None
        try:
            dt = datetime.fromisoformat(d.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, TypeError):
            try:
                return datetime.strptime(d[:10], "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except (ValueError, TypeError):
                return None

    parsed_dates = []
    for entry in entries:
        parsed = parse_date(entry)
        if parsed is not None:
            parsed_dates.append(parsed)
    distinct_dates = len({dt.date().isoformat() for dt in parsed_dates})
    time_series_signal = "usable"
    if len(entries) < 10 or distinct_dates < 2:
        time_series_signal = "none"
    elif len(entries) < 20 or distinct_dates < 7:
        time_series_signal = "weak"

    trends = {}
    for window_name, cutoff in windows.items():
        window_entries = [
            e
            for e in entries
            if (parse_date(e) or datetime(2000, 1, 1, tzinfo=timezone.utc)) >= cutoff
        ]
        if not window_entries:
            trends[window_name] = {"count": 0}
            continue

        frictions = [e.get("friction_score") or 0 for e in window_entries]
        opportunities = [e.get("plugin_opportunity_score") or 0 for e in window_entries]
        fingerprints = Counter(e.get("fingerprint", "unknown") for e in window_entries)
        tier2_count = sum(1 for e in window_entries if e.get("tier2_eligible"))
        rb_users = sum(
            1
            for e in window_entries
            if e.get("plugin_signals", {}).get("rb_commands_used")
        )
        backfilled = sum(1 for e in window_entries if e.get("backfilled"))
        providers = Counter(e.get("provider", "unknown") for e in window_entries)

        trends[window_name] = {
            "count": len(window_entries),
            "backfilled_count": backfilled,
            "avg_friction": round(sum(frictions) / len(frictions), 3),
            "max_friction": round(max(frictions), 3),
            "avg_opportunity": round(sum(opportunities) / len(opportunities), 3),
            "fingerprint_distribution": dict(fingerprints.most_common()),
            "tier2_eligible_count": tier2_count,
            "tier2_eligible_pct": round(tier2_count / len(window_entries) * 100, 1),
            "plugin_adoption_rate": round(rb_users / len(window_entries) * 100, 1),
            "provider_distribution": dict(providers.most_common()),
        }

    notes_reference = None
    if notes_path:
        notes_reference = {
            "path": notes_path,
            "exists": os.path.exists(notes_path),
        }

    return {
        "computed_at": now.isoformat(),
        "total_sessions": len(entries),
        "provider_filter": provider_filter or "all",
        "immature_ledger": len(entries) < 10,
        "distinct_dates": distinct_dates,
        "time_series_signal": time_series_signal,
        "windows": trends,
        "notes_reference": notes_reference,
    }


# ─── Batch Mode ──────────────────────────────────────────────────────────────


def load_session_data_from_db(db_path, session_id):
    """Load one session's messages and metadata from a ccrider SQLite DB."""
    expanded_db_path = Path(os.path.expandvars(db_path)).expanduser()
    if not expanded_db_path.exists():
        raise FileNotFoundError(f"ccrider DB not found: {expanded_db_path}")
    if not expanded_db_path.is_file():
        raise ValueError(f"ccrider DB path is not a file: {expanded_db_path}")
    uri = f"{expanded_db_path.resolve().as_uri()}?mode=ro"
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise ValueError(
            f"failed to read ccrider DB at {expanded_db_path}: {exc}"
        ) from exc
    try:
        row = conn.execute(
            (
                "SELECT id, project_path, provider, updated_at "
                "FROM sessions WHERE session_id = ?"
            ),
            (session_id,),
        ).fetchone()
        if not row:
            raise LookupError(f"session_id not found in DB: {session_id}")
        session_pk = row[0]
        project_path = row[1]
        provider = row[2]
        updated_at = row[3]
        rows = conn.execute(
            "SELECT content FROM messages WHERE session_id = ? ORDER BY sequence",
            (session_pk,),
        ).fetchall()
    except sqlite3.Error as exc:
        raise ValueError(
            f"failed to read ccrider DB at {expanded_db_path}: {exc}"
        ) from exc
    finally:
        conn.close()
    messages = []
    decode_failures = 0
    non_empty_rows = 0
    for (content,) in rows:
        if not content:
            continue
        non_empty_rows += 1
        try:
            messages.append(json.loads(content))
        except json.JSONDecodeError:
            decode_failures += 1
            continue
    if decode_failures:
        print(
            (
                f"WARNING: skipped {decode_failures} malformed message row(s) "
                f"while loading session {session_id} from {expanded_db_path}"
            ),
            file=sys.stderr,
        )
        if not messages and non_empty_rows:
            raise ValueError(
                f"failed to decode all {non_empty_rows} non-empty message row(s) "
                f"for session {session_id} in {expanded_db_path}"
            )
    metadata = {
        "project": normalize_project_path(project_path),
        "provider": provider or "unknown",
        "date": (updated_at or "")[:10] or None,
        "decode_failures": decode_failures,
    }
    return messages, metadata


def load_messages_from_db(db_path, session_id):
    """Load messages for one session directly from a ccrider SQLite DB."""
    messages, _metadata = load_session_data_from_db(db_path, session_id)
    return messages


def run_batch(manifest_path):
    """Process multiple sessions from a manifest file.

    Manifest format: JSON array of {session_id, project, messages_path}
    Appends results to metrics.jsonl in the same directory.
    """
    with open(manifest_path) as f:
        manifest = json.load(f)

    output_dir = os.path.dirname(manifest_path) or "."
    metrics_path = os.path.join(output_dir, "metrics.jsonl")

    results = []
    for i, entry in enumerate(manifest):
        sid = entry["session_id"]
        project = entry.get("project", "unknown")
        msg_path = entry["messages_path"]

        print(f"[{i + 1}/{len(manifest)}] {project}/{sid[:12]}... ", end="", flush=True)

        try:
            with open(msg_path) as f:
                data = json.load(f)
            metrics = compute_session_metrics(
                data, sid, project, provider=entry.get("provider")
            )
            results.append(metrics)

            with open(metrics_path, "a") as f:
                f.write(json.dumps(metrics) + "\n")

            print(
                f"OK (friction={metrics['friction_score']}, fp={metrics['fingerprint']})"
            )
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nDone: {len(results)} sessions processed -> {metrics_path}")
    return results


# ─── CLI ──────────────────────────────────────────────────────────────────────


def print_usage():
    print("Usage:")
    print(
        "  python3 compute-metrics.py <messages.json> --session-id ID --project NAME [--provider NAME]"
    )
    print(
        "  python3 compute-metrics.py --from-db SESSION_ID --db PATH [--project NAME] [--provider NAME]"
    )
    print("  python3 compute-metrics.py --batch <manifest.json>")
    print(
        "  python3 compute-metrics.py --trends <metrics.jsonl> [--project NAME] [--provider NAME] [--notes PATH]"
    )
    print("  python3 compute-metrics.py --backfill <extracts-dir/>")
    print("  python3 compute-metrics.py --help")
    print(
        "\nFor full scans prefer scan-sessions.py (discovery + dedup + triage)."
    )


if __name__ == "__main__":
    if len(sys.argv) < 2 or "--help" in sys.argv:
        print_usage()
        sys.exit(0)

    mode = sys.argv[1]

    if mode == "--batch":
        if len(sys.argv) < 3:
            print("Error: --batch requires manifest path")
            sys.exit(1)
        run_batch(sys.argv[2])

    elif mode == "--trends":
        if len(sys.argv) < 3:
            print("Error: --trends requires metrics.jsonl path")
            sys.exit(1)
        notes_path = None
        if "--notes" in sys.argv:
            idx = sys.argv.index("--notes")
            if idx + 1 < len(sys.argv):
                notes_path = sys.argv[idx + 1]
        elif "--memory" in sys.argv:
            idx = sys.argv.index("--memory")
            if idx + 1 < len(sys.argv):
                notes_path = sys.argv[idx + 1]
        project_filter = None
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            if idx + 1 < len(sys.argv):
                project_filter = sys.argv[idx + 1]
        provider_filter = None
        if "--provider" in sys.argv:
            idx = sys.argv.index("--provider")
            if idx + 1 < len(sys.argv):
                provider_filter = sys.argv[idx + 1]
        result = compute_trends(
            sys.argv[2],
            notes_path=notes_path,
            project_filter=project_filter,
            provider_filter=provider_filter,
        )
        print(json.dumps(result, indent=2))

    elif mode == "--from-db":
        if len(sys.argv) < 3:
            print("Error: --from-db requires SESSION_ID")
            sys.exit(1)
        session_id = sys.argv[2]
        db_path = None
        project = None
        provider = None
        if "--db" in sys.argv:
            idx = sys.argv.index("--db")
            if idx + 1 < len(sys.argv):
                db_path = sys.argv[idx + 1]
        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            if idx + 1 < len(sys.argv):
                project = sys.argv[idx + 1]
        if "--provider" in sys.argv:
            idx = sys.argv.index("--provider")
            if idx + 1 < len(sys.argv):
                provider = sys.argv[idx + 1]
        if not db_path:
            print("Error: --from-db requires --db PATH", file=sys.stderr)
            sys.exit(1)
        try:
            messages, metadata = load_session_data_from_db(db_path, session_id)
        except FileNotFoundError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(2)
        except LookupError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
        metrics = compute_session_metrics(
            messages,
            session_id,
            project or metadata["project"],
            date=metadata["date"],
            provider=provider or metadata["provider"],
        )
        print(json.dumps(metrics, indent=2))

    elif mode == "--backfill":
        if len(sys.argv) < 3:
            print("Error: --backfill requires extracts directory")
            sys.exit(1)
        extracts_dir = sys.argv[2]
        if not os.path.isdir(extracts_dir):
            print(f"Error: {extracts_dir} is not a directory")
            sys.exit(1)

        metrics_path = os.environ.get(
            "METRICS_PATH",
            os.path.join(
                os.path.dirname(extracts_dir), "session-metrics", "metrics.jsonl"
            ),
        )
        os.makedirs(os.path.dirname(metrics_path), exist_ok=True)

        # Load existing session IDs to skip
        existing_ids = set()
        if os.path.exists(metrics_path):
            with open(metrics_path) as f:
                for line in f:
                    try:
                        existing_ids.add(json.loads(line).get("session_id"))
                    except json.JSONDecodeError:
                        continue

        files = sorted(
            f
            for f in os.listdir(extracts_dir)
            if f.endswith(".json") and not f.startswith("_")
        )
        processed = 0
        skipped = 0

        for fname in files:
            fpath = os.path.join(extracts_dir, fname)
            try:
                with open(fpath) as f:
                    v1 = json.load(f)
                sid = v1.get("session_id", fname.replace(".json", ""))
                if sid in existing_ids:
                    skipped += 1
                    continue
                metrics = backfill_from_v1(fpath)
                with open(metrics_path, "a") as f:
                    f.write(json.dumps(metrics) + "\n")
                processed += 1
                print(f"  Backfilled: {fname} (friction={metrics['friction_score']})")
            except Exception as e:
                print(f"  Error: {fname}: {e}")

        print(
            f"\nBackfill complete: {processed} new, {skipped} skipped -> {metrics_path}"
        )

    else:
        # Single session mode
        messages_path = mode
        session_id = None
        project = "unknown"
        provider = None

        if "--session-id" in sys.argv:
            idx = sys.argv.index("--session-id")
            if idx + 1 < len(sys.argv):
                session_id = sys.argv[idx + 1]

        if "--project" in sys.argv:
            idx = sys.argv.index("--project")
            if idx + 1 < len(sys.argv):
                project = sys.argv[idx + 1]
        if "--provider" in sys.argv:
            idx = sys.argv.index("--provider")
            if idx + 1 < len(sys.argv):
                provider = sys.argv[idx + 1]

        if not session_id:
            session_id = os.path.basename(messages_path).replace(".json", "")

        with open(messages_path) as f:
            data = json.load(f)

        metrics = compute_session_metrics(data, session_id, project, provider=provider)
        print(json.dumps(metrics))
