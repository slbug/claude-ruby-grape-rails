"""Tests for the behavioral eval dimension and scorer."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Ensure project root is importable
import sys
PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lab.eval.behavioral_scorer import (
    build_routing_prompt,
    content_hash,
    score_skill,
)
from lab.eval.dimensions.behavioral import score as behavioral_score


SAMPLE_DESCRIPTIONS = {
    "plan": "Plan implementation approach for Ruby/Rails features",
    "work": "Execute plan tasks with structured progress tracking",
    "review": "Review code changes with parallel specialist agents",
}


class TestContentHash(unittest.TestCase):
    """Tests for cache invalidation hashing."""

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_stability(self, mock_trigger):
        """Same inputs produce the same hash."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        h2 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        self.assertEqual(h1, h2)

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_changes_with_description(self, mock_trigger):
        """Different descriptions produce different hashes."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        modified = dict(SAMPLE_DESCRIPTIONS)
        modified["plan"] = "Completely different description"
        h2 = content_hash("plan", modified)
        self.assertNotEqual(h1, h2)

    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    def test_hash_changes_with_triggers(self, mock_trigger):
        """Different trigger corpora produce different hashes."""
        mock_trigger.return_value = {"should_trigger": ["plan a feature"]}
        h1 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        mock_trigger.return_value = {"should_trigger": ["design architecture"]}
        h2 = content_hash("plan", SAMPLE_DESCRIPTIONS)
        self.assertNotEqual(h1, h2)


class TestRoutingPrompt(unittest.TestCase):
    """Tests for the routing prompt builder."""

    def test_includes_all_descriptions(self):
        """Prompt contains all skill names and descriptions."""
        prompt = build_routing_prompt(SAMPLE_DESCRIPTIONS, "plan a feature")
        for name, desc in SAMPLE_DESCRIPTIONS.items():
            self.assertIn(name, prompt)
            self.assertIn(desc[:50], prompt)

    def test_includes_user_prompt(self):
        """Prompt contains the user's input."""
        user_input = "I need to plan a new authentication feature"
        prompt = build_routing_prompt(SAMPLE_DESCRIPTIONS, user_input)
        self.assertIn(user_input, prompt)

    def test_response_format_instructions(self):
        """Prompt asks for skill names only."""
        prompt = build_routing_prompt(SAMPLE_DESCRIPTIONS, "test")
        self.assertIn("ONLY", prompt)
        self.assertIn("skill name", prompt.lower())


class TestBehavioralDimension(unittest.TestCase):
    """Tests for the dimension scorer that reads cached results."""

    def test_neutral_without_cache(self):
        """Returns 1.0 when no cache exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path=f"{tmpdir}/nonexistent/SKILL.md",
                )
                self.assertEqual(result.score, 1.0)
                self.assertEqual(result.name, "behavioral")
                self.assertTrue(all(a.passed for a in result.assertions))

    def test_score_from_cached_passing(self):
        """Returns passing score from cached results above thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {
                "skill": "plan",
                "accuracy": 0.875,
                "precision": 0.857,
                "recall": 0.75,
                "total": 8,
                "correct": 7,
                "tp": 6, "fp": 1, "fn": 2,
            }
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertGreater(result.score, 0.0)
                self.assertEqual(result.name, "behavioral")
                self.assertTrue(all(a.passed for a in result.assertions))

    def test_score_from_cached_failing(self):
        """Returns failing score from cached results below thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {
                "skill": "plan",
                "accuracy": 0.50,
                "precision": 0.50,
                "recall": 0.40,
                "total": 8,
                "correct": 4,
                "tp": 2, "fp": 2, "fn": 3,
            }
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertLess(result.score, 1.0)
                self.assertFalse(all(a.passed for a in result.assertions))

    def test_error_in_cache_returns_neutral(self):
        """Returns neutral score when cache contains an error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_data = {"skill": "plan", "error": "no trigger file"}
            cache_path = Path(tmpdir) / "plan.json"
            cache_path.write_text(json.dumps(cache_data))

            with patch("lab.eval.dimensions.behavioral.RESULTS_DIR", Path(tmpdir)):
                result = behavioral_score(
                    content="",
                    skill_path="/fake/skills/plan/SKILL.md",
                )
                self.assertEqual(result.score, 1.0)


class TestScoreSkill(unittest.TestCase):
    """Tests for the behavioral scorer's score_skill function."""

    @patch("lab.eval.behavioral_scorer.run_haiku")
    @patch("lab.eval.behavioral_scorer.load_trigger_file")
    @patch("lab.eval.behavioral_scorer.load_all_descriptions")
    def test_score_skill_with_mock_haiku(self, mock_descs, mock_triggers, mock_haiku):
        """Scores correctly with mocked haiku responses."""
        mock_descs.return_value = SAMPLE_DESCRIPTIONS
        mock_triggers.return_value = {
            "should_trigger": ["plan a feature", "design an implementation"],
            "should_not_trigger": ["review my code", "fix this bug"],
        }
        mock_haiku.side_effect = [
            ["plan"],         # should_trigger: correct
            ["plan"],         # should_trigger: correct
            ["review"],       # should_not_trigger: correct (plan not in list)
            ["work"],         # should_not_trigger: correct (plan not in list)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("lab.eval.behavioral_scorer.RESULTS_DIR", Path(tmpdir)):
                result = score_skill("plan", SAMPLE_DESCRIPTIONS)

        self.assertEqual(result["accuracy"], 1.0)
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["correct"], 4)


if __name__ == "__main__":
    unittest.main()
