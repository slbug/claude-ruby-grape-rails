"""Validate internal skill/agent cross-references.

Scans plugin tree for references to skills (/rb:<name>, skills/<name>) and
agents, confirms each resolves to a file on disk. Exit 0 if all valid,
exit 1 otherwise. Code fences are skipped so example references inside
code blocks do not raise false positives.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

SLASH_REF_RE = re.compile(r"/rb:([a-z][a-z0-9-]+)")
PATH_SKILL_REF_RE = re.compile(r"skills/([a-z][a-z0-9-]+)")
PATH_AGENT_REF_RE = re.compile(r"agents/([a-z][a-z0-9-]+)")
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)
# Fenced code blocks open with 3+ backticks or tildes followed by an
# optional info string (`````ruby`, `````bash my-file.sh`, etc). Closing
# fences per CommonMark MAY NOT carry an info string — they are the
# delimiter run on its own (with optional surrounding whitespace). Two
# regexes keep the asymmetry explicit so a `````ruby` line inside an
# outer 3-backtick block is NOT matched as a close.
FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")


@dataclass
class BrokenRef:
    source: str
    target: str
    line: int


@dataclass
class ScanResult:
    broken: list[BrokenRef] = field(default_factory=list)


def _frontmatter_name(md_path: Path) -> str | None:
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    m = FRONTMATTER_NAME_RE.search(parts[1])
    return m.group(1) if m else None


def _skill_universe(plugin_root: Path) -> tuple[set[str], set[str]]:
    """Return (dir_names, slash_aliases) for the skills tree.

    `dir_names` resolves `skills/<name>` path references and contains every
    skill directory name.
    `slash_aliases` resolves `/rb:<name>` invocations and contains ONLY
    skills whose frontmatter `name:` starts with `rb:` — i.e. user-invocable
    slash commands. Auto-loading reference skills (e.g. `name:
    active-record-patterns`) are intentionally excluded so a typo like
    `/rb:active-record-patterns` does not falsely resolve.
    """
    skills_dir = plugin_root / "skills"
    if not skills_dir.is_dir():
        return set(), set()
    dir_names: set[str] = set()
    aliases: set[str] = set()
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        dir_names.add(skill_dir.name)
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            continue
        name = _frontmatter_name(skill_md)
        if name and name.startswith("rb:"):
            aliases.add(name.removeprefix("rb:"))
    return dir_names, aliases


def _agent_names(plugin_root: Path) -> set[str]:
    agents_dir = plugin_root / "agents"
    if not agents_dir.is_dir():
        return set()
    out: set[str] = set()
    for agent_md in agents_dir.glob("*.md"):
        out.add(agent_md.stem)
        name = _frontmatter_name(agent_md)
        if name:
            out.add(name)
    return out


def _iter_non_fenced_lines(text: str):
    """Yield (lineno, line) tuples skipping fenced code blocks.

    Tracks the opening delimiter character and length so that a closing
    fence must use the same character and at least as many of them. The
    close match also requires the line to be *only* the delimiter run
    (CommonMark forbids info strings on closing fences) so an inner
    `````ruby` line inside an outer 3-backtick block does not falsely
    end the outer fence.
    """
    open_delim: str | None = None
    for lineno, line in enumerate(text.splitlines(), start=1):
        if open_delim is None:
            m = FENCE_OPEN_RE.match(line)
            if m:
                open_delim = m.group(1)
                continue
            yield lineno, line
            continue
        # Inside a fence — close only on a delimiter-only line whose
        # delimiter character matches the opener and whose length is at
        # least the opener's length.
        m = FENCE_CLOSE_RE.match(line)
        if m and m.group(1)[0] == open_delim[0] and len(m.group(1)) >= len(open_delim):
            open_delim = None
            continue
        # Still fenced; skip.


def scan(plugin_root: Path) -> ScanResult:
    skill_dirs, skill_aliases = _skill_universe(plugin_root)
    agents = _agent_names(plugin_root)
    # `/rb:<name>` resolves only via `rb:`-prefixed frontmatter aliases;
    # bare directory names are NOT a valid slash command.
    slash_universe = skill_aliases
    result = ScanResult()
    for md in plugin_root.rglob("*.md"):
        rel = md.relative_to(plugin_root)
        text = md.read_text(encoding="utf-8", errors="replace")
        for lineno, line in _iter_non_fenced_lines(text):
            for m in SLASH_REF_RE.finditer(line):
                target = m.group(1)
                if target not in slash_universe:
                    result.broken.append(
                        BrokenRef(source=str(rel), target=target, line=lineno)
                    )
            for m in PATH_SKILL_REF_RE.finditer(line):
                target = m.group(1)
                if target not in skill_dirs:
                    result.broken.append(
                        BrokenRef(source=str(rel), target=target, line=lineno)
                    )
            for m in PATH_AGENT_REF_RE.finditer(line):
                target = m.group(1)
                if target not in agents:
                    result.broken.append(
                        BrokenRef(source=str(rel), target=target, line=lineno)
                    )
    return result


def main(argv: list[str]) -> int:
    plugin_root = Path(argv[1]) if len(argv) > 1 else Path("plugins/ruby-grape-rails")
    result = scan(plugin_root)
    if not result.broken:
        print(f"check-refs: clean ({plugin_root})")
        return 0
    print(f"check-refs: {len(result.broken)} broken references in {plugin_root}")
    for ref in result.broken:
        print(f"  {ref.source}:{ref.line}: unknown -> {ref.target}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
