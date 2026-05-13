"""Unit test: every DMI'd skill must keep `user-invocable: true`.

Hard constraint per spec external review B4: when `disable-model-invocation: true`,
the skill MUST remain slash-invocable so users retain a manual entry point.
Internal-only exemptions go in INTERNAL_ONLY (empty by default).
"""

import unittest

from lab.eval.frontmatter import parse_frontmatter
from lab.eval.matchers import PLUGIN_ROOT

SKILL_DIR = PLUGIN_ROOT / "skills"

INTERNAL_ONLY: set[str] = set()


class DmiInvocabilityTests(unittest.TestCase):
    def test_dmi_skills_are_user_invocable(self) -> None:
        violators: list[str] = []
        for skill_md in sorted(SKILL_DIR.glob("*/SKILL.md")):
            fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if not fm.get("disable-model-invocation"):
                continue
            name = str(fm.get("name") or skill_md.parent.name)
            # `user-invocable` defaults to True per CC docs; only flag an explicit
            # `false` on a DMI skill (that would render the skill unreachable both
            # to the model and to manual slash invocation).
            if fm.get("user-invocable") is False and name not in INTERNAL_ONLY:
                violators.append(
                    f"{name} ({skill_md.relative_to(PLUGIN_ROOT.parent.parent)})"
                )
        self.assertEqual(
            violators,
            [],
            "DMI skills set user-invocable: false (would be unreachable):\n" + "\n".join(violators),
        )


if __name__ == "__main__":
    unittest.main()
