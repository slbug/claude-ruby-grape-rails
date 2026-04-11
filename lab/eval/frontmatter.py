"""Shared YAML frontmatter parser for eval tooling.

Lightweight delimiter-aware parser for SKILL.md and agent frontmatter.
Not a full YAML parser — handles the subset used by Claude Code plugin files.
"""

from __future__ import annotations

import re
from typing import Any

LIST_LIKE_FRONTMATTER_KEYS = {"tools", "disallowedTools", "skills"}


def _coerce_scalar(value: str) -> Any:
    raw = value.strip().strip('"').strip("'")
    lowered = raw.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if re.fullmatch(r"-?\d+", raw):
        return int(raw)
    return raw


def _coerce_frontmatter_value(key: str, value: str) -> Any:
    if key in LIST_LIKE_FRONTMATTER_KEYS and "," in value:
        return [_coerce_scalar(part) for part in value.split(",") if part.strip()]
    return _coerce_scalar(value)


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from a --- delimited block."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    end = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end = index
            break
    if end is None:
        return {}

    data: dict[str, Any] = {}
    body = lines[1:end]
    i = 0
    while i < len(body):
        line = body[i]
        if not line.strip():
            i += 1
            continue
        match = re.match(r"^([A-Za-z0-9_-]+):(?:\s+(.*))?$", line)
        if not match:
            i += 1
            continue
        key = match.group(1)
        value = (match.group(2) or "").rstrip()
        if value:
            data[key] = _coerce_frontmatter_value(key, value)
            i += 1
            continue

        items: list[Any] = []
        j = i + 1
        while j < len(body) and re.match(r"^\s*-\s+", body[j]):
            items.append(_coerce_scalar(re.sub(r"^\s*-\s+", "", body[j], count=1)))
            j += 1
        if items:
            data[key] = items
        else:
            data[key] = [] if key in LIST_LIKE_FRONTMATTER_KEYS else ""
        i = j
    return data


def get_body(content: str) -> str:
    """Return content after the frontmatter block."""
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1:]).strip()
    return content
