"""Tests for lab.eval.skill_budget."""

import tempfile
import unittest
from pathlib import Path

from lab.eval import skill_budget


class SkillBudgetTests(unittest.TestCase):
    def test_parses_frontmatter(self) -> None:
        text = "---\nname: foo\ndescription: bar\nwhen_to_use: baz\n---\nbody"
        fm = skill_budget.parse_frontmatter(text)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["name"], "foo")
        self.assertEqual(fm["description"], "bar")
        self.assertEqual(fm["when_to_use"], "baz")

    def test_returns_none_on_no_frontmatter(self) -> None:
        self.assertIsNone(skill_budget.parse_frontmatter("no frontmatter here"))

    def test_returns_none_on_invalid_yaml(self) -> None:
        text = "---\n: : :invalid\n---\nbody"
        self.assertIsNone(skill_budget.parse_frontmatter(text))

    def test_measure_skill_combined_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "myskill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: myskill\ndescription: abcde\nwhen_to_use: 12345\n---\n"
            )
            result = skill_budget.measure_skill(skill_dir)
            self.assertIsNotNone(result)
            name, combined, hidden = result
            self.assertEqual(name, "myskill")
            self.assertEqual(combined, 10)
            self.assertFalse(hidden)

    def test_measure_skill_detects_disable_model_invocation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "hidden"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: hidden\ndescription: x\n"
                "disable-model-invocation: true\n---\n"
            )
            result = skill_budget.measure_skill(skill_dir)
            self.assertIsNotNone(result)
            _, _, hidden = result
            self.assertTrue(hidden)

    def test_measure_skill_returns_none_for_dir_without_skill_md(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "empty"
            skill_dir.mkdir()
            self.assertIsNone(skill_budget.measure_skill(skill_dir))


if __name__ == "__main__":
    unittest.main()
