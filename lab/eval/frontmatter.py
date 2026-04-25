"""Shared YAML frontmatter parser for eval tooling.

Lightweight delimiter-aware parser for SKILL.md and agent frontmatter.
Not a full YAML parser — handles the subset used by Claude Code plugin files.
"""


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


def _find_delimiter_lines(content: str) -> tuple[list[str], int] | None:
    """Locate the closing `---` line index for a frontmatter block.

    Returns `(lines, end)` where `lines` is the full split content and
    `end` is the index of the closing `---` line. Returns None when no
    frontmatter is present or the closing delimiter is missing. Both
    delimiters are matched line-aware (`strip() == "---"`) so `---`
    inside a YAML value cannot mis-split the block.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return lines, index
    return None


def extract_frontmatter_block(content: str) -> str | None:
    """Return the raw YAML text between leading `---` delimiter lines.

    Line-aware: only `---` on its own line (after `strip()`) is treated
    as a delimiter, so `---` appearing inside a YAML value (URL, string)
    does not mis-split the frontmatter. Returns the inner YAML body
    (without the `---` lines themselves) or None when no frontmatter is
    present or the closing delimiter is missing.

    Use this when feeding the block to `yaml.safe_load` for full-YAML
    parsing; use `parse_frontmatter` for the flat-key subset.
    """
    found = _find_delimiter_lines(content)
    if found is None:
        return None
    lines, end = found
    return "\n".join(lines[1:end])


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse YAML frontmatter from a --- delimited block."""
    block = extract_frontmatter_block(content)
    if block is None:
        return {}
    body = block.splitlines()
    data: dict[str, Any] = {}
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
    found = _find_delimiter_lines(content)
    if found is None:
        return content
    lines, end = found
    return "\n".join(lines[end + 1 :]).strip()
