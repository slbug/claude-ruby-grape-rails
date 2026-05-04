"""Validate internal skill/agent cross-references and reference-asset integrity.

Failure modes (each fails CI):

- ``broken``: prose `/rb:<name>`, `skills/<name>`, `agents/<name>` reference
  resolves to no file on disk.
- ``registry_broken``: `iron-laws.yml` / `preferences.yml` `reference_files`
  points at a missing file.
- ``plain_broken``: a Markdown reference path like
  ``references/foo.md`` / ``skills/<skill>/references/foo.md`` /
  ``${CLAUDE_PLUGIN_ROOT}/...`` extracted from prose does not exist on
  disk.
- ``traversal``: extracted reference contains ``..`` segment — cross-skill
  paths must use ``${CLAUDE_PLUGIN_ROOT}/skills/...`` form, not
  ``${CLAUDE_SKILL_DIR}/../...``.
- ``orphans``: reference asset under ``references/`` (plugin or contributor)
  is unreachable from any non-orphan entry point. Failure-by-default; no
  env-var bypass.

Reference-asset coverage:

- file extensions: ``.md``, ``.py``, ``.rb``, ``.sh``, ``.yml``, ``.yaml``,
  ``.json``
- plugin scope: every ``plugins/ruby-grape-rails/**/references/`` subtree
- contributor scope: ``.claude/skills/**/references/`` subtree
- exclusions: ``__pycache__``, ``*.pyc``

Source-scan coverage (entry points + transitive closure):

- plugin Markdown bodies (skills, agents, top-level)
- plugin ``bin/`` and ``hooks/scripts/`` executables
- plugin ``lib/`` Ruby modules
- repo-level ``CLAUDE.md`` and ``README.md``
- contributor surfaces under ``.claude/{rules,skills,agents}``
- registry ``reference_files`` entries
- transitive walk through reference docs that are themselves reachable
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .frontmatter import parse_frontmatter

ASSET_EXTS = ("md", "py", "rb", "sh", "yml", "yaml", "json")
ASSET_EXT_GROUP = f"(?:{'|'.join(ASSET_EXTS)})"

SLASH_REF_RE = re.compile(r"/rb:([a-z][a-z0-9-]+)")
PATH_SKILL_REF_RE = re.compile(r"skills/([a-z][a-z0-9-]+)")
PATH_AGENT_REF_RE = re.compile(r"agents/([a-z][a-z0-9-]+)")
REFERENCE_PATH_RE = re.compile(rf"references/[A-Za-z0-9_./-]+\.{ASSET_EXT_GROUP}\b")
SKILL_REL_REF_RE = re.compile(rf"skills/[A-Za-z0-9_./-]+\.{ASSET_EXT_GROUP}\b")
PLUGIN_ROOT_VAR_RE = re.compile(
    rf"\$\{{CLAUDE_PLUGIN_ROOT\}}/([A-Za-z0-9_./-]+\.{ASSET_EXT_GROUP})\b"
)
SKILL_DIR_VAR_RE = re.compile(
    rf"\$\{{CLAUDE_SKILL_DIR\}}/([A-Za-z0-9_./-]+\.{ASSET_EXT_GROUP})\b"
)
FENCE_OPEN_RE = re.compile(r"^\s*(`{3,}|~{3,})")
FENCE_CLOSE_RE = re.compile(r"^\s*(`{3,}|~{3,})\s*$")

EXCLUDE_DIR_NAMES = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc"}

# Roots that own a `references/` namespace. (label, path-relative-to-repo).
# When `repo_root` resolves to outside the plugin, contributor scope is
# included; otherwise contributor scope is silently skipped.
PLUGIN_LABEL = "plugin"
CONTRIBUTOR_LABEL = "contributor"


@dataclass(frozen=True)
class RefSite:
    """A single extracted reference with its source location.

    ``resolution_root`` is the on-disk directory the ``target`` is
    relative to (plugin root for plugin sources, repo root + `.claude`
    for contributor sources). Empty string means "do not validate the
    path on disk" (used for non-markdown sources where comments may
    discuss paths that are not real references).
    """

    target: str
    source: str
    line: int
    resolution_root: str  # "plugin" | "contributor" | ""


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
class PlainBrokenRef:
    source: str
    target: str
    line: int


@dataclass
class TraversalRef:
    source: str
    target: str
    line: int


@dataclass
class OrphanRef:
    path: str
    scope: str  # "plugin" or "contributor"


@dataclass
class ScanResult:
    broken: list[BrokenRef] = field(default_factory=list)
    registry_broken: list[RegistryBrokenRef] = field(default_factory=list)
    plain_broken: list[PlainBrokenRef] = field(default_factory=list)
    traversal: list[TraversalRef] = field(default_factory=list)
    orphans: list[OrphanRef] = field(default_factory=list)


def _frontmatter_name(md_path: Path) -> str | None:
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    name = parse_frontmatter(text).get("name")
    return name if isinstance(name, str) and name else None


def _skill_universe(plugin_root: Path) -> tuple[set[str], set[str]]:
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
        m = FENCE_CLOSE_RE.match(line)
        if m and m.group(1)[0] == open_delim[0] and len(m.group(1)) >= len(open_delim):
            open_delim = None
            fenced_buffer = []
            continue
        fenced_buffer.append((lineno, line))
    if open_delim is not None:
        yield from fenced_buffer


def _registry_reference_files(plugin_root: Path) -> list[tuple[str, str, str]]:
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


def _is_excluded(path: Path) -> bool:
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return any(part in EXCLUDE_DIR_NAMES for part in path.parts)


def _all_reference_assets(
    plugin_root: Path, repo_root: Path
) -> dict[str, set[Path]]:
    """Return reference-asset paths grouped by scope.

    Each value set is paths RELATIVE TO THE OWNING ROOT (plugin or
    contributor), so callers can resolve the on-disk path with
    ``root / rel``. Asset extensions ``ASSET_EXTS`` are included; cache
    files (``.pyc``, ``__pycache__/``) are excluded.
    """
    assets: dict[str, set[Path]] = {PLUGIN_LABEL: set(), CONTRIBUTOR_LABEL: set()}

    def _walk(scope: str, root: Path, ref_dir_globs: list[str]) -> None:
        for pattern in ref_dir_globs:
            for ref_dir in root.glob(pattern):
                if not ref_dir.is_dir():
                    continue
                for path in ref_dir.rglob("*"):
                    if not path.is_file():
                        continue
                    if _is_excluded(path):
                        continue
                    if path.suffix.lstrip(".") not in ASSET_EXTS:
                        continue
                    assets[scope].add(path.relative_to(root))

    _walk(PLUGIN_LABEL, plugin_root, ["references", "skills/*/references"])
    contrib_root = repo_root / ".claude"
    if contrib_root.is_dir():
        _walk(CONTRIBUTOR_LABEL, contrib_root, ["skills/*/references"])
    return assets


def _extract_ref_sites(
    text: str,
    src_label: str,
    skill_dir_rel: str | None,
    skill_resolution: str,
) -> list[RefSite]:
    """Extract reference paths with line numbers, skipping fenced blocks.

    ``skill_dir_rel`` resolves the skill-local ``references/foo.md``
    form against its owning skill directory.
    ``skill_resolution`` labels the on-disk root for ``${CLAUDE_SKILL_DIR}``
    and skill-local ``references/foo.md`` matches.

    Resolution rules:

    - ``${CLAUDE_PLUGIN_ROOT}/<rel>`` → always plugin scope.
    - ``skills/<x>/<...>`` literal → always plugin scope (every shipped
      skill lives under the plugin tree).
    - ``${CLAUDE_SKILL_DIR}/<rel>`` → ``skill_resolution``.
    - bare ``references/<rel>`` preceded by ``plugins/ruby-grape-rails/``
      → plugin scope (explicit plugin-rooted path in prose).
    - bare ``references/<rel>`` preceded by other path tokens (e.g.
      ``../`` markdown link) → kept bare; validator checks at
      ``plugin_root``.
    - bare ``references/<rel>`` at a token start → resolved against
      ``skill_dir_rel`` if the source is a SKILL.md / reference doc;
      otherwise treated as plugin-root-relative.
    """
    sites: list[RefSite] = []
    plugin_root_prefix = "plugins/ruby-grape-rails/"
    for lineno, line in _iter_non_fenced_lines(text):
        # ``${CLAUDE_SKILL_DIR}/...`` — contextual scope.
        skill_var_spans: list[tuple[int, int]] = []
        for m in SKILL_DIR_VAR_RE.finditer(line):
            skill_var_spans.append(m.span())
            raw = m.group(1)
            target = (
                f"{skill_dir_rel}/{raw}"
                if skill_dir_rel and raw.startswith("references/")
                else raw
            )
            sites.append(
                RefSite(
                    target=target,
                    source=src_label,
                    line=lineno,
                    resolution_root=skill_resolution,
                )
            )
        # ``${CLAUDE_PLUGIN_ROOT}/...`` — always plugin scope.
        plugin_var_spans: list[tuple[int, int]] = []
        for m in PLUGIN_ROOT_VAR_RE.finditer(line):
            plugin_var_spans.append(m.span())
            sites.append(
                RefSite(
                    target=m.group(1),
                    source=src_label,
                    line=lineno,
                    resolution_root=PLUGIN_LABEL,
                )
            )
        # ``skills/<x>/...`` literal — capture before REFERENCE_PATH_RE
        # so the trailing ``references/...`` suffix is suppressed.
        # Resolution: explicit ``plugins/ruby-grape-rails/skills/...``
        # → plugin; ``.claude/skills/...`` → contributor; otherwise
        # default to ``skill_resolution`` (the source's own scope).
        skill_rel_spans: list[tuple[int, int]] = []
        for m in SKILL_REL_REF_RE.finditer(line):
            skill_rel_spans.append(m.span())
            if any(s <= m.start() and m.end() <= e for s, e in skill_var_spans + plugin_var_spans):
                continue
            pre = line[: m.start()]
            if pre.endswith(plugin_root_prefix):
                resolution = PLUGIN_LABEL
            elif pre.endswith(".claude/"):
                resolution = CONTRIBUTOR_LABEL
            else:
                resolution = skill_resolution
            sites.append(
                RefSite(
                    target=m.group(0),
                    source=src_label,
                    line=lineno,
                    resolution_root=resolution,
                )
            )

        consumed_spans = skill_var_spans + plugin_var_spans + skill_rel_spans

        def _inside(start: int, end: int) -> bool:
            return any(s <= start and end <= e for s, e in consumed_spans)

        for m in REFERENCE_PATH_RE.finditer(line):
            if _inside(*m.span()):
                continue
            raw = m.group(0)
            preceded_by_path_token = m.start() > 0 and line[m.start() - 1] in "/."
            # Detect prose form ``plugins/ruby-grape-rails/references/...``
            # and resolve against plugin root regardless of source.
            prefix_window = line[max(0, m.start() - len(plugin_root_prefix)) : m.start()]
            preceded_by_plugin_root = prefix_window.endswith(plugin_root_prefix)

            if preceded_by_plugin_root:
                resolution = PLUGIN_LABEL
                target = raw
            elif preceded_by_path_token:
                resolution = skill_resolution
                target = raw
            elif skill_dir_rel and raw.startswith("references/"):
                resolution = skill_resolution
                target = f"{skill_dir_rel}/{raw}"
            else:
                resolution = skill_resolution
                target = raw

            sites.append(
                RefSite(
                    target=target,
                    source=src_label,
                    line=lineno,
                    resolution_root=resolution,
                )
            )
    return sites


def _entry_sources(plugin_root: Path, repo_root: Path) -> list[Path]:
    sources: list[Path] = []
    for md in plugin_root.rglob("*.md"):
        rel_parts = md.relative_to(plugin_root).parts
        if "references" in rel_parts:
            continue
        sources.append(md)
    for sub in ("bin", "hooks/scripts", "lib"):
        sub_path = plugin_root / sub
        if sub_path.is_dir():
            for entry in sub_path.rglob("*"):
                if entry.is_file() and not _is_excluded(entry):
                    sources.append(entry)
    for extra in (repo_root / "CLAUDE.md", repo_root / "README.md"):
        if extra.is_file():
            sources.append(extra)
    for sub in (".claude/rules", ".claude/skills", ".claude/agents"):
        sub_path = repo_root / sub
        if sub_path.is_dir():
            for entry in sub_path.rglob("*"):
                if not entry.is_file() or _is_excluded(entry):
                    continue
                # contributor reference assets are TARGETS, not sources;
                # skip them here so an orphan contributor doc cannot
                # shield itself by mentioning its own path.
                if "references" in entry.relative_to(sub_path).parts:
                    continue
                sources.append(entry)
    return sources


def _source_label(path: Path, plugin_root: Path, repo_root: Path) -> str:
    try:
        return str(path.relative_to(plugin_root))
    except ValueError:
        return str(path.relative_to(repo_root))


def _skill_dir_rel_for(
    path: Path, plugin_root: Path, repo_root: Path
) -> str | None:
    """Return the skill-dir prefix for a SKILL.md relative to its
    owning root. Plugin SKILL.md → relative to plugin_root; contributor
    SKILL.md under `.claude/skills/<x>` → relative to `.claude/`.
    """
    if path.name != "SKILL.md":
        return None
    if path.is_relative_to(plugin_root):
        return str(path.parent.relative_to(plugin_root))
    contrib = repo_root / ".claude"
    if path.is_relative_to(contrib):
        return str(path.parent.relative_to(contrib))
    return None


def _ref_dir_rel_for(rel: str) -> str | None:
    """Resolve a reference doc's own skill-dir context.

    `skills/<skill>/references/<doc>.md` is owned by `skills/<skill>`.
    Used during the transitive walk so a doc can use the skill-local
    `references/<sibling>.md` form.
    """
    parts = rel.split("/")
    if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "references":
        return f"{parts[0]}/{parts[1]}"
    return None


def _resolution_for_source(path: Path, plugin_root: Path, repo_root: Path) -> str:
    if path.is_relative_to(plugin_root):
        return PLUGIN_LABEL
    contrib = repo_root / ".claude"
    if path.is_relative_to(contrib):
        return CONTRIBUTOR_LABEL
    return PLUGIN_LABEL


def _collect_reference_sites(
    plugin_root: Path, repo_root: Path
) -> tuple[set[str], set[str], list[RefSite]]:
    """Return (plugin closure, contributor closure, all extracted sites).

    Two-pass closure rooted at non-reference entry points so an orphan
    ref doc that links to another orphan does NOT shield it. Closures
    are scoped per resolution root: plugin paths are tracked against
    the plugin tree; contributor paths against `.claude/`.
    """
    plugin_closure: set[str] = set()
    contrib_closure: set[str] = set()
    all_sites: list[RefSite] = []

    # Registry root files are consumed by the generator + injector at
    # build time; treat them as reachable entry points. Their
    # `reference_files` entries seed the closure too.
    for registry_rel in (
        "references/iron-laws.yml",
        "references/preferences.yml",
    ):
        if (plugin_root / registry_rel).is_file():
            plugin_closure.add(registry_rel)
    for _label, _eid, ref in _registry_reference_files(plugin_root):
        plugin_closure.add(ref)
        all_sites.append(
            RefSite(
                target=ref,
                source="references/iron-laws+preferences.yml",
                line=0,
                resolution_root=PLUGIN_LABEL,
            )
        )

    contrib_root = repo_root / ".claude"

    md_sources_only_for_validation: set[Path] = set()

    for src in _entry_sources(plugin_root, repo_root):
        try:
            text = src.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        skill_dir_rel = _skill_dir_rel_for(src, plugin_root, repo_root)
        label = _source_label(src, plugin_root, repo_root)
        is_md = src.suffix == ".md"
        if is_md:
            md_sources_only_for_validation.add(src)
        skill_resolution = (
            CONTRIBUTOR_LABEL
            if src.is_relative_to(contrib_root)
            else PLUGIN_LABEL
        )
        # markdown sources participate in plain-path validation; non-md
        # sources only contribute to the closure (so orphan detection
        # still credits a script's reference) but their extracted paths
        # are tagged with empty resolution_root and skipped by the
        # path validator.
        sites = _extract_ref_sites(
            text,
            label,
            skill_dir_rel,
            skill_resolution=skill_resolution if is_md else "",
        )
        all_sites.extend(sites)
        for site in sites:
            if site.resolution_root == CONTRIBUTOR_LABEL or (
                site.resolution_root == "" and src.is_relative_to(contrib_root)
            ):
                contrib_closure.add(site.target)
            else:
                plugin_closure.add(site.target)

    # Pass 2: transitive closure through reachable reference docs ONLY.
    # SKILL.md and agents are scanned in pass 1; do not re-walk them
    # here, otherwise a closure entry referencing back to a SKILL.md
    # would yield duplicate (and mis-prefixed) sites.
    queue: list[tuple[str, str]] = [(t, PLUGIN_LABEL) for t in sorted(plugin_closure)]
    queue.extend((t, CONTRIBUTOR_LABEL) for t in sorted(contrib_closure))
    visited: set[tuple[str, str]] = set()
    while queue:
        rel, scope = queue.pop()
        key = (rel, scope)
        if key in visited:
            continue
        visited.add(key)
        if ".." in rel.split("/"):
            continue
        # Only reference docs participate in transitive walk.
        rel_parts = rel.split("/")
        if "references" not in rel_parts:
            continue
        if scope == PLUGIN_LABEL:
            candidate = plugin_root / rel
        else:
            candidate = contrib_root / rel
        if not candidate.is_file() or candidate.suffix != ".md":
            continue
        try:
            text = candidate.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        skill_dir_rel = _ref_dir_rel_for(rel)
        sites = _extract_ref_sites(
            text,
            rel,
            skill_dir_rel,
            skill_resolution=scope,
        )
        all_sites.extend(sites)
        for site in sites:
            target_scope = site.resolution_root or scope
            target_set = (
                contrib_closure if target_scope == CONTRIBUTOR_LABEL else plugin_closure
            )
            if site.target not in target_set:
                target_set.add(site.target)
                queue.append((site.target, target_scope))

    return plugin_closure, contrib_closure, all_sites


def _validate_extracted_paths(
    sites: list[RefSite],
    plugin_root: Path,
    repo_root: Path,
) -> tuple[list[PlainBrokenRef], list[TraversalRef]]:
    """Check every extracted plain reference resolves on disk.

    `..` traversal in the path is flagged as `TraversalRef` (cross-skill
    paths must use `${CLAUDE_PLUGIN_ROOT}/skills/<other>` form, not
    `${CLAUDE_SKILL_DIR}/../<other>`). Missing-but-clean paths become
    `PlainBrokenRef`. Sites with empty `resolution_root` are skipped —
    those came from non-markdown sources where comments may discuss
    placeholder paths.
    """
    plain_broken: list[PlainBrokenRef] = []
    traversal: list[TraversalRef] = []
    seen_broken: set[tuple[str, str, int]] = set()
    seen_traversal: set[tuple[str, str, int]] = set()

    contrib_root = repo_root / ".claude"

    for site in sites:
        rel = site.target
        if not rel or not site.resolution_root:
            continue
        # Traversal check first — `..` segments are an explicit
        # convention violation regardless of suffix prefix.
        if ".." in rel.split("/"):
            key = (site.source, rel, site.line)
            if key not in seen_traversal:
                seen_traversal.add(key)
                traversal.append(
                    TraversalRef(source=site.source, target=rel, line=site.line)
                )
            continue
        if not (rel.startswith("references/") or rel.startswith("skills/")):
            continue
        if site.resolution_root == CONTRIBUTOR_LABEL:
            disk_path = contrib_root / rel
        else:
            disk_path = plugin_root / rel
        if not disk_path.is_file():
            key = (site.source, rel, site.line)
            if key not in seen_broken:
                seen_broken.add(key)
                plain_broken.append(
                    PlainBrokenRef(source=site.source, target=rel, line=site.line)
                )
    return plain_broken, traversal


def _detect_orphans(
    plugin_root: Path,
    repo_root: Path,
    plugin_closure: set[str],
    contrib_closure: set[str],
) -> list[OrphanRef]:
    assets = _all_reference_assets(plugin_root, repo_root)
    orphans: list[OrphanRef] = []

    def _is_reachable(rel: str, closure: set[str]) -> bool:
        if rel in closure:
            return True
        parts = rel.split("/")
        if len(parts) >= 4 and parts[0] == "skills" and parts[2] == "references":
            skill_local = "/".join(parts[2:])
            if skill_local in closure:
                return True
        return False

    for rel_path in sorted(assets[PLUGIN_LABEL]):
        rel = str(rel_path)
        if _is_reachable(rel, plugin_closure):
            continue
        orphans.append(OrphanRef(path=rel, scope=PLUGIN_LABEL))

    contrib_root = repo_root / ".claude"
    if contrib_root.is_dir():
        for rel_path in sorted(assets[CONTRIBUTOR_LABEL]):
            rel = str(rel_path)
            if _is_reachable(rel, contrib_closure):
                continue
            orphans.append(
                OrphanRef(path=f".claude/{rel}", scope=CONTRIBUTOR_LABEL)
            )

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
    plugin_closure, contrib_closure, sites = _collect_reference_sites(
        plugin_root, repo_root
    )
    result.plain_broken, result.traversal = _validate_extracted_paths(
        sites, plugin_root, repo_root
    )
    result.orphans = _detect_orphans(
        plugin_root, repo_root, plugin_closure, contrib_closure
    )
    return result


def main(argv: list[str]) -> int:
    plugin_root = Path(argv[1]) if len(argv) > 1 else Path("plugins/ruby-grape-rails")
    result = scan(plugin_root)

    fail = bool(
        result.broken
        or result.registry_broken
        or result.plain_broken
        or result.traversal
        or result.orphans
    )
    if not fail:
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
    if result.plain_broken:
        print(f"check-refs: {len(result.plain_broken)} BROKEN_REFERENCE_PATH")
        for ref in result.plain_broken:
            print(f"  {ref.source}:{ref.line}: missing -> {ref.target}")
    if result.traversal:
        print(f"check-refs: {len(result.traversal)} TRAVERSAL_REFERENCE")
        for ref in result.traversal:
            print(
                f"  {ref.source}:{ref.line}: '..' segment in {ref.target} "
                f"(use ${{CLAUDE_PLUGIN_ROOT}}/skills/<other> form)"
            )
    if result.orphans:
        print(f"check-refs: {len(result.orphans)} ORPHAN_REFERENCE_FILE")
        for o in result.orphans:
            print(f"  orphan ({o.scope}): {o.path}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
