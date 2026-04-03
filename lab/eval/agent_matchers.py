"""Agent-specific structural matchers."""

from __future__ import annotations

from typing import Any

from .matchers import parse_frontmatter


def tools_present(content: str, min_count: int = 1, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = _coerce_tool_list(fm.get("tools", []))
    disallowed = _coerce_tool_list(fm.get("disallowedTools", []))
    if not tools and disallowed:
        return True, "denylist-only agent (inherits all tools minus disallowed)"
    count = len(tools)
    return count >= min_count, f"{count} tools listed"


def disallowed_tools_present(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = _coerce_tool_list(fm.get("disallowedTools", []))
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


def _coerce_tool_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [part.strip() for part in value.split(",") if part.strip()]
    return []


def read_only_tools_coherent(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = _coerce_tool_list(fm.get("tools", []))
    disallowed = _coerce_tool_list(fm.get("disallowedTools", []))
    write_like_tools = {"Write", "Edit", "NotebookEdit"}

    # Denylist-only agents: coherent if they have any disallowed tools
    if not tools and disallowed:
        if write_like_tools.intersection(disallowed):
            return True, "denylist-only with write restrictions"
        return True, "denylist-only agent (Edit/NotebookEdit restrictions expected)"

    if "Read" not in tools:
        return True, "no read tool; read-only coherence not applicable"

    if write_like_tools.intersection(tools):
        return True, "agent has explicit write access; not treated as read-only"

    if write_like_tools.intersection(disallowed):
        return True, "read-oriented restrictions present"

    return False, "Read tool present without disallowing write-capable tools"


def omit_claudemd_coherent(content: str, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    tools = _coerce_tool_list(fm.get("tools", []))
    disallowed = _coerce_tool_list(fm.get("disallowedTools", []))
    omit_claudemd = fm.get("omitClaudeMd")
    write_like_tools = {"Write", "Edit", "NotebookEdit"}

    # Denylist-only agents: omitClaudeMd is acceptable (specialists don't need
    # contributor context regardless of Write access)
    if not tools and disallowed:
        if omit_claudemd is True:
            return True, "specialist agent omits CLAUDE.md"
        # Denylist-only without omitClaudeMd is also acceptable (orchestrators)
        return True, "denylist-only agent without omitClaudeMd (acceptable)"

    # Allowlist agents: write-capable agents should keep CLAUDE.md
    if write_like_tools.intersection(tools):
        if omit_claudemd is True:
            return False, "write-capable allowlist agent should not set omitClaudeMd"
        return True, "write-capable agent keeps CLAUDE.md context"

    # Allowlist read-only agents: should set omitClaudeMd
    if omit_claudemd is True:
        return True, "read-only agent omits CLAUDE.md"

    agent_name = str(fm.get("name", "agent"))
    return False, f"read-only agent {agent_name!r} missing omitClaudeMd: true"


MATCHERS = {
    "tools_present": tools_present,
    "disallowed_tools_present": disallowed_tools_present,
    "permission_mode_valid": permission_mode_valid,
    "effort_present": effort_present,
    "read_only_tools_coherent": read_only_tools_coherent,
    "omit_claudemd_coherent": omit_claudemd_coherent,
}
