"""Agent-specific structural matchers."""

from __future__ import annotations

from typing import Any

from .matchers import parse_frontmatter


def tools_present(content: str, min_count: int = 1, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = fm.get("tools", [])
    if isinstance(tools, str):
        tools = [tools]
    count = len(tools)
    return count >= min_count, f"{count} tools listed"


def disallowed_tools_present(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = fm.get("disallowedTools", [])
    if isinstance(tools, str):
        tools = [tools]
    return bool(tools), "disallowedTools present" if tools else "disallowedTools missing"


def permission_mode_valid(content: str, allowed: list[str] | None = None, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    mode = fm.get("permissionMode", "")
    if not mode:
        return True, "permissionMode absent (acceptable for shipped plugin agents)"
    accepted = allowed or ["bypassPermissions", "default", "acceptEdits", "plan"]
    return mode in accepted, f"permissionMode={mode!r}"


def effort_present(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    effort = fm.get("effort", "")
    return bool(effort), f"effort={effort!r}"


def read_only_tools_coherent(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = fm.get("tools", [])
    disallowed = fm.get("disallowedTools", [])
    if isinstance(tools, str):
        tools = [tools]
    if isinstance(disallowed, str):
        disallowed = [disallowed]
    write_like_tools = {"Write", "Edit", "NotebookEdit"}

    if "Read" not in tools:
        return True, "no read tool; read-only coherence not applicable"

    if "Write" in tools:
        return True, "agent has explicit write access; not treated as read-only"

    if write_like_tools.intersection(disallowed):
        return True, "read-oriented restrictions present"

    return False, "Read tool present without disallowing write-capable tools"


MATCHERS = {
    "tools_present": tools_present,
    "disallowed_tools_present": disallowed_tools_present,
    "permission_mode_valid": permission_mode_valid,
    "effort_present": effort_present,
    "read_only_tools_coherent": read_only_tools_coherent,
}
