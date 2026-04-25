"""Tests for neighbor regression detection."""


import unittest
from unittest.mock import patch

from lab.eval.neighbor_regression import (
    build_neighbor_map,
    compare_results,
    get_changed_skills,
    get_test_set,
)


SAMPLE_PAIRS = {
    "pairs": [
        {"left": "plan", "right": "work", "overlap": 0.35, "shared_tokens": []},
        {"left": "plan", "right": "full", "overlap": 0.30, "shared_tokens": []},
        {"left": "plan", "right": "brief", "overlap": 0.25, "shared_tokens": []},
        {"left": "work", "right": "full", "overlap": 0.20, "shared_tokens": []},
    ],
    "count": 4,
}


class TestBuildNeighborMap(unittest.TestCase):
    """Tests for bidirectional neighbor map construction."""

    @patch("lab.eval.neighbor_regression.CONFUSABLE_PAIRS_PATH")
    def test_build_neighbor_map(self, mock_path):
        """Verify bidirectional mapping from confusable pairs."""
        import json
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = json.dumps(SAMPLE_PAIRS)

        neighbors = build_neighbor_map()

        # plan has 3 neighbors
        self.assertEqual(len(neighbors["plan"]), 3)
        # work appears as neighbor of plan
        self.assertIn("work", [n for n, _ in neighbors["plan"]])
        # plan appears as neighbor of work (bidirectional)
        self.assertIn("plan", [n for n, _ in neighbors["work"]])
        # brief only has plan as neighbor
        self.assertEqual(len(neighbors["brief"]), 1)
        self.assertEqual(neighbors["brief"][0][0], "plan")

    @patch("lab.eval.neighbor_regression.CONFUSABLE_PAIRS_PATH")
    def test_neighbors_sorted_by_overlap(self, mock_path):
        """Neighbors are sorted by descending overlap score."""
        import json
        mock_path.is_file.return_value = True
        mock_path.read_text.return_value = json.dumps(SAMPLE_PAIRS)

        neighbors = build_neighbor_map()

        plan_overlaps = [o for _, o in neighbors["plan"]]
        self.assertEqual(plan_overlaps, sorted(plan_overlaps, reverse=True))

    @patch("lab.eval.neighbor_regression.CONFUSABLE_PAIRS_PATH")
    def test_missing_file_returns_empty(self, mock_path):
        """Returns empty dict when confusable pairs file is missing."""
        mock_path.is_file.return_value = False
        self.assertEqual(build_neighbor_map(), {})


class TestGetTestSet(unittest.TestCase):
    """Tests for test set generation."""

    def test_get_test_set(self):
        """Returns skill + top N neighbors."""
        neighbor_map = {
            "plan": [("work", 0.35), ("full", 0.30), ("brief", 0.25), ("extra", 0.10)],
        }
        test_set = get_test_set("plan", neighbor_map, max_neighbors=3)

        self.assertEqual(len(test_set), 4)  # skill + 3 neighbors
        self.assertEqual(test_set[0], ("plan", None))
        self.assertEqual(test_set[1], ("work", 0.35))
        self.assertEqual(test_set[3], ("brief", 0.25))

    def test_skill_without_neighbors(self):
        """Skill with no confusable pairs returns only itself."""
        test_set = get_test_set("isolated", {}, max_neighbors=3)
        self.assertEqual(test_set, [("isolated", None)])


class TestCompareResults(unittest.TestCase):
    """Tests for baseline vs current comparison."""

    def test_compare_no_regression(self):
        """No regression when accuracy is stable."""
        baseline = {"accuracy": 1.0}
        current = {"accuracy": 1.0}
        result = compare_results("plan", baseline, current)

        self.assertFalse(result["regression"])
        self.assertEqual(result["delta"], 0.0)
        self.assertEqual(result["baseline_accuracy"], 1.0)
        self.assertEqual(result["current_accuracy"], 1.0)

    def test_compare_with_regression(self):
        """Flags regression when accuracy drops > 10%."""
        baseline = {"accuracy": 1.0}
        current = {"accuracy": 0.75}
        result = compare_results("plan", baseline, current)

        self.assertTrue(result["regression"])
        self.assertEqual(result["delta"], -0.25)

    def test_compare_small_drop_no_regression(self):
        """Small accuracy drops (<=10%) are not flagged."""
        baseline = {"accuracy": 1.0}
        current = {"accuracy": 0.92}
        result = compare_results("plan", baseline, current)

        self.assertFalse(result["regression"])

    def test_compare_improvement_no_regression(self):
        """Accuracy improvements are never flagged."""
        baseline = {"accuracy": 0.75}
        current = {"accuracy": 1.0}
        result = compare_results("plan", baseline, current)

        self.assertFalse(result["regression"])
        self.assertEqual(result["delta"], 0.25)


class TestGetChangedSkills(unittest.TestCase):
    """Tests for git-based skill change detection."""

    @patch("subprocess.run")
    def test_get_changed_skills(self, mock_run):
        """Extracts skill names from git diff output."""
        mock_run.return_value = type("Result", (), {
            "returncode": 0,
            "stdout": "plugins/ruby-grape-rails/skills/plan/SKILL.md\n"
                      "plugins/ruby-grape-rails/skills/work/SKILL.md\n"
                      "lab/eval/scorer.py\n",
        })()

        skills = get_changed_skills()
        self.assertIn("plan", skills)
        self.assertIn("work", skills)
        self.assertNotIn("scorer", skills)

    @patch("subprocess.run")
    def test_git_failure_returns_empty(self, mock_run):
        """Returns empty list when git command fails."""
        mock_run.return_value = type("Result", (), {
            "returncode": 1,
            "stdout": "",
        })()

        self.assertEqual(get_changed_skills(), [])


if __name__ == "__main__":
    unittest.main()
