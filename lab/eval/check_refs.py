"""Validate internal skill/agent cross-references.

Scans plugin tree for references to skills (/rb:<name>, skills/<name>) and
agents, confirms each resolves to a file on disk. Also validates registry
reference_files (iron-laws.yml, preferences.yml) and detects orphan
reference docs unreachable from any SKILL.md, agent, contributor rule, or
registry. Exit 0 if all valid, exit 1 otherwise. Code fences are skipped
so example references inside code blocks do not raise false positives.
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .frontmatter import parse_frontmatter

SLASH_REF_RE = re.compile(r"/rb:([a-z][a-z0-9-]+)")
PATH_SKILL_REF_RE = re.compile(r"skills/([a-z][a-z0-9-]+)")
PATH_AGENT_REF_RE = re.compile(r"agents/([a-z][a-z0-9-]+)")
REFERENCE_PATH_RE = re.compile(r"references/[A-Za-z0-9_./-]+\.md")
SKILL_REL_REF_RE = re.compile(r"skills/[A-Za-z0-9_./-]+\.md")
PLUGIN_VAR_RE = re.compile(r"\$\{CLAUDE_(?:PLUGIN_ROOT|SKILL_DIR)\}/([A-Za-z0-9_./-]+\.md)")
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
class RegistryBrokenRef:
    registry: str
    entry_id: str
    target: str


@dataclass
class OrphanRef:
    path: str


@dataclass
class ScanResult:
    broken: list[BrokenRef] = field(default_factory=list)
    registry_broken: list[RegistryBrokenRef] = field(default_factory=list)
    orphans: list[OrphanRef] = field(default_factory=list)


def _frontmatter_name(md_path: Path) -> str | None:
    """Extract the frontmatter `name:` value via the shared parser.

    Reuses `lab.eval.frontmatter.parse_frontmatter` so cross-reference
    resolution applies the same parsing rules as the rest of the eval
    suite (leading-whitespace tolerance, quote stripping, etc).
    """
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    name = parse_frontmatter(text).get("name")
    return name if isinstance(name, str) and name else None


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

    Unterminated-fence policy: if a file ends inside an open fence
    (missing closing delimiter), we conservatively yield the buffered
    in-fence lines back as scannable content. This trades CommonMark
    purity for not silently swallowing an entire tail of references
    that the author probably intended as prose.
    """
    open_delim: str | None = None
    fenced_buffer: list[tuple[int, str]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        if open_delim is None:
            m = FENCE_OPEN_RE.match(line)
            if m:
                open_delim = m.group(1)
                fenced_buffer = []
                continue
            yield lineno, line
            continue
        # Inside a fence — close only on a delimiter-only line whose
        # delimiter character matches the opener and whose length is at
        # least the opener's length.
        m = FENCE_CLOSE_RE.match(line)
        if m and m.group(1)[0] == open_delim[0] and len(m.group(1)) >= len(open_delim):
            open_delim = None
            fenced_buffer = []
            continue
        fenced_buffer.append((lineno, line))
    if open_delim is not None:
        # Fence never closed — fall back to scanning the buffered lines.
        yield from fenced_buffer


def _registry_reference_files(plugin_root: Path) -> list[tuple[str, str, str]]:
    """Yield (registry_label, entry_id, ref_path) for every reference_files entry."""
    out: list[tuple[str, str, str]] = []
    for label, rel in (
        ("iron-laws.yml", "references/iron-laws.yml"),
        ("preferences.yml", "references/preferences.yml"),
    ):
        path = plugin_root / rel
        if not path.is_file():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        entries = data.get("laws") or data.get("preferences") or []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            refs = entry.get("reference_files")
            if not isinstance(refs, list):
                continue
            entry_id = str(entry.get("id", "?"))
            for ref in refs:
                if isinstance(ref, str) and ref.strip():
                    out.append((label, entry_id, ref))
    return out


def _validate_registry_refs(plugin_root: Path) -> list[RegistryBrokenRef]:
    broken: list[RegistryBrokenRef] = []
    for label, entry_id, ref in _registry_reference_files(plugin_root):
        if not (plugin_root / ref).is_file():
            broken.append(RegistryBrokenRef(registry=label, entry_id=entry_id, target=ref))
    return broken


def _all_reference_md_files(plugin_root: Path) -> set[Path]:
    out: set[Path] = set()
    for ref_dir in plugin_root.rglob("references"):
        if not ref_dir.is_dir():
            continue
        for md in ref_dir.rglob("*.md"):
            out.add(md.relative_to(plugin_root))
    return out


def _collect_referenced_paths(plugin_root: Path, repo_root: Path) -> set[str]:
    """Return reference paths (relative to plugin_root) reachable from any source.

    Sources scanned: every plugin .md file (skill bodies, agents, references),
    contributor rules under .claude/rules + .claude/skills, root CLAUDE.md and
    README.md, and registry reference_files lists. Patterns matched:

    - bare ``references/foo.md`` and ``references/sub/foo.md``
    - ``skills/<skill>/references/foo.md`` (cross-skill plugin paths)
    - ``${CLAUDE_PLUGIN_ROOT}/...`` and ``${CLAUDE_SKILL_DIR}/...`` substitution forms
    """
    referenced: set[str] = set()

    # Registry reference_files
    for _label, _eid, ref in _registry_reference_files(plugin_root):
        referenced.add(ref)

    sources: list[Path] = []
    for md in plugin_root.rglob("*.md"):
        sources.append(md)
    bin_dir = plugin_root / "bin"
    if bin_dir.is_dir():
        for entry in bin_dir.iterdir():
            if entry.is_file():
                sources.append(entry)
    hooks_scripts = plugin_root / "hooks" / "scripts"
    if hooks_scripts.is_dir():
        for entry in hooks_scripts.iterdir():
            if entry.is_file():
                sources.append(entry)
    for extra in (
        repo_root / "CLAUDE.md",
        repo_root / "README.md",
    ):
        if extra.is_file():
            sources.append(extra)
    for sub in (".claude/rules", ".claude/skills", ".claude/agents"):
        sub_path = repo_root / sub
        if sub_path.is_dir():
            for md in sub_path.rglob("*.md"):
                sources.append(md)

    for src in sources:
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        skill_dir_rel: str | None = None
        if src.is_relative_to(plugin_root) and src.name == "SKILL.md":
            skill_dir_rel = str(src.parent.relative_to(plugin_root))
        for m in REFERENCE_PATH_RE.finditer(text):
            raw = m.group(0)
            if skill_dir_rel and raw.startswith("references/"):
                referenced.add(f"{skill_dir_rel}/{raw}")
            else:
                referenced.add(raw)
        for m in SKILL_REL_REF_RE.finditer(text):
            referenced.add(m.group(0))
        for m in PLUGIN_VAR_RE.finditer(text):
            referenced.add(m.group(1))

    return referenced


def _detect_orphans(plugin_root: Path, repo_root: Path) -> list[OrphanRef]:
    referenced = _collect_referenced_paths(plugin_root, repo_root)
    orphans: list[OrphanRef] = []
    for md in sorted(_all_reference_md_files(plugin_root)):
        rel = str(md)
        skill_local = None
        parts = rel.split("/")
        if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "references":
            skill_local = "/".join(parts[2:])
        if rel in referenced:
            continue
        if skill_local and skill_local in referenced:
            continue
        orphans.append(OrphanRef(path=rel))
    return orphans


def scan(plugin_root: Path, repo_root: Path | None = None) -> ScanResult:
    if repo_root is None:
        repo_root = plugin_root
        for parent in (plugin_root, *plugin_root.parents):
            if (parent / ".git").exists() or (parent / "CLAUDE.md").is_file():
                repo_root = parent
                break
    skill_dirs, skill_aliases = _skill_universe(plugin_root)
    agents = _agent_names(plugin_root)
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
    result.registry_broken = _validate_registry_refs(plugin_root)
    result.orphans = _detect_orphans(plugin_root, repo_root)
    return result


def main(argv: list[str]) -> int:
    plugin_root = Path(argv[1]) if len(argv) > 1 else Path("plugins/ruby-grape-rails")
    result = scan(plugin_root)
    fail = bool(result.broken or result.registry_broken)
    if not fail and not result.orphans:
        print(f"check-refs: clean ({plugin_root})")
        return 0
    if result.broken:
        print(f"check-refs: {len(result.broken)} broken references in {plugin_root}")
        for ref in result.broken:
            print(f"  {ref.source}:{ref.line}: unknown -> {ref.target}")
    if result.registry_broken:
        print(f"check-refs: {len(result.registry_broken)} BROKEN_REGISTRY_REFERENCE")
        for ref in result.registry_broken:
            print(f"  {ref.registry} id={ref.entry_id}: missing -> {ref.target}")
    if result.orphans:
        print(f"check-refs: {len(result.orphans)} ORPHAN_REFERENCE_FILE (advisory)")
        for o in result.orphans:
            print(f"  orphan: {o.path}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
