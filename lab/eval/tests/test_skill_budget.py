"""Tests for lab.eval.skill_budget."""

import tempfile
import unittest
from pathlib import Path

from lab.eval import skill_budget


class SkillBudgetTests(unittest.TestCase):
    def test_measure_skill_combined_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "myskill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: myskill\ndescription: abcde\nwhen_to_use: 12345\n---\n"
            )
            result = skill_budget.measure_skill(skill_dir)
            self.assertIsNotNone(result)
            label, combined, hidden = result
            self.assertEqual(label, "myskill")
            self.assertEqual(combined, 10)
            self.assertFalse(hidden)

    def test_measure_skill_uses_frontmatter_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "review"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\nname: rb:review\ndescription: x\n---\n"
            )
            result = skill_budget.measure_skill(skill_dir)
            self.assertIsNotNone(result)
            label, _, _ = result
            self.assertEqual(label, "rb:review")

    def test_measure_skill_falls_back_to_dir_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "noname"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(
                "---\ndescription: x\n---\n"
            )
            result = skill_budget.measure_skill(skill_dir)
            self.assertIsNotNone(result)
            label, _, _ = result
            self.assertEqual(label, "noname")

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
