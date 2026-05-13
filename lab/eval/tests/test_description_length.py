"""Unit test: every SKILL.md `description` <= 1024 chars (agentskills.io cap)."""

import unittest
from pathlib import Path

from lab.eval.frontmatter import parse_frontmatter
from lab.eval.matchers import PLUGIN_ROOT

SKILL_DIR = PLUGIN_ROOT / "skills"
MAX_DESCRIPTION_CHARS = 1024


class DescriptionLengthTests(unittest.TestCase):
    def test_all_skill_descriptions_within_cap(self) -> None:
        overlong: list[str] = []
        for skill_md in sorted(SKILL_DIR.glob("*/SKILL.md")):
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            desc = str(fm.get("description") or "")
            if len(desc) > MAX_DESCRIPTION_CHARS:
                overlong.append(
                    f"{skill_md.relative_to(PLUGIN_ROOT.parent.parent)}: {len(desc)} chars"
                )
        self.assertEqual(
            overlong,
            [],
            f"Descriptions exceed {MAX_DESCRIPTION_CHARS} chars:\n" + "\n".join(overlong),
        )


if __name__ == "__main__":
    unittest.main()
