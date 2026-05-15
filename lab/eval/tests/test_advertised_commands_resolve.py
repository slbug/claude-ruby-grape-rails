"""Unit test: every `/rb:<name>` reference in routing tables + hub bodies + docs
resolves to an existing skill frontmatter `name:` value.

Scans intent-detection routing table, README, and tutorial-content for
`` `/rb:<name>` `` patterns. Each must map to a SKILL.md `name:` field.
"""

import re
import unittest

from lab.eval.frontmatter import parse_frontmatter
from lab.eval.matchers import PLUGIN_ROOT, PROJECT_ROOT

SCAN_FILES = [
    PLUGIN_ROOT / "skills" / "intent-detection" / "SKILL.md",
    PROJECT_ROOT / "README.md",
    PLUGIN_ROOT / "skills" / "intro" / "references" / "tutorial-content.md",
]

COMMAND_PATTERN = re.compile(r"`/(rb:[a-z0-9_-]+)`")


class AdvertisedCommandsResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.skill_names: set[str] = set()
        for skill_md in (PLUGIN_ROOT / "skills").glob("*/SKILL.md"):
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            name = fm.get("name")
            if isinstance(name, str):
                self.skill_names.add(name)

    def test_advertised_slash_commands_resolve_to_skills(self) -> None:
        unresolved: list[str] = []
        for path in SCAN_FILES:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for match in COMMAND_PATTERN.finditer(text):
                cmd = match.group(1)
                if cmd not in self.skill_names:
                    unresolved.append(f"{path.relative_to(PROJECT_ROOT)}: /{cmd}")
        self.assertEqual(
            unresolved,
            [],
            "Slash commands without matching skill name:\n" + "\n".join(unresolved),
        )


if __name__ == "__main__":
    unittest.main()
