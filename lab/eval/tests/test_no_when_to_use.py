"""Unit test: no SKILL.md retains the legacy `when_to_use:` frontmatter field.

Skills use a single `description` field per the agentskills.io canon.
"""

import unittest

from lab.eval.frontmatter import parse_frontmatter
from lab.eval.matchers import PLUGIN_ROOT

SKILL_DIR = PLUGIN_ROOT / "skills"


class NoWhenToUseTests(unittest.TestCase):
    def test_no_skill_retains_when_to_use_field(self) -> None:
        carriers: list[str] = []
        for skill_md in sorted(SKILL_DIR.glob("*/SKILL.md")):
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if "when_to_use" in fm:
                carriers.append(str(skill_md.relative_to(PLUGIN_ROOT.parent.parent)))
        self.assertEqual(
            carriers,
            [],
            "Skills retain legacy when_to_use field:\n" + "\n".join(carriers),
        )


if __name__ == "__main__":
    unittest.main()
