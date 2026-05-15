"""Unit test: skill-registry.yml `visible_skills` / `hidden_skills` matches
each SKILL.md's `disable-model-invocation` frontmatter flag.

Drift mode caught: skill flips DMI in SKILL.md but contributor forgets to
move it across registry buckets. `scripts/generate-skill-routing.sh` reads
the registry as source of truth, so divergence silently misclassifies a
skill in routing artifacts (DMI roster, hub footers, tutorial inventory).
"""

import unittest
from pathlib import Path

import yaml

from lab.eval.frontmatter import parse_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / "plugins/ruby-grape-rails/skills"
REGISTRY = REPO_ROOT / "plugins/ruby-grape-rails/references/skill-registry.yml"


class RegistryVisibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = yaml.safe_load(REGISTRY.read_text(encoding="utf-8"))

    def _is_dmi(self, folder: str) -> bool:
        skill_md = SKILLS_DIR / folder / "SKILL.md"
        fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
        return fm.get("disable-model-invocation") is True

    def test_visible_skills_lack_dmi(self) -> None:
        violations = [
            entry["folder"]
            for entry in self.registry.get("visible_skills", [])
            if self._is_dmi(entry["folder"])
        ]
        self.assertEqual(
            violations,
            [],
            "Registry lists these as visible_skills but SKILL.md has "
            "disable-model-invocation: true (move to hidden_skills or "
            "drop the DMI flag):\n" + "\n".join(violations),
        )

    def test_hidden_skills_carry_dmi(self) -> None:
        violations = [
            entry["folder"]
            for entry in self.registry.get("hidden_skills", [])
            if not self._is_dmi(entry["folder"])
        ]
        self.assertEqual(
            violations,
            [],
            "Registry lists these as hidden_skills but SKILL.md lacks "
            "disable-model-invocation: true (move to visible_skills or "
            "add the DMI flag):\n" + "\n".join(violations),
        )


if __name__ == "__main__":
    unittest.main()
