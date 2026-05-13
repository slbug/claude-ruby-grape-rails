"""Unit test: no SKILL.md retains `paths:` frontmatter.

Plugin-scope SKILL.md `paths:` is empirically non-functional (no
harness-side auto-activation). Project-level `.claude/rules/*.md`
paths-routing mechanism is distinct and remains functional — NOT
covered by this test.
"""

import unittest

from lab.eval.frontmatter import parse_frontmatter
from lab.eval.matchers import PLUGIN_ROOT

SKILL_DIR = PLUGIN_ROOT / "skills"


class NoPathsOnSkillsTests(unittest.TestCase):
    def test_no_skill_retains_paths_frontmatter(self) -> None:
        carriers: list[str] = []
        for skill_md in sorted(SKILL_DIR.glob("*/SKILL.md")):
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if "paths" in fm:
                carriers.append(str(skill_md.relative_to(PLUGIN_ROOT.parent.parent)))
        self.assertEqual(
            carriers,
            [],
            "SKILL.md files retain paths frontmatter:\n" + "\n".join(carriers),
        )


if __name__ == "__main__":
    unittest.main()
