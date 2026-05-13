"""Context budget advisory checks for the Ruby plugin.

Two deterministic, zero-API-cost checks:
1. Root CLAUDE.md line count (warn if > 200)
2. SKILL.md files retaining `paths:` frontmatter (warn — empirically
   non-functional at plugin scope; `.claude/rules/*.md` paths-routing
   mechanism is distinct and unaffected)

Run as part of make eval (--changed), make eval-all, and make eval-ci-deterministic. Advisory only.
"""

import re
import sys
from pathlib import Path

from .frontmatter import parse_frontmatter

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PROJECT_ROOT / "plugins" / "ruby-grape-rails"
CLAUDE_MD = PROJECT_ROOT / "CLAUDE.md"
MAX_CLAUDE_MD_LINES = 200


def _count_lines(path: Path) -> int:
    if not path.exists():
        return 0
    return len(path.read_text(encoding="utf-8").splitlines())


def _count_imports(path: Path) -> list[tuple[str, int]]:
    if not path.exists():
        return []
    imports = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^@(.+)$", line.strip())
        if match:
            import_path = path.parent / match.group(1)
            imports.append((str(match.group(1)), _count_lines(import_path)))
    return imports


def _has_paths_field(path: Path) -> bool:
    """Check if a SKILL.md file has paths: in its YAML frontmatter."""
    if not path.exists():
        return False
    fm = parse_frontmatter(path.read_text(encoding="utf-8"))
    return "paths" in fm


def check_claude_md_size() -> tuple[bool, list[str]]:
    messages: list[str] = []
    if not CLAUDE_MD.exists():
        messages.append("  WARNING: CLAUDE.md not found")
        return False, messages
    line_count = _count_lines(CLAUDE_MD)
    imports = _count_imports(CLAUDE_MD)
    import_total = sum(lines for _, lines in imports)

    messages.append(f"  CLAUDE.md: {line_count} lines")
    if imports:
        for name, lines in imports:
            messages.append(f"    @{name}: {lines} lines")
        messages.append(
            f"  Total always-loaded (informational): "
            f"{line_count + import_total} lines"
        )

    passed = line_count <= MAX_CLAUDE_MD_LINES
    if not passed:
        messages.append(
            f"  WARNING: root CLAUDE.md exceeds {MAX_CLAUDE_MD_LINES} line "
            f"target ({line_count} lines). Official CC docs recommend < 200."
        )
    else:
        messages.append(
            f"  OK: root CLAUDE.md under {MAX_CLAUDE_MD_LINES} line target"
        )

    return passed, messages


def check_paths_coverage() -> tuple[bool, list[str]]:
    """Warn on any SKILL.md retaining `paths:` frontmatter.

    Plugin-scope SKILL.md `paths:` is empirically non-functional (no
    harness-side auto-activation). The field is removed to align with
    that empirical reality. Project-level rules (`.claude/rules/*.md`)
    use a distinct, functional `paths:` mechanism — out of scope here.
    """
    messages: list[str] = []
    carriers: list[str] = []
    skills_dir = PLUGIN_ROOT / "skills"

    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        if _has_paths_field(skill_md):
            carriers.append(skill_dir.name)

    if carriers:
        messages.append(
            f"  WARNING: {len(carriers)} SKILL.md file(s) retain paths: "
            "(empirically non-functional at plugin scope)"
        )
        for name in carriers:
            messages.append(f"    - {name}")
    else:
        messages.append("  OK: no SKILL.md retains paths: frontmatter")

    return len(carriers) == 0, messages


def main() -> int:
    print("=== Context Budget Checks (advisory) ===")
    print()

    print("CLAUDE.md size:")
    _, md_messages = check_claude_md_size()
    for msg in md_messages:
        print(msg)
    print()

    print("Framework skill paths: coverage:")
    _, paths_messages = check_paths_coverage()
    for msg in paths_messages:
        print(msg)
    print()

    return 0  # Advisory -- never fails


if __name__ == "__main__":
    sys.exit(main())
