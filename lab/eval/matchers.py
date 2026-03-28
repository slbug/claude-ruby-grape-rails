"""Deterministic matcher functions for Ruby plugin skill evals."""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PROJECT_ROOT / "plugins" / "ruby-grape-rails"
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
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return content
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            return "\n".join(lines[index + 1:]).strip()
    return content


def get_sections(content: str) -> dict[str, str]:
    body = get_body(content)
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in body.splitlines():
        if line.startswith("## ") or line.startswith("### "):
            current = line.lstrip("#").strip()
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)
    return {name: "\n".join(lines).strip() for name, lines in sections.items()}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def tokenize(text: str) -> set[str]:
    return {token for token in normalize_text(text).split(" ") if len(token) > 2}


def section_exists(content: str, section: str, **_: Any) -> tuple[bool, str]:
    sections = get_sections(content)
    for name in sections:
        if name.lower() == section.lower():
            return True, f"Section '{section}' found"
    return False, f"Section '{section}' not found"


def frontmatter_field(content: str, field: str, expected: Any | None = None, **_: Any) -> tuple[bool, str]:
    fm = parse_frontmatter(content)
    if field not in fm:
        return False, f"Frontmatter field '{field}' missing"
    if expected is not None and fm[field] != expected:
        return False, f"Frontmatter '{field}' is '{fm[field]}' (expected '{expected}')"
    return True, f"Frontmatter '{field}' present"


def description_length(content: str, min: int = 50, max: int = 280, **_: Any) -> tuple[bool, str]:
    desc = str(parse_frontmatter(content).get("description", ""))
    size = len(desc)
    passed = min <= size <= max
    return passed, f"description length={size} (expected {min}-{max})"


def description_keywords(content: str, min: int = 4, keywords: list[str] | None = None, **_: Any) -> tuple[bool, str]:
    desc = str(parse_frontmatter(content).get("description", "")).lower()
    domain = keywords or [
        "ruby", "rails", "grape", "sidekiq", "karafka", "sequel",
        "active record", "postgres", "redis", "hotwire", "brakeman",
        "rubocop", "zeitwerk", "research", "review", "verify",
        "plan", "work", "permissions", "migration", "security",
    ]
    found = sorted({item for item in domain if item in desc})
    return len(found) >= min, f"{len(found)} keywords found: {found[:8]}"


def description_structure(content: str, **_: Any) -> tuple[bool, str]:
    desc = str(parse_frontmatter(content).get("description", "")).lower()
    passed = ("use for" in desc or "use when" in desc or "use to" in desc) and (
        "plan" in desc or "review" in desc or "verify" in desc or "work" in desc
    )
    return passed, "description has explicit use/intent framing"


def has_iron_laws(content: str, min_count: int = 1, **_: Any) -> tuple[bool, str]:
    sections = get_sections(content)
    iron = next((body for name, body in sections.items() if name.lower() == "iron laws"), "")
    count = len(re.findall(r"^\d+\.\s", iron, flags=re.MULTILINE))
    if count == 0:
        count = len(re.findall(r"^[-*]\s", iron, flags=re.MULTILINE))
    return count >= min_count, f"{count} iron law items"


def line_count(content: str, target: int = 140, tolerance: int = 180, **_: Any) -> tuple[bool, str]:
    lines = len(content.splitlines())
    passed = lines <= target + tolerance
    return passed, f"{lines} lines (target+tolerance={target + tolerance})"


def max_section_lines(content: str, max: int = 55, **_: Any) -> tuple[bool, str]:
    sections = get_sections(content)
    offenders = [f"{name} ({len(body.splitlines())})" for name, body in sections.items() if len(body.splitlines()) > max]
    return not offenders, "all sections within limit" if not offenders else f"oversized sections: {offenders}"


def content_present(content: str, pattern: str, **_: Any) -> tuple[bool, str]:
    match = re.search(pattern, content, flags=re.MULTILINE)
    return bool(match), f"pattern '{pattern}' {'found' if match else 'missing'}"


def content_absent(content: str, pattern: str, **_: Any) -> tuple[bool, str]:
    match = re.search(pattern, content, flags=re.MULTILINE)
    return not bool(match), f"pattern '{pattern}' {'absent' if not match else 'present'}"


def action_density(content: str, min_ratio: float = 0.15, **_: Any) -> tuple[bool, str]:
    body = get_body(content)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return False, "no body lines"
    actionable = [
        line for line in lines
        if line.startswith(("-", "*", "1.", "2.", "3.", "`"))
        or line.lower().startswith(("run ", "read ", "check ", "use ", "write ", "spawn "))
    ]
    ratio = len(actionable) / len(lines)
    return ratio >= min_ratio, f"action density={ratio:.2f}"


def specificity_ratio(content: str, min_ratio: float = 0.12, **_: Any) -> tuple[bool, str]:
    body = get_body(content)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    if not lines:
        return False, "no body lines"
    specific = [
        line for line in lines
        if "`" in line or "/" in line or "::" in line or re.search(r"\b(rb:|bundle exec|rails |rake |rspec|rubocop|sidekiq|grape)\b", line)
    ]
    ratio = len(specific) / len(lines)
    return ratio >= min_ratio, f"specificity ratio={ratio:.2f}"


def has_examples(content: str, min_blocks: int = 1, **_: Any) -> tuple[bool, str]:
    blocks = len(re.findall(r"^```", content, flags=re.MULTILINE)) // 2
    return blocks >= min_blocks, f"{blocks} fenced code blocks"


def no_duplication(content: str, **_: Any) -> tuple[bool, str]:
    seen: dict[str, int] = {}
    duplicates: list[str] = []
    for line in get_body(content).splitlines():
        stripped = line.strip()
        if len(stripped) < 20:
            continue
        seen[stripped] = seen.get(stripped, 0) + 1
        if seen[stripped] == 2:
            duplicates.append(stripped[:60])
    return not duplicates, "no repeated long lines" if not duplicates else f"duplicate lines: {duplicates[:3]}"


def workflow_step_coverage(content: str, min_sections: int = 3, **_: Any) -> tuple[bool, str]:
    sections = get_sections(content)
    return len(sections) >= min_sections, f"{len(sections)} sections"


def valid_skill_refs(content: str, plugin_root: str = "", **_: Any) -> tuple[bool, str]:
    root = Path(plugin_root) if plugin_root else PLUGIN_ROOT
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return True, "skill directory missing; skipped"
    existing = {item.name for item in skills_dir.iterdir() if item.is_dir()}
    refs = set(re.findall(r"/rb:([a-z0-9][a-z0-9-]*)", content))
    missing = [ref for ref in refs if ref not in existing]
    return not missing, "all skill refs valid" if not missing else f"missing skills: {missing}"


def valid_agent_refs(content: str, plugin_root: str = "", **_: Any) -> tuple[bool, str]:
    root = Path(plugin_root) if plugin_root else PLUGIN_ROOT
    agents_dir = root / "agents"
    if not agents_dir.is_dir():
        return True, "agent directory missing; skipped"
    existing = {item.stem for item in agents_dir.glob("*.md")}
    refs = set(re.findall(r"`([a-z0-9][a-z0-9-]+)`", content))
    candidate_refs = sorted(ref for ref in refs if ref in existing or ref.endswith("-reviewer") or ref.endswith("-runner") or ref.endswith("-analyzer"))
    missing = [ref for ref in candidate_refs if ref not in existing]
    return not missing, "all agent refs valid" if not missing else f"missing agents: {missing}"


def valid_file_refs(content: str, skill_path: str = "", **_: Any) -> tuple[bool, str]:
    if not skill_path:
        return True, "no skill path supplied"
    skill_dir = Path(skill_path).resolve().parent
    local_refs = set(re.findall(r"`(?:\$\{CLAUDE_SKILL_DIR\}/)?(references/[A-Za-z0-9_./-]+\.md)`", content))
    missing = [ref for ref in sorted(local_refs) if not (skill_dir / ref).is_file()]
    return not missing, "all local references valid" if not missing else f"missing refs: {missing}"


def no_dangerous_patterns(content: str, **_: Any) -> tuple[bool, str]:
    patterns = [
        r"rm\s+-rf\s+/",
        r"rm\s+-fr\s+/",
        r"git reset --hard",
        r"curl\s+[^|]+\|\s*sh",
        r"sudo\s+rm",
    ]
    hits = [pattern for pattern in patterns if re.search(pattern, content)]
    return not hits, "no catastrophic patterns" if not hits else f"dangerous patterns: {hits}"


MATCHERS = {
    "section_exists": section_exists,
    "frontmatter_field": frontmatter_field,
    "description_length": description_length,
    "description_keywords": description_keywords,
    "description_structure": description_structure,
    "has_iron_laws": has_iron_laws,
    "line_count": line_count,
    "max_section_lines": max_section_lines,
    "content_present": content_present,
    "content_absent": content_absent,
    "action_density": action_density,
    "specificity_ratio": specificity_ratio,
    "has_examples": has_examples,
    "no_duplication": no_duplication,
    "workflow_step_coverage": workflow_step_coverage,
    "valid_skill_refs": valid_skill_refs,
    "valid_agent_refs": valid_agent_refs,
    "valid_file_refs": valid_file_refs,
    "no_dangerous_patterns": no_dangerous_patterns,
}
