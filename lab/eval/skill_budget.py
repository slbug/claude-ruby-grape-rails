"""Audit aggregate skill-listing budget. Run via `make eval-skill-budget`.

Per-skill `description_length` already enforced elsewhere:
- `lab/eval/scorer.py::default_eval` applies min 60 / max 1536 to
  every skill;
- per-skill `lab/eval/evals/*.json` may override min within that range.

This tool covers only the AGGREGATE gap: total listing chars across
model-visible skills must fit CC
`skillListingBudgetFraction=0.01` × plugin's 1M-context target.

Skills marked `disable-model-invocation: true` excluded (CC removes
them from listing per frontmatter reference docs).
"""

import sys
from pathlib import Path

from lab.eval.frontmatter import parse_frontmatter

SKILLS_DIR = Path("plugins/ruby-grape-rails/skills")
SKILL_AGGREGATE_TARGET_CHARS = 10_000


def measure_skill(skill_dir: Path) -> tuple[str, int, bool] | None:
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.is_file():
        return None
    fm = parse_frontmatter(skill_md.read_text(encoding="utf-8", errors="replace"))
    if not isinstance(fm, dict):
        return None
    label = str(fm.get("name") or skill_dir.name)
    desc = str(fm.get("description") or "").strip()
    wtu = str(fm.get("when_to_use") or "").strip()
    combined = len(desc) + len(wtu)
    hidden = bool(fm.get("disable-model-invocation", False))
    return (label, combined, hidden)


def main() -> int:
    if not SKILLS_DIR.is_dir():
        print(f"skill_budget: {SKILLS_DIR} not found", file=sys.stderr)
        return 1
    rows = []
    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        m = measure_skill(skill_dir)
        if m is not None:
            rows.append(m)
    if not rows:
        print("skill_budget: no skills found", file=sys.stderr)
        return 1
    listed = [(n, c) for n, c, h in rows if not h]
    hidden = [(n, c) for n, c, h in rows if h]
    aggregate = sum(c for _, c in listed)

    print(f"Skills total: {len(rows)} (listed: {len(listed)}, hidden: {len(hidden)})")
    print(f"Aggregate listing chars: {aggregate}")
    print(f"Target: <= {SKILL_AGGREGATE_TARGET_CHARS} (CC 1% x 1M context)")

    if aggregate > SKILL_AGGREGATE_TARGET_CHARS:
        print(f"\nFAIL: aggregate {aggregate} > target {SKILL_AGGREGATE_TARGET_CHARS}")
        listed_sorted = sorted(listed, key=lambda x: -x[1])
        print("\nTop 10 listed skills by chars:")
        for n, c in listed_sorted[:10]:
            print(f"  {c:5d}  {n}")
        return 1

    print(f"\nPASS: aggregate {aggregate} <= {SKILL_AGGREGATE_TARGET_CHARS}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
